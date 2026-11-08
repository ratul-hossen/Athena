import os
import sys
import asyncio

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.voice.stt import transcribe_audio_groq

def test_stt_resilience():
    # Test that empty or invalid audio returns None without unhandled exception
    dummy_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(transcribe_audio_groq(dummy_wav))
    print(f"STT test result with dummy wav (no key/mock): {result}")
    assert result is None or isinstance(result, str)
    loop.close()

def test_clarion_asr_repair():
    from backend.app.voice.clarion import clarion_repair_asr, clarion_decision_policy
    # Test phonetic slips repair
    assert clarion_repair_asr("said a lot for seven am") == "set an alarm for seven am"
    assert clarion_repair_asr("take a peak at me") == "take a pic at me"
    assert clarion_repair_asr("take a node down please") == "save a note down please"
    assert clarion_repair_asr("hey anthea good morning") == "hey athina good morning"

    # Test Clarion ambiguity policy
    high_conf = clarion_decision_policy("asks_alarm", 0.95, "set an alarm for 7am")
    assert high_conf["decision"] == "EXECUTE"
    assert not high_conf["clarification_needed"]

    ambiguous = clarion_decision_policy("asks_alarm", 0.40, "seven o clock")
    assert ambiguous["decision"] == "CLARIFY"
    assert ambiguous["clarification_needed"]
    print("Clarion ASR repair and decision policy tests passed!")

def test_voice_route_syntax():
    # Verify voice.py and ws.py code files are syntactically valid
    import py_compile
    py_compile.compile("backend/app/api/voice.py", doraise=True)
    py_compile.compile("backend/app/api/ws.py", doraise=True)
    py_compile.compile("backend/app/voice/clarion.py", doraise=True)
    print("voice.py, ws.py, and clarion.py compiled successfully!")

if __name__ == "__main__":
    print("--- Running Athina Voice Pipeline Tests ---")
    test_stt_resilience()
    test_clarion_asr_repair()
    test_voice_route_syntax()
    print("--- All Athina Voice Pipeline Tests Passed! ---")
