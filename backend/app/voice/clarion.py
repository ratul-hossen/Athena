"""
CLARION Integration for Athina Voice & Intent Pipeline.
Based on MD Ratul Hossen's research (PRG4206):
"Correction-Led, Ambiguity-Aware Recognition of Intent from Open Input"

Provides:
1. Fast ASR Phonetic & Acoustic Error Repair (maps noisy speech to clean intent text).
2. Stage 4 Calibrated Confidence Scaling (T* = 0.9248) & Ambiguity-Aware Clarification Policy.
"""

import re
from typing import Tuple, Optional, Dict, Any

# Optimized Temperature Scaling Constant from Clarion Step 6
TEMPERATURE_STAR = 0.9248
TAU_HIGH = 0.70
TAU_LOW = 0.30

# Fast phonetic and ASR confusion map learned from noisy speech recognition
ASR_REPAIR_PATTERNS = [
    # Athina name misrecognitions
    (r"\b(athena|anthea|adina|atina|arthena|atheena)\b", "athina"),
    
    # Alarm intent phonetic slips
    (r"\b(said a lot|set a lot|settle arm|set a arm|set an arm|said alarm)\b", "set an alarm"),
    (r"\b(wake me|weak me)\b", "wake me"),
    (r"\b(remind me at|remind me to)\b", "remind me to"),
    
    # Note intent phonetic slips
    (r"\b(save a no|take a node|take a note|save node|safe note|keep this no)\b", "save a note"),
    (r"\b(note down|no down|node down)\b", "note down"),
    
    # Image / Selfie request slips
    (r"\b(send a peak|send me a peak)\b", "send me a pic"),
    (r"\b(take a peak)\b", "take a pic"),
    (r"\b(show me a peak)\b", "show me a pic"),
    (r"\b(take a selphy|send a selphy|snap a selphy)\b", "take a selfie"),
    (r"\b(let me see u|let me c u)\b", "let me see you"),
    
    # Chit-chat & emotion disfluencies
    (r"\b(feeling really don|feeling down|feel dowm)\b", "feeling down"),
    (r"\b(good morning athina|morning athina)\b", "good morning athina"),
    (r"\b(good night athina|nite athina)\b", "good night athina"),
]

def clarion_repair_asr(raw_transcript: str) -> str:
    """
    Stage 2 Inspired: High-speed acoustic and phonetic error repair for ASR transcriptions.
    Corrects common misheard words and disfluencies without introducing hallucinated tokens.
    """
    if not raw_transcript or not raw_transcript.strip():
        return raw_transcript

    cleaned = raw_transcript.strip()
    
    # Apply acoustic confusion repair patterns
    for pattern, replacement in ASR_REPAIR_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
    # Clean redundant whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def clarion_calibrate_confidence(raw_confidence: float) -> float:
    """
    Stage 4: Calibrated Confidence Scaling via Temperature Scaling (T* = 0.9248).
    Calibrates raw Softmax/Classifier probabilities into true posterior likelihoods.
    """
    # Clip between 0.01 and 0.99 for numerical stability
    conf = max(0.01, min(0.99, raw_confidence))
    
    # Logit temperature scaling: z = log(p / (1-p)) / T*
    import math
    logit = math.log(conf / (1.0 - conf))
    calibrated_logit = logit / TEMPERATURE_STAR
    
    # Sigmoid to recover calibrated probability
    calibrated_prob = 1.0 / (1.0 + math.exp(-calibrated_logit))
    return round(calibrated_prob, 4)

def clarion_decision_policy(
    intent_class: str,
    raw_confidence: float,
    query: str
) -> Dict[str, Any]:
    """
    Stage 4 Clarification Dialogue Policy.
    - If Calibrated Confidence >= TAU_HIGH (0.70): Direct Execution.
    - If TAU_LOW (0.30) <= Calibrated Confidence < TAU_HIGH: Ambiguity Detected -> Selective Clarification.
    - If Calibrated Confidence < TAU_LOW: Low Confidence -> Reprompt gracefully.
    """
    calibrated_conf = clarion_calibrate_confidence(raw_confidence)
    
    if calibrated_conf >= TAU_HIGH:
        return {
            "decision": "EXECUTE",
            "intent": intent_class,
            "confidence": calibrated_conf,
            "clarification_needed": False,
            "clarification_prompt": None
        }
    elif calibrated_conf >= TAU_LOW:
        # Ambiguity: Formulate a targeted clarification question
        clarification_prompts = {
            "asks_alarm": f"I heard '{query}'. Did you want me to set an alarm or a reminder?",
            "asks_note": f"Did you want me to save that as a note in your memory?",
            "asks_image": f"Did you want me to send you a photo or selfie of myself?",
            "sad": "You sound a little worn out. Did you want to talk about how your day went?",
            "happy": "That sounds exciting! Are you celebrating some great news?",
        }
        prompt = clarification_prompts.get(
            intent_class,
            f"Just to make sure I understand correctly, did you want me to help with {intent_class.replace('_', ' ')}?"
        )
        return {
            "decision": "CLARIFY",
            "intent": intent_class,
            "confidence": calibrated_conf,
            "clarification_needed": True,
            "clarification_prompt": prompt
        }
    else:
        return {
            "decision": "REPROMPT",
            "intent": "uncertain",
            "confidence": calibrated_conf,
            "clarification_needed": True,
            "clarification_prompt": "I didn't quite catch that with the background noise. Could you say that again for me?"
        }
