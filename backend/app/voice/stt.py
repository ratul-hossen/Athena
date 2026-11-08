import io
from typing import Optional
from backend.app.config import settings
from backend.app.voice.clarion import clarion_repair_asr

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

async def transcribe_audio_groq(audio_bytes: bytes, filename: str = "voice.ogg", repair: bool = True) -> Optional[str]:
    """Transcribes audio using Groq's high-speed Whisper Large-v3 model with Clarion error repair."""
    groq_keys = settings.parsed_groq_keys
    if not groq_keys:
        return None

    model = settings.groq_stt_model or "whisper-large-v3"
    url = "https://api.groq.com/openai/v1/audio/transcriptions"

    for key in groq_keys:
        headers = {
            "Authorization": f"Bearer {key}"
        }
        files = {
            "file": (filename, audio_bytes, "audio/ogg")
        }
        data = {
            "model": model,
            "language": "en",
            "response_format": "json"
        }

        try:
            if HAS_HTTPX:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, headers=headers, data=data, files=files)
                    if res.status_code == 200:
                        json_data = res.json()
                        raw_text = json_data.get("text", "").strip()
                        if repair and raw_text:
                            return clarion_repair_asr(raw_text)
                        return raw_text
            else:
                return None
        except Exception:
            continue
    return None
