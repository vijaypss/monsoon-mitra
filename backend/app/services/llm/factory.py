"""Selects the active LLM provider from settings. Returns None in template mode."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.core.logging import get_logger
from app.services.llm.base import LLMProvider

log = get_logger(__name__)


@lru_cache
def get_provider() -> LLMProvider | None:
    s = get_settings()
    if not s.llm_enabled:
        log.info("llm_disabled", reason="no key or template mode; using deterministic fallback")
        return None
    if s.llm_provider == "groq":
        from app.services.llm.groq_provider import GroqProvider

        return GroqProvider(api_key=s.groq_api_key, model=s.llm_model, timeout=s.llm_timeout_seconds)
    # Extend here: "openai", "anthropic", "ollama" ...
    log.warning("unknown_provider", provider=s.llm_provider)
    return None
