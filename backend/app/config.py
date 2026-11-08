import os
from typing import List

env_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.env"))

# Native simple .env parser if python-dotenv is not installed
def _load_env_file(filepath: str):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

try:
    from dotenv import load_dotenv
    if os.path.exists(env_backend_path):
        load_dotenv(env_backend_path)
    load_dotenv(".env")
except ImportError:
    _load_env_file(env_backend_path)
    _load_env_file(".env")

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=(env_backend_path, ".env"),
            env_file_encoding="utf-8",
            extra="ignore"
        )

        database_url: str = Field(default="sqlite+aiosqlite:///./athina.db", alias="DATABASE_URL")
        gemini_api_keys: str = Field(default="", alias="GEMINI_API_KEYS")
        gemini_models: str = Field(default="gemini-2.5-flash,gemini-1.5-flash", alias="GEMINI_MODELS")
        gemini_embedding_model: str = Field(default="gemini-embedding-001", alias="GEMINI_EMBEDDING_MODEL")

        groq_api_keys: str = Field(default="", alias="GROQ_API_KEYS")
        groq_models: str = Field(default="openai/gpt-oss-120b,openai/gpt-oss-20b,llama-3.1-8b-instant", alias="GROQ_MODELS")
        groq_stt_model: str = Field(default="whisper-large-v3", alias="GROQ_STT_MODEL")

        tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
        image_gen_model: str = Field(default="nano-banana-reference,imagen-3.0-generate-002", alias="IMAGE_GEN_MODEL")

        admin_secret: str = Field(default="athina-dev-secret-change-in-prod", alias="ADMIN_SECRET")
        admin_emails: str = Field(default="", alias="ADMIN_EMAILS")

        telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
        telegram_owner_id: str = Field(default="", alias="TELEGRAM_OWNER_ID")
        telegram_storage_channel_id: str = Field(default="", alias="TELEGRAM_STORAGE_CHANNEL_ID")

        image_daily_limit: int = Field(default=20, alias="IMAGE_DAILY_LIMIT")
        modal_token_id: str = Field(default="", alias="MODAL_TOKEN_ID")
        modal_token_secret: str = Field(default="", alias="MODAL_TOKEN_SECRET")

        @property
        def parsed_gemini_keys(self) -> List[str]:
            return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]

        @property
        def parsed_gemini_models(self) -> List[str]:
            return [m.strip() for m in self.gemini_models.split(",") if m.strip()]

        @property
        def parsed_groq_keys(self) -> List[str]:
            return [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]

        @property
        def parsed_groq_models(self) -> List[str]:
            return [m.strip() for m in self.groq_models.split(",") if m.strip()]

    settings = Settings()

except ImportError:
    # Standard library fallback when pydantic-settings is not installed yet
    class FallbackSettings:
        def __init__(self):
            self.database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./athina.db")
            self.gemini_api_keys = os.getenv("GEMINI_API_KEYS", "")
            self.gemini_models = os.getenv("GEMINI_MODELS", "gemini-2.5-flash,gemini-1.5-flash")
            self.gemini_embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
            self.groq_api_keys = os.getenv("GROQ_API_KEYS", "")
            self.groq_models = os.getenv("GROQ_MODELS", "openai/gpt-oss-120b,openai/gpt-oss-20b,llama-3.1-8b-instant")
            self.groq_stt_model = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")
            self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
            self.image_gen_model = os.getenv("IMAGE_GEN_MODEL", "nano-banana-reference,imagen-3.0-generate-002")
            self.admin_secret = os.getenv("ADMIN_SECRET", "athina-dev-secret-change-in-prod")
            self.admin_emails = os.getenv("ADMIN_EMAILS", "")
            self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            self.telegram_owner_id = os.getenv("TELEGRAM_OWNER_ID", "")
            self.telegram_storage_channel_id = os.getenv("TELEGRAM_STORAGE_CHANNEL_ID", "")
            self.image_daily_limit = int(os.getenv("IMAGE_DAILY_LIMIT", "20"))
            self.modal_token_id = os.getenv("MODAL_TOKEN_ID", "")
            self.modal_token_secret = os.getenv("MODAL_TOKEN_SECRET", "")

        @property
        def parsed_gemini_keys(self) -> List[str]:
            return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]

        @property
        def parsed_gemini_models(self) -> List[str]:
            return [m.strip() for m in self.gemini_models.split(",") if m.strip()]

        @property
        def parsed_groq_keys(self) -> List[str]:
            return [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]

        @property
        def parsed_groq_models(self) -> List[str]:
            return [m.strip() for m in self.groq_models.split(",") if m.strip()]

    settings = FallbackSettings()
