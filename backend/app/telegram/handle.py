import json
import uuid
from typing import Dict, Any, Optional

try:
    from sqlalchemy import select
    from backend.app.db.session import async_session_factory
    from backend.app.db.models import ChatSession, ChatMessage, ImageJobRecord
    HAS_DB = True
except ImportError:
    HAS_DB = False
    async_session_factory = None
    ChatSession = None
    ChatMessage = None
    ImageJobRecord = None

from backend.app.config import settings
from backend.app.personality.state import PersonalityState
from backend.app.personality.prompt import build_system_prompt
from backend.app.personality.style_model import compute_style_vector
from backend.app.memory.retrieval import retrieve_relevant_facts
from backend.app.memory.facts import extract_and_save_facts
from backend.app.memory.actions import parse_and_strip_actions, handle_note_action, handle_alarm_action
from backend.app.voice.stt import transcribe_audio_groq
from backend.app.telegram.api import send_message, send_typing, download_file_by_id
from backend.app.telegram.backup import run_database_backup
from backend.app.llm.chat import chat_stream

TELEGRAM_SESSION_ID = "session_main_telegram_ratul"

async def handle_telegram_update(update: Dict[str, Any]):
    """Dispatches incoming Telegram updates (messages, voice, commands)."""
    message = update.get("message")
    if not message:
        return

    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    from_user = message.get("from", {})
    user_id = str(from_user.get("id"))

    # Security check: if TELEGRAM_OWNER_ID is configured, only respond to Ratul
    owner_id = settings.telegram_owner_id.strip()
    if owner_id and user_id != owner_id and chat_id != owner_id:
        await send_message(chat_id, "I only talk with my creator, Ratul. Have a nice day!")
        return

    # 1. Voice Note / Audio Handling
    voice = message.get("voice") or message.get("audio")
    text = message.get("text", "").strip()

    if voice:
        await send_typing(chat_id)
        file_id = voice.get("file_id")
        audio_bytes = await download_file_by_id(file_id)
        if audio_bytes:
            transcribed_text = await transcribe_audio_groq(audio_bytes)
            if transcribed_text:
                text = transcribed_text
            else:
                await send_message(chat_id, "I heard your voice note, but couldn't transcribe the audio. Could you say that again?")
                return
        else:
            await send_message(chat_id, "Failed to download your voice message.")
            return

    if not text:
        return

    # 2. Slash Commands
    if text.startswith("/"):
        cmd = text.split()[0].lower()
        if cmd in ("/start", "/help"):
            welcome = (
                "Hello Ratul! I'm **Athina**, your personal AI companion.\n\n"
                "You can chat with me here or in our Android app. We share the same memory, "
                "so whatever you tell me here, I'll remember everywhere.\n\n"
                "Commands:\n"
                "• /status - My current mood & state\n"
                "• /backup - Trigger an offsite database backup\n"
                "• Send me any voice note or text message!"
            )
            await send_message(chat_id, welcome)
            return

        elif cmd == "/status":
            state = PersonalityState.calculate_current_state()
            status_text = (
                f"✨ *Athina Status*\n"
                f"• Mood: `{state.mood}`\n"
                f"• Location: `{state.location}`\n"
                f"• Energy: `{int(state.energy * 100)}%`\n"
                f"• Relationship Warmth: `{int(state.relationship_warmth * 100)}%`"
            )
            await send_message(chat_id, status_text)
            return

        elif cmd == "/backup":
            await send_message(chat_id, "⏳ Generating database backup and archiving to storage channel…")
            file_id = await run_database_backup()
            if file_id:
                await send_message(chat_id, " Database backup completed and uploaded successfully!")
            else:
                await send_message(chat_id, "❌ Backup failed or storage channel not configured.")
            return

    # 3. Conversational Message (Shared Session & Memory)
    await send_typing(chat_id)
    user_msg_id = str(uuid.uuid4())
    asst_msg_id = str(uuid.uuid4())

    if not HAS_DB:
        await send_message(chat_id, "Database connection not initialized.")
        return

    async with async_session_factory() as db:
        # Load or create shared Telegram session
        session = await db.get(ChatSession, TELEGRAM_SESSION_ID)
        if not session:
            session = ChatSession(id=TELEGRAM_SESSION_ID, title="Telegram Chat", channel="telegram")
            db.add(session)
            await db.commit()

        # Save user message
        db.add(ChatMessage(id=user_msg_id, session_id=TELEGRAM_SESSION_ID, role="user", content=text))
        await db.commit()

        # Retrieve Long-Term Memories via Hybrid RRF
        relevant_facts = await retrieve_relevant_facts(db, text, top_k=5)

        # ML Style Adaptation
        state = PersonalityState.calculate_current_state()
        tone_guidance, style_meta = compute_style_vector(text, state)
        sys_prompt = build_system_prompt(state=state, facts=relevant_facts, tone_guidance=tone_guidance)

        # Get recent context
        res = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == TELEGRAM_SESSION_ID)
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        )
        recent = list(reversed(res.scalars().all()))

        prompt_messages = [{"role": "system", "content": sys_prompt}]
        for m in recent:
            prompt_messages.append({"role": m.role, "content": m.content})

    # Stream reply from KeyPool
    accumulated_text = ""
    provider_info = {}
    image_prompt = None

    try:
        async for event in chat_stream(prompt_messages):
            if event["type"] == "provider":
                provider_info = event
            elif event["type"] == "token":
                accumulated_text += event["text"]
            elif event["type"] == "image_trigger":
                image_prompt = event["prompt"]

        clean_text, actions = parse_and_strip_actions(accumulated_text)
        if image_prompt:
            clean_text = clean_text.replace(f"[[IMAGE_TRIGGER: {image_prompt}]]", "").strip()

        # Send text reply to Telegram
        await send_message(chat_id, clean_text)

        # Execute note actions if any
        async with async_session_factory() as db:
            asst_msg = ChatMessage(
                id=asst_msg_id,
                session_id=TELEGRAM_SESSION_ID,
                role="assistant",
                content=clean_text,
                meta_json=json.dumps({**provider_info, "style_vector": style_meta})
            )
            db.add(asst_msg)

            if "note" in actions:
                n = actions["note"]
                await handle_note_action(db, n["title"], n["content"], n["upload_telegram"])
                if not n["upload_telegram"]:
                    await send_message(chat_id, f"📌 Note saved: *{n['title']}*")

            if "alarm" in actions:
                a = actions["alarm"]
                await handle_alarm_action(db, a["label"], a["time_iso"], a["repeat_days"])
                await send_message(chat_id, f"⏰ Alarm set for: `{a['time_iso']}` ({a['label']})")

            if image_prompt:
                job = ImageJobRecord(
                    id=str(uuid.uuid4()),
                    session_id=TELEGRAM_SESSION_ID,
                    prompt=image_prompt,
                    status="queued",
                    tier=1
                )
                db.add(job)

            await db.commit()

            # Learn new facts from this turn
            await extract_and_save_facts(db, TELEGRAM_SESSION_ID, asst_msg_id, text, clean_text)

    except Exception as e:
        await send_message(chat_id, f"I'm feeling a bit dizzy right now: {str(e)}")
