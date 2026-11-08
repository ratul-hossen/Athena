import os
import gzip
import io
import asyncio
from datetime import datetime, timezone
from typing import Optional
from backend.app.config import settings
from backend.app.telegram.api import send_document

async def run_database_backup() -> Optional[str]:
    """
    Performs database dump, compresses with gzip, and sends directly
    to the private Telegram storage channel.
    """
    channel_id = settings.telegram_storage_channel_id or settings.telegram_owner_id
    if not channel_id:
        print("Telegram backup skipped: TELEGRAM_STORAGE_CHANNEL_ID not set.")
        return None

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    db_url = settings.database_url

    backup_bytes: Optional[bytes] = None
    backup_filename = f"athina_db_{now_str}.sql.gz"

    if "sqlite" in db_url:
        # For SQLite: read the database file and gzip it
        db_path = db_url.split(":///")[-1]
        if not os.path.exists(db_path):
            db_path = "./athina.db"

        if os.path.exists(db_path):
            with open(db_path, "rb") as f_in:
                raw_data = f_in.read()
            backup_bytes = gzip.compress(raw_data)
            backup_filename = f"athina_sqlite_{now_str}.db.gz"
    else:
        # For PostgreSQL: run pg_dump subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                "pg_dump", db_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if stdout:
                backup_bytes = gzip.compress(stdout)
        except Exception as e:
            print(f"pg_dump failed: {e}")
            return None

    if not backup_bytes:
        print("No database bytes captured for backup.")
        return None

    caption = (
        f"📦 *Athina Database Nightly Backup*\n"
        f"Timestamp: `{now_str} UTC`\n"
        f"Compressed Size: `{len(backup_bytes) / 1024:.1f} KB`"
    )

    file_id = await send_document(
        chat_id=channel_id,
        file_bytes=backup_bytes,
        filename=backup_filename,
        caption=caption
    )

    if file_id:
        print(f"Database backup sent successfully to Telegram! File ID: {file_id}")
    return file_id
