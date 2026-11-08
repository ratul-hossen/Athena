from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.db.models import MemoryFactRecord, AthinaNote, AthinaAlarm
from backend.app.memory.facts import delete_memory_by_id
from backend.app.memory.actions import upload_note_to_telegram

router = APIRouter(prefix="/api", tags=["memories_and_actions"])

class MemoryFactOut(BaseModel):
    id: str
    session_id: str
    message_id: Optional[str]
    fact: str
    category: str
    importance: float
    created_at: str

@router.get("/memories", response_model=List[MemoryFactOut])
async def list_memories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MemoryFactRecord).order_by(desc(MemoryFactRecord.created_at)))
    facts = result.scalars().all()
    return [
        MemoryFactOut(
            id=f.id,
            session_id=f.session_id,
            message_id=f.message_id,
            fact=f.fact,
            category=f.category,
            importance=f.importance,
            created_at=f.created_at.isoformat()
        )
        for f in facts
    ]

@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await delete_memory_by_id(db, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory fact not found")
    return {"status": "deleted", "id": memory_id}

@router.get("/notes")
async def list_notes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AthinaNote).order_by(desc(AthinaNote.created_at)))
    notes = result.scalars().all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "uploaded_to_telegram": n.uploaded_to_telegram,
            "telegram_msg_id": n.telegram_msg_id,
            "created_at": n.created_at.isoformat()
        }
        for n in notes
    ]

@router.post("/notes/{note_id}/upload_telegram")
async def forward_note_to_telegram(note_id: str, db: AsyncSession = Depends(get_db)):
    note = await db.get(AthinaNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    msg_id = await upload_note_to_telegram(note.title, note.content)
    if msg_id:
        note.uploaded_to_telegram = True
        note.telegram_msg_id = msg_id
        await db.commit()
        return {"status": "uploaded", "telegram_msg_id": msg_id}
    else:
        return {"status": "failed", "detail": "Telegram bot or owner channel not configured"}

@router.get("/alarms")
async def list_alarms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AthinaAlarm).order_by(desc(AthinaAlarm.created_at)))
    alarms = result.scalars().all()
    return [
        {
            "id": a.id,
            "label": a.label,
            "time_iso": a.time_iso,
            "repeat_days": a.repeat_days,
            "is_active": a.is_active,
            "created_at": a.created_at.isoformat()
        }
        for a in alarms
    ]
