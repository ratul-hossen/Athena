import asyncio
import logging
from typing import Optional
from backend.app.config import settings
from backend.app.telegram.api import is_telegram_configured, call_tg_method
from backend.app.telegram.handle import handle_telegram_update

logger = logging.getLogger("athina.telegram")

class TelegramBotWorker:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._offset = 0

    def start(self):
        if not is_telegram_configured():
            print("Telegram Bot: Token not configured. Long-polling worker idle.")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        print("Telegram Bot: Long-polling loop started successfully!")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            print("Telegram Bot: Long-polling stopped.")

    async def _poll_loop(self):
        # Delete any existing webhook to ensure clean long-polling
        await call_tg_method("deleteWebhook", {"drop_pending_updates": False})

        while self._running:
            try:
                updates = await call_tg_method("getUpdates", {
                    "offset": self._offset,
                    "timeout": 25,
                    "allowed_updates": ["message"]
                })

                if updates and isinstance(updates, list):
                    for update in updates:
                        update_id = update.get("update_id")
                        if update_id:
                            self._offset = update_id + 1

                        # Process update asynchronously
                        asyncio.create_task(handle_telegram_update(update))

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Network hiccup or telegram timeout: wait 3 seconds and retry
                await asyncio.sleep(3)

telegram_worker = TelegramBotWorker()
