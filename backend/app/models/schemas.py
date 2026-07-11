"""Pydantic schemas — the strict, validated contract for every endpoint.

Bounded fields (coordinate ranges, list sizes, enums) double as an
input-validation security layer.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

# ── Supported Indian languages (ISO 639-1 / common codes) ──────────────
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "हिन्दी (Hindi)",
    "bn": "বাংলা (Bengali)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "mr": "मराठी (Marathi)",
    "gu": "ગુજરાતી (Gujarati)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)",
    "pa": "ਪੰਜਾਬੀ (Punjabi)",
    "or": "ଓଡ଼ିଆ (Odia)",
    "as": "অসমীয়া (Assamese)",
}


class Phase(str, Enum):
    before = "before"
    during = "during"
    after = "after"


class DwellingType(str, Enum):
    apartment = "apartment"
    independent_house = "independent_house"
    slum_kutcha = "slum_kutcha"
    coastal = "coastal"
    hillside = "hillside"


class RiskLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"


# ── Shared building blocks ─────────────────────────────────────────────
class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    name: str = Field(default="", max_length=120)


class GeoResult(BaseModel):
    """A place resolved by the geocoder."""
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    admin1: str | None = None       # state / province
    country: str | None = None
    country_code: str | None = None
    label: str                       # "Kochi, Kerala, India"


class Household(BaseModel):
    adults: int = Field(default=1, ge=0, le=30)
    children: int = Field(default=0, ge=0, le=30)
    seniors: int = Field(default=0, ge=0, le=30)
    dwelling: DwellingType = Field(default=DwellingType.apartment)
    floor: int = Field(default=0, ge=-2, le=100, description="Ground=0; negative=basement")
    medical_needs: list[str] = Field(default_factory=list, max_length=20)
    has_vehicle: bool = Field(default=False)
    pets: int = Field(default=0, ge=0, le=50)

    @field_validator("medical_needs")
    @classmethod
    def _cap_lengths(cls, v: list[str]) -> list[str]:
        return [s.strip()[:60] for s in v if s.strip()]


# ── Weather ────────────────────────────────────────────────────────────
class DailyForecast(BaseModel):
    date: str
    precip_mm: float
    precip_prob: int
    temp_max: float
    temp_min: float
    wind_max_kmh: float


class WeatherSnapshot(BaseModel):
    location: Location
    observed_at: str
    temp_c: float
    feels_like_c: float
    precip_mm: float
    humidity: int
    wind_kmh: float
    monsoon_hazard_score: int = Field(ge=0, le=100)
    daily: list[DailyForecast] = Field(default_factory=list)


# ── Alerts ─────────────────────────────────────────────────────────────
class Alert(BaseModel):
    id: str
    severity: RiskLevel
    title: str
    message: str
    hazard: str  # heavy_rain | flooding | lightning | heat | wind
    issued_at: str
    valid_until: str


# ── Preparedness plan ──────────────────────────────────────────────────
class PlanRequest(BaseModel):
    location: Location
    household: Household = Field(default_factory=Household)
    language: str = Field(default="en")

    @field_validator("language")
    @classmethod
    def _known_language(cls, v: str) -> str:
        v = v.lower()
        return v if v in SUPPORTED_LANGUAGES else "en"


class PreparednessPlan(BaseModel):
    risk_level: RiskLevel
    summary: str
    before: list[str]
    during: list[str]
    after: list[str]
    go_bag: list[str]
    language: str
    generated_by: str  # "groq:<model>" or "template"


class PlanResponse(BaseModel):
    plan: PreparednessPlan
    weather: WeatherSnapshot
    alerts: list[Alert]


# ── Checklist ──────────────────────────────────────────────────────────
class ChecklistRequest(BaseModel):
    location: Location
    household: Household = Field(default_factory=Household)
    phase: Phase = Field(default=Phase.before)
    language: str = Field(default="en")


class ChecklistItem(BaseModel):
    task: str
    priority: RiskLevel
    done: bool = False


class ChecklistResponse(BaseModel):
    phase: Phase
    items: list[ChecklistItem]
    language: str
    generated_by: str


# ── Travel advisory ────────────────────────────────────────────────────
class TravelRequest(BaseModel):
    origin: Location
    destination: Location
    depart_in_hours: int = Field(default=0, ge=0, le=168)
    mode: str = Field(default="car", max_length=20)
    language: str = Field(default="en")


class TravelAdvisory(BaseModel):
    recommendation: str  # go | caution | postpone
    risk_level: RiskLevel
    summary: str
    tips: list[str]
    language: str
    generated_by: str


# ── Chat ───────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    location: Location | None = None
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)
    language: str = Field(default="en")


class ChatResponse(BaseModel):
    reply: str
    language: str
    grounded_on: list[str]  # what context was injected (for transparency)
    generated_by: str
