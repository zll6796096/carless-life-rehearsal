#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
Converter = Callable[[Path, Path], str]


class PbfPreparationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PbfPreparationResult:
    reused: bool
    sha256: str
    size_bytes: int
    converter_version: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _matches(path: Path, expected_sha256: str, expected_size: int) -> bool:
    try:
        return (
            path.is_file()
            and path.stat().st_size == expected_size
            and sha256_file(path) == expected_sha256
        )
    except OSError:
        return False


def _pyosmium_convert(source: Path, destination: Path) -> str:
    try:
        import osmium
    except ModuleNotFoundError as error:
        raise PbfPreparationError(
            "osmium is not installed; use the pinned isolated converter environment"
        ) from error

    try:
        version = importlib.metadata.version("osmium")
    except importlib.metadata.PackageNotFoundError as error:
        raise PbfPreparationError("cannot determine installed osmium version") from error

    writer: Any | None = None
    try:
        writer = osmium.SimpleWriter(destination, overwrite=True)
        for item in osmium.FileProcessor(source):
            writer.add(item)
    except Exception as error:
        raise PbfPreparationError(f"osmium conversion failed: {error}") from error
    finally:
        if writer is not None:
            writer.close()
    return version


def _check_sha(value: str, label: str) -> None:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise PbfPreparationError(f"{label} must be lowercase SHA-256 hexadecimal")


def prepare_osm_pbf(
    source: Path,
    destination: Path,
    *,
    expected_source_sha256: str,
    expected_output_sha256: str,
    expected_output_size: int,
    expected_output_filename: str,
    expected_converter_version: str,
    converter: Converter = _pyosmium_convert,
) -> PbfPreparationResult:
    """Convert pinned canonical OSM XML to an atomically verified OTP PBF."""

    _check_sha(expected_source_sha256, "expected source OSM sha256")
    _check_sha(expected_output_sha256, "expected output PBF sha256")
    if expected_output_size <= 0:
        raise PbfPreparationError("expected output PBF size must be positive")
    if destination.name != expected_output_filename:
        raise PbfPreparationError(
            "output PBF filename mismatch: "
            f"expected {expected_output_filename}, got {destination.name}"
        )
    if not source.is_file():
        raise PbfPreparationError(f"canonical OSM source is missing: {source}")
    actual_source_sha256 = sha256_file(source)
    if actual_source_sha256 != expected_source_sha256:
        raise PbfPreparationError(
            "source OSM sha256 mismatch: "
            f"expected {expected_source_sha256}, got {actual_source_sha256}"
        )
    if _matches(destination, expected_output_sha256, expected_output_size):
        return PbfPreparationResult(
            reused=True,
            sha256=expected_output_sha256,
            size_bytes=expected_output_size,
            converter_version=expected_converter_version,
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".osm.pbf",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        converter_version = converter(source, temporary_path)
        if converter_version != expected_converter_version:
            raise PbfPreparationError(
                "conversion requires osmium "
                f"{expected_converter_version}, found {converter_version}"
            )
        actual_size = temporary_path.stat().st_size
        if actual_size != expected_output_size:
            raise PbfPreparationError(
                f"output PBF size mismatch: expected {expected_output_size}, got {actual_size}"
            )
        actual_sha256 = sha256_file(temporary_path)
        if actual_sha256 != expected_output_sha256:
            raise PbfPreparationError(
                "output PBF sha256 mismatch: "
                f"expected {expected_output_sha256}, got {actual_sha256}"
            )
        with temporary_path.open("rb") as converted:
            os.fsync(converted.fileno())
        temporary_path.replace(destination)
        return PbfPreparationResult(
            reused=False,
            sha256=actual_sha256,
            size_bytes=actual_size,
            converter_version=converter_version,
        )
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _load_contract(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PbfPreparationError(f"cannot read OTP source contract: {error}") from error
    if not isinstance(payload, dict):
        raise PbfPreparationError("OTP source contract must contain a JSON object")
    return payload


def _parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Prepare pinned Hakusan OSM PBF for OTP")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=repo_root / "data" / "hakusan" / "otp-sources.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    contract = _load_contract(args.contract)
    osm = contract["osm"]
    otp_input = osm["otp_input"]
    converter = osm["converter"]
    result = prepare_osm_pbf(
        args.source,
        args.output,
        expected_source_sha256=osm["canonical_sha256"],
        expected_output_sha256=otp_input["sha256"],
        expected_output_size=otp_input["size_bytes"],
        expected_output_filename=otp_input["filename"],
        expected_converter_version=converter["version"],
    )
    action = "reused" if result.reused else "converted"
    print(f"Hakusan OTP OSM PBF {action}: {args.output}")
    print(f"PBF sha256: {result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
