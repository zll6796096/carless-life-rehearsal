import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_hakusan_otp_contract import validate_otp_contract


ROOT = Path(__file__).resolve().parents[1]


class OtpContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        shutil.copytree(ROOT / "data" / "hakusan", self.root / "data" / "hakusan")
        shutil.copytree(
            ROOT / "config" / "otp" / "hakusan",
            self.root / "config" / "otp" / "hakusan",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @property
    def sources_path(self) -> Path:
        return self.root / "data" / "hakusan" / "otp-sources.json"

    def _sources(self) -> dict[str, object]:
        return json.loads(self.sources_path.read_text(encoding="utf-8"))

    def _write_sources(self, payload: dict[str, object]) -> None:
        self.sources_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_committed_contract_is_valid(self) -> None:
        self.assertEqual(validate_otp_contract(ROOT), [])

    def test_latest_otp_url_is_rejected(self) -> None:
        payload = self._sources()
        payload["otp"]["artifact_url"] = "https://example.test/latest.jar"
        self._write_sources(payload)

        self.assertIn("OTP artifact URL must pin v2.9.0", validate_otp_contract(self.root))

    def test_java_major_is_pinned(self) -> None:
        payload = self._sources()
        payload["otp"]["java_major"] = 21
        self._write_sources(payload)

        self.assertIn("OTP Java major must be 25", validate_otp_contract(self.root))

    def test_config_hash_drift_is_rejected(self) -> None:
        (self.root / "config" / "otp" / "hakusan" / "build-config.json").write_text(
            "{}\n",
            encoding="utf-8",
        )

        self.assertIn("OTP build-config sha256 mismatch", validate_otp_contract(self.root))

    def test_osm_query_requires_historical_date_bbox_and_license(self) -> None:
        query_path = self.root / "config" / "otp" / "hakusan" / "osm-overpass.ql"
        query_path.write_text('[out:xml];way["highway"];out;\n', encoding="utf-8")
        payload = self._sources()
        payload["osm"]["license"]["url"] = "https://example.test/license"
        self._write_sources(payload)

        errors = validate_otp_contract(self.root)

        self.assertIn("OSM query sha256 mismatch", errors)
        self.assertIn("OSM query must pin historical timestamp", errors)
        self.assertIn("OSM query must pin approved bbox", errors)
        self.assertIn("OSM license URL must pin ODbL 1.0", errors)

    def test_gtfs_identity_counts_and_sha_formats_are_pinned(self) -> None:
        payload = self._sources()
        payload["gtfs"]["source_uid"] = "mutable"
        payload["gtfs"]["source_sha256"] = "not-a-sha"
        payload["gtfs"]["expected"]["route_count"] = 21
        payload["osm"]["canonical_sha256"] = "ABC"
        self._write_sources(payload)

        errors = validate_otp_contract(self.root)

        self.assertIn("GTFS source UID mismatch", errors)
        self.assertIn("GTFS source sha256 must be lowercase hexadecimal", errors)
        self.assertIn("GTFS expected route_count must be 11", errors)
        self.assertIn("OSM canonical sha256 must be lowercase hexadecimal", errors)

    def test_scenario_and_graphql_contract_are_pinned(self) -> None:
        payload = self._sources()
        payload["runtime"]["graphql_endpoint_path"] = "/otp/routers/default/index/graphql"
        payload["runtime"]["port"] = 8080
        payload["scenario"]["service_date"] = "2026-09-09"
        payload["scenario"]["outbound_time"] = "07:00:00+09:00"
        payload["scenario"]["destination_id"] = "station-matto"
        self._write_sources(payload)

        errors = validate_otp_contract(self.root)

        self.assertIn("OTP GraphQL endpoint path must be /otp/gtfs/v1", errors)
        self.assertIn("OTP local port must be 18081", errors)
        self.assertIn("scenario service date must be 2026-09-08", errors)
        self.assertIn("scenario outbound time must be 06:50:00+09:00", errors)
        self.assertIn("scenario destination must be the hospital", errors)


if __name__ == "__main__":
    unittest.main()
