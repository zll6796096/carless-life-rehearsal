import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.prepare_hakusan_otp import (
    PreparationError,
    inspect_pilot_gtfs,
    prepare_pilot_gtfs,
    sha256_file,
)


REQUIRED_FILES = [
    "agency.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "fare_attributes.txt",
    "fare_rules.txt",
    "feed_info.txt",
    "routes.txt",
    "shapes.txt",
    "stop_times.txt",
    "stops.txt",
    "translations.txt",
    "trips.txt",
]


def _csv_bytes(fieldnames: list[str], rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


class PilotGtfsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.contract_root = self.root / "data/hakusan"
        self.contract_root.mkdir(parents=True)
        self.source_zip = self.root / "source.zip"
        self.output_zip = self.root / "pilot.zip"
        self._write_contract()
        self._write_source()
        self.source_sha = sha256_file(self.source_zip)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write_contract(self, *, extra_allowed_route: str | None = None) -> None:
        allowed_routes = [
            {"route_id": "allowed-route", "name_ja": "Allowed", "service_type": "fixed_route"}
        ]
        if extra_allowed_route is not None:
            allowed_routes.append(
                {"route_id": extra_allowed_route, "name_ja": "Missing", "service_type": "fixed_route"}
            )
        (self.contract_root / "manifest.json").write_text(
            json.dumps({"feed": {"artifact": {"required_files": REQUIRED_FILES}}}),
            encoding="utf-8",
        )
        (self.contract_root / "route-rules.json").write_text(
            json.dumps(
                {
                    "default_policy": "deny",
                    "allowed_routes": allowed_routes,
                    "excluded_routes": [
                        {
                            "route_id": "excluded-route",
                            "name_ja": "Excluded",
                            "reason_code": "reservation_required",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (self.contract_root / "destinations.json").write_text(
            json.dumps(
                {
                    "destinations": [
                        {
                            "id": "hospital",
                            "category": "hospital",
                            "access_stop_ids": ["allowed-stop"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def _source_tables(
        self,
        *,
        include_unclassified: bool = False,
        broken_reference: str | None = None,
    ) -> dict[str, bytes]:
        routes = [
            {"route_id": "allowed-route", "agency_id": "agency", "route_long_name": "Allowed", "route_type": "3"},
            {"route_id": "excluded-route", "agency_id": "agency", "route_long_name": "Excluded", "route_type": "3"},
        ]
        trips = [
            {
                "route_id": "allowed-route",
                "service_id": "weekday",
                "trip_id": "allowed-trip",
                "trip_headsign": "Hospital",
                "shape_id": "allowed-shape",
            },
            {
                "route_id": "excluded-route",
                "service_id": "weekend",
                "trip_id": "excluded-trip",
                "trip_headsign": "Reserved",
                "shape_id": "excluded-shape",
            },
        ]
        if include_unclassified:
            routes.append(
                {"route_id": "new-route", "agency_id": "agency", "route_long_name": "New", "route_type": "3"}
            )
            trips.append(
                {
                    "route_id": "new-route",
                    "service_id": "weekday",
                    "trip_id": "new-trip",
                    "trip_headsign": "New",
                    "shape_id": "new-shape",
                }
            )
        allowed_stop_reference = "missing-stop" if broken_reference == "stop" else "allowed-stop"
        allowed_shape_reference = "missing-shape" if broken_reference == "shape" else "allowed-shape"
        allowed_service_reference = "missing-service" if broken_reference == "service" else "weekday"
        trips[0]["shape_id"] = allowed_shape_reference
        trips[0]["service_id"] = allowed_service_reference
        fare_id = "missing-fare" if broken_reference == "fare" else "allowed-fare"
        tables = {
            "agency.txt": _csv_bytes(
                ["agency_id", "agency_name", "agency_url", "agency_timezone"],
                [{"agency_id": "agency", "agency_name": "Agency", "agency_url": "https://example.test", "agency_timezone": "Asia/Tokyo"}],
            ),
            "calendar.txt": _csv_bytes(
                ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
                [
                    {"service_id": "weekday", "monday": "1", "tuesday": "1", "wednesday": "1", "thursday": "1", "friday": "1", "saturday": "0", "sunday": "0", "start_date": "20260316", "end_date": "20270315"},
                    {"service_id": "weekend", "monday": "0", "tuesday": "0", "wednesday": "0", "thursday": "0", "friday": "0", "saturday": "1", "sunday": "1", "start_date": "20260316", "end_date": "20270315"},
                ],
            ),
            "calendar_dates.txt": _csv_bytes(
                ["service_id", "date", "exception_type"],
                [
                    {"service_id": "weekday", "date": "20260922", "exception_type": "2"},
                    {"service_id": "weekend", "date": "20260923", "exception_type": "1"},
                ],
            ),
            "fare_attributes.txt": _csv_bytes(
                ["fare_id", "price", "currency_type", "payment_method", "transfers", "agency_id"],
                [
                    {"fare_id": "allowed-fare", "price": "100", "currency_type": "JPY", "payment_method": "0", "transfers": "0", "agency_id": "agency"},
                    {"fare_id": "excluded-fare", "price": "200", "currency_type": "JPY", "payment_method": "0", "transfers": "0", "agency_id": "agency"},
                ],
            ),
            "fare_rules.txt": _csv_bytes(
                ["fare_id", "route_id", "origin_id", "destination_id", "contains_id"],
                [
                    {"fare_id": fare_id, "route_id": "allowed-route", "origin_id": "", "destination_id": "", "contains_id": ""},
                    {"fare_id": "excluded-fare", "route_id": "excluded-route", "origin_id": "", "destination_id": "", "contains_id": ""},
                ],
            ),
            "feed_info.txt": _csv_bytes(
                ["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_start_date", "feed_end_date", "feed_version"],
                [{"feed_publisher_name": "Publisher", "feed_publisher_url": "https://example.test", "feed_lang": "ja", "feed_start_date": "20260316", "feed_end_date": "20270315", "feed_version": "test"}],
            ),
            "routes.txt": _csv_bytes(
                ["route_id", "agency_id", "route_long_name", "route_type"],
                routes,
            ),
            "shapes.txt": _csv_bytes(
                ["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
                [
                    {"shape_id": "allowed-shape", "shape_pt_lat": "36.50", "shape_pt_lon": "136.50", "shape_pt_sequence": "1"},
                    {"shape_id": "excluded-shape", "shape_pt_lat": "36.60", "shape_pt_lon": "136.60", "shape_pt_sequence": "1"},
                    {"shape_id": "new-shape", "shape_pt_lat": "36.55", "shape_pt_lon": "136.55", "shape_pt_sequence": "1"},
                ],
            ),
            "stop_times.txt": _csv_bytes(
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    {"trip_id": "allowed-trip", "arrival_time": "08:00:00", "departure_time": "08:00:00", "stop_id": allowed_stop_reference, "stop_sequence": "1"},
                    {"trip_id": "allowed-trip", "arrival_time": "08:10:00", "departure_time": "08:10:00", "stop_id": "allowed-other", "stop_sequence": "2"},
                    {"trip_id": "excluded-trip", "arrival_time": "09:00:00", "departure_time": "09:00:00", "stop_id": "excluded-stop", "stop_sequence": "1"},
                ],
            ),
            "stops.txt": _csv_bytes(
                ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"],
                [
                    {"stop_id": "allowed-stop", "stop_name": "Allowed", "stop_lat": "36.50", "stop_lon": "136.50", "location_type": "0", "parent_station": "allowed-parent"},
                    {"stop_id": "allowed-other", "stop_name": "Other", "stop_lat": "36.51", "stop_lon": "136.51", "location_type": "0", "parent_station": ""},
                    {"stop_id": "allowed-parent", "stop_name": "Parent", "stop_lat": "36.50", "stop_lon": "136.50", "location_type": "1", "parent_station": ""},
                    {"stop_id": "excluded-stop", "stop_name": "Excluded", "stop_lat": "36.60", "stop_lon": "136.60", "location_type": "0", "parent_station": ""},
                ],
            ),
            "translations.txt": _csv_bytes(
                ["table_name", "field_name", "language", "translation", "record_id", "record_sub_id", "field_value"],
                [
                    {"table_name": "routes", "field_name": "route_long_name", "language": "en", "translation": "Allowed", "record_id": "allowed-route", "record_sub_id": "", "field_value": ""},
                    {"table_name": "routes", "field_name": "route_long_name", "language": "en", "translation": "Excluded", "record_id": "excluded-route", "record_sub_id": "", "field_value": ""},
                    {"table_name": "stops", "field_name": "stop_name", "language": "en", "translation": "Allowed", "record_id": "allowed-stop", "record_sub_id": "", "field_value": ""},
                    {"table_name": "stops", "field_name": "stop_name", "language": "en", "translation": "Excluded", "record_id": "excluded-stop", "record_sub_id": "", "field_value": ""},
                    {"table_name": "feed_info", "field_name": "feed_publisher_name", "language": "en", "translation": "Publisher", "record_id": "", "record_sub_id": "", "field_value": "Publisher"},
                ],
            ),
            "trips.txt": _csv_bytes(
                ["route_id", "service_id", "trip_id", "trip_headsign", "shape_id"],
                trips,
            ),
        }
        return tables

    def _write_source(
        self,
        *,
        include_unclassified: bool = False,
        broken_reference: str | None = None,
    ) -> None:
        with zipfile.ZipFile(self.source_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in REQUIRED_FILES:
                archive.writestr(
                    name,
                    self._source_tables(
                        include_unclassified=include_unclassified,
                        broken_reference=broken_reference,
                    )[name],
                )
        self.source_sha = hashlib.sha256(self.source_zip.read_bytes()).hexdigest()

    def _rows(self, name: str) -> list[dict[str, str]]:
        with zipfile.ZipFile(self.output_zip) as archive:
            text = io.TextIOWrapper(archive.open(name), encoding="utf-8", newline="")
            return list(csv.DictReader(text))

    def test_source_sha_must_match(self) -> None:
        with self.assertRaisesRegex(PreparationError, "source GTFS sha256 mismatch"):
            prepare_pilot_gtfs(
                self.contract_root,
                self.source_zip,
                self.output_zip,
                "0" * 64,
            )

    def test_excluded_route_and_dependencies_are_removed(self) -> None:
        summary = prepare_pilot_gtfs(
            self.contract_root,
            self.source_zip,
            self.output_zip,
            self.source_sha,
        )

        self.assertEqual(summary["route_ids"], ["allowed-route"])
        self.assertEqual(summary["trip_ids"], ["allowed-trip"])
        self.assertEqual(summary["shape_ids"], ["allowed-shape"])
        self.assertNotIn("excluded-stop", summary["stop_ids"])
        self.assertEqual([row["service_id"] for row in self._rows("calendar.txt")], ["weekday"])
        self.assertEqual([row["fare_id"] for row in self._rows("fare_attributes.txt")], ["allowed-fare"])

    def test_output_is_byte_identical_across_runs(self) -> None:
        second_output = self.root / "pilot-second.zip"

        prepare_pilot_gtfs(self.contract_root, self.source_zip, self.output_zip, self.source_sha)
        prepare_pilot_gtfs(self.contract_root, self.source_zip, second_output, self.source_sha)

        self.assertEqual(self.output_zip.read_bytes(), second_output.read_bytes())

    def test_destination_access_stop_and_parent_are_preserved(self) -> None:
        summary = prepare_pilot_gtfs(
            self.contract_root,
            self.source_zip,
            self.output_zip,
            self.source_sha,
        )

        self.assertIn("allowed-stop", summary["stop_ids"])
        self.assertIn("allowed-parent", summary["stop_ids"])

    def test_translations_for_removed_records_are_filtered(self) -> None:
        prepare_pilot_gtfs(self.contract_root, self.source_zip, self.output_zip, self.source_sha)

        translation_ids = [row["record_id"] for row in self._rows("translations.txt")]
        self.assertIn("allowed-route", translation_ids)
        self.assertIn("allowed-stop", translation_ids)
        self.assertIn("", translation_ids)
        self.assertNotIn("excluded-route", translation_ids)
        self.assertNotIn("excluded-stop", translation_ids)

    def test_unclassified_route_fails_closed(self) -> None:
        self._write_source(include_unclassified=True)

        with self.assertRaisesRegex(PreparationError, "unclassified route: new-route"):
            prepare_pilot_gtfs(
                self.contract_root,
                self.source_zip,
                self.output_zip,
                self.source_sha,
            )

    def test_missing_allowlisted_route_fails_closed(self) -> None:
        self._write_contract(extra_allowed_route="missing-route")

        with self.assertRaisesRegex(PreparationError, "allowlisted route missing from source: missing-route"):
            prepare_pilot_gtfs(
                self.contract_root,
                self.source_zip,
                self.output_zip,
                self.source_sha,
            )

    def test_broken_stop_shape_service_and_fare_references_fail(self) -> None:
        expected_messages = {
            "stop": "stop_times.txt references missing stop_id: missing-stop",
            "shape": "trips.txt references missing shape_id: missing-shape",
            "service": "trips.txt references missing service_id: missing-service",
            "fare": "fare_rules.txt references missing fare_id: missing-fare",
        }
        for broken_reference, expected_message in expected_messages.items():
            with self.subTest(broken_reference=broken_reference):
                self._write_source(broken_reference=broken_reference)
                with self.assertRaisesRegex(PreparationError, expected_message):
                    prepare_pilot_gtfs(
                        self.contract_root,
                        self.source_zip,
                        self.output_zip,
                        self.source_sha,
                    )

    def test_inspection_rejects_excluded_route(self) -> None:
        self.output_zip.write_bytes(self.source_zip.read_bytes())

        errors = inspect_pilot_gtfs(self.contract_root, self.output_zip)

        self.assertIn("pilot GTFS contains excluded route: excluded-route", errors)


if __name__ == "__main__":
    unittest.main()
