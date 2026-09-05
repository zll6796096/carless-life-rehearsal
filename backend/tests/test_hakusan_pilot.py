import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_pilot_rejects_mock_backend(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "mock")
    client = TestClient(app)
    assert client.get("/fixtures/hakusan").status_code == 503
    demo = client.get("/fixtures/demo").json()
    assert demo["mock_transport_results"]
    assert (
        client.post("/diagnosis/run", json={**demo, "data_profile": "hakusan"}).status_code == 503
    )


def test_pilot_requires_endpoint(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "otp")
    monkeypatch.setenv("OTP_GRAPHQL_URL", "")
    assert TestClient(app).get("/fixtures/hakusan").status_code == 503


def test_pilot_contract_and_date_guards(monkeypatch):
    monkeypatch.setenv("ROUTING_PROVIDER", "otp")
    monkeypatch.setenv("OTP_GRAPHQL_URL", "http://127.0.0.1:1/otp/gtfs/v1")
    client = TestClient(app)
    response = client.get("/fixtures/hakusan")
    assert response.status_code == 200
    fixture = response.json()
    assert len({d["category"] for d in fixture["destinations"]}) == 6
    assert fixture["home_location"]["lat"] == 36.52725
    assert fixture["mock_transport_results"] == {}
    assert fixture["pilot"]["service_end"] == "2027-03-15"
    assert client.post("/diagnosis/run", json=fixture).status_code == 422
    for outbound, returning in [
        ("2026-09-08T11:00:00+09:00", "2026-09-08T06:50:00+09:00"),
        ("2027-03-16T06:50:00+09:00", "2027-03-16T11:00:00+09:00"),
        ("2026-03-15T06:50:00+09:00", "2026-03-15T11:00:00+09:00"),
    ]:
        assert (
            client.post(
                "/diagnosis/run",
                json={**fixture, "outbound_departure": outbound, "return_departure": returning},
            ).status_code
            == 422
        )
    valid = {
        **fixture,
        "outbound_departure": "2026-09-08T06:50:00+09:00",
        "return_departure": "2026-09-08T11:00:00+09:00",
    }
    demo = client.get("/fixtures/demo").json()
    assert (
        client.post(
            "/diagnosis/run",
            json={**valid, "mock_transport_results": demo["mock_transport_results"]},
        ).status_code
        == 422
    )
    unavailable = client.post("/diagnosis/run", json=valid)
    assert unavailable.status_code == 200
    assert unavailable.json()["data_source"] == "routing_provider"
    assert all(item["status"] == "unknown" for item in unavailable.json()["item_results"])
