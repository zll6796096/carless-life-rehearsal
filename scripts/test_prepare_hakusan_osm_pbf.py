import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_hakusan_osm_pbf import PbfPreparationError, prepare_osm_pbf


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class OsmPbfPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source.osm"
        self.destination = self.root / "source.osm.pbf"
        self.source.write_bytes(b"canonical xml")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def _converter(payload: bytes, version: str = "4.3.1"):
        def convert(_source: Path, destination: Path) -> str:
            destination.write_bytes(payload)
            return version

        return convert

    def test_source_hash_mismatch_fails_before_conversion(self) -> None:
        with self.assertRaisesRegex(PbfPreparationError, "source OSM sha256 mismatch"):
            prepare_osm_pbf(
                self.source,
                self.destination,
                expected_source_sha256="0" * 64,
                expected_output_sha256=sha256_bytes(b"pbf"),
                expected_output_size=3,
                expected_output_filename=self.destination.name,
                expected_converter_version="4.3.1",
                converter=self._converter(b"pbf"),
            )

    def test_valid_cached_pbf_is_reused_without_converter(self) -> None:
        payload = b"pinned pbf"
        self.destination.write_bytes(payload)

        def unexpected_converter(_source: Path, _destination: Path) -> str:
            raise AssertionError("converter must not run for a verified cache")

        result = prepare_osm_pbf(
            self.source,
            self.destination,
            expected_source_sha256=sha256_bytes(self.source.read_bytes()),
            expected_output_sha256=sha256_bytes(payload),
            expected_output_size=len(payload),
            expected_output_filename=self.destination.name,
            expected_converter_version="4.3.1",
            converter=unexpected_converter,
        )

        self.assertTrue(result.reused)
        self.assertEqual(result.sha256, sha256_bytes(payload))

    def test_verified_conversion_atomically_replaces_stale_output(self) -> None:
        self.destination.write_bytes(b"stale")
        payload = b"pinned pbf"

        result = prepare_osm_pbf(
            self.source,
            self.destination,
            expected_source_sha256=sha256_bytes(self.source.read_bytes()),
            expected_output_sha256=sha256_bytes(payload),
            expected_output_size=len(payload),
            expected_output_filename=self.destination.name,
            expected_converter_version="4.3.1",
            converter=self._converter(payload),
        )

        self.assertFalse(result.reused)
        self.assertEqual(self.destination.read_bytes(), payload)
        self.assertEqual(list(self.root.glob(".source.osm.pbf.*")), [])

    def test_output_hash_mismatch_preserves_existing_output(self) -> None:
        self.destination.write_bytes(b"trusted")

        with self.assertRaisesRegex(PbfPreparationError, "output PBF sha256 mismatch"):
            prepare_osm_pbf(
                self.source,
                self.destination,
                expected_source_sha256=sha256_bytes(self.source.read_bytes()),
                expected_output_sha256="0" * 64,
                expected_output_size=3,
                expected_output_filename=self.destination.name,
                expected_converter_version="4.3.1",
                converter=self._converter(b"pbf"),
            )

        self.assertEqual(self.destination.read_bytes(), b"trusted")
        self.assertEqual(list(self.root.glob(".source.osm.pbf.*")), [])

    def test_converter_version_mismatch_preserves_existing_output(self) -> None:
        self.destination.write_bytes(b"trusted")
        payload = b"pbf"

        with self.assertRaisesRegex(PbfPreparationError, "requires osmium 4.3.1, found 4.4.0"):
            prepare_osm_pbf(
                self.source,
                self.destination,
                expected_source_sha256=sha256_bytes(self.source.read_bytes()),
                expected_output_sha256=sha256_bytes(payload),
                expected_output_size=len(payload),
                expected_output_filename=self.destination.name,
                expected_converter_version="4.3.1",
                converter=self._converter(payload, version="4.4.0"),
            )

        self.assertEqual(self.destination.read_bytes(), b"trusted")

    def test_output_filename_must_match_contract(self) -> None:
        with self.assertRaisesRegex(PbfPreparationError, "output PBF filename mismatch"):
            prepare_osm_pbf(
                self.source,
                self.destination,
                expected_source_sha256=sha256_bytes(self.source.read_bytes()),
                expected_output_sha256=sha256_bytes(b"pbf"),
                expected_output_size=3,
                expected_output_filename="approved.osm.pbf",
                expected_converter_version="4.3.1",
                converter=self._converter(b"pbf"),
            )


if __name__ == "__main__":
    unittest.main()
