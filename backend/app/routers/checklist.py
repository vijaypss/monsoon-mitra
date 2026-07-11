"""Emergency checklist endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ChecklistRequest, ChecklistResponse
from app.services.generation import generate_checklist
from app.services.weather import get_weather

router = APIRouter(tags=["checklist"])


@router.post("/checklist", response_model=ChecklistResponse)
async def create_checklist(req: ChecklistRequest) -> ChecklistResponse:
    weather = await get_weather(req.location)
    return await generate_checklist(req, weather)
