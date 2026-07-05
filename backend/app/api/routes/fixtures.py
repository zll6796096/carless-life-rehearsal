from fastapi import APIRouter

from app.domain.models import DemoFixture
from app.fixtures.demo import build_demo_fixture

router = APIRouter(prefix="/fixtures", tags=["fixtures"])


@router.get("/demo", response_model=DemoFixture)
def get_demo_fixture() -> DemoFixture:
    return build_demo_fixture()
