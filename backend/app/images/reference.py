import os
import json
import random
from typing import Dict, Any, Optional

MANIFEST_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../imagegen/curated/dataset_manifest.json")
)
CURATED_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../imagegen/curated")
)

_cached_manifest = None

def load_manifest():
    global _cached_manifest
    if _cached_manifest is None and os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                _cached_manifest = json.load(f)
        except Exception:
            _cached_manifest = []
    return _cached_manifest or []

def find_best_reference(prompt: str) -> Dict[str, Any]:
    """Finds the most contextually relevant Athina reference photo and visual DNA."""
    manifest = load_manifest()
    if not manifest:
        return {
            "image_path": None,
            "group": "group_b_midbody",
            "prompt_dna": "RAW photo of athina_woman, amber hazel eyes, dark brown hair, slender waist, natural feminine curves, photorealistic"
        }

    p_lower = prompt.lower()

    # Determine desired framing
    if any(k in p_lower for k in ["close up", "face", "eyes", "lips", "smile", "portrait", "selfie"]):
        preferred_group = "group_a_face"
    elif any(k in p_lower for k in ["full body", "standing", "legs", "walk", "feet", "nature", "silhouette", "waterfall"]):
        preferred_group = "group_c_fullbody"
    else:
        preferred_group = "group_b_midbody"

    # Filter candidates by group
    candidates = [entry for entry in manifest if entry.get("group") == preferred_group]
    if not candidates:
        candidates = manifest

    # Keyword matching against setting / attire / tags
    matched = []
    keywords = [w for w in p_lower.split() if len(w) > 3]
    for c in candidates:
        score = 0
        text_corpus = (
            str(c.get("outfit_and_styling", {})) + " " +
            str(c.get("detailed_prompt", "")) + " " +
            " ".join(c.get("tags", []))
        ).lower()
        for kw in keywords:
            if kw in text_corpus:
                score += 1
        if score > 0:
            matched.append((score, c))

    if matched:
        matched.sort(key=lambda x: x[0], reverse=True)
        chosen = matched[0][1]
    else:
        chosen = random.choice(candidates)

    group = chosen.get("group", "group_b_midbody")
    fname = chosen.get("filename", "")
    full_path = os.path.join(CURATED_BASE, group, fname)

    return {
        "image_path": full_path if os.path.exists(full_path) else None,
        "filename": fname,
        "group": group,
        "reference_url": f"/static/references/{group}/{fname}" if fname else None,
        "prompt_dna": chosen.get("detailed_prompt", ""),
        "facial_features": chosen.get("facial_features", {}),
        "body_anatomy": chosen.get("body_anatomy", {})
    }
