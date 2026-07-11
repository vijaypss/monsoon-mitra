"""Generation tests with the LLM mocked — verifies grounding, JSON parsing,
and graceful fallback without any network or API key."""
import pytest

from app.models.schemas import (
    ChatRequest,
    ChecklistRequest,
    Household,
    Location,
    Phase,
    PlanRequest,
)
from app.services import generation
from app.services.llm.base import LLMError, LLMResult


class _FakeProvider:
    def __init__(self, text: str = "", raise_error: bool = False):
        self._text = text
        self._raise = raise_error

    async def complete(self, **kwargs):
        if self._raise:
            raise LLMError("boom")
        return LLMResult(text=self._text, model="groq:test")


@pytest.fixture
def loc():
    return Location(lat=19.076, lon=72.877, name="Mumbai")


async def test_plan_parses_llm_json(monkeypatch, loc, fake_weather):
    good = (
        '{"risk_level":"high","summary":"Heavy rain ahead.",'
        '"before":["Charge phone","Store water"],'
        '"during":["Stay indoors","Avoid floodwater"],'
        '"after":["Clean up safely"],"go_bag":["Torch","Water"]}'
    )
    monkeypatch.setattr(generation, "get_provider", lambda: _FakeProvider(good))
    req = PlanRequest(location=loc, household=Household(), language="hi")
    plan = await generation.generate_plan(req, fake_weather)
    assert plan.risk_level.value == "high"
    assert plan.before and plan.go_bag
    assert plan.generated_by == "groq:test"


async def test_plan_falls_back_on_llm_error(monkeypatch, loc, fake_weather):
    monkeypatch.setattr(generation, "get_provider", lambda: _FakeProvider(raise_error=True))
    req = PlanRequest(location=loc, household=Household(seniors=1, medical_needs=["diabetes"]))
    plan = await generation.generate_plan(req, fake_weather)
    assert plan.generated_by == "template"
    assert plan.before  # still usable


async def test_plan_template_mode_when_no_provider(monkeypatch, loc, fake_weather):
    monkeypatch.setattr(generation, "get_provider", lambda: None)
    req = PlanRequest(location=loc, household=Household(floor=0, dwelling="coastal"))
    plan = await generation.generate_plan(req, fake_weather)
    assert plan.generated_by == "template"


async def test_checklist_fallback(monkeypatch, loc, fake_weather):
    monkeypatch.setattr(generation, "get_provider", lambda: None)
    req = ChecklistRequest(location=loc, phase=Phase.during)
    res = await generation.generate_checklist(req, fake_weather)
    assert res.phase == Phase.during
    assert len(res.items) >= 3


async def test_chat_is_grounded(monkeypatch, loc, fake_weather):
    monkeypatch.setattr(generation, "get_provider", lambda: _FakeProvider("Stay safe indoors."))
    req = ChatRequest(message="Is it safe to travel by car today?", location=loc, language="en")
    res = await generation.generate_chat(req, fake_weather)
    assert res.reply
    assert res.grounded_on  # context ids were injected


def test_safe_json_extracts_from_prose():
    assert generation._safe_json('noise {"a": 1} trailing')["a"] == 1
    assert generation._safe_json("not json at all") is None
