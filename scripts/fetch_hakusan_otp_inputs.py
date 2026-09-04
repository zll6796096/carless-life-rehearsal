#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

try:
    from scripts.prepare_hakusan_osm import Bounds, canonicalize_osm
    from scripts.validate_hakusan_otp_contract import validate_otp_contract
except ModuleNotFoundError:
    from prepare_hakusan_osm import Bounds, canonicalize_osm
    from validate_hakusan_otp_contract import validate_otp_contract


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_BBOX_PATTERN = re.compile(r"\[bbox:([^,\]]+),([^,\]]+),([^,\]]+),([^\]]+)\]")
_READ_SIZE = 1024 * 1024
_MAX_OSM_BYTES = 256 * 1024 * 1024

ResponseOpener = Callable[..., BinaryIO]


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArtifactSource:
    url: str
    sha256: str
    size_bytes: int
    allowed_hosts: frozenset[str]


@dataclass(frozen=True)
class OsmSource:
    endpoint: str
    allowed_hosts: frozenset[str]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_READ_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _allowed_host(host: str | None, allowed_hosts: frozenset[str]) -> bool:
    if host is None:
        return False
    normalized = host.lower().rstrip(".")
    for allowed in allowed_hosts:
        rule = allowed.lower().rstrip(".")
        if rule.startswith("."):
            if normalized.endswith(rule) and normalized != rule[1:]:
                return True
        elif normalized == rule:
            return True
    return False


def _validate_https_url(url: str, allowed_hosts: frozenset[str], label: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not _allowed_host(parsed.hostname, allowed_hosts):
        raise FetchError(f"{label} source URL must use HTTPS and an allowlisted host")
    if parsed.username is not None or parsed.password is not None:
        raise FetchError(f"{label} source URL must not contain credentials")


def _validate_final_url(response: BinaryIO, allowed_hosts: frozenset[str], label: str) -> None:
    geturl = getattr(response, "geturl", None)
    if not callable(geturl):
        raise FetchError(f"{label} response did not expose its final URL")
    final_url = geturl()
    parsed = urlparse(final_url)
    if parsed.scheme != "https" or not _allowed_host(parsed.hostname, allowed_hosts):
        raise FetchError(f"{label} unexpected redirect host: {parsed.hostname or '<missing>'}")


def _matches(path: Path, expected_sha256: str, expected_size: int) -> bool:
    try:
        return path.is_file() and path.stat().st_size == expected_size and _sha256(path) == expected_sha256
    except OSError:
        return False


def _temporary_sibling(destination: Path) -> tuple[Path, BinaryIO]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        mode="w+b",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        delete=False,
    )
    return Path(temporary.name), temporary


def _copy_bounded(
    response: BinaryIO,
    output: BinaryIO,
    *,
    maximum_bytes: int,
    digest: Any | None = None,
) -> int:
    total = 0
    while True:
        chunk = response.read(_READ_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > maximum_bytes:
            raise FetchError(f"download exceeded maximum size of {maximum_bytes} bytes")
        output.write(chunk)
        if digest is not None:
            digest.update(chunk)
    return total


def download_checked(
    source: ArtifactSource,
    destination: Path,
    *,
    opener: ResponseOpener = urlopen,
    timeout: float = 60.0,
) -> Path:
    """Download to a temporary sibling, validate final host/size/hash, then replace."""

    _validate_https_url(source.url, source.allowed_hosts, "artifact")
    if _SHA256_PATTERN.fullmatch(source.sha256) is None:
        raise FetchError("artifact expected sha256 must be lowercase hexadecimal")
    if source.size_bytes <= 0:
        raise FetchError("artifact expected size must be positive")
    if _matches(destination, source.sha256, source.size_bytes):
        return destination

    temporary_path: Path | None = None
    temporary_file: BinaryIO | None = None
    try:
        request = Request(source.url, headers={"User-Agent": "carless-life-hakusan-gate1/1"})
        try:
            response_context = opener(request, timeout=timeout)
        except (OSError, URLError) as error:
            raise FetchError(f"artifact download failed: {error}") from error
        with response_context as response:
            _validate_final_url(response, source.allowed_hosts, "artifact")
            temporary_path, temporary_file = _temporary_sibling(destination)
            digest = hashlib.sha256()
            actual_size = _copy_bounded(
                response,
                temporary_file,
                maximum_bytes=source.size_bytes,
                digest=digest,
            )
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_file.close()
            temporary_file = None
        if actual_size != source.size_bytes:
            raise FetchError(
                f"artifact size mismatch: expected {source.size_bytes}, got {actual_size}"
            )
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != source.sha256:
            raise FetchError(
                f"artifact sha256 mismatch: expected {source.sha256}, got {actual_sha256}"
            )
        temporary_path.replace(destination)
        return destination
    finally:
        if temporary_file is not None:
            temporary_file.close()
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def fetch_overpass_snapshot(
    source: OsmSource,
    query: bytes,
    raw_destination: Path,
    *,
    opener: ResponseOpener = urlopen,
    timeout: float = 180.0,
) -> Path:
    """POST the tracked query and atomically write the ignored raw response."""

    _validate_https_url(source.endpoint, source.allowed_hosts, "OSM")
    if not query.strip():
        raise FetchError("OSM query must not be empty")
    try:
        query_text = query.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FetchError("OSM query must be UTF-8") from error
    request = Request(
        source.endpoint,
        data=urlencode({"data": query_text}).encode("ascii"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "carless-life-hakusan-gate1/1",
        },
        method="POST",
    )

    temporary_path: Path | None = None
    temporary_file: BinaryIO | None = None
    try:
        try:
            response_context = opener(request, timeout=timeout)
        except (OSError, URLError) as error:
            raise FetchError(f"OSM download failed: {error}") from error
        with response_context as response:
            _validate_final_url(response, source.allowed_hosts, "OSM")
            temporary_path, temporary_file = _temporary_sibling(raw_destination)
            _copy_bounded(response, temporary_file, maximum_bytes=_MAX_OSM_BYTES)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_file.close()
            temporary_file = None
        prefix = temporary_path.read_bytes()[:4096]
        if b"<osm" not in prefix:
            raise FetchError("OSM response is not an OSM XML document")
        temporary_path.replace(raw_destination)
        return raw_destination
    finally:
        if temporary_file is not None:
            temporary_file.close()
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _load_sources(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "data" / "hakusan" / "otp-sources.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FetchError(f"cannot read OTP source contract: {error}") from error
    if not isinstance(payload, dict):
        raise FetchError("OTP source contract must contain a JSON object")
    return payload


def _query_bounds(query: bytes) -> Bounds:
    try:
        query_text = query.decode("utf-8")
    except UnicodeDecodeError as error:
        raise FetchError("OSM query must be UTF-8") from error
    match = _BBOX_PATTERN.search(query_text)
    if match is None:
        raise FetchError("OSM query is missing a global bbox")
    return tuple(part.strip() for part in match.groups())  # type: ignore[return-value]


def _require_external_output(repo_root: Path, output_dir: Path) -> Path:
    external_root = (repo_root / "data" / "external").resolve()
    resolved = output_dir.resolve()
    try:
        resolved.relative_to(external_root)
    except ValueError as error:
        raise FetchError("output directory must be inside data/external") from error
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _fetch_otp(sources: dict[str, Any], output_dir: Path) -> Path:
    otp = sources["otp"]
    source = ArtifactSource(
        url=otp["artifact_url"],
        sha256=otp["sha256"],
        size_bytes=otp["size_bytes"],
        allowed_hosts=frozenset({"github.com", ".githubusercontent.com"}),
    )
    destination = output_dir / otp["artifact_filename"]
    reused = _matches(destination, source.sha256, source.size_bytes)
    result = download_checked(source, destination)
    print(f"OTP JAR {'reused' if reused else 'downloaded'}: {result}")
    return result


def _fetch_osm(repo_root: Path, sources: dict[str, Any], output_dir: Path) -> Path:
    osm = sources["osm"]
    canonical_destination = output_dir / osm["canonical_filename"]
    if _matches(canonical_destination, osm["canonical_sha256"], osm["canonical_size_bytes"]):
        print(f"Canonical OSM reused: {canonical_destination}")
        return canonical_destination

    query_path = repo_root / osm["query_path"]
    query = query_path.read_bytes()
    raw_destination = output_dir / "hakusan-20260903.osm"
    raw_candidate_path: Path | None = None
    canonical_candidate_path: Path | None = None
    try:
        raw_handle = tempfile.NamedTemporaryFile(
            dir=output_dir,
            prefix=f".{raw_destination.name}.",
            delete=False,
        )
        raw_candidate_path = Path(raw_handle.name)
        raw_handle.close()
        raw_candidate_path.unlink()
        fetch_overpass_snapshot(
            OsmSource(
                endpoint=osm["endpoint"],
                allowed_hosts=frozenset({"overpass-api.de"}),
            ),
            query,
            raw_candidate_path,
        )

        canonical_handle = tempfile.NamedTemporaryFile(
            dir=output_dir,
            prefix=f".{canonical_destination.name}.",
            delete=False,
        )
        canonical_candidate_path = Path(canonical_handle.name)
        canonical_handle.close()
        canonicalize_osm(raw_candidate_path, canonical_candidate_path, _query_bounds(query))
        if not _matches(
            canonical_candidate_path,
            osm["canonical_sha256"],
            osm["canonical_size_bytes"],
        ):
            raise FetchError("canonical OSM size or sha256 mismatch")
        raw_candidate_path.replace(raw_destination)
        raw_candidate_path = None
        canonical_candidate_path.replace(canonical_destination)
        canonical_candidate_path = None
        print(f"Canonical OSM downloaded and verified: {canonical_destination}")
        return canonical_destination
    finally:
        if raw_candidate_path is not None and raw_candidate_path.exists():
            raw_candidate_path.unlink()
        if canonical_candidate_path is not None and canonical_candidate_path.exists():
            canonical_candidate_path.unlink()


def _parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Acquire pinned Hakusan OTP inputs")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "data" / "external" / "hakusan" / "otp",
    )
    parser.add_argument("--artifact", choices=("otp", "osm", "all"), default="all")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    contract_errors = validate_otp_contract(repo_root)
    if contract_errors:
        raise FetchError(f"OTP source contract invalid: {contract_errors[0]}")
    sources = _load_sources(repo_root)
    output_dir = _require_external_output(repo_root, args.output_dir)
    if args.artifact in {"otp", "all"}:
        _fetch_otp(sources, output_dir)
    if args.artifact in {"osm", "all"}:
        _fetch_osm(repo_root, sources, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
