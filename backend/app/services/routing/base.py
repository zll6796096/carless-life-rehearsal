from typing import Protocol

from app.domain.models import Destination, HomeLocation, MobilityProfile, TripPlanResult


class RoutingProvider(Protocol):
    def plan_trip(
        self,
        *,
        origin: HomeLocation,
        destination: Destination,
        departure_time: str,
        profile: MobilityProfile,
        direction: str,
    ) -> TripPlanResult:
        """Return a deterministic trip plan or an unavailable plan with a warning summary."""
