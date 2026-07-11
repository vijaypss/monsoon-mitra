"""Alerts: point-in-time query + Server-Sent Events stream for real-time push."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Query, Request
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import Alert, Location
from app.services.alerts import derive_alerts
from app.services.weather import get_weather

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[Alert])
async def alerts(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    name: str = Query("", max_length=120),
) -> list[Alert]:
    weather = await get_weather(Location(lat=lat, lon=lon, name=name))
    return derive_alerts(weather)


@router.get("/alerts/stream")
async def alerts_stream(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    interval: int = Query(60, ge=15, le=600),
):
    """Streams alerts every `interval` seconds. The client keeps one connection
    open and receives fresh alerts as conditions change (weather is cached, so
    this is cheap). Emits only when the alert set changes."""

    async def event_generator():
        last_signature = None
        while True:
            if await request.is_disconnected():
                break
            weather = await get_weather(Location(lat=lat, lon=lon))
            current = derive_alerts(weather)
            signature = json.dumps([a.model_dump(mode="json") for a in current], sort_keys=True)
            if signature != last_signature:
                last_signature = signature
                yield {
                    "event": "alerts",
                    "data": json.dumps({
                        "alerts": [a.model_dump(mode="json") for a in current],
                        "hazard_score": weather.monsoon_hazard_score,
                    }),
                }
            await asyncio.sleep(interval)

    return EventSourceResponse(event_generator())
