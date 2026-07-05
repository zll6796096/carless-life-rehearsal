import httpx

from app.domain.models import DestinationCategory
from app.fixtures.demo import build_demo_fixture
from app.services.routing.mock import MockRoutingProvider
from app.services.routing.otp import OTPRoutingProvider


def test_mock_routing_provider_returns_fixture_plan() -> None:
    fixture = build_demo_fixture()
    provider = MockRoutingProvider(fixture.mock_transport_results)
    destination = fixture.destinations[0]

    plan = provider.plan_trip(
        origin=fixture.home_location,
        destination=destination,
        departure_time="2026-07-06T09:00:00+09:00",
        profile=fixture.default_mobility_profile,
        direction="outbound",
    )

    assert plan.available is True
    assert plan.route_name == "地域バス"
    assert plan.walk_minutes == 8


def test_otp_routing_provider_parses_graphql_response_without_internal_ids() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/graphql"
        return httpx.Response(
            200,
            json={
                "data": {
                    "plan": {
                        "itineraries": [
                            {
                                "duration": 1800,
                                "walkTime": 420,
                                "waitingTime": 300,
                                "transfers": 1,
                                "legs": [
                                    {
                                        "mode": "WALK",
                                        "startTime": "2026-07-06T09:00:00+09:00",
                                        "endTime": "2026-07-06T09:07:00+09:00",
                                        "duration": 420,
                                        "route": None,
                                        "from": {"name": "自宅"},
                                        "to": {"name": "停留所"},
                                    },
                                    {
                                        "mode": "BUS",
                                        "startTime": "2026-07-06T09:12:00+09:00",
                                        "endTime": "2026-07-06T09:30:00+09:00",
                                        "duration": 1080,
                                        "route": {"shortName": "地域バス"},
                                        "from": {"name": "停留所"},
                                        "to": {"name": "スーパー前"},
                                    },
                                ],
                            }
                        ]
                    }
                }
            },
        )

    fixture = build_demo_fixture()
    provider = OTPRoutingProvider(
        graphql_url="https://otp.example.test/graphql",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    plan = provider.plan_trip(
        origin=fixture.home_location,
        destination=fixture.destinations[0],
        departure_time="2026-07-06T09:00:00+09:00",
        profile=fixture.default_mobility_profile,
        direction="outbound",
    )

    assert plan.available is True
    assert plan.duration_minutes == 30
    assert plan.walk_minutes == 7
    assert plan.wait_minutes == 5
    assert plan.transfers == 1
    assert plan.route_name == "地域バス"
    assert "internal" not in plan.summary_ja.lower()


def test_otp_routing_provider_returns_unavailable_plan_on_http_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    fixture = build_demo_fixture()
    provider = OTPRoutingProvider(
        graphql_url="https://otp.example.test/graphql",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    plan = provider.plan_trip(
        origin=fixture.home_location,
        destination=fixture.destinations[0],
        departure_time="2026-07-06T09:00:00+09:00",
        profile=fixture.default_mobility_profile,
        direction="outbound",
    )

    assert plan.available is False
    assert plan.route_name is None
    assert "判定不能" in plan.summary_ja


def test_mock_provider_missing_destination_is_unavailable() -> None:
    fixture = build_demo_fixture()
    provider = MockRoutingProvider({})
    destination = fixture.destinations[0].model_copy(
        update={"id": "missing", "category": DestinationCategory.SUPERMARKET}
    )

    plan = provider.plan_trip(
        origin=fixture.home_location,
        destination=destination,
        departure_time="2026-07-06T09:00:00+09:00",
        profile=fixture.default_mobility_profile,
        direction="outbound",
    )

    assert plan.available is False
    assert "判定不能" in plan.summary_ja
