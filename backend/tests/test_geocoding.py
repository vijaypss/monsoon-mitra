"""Geocoding tests — upstream mocked, no network."""
import httpx
import pytest

from app.services import geocoding


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):  # noqa: D401
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, *a, **k):
        return _FakeResp(self._payload)


@pytest.fixture(autouse=True)
def _clear_cache():
    geocoding._cache.clear()
    yield


async def test_search_parses_results(monkeypatch):
    payload = {"results": [
        {"name": "Kochi", "latitude": 9.93, "longitude": 76.26,
         "admin1": "Kerala", "country": "India", "country_code": "IN"},
    ]}
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeClient(payload))
    res = await geocoding.search_places("kochi")
    assert len(res) == 1
    assert res[0].label == "Kochi, Kerala, India"
    assert res[0].lat == 9.93


async def test_short_query_returns_empty():
    assert await geocoding.search_places("k") == []


async def test_no_results_key(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeClient({}))
    assert await geocoding.search_places("zzzznowhere") == []


async def test_upstream_error_degrades(monkeypatch):
    def _boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    assert await geocoding.search_places("mumbai") == []


async def test_reverse_geocode_resolves_name(monkeypatch):
    payload = {"city": "Mumbai", "locality": "Bandra West",
               "principalSubdivision": "Maharashtra", "countryName": "India",
               "countryCode": "IN"}
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _FakeClient(payload))
    res = await geocoding.reverse_geocode(19.06, 72.83)
    assert res is not None
    assert res.name == "Mumbai"
    assert "Bandra West" in res.label and "India" in res.label


async def test_reverse_geocode_error_returns_none(monkeypatch):
    def _boom(*a, **k):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    assert await geocoding.reverse_geocode(19.06, 72.83) is None
