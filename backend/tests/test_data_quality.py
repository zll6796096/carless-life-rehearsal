from fastapi.testclient import TestClient

from app.main import app
from app.services.data_quality.service import build_data_quality_report


def test_data_quality_returns_warning_when_no_gtfs_data_present() -> None:
    report = build_data_quality_report(gtfs_root=None, validator_json_path=None)

    assert report.level == "unknown"
    assert report.warnings
    assert report.warnings[0].code == "gtfs_data_absent"


def test_data_quality_endpoint_returns_warnings_without_crashing() -> None:
    client = TestClient(app)

    response = client.get("/data-quality")

    assert response.status_code == 200
    payload = response.json()
    assert payload["level"] == "unknown"
    assert payload["warnings"]
    assert payload["feed_summary"]
