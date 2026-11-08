import gzip
import os
from backend.app.telegram.api import is_telegram_configured
from backend.app.memory.actions import parse_and_strip_actions

def test_telegram_config_check():
    # Verify configuration detector
    cfg = is_telegram_configured()
    print(f"Telegram configured status: {cfg}")
    assert isinstance(cfg, bool)

def test_backup_compression():
    dummy_sql = b"CREATE TABLE test (id TEXT PRIMARY KEY); INSERT INTO test VALUES ('athina_test');"
    compressed = gzip.compress(dummy_sql)
    decompressed = gzip.decompress(compressed)
    print(f"Original size: {len(dummy_sql)} bytes, Compressed: {len(compressed)} bytes")
    assert decompressed == dummy_sql

def test_telegram_action_handling():
    text = (
        "Got it Ratul! I've noted down your meeting notes.\n\n"
        "[[NOTE_ACTION: Client Meeting Notes | Finalize Athina mobile release by Sunday | true]]"
    )
    clean, actions = parse_and_strip_actions(text)
    print(f"Telegram action parsed: {actions}")
    assert "note" in actions
    assert actions["note"]["upload_telegram"] is True
    assert "[[NOTE_ACTION" not in clean

if __name__ == "__main__":
    print("--- Running Telegram Module Tests ---")
    test_telegram_config_check()
    test_backup_compression()
    test_telegram_action_handling()
    print("--- All Telegram Module Tests Passed! ---")
