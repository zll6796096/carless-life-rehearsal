#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path


Bounds = tuple[str, str, str, str]

_ELEMENT_ORDER = {"node": 0, "way": 1, "relation": 2}
_REMOVED_ATTRIBUTES = {"uid", "user"}


def _validate_bounds(bounds: Bounds) -> None:
    try:
        south, west, north, east = (Decimal(value) for value in bounds)
    except InvalidOperation as error:
        raise ValueError("OSM bounds must be decimal numbers") from error
    if south >= north or west >= east:
        raise ValueError("OSM bounds must satisfy south < north and west < east")


def _numeric_id(element: ET.Element) -> int:
    raw_id = element.attrib.get("id")
    if raw_id is None:
        raise ValueError(f"OSM {element.tag} element is missing id")
    try:
        return int(raw_id)
    except ValueError as error:
        raise ValueError(f"OSM {element.tag} id must be an integer: {raw_id}") from error


def _clone_element(element: ET.Element) -> ET.Element:
    attributes = {
        key: value
        for key, value in sorted(element.attrib.items())
        if key not in _REMOVED_ATTRIBUTES
    }
    clone = ET.Element(element.tag, attributes)

    children = list(element)
    tags = sorted(
        (child for child in children if child.tag == "tag"),
        key=lambda child: (child.attrib.get("k", ""), child.attrib.get("v", "")),
    )
    non_tags = [child for child in children if child.tag != "tag"]
    for child in (*non_tags, *tags):
        clone.append(_clone_element(child))
    return clone


def canonicalize_osm(source: Path, destination: Path, bounds: Bounds) -> bytes:
    """Write stable OSM XML and return the exact written bytes."""

    _validate_bounds(bounds)
    source_root = ET.parse(source).getroot()
    if source_root.tag != "osm":
        raise ValueError("OSM input root element must be <osm>")

    elements = [element for element in source_root if element.tag in _ELEMENT_ORDER]
    if not elements:
        raise ValueError("OSM input has no node, way, or relation elements")
    elements.sort(key=lambda element: (_ELEMENT_ORDER[element.tag], _numeric_id(element)))

    root = ET.Element(
        "osm",
        {
            "version": "0.6",
            "generator": "carless-life-rehearsal-hakusan-gate1",
        },
    )
    south, west, north, east = bounds
    root.append(
        ET.Element(
            "bounds",
            {
                "minlat": south,
                "minlon": west,
                "maxlat": north,
                "maxlon": east,
            },
        )
    )
    for element in elements:
        root.append(_clone_element(element))

    ET.indent(root, space="  ")
    payload = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    ) + b"\n"

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonicalize an Overpass OSM XML snapshot")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--south", required=True)
    parser.add_argument("--west", required=True)
    parser.add_argument("--north", required=True)
    parser.add_argument("--east", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = canonicalize_osm(
        args.input,
        args.output,
        (args.south, args.west, args.north, args.east),
    )
    print(f"Canonical OSM written: {args.output} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
