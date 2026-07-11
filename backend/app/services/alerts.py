"""Deterministic alert engine.

Life-safety severity is computed by transparent, testable rules — NOT by the
LLM. The model may later phrase these alerts, but the trigger logic is code.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from app.models.schemas import Alert, Location, RiskLevel, WeatherSnapshot


def _mk_id(location: Location, hazard: str, day: str) -> str:
    raw = f"{location.lat:.2f}:{location.lon:.2f}:{hazard}:{day}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _alert(location: Location, hazard: str, severity: RiskLevel, title: str, msg: str,
           valid_hours: int) -> Alert:
    now = datetime.now(timezone.utc)
    return Alert(
        id=_mk_id(location, hazard, now.strftime("%Y-%m-%d")),
        severity=severity,
        title=title,
        message=msg,
        hazard=hazard,
        issued_at=now.isoformat(),
        valid_until=(now + timedelta(hours=valid_hours)).isoformat(),
    )


def derive_alerts(weather: WeatherSnapshot) -> list[Alert]:
    """Map forecast signals to alerts using IMD-style thresholds."""
    loc = weather.location
    alerts: list[Alert] = []

    # Rainfall (use max of today's observed precip and forecast sum)
    today_precip = weather.daily[0].precip_mm if weather.daily else weather.precip_mm
    peak_precip = max(today_precip, weather.precip_mm)
    if peak_precip >= 204.4:
        alerts.append(_alert(loc, "flooding", RiskLevel.severe,
                             "Extremely heavy rain — flooding likely",
                             "Rainfall above 204mm expected. Avoid all travel; move valuables and "
                             "people to higher floors. Do not enter flooded roads.", 24))
    elif peak_precip >= 115.6:
        alerts.append(_alert(loc, "flooding", RiskLevel.high,
                             "Very heavy rain warning",
                             "115-204mm rain expected. Waterlogging and localised flooding likely. "
                             "Postpone non-essential travel and keep a go-bag ready.", 24))
    elif peak_precip >= 64.5:
        alerts.append(_alert(loc, "heavy_rain", RiskLevel.moderate,
                             "Heavy rain expected",
                             "64-115mm rain expected. Expect waterlogging in low-lying areas; "
                             "plan your commute and carry rain protection.", 18))

    # Wind
    peak_wind = max((d.wind_max_kmh for d in weather.daily[:1]), default=weather.wind_kmh)
    peak_wind = max(peak_wind, weather.wind_kmh)
    if peak_wind >= 62:
        alerts.append(_alert(loc, "wind", RiskLevel.high,
                             "Gale-force winds",
                             "Winds of 62+ km/h expected. Secure loose objects, stay away from "
                             "trees, hoardings and weak structures.", 12))

    # Lightning proxy: high rain probability + rain implies convective storms
    prob = weather.daily[0].precip_prob if weather.daily else 0
    if prob >= 70 and peak_precip >= 20:
        alerts.append(_alert(loc, "lightning", RiskLevel.moderate,
                             "Thunderstorm & lightning risk",
                             "Thunderstorms likely. When thunder roars, go indoors; avoid open "
                             "fields, tall isolated trees and water bodies.", 12))

    # Concurrent heat
    if weather.temp_c >= 40:
        alerts.append(_alert(loc, "heat", RiskLevel.moderate,
                             "High heat before the rain",
                             "Temperatures at/above 40°C. Stay hydrated and avoid midday sun until "
                             "the rain arrives.", 12))

    return alerts


def top_risk(alerts: list[Alert]) -> RiskLevel:
    order = {RiskLevel.low: 0, RiskLevel.moderate: 1, RiskLevel.high: 2, RiskLevel.severe: 3}
    if not alerts:
        return RiskLevel.low
    return max(alerts, key=lambda a: order[a.severity]).severity
