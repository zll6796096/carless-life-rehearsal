import tempfile
import unittest
from pathlib import Path

from scripts.prepare_hakusan_osm import canonicalize_osm


BOUNDS = ("36.44917", "136.4535465", "36.58471", "136.6223390")


class CanonicalOsmTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write_osm(
        self,
        filename: str,
        *,
        generator: str,
        osm_base: str,
        reverse: bool = False,
    ) -> Path:
        node_one = (
            '<node lon="136.50" user="mapper-one" id="1" lat="36.50" '
            'uid="101" version="2" timestamp="2026-01-01T00:00:00Z" />'
        )
        node_two_tags = (
            '<tag v="Crossing B" k="name"/><tag v="crossing" k="highway"/>'
            if not reverse
            else '<tag k="highway" v="crossing"/><tag k="name" v="Crossing B"/>'
        )
        node_two = (
            '<node id="2" lat="36.51" lon="136.51" version="1" '
            f'user="mapper-two" uid="202">{node_two_tags}</node>'
        )
        way_tags = (
            '<tag k="name" v="Pilot Road"/><tag k="highway" v="residential"/>'
            if not reverse
            else '<tag v="residential" k="highway"/><tag v="Pilot Road" k="name"/>'
        )
        way = (
            '<way version="3" uid="303" user="mapper-three" id="20">'
            f'<nd ref="2"/><nd ref="1"/>{way_tags}</way>'
        )
        relation_tags = (
            '<tag k="type" v="restriction"/><tag k="restriction" v="no_left_turn"/>'
            if not reverse
            else '<tag v="no_left_turn" k="restriction"/><tag v="restriction" k="type"/>'
        )
        relation = (
            '<relation id="30" version="1" user="mapper-four" uid="404">'
            '<member role="from" ref="20" type="way"/>'
            f'{relation_tags}</relation>'
        )
        elements = [node_two, relation, way, node_one]
        if reverse:
            elements.reverse()
        payload = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<osm generator="{generator}" version="0.6">'
            '<note>OpenStreetMap data under ODbL</note>'
            f'<meta osm_base="{osm_base}"/>'
            + "".join(elements)
            + "</osm>"
        )
        path = self.root / filename
        path.write_text(payload, encoding="utf-8")
        return path

    def test_mutable_overpass_metadata_does_not_change_output(self) -> None:
        first = self._write_osm(
            "one.osm",
            generator="Overpass 0.7.1",
            osm_base="2026-09-04T00:00:00Z",
        )
        second = self._write_osm(
            "two.osm",
            generator="Overpass 0.7.2",
            osm_base="2026-09-05T00:00:00Z",
            reverse=True,
        )

        first_destination = self.root / "first-canonical.osm"
        second_destination = self.root / "second-canonical.osm"
        first_bytes = canonicalize_osm(first, first_destination, BOUNDS)
        second_bytes = canonicalize_osm(second, second_destination, BOUNDS)

        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(first_destination.read_bytes(), first_bytes)
        self.assertNotIn(b"osm_base", first_bytes)
        self.assertNotIn(b"Overpass", first_bytes)
        self.assertNotIn(b"user=", first_bytes)
        self.assertNotIn(b"uid=", first_bytes)

    def test_output_has_fixed_bounds_and_stable_element_order(self) -> None:
        source = self._write_osm(
            "unordered.osm",
            generator="Overpass",
            osm_base="2026-09-05T00:00:00Z",
        )

        result = canonicalize_osm(source, self.root / "canonical.osm", BOUNDS)

        self.assertIn(
            b'<bounds minlat="36.44917" minlon="136.4535465" '
            b'maxlat="36.58471" maxlon="136.6223390"',
            result,
        )
        self.assertLess(result.index(b'<node id="1"'), result.index(b'<node id="2"'))
        self.assertLess(result.index(b'<node id="2"'), result.index(b'<way id="20"'))
        self.assertLess(result.index(b'<way id="20"'), result.index(b'<relation id="30"'))
        self.assertLess(result.index(b'<nd ref="2"'), result.index(b'<nd ref="1"'))
        self.assertLess(
            result.index(b'<tag k="highway" v="residential"'),
            result.index(b'<tag k="name" v="Pilot Road"'),
        )

    def test_rejects_input_without_osm_elements(self) -> None:
        source = self.root / "empty.osm"
        source.write_text(
            '<osm version="0.6"><meta osm_base="2026-09-05T00:00:00Z"/></osm>',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "no node, way, or relation elements"):
            canonicalize_osm(source, self.root / "out.osm", BOUNDS)

    def test_malformed_input_does_not_replace_existing_destination(self) -> None:
        source = self.root / "malformed.osm"
        source.write_text("<osm><node", encoding="utf-8")
        destination = self.root / "canonical.osm"
        destination.write_bytes(b"trusted")

        with self.assertRaises(Exception):
            canonicalize_osm(source, destination, BOUNDS)

        self.assertEqual(destination.read_bytes(), b"trusted")


if __name__ == "__main__":
    unittest.main()
