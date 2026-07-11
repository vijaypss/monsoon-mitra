import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Location, WeatherSnapshot


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fake_weather() -> WeatherSnapshot:
    return WeatherSnapshot(
        location=Location(lat=19.076, lon=72.877, name="Mumbai"),
        observed_at="2026-07-11T09:00:00Z",
        temp_c=29.0, feels_like_c=34.0, precip_mm=120.0, humidity=88,
        wind_kmh=40.0, monsoon_hazard_score=62, daily=[],
    )
