import uuid
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.app.db.models import AthinaNote, AthinaAlarm
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    AsyncSession = Any
    AthinaNote = Any
    AthinaAlarm = Any

from backend.app.config import settings

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

async def upload_note_to_telegram(title: str, content: str) -> Optional[int]:
    """Sends a note directly to Ratul's Telegram chat or storage channel."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_owner_id or settings.telegram_storage_channel_id

    if not token or not chat_id:
        return None

    message_text = f"📝 *Athina Note: {title}*\n\n{content}\n\n_Saved by Athina on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "Markdown"
    }

    try:
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("result", {}).get("message_id")
        else:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    return data.get("result", {}).get("message_id")
    except Exception:
        pass
    return None

async def handle_note_action(
    db: Any,
    title: str,
    content: str,
    upload_telegram: bool = False
) -> Any:
    """Saves a note in the database and optionally forwards to Telegram."""
    telegram_msg_id = None
    if upload_telegram:
        telegram_msg_id = await upload_note_to_telegram(title, content)

    if not HAS_SQLALCHEMY:
        return None

    note = AthinaNote(
        id=str(uuid.uuid4()),
        title=title.strip(),
        content=content.strip(),
        uploaded_to_telegram=(telegram_msg_id is not None or upload_telegram),
        telegram_msg_id=telegram_msg_id
    )
    db.add(note)
    await db.commit()
    return note

async def handle_alarm_action(
    db: Any,
    label: str,
    time_iso: str,
    repeat_days: Optional[str] = None
) -> Any:
    """Creates a new alarm or timed reminder."""
    if not HAS_SQLALCHEMY:
        return None

    alarm = AthinaAlarm(
        id=str(uuid.uuid4()),
        label=label.strip(),
        time_iso=time_iso.strip(),
        repeat_days=repeat_days.strip() if repeat_days else None,
        is_active=True
    )
    db.add(alarm)
    await db.commit()
    return alarm

def parse_and_strip_actions(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parses action tags embedded in Athina's response:
    - [[NOTE_ACTION: <title> | <content> | <upload_telegram: true/false>]]
    - [[ALARM_ACTION: <label> | <time_iso> | <repeat_days>]]
    Returns: (clean_text, action_dict)
    """
    actions: Dict[str, Any] = {}
    clean_text = text

    # Parse Note Action
    note_match = re.search(r"\[\[NOTE_ACTION:\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(true|false)\]\]", clean_text, re.IGNORECASE)
    if note_match:
        actions["note"] = {
            "title": note_match.group(1).strip(),
            "content": note_match.group(2).strip(),
            "upload_telegram": note_match.group(3).lower() == "true"
        }
        clean_text = clean_text.replace(note_match.group(0), "").strip()

    # Parse Alarm Action
    alarm_match = re.search(r"\[\[ALARM_ACTION:\s*(.+?)\s*\|\s*(.+?)(?:\s*\|\s*(.+?))?\]\]", clean_text)
    if alarm_match:
        actions["alarm"] = {
            "label": alarm_match.group(1).strip(),
            "time_iso": alarm_match.group(2).strip(),
            "repeat_days": alarm_match.group(3).strip() if alarm_match.group(3) else None
        }
        clean_text = clean_text.replace(alarm_match.group(0), "").strip()

    return clean_text, actions
