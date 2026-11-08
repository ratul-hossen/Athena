import json
import re
import httpx
from typing import List, Dict, Any, AsyncGenerator, Optional
from backend.app.llm.keypool import key_pool, Slot, Provider

BASE_URLS: Dict[Provider, str] = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions"
}

class AllProvidersFailedException(Exception):
    def __init__(self, tried: List[str]):
        super().__init__(
            f"All LLM keys are busy, cooling down, or exhausted ({len(tried)} slots tried: {', '.join(tried)}). Please try again shortly."
            if tried else "No valid API keys configured. Set GEMINI_API_KEYS or GROQ_API_KEYS."
        )
        self.tried = tried

class ThinkFilter:
    """Strips <think>...</think> blocks from streamed output even across chunk boundaries."""
    def __init__(self):
        self.buf = ""
        self.thinking = False
        self.shown = False

    def push(self, text: str) -> str:
        self.buf += text
        out = ""
        while self.buf:
            if self.thinking:
                end_idx = self.buf.indexOf("</think>") if hasattr(self.buf, "indexOf") else self.buf.find("</think>")
                if end_idx < 0:
                    # Keep possible prefix of "</think>"
                    self.buf = self.buf[-7:] if len(self.buf) > 7 else self.buf
                    break
                self.buf = self.buf[end_idx + 8:]
                self.thinking = False
            else:
                start_idx = self.buf.find("<think>")
                if start_idx < 0:
                    out += self.buf
                    self.buf = ""
                    break
                out += self.buf[:start_idx]
                self.buf = self.buf[start_idx + 7:]
                self.thinking = True

        if not self.shown:
            out = out.lstrip()
            if out:
                self.shown = True
        return out

async def chat_stream(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1500
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Streams chat completion from KeyPool with automatic pre-token failover.
    Yields events:
      {"type": "provider", "provider": ..., "model": ..., "slot_id": ...}
      {"type": "token", "text": ...}
      {"type": "image_trigger", "prompt": ...}
    """
    candidate_slots = await key_pool.ordered_slots()
    if not candidate_slots:
        raise AllProvidersFailedException([])

    tried_slots: List[str] = []

    for slot in candidate_slots:
        tried_slots.append(slot.id)
        endpoint = BASE_URLS.get(slot.provider)
        if not endpoint:
            continue

        headers = {
            "Authorization": f"Bearer {slot.key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": slot.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        first_token_sent = False
        think_filter = ThinkFilter()
        collected_full_text = ""

        try:
            await key_pool.mark_used(slot)
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=40.0, write=10.0, pool=10.0)) as client:
                async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        error_text = error_body.decode(errors="replace")
                        retry_after = response.headers.get("Retry-After")
                        retry_secs = int(retry_after) if retry_after and retry_after.isdigit() else None
                        await key_pool.report_failure(slot, response.status_code, error_text, retry_secs)
                        continue  # Try next slot

                    # Successfully connected, emit provider event
                    yield {
                        "type": "provider",
                        "provider": slot.provider,
                        "model": slot.model,
                        "slot_id": slot.id,
                        "attempts": len(tried_slots)
                    }

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_part = line[5:].strip()
                        if data_part == "[DONE]":
                            break

                        try:
                            parsed = json.loads(data_part)
                            delta = parsed.get("choices", [{}])[0].get("delta", {})
                            content_piece = delta.get("content", "")
                            if content_piece:
                                first_token_sent = True
                                clean_text = think_filter.push(content_piece)
                                collected_full_text += content_piece
                                if clean_text:
                                    yield {"type": "token", "text": clean_text}
                        except Exception:
                            continue

            # Stream finished successfully
            await key_pool.report_success(slot)

            # Check for image triggers
            # Syntax: [[IMAGE_TRIGGER: <prompt>]]
            img_match = re.search(r"\[\[IMAGE_TRIGGER:\s*(.+?)\]\]", collected_full_text, re.DOTALL)
            if img_match:
                img_prompt = img_match.group(1).strip()
                yield {"type": "image_trigger", "prompt": img_prompt}

            return

        except Exception as e:
            if first_token_sent:
                # Mid-stream error; do not silently switch models mid-sentence
                yield {"type": "error", "error": f"Stream interrupted: {str(e)}"}
                return
            else:
                # Pre-token error: log failure and loop to next slot
                await key_pool.report_failure(slot, 500, str(e))
                continue

    raise AllProvidersFailedException(tried_slots)
