import pytest
from pydantic import ValidationError

from app.domain.models import DiagnosisRequest
from app.fixtures.demo import build_demo_fixture
from app.services.diagnosis import engine


def request_data():
    data = build_demo_fixture().model_dump()
    data["mock_transport_results"] = {}
    return data


def test_missing_dates_remain_unknown_without_network(monkeypatch):
    class NoNetwork:
        def plan_trip(self, **kwargs):
            raise AssertionError("missing dates must not query routing")

    monkeypatch.setattr(engine, "get_routing_provider", lambda **_: NoNetwork())
    result = engine.run_life_diagnosis(DiagnosisRequest(**request_data()))
    assert all(item.status == "unknown" for item in result.item_results)


def test_explicit_dates_propagate_and_accessibility_is_not_assumed(monkeypatch):
    fixture = build_demo_fixture()
    calls = []

    class Capture:
        def plan_trip(self, **kwargs):
            calls.append((kwargs["direction"], kwargs["departure_time"]))
            plan = next(iter(fixture.mock_transport_results.values())).outbound.model_copy(
                deep=True
            )
            plan.provider = "otp"
            plan.legs[-1].end_time = "2026-09-08T09:20:00+09:00"
            plan.accessibility_verified = False
            return plan

    monkeypatch.setattr(engine, "get_routing_provider", lambda **_: Capture())
    data = request_data()
    data.update(
        outbound_departure="2026-09-08T06:50:00+09:00", return_departure="2026-09-08T11:00:00+09:00"
    )
    result = engine.run_life_diagnosis(DiagnosisRequest(**data))
    assert set(calls) == {
        ("outbound", data["outbound_departure"]),
        ("return", data["return_departure"]),
    }
    assert all(
        any("未確認" in reason for reason in item.reasons_ja) for item in result.item_results
    )


@pytest.mark.parametrize(
    "outbound,return_time",
    [
        ("2026-09-08T06:50:00", "2026-09-08T11:00:00+09:00"),
        ("2026-09-08T11:00:00+09:00", "2026-09-08T06:50:00+09:00"),
    ],
)
def test_invalid_dates_rejected(outbound, return_time):
    with pytest.raises(ValidationError):
        DiagnosisRequest(
            **request_data(), outbound_departure=outbound, return_departure=return_time
        )


def test_outbound_arrival_after_return_departure_is_unknown(monkeypatch):
    fixture = build_demo_fixture()

    class TooLate:
        def plan_trip(self, **kwargs):
            plan = next(iter(fixture.mock_transport_results.values())).outbound.model_copy(
                deep=True
            )
            plan.provider = "otp"
            plan.legs[-1].end_time = "2026-09-08T12:00:00+09:00"
            return plan

    monkeypatch.setattr(engine, "get_routing_provider", lambda **_: TooLate())
    request = DiagnosisRequest(
        **request_data(),
        outbound_departure="2026-09-08T06:50:00+09:00",
        return_departure="2026-09-08T11:00:00+09:00",
    )
    result = engine.run_life_diagnosis(request)
    assert all(item.status == "unknown" for item in result.item_results)
