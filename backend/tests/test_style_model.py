from backend.app.personality.state import PersonalityState
from backend.app.personality.style_model import classify_intent_and_emotion, compute_style_vector
from backend.app.personality.prompt import build_system_prompt

def test_intent_classification():
    label, conf = classify_intent_and_emotion("Take a cute selfie for me")
    print(f"Classification result: {label} (confidence: {conf:.2f})")
    assert label == "asks_image"

    label, conf = classify_intent_and_emotion("I feel completely drained and overwhelmed")
    print(f"Classification result: {label} (confidence: {conf:.2f})")
    assert label == "sad"

def test_style_vector_computation():
    state = PersonalityState.calculate_current_state()
    tone_guidance, style = compute_style_vector("I am having a terrible day", state)
    print(f"Computed style: {style}")
    print(f"Tone guidance: {tone_guidance}")
    assert style["predicted_class"] == "sad"
    assert style["warmth"] == 1.0
    assert "caring" in tone_guidance.lower()

def test_prompt_with_tone_guidance():
    state = PersonalityState.calculate_current_state()
    tone_guidance, style = compute_style_vector("We won the competition!", state)
    prompt = build_system_prompt(state=state, tone_guidance=tone_guidance)
    print(f"Generated prompt length with tone guidance: {len(prompt)} chars")
    assert "Conversational Tone & Nuance (ML Adapted)" in prompt
    assert "excited" in prompt.lower() or "joyful" in prompt.lower() or "celebrat" in prompt.lower()

if __name__ == "__main__":
    print("--- Running Style Model & ML Subsystem Tests ---")
    test_intent_classification()
    test_style_vector_computation()
    test_prompt_with_tone_guidance()
    print("--- All Style Model & ML Subsystem Tests Passed! ---")
