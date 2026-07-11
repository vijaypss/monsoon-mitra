"""Geocoding service — resolves free-text place names to coordinates using
Open-Meteo's free, keyless geocoding API. Cached to limit upstream calls."""
from __future__ import annotations

import httpx

from app.core.cache import TTLCache
from app.core.logging import get_logger
from app.models.schemas import GeoResult

log = get_logger(__name__)
_cache = TTLCache(ttl_seconds=86_400)  # place names are stable; cache a day
_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
# Free, keyless reverse geocoder (coords -> place name).
_REVERSE_URL = "https://api.bigdatacloud.net/data/reverse-geocode-client"


async def search_places(query: str, count: int = 6, language: str = "en") -> list[GeoResult]:
    query = query.strip()
    if len(query) < 2:
        return []
    key = f"geo:{language}:{count}:{query.lower()}"
    cached = _cache.get(key)
    if cached is not None:
        return cached

    params = {"name": query, "count": count, "language": language, "format": "json"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_GEOCODE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - upstream must never crash the request
        log.warning("geocode_upstream_failed", error=str(exc))
        return []

    results: list[GeoResult] = []
    for r in data.get("results", []) or []:
        if r.get("latitude") is None or r.get("longitude") is None:
            continue
        # Human-friendly label: "Kochi, Kerala, India"
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        label = ", ".join(p for p in parts if p)
        results.append(
            GeoResult(
                name=r.get("name", query),
                lat=float(r["latitude"]),
                lon=float(r["longitude"]),
                admin1=r.get("admin1"),
                country=r.get("country"),
                country_code=r.get("country_code"),
                label=label,
            )
        )
    _cache.set(key, results)
    return results


async def reverse_geocode(lat: float, lon: float, language: str = "en") -> GeoResult | None:
    """Resolve coordinates to a human place name (used after browser geolocation)."""
    key = f"rev:{language}:{lat:.3f}:{lon:.3f}"
    cached = _cache.get(key)
    if cached is not None:
        return cached or None

    params = {"latitude": lat, "longitude": lon, "localityLanguage": language}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_REVERSE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - upstream must never crash the request
        log.warning("reverse_geocode_failed", error=str(exc))
        return None

    # Prefer the most specific meaningful name available.
    name = data.get("city") or data.get("locality") or data.get("principalSubdivision") or ""
    admin1 = data.get("principalSubdivision") or None
    country = data.get("countryName") or None
    if not name and not country:
        _cache.set(key, [])  # cache the miss briefly (empty list => None)
        return None

    locality = data.get("locality")
    parts = [locality or name, admin1 if admin1 != (locality or name) else None, country]
    label = ", ".join(p for p in parts if p)
    result = GeoResult(
        name=name or (country or "Selected location"),
        lat=float(lat),
        lon=float(lon),
        admin1=admin1,
        country=country,
        country_code=data.get("countryCode"),
        label=label or f"{lat:.3f}, {lon:.3f}",
    )
    _cache.set(key, result)
    return result
