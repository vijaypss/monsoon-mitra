"""Deterministic fallbacks used when the LLM is disabled or errors.

Guarantees the product works end-to-end with zero AI budget (English only).
Grounded in the same knowledge base so guidance stays safe.
"""
from __future__ import annotations

from app.models.schemas import (
    ChecklistItem,
    Household,
    Phase,
    PreparednessPlan,
    RiskLevel,
    TravelAdvisory,
    WeatherSnapshot,
)


def _risk_from_score(score: int) -> RiskLevel:
    if score >= 75:
        return RiskLevel.severe
    if score >= 50:
        return RiskLevel.high
    if score >= 25:
        return RiskLevel.moderate
    return RiskLevel.low


def fallback_plan(weather: WeatherSnapshot, household: Household, language: str) -> PreparednessPlan:
    risk = _risk_from_score(weather.monsoon_hazard_score)
    low_floor = household.floor <= 0 or household.dwelling.value in {"slum_kutcha", "coastal"}
    before = [
        "Charge phones and power banks; keep a torch with spare batteries ready.",
        "Store 3 litres of safe drinking water per person for 3 days.",
        "Pack a waterproof pouch with ID, insurance and cash.",
        "Clear drains and balconies of blockages so water can flow away.",
    ]
    if household.medical_needs:
        before.append("Keep a 7-day supply of medicines and a note of dosages.")
    if low_floor:
        before.append("Identify the nearest higher ground or relief shelter now.")
    during = [
        "Switch off mains electricity if water enters the home.",
        "Do not walk or drive through moving floodwater.",
        "Stay indoors during thunder; avoid open areas and isolated trees.",
        "Keep listening to official IMD/NDMA updates on radio or phone.",
    ]
    if household.seniors or household.children:
        during.append("Keep elderly and children warm, dry and hydrated.")
    after = [
        "Wear gloves and boots during cleanup; disinfect surfaces.",
        "Discard food and water touched by floodwater.",
        "Watch for snakes and pests displaced by water.",
        "Report damaged power lines to authorities.",
    ]
    go_bag = [
        "Drinking water and dry non-perishable food",
        "Torch, spare batteries and power bank",
        "First-aid kit and essential medicines",
        "Waterproof pouch with ID/insurance copies",
        "Cash, whistle and phone charger",
    ]
    summary = (
        f"Monsoon hazard is {risk.value} (score {weather.monsoon_hazard_score}/100). "
        "Follow the steps below before, during and after the rain."
    )
    return PreparednessPlan(
        risk_level=risk, summary=summary, before=before, during=during, after=after,
        go_bag=go_bag, language=language, generated_by="template",
    )


def fallback_checklist(weather: WeatherSnapshot, household: Household, phase: Phase,
                       language: str) -> list[ChecklistItem]:
    plan = fallback_plan(weather, household, language)
    src = {Phase.before: plan.before, Phase.during: plan.during, Phase.after: plan.after}[phase]
    risk = _risk_from_score(weather.monsoon_hazard_score)
    return [ChecklistItem(task=t, priority=risk) for t in src]


def fallback_travel(origin_w: WeatherSnapshot, dest_w: WeatherSnapshot,
                    language: str) -> TravelAdvisory:
    score = max(origin_w.monsoon_hazard_score, dest_w.monsoon_hazard_score)
    risk = _risk_from_score(score)
    if score >= 65:
        rec, summary = "postpone", "High rainfall/flood risk on this route. Postpone if you can."
    elif score >= 35:
        rec, summary = "caution", "Moderate risk. Travel only if necessary and stay alert."
    else:
        rec, summary = "go", "Conditions look manageable, but keep checking updates."
    tips = [
        "Avoid waterlogged underpasses and flooded roads.",
        "Keep the fuel tank full and share your route with someone.",
        "Check IMD and local traffic advisories before leaving.",
    ]
    return TravelAdvisory(recommendation=rec, risk_level=risk, summary=summary, tips=tips,
                          language=language, generated_by="template")


def fallback_chat_reply(weather: WeatherSnapshot | None) -> str:
    base = ("Here is general monsoon safety guidance: keep an emergency go-bag ready, store "
            "safe drinking water, avoid moving floodwater, switch off mains power if water "
            "enters your home, and go indoors during thunder. For official warnings check IMD "
            "and NDMA, and call 112 in an emergency.")
    if weather and weather.monsoon_hazard_score >= 50:
        base = ("Conditions look risky right now. " + base)
    return base
