"""Weather service — fetches live + 7-day forecast from Open-Meteo (free, keyless)
and derives a 0-100 monsoon hazard score. Cached to limit upstream calls."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.core.cache import TTLCache
from app.core.logging import get_logger
from app.models.schemas import DailyForecast, Location, WeatherSnapshot

log = get_logger(__name__)
_settings = get_settings()
_cache = TTLCache(ttl_seconds=_settings.cache_ttl_seconds)

_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"


def _hazard_score(precip_mm: float, wind_kmh: float, precip_prob: int, temp_c: float) -> int:
    """Deterministic monsoon hazard heuristic (rainfall-dominant).
    IMD-style rainfall bands: 64.5-115.5mm heavy, 115.6-204.4 very heavy, >204.4 extreme."""
    score = 0.0
    score += min(precip_mm / 204.4, 1.0) * 60          # rainfall is the main driver
    score += min(wind_kmh / 62.0, 1.0) * 20            # >=62 km/h ~ gale
    score += (precip_prob / 100.0) * 10
    if temp_c >= 40:                                    # concurrent heat stress
        score += 10
    return int(max(0, min(100, round(score))))


async def get_weather(location: Location) -> WeatherSnapshot:
    key = f"wx:{location.lat:.3f}:{location.lon:.3f}"
    cached = _cache.get(key)
    if cached:
        return cached

    params = {
        "latitude": location.lat,
        "longitude": location.lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
        "precipitation,wind_speed_10m",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,"
        "temperature_2m_min,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_OPEN_METEO, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001 - upstream must never crash the request
        # Network error, bad payload, proxy/transport issue: degrade gracefully.
        log.warning("weather_upstream_failed", error=str(exc))
        return _fallback_snapshot(location)

    cur = data.get("current", {})
    daily_raw = data.get("daily", {})
    daily: list[DailyForecast] = []
    dates = daily_raw.get("time", [])
    for i, date in enumerate(dates):
        daily.append(
            DailyForecast(
                date=date,
                precip_mm=_num(daily_raw, "precipitation_sum", i),
                precip_prob=int(_num(daily_raw, "precipitation_probability_max", i)),
                temp_max=_num(daily_raw, "temperature_2m_max", i),
                temp_min=_num(daily_raw, "temperature_2m_min", i),
                wind_max_kmh=_num(daily_raw, "wind_speed_10m_max", i),
            )
        )

    temp_c = float(cur.get("temperature_2m", 0.0))
    precip = float(cur.get("precipitation", 0.0))
    wind = float(cur.get("wind_speed_10m", 0.0))
    prob = int(daily[0].precip_prob) if daily else 0

    snapshot = WeatherSnapshot(
        location=location,
        observed_at=cur.get("time", datetime.now(timezone.utc).isoformat()),
        temp_c=temp_c,
        feels_like_c=float(cur.get("apparent_temperature", temp_c)),
        precip_mm=precip,
        humidity=int(cur.get("relative_humidity_2m", 0)),
        wind_kmh=wind,
        monsoon_hazard_score=_hazard_score(
            max(precip, daily[0].precip_mm if daily else 0), wind, prob, temp_c
        ),
        daily=daily,
    )
    _cache.set(key, snapshot)
    return snapshot


def _num(block: dict, field: str, i: int) -> float:
    try:
        val = block.get(field, [])[i]
        return float(val) if val is not None else 0.0
    except (IndexError, TypeError, ValueError):
        return 0.0


def _fallback_snapshot(location: Location) -> WeatherSnapshot:
    """Degraded mode if the upstream is unreachable — keeps the API responsive."""
    return WeatherSnapshot(
        location=location,
        observed_at=datetime.now(timezone.utc).isoformat(),
        temp_c=28.0,
        feels_like_c=31.0,
        precip_mm=0.0,
        humidity=80,
        wind_kmh=12.0,
        monsoon_hazard_score=0,
        daily=[],
    )
