from backend.app.config import settings
from backend.app.personality.state import PersonalityState
from backend.app.personality.prompt import build_system_prompt
import hashlib

def key_id(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]

def test_personality_state():
    state = PersonalityState.calculate_current_state()
    print(f"Calculated state: Mood='{state.mood}', Location='{state.location}', Energy={state.energy}")
    assert state.mood
    assert state.location
    assert 0.0 <= state.energy <= 1.0

def test_prompt_generation():
    state = PersonalityState.calculate_current_state()
    prompt = build_system_prompt(state=state, facts=["Ratul loves machine learning and Android development."])
    print(f"Generated prompt length: {len(prompt)} chars")
    assert "Athina" in prompt
    assert "STRICTLY ENGLISH" in prompt
    assert "Ratul loves machine learning" in prompt

def test_key_hashing():
    k = "sample_test_key_12345"
    kid = key_id(k)
    print(f"Key hash for test: {kid}")
    assert len(kid) == 10

if __name__ == "__main__":
    print("--- Running Athina Core Logic Tests ---")
    test_personality_state()
    test_prompt_generation()
    test_key_hashing()
    print("--- All Athina Core Logic Tests Passed! ---")
