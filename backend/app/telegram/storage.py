from typing import Optional
from backend.app.config import settings
from backend.app.telegram.api import send_photo, send_document

async def store_image_in_telegram_channel(
    photo_bytes: bytes,
    prompt: str
) -> Optional[str]:
    """Stores a generated selfie or image in the private storage channel."""
    channel_id = settings.telegram_storage_channel_id or settings.telegram_owner_id
    if not channel_id:
        return None

    caption = f"📸 Athina Image\nPrompt: {prompt[:300]}"
    return await send_photo(channel_id, photo_bytes, caption=caption)

async def store_file_in_telegram_channel(
    file_bytes: bytes,
    filename: str,
    caption: str
) -> Optional[str]:
    """Stores any arbitrary file or audio in the private storage channel."""
    channel_id = settings.telegram_storage_channel_id or settings.telegram_owner_id
    if not channel_id:
        return None

    return await send_document(channel_id, file_bytes, filename=filename, caption=caption)
