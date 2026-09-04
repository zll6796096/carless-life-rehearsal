import hashlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request

from scripts.fetch_hakusan_otp_inputs import (
    ArtifactSource,
    FetchError,
    OsmSource,
    download_checked,
    fetch_overpass_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, final_url: str) -> None:
        super().__init__(payload)
        self.final_url = final_url

    def geturl(self) -> str:
        return self.final_url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class FetchInputsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def _artifact(payload: bytes, *, url: str = "https://github.com/example/otp.jar") -> ArtifactSource:
        return ArtifactSource(
            url=url,
            sha256=sha256_bytes(payload),
            size_bytes=len(payload),
            allowed_hosts=frozenset({"github.com", ".githubusercontent.com"}),
        )

    @staticmethod
    def _opener(payload: bytes, *, final_url: str = "https://github.com/example/otp.jar"):
        def open_response(request: Request, *, timeout: float) -> FakeResponse:
            del request, timeout
            return FakeResponse(payload, final_url)

        return open_response

    def test_checksum_mismatch_does_not_replace_destination(self) -> None:
        destination = self.root / "otp.jar"
        destination.write_bytes(b"trusted")
        source = ArtifactSource(
            url="https://github.com/example/otp.jar",
            sha256="0" * 64,
            size_bytes=3,
            allowed_hosts=frozenset({"github.com", ".githubusercontent.com"}),
        )

        with self.assertRaisesRegex(FetchError, "sha256 mismatch"):
            download_checked(source, destination, opener=self._opener(b"bad"))

        self.assertEqual(destination.read_bytes(), b"trusted")
        self.assertEqual(list(self.root.glob(".otp.jar.*")), [])

    def test_unexpected_redirect_host_is_rejected(self) -> None:
        payload = b"asset"
        source = self._artifact(payload)

        with self.assertRaisesRegex(FetchError, "unexpected redirect host"):
            download_checked(
                source,
                self.root / "otp.jar",
                opener=self._opener(payload, final_url="https://attacker.example/otp.jar"),
            )

        self.assertFalse((self.root / "otp.jar").exists())

    def test_initial_url_must_be_https_and_allowlisted(self) -> None:
        for url in ("http://github.com/example/otp.jar", "https://attacker.example/otp.jar"):
            with self.subTest(url=url), self.assertRaisesRegex(FetchError, "source URL"):
                download_checked(
                    self._artifact(b"asset", url=url),
                    self.root / "otp.jar",
                    opener=self._opener(b"asset"),
                )

    def test_valid_download_atomically_replaces_stale_cache(self) -> None:
        destination = self.root / "nested" / "otp.jar"
        destination.parent.mkdir()
        destination.write_bytes(b"stale")
        payload = b"verified asset"

        result = download_checked(
            self._artifact(payload),
            destination,
            opener=self._opener(
                payload,
                final_url="https://release-assets.githubusercontent.com/example/otp.jar",
            ),
        )

        self.assertEqual(result, destination)
        self.assertEqual(destination.read_bytes(), payload)

    def test_valid_cached_file_is_reused_without_network(self) -> None:
        destination = self.root / "otp.jar"
        payload = b"verified asset"
        destination.write_bytes(payload)

        def unexpected_opener(_request: Request, *, timeout: float) -> FakeResponse:
            del timeout
            raise AssertionError("network must not be used for a valid cached file")

        result = download_checked(self._artifact(payload), destination, opener=unexpected_opener)

        self.assertEqual(result, destination)

    def test_size_mismatch_is_rejected(self) -> None:
        payload = b"asset"
        source = ArtifactSource(
            url="https://github.com/example/otp.jar",
            sha256=sha256_bytes(payload),
            size_bytes=len(payload) + 1,
            allowed_hosts=frozenset({"github.com"}),
        )

        with self.assertRaisesRegex(FetchError, "size mismatch"):
            download_checked(source, self.root / "otp.jar", opener=self._opener(payload))

    def test_overpass_post_is_atomic_and_domain_limited(self) -> None:
        raw_destination = self.root / "hakusan.osm"
        payload = b'<?xml version="1.0"?><osm version="0.6"><node id="1"/></osm>'
        observed: dict[str, object] = {}

        def opener(request: Request, *, timeout: float) -> FakeResponse:
            observed["url"] = request.full_url
            observed["data"] = request.data
            observed["timeout"] = timeout
            return FakeResponse(payload, "https://overpass-api.de/api/interpreter")

        result = fetch_overpass_snapshot(
            OsmSource(
                endpoint="https://overpass-api.de/api/interpreter",
                allowed_hosts=frozenset({"overpass-api.de"}),
            ),
            b'[out:xml][date:"2026-09-03T00:00:00Z"];out;',
            raw_destination,
            opener=opener,
        )

        self.assertEqual(result, raw_destination)
        self.assertEqual(raw_destination.read_bytes(), payload)
        self.assertEqual(observed["url"], "https://overpass-api.de/api/interpreter")
        self.assertIn(b"data=", observed["data"])

    def test_overpass_redirect_outside_allowlist_preserves_existing_file(self) -> None:
        raw_destination = self.root / "hakusan.osm"
        raw_destination.write_bytes(b"existing")

        def opener(_request: Request, *, timeout: float) -> FakeResponse:
            del timeout
            return FakeResponse(b"untrusted", "https://attacker.example/api")

        with self.assertRaisesRegex(FetchError, "unexpected redirect host"):
            fetch_overpass_snapshot(
                OsmSource(
                    endpoint="https://overpass-api.de/api/interpreter",
                    allowed_hosts=frozenset({"overpass-api.de"}),
                ),
                b"query",
                raw_destination,
                opener=opener,
            )

        self.assertEqual(raw_destination.read_bytes(), b"existing")

    def test_cli_can_run_as_a_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/fetch_hakusan_otp_inputs.py", "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Acquire pinned Hakusan OTP inputs", result.stdout)


if __name__ == "__main__":
    unittest.main()
