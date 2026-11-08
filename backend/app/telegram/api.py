import os
import re
import urllib.request
import urllib.error
import json
from typing import Optional, Dict, Any, List, Union
from backend.app.config import settings

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

def is_telegram_configured() -> bool:
    token = settings.telegram_bot_token.strip()
    return bool(token and ":" in token)

def get_base_url() -> str:
    return f"https://api.telegram.org/bot{settings.telegram_bot_token.strip()}"

def get_file_url(file_path: str) -> str:
    return f"https://api.telegram.org/file/bot{settings.telegram_bot_token.strip()}/{file_path}"

async def call_tg_method(method: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not is_telegram_configured():
        return None

    url = f"{get_base_url()}/{method}"
    try:
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json().get("result")
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20.0) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode()).get("result")
    except Exception:
        pass
    return None

async def send_typing(chat_id: str):
    await call_tg_method("sendChatAction", {"chat_id": chat_id, "action": "typing"})

async def send_upload_photo_action(chat_id: str):
    await call_tg_method("sendChatAction", {"chat_id": chat_id, "action": "upload_photo"})

async def send_message(
    chat_id: str,
    text: str,
    parse_mode: Optional[str] = "Markdown"
) -> Optional[int]:
    """Sends a text message to Telegram."""
    res = await call_tg_method("sendMessage", {
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": parse_mode
    })
    return res.get("message_id") if res else None

async def send_document(
    chat_id: str,
    file_bytes: bytes,
    filename: str,
    caption: Optional[str] = None
) -> Optional[str]:
    """Uploads a document (e.g. backup or note) to a Telegram chat or storage channel."""
    if not is_telegram_configured():
        return None

    url = f"{get_base_url()}/sendDocument"
    if HAS_HTTPX:
        files = {"document": (filename, file_bytes)}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption[:1024]
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, data=data, files=files)
                if res.status_code == 200:
                    doc = res.json().get("result", {}).get("document", {})
                    return doc.get("file_id")
        except Exception:
            pass
    return None

async def send_photo(
    chat_id: str,
    photo_input: Union[bytes, str],
    caption: Optional[str] = None
) -> Optional[str]:
    """Uploads a photo to a Telegram chat or storage channel. Accepts raw bytes or local file path."""
    if not is_telegram_configured():
        return None

    if isinstance(photo_input, str):
        if os.path.exists(photo_input):
            try:
                with open(photo_input, "rb") as f:
                    photo_bytes = f.read()
            except Exception:
                return None
        else:
            return None
    elif isinstance(photo_input, bytes):
        photo_bytes = photo_input
    else:
        return None

    url = f"{get_base_url()}/sendPhoto"
    if HAS_HTTPX:
        files = {"photo": ("athina.jpg", photo_bytes, "image/jpeg")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption[:1024]
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, data=data, files=files)
                if res.status_code == 200:
                    photos = res.json().get("result", {}).get("photo", [])
                    if photos:
                        return photos[-1].get("file_id")
        except Exception:
            pass
    return None

async def download_file_by_id(file_id: str) -> Optional[bytes]:
    """Gets file path from Telegram and downloads raw bytes."""
    res = await call_tg_method("getFile", {"file_id": file_id})
    if not res:
        return None

    file_path = res.get("file_path")
    if not file_path:
        return None

    download_url = get_file_url(file_path)
    try:
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(download_url)
                if resp.status_code == 200:
                    return resp.content
        else:
            with urllib.request.urlopen(download_url, timeout=30.0) as resp:
                if resp.status == 200:
                    return resp.read()
    except Exception:
        pass
    return None
