from app.core.config import Settings, get_settings
from app.domain.models import RoundTripPlan
from app.services.routing.base import RoutingProvider
from app.services.routing.mock import MockRoutingProvider
from app.services.routing.otp import OTPRoutingProvider


def get_routing_provider(
    settings: Settings | None = None,
    mock_results: dict[str, RoundTripPlan] | None = None,
) -> RoutingProvider:
    active_settings = settings or get_settings()
    if active_settings.routing_provider == "otp" and active_settings.otp_graphql_url:
        return OTPRoutingProvider(active_settings.otp_graphql_url)
    return MockRoutingProvider(mock_results)
