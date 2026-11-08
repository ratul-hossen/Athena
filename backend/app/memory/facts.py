import json
import uuid
from typing import List, Dict, Any, Optional

try:
    from sqlalchemy import select, delete
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.app.db.models import MemoryFactRecord
    HAS_DB = True
except ImportError:
    HAS_DB = False
    AsyncSession = Any
    MemoryFactRecord = Any

from backend.app.memory.retrieval import get_embedding
from backend.app.llm.chat import chat_stream

FACT_EXTRACTION_PROMPT = """Analyze the conversation turn below between Ratul and his companion Athina.
Did Ratul state or reveal any durable, long-term personal facts about himself?
Examples of durable facts:
- His preferences, likes, dislikes
- His projects, programming languages, goals
- Personal habits, routines, family, or friends
Do NOT extract ephemeral/temporary things like "Ratul said hello" or "Ratul asked for the time".

Respond with a valid JSON array of objects, or an empty array [] if nothing durable was stated.
Schema:
[
  {
    "fact": "A clear, concise fact in English about Ratul",
    "category": "preference" | "project" | "habit" | "goal" | "person",
    "importance": 0.5 to 1.0
  }
]
Output ONLY the JSON array and nothing else.
"""

async def extract_and_save_facts(
    db: Any,
    session_id: str,
    message_id: str,
    user_text: str,
    assistant_text: str
) -> List[Any]:
    """Extracts durable facts about Ratul from a chat turn and saves them linked to session & message."""
    if not HAS_DB:
        return []

    # Don't run extraction for very short messages
    if len(user_text.strip()) < 15:
        return []

    messages = [
        {"role": "system", "content": FACT_EXTRACTION_PROMPT},
        {"role": "user", "content": f"User: {user_text}\nAssistant: {assistant_text}"}
    ]

    extracted_raw = ""
    try:
        async for event in chat_stream(messages, temperature=0.2, max_tokens=300):
            if event["type"] == "token":
                extracted_raw += event["text"]

        extracted_raw = extracted_raw.strip()
        # Clean json backticks if model wrapped it in ```json ... ```
        if extracted_raw.startswith("```"):
            extracted_raw = extracted_raw.split("\n", 1)[-1]
            if extracted_raw.endswith("```"):
                extracted_raw = extracted_raw.rsplit("```", 1)[0].strip()

        facts_data = json.loads(extracted_raw)
        if not isinstance(facts_data, list):
            return []

        saved_records: List[Any] = []
        for item in facts_data:
            fact_str = item.get("fact", "").strip()
            category = item.get("category", "general").strip()
            importance = float(item.get("importance", 0.7))

            if fact_str and len(fact_str) > 5:
                # Generate vector embedding for the fact
                vec = await get_embedding(fact_str)
                vec_json = json.dumps(vec) if vec else None

                record = MemoryFactRecord(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    message_id=message_id,
                    fact=fact_str,
                    category=category,
                    importance=importance,
                    embedding_json=vec_json
                )
                db.add(record)
                saved_records.append(record)

        if saved_records:
            await db.commit()
        return saved_records

    except Exception:
        return []

async def delete_memory_by_id(db: Any, memory_id: str) -> bool:
    """Deletes an individual memory fact."""
    if not HAS_DB:
        return False
    record = await db.get(MemoryFactRecord, memory_id)
    if record:
        await db.delete(record)
        await db.commit()
        return True
    return False

async def delete_memories_for_message(db: Any, message_id: str):
    """Deletes all facts extracted from a specific message."""
    if not HAS_DB:
        return
    await db.execute(delete(MemoryFactRecord).where(MemoryFactRecord.message_id == message_id))
    await db.commit()

async def delete_memories_for_session(db: Any, session_id: str):
    """Deletes all facts extracted from a deleted chat session."""
    if not HAS_DB:
        return
    await db.execute(delete(MemoryFactRecord).where(MemoryFactRecord.session_id == session_id))
    await db.commit()
