"""LLM provider abstraction.

Every call site depends only on `LLMProvider`. Swapping Groq for OpenAI,
Anthropic, or a self-hosted Ollama model is a one-file change in the factory.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    model: str


class LLMProvider(abc.ABC):
    """Minimal, provider-agnostic chat interface."""

    name: str = "base"

    @abc.abstractmethod
    async def complete(
        self,
        *,
        system: str,
        user: str,
        json_mode: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.4,
    ) -> LLMResult:
        """Return a single completion. Implementations must not raise on
        upstream errors that callers can recover from — instead raise
        `LLMError` so services can fall back to templates."""
        raise NotImplementedError


class LLMError(RuntimeError):
    """Raised when the provider cannot produce a completion."""
