import hashlib
import time
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Literal, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.config import settings
from backend.app.db.models import ApiKeyState
from backend.app.db.session import async_session_factory

Provider = Literal["gemini", "groq"]

def key_id(key: str) -> str:
    """Generates a stable 10-char hash of an API key for logs and slot IDs."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]

class Slot:
    def __init__(self, provider: Provider, model: str, key: str, key_index: int):
        self.provider = provider
        self.model = model
        self.key = key
        self.key_index = key_index
        self.id = f"{provider}:{key_id(key)}:{model}"

    def __repr__(self):
        return f"<Slot {self.id}>"

class SlotState:
    def __init__(
        self,
        cooldown_until: float = 0.0,
        fatal: bool = False,
        failures: int = 0,
        successes: int = 0,
        last_used_at: float = 0.0,
        last_error: Optional[str] = None
    ):
        self.cooldown_until = cooldown_until
        self.fatal = fatal
        self.failures = failures
        self.successes = successes
        self.last_used_at = last_used_at
        self.last_error = last_error

class KeyPool:
    def __init__(self):
        self._states: Dict[str, SlotState] = {}
        self._loaded_at: float = 0.0
        self._reload_interval: float = 10.0  # seconds

    def clear_cooldowns(self):
        """Clears all in-memory cooldowns and resets failure counts across all slots."""
        for state in self._states.values():
            state.cooldown_until = 0.0
            state.failures = 0
            state.fatal = False

    def all_slots(self) -> List[Slot]:
        slots: List[Slot] = []

        # Model-major order: try best model on each key before dropping to next model
        # 1. Gemini
        for model in settings.parsed_gemini_models:
            for idx, key in enumerate(settings.parsed_gemini_keys):
                slots.append(Slot(provider="gemini", model=model, key=key, key_index=idx))

        # 2. Groq
        for model in settings.parsed_groq_models:
            for idx, key in enumerate(settings.parsed_groq_keys):
                slots.append(Slot(provider="groq", model=model, key=key, key_index=idx))

        return slots

    def get_state(self, slot_id: str) -> SlotState:
        if slot_id not in self._states:
            self._states[slot_id] = SlotState()
        return self._states[slot_id]

    async def load_state_from_db(self):
        now = time.time()
        if now - self._loaded_at < self._reload_interval:
            return
        self._loaded_at = now

        try:
            async with async_session_factory() as session:
                result = await session.execute(select(ApiKeyState))
                rows = result.scalars().all()
                for r in rows:
                    st = self.get_state(r.slot)
                    if r.cooldown_until:
                        cd_ts = r.cooldown_until.timestamp()
                        st.cooldown_until = max(st.cooldown_until, cd_ts)
                    st.failures = r.failures
                    st.successes = r.successes
                    if r.last_used_at:
                        st.last_used_at = max(st.last_used_at, r.last_used_at.timestamp())
                    st.last_error = r.last_error
                    # Fatal if bad/revoked key
                    if r.last_error and re.search(r"401|403|api.?key", r.last_error, re.IGNORECASE):
                        st.fatal = True
        except Exception:
            # Non-critical: KeyPool operates in-memory if DB is temporarily unreachable
            pass

    async def persist_state(self, slot_id: str):
        st = self.get_state(slot_id)
        try:
            async with async_session_factory() as session:
                cd_dt = datetime.fromtimestamp(st.cooldown_until, tz=timezone.utc) if st.cooldown_until > 0 else None
                lu_dt = datetime.fromtimestamp(st.last_used_at, tz=timezone.utc) if st.last_used_at > 0 else datetime.now(timezone.utc)

                record = await session.get(ApiKeyState, slot_id)
                if not record:
                    record = ApiKeyState(
                        slot=slot_id,
                        cooldown_until=cd_dt,
                        failures=st.failures,
                        successes=st.successes,
                        last_error=st.last_error,
                        last_used_at=lu_dt
                    )
                    session.add(record)
                else:
                    record.cooldown_until = cd_dt
                    record.failures = st.failures
                    record.successes = max(record.successes, st.successes)
                    record.last_error = st.last_error
                    record.last_used_at = lu_dt

                await session.commit()
        except Exception:
            pass

    async def ordered_slots(self) -> List[Slot]:
        """Returns candidate slots: Gemini first, then Groq; cooling down slots skipped; LRU sorted."""
        await self.load_state_from_db()
        slots = self.all_slots()
        now = time.time()

        healthy: List[Tuple[float, Slot]] = []
        cooling: List[Tuple[float, Slot]] = []

        for slot in slots:
            st = self.get_state(slot.id)
            if st.fatal:
                continue
            if st.cooldown_until <= now:
                # Healthy slot: priority by least recently used
                healthy.append((st.last_used_at, slot))
            else:
                cooling.append((st.cooldown_until, slot))

        # Sort healthy slots by last_used_at ascending (LRU)
        healthy.sort(key=lambda x: x[0])
        # Sort cooling slots by who recovers earliest
        cooling.sort(key=lambda x: x[0])

        # Separate by provider priority: Gemini first, Groq second
        def filter_by_provider(items, prov):
            return [slot for _, slot in items if slot.provider == prov]

        gemini_healthy = filter_by_provider(healthy, "gemini")
        groq_healthy = filter_by_provider(healthy, "groq")

        # Fallback to cooling slots if all healthy slots are exhausted
        gemini_cooling = filter_by_provider(cooling, "gemini")
        groq_cooling = filter_by_provider(cooling, "groq")

        return gemini_healthy + groq_healthy + gemini_cooling + groq_cooling

    async def mark_used(self, slot: Slot):
        st = self.get_state(slot.id)
        st.last_used_at = time.time()
        await self.persist_state(slot.id)

    async def report_success(self, slot: Slot):
        st = self.get_state(slot.id)
        st.successes += 1
        st.failures = 0
        st.last_error = None
        st.cooldown_until = 0.0
        await self.persist_state(slot.id)

    async def report_failure(self, slot: Slot, status_code: int, error_text: str, retry_after_seconds: Optional[int] = None):
        st = self.get_state(slot.id)
        st.failures += 1
        st.last_error = f"{status_code}: {error_text}"[:256]
        now = time.time()

        if status_code in (401, 403):
            st.fatal = True
            st.cooldown_until = now + 86400.0  # 24 hours
        elif status_code == 429:
            if retry_after_seconds and retry_after_seconds > 0:
                cooldown = float(retry_after_seconds)
            else:
                # Exponential backoff: 30s -> 60s -> 120s -> max 1 hour
                cooldown = min(30.0 * (2 ** min(st.failures - 1, 6)), 3600.0)
            st.cooldown_until = now + cooldown
        else:
            # 5xx or connection error
            st.cooldown_until = now + 15.0

        await self.persist_state(slot.id)

key_pool = KeyPool()
