from fastapi.testclient import TestClient

from app.domain.models import DestinationCategory, FeasibilityStatus
from app.fixtures.demo import build_demo_fixture
from app.main import app
from app.services.diagnosis.engine import run_life_diagnosis
from app.services.rehearsal.engine import generate_rehearsal_tasks


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
