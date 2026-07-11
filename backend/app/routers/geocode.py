"""Geocoding endpoint — turns a free-text place query into coordinate options."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import GeoResult
from app.services.geocoding import reverse_geocode, search_places

router = APIRouter(tags=["geocode"])


@router.get("/geocode", response_model=list[GeoResult])
async def geocode(
    q: str = Query(..., min_length=2, max_length=120, description="Place name to search"),
    count: int = Query(6, ge=1, le=10),
    language: str = Query("en", max_length=5),
) -> list[GeoResult]:
    return await search_places(q, count=count, language=language)


@router.get("/reverse-geocode", response_model=GeoResult | None)
async def reverse(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    language: str = Query("en", max_length=5),
) -> GeoResult | None:
    """Resolve coordinates from browser geolocation into a readable place name."""
    return await reverse_geocode(lat, lon, language=language)
