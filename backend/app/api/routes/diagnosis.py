from fastapi import APIRouter

from app.domain.models import DiagnosisRequest, LifeDiagnosis
from app.services.diagnosis.engine import run_life_diagnosis

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


@router.post("/run", response_model=LifeDiagnosis)
def run_diagnosis(request: DiagnosisRequest) -> LifeDiagnosis:
    return run_life_diagnosis(request)
