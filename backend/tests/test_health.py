def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "llm_enabled" in body


def test_languages_lists_indian_langs(client):
    r = client.get("/api/v1/languages")
    assert r.status_code == 200
    langs = r.json()["languages"]
    assert "hi" in langs and "ta" in langs and "bn" in langs


def test_security_headers_present(client):
    r = client.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
