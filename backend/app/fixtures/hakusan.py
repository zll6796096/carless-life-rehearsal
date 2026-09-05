"""Public pilot inputs, never a substitute for real routing."""

import json
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_settings
from app.domain.models import DemoFixture

DATA = Path(__file__).resolve().parents[3] / "data/hakusan"


def require_hakusan_routing() -> None:
    settings = get_settings()
    if settings.routing_provider != "otp" or not settings.otp_graphql_url:
        raise HTTPException(503, "Hakusan pilot requires configured OTP routing")


def build_hakusan_fixture() -> dict:
    require_hakusan_routing()
    manifest = json.loads((DATA / "manifest.json").read_text())
    origin = json.loads((DATA / "otp-sources.json").read_text())["scenario"]["origin"]
    places = json.loads((DATA / "destinations.json").read_text())["destinations"]
    fixture = DemoFixture(
        home_location={
            "name": origin["label"],
            "address": "公開テスト地点（自宅ではありません）",
            "lat": origin["lat"],
            "lon": origin["lon"],
        },
        destinations=[
            {
                "id": p["id"],
                "name": p["name_ja"],
                "category": p["category"],
                **p["location"],
                "importance_weight": 1 / len(places),
            }
            for p in places
        ],
        default_mobility_profile={"walk_minutes": 15, "max_transfers": 1, "max_wait_minutes": 30},
        time_windows=[],
    ).model_dump(mode="json")
    artifact = manifest["feed"]["artifact"]
    return {
        **fixture,
        "data_profile": "hakusan",
        "pilot": {
            "service_start": artifact["service_start_date"],
            "service_end": artifact["service_end_date"],
            "attribution": list(manifest["attribution"].values()),
            "source_url": manifest["feed"]["source_page_url"],
        },
    }
