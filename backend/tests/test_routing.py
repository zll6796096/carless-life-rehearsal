import json
from copy import deepcopy

import httpx
import pytest

from app.core.config import Settings
from app.fixtures.demo import build_demo_fixture
from app.services.routing.mock import MockRoutingProvider
from app.services.routing.otp import OTPRoutingProvider
from app.services.routing.provider import get_routing_provider


def payload():
    return {
        "data": {
            "planConnection": {
                "routingErrors": [],
                "edges": [
                    {
                        "node": {
                            "duration": 1800,
                            "walkTime": 420,
                            "waitingTime": 300,
                            "numberOfTransfers": 0,
                            "legs": [
                                {
                                    "mode": "WALK",
                                    "duration": 420,
                                    "route": None,
                                    "start": {"scheduledTime": "2026-09-08T09:00:00+09:00"},
                                    "end": {"scheduledTime": "2026-09-08T09:07:00+09:00"},
                                    "from": {"name": "自宅"},
                                    "to": {"name": "停留所"},
                                },
                                {
                                    "mode": "BUS",
                                    "duration": 1080,
                                    "route": {"gtfsId": "1:allowed", "shortName": "地域バス"},
                                    "start": {"scheduledTime": "2026-09-08T09:12:00+09:00"},
                                    "end": {"scheduledTime": "2026-09-08T09:30:00+09:00"},
                                    "from": {"name": "停留所"},
                                    "to": {"name": "スーパー前"},
                                },
                            ],
                        }
                    }
                ],
            }
        }
    }


def plan(provider, direction="outbound", departure="2026-09-08T09:00:00+09:00"):
    fixture = build_demo_fixture()
    return provider.plan_trip(
        origin=fixture.home_location,
        destination=fixture.destinations[0],
        departure_time=departure,
        profile=fixture.default_mobility_profile,
        direction=direction,
    )


def test_mock_fixture_and_missing_destination():
    fixture = build_demo_fixture()
    assert plan(MockRoutingProvider(fixture.mock_transport_results)).available
    assert not plan(MockRoutingProvider({})).available


@pytest.mark.parametrize("direction", ["outbound", "return"])
def test_new_api_metrics_and_return_coordinates(direction):
    fixture = build_demo_fixture()

    def handler(request):
        body = json.loads(request.content)
        assert "planConnection" in body["query"]
        coordinates = body["variables"]["origin"]["location"]["coordinate"]
        expected = fixture.home_location if direction == "outbound" else fixture.destinations[0]
        assert coordinates == {"latitude": expected.lat, "longitude": expected.lon}
        assert body["variables"]["dateTime"]["earliestDeparture"].startswith("2026-09-08")
        return httpx.Response(200, json=payload())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = plan(
            OTPRoutingProvider("https://otp.test/graphql", client, frozenset({"allowed"})),
            direction,
        )
    assert result.available
    assert (result.duration_minutes, result.walk_minutes, result.wait_minutes) == (30, 7, 5)
    assert result.route_name == "地域バス"
    assert not result.accessibility_verified
    assert "allowed" not in result.model_dump_json()


@pytest.mark.parametrize("case", ["graphql", "null", "empty", "route", "mode", "metric", "http"])
def test_invalid_response_fails_closed(case):
    data = payload()
    node = data["data"]["planConnection"]["edges"][0]["node"]
    if case == "graphql":
        data["errors"] = [{"message": "partial error"}]
    elif case == "null":
        data = {"data": None}
    elif case == "empty":
        node["legs"] = []
    elif case == "route":
        node["legs"][1]["route"]["gtfsId"] = "1:reservation"
    elif case == "mode":
        node["legs"][1]["mode"] = "CAR"
    elif case == "metric":
        node["walkTime"] = None
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(503 if case == "http" else 200, json=data)
        )
    ) as client:
        result = plan(
            OTPRoutingProvider("https://otp.test/graphql", client, frozenset({"allowed"}))
        )
    assert not result.available
    assert "判定不能" in result.summary_ja


def test_selected_otp_without_url_does_not_fall_back_to_mock():
    provider = get_routing_provider(Settings(routing_provider="otp", otp_graphql_url=None))
    result = plan(provider)
    assert result.provider == "otp"
    assert not result.available


def test_naive_date_does_not_make_request():
    def handler(_):
        raise AssertionError("must not query without timezone")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = plan(
            OTPRoutingProvider("https://otp.test/graphql", client, frozenset({"allowed"})),
            departure="2026-09-08T09:00:00",
        )
    assert not result.available


def test_private_cloud_run_uses_metadata_identity_token():
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.host == "metadata.google.internal":
            assert request.headers["Metadata-Flavor"] == "Google"
            assert request.url.params["audience"] == "https://otp.test"
            return httpx.Response(200, text="test-identity-token")
        assert request.headers["Authorization"] == "Bearer test-identity-token"
        return httpx.Response(200, json=payload())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OTPRoutingProvider(
            "https://otp.test/graphql",
            client,
            frozenset({"allowed"}),
            identity_audience="https://otp.test",
        )
        assert plan(provider).available
    assert len(calls) == 2


def test_identity_token_is_not_sent_to_a_different_origin():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: (_ for _ in ()).throw(AssertionError("must not fetch or send token"))
        )
    ) as client:
        provider = OTPRoutingProvider(
            "https://other.test/graphql",
            client,
            frozenset({"allowed"}),
            identity_audience="https://otp.test",
        )
        assert not plan(provider).available


def test_choose_profile_compatible_bus_instead_of_first_long_walk():
    data = payload()
    bus = data["data"]["planConnection"]["edges"][0]
    walk = deepcopy(bus)
    walk["node"]["walkTime"] = 1800
    walk["node"]["legs"] = [walk["node"]["legs"][0]]
    data["data"]["planConnection"]["edges"] = [walk, bus]
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))) as c:
        result = plan(OTPRoutingProvider("https://otp.test/graphql", c, frozenset({"allowed"})))
    assert result.walk_minutes == 7
    assert result.route_name == "地域バス"


def test_walking_better_notice_with_valid_walk_is_available():
    data = payload()
    connection = data["data"]["planConnection"]
    connection["routingErrors"] = [{"code": "WALKING_BETTER_THAN_TRANSIT"}]
    connection["edges"][0]["node"]["legs"] = [connection["edges"][0]["node"]["legs"][0]]
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))) as c:
        result = plan(OTPRoutingProvider("https://otp.test/graphql", c, frozenset({"allowed"})))
    assert result.available
    assert all(leg.mode == "WALK" for leg in result.legs)
