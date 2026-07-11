"""Generation service — orchestrates grounding, the LLM call, structured parsing,
and deterministic fallback for every AI feature."""
from __future__ import annotations

import json

from app.core.cache import TTLCache
from app.core.logging import get_logger
from app.config import get_settings
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChecklistItem,
    ChecklistRequest,
    ChecklistResponse,
    PlanRequest,
    PreparednessPlan,
    RiskLevel,
    TravelAdvisory,
    TravelRequest,
    WeatherSnapshot,
)
from app.prompts import templates as P
from app.services import knowledge_base as kb
from app.services import templates_fallback as fb
from app.services.formatting import household_block, weather_block
from app.services.llm.base import LLMError
from app.services.llm.factory import get_provider

log = get_logger(__name__)
_settings = get_settings()
_gen_cache = TTLCache(ttl_seconds=_settings.cache_ttl_seconds)


def _safe_json(text: str) -> dict | None:
    """Parse a JSON object even if the model wraps it in prose/code fences."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _coerce_risk(value: str) -> RiskLevel:
    try:
        return RiskLevel(str(value).lower())
    except ValueError:
        return RiskLevel.moderate


def _str_list(value, cap: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()][:cap]


# ── Preparedness plan ──────────────────────────────────────────────────
async def generate_plan(req: PlanRequest, weather: WeatherSnapshot) -> PreparednessPlan:
    provider = get_provider()
    if provider is None:
        return fb.fallback_plan(weather, req.household, req.language)

    facts = kb.retrieve(
        f"{req.household.dwelling.value} floor {req.household.floor} "
        + " ".join(req.household.medical_needs) + " flood prepare go-bag", k=5
    )
    system = P.plan_system(req.language)
    user = P.plan_user(
        weather_block=weather_block(weather),
        household_block=household_block(req.household),
        safety_block=kb.as_context(facts),
    )
    try:
        result = await provider.complete(
            system=system, user=user, json_mode=True,
            max_tokens=_settings.llm_max_tokens, temperature=0.4,
        )
        data = _safe_json(result.text)
        if not data:
            raise LLMError("unparseable plan JSON")
        return PreparednessPlan(
            risk_level=_coerce_risk(data.get("risk_level", "moderate")),
            summary=str(data.get("summary", "")).strip()[:400] or "Monsoon preparedness plan.",
            before=_str_list(data.get("before")) or fb.fallback_plan(weather, req.household, req.language).before,
            during=_str_list(data.get("during")) or fb.fallback_plan(weather, req.household, req.language).during,
            after=_str_list(data.get("after")) or fb.fallback_plan(weather, req.household, req.language).after,
            go_bag=_str_list(data.get("go_bag")) or fb.fallback_plan(weather, req.household, req.language).go_bag,
            language=req.language,
            generated_by=result.model,
        )
    except LLMError as exc:
        log.warning("plan_fallback", error=str(exc))
        return fb.fallback_plan(weather, req.household, req.language)


# ── Checklist ──────────────────────────────────────────────────────────
async def generate_checklist(req: ChecklistRequest, weather: WeatherSnapshot) -> ChecklistResponse:
    provider = get_provider()
    if provider is None:
        items = fb.fallback_checklist(weather, req.household, req.phase, req.language)
        return ChecklistResponse(phase=req.phase, items=items, language=req.language,
                                 generated_by="template")
    facts = kb.retrieve(f"{req.phase.value} monsoon flood {req.household.dwelling.value}", k=4)
    try:
        result = await provider.complete(
            system=P.checklist_system(req.language, req.phase.value),
            user=P.checklist_user(
                weather_block=weather_block(weather),
                household_block=household_block(req.household),
                safety_block=kb.as_context(facts),
            ),
            json_mode=True, max_tokens=900, temperature=0.4,
        )
        data = _safe_json(result.text) or {}
        raw_items = data.get("items", [])
        items: list[ChecklistItem] = []
        for it in raw_items[:12]:
            if isinstance(it, dict) and it.get("task"):
                items.append(ChecklistItem(task=str(it["task"]).strip()[:200],
                                           priority=_coerce_risk(it.get("priority", "moderate"))))
        if not items:
            raise LLMError("empty checklist")
        return ChecklistResponse(phase=req.phase, items=items, language=req.language,
                                 generated_by=result.model)
    except LLMError as exc:
        log.warning("checklist_fallback", error=str(exc))
        items = fb.fallback_checklist(weather, req.household, req.phase, req.language)
        return ChecklistResponse(phase=req.phase, items=items, language=req.language,
                                 generated_by="template")


# ── Travel advisory ────────────────────────────────────────────────────
async def generate_travel(req: TravelRequest, origin_w: WeatherSnapshot,
                          dest_w: WeatherSnapshot) -> TravelAdvisory:
    provider = get_provider()
    if provider is None:
        return fb.fallback_travel(origin_w, dest_w, req.language)
    facts = kb.retrieve("travel car road waterlogging flood drive advisory", k=3)
    trip = (f"From {req.origin.name or 'origin'} to {req.destination.name or 'destination'} "
            f"by {req.mode}, departing in {req.depart_in_hours}h.")
    try:
        result = await provider.complete(
            system=P.travel_system(req.language),
            user=P.travel_user(origin_weather=weather_block(origin_w),
                               dest_weather=weather_block(dest_w),
                               trip_block=trip, safety_block=kb.as_context(facts)),
            json_mode=True, max_tokens=700, temperature=0.4,
        )
        data = _safe_json(result.text)
        if not data:
            raise LLMError("unparseable travel JSON")
        rec = str(data.get("recommendation", "caution")).lower()
        rec = rec if rec in {"go", "caution", "postpone"} else "caution"
        return TravelAdvisory(
            recommendation=rec,
            risk_level=_coerce_risk(data.get("risk_level", "moderate")),
            summary=str(data.get("summary", "")).strip()[:300] or "Travel advisory.",
            tips=_str_list(data.get("tips"), cap=6) or fb.fallback_travel(origin_w, dest_w, req.language).tips,
            language=req.language, generated_by=result.model,
        )
    except LLMError as exc:
        log.warning("travel_fallback", error=str(exc))
        return fb.fallback_travel(origin_w, dest_w, req.language)


# ── Chat ───────────────────────────────────────────────────────────────
async def generate_chat(req: ChatRequest, weather: WeatherSnapshot | None) -> ChatResponse:
    provider = get_provider()
    facts = kb.retrieve(req.message, k=4)
    grounded = [e["id"] for e in facts] + (["live_weather"] if weather else [])
    if provider is None:
        return ChatResponse(reply=fb.fallback_chat_reply(weather), language=req.language,
                            grounded_on=grounded, generated_by="template")
    wx = weather_block(weather) if weather else "No location provided; give general guidance."
    try:
        result = await provider.complete(
            system=P.chat_system(req.language),
            user=P.chat_user(weather_block=wx, safety_block=kb.as_context(facts),
                             question=req.message),
            json_mode=False, max_tokens=800, temperature=0.5,
        )
        return ChatResponse(reply=result.text[:4000], language=req.language,
                            grounded_on=grounded, generated_by=result.model)
    except LLMError as exc:
        log.warning("chat_fallback", error=str(exc))
        return ChatResponse(reply=fb.fallback_chat_reply(weather), language=req.language,
                            grounded_on=grounded, generated_by="template")
