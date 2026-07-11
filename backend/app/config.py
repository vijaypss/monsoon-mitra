"""Application configuration (12-factor, env-driven)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Gen-AI
    groq_api_key: str = Field(default="")
    llm_provider: str = Field(default="groq")  # groq | template
    llm_model: str = Field(default="llama-3.3-70b-versatile")
    llm_timeout_seconds: float = Field(default=30.0)
    llm_max_tokens: int = Field(default=1536)

    # Security / networking
    allowed_origins: str = Field(default="http://localhost:5173")
    rate_limit: str = Field(default="30/minute")

    # Cache
    cache_ttl_seconds: int = Field(default=900)
    redis_url: str = Field(default="")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def llm_enabled(self) -> bool:
        """AI text generation is live only when a provider + key are present."""
        if self.llm_provider == "template":
            return False
        return bool(self.groq_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
