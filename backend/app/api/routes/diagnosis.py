from datetime import timedelta, timezone

from fastapi import APIRouter, HTTPException

from app.domain.models import DiagnosisRequest, LifeDiagnosis
from app.fixtures.hakusan import build_hakusan_fixture
from app.services.diagnosis.engine import run_life_diagnosis

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


@router.post("/run", response_model=LifeDiagnosis)
def run_diagnosis(request: DiagnosisRequest) -> LifeDiagnosis:
    if request.data_profile == "hakusan":
        pilot = build_hakusan_fixture()["pilot"]
        for departure in (request.outbound_departure, request.return_departure):
            if departure is None:
                raise HTTPException(422, "Explicit outbound and return departures required")
            day = departure.astimezone(timezone(timedelta(hours=9))).date().isoformat()
            if not pilot["service_start"] <= day <= pilot["service_end"]:
                raise HTTPException(422, "Departure outside the pilot service period")
        if request.mock_transport_results:
            raise HTTPException(422, "Pilot does not accept mock journeys")
    return run_life_diagnosis(request)
