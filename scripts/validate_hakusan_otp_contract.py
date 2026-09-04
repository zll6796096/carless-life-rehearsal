#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any


OTP_URL = (
    "https://github.com/opentripplanner/OpenTripPlanner/releases/download/"
    "v2.9.0/otp-shaded-2.9.0.jar"
)
OTP_SHA256 = "112824122cd1a89e2dff6b5b3088ffbd4f04c3c0a400ca9f08f17b762f5325f6"
GTFS_UID = "765cd548-a1f3-46e6-b05b-d6168b9b85d1"
GTFS_SHA256 = "ea1a0108c4a7f24215aa1b3811a267d85abf9777a356b8c7b3ff857edbcae740"
OSM_QUERY_SHA256 = "76f960f09572b668beebfb54b38718b2ed0822e860258692fd15986c97ba1990"
OSM_CANONICAL_SHA256 = "81989628fee073e360aa390c718151af12456fdb66c752055e1d7b38e3b437df"
BUILD_CONFIG_SHA256 = "0e0e3c3f49f72ef026386001f680eab1f1445b1312f2a8d7dad5c3287968aacd"
ROUTER_CONFIG_SHA256 = "d5b21f29f847303b6e7ecef50e6b05bf8a101a5971cf2e466dd3b60c15711b41"

QUERY_PATH = "config/otp/hakusan/osm-overpass.ql"
BUILD_CONFIG_PATH = "config/otp/hakusan/build-config.json"
ROUTER_CONFIG_PATH = "config/otp/hakusan/router-config.json"
HISTORICAL_TIMESTAMP = "2026-09-03T00:00:00Z"
APPROVED_BBOX = {
    "south": 36.44917,
    "west": 136.4535465,
    "north": 36.58471,
    "east": 136.622339,
}
EXPECTED_COUNTS = {
    "route_count": 11,
    "trip_count": 115,
    "stop_time_count": 2867,
    "stop_count": 205,
}
EXPECTED_BUILD_CONFIG = {
    "configVersion": "hakusan-gate1-v1",
    "dataImportReport": True,
    "transitServiceStart": "2026-03-16",
    "transitServiceEnd": "2027-03-15",
}
EXPECTED_ROUTER_CONFIG = {"configVersion": "hakusan-gate1-v1"}
EXPECTED_ORIGIN = {
    "label": "松任駅西側の住宅地テスト地点",
    "lat": 36.52725,
    "lon": 136.5605,
}

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot read {label}: {error}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return payload


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _expect(
    errors: list[str],
    actual: Any,
    expected: Any,
    message: str,
) -> None:
    if actual != expected:
        errors.append(message)


def _check_sha(errors: list[str], value: Any, label: str) -> None:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        errors.append(f"{label} sha256 must be lowercase hexadecimal")


def _tracked_path(repo_root: Path, relative_path: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        errors.append(f"{label} path is missing")
        return None
    root = repo_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{label} path escapes repository root")
        return None
    return candidate


def _validate_hashed_file(
    repo_root: Path,
    relative_path: Any,
    expected_path: str,
    declared_sha: Any,
    expected_sha: str,
    label: str,
    errors: list[str],
) -> Path | None:
    _expect(errors, relative_path, expected_path, f"{label} path mismatch")
    _check_sha(errors, declared_sha, label)
    _expect(errors, declared_sha, expected_sha, f"{label} sha256 must pin approved bytes")
    path = _tracked_path(repo_root, relative_path, label, errors)
    if path is None:
        return None
    if not path.is_file():
        errors.append(f"{label} file is missing")
        return None
    if _sha256(path) != declared_sha:
        errors.append(f"{label} sha256 mismatch")
    return path


def _validate_configs(repo_root: Path, sources: dict[str, Any], errors: list[str]) -> None:
    build_path = _validate_hashed_file(
        repo_root,
        _nested(sources, "config", "build_config_path"),
        BUILD_CONFIG_PATH,
        _nested(sources, "config", "build_config_sha256"),
        BUILD_CONFIG_SHA256,
        "OTP build-config",
        errors,
    )
    router_path = _validate_hashed_file(
        repo_root,
        _nested(sources, "config", "router_config_path"),
        ROUTER_CONFIG_PATH,
        _nested(sources, "config", "router_config_sha256"),
        ROUTER_CONFIG_SHA256,
        "OTP router-config",
        errors,
    )
    if build_path is not None:
        build_config = _load_json(build_path, "OTP build-config", errors)
        if build_config is not None and build_config != EXPECTED_BUILD_CONFIG:
            errors.append("OTP build-config content mismatch")
    if router_path is not None:
        router_config = _load_json(router_path, "OTP router-config", errors)
        if router_config is not None and router_config != EXPECTED_ROUTER_CONFIG:
            errors.append("OTP router-config content mismatch")


def _validate_osm(repo_root: Path, sources: dict[str, Any], errors: list[str]) -> None:
    query_path = _validate_hashed_file(
        repo_root,
        _nested(sources, "osm", "query_path"),
        QUERY_PATH,
        _nested(sources, "osm", "query_sha256"),
        OSM_QUERY_SHA256,
        "OSM query",
        errors,
    )
    query = ""
    if query_path is not None:
        try:
            query = query_path.read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"cannot read OSM query: {error}")
    timestamp = _nested(sources, "osm", "historical_timestamp")
    _expect(
        errors,
        timestamp,
        HISTORICAL_TIMESTAMP,
        "OSM historical timestamp must be 2026-09-03T00:00:00Z",
    )
    if f'[date:"{HISTORICAL_TIMESTAMP}"]' not in query:
        errors.append("OSM query must pin historical timestamp")
    _expect(errors, _nested(sources, "osm", "bbox"), APPROVED_BBOX, "OSM bbox mismatch")
    approved_bbox_text = "[bbox:36.44917,136.4535465,36.58471,136.6223390]"
    if approved_bbox_text not in query:
        errors.append("OSM query must pin approved bbox")
    if 'way["highway"]' not in query or 'relation["type"="restriction"]' not in query:
        errors.append("OSM query must include highways and restriction relations")

    _expect(
        errors,
        _nested(sources, "osm", "endpoint"),
        "https://overpass-api.de/api/interpreter",
        "OSM endpoint mismatch",
    )
    _expect(
        errors,
        _nested(sources, "osm", "canonical_filename"),
        "hakusan-20260903-canonical.osm",
        "OSM canonical filename mismatch",
    )
    canonical_sha = _nested(sources, "osm", "canonical_sha256")
    _check_sha(errors, canonical_sha, "OSM canonical")
    _expect(
        errors,
        canonical_sha,
        OSM_CANONICAL_SHA256,
        "OSM canonical sha256 must pin approved snapshot",
    )
    _expect(
        errors,
        _nested(sources, "osm", "canonical_size_bytes"),
        14815819,
        "OSM canonical size mismatch",
    )
    _expect(
        errors,
        _nested(sources, "osm", "license", "spdx_id"),
        "ODbL-1.0",
        "OSM license SPDX identifier must be ODbL-1.0",
    )
    _expect(
        errors,
        _nested(sources, "osm", "license", "url"),
        "https://opendatacommons.org/licenses/odbl/1-0/",
        "OSM license URL must pin ODbL 1.0",
    )


def _validate_gtfs(repo_root: Path, sources: dict[str, Any], errors: list[str]) -> None:
    manifest = _load_json(repo_root / "data" / "hakusan" / "manifest.json", "Hakusan manifest", errors)
    route_rules = _load_json(
        repo_root / "data" / "hakusan" / "route-rules.json",
        "Hakusan route rules",
        errors,
    )
    _expect(errors, _nested(sources, "gtfs", "source_uid"), GTFS_UID, "GTFS source UID mismatch")
    source_sha = _nested(sources, "gtfs", "source_sha256")
    _check_sha(errors, source_sha, "GTFS source")
    _expect(errors, source_sha, GTFS_SHA256, "GTFS source sha256 mismatch")
    pilot_filename = _nested(sources, "gtfs", "pilot_filename")
    _expect(
        errors,
        pilot_filename,
        "hakusan-meguru-fixed-routes-gtfs.zip",
        "GTFS pilot filename mismatch",
    )
    if not isinstance(pilot_filename, str) or "gtfs" not in pilot_filename.lower():
        errors.append("GTFS pilot filename must contain gtfs")
    for key, expected in EXPECTED_COUNTS.items():
        _expect(
            errors,
            _nested(sources, "gtfs", "expected", key),
            expected,
            f"GTFS expected {key} must be {expected}",
        )
    if manifest is not None:
        _expect(
            errors,
            _nested(manifest, "feed", "artifact", "uid"),
            GTFS_UID,
            "Hakusan manifest GTFS UID mismatch",
        )
        _expect(
            errors,
            _nested(manifest, "feed", "artifact", "sha256"),
            GTFS_SHA256,
            "Hakusan manifest GTFS sha256 mismatch",
        )
    if route_rules is not None:
        allowed_routes = route_rules.get("allowed_routes")
        if not isinstance(allowed_routes, list) or len(allowed_routes) != EXPECTED_COUNTS["route_count"]:
            errors.append("Hakusan route policy must contain 11 allowed routes")
        if route_rules.get("default_policy") != "deny":
            errors.append("Hakusan route policy must be deny-by-default")


def _validate_runtime_and_scenario(
    repo_root: Path,
    sources: dict[str, Any],
    errors: list[str],
) -> None:
    _expect(errors, _nested(sources, "runtime", "host"), "127.0.0.1", "OTP host must be loopback")
    _expect(errors, _nested(sources, "runtime", "port"), 18081, "OTP local port must be 18081")
    _expect(
        errors,
        _nested(sources, "runtime", "graphql_endpoint_path"),
        "/otp/gtfs/v1",
        "OTP GraphQL endpoint path must be /otp/gtfs/v1",
    )
    _expect(errors, _nested(sources, "runtime", "max_heap_mb"), 2048, "OTP heap cap must be 2048 MiB")
    timeout = _nested(sources, "runtime", "startup_timeout_seconds")
    if not isinstance(timeout, int) or not 1 <= timeout <= 180:
        errors.append("OTP startup timeout must be between 1 and 180 seconds")

    _expect(
        errors,
        _nested(sources, "scenario", "service_date"),
        "2026-09-08",
        "scenario service date must be 2026-09-08",
    )
    _expect(
        errors,
        _nested(sources, "scenario", "outbound_time"),
        "06:50:00+09:00",
        "scenario outbound time must be 06:50:00+09:00",
    )
    _expect(
        errors,
        _nested(sources, "scenario", "return_time"),
        "11:00:00+09:00",
        "scenario return time must be 11:00:00+09:00",
    )
    _expect(
        errors,
        _nested(sources, "scenario", "origin"),
        EXPECTED_ORIGIN,
        "scenario residential origin mismatch",
    )
    destination_id = _nested(sources, "scenario", "destination_id")
    _expect(
        errors,
        destination_id,
        "hospital-matto-ishikawa-chuo",
        "scenario destination must be the hospital",
    )
    destinations = _load_json(
        repo_root / "data" / "hakusan" / "destinations.json",
        "Hakusan destinations",
        errors,
    )
    if destinations is not None:
        ids = {
            destination.get("id")
            for destination in destinations.get("destinations", [])
            if isinstance(destination, dict)
        }
        if destination_id not in ids:
            errors.append("scenario destination is missing from Hakusan destinations")

    service_date = _nested(sources, "scenario", "service_date")
    if isinstance(service_date, str):
        try:
            if date.fromisoformat(service_date).weekday() != 1:
                errors.append("scenario service date must be a Tuesday")
        except ValueError:
            errors.append("scenario service date must be ISO-8601")


def validate_otp_contract(repo_root: Path) -> list[str]:
    """Return all committed source/config contract errors."""

    errors: list[str] = []
    sources = _load_json(
        repo_root / "data" / "hakusan" / "otp-sources.json",
        "Hakusan OTP source contract",
        errors,
    )
    if sources is None:
        return errors

    _expect(errors, sources.get("schema_version"), 1, "OTP source schema_version must be 1")
    _expect(
        errors,
        sources.get("contract_id"),
        "hakusan-otp-gate1-v1",
        "OTP contract_id mismatch",
    )
    _expect(errors, _nested(sources, "otp", "version"), "2.9.0", "OTP version must be 2.9.0")
    _expect(errors, _nested(sources, "otp", "artifact_url"), OTP_URL, "OTP artifact URL must pin v2.9.0")
    _expect(
        errors,
        _nested(sources, "otp", "artifact_filename"),
        "otp-shaded-2.9.0.jar",
        "OTP artifact filename mismatch",
    )
    otp_sha = _nested(sources, "otp", "sha256")
    _check_sha(errors, otp_sha, "OTP artifact")
    _expect(errors, otp_sha, OTP_SHA256, "OTP artifact sha256 mismatch")
    _expect(
        errors,
        _nested(sources, "otp", "size_bytes"),
        183261367,
        "OTP artifact size mismatch",
    )
    _expect(errors, _nested(sources, "otp", "java_major"), 25, "OTP Java major must be 25")

    _validate_gtfs(repo_root, sources, errors)
    _validate_osm(repo_root, sources, errors)
    _validate_configs(repo_root, sources, errors)
    _validate_runtime_and_scenario(repo_root, sources, errors)
    return list(dict.fromkeys(errors))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the committed Hakusan OTP contract")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_otp_contract(args.repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Hakusan OTP source contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
