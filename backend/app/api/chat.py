import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db, async_session_factory
from backend.app.db.models import ChatSession, ChatMessage, ImageJobRecord
from backend.app.personality.state import PersonalityState
from backend.app.personality.prompt import build_system_prompt
from backend.app.personality.style_model import compute_style_vector
from backend.app.memory.retrieval import retrieve_relevant_facts
from backend.app.memory.facts import extract_and_save_facts
from backend.app.memory.actions import parse_and_strip_actions, handle_note_action, handle_alarm_action
from backend.app.llm.chat import chat_stream

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Session ID. If omitted, a new session is created.")
    message: str = Field(..., min_length=1, description="User message text in English.")
    channel: Optional[str] = Field(default="android", description="Client source: android, web, or telegram.")

async def stream_chat_generator(session_id: str, user_text: str, channel: str):
    user_msg_id = str(uuid.uuid4())
    asst_msg_id = str(uuid.uuid4())

    # 1. Setup session, save user message, and retrieve memories
    async with async_session_factory() as db:
        session = await db.get(ChatSession, session_id)
        if not session:
            session = ChatSession(id=session_id, title=user_text[:40], channel=channel)
            db.add(session)
            await db.commit()

        # Save user message
        user_msg = ChatMessage(id=user_msg_id, session_id=session_id, role="user", content=user_text)
        db.add(user_msg)
        await db.commit()

        # Fetch last 10 messages for context
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        recent_messages = list(reversed(result.scalars().all()))

        # Long-Term Memory: Retrieve relevant facts using Hybrid RRF
        relevant_facts = await retrieve_relevant_facts(db, user_text, top_k=5)

        # ML Style & Emotion Adaptation
        state = PersonalityState.calculate_current_state()
        tone_guidance, style_meta = compute_style_vector(user_text, state)

        # Optional Real-Time Web Search via Tavily
        search_triggers = ["search", "latest", "today", "news", "weather", "price", "current", "who won", "what happened"]
        if any(t in user_text.lower() for t in search_triggers):
            try:
                from backend.app.search.tavily import search_tavily, format_search_context
                search_data = await search_tavily(user_text)
                if search_data:
                    tone_guidance += format_search_context(search_data)
            except Exception:
                pass

        # Build prompt payload
        system_prompt = build_system_prompt(state=state, facts=relevant_facts, tone_guidance=tone_guidance)
        messages_payload = [{"role": "system", "content": system_prompt}]
        for m in recent_messages:
            messages_payload.append({"role": m.role, "content": m.content})

    # 2. Stream generation from KeyPool
    accumulated_text = ""
    provider_info = {}
    image_prompt = None

    try:
        # Emit style/intent event first
        yield f"data: {json.dumps({'type': 'style_meta', 'data': style_meta})}\n\n"

        async for event in chat_stream(messages_payload):
            if event["type"] == "provider":
                provider_info = event
                yield f"data: {json.dumps(event)}\n\n"
            elif event["type"] == "token":
                accumulated_text += event["text"]
                yield f"data: {json.dumps(event)}\n\n"
            elif event["type"] == "image_trigger":
                image_prompt = event["prompt"]
            elif event["type"] == "error":
                yield f"data: {json.dumps(event)}\n\n"

        # 3. Post-processing: Parse action tags (Notes, Telegram upload, Alarms)
        clean_text, actions = parse_and_strip_actions(accumulated_text)
        if image_prompt:
            clean_text = clean_text.replace(f"[[IMAGE_TRIGGER: {image_prompt}]]", "").strip()

        meta_combined = {**provider_info, "style_vector": style_meta}

        async with async_session_factory() as db:
            # Save assistant message
            asst_msg = ChatMessage(
                id=asst_msg_id,
                session_id=session_id,
                role="assistant",
                content=clean_text,
                meta_json=json.dumps(meta_combined)
            )
            db.add(asst_msg)

            # Handle Note Action
            if "note" in actions:
                n_info = actions["note"]
                note = await handle_note_action(
                    db,
                    title=n_info["title"],
                    content=n_info["content"],
                    upload_telegram=n_info["upload_telegram"]
                )
                note_event = {
                    "type": "action_executed",
                    "action": "note",
                    "note_id": note.id,
                    "title": note.title,
                    "uploaded_to_telegram": note.uploaded_to_telegram
                }
                yield f"data: {json.dumps(note_event)}\n\n"

            # Handle Alarm Action
            if "alarm" in actions:
                a_info = actions["alarm"]
                alarm = await handle_alarm_action(
                    db,
                    label=a_info["label"],
                    time_iso=a_info["time_iso"],
                    repeat_days=a_info["repeat_days"]
                )
                alarm_event = {
                    "type": "action_executed",
                    "action": "alarm",
                    "alarm_id": alarm.id,
                    "label": alarm.label,
                    "time_iso": alarm.time_iso
                }
                yield f"data: {json.dumps(alarm_event)}\n\n"

            # If image was requested, queue ImageJob
            if image_prompt:
                job_id = str(uuid.uuid4())
                job = ImageJobRecord(
                    id=job_id,
                    session_id=session_id,
                    prompt=image_prompt,
                    status="queued",
                    tier=1
                )
                db.add(job)
                await db.commit()

                job_event = {
                    "type": "image_job",
                    "job_id": job_id,
                    "prompt": image_prompt,
                    "status": "queued"
                }
                yield f"data: {json.dumps(job_event)}\n\n"
            else:
                await db.commit()

            # 4. Long-Term Memory Extraction
            await extract_and_save_facts(db, session_id, asst_msg_id, user_text, clean_text)

        yield "data: [DONE]\n\n"

    except Exception as e:
        error_event = {"type": "error", "error": str(e)}
        yield f"data: {json.dumps(error_event)}\n\n"
        yield "data: [DONE]\n\n"

@router.post("")
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    return StreamingResponse(
        stream_chat_generator(session_id, req.message, req.channel or "android"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id
        }
    )
