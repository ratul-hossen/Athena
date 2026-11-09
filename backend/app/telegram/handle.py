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
from backend.app.telegram.api import send_message, send_typing, send_photo, send_upload_photo_action, download_file_by_id
from backend.app.telegram.backup import run_database_backup
from backend.app.llm.chat import chat_stream
from backend.app.images.generator import generate_athina_image_nanobanana

TELEGRAM_SESSION_ID = "session_main_telegram_ratul"

def is_photo_request(text: str) -> bool:
    """Detects whether user is asking for a photo, selfie, or picture."""
    t = text.lower().strip()
    if t in ("/pic", "/photo", "/selfie"):
        return True
    triggers = ["picture", "selfie", "pic", "photo", "pics", "photos", "chobi", "ছবি"]
    intents = [
        "send", "show", "see", "want", "let me", "give", "share", "snap", "take",
        "dao", "de", "pathao", "dekhi", "dekhte", "দাও", "পাঠাও"
    ]
    for trig in triggers:
        if trig in t:
            for intent in intents:
                if intent in t:
                    return True
    phrases = [
        "send me your picture", "send a selfie", "send me a selfie",
        "let me see your pic", "let me see you", "want to see you",
        "send me pic", "send pic", "show me yourself", "send me your photo",
        "chobi dao", "chobi pathao", "pic dao", "pic de", "photo dao"
    ]
    return any(p in t for p in phrases)

def extract_photo_scene_and_caption(
    user_text: str,
    image_prompt: Optional[str],
    state: PersonalityState
) -> tuple[str, str]:
    """
    Extracts the visual description and caption for Athina photo generation.
    Honors user's specific outfit, location, or pose requests.
    """
    clean_user = user_text.lower().strip()
    strip_phrases = [
        "/pic", "/photo", "/selfie",
        "i want to see you now, send me pic",
        "i want to see you now",
        "i want to see you",
        "let me see your pic",
        "let me see you",
        "send me your picture now",
        "send me your picture",
        "send me your pic",
        "send me your photo",
        "send me a selfie",
        "send me a photo",
        "send a selfie",
        "send selfie",
        "send me pic",
        "send pic",
        "send photo",
        "show me a picture",
        "show me yourself",
        "can you send me a picture",
        "can you send me a photo",
        "will you wear it and send me picture",
        "will you wear it and send picture",
        "and send me picture",
        "and send picture",
        "picture pathao",
        "chobi pathao",
        "ekta chobi dao",
        "photo dao",
        "pic dao",
        "pic de"
    ]
    for p in strip_phrases:
        clean_user = clean_user.replace(p, "").strip()

    clean_user = clean_user.strip(" ,.?!'\"")

    # If Ratul explicitly requested an attire or action (e.g. "wearing burka", "in saree")
    if len(clean_user) >= 3 and clean_user not in ("now", "please", "today", "pic", "photo", "selfie"):
        scene = clean_user
        caption = f"📸 For you, Ratul • {clean_user.capitalize()}"
    elif image_prompt and len(image_prompt.strip()) >= 5:
        scene = image_prompt.strip()
        clean_scene = scene.replace("photo of athina_woman,", "").replace("photo of athina_woman", "").strip()
        caption = f"📸 For you, Ratul • {clean_scene.capitalize() if clean_scene else state.location}"
    else:
        scene = f"casual selfie, smiling, in {state.location}, {state.mood}"
        caption = f"📸 Here I am for you, Ratul... in the {state.location} thinking of you. 💖"

    return scene, caption

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
                "• /pic - Get a photo of me right now in my current mood & location\n"
                "• /status - My current mood & state\n"
                "• /backup - Trigger an offsite database backup\n"
                "• Or just ask me: 'Send me your picture' or 'Send a selfie' anytime!"
            )
            await send_message(chat_id, welcome)
            return

        elif cmd in ("/pic", "/photo", "/selfie"):
            await send_upload_photo_action(chat_id)
            state = PersonalityState.calculate_current_state()
            scene, caption = extract_photo_scene_and_caption(text, None, state)
            img_result = await generate_athina_image_nanobanana(scene)
            if img_result.get("local_path") and os.path.exists(img_result["local_path"]):
                await send_photo(chat_id, img_result["local_path"], caption=caption)
            else:
                await send_message(chat_id, "I tried to take a photo for you, but my camera fluttered. Ask me again in a moment!")
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

        # Check if Ratul requested a picture or if Athina triggered an image
        wants_photo = is_photo_request(text) or bool(image_prompt)
        if wants_photo:
            try:
                await send_upload_photo_action(chat_id)
                scene, caption = extract_photo_scene_and_caption(text, image_prompt, state)
                img_result = await generate_athina_image_nanobanana(scene)
                if img_result.get("local_path") and os.path.exists(img_result["local_path"]):
                    await send_photo(chat_id, img_result["local_path"], caption=caption)
            except Exception:
                pass

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
