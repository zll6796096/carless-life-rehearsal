import json
from pathlib import Path

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
    if active_settings.routing_provider == "otp":
        allowed = frozenset()
        try:
            policy = json.loads(Path(active_settings.otp_route_rules_path).read_text())
            if policy["default_policy"] == "deny":
                allowed = frozenset(row["route_id"] for row in policy["allowed_routes"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return OTPRoutingProvider(
            active_settings.otp_graphql_url or "",
            allowed_route_ids=allowed,
            identity_audience=active_settings.otp_identity_audience,
        )
    return MockRoutingProvider(mock_results)
