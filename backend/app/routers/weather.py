"""Weather endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import Location, WeatherSnapshot
from app.services.weather import get_weather

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherSnapshot)
async def weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    name: str = Query("", max_length=120),
) -> WeatherSnapshot:
    return await get_weather(Location(lat=lat, lon=lon, name=name))
