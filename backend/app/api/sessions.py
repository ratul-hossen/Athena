from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.db.models import ChatSession, ChatMessage
from backend.app.memory.facts import delete_memories_for_session, delete_memories_for_message

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str

    class Config:
        from_attributes = True

class SessionOut(BaseModel):
    id: str
    title: str
    channel: str
    created_at: str
    updated_at: str
    message_count: int

@router.get("", response_model=List[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatSession).order_by(desc(ChatSession.updated_at)))
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        msg_count_res = await db.execute(
            select(ChatMessage.id).where(ChatMessage.session_id == s.id)
        )
        count = len(msg_count_res.scalars().all())
        out.append(SessionOut(
            id=s.id,
            title=s.title,
            channel=s.channel,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            message_count=count
        ))
    return out

@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
            "feedback": m.feedback,
            "meta": m.meta_json
        }
        for m in messages
    ]

@router.delete("/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a chat session AND permanently deletes all memories/facts Athina learned from it."""
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Explicitly cascade memory deletion to guarantee complete control
    await delete_memories_for_session(db, session_id)

    await db.delete(session)
    await db.commit()
    return {"status": "deleted", "id": session_id, "detail": "Session and all learned facts destroyed"}

@router.delete("/{session_id}/messages/{message_id}")
async def delete_single_message(session_id: str, message_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes an individual chat turn and permanently wipes any facts extracted from it."""
    msg = await db.get(ChatMessage, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # Wipe memories learned from this message
    await delete_memories_for_message(db, message_id)

    await db.delete(msg)
    await db.commit()
    return {"status": "deleted", "id": message_id, "detail": "Message and learned facts destroyed"}
