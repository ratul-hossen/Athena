import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from backend.app.images.generator import generate_athina_image_nanobanana

def utc_now():
    return datetime.now(timezone.utc)

async def create_and_run_image_job(
    prompt: str,
    session_id: str = "main",
    send_telegram: bool = True
) -> Dict[str, Any]:
    """Processes an image request asynchronously via Nano Banana."""
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    result = await generate_athina_image_nanobanana(prompt, job_id=job_id)

    # If telegram channel is configured and image exists, send it
    if send_telegram and result.get("local_path"):
        try:
            from backend.app.telegram.api import send_photo
            from backend.app.config import settings
            channel_id = getattr(settings, "TELEGRAM_STORAGE_CHANNEL_ID", None)
            if channel_id and os.path.exists(result["local_path"]):
                caption = f"📸 Athina Photo: {prompt[:120]}"
                await send_photo(channel_id, result["local_path"], caption=caption)
        except Exception:
            pass

    return result
