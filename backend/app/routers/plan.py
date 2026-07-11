"""Preparedness plan + travel advisory endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import (
    PlanRequest,
    PlanResponse,
    TravelAdvisory,
    TravelRequest,
)
from app.services.alerts import derive_alerts
from app.services.generation import generate_plan, generate_travel
from app.services.weather import get_weather

router = APIRouter(tags=["plan"])


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest) -> PlanResponse:
    weather = await get_weather(req.location)
    plan = await generate_plan(req, weather)
    alerts = derive_alerts(weather)
    return PlanResponse(plan=plan, weather=weather, alerts=alerts)


@router.post("/plan/travel", response_model=TravelAdvisory)
async def travel_advisory(req: TravelRequest) -> TravelAdvisory:
    origin_w = await get_weather(req.origin)
    dest_w = await get_weather(req.destination)
    return await generate_travel(req, origin_w, dest_w)
