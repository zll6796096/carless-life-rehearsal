from math import ceil
from typing import Any

import httpx

from app.domain.models import Destination, HomeLocation, MobilityProfile, TripLeg, TripPlanResult


class OTPRoutingProvider:
    def __init__(self, graphql_url: str, client: httpx.Client | None = None) -> None:
        self.graphql_url = graphql_url
        self.client = client or httpx.Client(timeout=10)

    def plan_trip(
        self,
        *,
        origin: HomeLocation,
        destination: Destination,
        departure_time: str,
        profile: MobilityProfile,
        direction: str,
    ) -> TripPlanResult:
        missing_coordinates = (
            origin.lat is None
            or origin.lon is None
            or destination.lat is None
            or destination.lon is None
        )
        if missing_coordinates:
            return _unavailable("位置情報が不足しているため判定不能です。")

        variables = {
            "from": {"lat": origin.lat, "lon": origin.lon},
            "to": {"lat": destination.lat, "lon": destination.lon},
            "dateTime": departure_time,
            "walkReluctance": 2.0 if profile.avoid_stairs else 1.0,
            "direction": direction,
        }
        try:
            response = self.client.post(
                self.graphql_url,
                json={"query": _PLAN_QUERY, "variables": variables},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return _unavailable("OTPから経路を取得できないため判定不能です。")

        itineraries = (
            payload.get("data", {}).get("plan", {}).get("itineraries", [])
            if isinstance(payload, dict)
            else []
        )
        if not itineraries:
            return _unavailable("利用できる経路が見つからないため判定不能です。")

        itinerary = itineraries[0]
        return _parse_itinerary(itinerary)


def _parse_itinerary(itinerary: dict[str, Any]) -> TripPlanResult:
    legs: list[TripLeg] = []
    route_names: list[str] = []
    for leg in itinerary.get("legs", []):
        route_name = None
        route = leg.get("route")
        if isinstance(route, dict):
            route_name = route.get("shortName") or route.get("longName")
        if route_name:
            route_names.append(route_name)
        duration_seconds = int(leg.get("duration") or 0)
        legs.append(
            TripLeg(
                mode=str(leg.get("mode") or "UNKNOWN"),
                start_time=str(leg.get("startTime") or ""),
                end_time=str(leg.get("endTime") or ""),
                duration_minutes=ceil(duration_seconds / 60),
                walk_minutes=ceil(duration_seconds / 60) if leg.get("mode") == "WALK" else 0,
                wait_minutes=0,
                transfers=0,
                route_name=route_name,
                from_name=str((leg.get("from") or {}).get("name") or ""),
                to_name=str((leg.get("to") or {}).get("name") or ""),
            )
        )

    route_name = " / ".join(dict.fromkeys(route_names)) if route_names else None
    duration_minutes = ceil(int(itinerary.get("duration") or 0) / 60)
    walk_minutes = ceil(int(itinerary.get("walkTime") or 0) / 60)
    wait_minutes = ceil(int(itinerary.get("waitingTime") or 0) / 60)
    transfers = int(itinerary.get("transfers") or 0)
    summary = (
        f"{route_name}を使う経路です。徒歩{walk_minutes}分、待ち時間{wait_minutes}分です。"
        if route_name
        else f"公共交通の経路です。徒歩{walk_minutes}分、待ち時間{wait_minutes}分です。"
    )

    return TripPlanResult(
        provider="otp",
        available=True,
        duration_minutes=duration_minutes,
        walk_minutes=walk_minutes,
        wait_minutes=wait_minutes,
        transfers=transfers,
        route_name=route_name,
        summary_ja=summary,
        option_count=1,
        legs=legs,
    )


def _unavailable(summary_ja: str) -> TripPlanResult:
    return TripPlanResult(
        provider="otp",
        available=False,
        duration_minutes=0,
        walk_minutes=0,
        wait_minutes=0,
        transfers=0,
        route_name=None,
        summary_ja=summary_ja,
        option_count=0,
        legs=[],
    )


_PLAN_QUERY = """
query Plan($from: InputCoordinates!, $to: InputCoordinates!, $dateTime: DateTime!) {
  plan(from: $from, to: $to, dateTime: $dateTime) {
    itineraries {
      duration
      walkTime
      waitingTime
      transfers
      legs {
        mode
        startTime
        endTime
        duration
        route {
          shortName
          longName
        }
        from {
          name
        }
        to {
          name
        }
      }
    }
  }
}
"""
