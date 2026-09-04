#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any


class PreparationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreparationError(f"cannot read JSON contract {path.name}: {error}") from error
    if not isinstance(payload, dict):
        raise PreparationError(f"JSON contract {path.name} must contain an object")
    return payload


def _read_csv(archive: zipfile.ZipFile, name: str) -> tuple[list[str], list[dict[str, str]]]:
    try:
        raw = archive.read(name)
    except KeyError as error:
        raise PreparationError(f"source GTFS missing required file: {name}") from error
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise PreparationError(f"source GTFS file is not UTF-8: {name}") from error
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames is None:
        raise PreparationError(f"source GTFS file has no header: {name}")
    rows = [{key: value or "" for key, value in row.items() if key is not None} for row in reader]
    return list(reader.fieldnames), rows


def _csv_payload(fieldnames: list[str], rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=fieldnames,
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _ids(rows: list[dict[str, str]], key: str) -> set[str]:
    return {row.get(key, "") for row in rows if row.get(key, "")}


def _contract(contract_root: Path) -> tuple[list[str], set[str], set[str], set[str]]:
    manifest = _load_json(contract_root / "manifest.json")
    route_rules = _load_json(contract_root / "route-rules.json")
    destinations = _load_json(contract_root / "destinations.json")
    try:
        required_files = manifest["feed"]["artifact"]["required_files"]
        allowed_routes = {row["route_id"] for row in route_rules["allowed_routes"]}
        excluded_routes = {row["route_id"] for row in route_rules["excluded_routes"]}
        access_stops = {
            stop_id
            for destination in destinations["destinations"]
            for stop_id in destination["access_stop_ids"]
        }
    except (KeyError, TypeError) as error:
        raise PreparationError(f"invalid Hakusan contract structure: {error}") from error
    if not isinstance(required_files, list) or not all(
        isinstance(name, str) and name for name in required_files
    ):
        raise PreparationError("manifest required_files must be a non-empty string list")
    if route_rules.get("default_policy") != "deny":
        raise PreparationError("route policy must be deny-by-default")
    if allowed_routes & excluded_routes:
        duplicate = sorted(allowed_routes & excluded_routes)[0]
        raise PreparationError(f"route appears in both allowed and excluded policy: {duplicate}")
    return required_files, allowed_routes, excluded_routes, access_stops


def _load_tables(
    archive: zipfile.ZipFile,
    required_files: list[str],
) -> tuple[dict[str, list[str]], dict[str, list[dict[str, str]]]]:
    headers: dict[str, list[str]] = {}
    tables: dict[str, list[dict[str, str]]] = {}
    for name in required_files:
        headers[name], tables[name] = _read_csv(archive, name)
    return headers, tables


def _raise_source_policy_errors(
    tables: dict[str, list[dict[str, str]]],
    allowed_routes: set[str],
    excluded_routes: set[str],
) -> None:
    source_route_ids = _ids(tables["routes.txt"], "route_id")
    missing = sorted(allowed_routes - source_route_ids)
    if missing:
        raise PreparationError(f"allowlisted route missing from source: {missing[0]}")
    unclassified = sorted(source_route_ids - allowed_routes - excluded_routes)
    if unclassified:
        raise PreparationError(f"unclassified route: {unclassified[0]}")


def _retained_stops(
    source_stops: list[dict[str, str]],
    referenced_stop_ids: set[str],
) -> tuple[list[dict[str, str]], set[str]]:
    by_id = {row.get("stop_id", ""): row for row in source_stops if row.get("stop_id", "")}
    retained_ids = set(referenced_stop_ids)
    pending = list(referenced_stop_ids)
    while pending:
        stop_id = pending.pop()
        row = by_id.get(stop_id)
        if row is None:
            raise PreparationError(f"stop_times.txt references missing stop_id: {stop_id}")
        parent_id = row.get("parent_station", "")
        if parent_id and parent_id not in retained_ids:
            if parent_id not in by_id:
                raise PreparationError(f"stops.txt references missing parent_station: {parent_id}")
            retained_ids.add(parent_id)
            pending.append(parent_id)
    return [row for row in source_stops if row.get("stop_id", "") in retained_ids], retained_ids


def _filter_translations(
    rows: list[dict[str, str]],
    retained_ids: dict[str, set[str]],
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for row in rows:
        record_id = row.get("record_id", "")
        table_name = row.get("table_name", "")
        accepted_ids = retained_ids.get(table_name)
        if not record_id or accepted_ids is None or record_id in accepted_ids:
            filtered.append(row)
    return filtered


def _filter_tables(
    tables: dict[str, list[dict[str, str]]],
    allowed_routes: set[str],
    access_stops: set[str],
) -> tuple[dict[str, list[dict[str, str]]], dict[str, object]]:
    routes = [row for row in tables["routes.txt"] if row.get("route_id", "") in allowed_routes]
    route_ids = _ids(routes, "route_id")
    trips = [row for row in tables["trips.txt"] if row.get("route_id", "") in route_ids]
    trip_ids = _ids(trips, "trip_id")
    if not trip_ids:
        raise PreparationError("pilot GTFS has no trips")

    stop_times = [row for row in tables["stop_times.txt"] if row.get("trip_id", "") in trip_ids]
    stop_time_trip_ids = _ids(stop_times, "trip_id")
    trips_without_stops = sorted(trip_ids - stop_time_trip_ids)
    if trips_without_stops:
        raise PreparationError(f"trip has no stop_times rows: {trips_without_stops[0]}")

    source_shape_ids = _ids(tables["shapes.txt"], "shape_id")
    shape_ids = _ids(trips, "shape_id")
    missing_shapes = sorted(shape_ids - source_shape_ids)
    if missing_shapes:
        raise PreparationError(f"trips.txt references missing shape_id: {missing_shapes[0]}")
    shapes = [row for row in tables["shapes.txt"] if row.get("shape_id", "") in shape_ids]

    source_service_ids = _ids(tables["calendar.txt"], "service_id") | _ids(
        tables["calendar_dates.txt"], "service_id"
    )
    service_ids = _ids(trips, "service_id")
    missing_services = sorted(service_ids - source_service_ids)
    if missing_services:
        raise PreparationError(f"trips.txt references missing service_id: {missing_services[0]}")
    calendar = [row for row in tables["calendar.txt"] if row.get("service_id", "") in service_ids]
    calendar_dates = [
        row for row in tables["calendar_dates.txt"] if row.get("service_id", "") in service_ids
    ]

    referenced_stop_ids = _ids(stop_times, "stop_id")
    stops, stop_ids = _retained_stops(tables["stops.txt"], referenced_stop_ids)
    missing_access_stops = sorted(access_stops - stop_ids)
    if missing_access_stops:
        raise PreparationError(
            f"destination access stop missing from pilot GTFS: {missing_access_stops[0]}"
        )

    fare_rules = [
        row
        for row in tables["fare_rules.txt"]
        if not row.get("route_id", "") or row.get("route_id", "") in route_ids
    ]
    fare_ids = _ids(fare_rules, "fare_id")
    source_fare_ids = _ids(tables["fare_attributes.txt"], "fare_id")
    missing_fares = sorted(fare_ids - source_fare_ids)
    if missing_fares:
        raise PreparationError(f"fare_rules.txt references missing fare_id: {missing_fares[0]}")
    fare_attributes = [
        row for row in tables["fare_attributes.txt"] if row.get("fare_id", "") in fare_ids
    ]

    retained_ids = {
        "routes": route_ids,
        "trips": trip_ids,
        "stops": stop_ids,
        "shapes": shape_ids,
        "calendar": service_ids,
        "calendar_dates": service_ids,
        "fare_attributes": fare_ids,
    }
    translations = _filter_translations(tables["translations.txt"], retained_ids)

    filtered = dict(tables)
    filtered.update(
        {
            "calendar.txt": calendar,
            "calendar_dates.txt": calendar_dates,
            "fare_attributes.txt": fare_attributes,
            "fare_rules.txt": fare_rules,
            "routes.txt": routes,
            "shapes.txt": shapes,
            "stop_times.txt": stop_times,
            "stops.txt": stops,
            "translations.txt": translations,
            "trips.txt": trips,
        }
    )
    summary: dict[str, object] = {
        "route_ids": sorted(route_ids),
        "trip_ids": sorted(trip_ids),
        "shape_ids": sorted(shape_ids),
        "service_ids": sorted(service_ids),
        "stop_ids": sorted(stop_ids),
        "fare_ids": sorted(fare_ids),
        "route_count": len(route_ids),
        "trip_count": len(trip_ids),
        "stop_time_count": len(stop_times),
        "stop_count": len(stop_ids),
    }
    return filtered, summary


def _write_zip(
    output_zip: Path,
    required_files: list[str],
    headers: dict[str, list[str]],
    tables: dict[str, list[dict[str, str]]],
) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_zip.parent,
            prefix=f".{output_zip.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        with zipfile.ZipFile(temporary_path, "w") as archive:
            for name in required_files:
                info = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(
                    info,
                    _csv_payload(headers[name], tables[name]),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
        with temporary_path.open("rb") as written:
            os.fsync(written.fileno())
        temporary_path.replace(output_zip)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _inspect_loaded_tables(
    allowed_routes: set[str],
    excluded_routes: set[str],
    access_stops: set[str],
    tables: dict[str, list[dict[str, str]]],
) -> list[str]:
    errors: list[str] = []
    route_ids = _ids(tables["routes.txt"], "route_id")
    for route_id in sorted(route_ids & excluded_routes):
        errors.append(f"pilot GTFS contains excluded route: {route_id}")
    for route_id in sorted(route_ids - allowed_routes - excluded_routes):
        errors.append(f"pilot GTFS contains unclassified route: {route_id}")
    for route_id in sorted(allowed_routes - route_ids):
        errors.append(f"pilot GTFS missing allowlisted route: {route_id}")

    trip_ids = _ids(tables["trips.txt"], "trip_id")
    for row in tables["trips.txt"]:
        if row.get("route_id", "") not in route_ids:
            errors.append(f"trips.txt references missing route_id: {row.get('route_id', '')}")
    for row in tables["stop_times.txt"]:
        if row.get("trip_id", "") not in trip_ids:
            errors.append(f"stop_times.txt references missing trip_id: {row.get('trip_id', '')}")

    stop_ids = _ids(tables["stops.txt"], "stop_id")
    for row in tables["stop_times.txt"]:
        if row.get("stop_id", "") not in stop_ids:
            errors.append(f"stop_times.txt references missing stop_id: {row.get('stop_id', '')}")
    for stop_id in sorted(access_stops - stop_ids):
        errors.append(f"pilot GTFS missing destination access stop: {stop_id}")
    return list(dict.fromkeys(errors))


def inspect_pilot_gtfs(contract_root: Path, pilot_zip: Path) -> list[str]:
    try:
        required_files, allowed_routes, excluded_routes, access_stops = _contract(contract_root)
        with zipfile.ZipFile(pilot_zip) as archive:
            _, tables = _load_tables(archive, required_files)
    except (OSError, zipfile.BadZipFile, PreparationError) as error:
        return [str(error)]
    return _inspect_loaded_tables(allowed_routes, excluded_routes, access_stops, tables)


def prepare_pilot_gtfs(
    contract_root: Path,
    source_zip: Path,
    output_zip: Path,
    expected_source_sha256: str,
) -> dict[str, object]:
    actual_sha256 = sha256_file(source_zip)
    if actual_sha256 != expected_source_sha256:
        raise PreparationError(
            f"source GTFS sha256 mismatch: expected {expected_source_sha256}, got {actual_sha256}"
        )

    required_files, allowed_routes, excluded_routes, access_stops = _contract(contract_root)
    try:
        with zipfile.ZipFile(source_zip) as archive:
            headers, tables = _load_tables(archive, required_files)
    except zipfile.BadZipFile as error:
        raise PreparationError("source GTFS is not a valid ZIP archive") from error

    _raise_source_policy_errors(tables, allowed_routes, excluded_routes)
    filtered, summary = _filter_tables(tables, allowed_routes, access_stops)
    _write_zip(output_zip, required_files, headers, filtered)
    inspection_errors = inspect_pilot_gtfs(contract_root, output_zip)
    if inspection_errors:
        output_zip.unlink(missing_ok=True)
        raise PreparationError(inspection_errors[0])
    summary["source_sha256"] = actual_sha256
    summary["pilot_sha256"] = sha256_file(output_zip)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an allowlisted Hakusan pilot GTFS")
    parser.add_argument("--contract-root", type=Path, default=Path("data/hakusan"))
    parser.add_argument("--source-gtfs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    expected_sha256 = args.expected_sha256
    if expected_sha256 is None:
        manifest = _load_json(args.contract_root / "manifest.json")
        try:
            expected_sha256 = manifest["feed"]["artifact"]["sha256"]
        except (KeyError, TypeError) as error:
            raise PreparationError("manifest feed.artifact.sha256 is missing") from error
    summary = prepare_pilot_gtfs(
        args.contract_root,
        args.source_gtfs,
        args.output,
        expected_sha256,
    )
    print(
        "Hakusan pilot GTFS written: "
        f"{summary['route_count']} routes, {summary['trip_count']} trips, "
        f"{summary['stop_count']} stops"
    )
    print(f"Pilot GTFS sha256: {summary['pilot_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
