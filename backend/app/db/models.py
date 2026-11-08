import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class ApiKeyState(Base):
    """Tracks LLM key/model health, cooldowns, and success/failure metrics."""
    __tablename__ = "api_key_state"

    slot: Mapped[str] = mapped_column(String(128), primary_key=True)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    successes: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class ChatSession(Base):
    """A conversation session (Android client or Telegram)."""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(256), default="Chat with Athina")
    channel: Mapped[str] = mapped_column(String(32), default="android")  # android | telegram | web
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    facts: Mapped[List["MemoryFactRecord"]] = relationship(
        "MemoryFactRecord",
        back_populates="session",
        cascade="all, delete-orphan"
    )

class ChatMessage(Base):
    """A single turn in the conversation."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system
    content: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string: provider, model, etc.
    feedback: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 1 (up) or -1 (down)
    feedback_notes: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    extracted_facts: Mapped[List["MemoryFactRecord"]] = relationship(
        "MemoryFactRecord",
        back_populates="source_message",
        cascade="all, delete-orphan"
    )

class MemoryFactRecord(Base):
    """
    Long-term memories & learned facts about Ratul.
    Strictly linked to source session and message so deleting a chat cascades
    and permanently deletes what Athina learned from that chat!
    """
    __tablename__ = "memory_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    fact: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="general")  # preference | project | habit | person | goal
    importance: Mapped[float] = mapped_column(Float, default=0.7)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON float array
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="facts")
    source_message: Mapped[Optional["ChatMessage"]] = relationship("ChatMessage", back_populates="extracted_facts")

class MemoryEpisodeRecord(Base):
    """Nightly summaries of conversations and memorable days."""
    __tablename__ = "memory_episodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    summary: Mapped[str] = mapped_column(Text)
    date_str: Mapped[str] = mapped_column(String(32), index=True) # YYYY-MM-DD
    mood_summary: Mapped[str] = mapped_column(String(64), default="cheerful")
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class PersonalityStateRecord(Base):
    """Persistent state machine for Athina: mood, energy, routine, etc."""
    __tablename__ = "personality_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mood: Mapped[str] = mapped_column(String(64), default="happy")
    energy: Mapped[float] = mapped_column(Float, default=0.9)
    location: Mapped[str] = mapped_column(String(128), default="in her cozy study room")
    relationship_warmth: Mapped[float] = mapped_column(Float, default=1.0)
    last_interaction: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class ImageJobRecord(Base):
    """Asynchronous image generation job."""
    __tablename__ = "image_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued") # queued | running | done | failed
    tier: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # modal | cpu | nanobanana
    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class AthinaNote(Base):
    """Saved personal notes created by Athina for Ratul."""
    __tablename__ = "athina_notes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(256))
    content: Mapped[Text] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    uploaded_to_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_msg_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

class AthinaAlarm(Base):
    """Alarms and timed reminders managed by Athina."""
    __tablename__ = "athina_alarms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    label: Mapped[str] = mapped_column(String(256))
    time_iso: Mapped[str] = mapped_column(String(64)) # ISO format string
    repeat_days: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # e.g. "Mon,Tue,Wed"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
