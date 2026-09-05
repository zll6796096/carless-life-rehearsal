from datetime import datetime
from math import ceil, isfinite
from typing import Any

import httpx

from app.domain.models import Destination, HomeLocation, MobilityProfile, TripLeg, TripPlanResult


class OTPRoutingProvider:
    def __init__(
        self,
        graphql_url: str,
        client: httpx.Client | None = None,
        allowed_route_ids: frozenset[str] = frozenset(),
        identity_audience: str | None = None,
    ) -> None:
        self.graphql_url = graphql_url
        self.client = client
        self.allowed_route_ids = allowed_route_ids
        self.identity_audience = identity_audience

    def _headers(self, client: httpx.Client) -> dict[str, str]:
        if not self.identity_audience:
            return {}
        audience = self.identity_audience.rstrip("/")
        if not audience.startswith("https://") or not self.graphql_url.startswith(audience + "/"):
            raise ValueError("OTP identity audience must match the configured service")
        token = client.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity",
            params={"audience": audience},
            headers={"Metadata-Flavor": "Google"},
            timeout=5,
        )
        token.raise_for_status()
        if not token.text.strip():
            raise ValueError("Empty identity token")
        return {"Authorization": f"Bearer {token.text.strip()}"}

    def plan_trip(
        self,
        *,
        origin: HomeLocation,
        destination: Destination,
        departure_time: str,
        profile: MobilityProfile,
        direction: str,
    ) -> TripPlanResult:
        if any(v is None for v in (origin.lat, origin.lon, destination.lat, destination.lon)):
            return _unavailable("位置情報が不足しているため判定不能です。")
        if not self.graphql_url or not self.allowed_route_ids:
            return _unavailable("経路サービスの設定が不足しているため判定不能です。")
        try:
            _date(departure_time)
            if direction not in {"outbound", "return"}:
                raise ValueError("invalid direction")
            start = _location(origin.name, origin.lat, origin.lon)
            end = _location(destination.name, destination.lat, destination.lon)
            if direction == "return":
                start, end = end, start
            variables = {
                "origin": start,
                "destination": end,
                "dateTime": {"earliestDeparture": departure_time},
            }
            if self.client is not None:
                response = self.client.post(
                    self.graphql_url,
                    headers=self._headers(self.client),
                    json={"query": _PLAN_QUERY, "variables": variables},
                )
            else:
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        self.graphql_url,
                        headers=self._headers(client),
                        json={"query": _PLAN_QUERY, "variables": variables},
                    )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise ValueError("GraphQL errors")
            connection = payload["data"]["planConnection"]
            routing_errors = connection.get("routingErrors") or []
            if any(e["code"] != "WALKING_BETTER_THAN_TRANSIT" for e in routing_errors):
                raise ValueError("routing errors")
            edges = connection["edges"]
            if not edges:
                raise ValueError("no itinerary")
            plans = [_parse_itinerary(e["node"], self.allowed_route_ids) for e in edges]
            if routing_errors and any(leg.mode != "WALK" for plan in plans for leg in plan.legs):
                raise ValueError("unexpected transit with walking-only notice")
            plan = min(
                plans,
                key=lambda p: (
                    max(0, p.walk_minutes - profile.walk_minutes)
                    + max(0, p.wait_minutes - profile.max_wait_minutes)
                    + 15 * max(0, p.transfers - profile.max_transfers),
                    _date(p.legs[-1].end_time),
                ),
            )
            plan.option_count = len(plans)
            if profile.avoid_stairs:
                plan.summary_ja += " 階段の有無や建物入口の通行条件は未確認です。"
            return plan
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
            return _unavailable("信頼できる経路データを取得できないため判定不能です。")


def _location(name: str, lat: float | None, lon: float | None) -> dict[str, Any]:
    return {"label": name, "location": {"coordinate": {"latitude": lat, "longitude": lon}}}


def _date(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("timezone required")
    return result


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("numeric value required")
    if not isfinite(value) or value < 0:
        raise ValueError("invalid value")
    return float(value)


def _parse_itinerary(itinerary: dict[str, Any], allowed: frozenset[str]) -> TripPlanResult:
    legs = []
    names = []
    for leg in itinerary["legs"]:
        mode = leg["mode"]
        if mode not in {"WALK", "BUS"}:
            raise ValueError("unsupported mode")
        name = None
        if mode == "BUS":
            route = leg["route"]
            if route["gtfsId"].split(":", 1)[-1] not in allowed:
                raise ValueError("route outside pilot")
            name = route.get("shortName") or route.get("longName") or "路線バス"
            names.append(name)
        start, end = leg["start"]["scheduledTime"], leg["end"]["scheduledTime"]
        if _date(end) < _date(start):
            raise ValueError("reversed times")
        minutes = ceil(_number(leg["duration"]) / 60)
        legs.append(
            TripLeg(
                mode=mode,
                start_time=start,
                end_time=end,
                duration_minutes=minutes,
                walk_minutes=minutes if mode == "WALK" else 0,
                route_name=name,
                from_name=leg["from"]["name"] or "出発地",
                to_name=leg["to"]["name"] or "目的地",
                wait_minutes=0,
                transfers=0,
            )
        )
    if not legs:
        raise ValueError("empty legs")
    walk = ceil(_number(itinerary["walkTime"]) / 60)
    wait = ceil(_number(itinerary["waitingTime"]) / 60)
    transfers = _number(itinerary["numberOfTransfers"])
    if not transfers.is_integer():
        raise ValueError("invalid transfers")
    route_name = " / ".join(dict.fromkeys(names)) or None
    return TripPlanResult(
        provider="otp",
        available=True,
        duration_minutes=ceil(_number(itinerary["duration"]) / 60),
        walk_minutes=walk,
        wait_minutes=wait,
        transfers=int(transfers),
        route_name=route_name,
        summary_ja=f"徒歩{walk}分、待ち時間{wait}分の経路です。",
        legs=legs,
        accessibility_verified=False,
    )


def _unavailable(summary_ja: str) -> TripPlanResult:
    return TripPlanResult(
        provider="otp",
        available=False,
        duration_minutes=0,
        walk_minutes=0,
        wait_minutes=0,
        transfers=0,
        summary_ja=summary_ja,
        option_count=0,
        accessibility_verified=False,
    )


_PLAN_QUERY = """
query Plan($origin: PlanLabeledLocationInput!, $destination: PlanLabeledLocationInput!,
           $dateTime: PlanDateTimeInput!) {
  planConnection(origin: $origin, destination: $destination, dateTime: $dateTime,
    first: 3, searchWindow: "PT2H",
    modes: {direct: [WALK], transit: {access: [WALK], egress: [WALK],
      transfer: [WALK], transit: [{mode: BUS}]}}) {
    routingErrors { code }
    edges { node {
      duration walkTime waitingTime numberOfTransfers
      legs {
        mode duration start { scheduledTime } end { scheduledTime }
        route { gtfsId shortName longName }
        from { name } to { name }
      }
    } }
  }
}
"""
