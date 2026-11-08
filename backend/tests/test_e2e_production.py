import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.voice.clarion import clarion_repair_asr, clarion_decision_policy, clarion_calibrate_confidence
from backend.app.personality.state import PersonalityState
from backend.app.personality.style_model import compute_style_vector
from backend.app.images.reference import find_best_reference
from backend.app.memory.actions import parse_and_strip_actions

class TestProductionEndToEnd(unittest.TestCase):

    def test_clarion_full_pipeline(self):
        # 1. ASR Repair
        raw_noisy = "said a lot for seven am and send me a peak"
        repaired = clarion_repair_asr(raw_noisy)
        self.assertIn("set an alarm", repaired)
        self.assertIn("send me a pic", repaired)

        # 2. Calibrated Confidence Scaling
        raw_conf = 0.85
        calibrated = clarion_calibrate_confidence(raw_conf)
        self.assertGreaterEqual(calibrated, 0.70)

        # 3. Decision Policy
        decision = clarion_decision_policy("asks_alarm", 0.90, "set alarm")
        self.assertEqual(decision["decision"], "EXECUTE")

        ambiguous = clarion_decision_policy("asks_alarm", 0.45, "alarm maybe")
        self.assertEqual(ambiguous["decision"], "CLARIFY")
        self.assertTrue(ambiguous["clarification_needed"])

    def test_personality_and_style_vector(self):
        state = PersonalityState.calculate_current_state()
        self.assertIsNotNone(state.mood)
        self.assertIsNotNone(state.location)

        guidance, style = compute_style_vector("Can you send me a selfie?", state)
        self.assertEqual(style["predicted_class"], "asks_image")
        self.assertGreater(style["warmth"], 0.8)

    def test_nano_banana_reference_visual_dna(self):
        # Test reference search
        ref = find_best_reference("Take a close-up portrait selfie looking at camera")
        self.assertIsNotNone(ref)
        self.assertEqual(ref["group"], "group_a_face")
        self.assertIn("facial_features", ref)
        self.assertIn("body_anatomy", ref)
        if ref["image_path"]:
            self.assertTrue(os.path.exists(ref["image_path"]))

    def test_memory_action_parsing(self):
        # Note action parsing
        note_text = "Here's what you need. [[NOTE_ACTION: Architecture | Kotlin Coroutines Flow Architecture | true]] Have a look!"
        cleaned, actions = parse_and_strip_actions(note_text)
        self.assertIn("note", actions)
        self.assertEqual(actions["note"]["title"], "Architecture")
        self.assertTrue(actions["note"]["upload_telegram"])
        self.assertNotIn("[[NOTE_ACTION:", cleaned)

if __name__ == "__main__":
    unittest.main()
