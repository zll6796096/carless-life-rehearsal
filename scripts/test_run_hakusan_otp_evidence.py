import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.run_hakusan_otp_evidence import (
    PLAN_QUERY,
    EvidenceError,
    normalize_gtfs_id,
    parse_java_major,
    sanitize_evidence_path,
    scan_otp_log,
    stop_process,
    validate_java_major,
    validate_plan_response,
    validate_route_inventory,
    validate_stop_inventory,
    write_json_atomic,
)


class FakeProcess:
    def __init__(self, *, timeout_on_first_wait: bool = False) -> None:
        self.timeout_on_first_wait = timeout_on_first_wait
        self.terminated = False
        self.killed = False
        self.wait_calls = 0

    def poll(self) -> int | None:
        return None if not self.killed else -9

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float) -> int:
        del timeout
        self.wait_calls += 1
        if self.timeout_on_first_wait and self.wait_calls == 1:
            raise subprocess.TimeoutExpired("otp", 1)
        return -9 if self.killed else -15


class EvidenceValidationTests(unittest.TestCase):
    @staticmethod
    def _plan(modes: list[str], route_id: str = "F:allowed") -> dict[str, object]:
        legs: list[dict[str, object]] = []
        for mode in modes:
            leg: dict[str, object] = {"mode": mode}
            if mode == "BUS":
                leg["route"] = {"gtfsId": route_id} if route_id else None
            else:
                leg["route"] = None
            legs.append(leg)
        return {
            "data": {
                "planConnection": {
                    "routingErrors": [],
                    "edges": [{"node": {"duration": 900.0, "legs": legs}}],
                }
            }
        }

    def test_normalize_gtfs_id_removes_only_feed_prefix(self) -> None:
        self.assertEqual(normalize_gtfs_id("F:allowed"), "allowed")
        self.assertEqual(normalize_gtfs_id("allowed"), "allowed")
        self.assertEqual(normalize_gtfs_id("F:route:variant"), "route:variant")

    def test_route_inventory_must_equal_allowlist(self) -> None:
        errors = validate_route_inventory(
            {"data": {"routes": [{"gtfsId": "F:allowed"}]}},
            {"allowed", "other"},
        )

        self.assertIn("OTP route inventory missing: other", errors)

    def test_route_inventory_rejects_unexpected_and_graphql_errors(self) -> None:
        unexpected = validate_route_inventory(
            {"data": {"routes": [{"gtfsId": "F:excluded"}]}},
            {"allowed"},
        )
        graphql = validate_route_inventory(
            {"errors": [{"message": "query failed"}]},
            {"allowed"},
        )

        self.assertIn("OTP route inventory unexpected: excluded", unexpected)
        self.assertIn("GraphQL error: query failed", graphql)

    def test_stop_inventory_requires_every_access_stop(self) -> None:
        errors = validate_stop_inventory(
            {"data": {"stops": [{"gtfsId": "F:stop-a"}]}},
            {"stop-a", "stop-b"},
        )

        self.assertIn("OTP stop inventory missing: stop-b", errors)

    def test_plan_requires_walk_and_allowed_bus(self) -> None:
        result = validate_plan_response(self._plan(["WALK", "BUS"]), {"allowed"})

        self.assertEqual(result.errors, [])
        self.assertEqual(result.modes, ["WALK", "BUS"])
        self.assertEqual(result.route_ids, ["allowed"])
        self.assertEqual(result.duration_seconds, 900)

    def test_excluded_bus_route_fails(self) -> None:
        result = validate_plan_response(
            self._plan(["WALK", "BUS"], route_id="F:excluded"),
            {"allowed"},
        )

        self.assertIn("OTP itinerary uses non-allowlisted route: excluded", result.errors)

    def test_plan_reports_graphql_and_routing_errors(self) -> None:
        graphql = validate_plan_response(
            {"errors": [{"message": "bad query"}]},
            {"allowed"},
        )
        routing = validate_plan_response(
            {
                "data": {
                    "planConnection": {
                        "routingErrors": [
                            {"code": "LOCATION_NOT_FOUND", "description": "not linked"}
                        ],
                        "edges": [],
                    }
                }
            },
            {"allowed"},
        )

        self.assertIn("GraphQL error: bad query", graphql.errors)
        self.assertIn("OTP routing error LOCATION_NOT_FOUND: not linked", routing.errors)

    def test_plan_rejects_no_itinerary_walk_or_bus(self) -> None:
        no_itinerary = validate_plan_response(
            {"data": {"planConnection": {"routingErrors": [], "edges": []}}},
            {"allowed"},
        )
        no_walk = validate_plan_response(self._plan(["BUS"]), {"allowed"})
        no_bus = validate_plan_response(self._plan(["WALK"]), {"allowed"})

        self.assertIn("OTP returned no itinerary", no_itinerary.errors)
        self.assertIn("OTP itinerary has no WALK leg", no_walk.errors)
        self.assertIn("OTP itinerary has no BUS leg", no_bus.errors)

    def test_bus_leg_requires_route_id(self) -> None:
        result = validate_plan_response(
            self._plan(["WALK", "BUS"], route_id=""),
            {"allowed"},
        )

        self.assertIn("OTP BUS leg is missing route gtfsId", result.errors)

    def test_java_major_is_parsed_and_mismatch_fails(self) -> None:
        self.assertEqual(parse_java_major('openjdk version "25.0.3" 2026-04-21 LTS'), 25)
        self.assertEqual(parse_java_major('java version "1.8.0_401"'), 8)
        with self.assertRaisesRegex(EvidenceError, "requires Java major 25, found 21"):
            validate_java_major('openjdk version "21.0.8"', 25)

    def test_config_warning_log_scan_is_narrow(self) -> None:
        text = "\n".join(
            [
                "WARN No elevation data supplied",
                "WARN Unrecognized configuration property: mystery",
                "INFO Graph built",
            ]
        )

        self.assertEqual(
            scan_otp_log(text),
            ["WARN Unrecognized configuration property: mystery"],
        )

    def test_plan_query_uses_new_api_and_transit_constraints(self) -> None:
        self.assertIn("planConnection", PLAN_QUERY)
        self.assertNotIn("plan(", PLAN_QUERY)
        self.assertIn("routingErrors", PLAN_QUERY)
        self.assertIn("route {", PLAN_QUERY)

    def test_evidence_paths_are_relative_or_basename_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            inside = root / "data" / "evidence.json"
            outside = Path("/private/tmp/private-source.zip")

            self.assertEqual(sanitize_evidence_path(inside, root), "data/evidence.json")
            self.assertEqual(sanitize_evidence_path(outside, root), "private-source.zip")

    def test_atomic_json_writer_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "summary.json"
            with self.assertRaisesRegex(EvidenceError, "absolute path"):
                write_json_atomic(destination, {"input": "/Users/example/private.zip"})
            self.assertFalse(destination.exists())

            write_json_atomic(destination, {"status": "PASS", "input": "pilot.zip"})
            self.assertEqual(json.loads(destination.read_text()), {"input": "pilot.zip", "status": "PASS"})

    def test_stop_process_escalates_to_kill_after_timeout(self) -> None:
        process = FakeProcess(timeout_on_first_wait=True)

        outcome = stop_process(process, timeout=0.01)

        self.assertTrue(process.terminated)
        self.assertTrue(process.killed)
        self.assertEqual(outcome, "killed")


if __name__ == "__main__":
    unittest.main()
