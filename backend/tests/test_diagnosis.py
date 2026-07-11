import pytest
from fastapi.testclient import TestClient

from app.domain.models import Destination, DestinationCategory, FeasibilityStatus
from app.fixtures.demo import build_demo_fixture
from app.main import app
from app.services.diagnosis.engine import calculate_life_score, run_life_diagnosis


def test_fixtures_demo_endpoint_returns_usable_sample_data() -> None:
    client = TestClient(app)

    response = client.get("/fixtures/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["home_location"]["name"] == "デモ自宅"
    assert len(payload["destinations"]) >= 5
    assert payload["default_mobility_profile"]["walk_minutes"] == 10
    assert payload["mock_transport_results"]


def test_diagnosis_endpoint_returns_status_for_all_demo_categories() -> None:
    client = TestClient(app)
    fixture = client.get("/fixtures/demo").json()

    response = client.post("/diagnosis/run", json=fixture)

    assert response.status_code == 200
    payload = response.json()
    categories = {item["category"] for item in payload["item_results"]}
    assert categories == {
        "supermarket",
        "hospital",
        "pharmacy",
        "city_hall",
        "station",
        "social",
    }
    assert payload["summary_ja"]
    assert payload["next_recommended_action"]
    assert 0 <= payload["data_confidence"] <= 1


def test_demo_diagnosis_has_explainable_expected_statuses() -> None:
    fixture = build_demo_fixture()

    diagnosis = run_life_diagnosis(fixture)
    by_category = {item.category: item for item in diagnosis.item_results}

    assert by_category[DestinationCategory.SUPERMARKET].status == FeasibilityStatus.OK
    assert by_category[DestinationCategory.HOSPITAL].status == FeasibilityStatus.CAUTION
    assert "帰りの待ち時間" in " ".join(by_category[DestinationCategory.HOSPITAL].reasons_ja)
    assert by_category[DestinationCategory.CITY_HALL].status == FeasibilityStatus.SUPPORT_NEEDED
    assert "帰りの便" in " ".join(by_category[DestinationCategory.CITY_HALL].reasons_ja)


def test_demo_diagnosis_marks_fixture_provenance_and_caps_confidence() -> None:
    diagnosis = run_life_diagnosis(build_demo_fixture())

    assert diagnosis.data_source == "fixture"
    assert diagnosis.data_confidence <= 0.75
    assert any(
        warning.code == "fixture_data_only" for warning in diagnosis.data_quality_warnings
    )


def test_missing_destination_data_returns_unknown_with_warning() -> None:
    fixture = build_demo_fixture()
    fixture.destinations = [
        Destination(
            id="unknown-shop",
            category=DestinationCategory.SUPERMARKET,
            name="場所未確認のスーパー",
            lat=None,
            lon=None,
            importance_weight=0.25,
        )
    ]

    diagnosis = run_life_diagnosis(fixture)

    assert diagnosis.item_results[0].status == FeasibilityStatus.UNKNOWN
    assert diagnosis.data_quality_warnings
    assert diagnosis.item_results[0].warnings
    assert "判定不能" in diagnosis.summary_ja


def test_score_aggregation_uses_default_category_weights() -> None:
    weighted_score = calculate_life_score(
        {
            DestinationCategory.SUPERMARKET: FeasibilityStatus.OK,
            DestinationCategory.HOSPITAL: FeasibilityStatus.CAUTION,
            DestinationCategory.PHARMACY: FeasibilityStatus.OK,
            DestinationCategory.CITY_HALL: FeasibilityStatus.SUPPORT_NEEDED,
            DestinationCategory.STATION: FeasibilityStatus.CAUTION,
            DestinationCategory.SOCIAL: FeasibilityStatus.CAUTION,
        }
    )

    assert weighted_score == pytest.approx(75.0)
