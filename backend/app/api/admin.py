import os
import json
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.db.session import get_db, async_session_factory
from backend.app.db.models import ChatSession, ChatMessage, MemoryFactRecord, AthinaNote, AthinaAlarm, ApiKeyState
from backend.app.personality.state import PersonalityState
from backend.app.personality.prompt import (
    build_system_prompt,
    get_identity_config,
    save_identity_config,
    generate_identity_system_prompt
)
from backend.app.memory.retrieval import retrieve_relevant_facts, get_embedding
from backend.app.llm.keypool import key_pool

router = APIRouter(prefix="/api/admin", tags=["admin"])

SESSION_RAG_ID = "session_system_knowledge_rag"

# Global in-memory overrides for live prompt editing without redeployment
custom_admin_config = {
    "custom_instructions": "",
    "mood_override": None,
    "location_override": None
}

class PromptUpdateRequest(BaseModel):
    custom_instructions: str
    mood_override: Optional[str] = None
    location_override: Optional[str] = None

class IdentityUpdateRequest(BaseModel):
    its_name: str
    my_name: str
    call_me: str
    persona: str
    physical_structure: Optional[str] = ""
    personality: str
    communication_style: str
    rules: str
    context: str

class RagKnowledgeCreateRequest(BaseModel):
    fact: str
    category: Optional[str] = "general"
    importance: Optional[float] = 0.8

class RagTestRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

def verify_admin(authorization: Optional[str] = Header(None)):
    """Verifies admin authorization token."""
    secret = settings.admin_secret.strip()
    if not secret or secret == "athina-dev-secret-change-in-prod":
        return True

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()
    if token != secret:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    return True

@router.get("/overview")
async def get_admin_overview(db: AsyncSession = Depends(get_db)):
    session_count = await db.scalar(select(func.count(ChatSession.id))) or 0
    message_count = await db.scalar(select(func.count(ChatMessage.id))) or 0
    fact_count = await db.scalar(select(func.count(MemoryFactRecord.id))) or 0
    note_count = await db.scalar(select(func.count(AthinaNote.id))) or 0
    alarm_count = await db.scalar(select(func.count(AthinaAlarm.id))) or 0

    state = PersonalityState.calculate_current_state()
    slots = key_pool.all_slots()

    result = await db.execute(select(ApiKeyState))
    key_states = {r.slot: {"failures": r.failures, "successes": r.successes, "last_error": r.last_error} for r in result.scalars().all()}

    slot_details = []
    for s in slots:
        st = key_states.get(s.id, {"failures": 0, "successes": 0, "last_error": None})
        slot_details.append({
            "id": s.id,
            "provider": s.provider,
            "model": s.model,
            "failures": st["failures"],
            "successes": st["successes"],
            "last_error": st["last_error"]
        })

    return {
        "stats": {
            "sessions": session_count,
            "messages": message_count,
            "learned_facts": fact_count,
            "notes": note_count,
            "alarms": alarm_count
        },
        "companion_state": {
            "mood": custom_admin_config["mood_override"] or state.mood,
            "location": custom_admin_config["location_override"] or state.location,
            "energy": state.energy,
            "relationship_warmth": state.relationship_warmth
        },
        "slots": slot_details,
        "custom_config": custom_admin_config
    }

# ------------------------------------------------------------------------------
# IDENTITY & STRUCTURED PERSONA ENDPOINTS
# ------------------------------------------------------------------------------
@router.get("/identity")
async def get_identity():
    cfg = get_identity_config()
    generated_prompt = generate_identity_system_prompt(cfg)
    return {
        "config": cfg,
        "generated_system_prompt": generated_prompt
    }

@router.post("/identity")
async def update_identity(req: IdentityUpdateRequest):
    data = req.dict()
    save_identity_config(data)
    generated_prompt = generate_identity_system_prompt(data)
    return {
        "status": "updated",
        "config": data,
        "generated_system_prompt": generated_prompt
    }

@router.post("/identity/reset")
async def reset_identity():
    from backend.app.personality.prompt import DEFAULT_IDENTITY_CONFIG
    save_identity_config(DEFAULT_IDENTITY_CONFIG)
    generated_prompt = generate_identity_system_prompt(DEFAULT_IDENTITY_CONFIG)
    return {
        "status": "reset",
        "config": DEFAULT_IDENTITY_CONFIG,
        "generated_system_prompt": generated_prompt
    }

# ------------------------------------------------------------------------------
# PROMPT PREVIEW & OVERRIDE
# ------------------------------------------------------------------------------
@router.get("/prompt")
async def get_current_prompt():
    state = PersonalityState.calculate_current_state()
    if custom_admin_config["mood_override"]:
        state.mood = custom_admin_config["mood_override"]
    if custom_admin_config["location_override"]:
        state.location = custom_admin_config["location_override"]

    full_prompt = build_system_prompt(state=state)
    if custom_admin_config["custom_instructions"]:
        full_prompt += f"\n\nAdditional Admin Custom Instructions:\n{custom_admin_config['custom_instructions']}"

    return {
        "full_system_prompt": full_prompt,
        "custom_instructions": custom_admin_config["custom_instructions"],
        "mood_override": custom_admin_config["mood_override"],
        "location_override": custom_admin_config["location_override"]
    }

@router.post("/prompt")
async def update_prompt_config(req: PromptUpdateRequest):
    custom_admin_config["custom_instructions"] = req.custom_instructions.strip()
    custom_admin_config["mood_override"] = req.mood_override.strip() if req.mood_override else None
    custom_admin_config["location_override"] = req.location_override.strip() if req.location_override else None

    return {
        "status": "updated",
        "custom_instructions": custom_admin_config["custom_instructions"],
        "mood_override": custom_admin_config["mood_override"],
        "location_override": custom_admin_config["location_override"]
    }

# ------------------------------------------------------------------------------
# RAG KNOWLEDGE BASE ENDPOINTS
# ------------------------------------------------------------------------------
@router.get("/rag")
async def get_rag_knowledge(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MemoryFactRecord).order_by(MemoryFactRecord.created_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "fact": r.fact,
            "category": r.category,
            "importance": r.importance,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "has_embedding": bool(r.embedding_json)
        }
        for r in records
    ]

@router.post("/rag")
async def add_rag_knowledge(req: RagKnowledgeCreateRequest, db: AsyncSession = Depends(get_db)):
    # Ensure system knowledge session exists
    session = await db.get(ChatSession, SESSION_RAG_ID)
    if not session:
        session = ChatSession(
            id=SESSION_RAG_ID,
            title="System Knowledge & RAG Base",
            channel="admin"
        )
        db.add(session)
        await db.commit()

    emb = await get_embedding(req.fact)
    fact_id = str(uuid.uuid4())
    record = MemoryFactRecord(
        id=fact_id,
        session_id=SESSION_RAG_ID,
        fact=req.fact.strip(),
        category=req.category.strip() if req.category else "general",
        importance=req.importance if req.importance is not None else 0.8,
        embedding_json=json.dumps(emb) if emb else None
    )
    db.add(record)
    await db.commit()

    return {
        "status": "created",
        "id": fact_id,
        "fact": req.fact,
        "has_embedding": bool(emb)
    }

class RagKnowledgeUpdateRequest(BaseModel):
    fact: str
    category: Optional[str] = None
    importance: Optional[float] = None

@router.put("/rag/{fact_id}")
async def update_rag_knowledge(fact_id: str, req: RagKnowledgeUpdateRequest, db: AsyncSession = Depends(get_db)):
    record = await db.get(MemoryFactRecord, fact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Knowledge record not found")
    record.fact = req.fact.strip()
    if req.category:
        record.category = req.category.strip()
    if req.importance is not None:
        record.importance = req.importance

    # Recompute embedding if fact text changed
    emb = await get_embedding(record.fact)
    record.embedding_json = json.dumps(emb) if emb else None
    await db.commit()

    return {
        "status": "updated",
        "id": fact_id,
        "fact": record.fact,
        "category": record.category,
        "has_embedding": bool(emb)
    }

@router.delete("/rag/{fact_id}")
async def delete_rag_knowledge(fact_id: str, db: AsyncSession = Depends(get_db)):
    record = await db.get(MemoryFactRecord, fact_id)
    if not record:
        raise HTTPException(status_code=404, detail="Knowledge record not found")
    await db.delete(record)
    await db.commit()
    return {"status": "deleted", "id": fact_id}

@router.post("/rag/test")
async def test_rag_retrieval(req: RagTestRequest, db: AsyncSession = Depends(get_db)):
    matched_facts = await retrieve_relevant_facts(db, req.query, top_k=req.top_k or 5)
    return {
        "query": req.query,
        "matched_count": len(matched_facts),
        "results": matched_facts
    }

@router.post("/keypool/reset")
async def reset_keypool_cooldowns(db: AsyncSession = Depends(get_db)):
    key_pool.clear_cooldowns()
    result = await db.execute(select(ApiKeyState))
    for r in result.scalars().all():
        r.cooldown_until = None
        r.failures = 0
        r.last_error = None
    await db.commit()
    return {"status": "cooldowns_cleared"}
