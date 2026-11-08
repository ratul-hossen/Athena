import os
import sys
import asyncio
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.images.reference import find_best_reference, load_manifest
from backend.app.images.generator import generate_athina_image_nanobanana

class TestAthinaNanoBanana(unittest.TestCase):

    def test_manifest_loads(self):
        manifest = load_manifest()
        self.assertGreaterEqual(len(manifest), 500)
        first = manifest[0]
        self.assertIn("facial_features", first)
        self.assertIn("body_anatomy", first)
        self.assertIn("detailed_prompt", first)

    def test_find_best_reference_face(self):
        ref = find_best_reference("Athina please send me a close up selfie with sweet smile")
        self.assertEqual(ref["group"], "group_a_face")
        self.assertIsNotNone(ref["image_path"])

    def test_find_best_reference_body(self):
        ref = find_best_reference("Athina full body photo standing in nature waterfall")
        self.assertEqual(ref["group"], "group_c_fullbody")
        self.assertIsNotNone(ref["image_path"])

    def test_nanobanana_generator(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            generate_athina_image_nanobanana("Athina wearing yellow saree near bed")
        )
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["source"], "nanobanana")
        self.assertTrue(result["image_url"].startswith("/static/images/"))
        self.assertTrue(os.path.exists(result["local_path"]))
        loop.close()

if __name__ == "__main__":
    print("--- Running Athina Nano Banana Image Pipeline Tests ---")
    unittest.main()
