import json
import math
import os
import re
from collections import Counter
from typing import Dict, Any, Tuple
from backend.app.personality.state import PersonalityState

MODEL_PATH = "/home/ratul/Athena/ml/exports/classifier_model.json"

_loaded_model = None

def load_classifier_model() -> Optional[Dict[str, Any]]:
    global _loaded_model
    if _loaded_model is not None:
        return _loaded_model

    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "r", encoding="utf-8") as f:
                _loaded_model = json.load(f)
                return _loaded_model
        except Exception:
            pass
    return None

def tokenize(text: str):
    tokens = re.findall(r"\b[a-z0-9']+\b", text.lower())
    unigrams = tokens
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return unigrams + bigrams

def classify_intent_and_emotion(text: str) -> Tuple[str, float]:
    """Classifies user message into intent/emotion class with confidence score."""
    model = load_classifier_model()
    if not model:
        return "chit_chat", 0.5

    tokens = tokenize(text)
    if not tokens:
        return "chit_chat", 0.5

    tf = Counter(tokens)
    vocab = model["vocabulary"]
    idf = model["idf"]

    vec = {}
    norm_sq = 0.0
    for t, count in tf.items():
        if t in vocab:
            val = count * idf[t]
            vec[t] = val
            norm_sq += val * val

    norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
    norm_vec = {t: val / norm for t, val in vec.items()}

    scores = {}
    for label, weights in model["class_weights"].items():
        dot = sum(norm_vec[t] * weights[t] for t in norm_vec if t in weights)
        scores[label] = dot

    best_label = max(scores, key=scores.get)
    best_score = scores[best_label]
    return best_label, best_score

def compute_style_vector(
    user_text: str,
    state: PersonalityState
) -> Tuple[str, Dict[str, Any]]:
    """
    Computes an adaptive Style Vector based on user emotion, time of day, and state.
    Returns: (tone_guidance_prompt_string, style_vector_dict)
    """
    predicted_class, confidence = classify_intent_and_emotion(user_text)

    # Base style initialized from companion state
    warmth = state.relationship_warmth
    humor = 0.5
    reply_length = "balanced"
    tone_guidance = "Be warm, attentive, and genuinely engaging."

    if predicted_class == "sad":
        warmth = 1.0
        humor = 0.1
        reply_length = "gentle"
        tone_guidance = (
            "Ratul is having a hard time or feeling down. Be exceptionally caring, gentle, "
            "validating, and emotionally supportive. Do not give shallow advice; just be there with him warmly."
        )
    elif predicted_class == "happy":
        warmth = 0.95
        humor = 0.8
        reply_length = "expressive"
        tone_guidance = (
            "Ratul is joyful or celebrating! Match his excitement enthusiastically, share his happiness, "
            "and celebrate this moment together!"
        )
    elif predicted_class == "curious":
        warmth = 0.85
        humor = 0.3
        reply_length = "articulate"
        tone_guidance = (
            "Ratul is asking an intellectual or technical question. Be sharp, clear, articulate, and insightful "
            "while maintaining your companion charm."
        )
    elif predicted_class == "playful":
        warmth = 0.9
        humor = 0.95
        reply_length = "playful"
        tone_guidance = (
            "Ratul is in a playful or joking mood. Be witty, playful, and affectionately teasing in your response."
        )
    elif predicted_class == "asks_image":
        tone_guidance = (
            "Ratul is asking for a picture or selfie of you. Express genuine excitement about sharing a photo "
            "and let him know what you're wearing right now!"
        )
    elif predicted_class == "asks_note":
        tone_guidance = (
            "Ratul wants to save a note. Confirm clearly and smoothly that you have recorded his thoughts."
        )
    elif predicted_class == "asks_alarm":
        tone_guidance = (
            "Ratul wants to set a timed alarm or reminder. Confirm the exact time warmly and wish him well."
        )

    style_vector = {
        "predicted_class": predicted_class,
        "confidence": round(confidence, 3),
        "warmth": warmth,
        "humor": humor,
        "reply_length": reply_length
    }

    return tone_guidance, style_vector
