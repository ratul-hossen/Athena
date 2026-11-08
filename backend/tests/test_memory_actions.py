import re
from backend.app.memory.retrieval import extract_keywords
from backend.app.memory.actions import parse_and_strip_actions

def test_keyword_extraction():
    sample = "Ratul is building Athina with Kotlin, Jetpack Compose and FastAPI backend!"
    kw = extract_keywords(sample)
    print(f"Extracted keywords: {kw}")
    assert "ratul" in kw
    assert "building" in kw
    assert "athina" in kw
    assert "kotlin" in kw
    assert "is" not in kw  # Stopword removed
    assert "and" not in kw  # Stopword removed

def test_note_and_telegram_action_parsing():
    model_response = (
        "I've saved that idea for you, Ratul! It's going to be an awesome feature.\n\n"
        "[[NOTE_ACTION: Jetpack Compose Roadmap | Port Three.js eagle mark and add Room caching | true]]"
    )
    clean_text, actions = parse_and_strip_actions(model_response)
    print(f"Clean text: '{clean_text}'")
    print(f"Parsed actions: {actions}")

    assert "[[NOTE_ACTION" not in clean_text
    assert "note" in actions
    assert actions["note"]["title"] == "Jetpack Compose Roadmap"
    assert actions["note"]["upload_telegram"] is True

def test_alarm_action_parsing():
    model_response = (
        "Setting your alarm now, get some good rest tonight!\n\n"
        "[[ALARM_ACTION: Wake up for gym | 06:30 AM | Mon,Wed,Fri]]"
    )
    clean_text, actions = parse_and_strip_actions(model_response)
    print(f"Clean text: '{clean_text}'")
    print(f"Parsed actions: {actions}")

    assert "[[ALARM_ACTION" not in clean_text
    assert "alarm" in actions
    assert actions["alarm"]["label"] == "Wake up for gym"
    assert actions["alarm"]["time_iso"] == "06:30 AM"
    assert actions["alarm"]["repeat_days"] == "Mon,Wed,Fri"

if __name__ == "__main__":
    print("--- Running Memory & Actions Tests ---")
    test_keyword_extraction()
    test_note_and_telegram_action_parsing()
    test_alarm_action_parsing()
    print("--- All Memory & Actions Tests Passed! ---")
