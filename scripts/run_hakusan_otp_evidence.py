#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from scripts.prepare_hakusan_otp import inspect_pilot_gtfs, prepare_pilot_gtfs
    from scripts.validate_hakusan_otp_contract import validate_otp_contract
except ModuleNotFoundError:
    from prepare_hakusan_otp import inspect_pilot_gtfs, prepare_pilot_gtfs
    from validate_hakusan_otp_contract import validate_otp_contract


ROUTES_QUERY = """\
query HakusanRoutes {
  routes {
    gtfsId
    longName
    shortName
  }
}
"""

STOPS_QUERY = """\
query HakusanStops {
  stops {
    gtfsId
    name
  }
}
"""

PLAN_QUERY = """\
query HakusanPlan(
  $origin: PlanLabeledLocationInput!
  $destination: PlanLabeledLocationInput!
  $dateTime: PlanDateTimeInput!
  $modes: PlanModesInput!
  $searchWindow: Duration
) {
  planConnection(
    origin: $origin
    destination: $destination
    dateTime: $dateTime
    modes: $modes
    searchWindow: $searchWindow
    first: 3
  ) {
    routingErrors {
      code
      description
      inputField
    }
    edges {
      node {
        duration
        legs {
          mode
          route {
            gtfsId
          }
        }
      }
    }
  }
}
"""

_JAVA_VERSION_PATTERN = re.compile(r'(?:openjdk|java) version "(?:(1)\.)?(\d+)')
_CONFIG_WARNING_MARKERS = (
    "unrecognized",
    "unknown",
    "unused",
    "not used",
    "deprecated",
    "invalid",
)


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlanEvidence:
    errors: list[str]
    modes: list[str]
    route_ids: list[str]
    duration_seconds: int | None


def normalize_gtfs_id(value: str) -> str:
    return value.split(":", 1)[-1]


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _sequence(value: object) -> Sequence[object] | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return None


def _graphql_errors(payload: object) -> list[str]:
    document = _mapping(payload)
    if document is None:
        return ["GraphQL response must be a JSON object"]
    raw_errors = _sequence(document.get("errors"))
    if not raw_errors:
        return []
    errors: list[str] = []
    for item in raw_errors:
        entry = _mapping(item)
        message = entry.get("message") if entry is not None else None
        errors.append(f"GraphQL error: {message if isinstance(message, str) else 'unknown error'}")
    return errors


def _data_field(payload: object, field: str) -> object | None:
    document = _mapping(payload)
    data = _mapping(document.get("data")) if document is not None else None
    return data.get(field) if data is not None else None


def validate_route_inventory(payload: object, allowed_route_ids: set[str]) -> list[str]:
    errors = _graphql_errors(payload)
    if errors:
        return errors
    routes = _sequence(_data_field(payload, "routes"))
    if routes is None:
        return ["OTP route inventory response is missing routes"]
    observed: set[str] = set()
    for route in routes:
        row = _mapping(route)
        gtfs_id = row.get("gtfsId") if row is not None else None
        if not isinstance(gtfs_id, str) or not gtfs_id:
            errors.append("OTP route inventory contains missing gtfsId")
            continue
        observed.add(normalize_gtfs_id(gtfs_id))
    for route_id in sorted(allowed_route_ids - observed):
        errors.append(f"OTP route inventory missing: {route_id}")
    for route_id in sorted(observed - allowed_route_ids):
        errors.append(f"OTP route inventory unexpected: {route_id}")
    return list(dict.fromkeys(errors))


def validate_stop_inventory(payload: object, access_stop_ids: set[str]) -> list[str]:
    errors = _graphql_errors(payload)
    if errors:
        return errors
    stops = _sequence(_data_field(payload, "stops"))
    if stops is None:
        return ["OTP stop inventory response is missing stops"]
    observed: set[str] = set()
    for stop in stops:
        row = _mapping(stop)
        gtfs_id = row.get("gtfsId") if row is not None else None
        if not isinstance(gtfs_id, str) or not gtfs_id:
            errors.append("OTP stop inventory contains missing gtfsId")
            continue
        observed.add(normalize_gtfs_id(gtfs_id))
    for stop_id in sorted(access_stop_ids - observed):
        errors.append(f"OTP stop inventory missing: {stop_id}")
    return list(dict.fromkeys(errors))


def _routing_errors(connection: Mapping[str, object]) -> list[str]:
    raw_errors = _sequence(connection.get("routingErrors"))
    if not raw_errors:
        return []
    errors: list[str] = []
    for item in raw_errors:
        row = _mapping(item)
        code = row.get("code") if row is not None else None
        description = row.get("description") if row is not None else None
        code_text = code if isinstance(code, str) and code else "UNKNOWN"
        description_text = description if isinstance(description, str) and description else "no description"
        errors.append(f"OTP routing error {code_text}: {description_text}")
    return errors


def validate_plan_response(payload: object, allowed_route_ids: set[str]) -> PlanEvidence:
    errors = _graphql_errors(payload)
    if errors:
        return PlanEvidence(errors, [], [], None)
    connection = _mapping(_data_field(payload, "planConnection"))
    if connection is None:
        return PlanEvidence(["OTP plan response is missing planConnection"], [], [], None)
    errors.extend(_routing_errors(connection))
    edges = _sequence(connection.get("edges"))
    if not edges:
        errors.append("OTP returned no itinerary")
        return PlanEvidence(list(dict.fromkeys(errors)), [], [], None)
    first_edge = _mapping(edges[0])
    node = _mapping(first_edge.get("node")) if first_edge is not None else None
    if node is None:
        errors.append("OTP itinerary edge is missing node")
        return PlanEvidence(list(dict.fromkeys(errors)), [], [], None)

    duration = node.get("duration")
    duration_seconds: int | None = None
    if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 0:
        duration_seconds = round(duration)
    else:
        errors.append("OTP itinerary duration is missing or invalid")

    legs = _sequence(node.get("legs"))
    if legs is None:
        errors.append("OTP itinerary legs are missing")
        return PlanEvidence(list(dict.fromkeys(errors)), [], [], duration_seconds)
    modes: list[str] = []
    route_ids: list[str] = []
    for leg in legs:
        row = _mapping(leg)
        mode = row.get("mode") if row is not None else None
        if not isinstance(mode, str) or not mode:
            errors.append("OTP itinerary leg is missing mode")
            continue
        modes.append(mode)
        if mode != "BUS":
            continue
        route = _mapping(row.get("route"))
        gtfs_id = route.get("gtfsId") if route is not None else None
        if not isinstance(gtfs_id, str) or not gtfs_id:
            errors.append("OTP BUS leg is missing route gtfsId")
            continue
        route_id = normalize_gtfs_id(gtfs_id)
        route_ids.append(route_id)
        if route_id not in allowed_route_ids:
            errors.append(f"OTP itinerary uses non-allowlisted route: {route_id}")
    if "WALK" not in modes:
        errors.append("OTP itinerary has no WALK leg")
    if "BUS" not in modes:
        errors.append("OTP itinerary has no BUS leg")
    return PlanEvidence(list(dict.fromkeys(errors)), modes, route_ids, duration_seconds)


def parse_java_major(version_output: str) -> int:
    match = _JAVA_VERSION_PATTERN.search(version_output)
    if match is None:
        raise EvidenceError("cannot parse Java major version")
    legacy_prefix, major = match.groups()
    return int(major) if legacy_prefix is None else int(major)


def validate_java_major(version_output: str, expected_major: int) -> int:
    actual_major = parse_java_major(version_output)
    if actual_major != expected_major:
        raise EvidenceError(f"OTP requires Java major {expected_major}, found {actual_major}")
    return actual_major


def scan_otp_log(text: str) -> list[str]:
    warnings: list[str] = []
    for line in text.splitlines():
        normalized = line.lower()
        if "warn" not in normalized:
            continue
        mentions_configuration = "config" in normalized or "parameter" in normalized or "property" in normalized
        if mentions_configuration and any(marker in normalized for marker in _CONFIG_WARNING_MARKERS):
            warnings.append(line.strip()[:500])
    return list(dict.fromkeys(warnings))


def sanitize_evidence_path(path: Path, repo_root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return resolved.name


def _absolute_string(value: object) -> str | None:
    if isinstance(value, str):
        if Path(value).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", value):
            return value
        return None
    if isinstance(value, Mapping):
        for nested in value.values():
            found = _absolute_string(nested)
            if found is not None:
                return found
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            found = _absolute_string(nested)
            if found is not None:
                return found
    return None


def write_json_atomic(destination: Path, payload: Mapping[str, object]) -> None:
    absolute = _absolute_string(payload)
    if absolute is not None:
        raise EvidenceError(f"evidence summary contains absolute path: {absolute}")
    serialized = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def stop_process(process: Any, *, timeout: float = 10.0) -> str:
    if process.poll() is not None:
        return "already_stopped"
    process.terminate()
    try:
        process.wait(timeout=timeout)
        return "terminated"
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)
        return "killed"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise EvidenceError(f"{label} is missing: {path}")


def _validate_input(path: Path, label: str, expected_sha: str, expected_size: int) -> None:
    _require_file(path, label)
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise EvidenceError(f"{label} size mismatch: expected {expected_size}, got {actual_size}")
    actual_sha = _sha256(path)
    if actual_sha != expected_sha:
        raise EvidenceError(f"{label} sha256 mismatch: expected {expected_sha}, got {actual_sha}")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError(f"cannot read {label}: {error}") from error
    if not isinstance(payload, dict):
        raise EvidenceError(f"{label} must contain a JSON object")
    return payload


def _policy(repo_root: Path) -> tuple[set[str], set[str], dict[str, Any]]:
    route_rules = _load_json(repo_root / "data" / "hakusan" / "route-rules.json", "route policy")
    destinations = _load_json(
        repo_root / "data" / "hakusan" / "destinations.json",
        "destination contract",
    )
    allowed_routes = {
        row["route_id"]
        for row in route_rules.get("allowed_routes", [])
        if isinstance(row, dict) and isinstance(row.get("route_id"), str)
    }
    access_stops = {
        stop_id
        for destination in destinations.get("destinations", [])
        if isinstance(destination, dict)
        for stop_id in destination.get("access_stop_ids", [])
        if isinstance(stop_id, str)
    }
    return allowed_routes, access_stops, destinations


def _destination(destinations: dict[str, Any], destination_id: str) -> dict[str, Any]:
    for destination in destinations.get("destinations", []):
        if isinstance(destination, dict) and destination.get("id") == destination_id:
            return destination
    raise EvidenceError(f"destination is missing from contract: {destination_id}")


def _graphql_post(
    endpoint: str,
    query: str,
    variables: Mapping[str, object] | None = None,
    *,
    timeout: float = 30.0,
) -> object:
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise EvidenceError("OTP evidence endpoint must use http://127.0.0.1")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", "OTPTimeout": "180000"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read()
    except (HTTPError, URLError, OSError) as error:
        raise EvidenceError(f"OTP GraphQL request failed: {error}") from error
    try:
        return json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"OTP GraphQL response is not valid JSON: {error}") from error


def _wait_for_graphql(endpoint: str, process: subprocess.Popen[bytes], timeout: float) -> object:
    deadline = time.monotonic() + timeout
    last_error = "not started"
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            raise EvidenceError(f"OTP server exited before readiness with code {return_code}")
        try:
            payload = _graphql_post(endpoint, ROUTES_QUERY, timeout=5.0)
            graphql_errors = _graphql_errors(payload)
            if graphql_errors:
                raise EvidenceError(graphql_errors[0])
            if _sequence(_data_field(payload, "routes")) is not None:
                return payload
            last_error = "route inventory is missing"
        except EvidenceError as error:
            last_error = str(error)
        time.sleep(0.5)
    raise EvidenceError(f"OTP startup timed out after {timeout:g}s: {last_error}")


def _location(label: str, lat: float, lon: float) -> dict[str, object]:
    return {
        "label": label,
        "location": {"coordinate": {"latitude": lat, "longitude": lon}},
    }


def _plan_variables(
    origin: Mapping[str, object],
    destination: Mapping[str, object],
    departure: str,
) -> dict[str, object]:
    return {
        "origin": dict(origin),
        "destination": dict(destination),
        "dateTime": {"earliestDeparture": departure},
        "modes": {
            "transitOnly": True,
            "transit": {
                "access": ["WALK"],
                "egress": ["WALK"],
                "transfer": ["WALK"],
                "transit": [{"mode": "BUS"}],
            },
        },
        "searchWindow": "PT2H",
    }


def _fresh_run_directory(work_root: Path) -> Path:
    work_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=work_root))


def _copy_inputs(repo_root: Path, osm: Path, run_directory: Path) -> None:
    shutil.copyfile(osm, run_directory / "hakusan-20260903-canonical.osm")
    shutil.copyfile(
        repo_root / "config" / "otp" / "hakusan" / "build-config.json",
        run_directory / "build-config.json",
    )
    shutil.copyfile(
        repo_root / "config" / "otp" / "hakusan" / "router-config.json",
        run_directory / "router-config.json",
    )


def _run_build(
    otp_jar: Path,
    run_directory: Path,
    heap_mb: int,
    timeout: float,
) -> tuple[Path, str]:
    log_path = run_directory / "otp-build.log"
    command = [
        "java",
        f"-Xmx{heap_mb}m",
        "-jar",
        str(otp_jar.resolve()),
        "--build",
        "--save",
        str(run_directory.resolve()),
    ]
    with log_path.open("wb") as log:
        try:
            result = subprocess.run(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise EvidenceError(f"OTP graph build timed out after {timeout:g}s") from error
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise EvidenceError(f"OTP graph build failed with code {result.returncode}; see {log_path.name}")
    warnings = scan_otp_log(log_text)
    if warnings:
        raise EvidenceError(f"OTP graph build configuration warning: {warnings[0]}")
    graph_path = run_directory / "graph.obj"
    _require_file(graph_path, "OTP graph")
    return graph_path, log_text


def _start_server(
    otp_jar: Path,
    run_directory: Path,
    heap_mb: int,
    port: int,
    log_file: Any,
) -> subprocess.Popen[bytes]:
    command = [
        "java",
        f"-Xmx{heap_mb}m",
        "-jar",
        str(otp_jar.resolve()),
        "--load",
        "--serve",
        "--bindAddress",
        "127.0.0.1",
        "--port",
        str(port),
        str(run_directory.resolve()),
    ]
    return subprocess.Popen(command, stdout=log_file, stderr=subprocess.STDOUT)


def _java_version(expected_major: int) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EvidenceError(f"cannot execute java -version: {error}") from error
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0:
        raise EvidenceError(f"java -version failed with code {result.returncode}")
    return validate_java_major(output, expected_major), output.splitlines()[0]


def run_evidence(args: argparse.Namespace) -> dict[str, object]:
    repo_root = args.repo_root.resolve()
    contract_errors = validate_otp_contract(repo_root)
    if contract_errors:
        raise EvidenceError(f"OTP source contract invalid: {contract_errors[0]}")
    sources = _load_json(repo_root / "data" / "hakusan" / "otp-sources.json", "OTP sources")
    allowed_routes, access_stops, destinations = _policy(repo_root)

    otp_jar = args.otp_jar.resolve()
    osm = args.osm.resolve()
    gtfs_zip = args.gtfs_zip.resolve()
    _validate_input(otp_jar, "OTP JAR", sources["otp"]["sha256"], sources["otp"]["size_bytes"])
    _validate_input(
        osm,
        "canonical OSM",
        sources["osm"]["canonical_sha256"],
        sources["osm"]["canonical_size_bytes"],
    )
    _require_file(gtfs_zip, "source GTFS")
    if args.port != sources["runtime"]["port"]:
        raise EvidenceError(f"OTP port must match contract: {sources['runtime']['port']}")
    if not 1 <= args.startup_timeout <= sources["runtime"]["startup_timeout_seconds"]:
        raise EvidenceError("startup timeout exceeds committed guardrail")
    if not 1 <= args.build_timeout <= 900:
        raise EvidenceError("build timeout must be between 1 and 900 seconds")

    java_major, java_version_line = _java_version(sources["otp"]["java_major"])
    run_directory = _fresh_run_directory(args.work_dir.resolve())
    pilot_gtfs = run_directory / sources["gtfs"]["pilot_filename"]
    gtfs_summary = prepare_pilot_gtfs(
        repo_root / "data" / "hakusan",
        gtfs_zip,
        pilot_gtfs,
        sources["gtfs"]["source_sha256"],
    )
    inspection_errors = inspect_pilot_gtfs(repo_root / "data" / "hakusan", pilot_gtfs)
    if inspection_errors:
        raise EvidenceError(f"pilot GTFS invalid: {inspection_errors[0]}")
    for key, expected in sources["gtfs"]["expected"].items():
        if gtfs_summary.get(key) != expected:
            raise EvidenceError(
                f"pilot GTFS {key} mismatch: expected {expected}, got {gtfs_summary.get(key)}"
            )
    _copy_inputs(repo_root, osm, run_directory)

    graph_path, _build_log = _run_build(
        otp_jar,
        run_directory,
        sources["runtime"]["max_heap_mb"],
        args.build_timeout,
    )
    endpoint = f"http://127.0.0.1:{args.port}{sources['runtime']['graphql_endpoint_path']}"
    server_log_path = run_directory / "otp-server.log"
    process: subprocess.Popen[bytes] | None = None
    stop_outcome: str | None = None
    route_payload: object
    stop_payload: object
    outbound: PlanEvidence
    return_trip: PlanEvidence
    with server_log_path.open("wb") as server_log:
        try:
            process = _start_server(
                otp_jar,
                run_directory,
                sources["runtime"]["max_heap_mb"],
                args.port,
                server_log,
            )
            route_payload = _wait_for_graphql(endpoint, process, args.startup_timeout)
            route_errors = validate_route_inventory(route_payload, allowed_routes)
            if route_errors:
                raise EvidenceError(route_errors[0])

            stop_payload = _graphql_post(endpoint, STOPS_QUERY)
            stop_errors = validate_stop_inventory(stop_payload, access_stops)
            if stop_errors:
                raise EvidenceError(stop_errors[0])

            scenario = sources["scenario"]
            destination = _destination(destinations, scenario["destination_id"])
            origin_location = _location(
                scenario["origin"]["label"],
                scenario["origin"]["lat"],
                scenario["origin"]["lon"],
            )
            destination_location = _location(
                destination["name_ja"],
                destination["location"]["lat"],
                destination["location"]["lon"],
            )
            outbound_payload = _graphql_post(
                endpoint,
                PLAN_QUERY,
                _plan_variables(
                    origin_location,
                    destination_location,
                    f"{scenario['service_date']}T{scenario['outbound_time']}",
                ),
            )
            outbound = validate_plan_response(outbound_payload, allowed_routes)
            if outbound.errors:
                raise EvidenceError(f"outbound plan invalid: {outbound.errors[0]}")
            return_payload = _graphql_post(
                endpoint,
                PLAN_QUERY,
                _plan_variables(
                    destination_location,
                    origin_location,
                    f"{scenario['service_date']}T{scenario['return_time']}",
                ),
            )
            return_trip = validate_plan_response(return_payload, allowed_routes)
            if return_trip.errors:
                raise EvidenceError(f"return plan invalid: {return_trip.errors[0]}")
        finally:
            if process is not None:
                stop_outcome = stop_process(process)
    if stop_outcome is None:
        raise EvidenceError("OTP process cleanup was not confirmed")

    server_warnings = scan_otp_log(server_log_path.read_text(encoding="utf-8", errors="replace"))
    if server_warnings:
        raise EvidenceError(f"OTP server configuration warning: {server_warnings[0]}")

    summary: dict[str, object] = {
        "schema_version": 1,
        "status": "PASS",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "contract_id": sources["contract_id"],
        "otp": {
            "version": sources["otp"]["version"],
            "jar_sha256": sources["otp"]["sha256"],
            "java_major": java_major,
            "java_version": java_version_line,
            "heap_cap_mb": sources["runtime"]["max_heap_mb"],
            "process_stop": stop_outcome,
        },
        "inputs": {
            "source_gtfs": sanitize_evidence_path(gtfs_zip, repo_root),
            "source_gtfs_sha256": sources["gtfs"]["source_sha256"],
            "pilot_gtfs": pilot_gtfs.name,
            "pilot_gtfs_sha256": gtfs_summary["pilot_sha256"],
            "canonical_osm": osm.name,
            "canonical_osm_sha256": sources["osm"]["canonical_sha256"],
            "graph": graph_path.name,
            "graph_sha256": _sha256(graph_path),
        },
        "inventory": {
            "route_count": len(allowed_routes),
            "route_ids": sorted(allowed_routes),
            "required_access_stop_count": len(access_stops),
            "required_access_stop_ids": sorted(access_stops),
            "trip_count": gtfs_summary["trip_count"],
            "stop_time_count": gtfs_summary["stop_time_count"],
            "stop_count": gtfs_summary["stop_count"],
        },
        "scenarios": {
            "outbound": {
                "departure": f"{sources['scenario']['service_date']}T{sources['scenario']['outbound_time']}",
                "modes": outbound.modes,
                "route_ids": outbound.route_ids,
                "duration_seconds": outbound.duration_seconds,
            },
            "return": {
                "departure": f"{sources['scenario']['service_date']}T{sources['scenario']['return_time']}",
                "modes": return_trip.modes,
                "route_ids": return_trip.route_ids,
                "duration_seconds": return_trip.duration_seconds,
            },
        },
        "limitations": {
            "realtime": False,
            "routing_provider_changed": False,
            "scope": "local Gate 1 evidence only",
        },
    }
    write_json_atomic(args.summary_output.resolve(), summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build and verify Hakusan OTP Gate 1 evidence")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--gtfs-zip", type=Path, required=True)
    parser.add_argument("--osm", type=Path, required=True)
    parser.add_argument("--otp-jar", type=Path, required=True)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=repo_root / "data" / "external" / "hakusan" / "otp" / "evidence-runs",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=repo_root / "data" / "hakusan" / "otp-validation-summary.json",
    )
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--startup-timeout", type=float, default=120.0)
    parser.add_argument("--build-timeout", type=float, default=600.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    summary = run_evidence(args)
    print(
        "Hakusan OTP Gate 1: PASS "
        f"({summary['inventory']['route_count']} routes, "
        f"{summary['inventory']['required_access_stop_count']} access stops)"
    )
    print(f"Evidence summary: {sanitize_evidence_path(args.summary_output, args.repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
