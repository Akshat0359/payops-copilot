from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini (primary)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Anthropic (optional fallback)
    anthropic_api_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./payops.db"
    frontend_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def active_provider(self) -> str | None:
        """Return whichever AI provider is configured (Gemini preferred)."""
        if self.gemini_api_key:
            return "gemini"
        if self.anthropic_api_key:
            return "anthropic"
        return None

    @property
    def has_ai_key(self) -> bool:
        return self.active_provider is not None


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
