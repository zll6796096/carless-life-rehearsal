from app.domain.models import (
    Destination,
    HomeLocation,
    MobilityProfile,
    RoundTripPlan,
    TripPlanResult,
)


class MockRoutingProvider:
    def __init__(self, results: dict[str, RoundTripPlan] | None = None) -> None:
        self.results = results or {}

    def plan_trip(
        self,
        *,
        origin: HomeLocation,
        destination: Destination,
        departure_time: str,
        profile: MobilityProfile,
        direction: str,
    ) -> TripPlanResult:
        del origin, departure_time, profile
        round_trip = self.results.get(destination.id)
        plan = round_trip.outbound if direction == "outbound" and round_trip else None
        if direction == "return" and round_trip:
            plan = round_trip.return_plan
        if plan is not None:
            return plan
        return unavailable_plan(f"{destination.name}の交通データが不足しているため判定不能です。")


def unavailable_plan(summary_ja: str) -> TripPlanResult:
    return TripPlanResult(
        provider="mock",
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
