"""Health & metadata endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.models.schemas import SUPPORTED_LANGUAGES

router = APIRouter(tags=["meta"])
_settings = get_settings()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_enabled": _settings.llm_enabled,
        "provider": _settings.llm_provider if _settings.llm_enabled else "template",
    }


@router.get("/languages")
async def languages() -> dict:
    return {"languages": SUPPORTED_LANGUAGES}
