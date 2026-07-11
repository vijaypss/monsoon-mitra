"""Groq (free-tier) implementation of the LLM provider interface."""
from __future__ import annotations

from groq import AsyncGroq, GroqError

from app.core.logging import get_logger
from app.services.llm.base import LLMError, LLMProvider, LLMResult

log = get_logger(__name__)


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str, timeout: float = 30.0) -> None:
        self._client = AsyncGroq(api_key=api_key, timeout=timeout, max_retries=2)
        self._model = model

    async def complete(
        self,
        *,
        system: str,
        user: str,
        json_mode: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.4,
    ) -> LLMResult:
        kwargs: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = await self._client.chat.completions.create(**kwargs)
        except GroqError as exc:  # network, auth, rate limit, etc.
            log.warning("groq_error", error=str(exc))
            raise LLMError(str(exc)) from exc
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise LLMError("empty completion")
        return LLMResult(text=text, model=f"groq:{self._model}")
