from fastapi.testclient import TestClient

from app.domain.models import DestinationCategory, FeasibilityStatus
from app.fixtures.demo import build_demo_fixture
from app.main import app
from app.services.diagnosis.engine import run_life_diagnosis
from app.services.rehearsal.engine import generate_rehearsal_tasks


def real_diagnosis_payload():
    payload = run_life_diagnosis(build_demo_fixture()).model_dump(mode="json")
    payload.update(
        data_source="routing_provider",
        origin_label="公開テスト地点",
        outbound_departure="2026-09-08T06:50:00+09:00",
        return_departure="2026-09-08T11:00:00+09:00",
    )
    return payload


def test_real_rehearsals_keep_dates_in_all_channels():
    client = TestClient(app)
    payload = real_diagnosis_payload()
    response = client.post("/rehearsals/generate", json=payload)
    assert response.status_code == 200
    tasks = response.json()["tasks"]
    eligible = [i for i in payload["item_results"] if i["status"] != "unknown"]
    assert len(tasks) == len(eligible)
    for task in tasks:
        assert task["outbound_departure"] == payload["outbound_departure"]
        assert task["return_departure"] == payload["return_departure"]
        for field in ("memo_ja", "voice_script_ja", "family_share_text_ja"):
            assert "2026-09-08 06:50" in task[field]
            assert "2026-09-08 11:00" in task[field]
            assert "10時ごろ" not in task[field]
            assert "公開テスト地点" in task[field]
        assert "次の便を待つ" not in task["missed_connection_ja"]


def test_real_rehearsals_reject_missing_or_reversed_dates():
    client = TestClient(app)
    for changes in (
        {"outbound_departure": None},
        {"return_departure": None},
        {"outbound_departure": "2026-09-08T06:50:00"},
        {"return_departure": "2026-09-08T06:00:00+09:00"},
    ):
        assert (
            client.post(
                "/rehearsals/generate", json={**real_diagnosis_payload(), **changes}
            ).status_code
            == 422
        )


def test_unknown_routes_do_not_create_real_rehearsals():
    payload = real_diagnosis_payload()
    for item in payload["item_results"]:
        item["status"] = "unknown"
    assert TestClient(app).post("/rehearsals/generate", json=payload).json()["tasks"] == []


def test_generate_rehearsal_tasks_prefers_easy_destinations() -> None:
    diagnosis = run_life_diagnosis(build_demo_fixture())

    tasks = generate_rehearsal_tasks(diagnosis)

    assert 1 <= len(tasks) <= 3
    assert tasks[0].destination_category in {
        DestinationCategory.SUPERMARKET,
        DestinationCategory.PHARMACY,
    }
    for task in tasks:
        assert task.title_ja
        assert task.memo_ja
        assert task.voice_script_ja
        assert task.family_share_text_ja
        assert "GTFS" not in task.memo_ja


def test_support_needed_rehearsal_is_framed_with_family_or_supporter() -> None:
    diagnosis = run_life_diagnosis(build_demo_fixture())
    diagnosis.item_results = [
        item
        for item in diagnosis.item_results
        if item.destination_category == DestinationCategory.CITY_HALL
    ]

    tasks = generate_rehearsal_tasks(diagnosis)

    assert tasks
    assert tasks[0].source_status == FeasibilityStatus.SUPPORT_NEEDED
    assert "家族" in tasks[0].title_ja or "支援者" in tasks[0].title_ja
    assert "一人で無理をしない" in tasks[0].voice_script_ja


def test_rehearsal_api_stores_and_reads_task() -> None:
    client = TestClient(app)
    fixture = client.get("/fixtures/demo").json()
    diagnosis = client.post("/diagnosis/run", json=fixture).json()

    generate_response = client.post("/rehearsals/generate", json=diagnosis)

    assert generate_response.status_code == 200
    tasks = generate_response.json()["tasks"]
    assert 1 <= len(tasks) <= 3

    read_response = client.get(f"/rehearsals/{tasks[0]['id']}")
    assert read_response.status_code == 200
    assert read_response.json()["id"] == tasks[0]["id"]
