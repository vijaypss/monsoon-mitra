"""Multilingual assistant endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.generation import generate_chat
from app.services.weather import get_weather

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    weather = await get_weather(req.location) if req.location else None
    return await generate_chat(req, weather)
