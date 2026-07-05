import pytest
from pydantic import ValidationError

from app.domain.models import Destination, DestinationCategory, FeasibilityStatus, MobilityProfile
from app.fixtures.demo import build_demo_fixture


def test_mobility_profile_validates_positive_limits() -> None:
    with pytest.raises(ValidationError):
        MobilityProfile(
            walk_minutes=0,
            max_transfers=1,
            max_wait_minutes=10,
            avoid_stairs=True,
            can_use_demand_transit=False,
            prefers_voice_guidance=True,
        )


def test_destination_accepts_known_categories_and_optional_coordinates() -> None:
    destination = Destination(
        id="missing-coordinates",
        category=DestinationCategory.PHARMACY,
        name="駅前薬局",
        lat=None,
        lon=None,
        importance_weight=0.15,
    )

    assert destination.category == DestinationCategory.PHARMACY
    assert destination.lat is None


def test_fixture_contains_demo_life_inputs() -> None:
    fixture = build_demo_fixture()

    categories = {destination.category for destination in fixture.destinations}

    assert fixture.home_location.name == "デモ自宅"
    assert len(fixture.destinations) >= 5
    assert DestinationCategory.SUPERMARKET in categories
    assert DestinationCategory.HOSPITAL in categories
    assert fixture.default_mobility_profile.walk_minutes == 10
    assert {window.label for window in fixture.time_windows} == {
        "weekday_morning",
        "weekday_afternoon",
    }
    assert fixture.mock_transport_results
    assert FeasibilityStatus.OK.value == "ok"
