from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any

DHAKA_TZ = ZoneInfo("Asia/Dhaka")

class PersonalityState:
    def __init__(
        self,
        mood: str = "happy",
        energy: float = 0.9,
        location: str = "in her cozy study room",
        relationship_warmth: float = 1.0
    ):
        self.mood = mood
        self.energy = energy
        self.location = location
        self.relationship_warmth = relationship_warmth

    @classmethod
    def calculate_current_state(cls, now_dt: datetime = None) -> "PersonalityState":
        if now_dt is None:
            now_dt = datetime.now(DHAKA_TZ)
        else:
            now_dt = now_dt.astimezone(DHAKA_TZ)

        hour = now_dt.hour

        # Determine routine and location based on time of day
        if 0 <= hour < 6:
            location = "resting comfortably in bed, lights dimmed"
            mood = "sleepy and calm"
            energy = 0.4
        elif 6 <= hour < 9:
            location = "sitting on the balcony with warm morning tea"
            mood = "fresh and cheerful"
            energy = 0.8
        elif 9 <= hour < 14:
            location = "at her wooden desk with notebooks and laptop"
            mood = "focused, creative and lively"
            energy = 0.95
        elif 14 <= hour < 18:
            location = "curled up in the reading chair by the window"
            mood = "relaxed, playful and thoughtful"
            energy = 0.85
        elif 18 <= hour < 22:
            location = "in the living room listening to acoustic music"
            mood = "warm, chatty and affectionate"
            energy = 0.9
        else:
            location = "unwinding in a cozy hoodie, soft ambient lighting"
            mood = "gentle, cozy and reflective"
            energy = 0.6

        return cls(mood=mood, energy=energy, location=location, relationship_warmth=1.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mood": self.mood,
            "energy": self.energy,
            "location": self.location,
            "relationship_warmth": self.relationship_warmth
        }
