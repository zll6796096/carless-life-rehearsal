from fastapi import APIRouter

from app.domain.models import DataQualityReport
from app.services.data_quality.service import build_data_quality_report

router = APIRouter(tags=["data-quality"])


@router.get("/data-quality", response_model=DataQualityReport)
def get_data_quality() -> DataQualityReport:
    return build_data_quality_report(gtfs_root=None, validator_json_path=None)
