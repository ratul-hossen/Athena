from fastapi import APIRouter
from backend.app.personality.state import PersonalityState
from backend.app.llm.keypool import key_pool

router = APIRouter(prefix="/api/health", tags=["health"])

@router.get("")
async def health_check():
    state = PersonalityState.calculate_current_state()
    slots = key_pool.all_slots()

    return {
        "status": "online",
        "companion": "Athina",
        "current_state": state.to_dict(),
        "keypool_slots": len(slots),
        "providers": {
            "gemini": len([s for s in slots if s.provider == "gemini"]),
            "groq": len([s for s in slots if s.provider == "groq"])
        }
    }
