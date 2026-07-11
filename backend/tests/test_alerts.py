from app.models.schemas import RiskLevel
from app.services.alerts import derive_alerts, top_risk


def test_very_heavy_rain_triggers_high_flood_alert(fake_weather):
    fake_weather.precip_mm = 150.0
    alerts = derive_alerts(fake_weather)
    assert any(a.hazard == "flooding" and a.severity == RiskLevel.high for a in alerts)


def test_extreme_rain_triggers_severe(fake_weather):
    fake_weather.precip_mm = 250.0
    alerts = derive_alerts(fake_weather)
    assert top_risk(alerts) == RiskLevel.severe


def test_calm_weather_no_alerts(fake_weather):
    fake_weather.precip_mm = 2.0
    fake_weather.wind_kmh = 8.0
    fake_weather.temp_c = 30.0
    fake_weather.daily = []
    assert derive_alerts(fake_weather) == []


def test_gale_wind_alert(fake_weather):
    fake_weather.precip_mm = 0.0
    fake_weather.wind_kmh = 70.0
    fake_weather.daily = []
    alerts = derive_alerts(fake_weather)
    assert any(a.hazard == "wind" for a in alerts)
