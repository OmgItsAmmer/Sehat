from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root `.env` (make migrate runs from backend/, so CWD-relative ".env" misses it)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    green_api_instance: str = ""
    green_api_token: str = ""

    # Core (optional for Phase 1 smoke test)
    database_url: str = ""
    redis_url: str = ""

    # LLM (Google AI / Gemini API — see ListModels for ids)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"


settings = Settings()
