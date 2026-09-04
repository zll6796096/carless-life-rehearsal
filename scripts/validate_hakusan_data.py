from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import uuid
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_ROOT = REPO_ROOT / "data" / "hakusan"
CONTRACT_FILES = (
    "manifest.json",
    "destinations.json",
    "route-rules.json",
    "validation-summary.json",
)
REQUIRED_CATEGORIES = {
    "supermarket",
    "hospital",
    "pharmacy",
    "city_hall",
    "station",
    "social",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def _load_contracts(contract_root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    contracts: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for filename in CONTRACT_FILES:
        path = contract_root / filename
        if not path.is_file():
            errors.append(f"missing contract file: {filename}")
            continue
        try:
            contracts[filename] = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid contract file {filename}: {exc}")
    return contracts, errors


def _is_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except ValueError:
        return False


def _parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _is_https_url(value: object) -> bool:
    return isinstance(value, str) and value.startswith("https://")


def _route_ids(routes: object) -> list[str]:
    if not isinstance(routes, list):
        return []
    return [
        route.get("route_id")
        for route in routes
        if isinstance(route, dict) and isinstance(route.get("route_id"), str)
    ]


def validate_contract(contract_root: Path) -> list[str]:
    contracts, errors = _load_contracts(contract_root)
    if errors:
        return errors

    manifest = contracts["manifest.json"]
    destinations = contracts["destinations.json"]
    rules = contracts["route-rules.json"]
    validation = contracts["validation-summary.json"]

    for filename, payload in contracts.items():
        if payload.get("schema_version") != 1:
            errors.append(f"{filename} schema_version must be 1")

    feed = manifest.get("feed") if isinstance(manifest.get("feed"), dict) else {}
    artifact = feed.get("artifact") if isinstance(feed.get("artifact"), dict) else {}
    license_info = feed.get("license") if isinstance(feed.get("license"), dict) else {}
    uid = artifact.get("uid")
    digest = artifact.get("sha256")
    if not _is_uuid(uid):
        errors.append("manifest feed.artifact.uid must be a UUID")
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        errors.append("manifest feed.artifact.sha256 must be 64 lowercase hex characters")
    download_url = artifact.get("download_url")
    if (
        not isinstance(download_url, str)
        or not isinstance(uid, str)
        or f"uid={uid}" not in download_url
    ):
        errors.append("manifest download_url must pin feed.artifact.uid")
    if (
        license_info.get("name") != "CC BY 4.0"
        or license_info.get("spdx_id") != "CC-BY-4.0"
    ):
        errors.append("manifest feed license must be CC BY 4.0 / CC-BY-4.0")
    if not _is_https_url(feed.get("repository_metadata_url")) or not _is_https_url(
        feed.get("source_page_url")
    ):
        errors.append("manifest feed requires repository and source page URLs")
    if not _is_https_url(license_info.get("url")):
        errors.append("manifest feed license requires an HTTPS URL")
    realtime = feed.get("realtime") if isinstance(feed.get("realtime"), dict) else {}
    if realtime.get("available") is not False:
        errors.append("manifest must identify this feed as static-only")

    start_date = _parse_iso_date(artifact.get("service_start_date"))
    end_date = _parse_iso_date(artifact.get("service_end_date"))
    contest = manifest.get("contest") if isinstance(manifest.get("contest"), dict) else {}
    contest_end = _parse_iso_date(contest.get("contest_end_date"))
    if start_date is None or end_date is None or start_date > end_date:
        errors.append("manifest service dates must be valid ISO dates in ascending order")
    if end_date is None or contest_end is None or end_date < contest_end:
        errors.append("manifest service_end_date must cover the contest end date")

    required_files = artifact.get("required_files")
    if not isinstance(required_files, list) or not all(
        isinstance(filename, str) and filename.endswith(".txt") for filename in required_files
    ):
        errors.append("manifest required_files must be a list of GTFS .txt filenames")

    if validation.get("feed_uid") != uid:
        errors.append("validation-summary feed_uid must match manifest")
    if validation.get("archive_sha256") != digest:
        errors.append("validation-summary archive_sha256 must match manifest")
    if validation.get("error_count") != 0:
        errors.append("validation-summary error_count must be zero")
    validator = validation.get("validator") if isinstance(validation.get("validator"), dict) else {}
    manifest_validator = (
        manifest.get("validation") if isinstance(manifest.get("validation"), dict) else {}
    )
    if validator.get("version") != manifest_validator.get("validator_version"):
        errors.append("validation-summary validator version must match manifest")
    notice_total = sum(
        item.get("count", 0)
        for item in validation.get("notices", [])
        if isinstance(item, dict) and item.get("severity") == "WARNING"
    )
    if validation.get("warning_count") != notice_total:
        errors.append("validation-summary warning_count must equal WARNING notice totals")

    required_categories = destinations.get("required_categories")
    if not isinstance(required_categories, list) or set(required_categories) != REQUIRED_CATEGORIES:
        errors.append("destinations required_categories must contain the six product categories")
    destination_items = destinations.get("destinations")
    if not isinstance(destination_items, list):
        errors.append("destinations destinations must be a list")
        destination_items = []
    category_values = [
        item.get("category") for item in destination_items if isinstance(item, dict)
    ]
    if (
        len(destination_items) != len(REQUIRED_CATEGORIES)
        or set(category_values) != REQUIRED_CATEGORIES
    ):
        errors.append("destinations must define exactly one entry for each required category")
    destination_ids = [item.get("id") for item in destination_items if isinstance(item, dict)]
    if len(destination_ids) != len(set(destination_ids)):
        errors.append("destination ids must be unique")

    for item in destination_items:
        if not isinstance(item, dict):
            errors.append("each destination must be a JSON object")
            continue
        destination_id = str(item.get("id") or "<missing>")
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        lat = location.get("lat")
        lon = location.get("lon")
        if not isinstance(lat, (int, float)) or not -90 <= lat <= 90:
            errors.append(f"destination {destination_id} requires a valid latitude")
        if not isinstance(lon, (int, float)) or not -180 <= lon <= 180:
            errors.append(f"destination {destination_id} requires a valid longitude")
        access_stop_ids = item.get("access_stop_ids")
        if not isinstance(access_stop_ids, list) or not access_stop_ids or not all(
            isinstance(stop_id, str) and stop_id for stop_id in access_stop_ids
        ):
            errors.append(f"destination {destination_id} requires access_stop_ids")

        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        source_type = source.get("type")
        if source_type == "gtfs_stop":
            if source.get("feed_uid") != uid:
                errors.append(f"destination {destination_id} GTFS source must pin the feed UID")
            if source.get("stop_id") not in (access_stop_ids or []):
                errors.append(
                    f"destination {destination_id} GTFS source stop must be an access stop"
                )
            if source.get("license") != "CC-BY-4.0" or not source.get("url"):
                errors.append(
                    f"destination {destination_id} GTFS source requires CC-BY-4.0 and URL"
                )
        elif source_type == "openstreetmap":
            if not isinstance(source.get("element_id"), int):
                errors.append(
                    f"destination {destination_id} OSM source requires integer element_id"
                )
            if source.get("element_type") not in {"node", "way", "relation"}:
                errors.append(f"destination {destination_id} OSM source requires element_type")
            if not isinstance(source.get("element_version"), int) or not source.get(
                "element_timestamp"
            ):
                errors.append(
                    f"destination {destination_id} OSM source requires version and timestamp"
                )
            if source.get("license") != "ODbL-1.0" or not _is_https_url(source.get("url")):
                errors.append(
                    f"destination {destination_id} OSM source requires ODbL-1.0 and URL"
                )
            if not _is_https_url(source.get("license_url")):
                errors.append(
                    f"destination {destination_id} OSM source requires an ODbL URL"
                )
            if not source.get("snapshot_at"):
                errors.append(f"destination {destination_id} OSM source requires snapshot_at")
        else:
            errors.append(f"destination {destination_id} has unsupported source type")

    if rules.get("default_policy") != "deny":
        errors.append("route-rules default_policy must be 'deny'")
    allowed_routes = rules.get("allowed_routes")
    excluded_routes = rules.get("excluded_routes")
    allowed_ids = _route_ids(allowed_routes)
    excluded_ids = _route_ids(excluded_routes)
    if len(allowed_ids) != len(set(allowed_ids)) or len(excluded_ids) != len(
        set(excluded_ids)
    ):
        errors.append("route ids must be unique within each policy list")
    if set(allowed_ids) & set(excluded_ids):
        errors.append("allowed and excluded route ids must not overlap")
    expected_count = rules.get("expected_feed_route_count")
    if (
        not isinstance(expected_count, int)
        or len(set(allowed_ids + excluded_ids)) != expected_count
    ):
        errors.append("route policy must classify every expected feed route")
    for route in allowed_routes if isinstance(allowed_routes, list) else []:
        if not isinstance(route, dict) or route.get("service_type") != "fixed_route":
            errors.append("every allowed route must be classified as fixed_route")
    valid_reasons = {"outside_pilot_area", "reservation_required"}
    reservation_count = 0
    for route in excluded_routes if isinstance(excluded_routes, list) else []:
        if not isinstance(route, dict) or route.get("reason_code") not in valid_reasons:
            errors.append("every excluded route must have an approved reason_code")
            continue
        if route.get("reason_code") == "reservation_required":
            reservation_count += 1
            if "予約が必要" not in str(route.get("user_message_ja") or ""):
                errors.append("reservation routes must show a reservation-required message")
    if reservation_count == 0:
        errors.append("route policy must identify reservation-required routes")
    reservation_source = (
        rules.get("reservation_source")
        if isinstance(rules.get("reservation_source"), dict)
        else {}
    )
    if not reservation_source.get("url") or not reservation_source.get("checked_at"):
        errors.append("route policy requires an auditable reservation source")

    return errors


def _read_csv(archive: zipfile.ZipFile, filename: str) -> list[dict[str, str]]:
    text = archive.read(filename).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _normalise_gtfs_date(value: str | None) -> str | None:
    if value is None or len(value) != 8 or not value.isdigit():
        return value
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def verify_gtfs_archive(contract_root: Path, archive_path: Path) -> list[str]:
    contracts, errors = _load_contracts(contract_root)
    if errors:
        return errors
    manifest = contracts["manifest.json"]
    destinations = contracts["destinations.json"]
    rules = contracts["route-rules.json"]
    artifact = manifest["feed"]["artifact"]

    if not archive_path.is_file():
        return [f"GTFS archive not found: {archive_path}"]
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if digest != artifact["sha256"]:
        errors.append("GTFS archive sha256 does not match manifest")

    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            for filename in artifact["required_files"]:
                if filename not in names:
                    errors.append(f"GTFS archive missing required file: {filename}")
            if errors:
                return errors

            feed_rows = _read_csv(archive, "feed_info.txt")
            if len(feed_rows) != 1:
                errors.append("GTFS feed_info.txt must contain exactly one data row")
            else:
                feed_info = feed_rows[0]
                if _normalise_gtfs_date(feed_info.get("feed_start_date")) != artifact[
                    "service_start_date"
                ]:
                    errors.append("GTFS feed_start_date does not match manifest")
                if _normalise_gtfs_date(feed_info.get("feed_end_date")) != artifact[
                    "service_end_date"
                ]:
                    errors.append("GTFS feed_end_date does not match manifest")
                if feed_info.get("feed_version") != artifact["feed_version"]:
                    errors.append("GTFS feed_version does not match manifest")

            actual_route_ids = {row.get("route_id") for row in _read_csv(archive, "routes.txt")}
            expected_route_ids = set(
                _route_ids(rules["allowed_routes"]) + _route_ids(rules["excluded_routes"])
            )
            for route_id in sorted(expected_route_ids - actual_route_ids):
                errors.append(f"GTFS routes.txt missing classified route: {route_id}")
            for route_id in sorted(actual_route_ids - expected_route_ids):
                errors.append(f"GTFS routes.txt contains unclassified route: {route_id}")

            trips = {
                row.get("trip_id"): row.get("route_id")
                for row in _read_csv(archive, "trips.txt")
            }
            allowed_route_ids = set(_route_ids(rules["allowed_routes"]))
            allowed_trip_ids = {
                trip_id for trip_id, route_id in trips.items() if route_id in allowed_route_ids
            }
            allowed_stop_ids = {
                row.get("stop_id")
                for row in _read_csv(archive, "stop_times.txt")
                if row.get("trip_id") in allowed_trip_ids
            }
            stops = {
                row.get("stop_id"): row for row in _read_csv(archive, "stops.txt")
            }
            for destination in destinations["destinations"]:
                destination_id = destination["id"]
                for stop_id in destination["access_stop_ids"]:
                    if stop_id not in stops:
                        errors.append(
                            f"GTFS stops.txt missing access stop {stop_id} for {destination_id}"
                        )
                if not set(destination["access_stop_ids"]) & allowed_stop_ids:
                    errors.append(
                        f"destination {destination_id} has no access stop served by "
                        "an allowed route"
                    )
                source = destination["source"]
                if source["type"] != "gtfs_stop" or source["stop_id"] not in stops:
                    continue
                stop = stops[source["stop_id"]]
                if stop.get("stop_name") != destination["name_ja"]:
                    errors.append(f"GTFS stop name does not match destination {destination_id}")
                try:
                    lat = float(stop.get("stop_lat", ""))
                    lon = float(stop.get("stop_lon", ""))
                except ValueError:
                    errors.append(f"GTFS stop coordinates are invalid for {destination_id}")
                    continue
                if abs(lat - destination["location"]["lat"]) > 1e-9 or abs(
                    lon - destination["location"]["lon"]
                ) > 1e-9:
                    errors.append(
                        f"GTFS stop coordinates do not match destination {destination_id}"
                    )
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile, KeyError) as exc:
        errors.append(f"invalid GTFS archive: {exc}")

    return errors


def verify_validator_report(contract_root: Path, report_path: Path) -> list[str]:
    contracts, errors = _load_contracts(contract_root)
    if errors:
        return errors
    manifest = contracts["manifest.json"]
    expected = contracts["validation-summary.json"]
    artifact = manifest["feed"]["artifact"]

    if not report_path.is_file():
        return [f"validator report not found: {report_path}"]
    try:
        report = _load_json(report_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"invalid validator report: {exc}"]

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    if summary.get("validatorVersion") != expected["validator"]["version"]:
        errors.append("validator report version does not match validation-summary")
    if summary.get("countryCode") != expected["validator"]["country_code"]:
        errors.append("validator report country code does not match validation-summary")
    feed_info = summary.get("feedInfo") if isinstance(summary.get("feedInfo"), dict) else {}
    if feed_info.get("feedStartDate") != artifact["service_start_date"]:
        errors.append("validator report feedStartDate does not match manifest")
    if feed_info.get("feedEndDate") != artifact["service_end_date"]:
        errors.append("validator report feedEndDate does not match manifest")
    if summary.get("counts") != expected["counts"]:
        errors.append("validator report counts do not match validation-summary")

    notices = report.get("notices") if isinstance(report.get("notices"), list) else []
    error_count = sum(
        int(item.get("totalNotices", 0))
        for item in notices
        if isinstance(item, dict) and item.get("severity") == "ERROR"
    )
    if error_count:
        errors.append(f"validator report contains {error_count} ERROR notices")
    expected_warnings = {
        item["code"]: item["count"]
        for item in expected["notices"]
        if item["severity"] == "WARNING"
    }
    actual_warnings = {
        item.get("code"): item.get("totalNotices")
        for item in notices
        if isinstance(item, dict) and item.get("severity") == "WARNING"
    }
    if actual_warnings != expected_warnings:
        errors.append("validator WARNING notices do not match validation-summary")

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the pinned Hakusan GTFS contract")
    parser.add_argument("--contract-root", type=Path, default=DEFAULT_CONTRACT_ROOT)
    parser.add_argument("--gtfs-zip", type=Path)
    parser.add_argument("--validator-report", type=Path)
    parser.add_argument("--require-evidence", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    errors = validate_contract(args.contract_root)
    if args.require_evidence and args.gtfs_zip is None:
        errors.append("--require-evidence requires --gtfs-zip")
    if args.require_evidence and args.validator_report is None:
        errors.append("--require-evidence requires --validator-report")
    if args.gtfs_zip is not None:
        errors.extend(verify_gtfs_archive(args.contract_root, args.gtfs_zip))
    if args.validator_report is not None:
        errors.extend(verify_validator_report(args.contract_root, args.validator_report))

    if errors:
        for error in dict.fromkeys(errors):
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Hakusan data contract: PASS")
    if args.gtfs_zip is not None and args.validator_report is not None:
        print("Hakusan GTFS evidence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
