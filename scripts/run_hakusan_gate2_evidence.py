"""Run with backend/.venv/bin/python against the verified local Gate 1 graph."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from scripts.run_hakusan_otp_evidence import (  # noqa: E402
    ROUTES_QUERY,
    STOPS_QUERY,
    _graphql_post,
    validate_route_inventory,
    validate_stop_inventory,
    write_json_atomic,
)

from app.core.config import get_settings  # noqa: E402
from app.domain.models import DiagnosisRequest  # noqa: E402
from app.main import app  # noqa: E402
from app.services.routing.provider import get_routing_provider  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/hakusan/gate2-validation-summary.json"
    )
    args = parser.parse_args()
    gate1 = json.loads((ROOT / "data/hakusan/otp-validation-summary.json").read_text())
    graph_sha = hashlib.sha256(args.graph.read_bytes()).hexdigest()
    if graph_sha != gate1["inputs"]["graph_sha256"]:
        raise RuntimeError("graph differs from Gate 1 evidence")
    sources = json.loads((ROOT / "data/hakusan/otp-sources.json").read_text())
    places = json.loads((ROOT / "data/hakusan/destinations.json").read_text())
    endpoint = "http://127.0.0.1:18081/otp/gtfs/v1"
    allowed = set(gate1["inventory"]["route_ids"])
    errors = validate_route_inventory(_graphql_post(endpoint, ROUTES_QUERY), allowed)
    errors += validate_stop_inventory(
        _graphql_post(endpoint, STOPS_QUERY), set(gate1["inventory"]["required_access_stop_ids"])
    )
    if errors:
        raise RuntimeError(errors)
    os.environ["ROUTING_PROVIDER"] = "otp"
    os.environ["OTP_GRAPHQL_URL"] = endpoint
    os.environ["OTP_ROUTE_RULES_PATH"] = str(ROOT / "data/hakusan/route-rules.json")
    get_settings.cache_clear()
    origin = sources["scenario"]["origin"]
    data = {
        "home_location": {
            "name": origin["label"],
            "address": "公開テスト地点",
            "lat": origin["lat"],
            "lon": origin["lon"],
        },
        "destinations": [
            {
                "id": p["id"],
                "name": p["name_ja"],
                "category": p["category"],
                **p["location"],
                "importance_weight": 1 / 6,
            }
            for p in places["destinations"]
        ],
        "mobility_profile": {
            "walk_minutes": 15,
            "max_transfers": 1,
            "max_wait_minutes": 30,
            "avoid_stairs": True,
        },
        "outbound_departure": "2026-09-08T06:50:00+09:00",
        "return_departure": "2026-09-08T11:00:00+09:00",
    }
    request = DiagnosisRequest(**data)
    provider = get_routing_provider()
    results = []
    for destination in request.destinations:
        row = {"destination_id": destination.id, "category": destination.category.value}
        for direction, departure in [
            ("outbound", data["outbound_departure"]),
            ("return", data["return_departure"]),
        ]:
            plan = provider.plan_trip(
                origin=request.home_location,
                destination=destination,
                departure_time=departure,
                profile=request.selected_mobility_profile,
                direction=direction,
            )
            row[direction] = {
                "available": plan.available,
                "provider": plan.provider,
                "duration_minutes": plan.duration_minutes,
                "walk_minutes": plan.walk_minutes,
                "modes": [leg.mode for leg in plan.legs],
                "accessibility_verified": plan.accessibility_verified,
            }
        results.append(row)
    with TestClient(app) as client:
        response = client.post("/diagnosis/run", json=data)
        response.raise_for_status()
        diagnosis = response.json()
        if diagnosis["data_source"] != "routing_provider" or len(diagnosis["item_results"]) != 6:
            raise RuntimeError("diagnosis did not use all six live destinations")
        if any(item["status"] == "unknown" for item in diagnosis["item_results"]):
            raise RuntimeError("live API diagnosis has unknown destinations")
        missing = dict(data)
        missing.pop("outbound_departure")
        missing.pop("return_departure")
        missing_result = client.post("/diagnosis/run", json=missing).json()
    if not all(item["status"] == "unknown" for item in missing_result["item_results"]):
        raise RuntimeError("missing dates did not fail closed")
    available = sum(r[d]["available"] for r in results for d in ("outbound", "return"))
    summary = {
        "schema_version": 1,
        "status": "PASS" if available == 12 else "PARTIAL",
        "graph_sha256": graph_sha,
        "available_journeys": available,
        "expected_journeys": 12,
        "results": results,
        "diagnosis_statuses": {i["category"]: i["status"] for i in diagnosis["item_results"]},
        "missing_dates_unknown": True,
        "realtime": False,
        "outbound_departure": data["outbound_departure"],
        "return_departure": data["return_departure"],
        "origin": data["home_location"],
        "profile": data["mobility_profile"],
        "diagnosis_data_confidence": diagnosis["data_confidence"],
        "limitations": [
            "Destination coordinates are stop/POI proxies, not verified entrances",
            "Stair-free accessibility remains unverified",
        ],
    }
    write_json_atomic(args.output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if available == 12 else 1


if __name__ == "__main__":
    raise SystemExit(main())
