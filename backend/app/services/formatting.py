"""Turn typed models into compact text blocks for prompt grounding."""
from __future__ import annotations

from app.models.schemas import Household, WeatherSnapshot


def weather_block(w: WeatherSnapshot) -> str:
    lines = [
        f"Location: {w.location.name or f'{w.location.lat},{w.location.lon}'}",
        f"Now: {w.temp_c}°C (feels {w.feels_like_c}°C), precip {w.precip_mm}mm, "
        f"humidity {w.humidity}%, wind {w.wind_kmh}km/h",
        f"Monsoon hazard score: {w.monsoon_hazard_score}/100",
    ]
    for d in w.daily[:5]:
        lines.append(
            f"  {d.date}: rain {d.precip_mm}mm ({d.precip_prob}% chance), "
            f"{d.temp_min}-{d.temp_max}°C, wind up to {d.wind_max_kmh}km/h"
        )
    return "\n".join(lines)


def household_block(h: Household) -> str:
    parts = [
        f"{h.adults} adult(s), {h.children} child(ren), {h.seniors} senior(s)",
        f"Dwelling: {h.dwelling.value}, floor {h.floor}",
        f"Vehicle: {'yes' if h.has_vehicle else 'no'}, pets: {h.pets}",
    ]
    if h.medical_needs:
        parts.append("Medical needs: " + ", ".join(h.medical_needs))
    return "\n".join(parts)
