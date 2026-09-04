from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.validate_hakusan_data import (
    validate_contract,
    verify_gtfs_archive,
    verify_validator_report,
)

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_CONTRACT = ROOT / "data" / "hakusan"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _csv_text(fieldnames: list[str], rows: list[dict[str, object]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


class ContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.contract_root = Path(self.temp_dir.name) / "hakusan"
        shutil.copytree(COMMITTED_CONTRACT, self.contract_root)

    def test_committed_contract_is_valid(self) -> None:
        self.assertEqual(validate_contract(COMMITTED_CONTRACT), [])

    def test_manifest_requires_pinned_uid_and_sha256(self) -> None:
        manifest_path = self.contract_root / "manifest.json"
        manifest = _load_json(manifest_path)
        manifest["feed"]["artifact"]["uid"] = "current"
        manifest["feed"]["artifact"]["sha256"] = "mutable"
        _write_json(manifest_path, manifest)

        errors = validate_contract(self.contract_root)

        self.assertIn("manifest feed.artifact.uid must be a UUID", errors)
        self.assertIn(
            "manifest feed.artifact.sha256 must be 64 lowercase hex characters",
            errors,
        )

    def test_manifest_requires_auditable_source_and_license_urls(self) -> None:
        manifest_path = self.contract_root / "manifest.json"
        manifest = _load_json(manifest_path)
        del manifest["feed"]["repository_metadata_url"]
        del manifest["feed"]["license"]["url"]
        _write_json(manifest_path, manifest)

        errors = validate_contract(self.contract_root)

        self.assertIn("manifest feed requires repository and source page URLs", errors)
        self.assertIn("manifest feed license requires an HTTPS URL", errors)

    def test_osm_destination_requires_auditable_element_id(self) -> None:
        destinations_path = self.contract_root / "destinations.json"
        destinations = _load_json(destinations_path)
        pharmacy = next(
            item for item in destinations["destinations"] if item["category"] == "pharmacy"
        )
        del pharmacy["source"]["element_id"]
        pharmacy["source"].pop("element_version", None)
        pharmacy["source"].pop("element_timestamp", None)
        del pharmacy["source"]["license_url"]
        _write_json(destinations_path, destinations)

        errors = validate_contract(self.contract_root)

        self.assertIn(
            "destination pharmacy-kusuri-aoki-nunoichi OSM source requires integer element_id",
            errors,
        )
        self.assertIn(
            "destination pharmacy-kusuri-aoki-nunoichi OSM source requires an ODbL URL",
            errors,
        )
        self.assertIn(
            "destination pharmacy-kusuri-aoki-nunoichi OSM source requires version and timestamp",
            errors,
        )

    def test_non_pilot_routes_are_denied_by_default(self) -> None:
        rules_path = self.contract_root / "route-rules.json"
        rules = _load_json(rules_path)
        rules["default_policy"] = "allow"
        _write_json(rules_path, rules)

        errors = validate_contract(self.contract_root)

        self.assertIn("route-rules default_policy must be 'deny'", errors)


class EvidenceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.contract_root = self.root / "hakusan"
        shutil.copytree(COMMITTED_CONTRACT, self.contract_root)

    def _build_synthetic_archive(
        self,
        *,
        omit: str | None = None,
        serve_destinations_from_allowed_route: bool = True,
    ) -> Path:
        manifest = _load_json(self.contract_root / "manifest.json")
        rules = _load_json(self.contract_root / "route-rules.json")
        destinations = _load_json(self.contract_root / "destinations.json")
        artifact = manifest["feed"]["artifact"]

        route_rows = [
            {"route_id": route["route_id"], "route_long_name": route["name_ja"]}
            for route in rules["allowed_routes"] + rules["excluded_routes"]
        ]
        stop_rows_by_id: dict[str, dict[str, object]] = {}
        for destination in destinations["destinations"]:
            for stop_id in destination["access_stop_ids"]:
                stop_rows_by_id.setdefault(
                    stop_id,
                    {
                        "stop_id": stop_id,
                        "stop_name": destination["name_ja"],
                        "stop_lat": destination["location"]["lat"],
                        "stop_lon": destination["location"]["lon"],
                    },
                )
            if destination["source"]["type"] == "gtfs_stop":
                stop_rows_by_id[destination["source"]["stop_id"]] = {
                    "stop_id": destination["source"]["stop_id"],
                    "stop_name": destination["name_ja"],
                    "stop_lat": destination["location"]["lat"],
                    "stop_lon": destination["location"]["lon"],
                }

        service_route = (
            rules["allowed_routes"][0]
            if serve_destinations_from_allowed_route
            else rules["excluded_routes"][0]
        )
        trip_id = "synthetic-pilot-trip"
        stop_time_rows = [
            {
                "trip_id": trip_id,
                "arrival_time": "09:00:00",
                "departure_time": "09:00:00",
                "stop_id": stop_id,
                "stop_sequence": sequence,
            }
            for sequence, stop_id in enumerate(stop_rows_by_id, start=1)
        ]

        files = {
            "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\r\n",
            "calendar.txt": (
                "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
                "start_date,end_date\r\n"
            ),
            "calendar_dates.txt": "service_id,date,exception_type\r\n",
            "fare_attributes.txt": "fare_id,price,currency_type,payment_method,transfers\r\n",
            "fare_rules.txt": "fare_id,route_id\r\n",
            "feed_info.txt": _csv_text(
                [
                    "feed_publisher_name",
                    "feed_publisher_url",
                    "feed_lang",
                    "feed_start_date",
                    "feed_end_date",
                    "feed_version",
                ],
                [
                    {
                        "feed_publisher_name": manifest["feed"]["publisher_name"],
                        "feed_publisher_url": manifest["feed"]["source_page_url"],
                        "feed_lang": "ja",
                        "feed_start_date": artifact["service_start_date"].replace("-", ""),
                        "feed_end_date": artifact["service_end_date"].replace("-", ""),
                        "feed_version": artifact["feed_version"],
                    }
                ],
            ),
            "routes.txt": _csv_text(["route_id", "route_long_name"], route_rows),
            "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\r\n",
            "stop_times.txt": _csv_text(
                [
                    "trip_id",
                    "arrival_time",
                    "departure_time",
                    "stop_id",
                    "stop_sequence",
                ],
                stop_time_rows,
            ),
            "stops.txt": _csv_text(
                ["stop_id", "stop_name", "stop_lat", "stop_lon"],
                list(stop_rows_by_id.values()),
            ),
            "translations.txt": "table_name,field_name,language,translation,record_id\r\n",
            "trips.txt": _csv_text(
                ["route_id", "service_id", "trip_id"],
                [
                    {
                        "route_id": service_route["route_id"],
                        "service_id": "synthetic-service",
                        "trip_id": trip_id,
                    }
                ],
            ),
        }
        if omit is not None:
            del files[omit]

        archive_path = self.root / "feed.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        manifest["feed"]["artifact"]["sha256"] = digest
        _write_json(self.contract_root / "manifest.json", manifest)
        validation = _load_json(self.contract_root / "validation-summary.json")
        validation["archive_sha256"] = digest
        _write_json(self.contract_root / "validation-summary.json", validation)
        return archive_path

    def _write_validator_report(self, *, error_count: int = 0) -> Path:
        manifest = _load_json(self.contract_root / "manifest.json")
        validation = _load_json(self.contract_root / "validation-summary.json")
        artifact = manifest["feed"]["artifact"]
        notices = [
            {
                "severity": item["severity"],
                "code": item["code"],
                "totalNotices": item["count"],
            }
            for item in validation["notices"]
        ]
        if error_count:
            notices.append(
                {
                    "severity": "ERROR",
                    "code": "missing_required_file",
                    "totalNotices": error_count,
                }
            )
        report = {
            "summary": {
                "validatorVersion": validation["validator"]["version"],
                "countryCode": validation["validator"]["country_code"],
                "feedInfo": {
                    "feedStartDate": artifact["service_start_date"],
                    "feedEndDate": artifact["service_end_date"],
                },
                "counts": validation["counts"],
            },
            "notices": notices,
        }
        report_path = self.root / "report.json"
        _write_json(report_path, report)
        return report_path

    def test_synthetic_archive_with_contract_rows_passes(self) -> None:
        archive_path = self._build_synthetic_archive()

        self.assertEqual(verify_gtfs_archive(self.contract_root, archive_path), [])

    def test_archive_hash_mismatch_is_rejected(self) -> None:
        archive_path = self.root / "feed.zip"
        archive_path.write_bytes(b"not the pinned archive")

        errors = verify_gtfs_archive(self.contract_root, archive_path)

        self.assertIn("GTFS archive sha256 does not match manifest", errors)

    def test_archive_missing_required_file_is_rejected(self) -> None:
        archive_path = self._build_synthetic_archive(omit="trips.txt")

        errors = verify_gtfs_archive(self.contract_root, archive_path)

        self.assertIn("GTFS archive missing required file: trips.txt", errors)

    def test_destination_access_stops_must_be_served_by_allowed_route(self) -> None:
        archive_path = self._build_synthetic_archive(
            serve_destinations_from_allowed_route=False
        )

        errors = verify_gtfs_archive(self.contract_root, archive_path)

        self.assertIn(
            "destination supermarket-osakaya-matto has no access stop served by an allowed route",
            errors,
        )

    def test_validator_report_matching_summary_passes(self) -> None:
        report_path = self._write_validator_report()

        self.assertEqual(verify_validator_report(self.contract_root, report_path), [])

    def test_validator_report_rejects_any_error_notice(self) -> None:
        report_path = self._write_validator_report(error_count=1)

        errors = verify_validator_report(self.contract_root, report_path)

        self.assertIn("validator report contains 1 ERROR notices", errors)


if __name__ == "__main__":
    unittest.main()
