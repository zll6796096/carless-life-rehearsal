from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_state import (  # noqa: E402
    LockConflict,
    LockOwnershipError,
    ProvenanceMismatch,
    acquire_lock_payload,
    assert_lock_owner,
    assert_matching_production_provenance,
    candidate_urls,
    plan_interrupted_pair_recovery,
    release_lock_payload,
)


BUILD_OLD = "11111111-1111-4111-8111-111111111111"
BUILD_NEW = "22222222-2222-4222-8222-222222222222"
SHA_OLD = "a" * 40
SHA_NEW = "b" * 40


def service(
    name: str,
    revision: str,
    *,
    build: str = BUILD_OLD,
    commit: str = SHA_OLD,
    lock_owner: str | None = None,
) -> dict:
    annotations = {
        "run.googleapis.com/ingress": "all",
    }
    if lock_owner:
        annotations["release.carless-life.dev/owner"] = lock_owner
        annotations["release.carless-life.dev/commit"] = SHA_NEW
    return {
        "apiVersion": "serving.knative.dev/v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": "788259830737",
            "resourceVersion": f"rv-{name}-{revision}",
            "annotations": annotations,
            "labels": {
                "source-commit": commit,
                "release-build": build,
                "managed-by": "cloud-build",
                "product": "carless-life",
                "environment": "production",
            },
        },
        "spec": {
            "template": {
                "metadata": {"labels": {}},
                "spec": {
                    "containers": [
                        {
                            "image": (
                                "asia-northeast1-docker.pkg.dev/project/apps/"
                                f"{name}@sha256:{'1' * 64}"
                            )
                        }
                    ]
                },
            },
            "traffic": [{"revisionName": revision, "percent": 100}],
        },
        "status": {
            "url": f"https://{name}-hash-an.a.run.app",
            "latestReadyRevisionName": revision,
            "conditions": [{"type": "Ready", "status": "True"}],
            "traffic": [{"revisionName": revision, "percent": 100}],
        },
    }


def revision(name: str, component: str) -> dict:
    return {
        "metadata": {
            "name": name,
            "labels": {
                "source-commit": SHA_OLD,
                "release-build": BUILD_OLD,
                "managed-by": "cloud-build",
                "product": "carless-life",
                "environment": "production",
                "component": component,
            },
        },
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "imageDigest": (
                "asia-northeast1-docker.pkg.dev/project/apps/"
                f"carless-life-{component}@sha256:{'1' * 64}"
            ),
        },
    }


def apply_payload(current: dict, payload: dict, next_version: str) -> dict:
    updated = copy.deepcopy(current)
    updated["metadata"]["annotations"] = copy.deepcopy(
        payload["metadata"]["annotations"]
    )
    updated["metadata"]["labels"] = copy.deepcopy(payload["metadata"]["labels"])
    updated["metadata"]["resourceVersion"] = next_version
    updated["spec"] = copy.deepcopy(payload["spec"])
    return updated


class ReleaseLockTests(unittest.TestCase):
    def test_overlapping_build_cannot_take_existing_lock(self) -> None:
        coordinator = service(
            "carless-life-api",
            "carless-life-api-00007-aaa",
        )
        first_payload = acquire_lock_payload(
            coordinator,
            BUILD_NEW,
            SHA_NEW,
        )
        locked = apply_payload(coordinator, first_payload, "rv-locked")

        with self.assertRaises(LockConflict):
            acquire_lock_payload(
                locked,
                "33333333-3333-4333-8333-333333333333",
                "c" * 40,
            )

    def test_only_owner_can_release_lock(self) -> None:
        coordinator = service(
            "carless-life-api",
            "carless-life-api-00007-aaa",
            lock_owner=BUILD_NEW,
        )

        with self.assertRaises(LockOwnershipError):
            release_lock_payload(coordinator, BUILD_OLD)

        released = release_lock_payload(coordinator, BUILD_NEW)
        annotations = released["metadata"]["annotations"]
        self.assertNotIn("release.carless-life.dev/owner", annotations)
        self.assertNotIn("release.carless-life.dev/commit", annotations)

    def test_every_mutation_requires_current_lock_owner(self) -> None:
        coordinator = service(
            "carless-life-api",
            "carless-life-api-00007-aaa",
            lock_owner=BUILD_NEW,
        )
        assert_lock_owner(coordinator, BUILD_NEW, SHA_NEW)

        with self.assertRaises(LockOwnershipError):
            assert_lock_owner(coordinator, BUILD_OLD, SHA_OLD)


class PairSafetyTests(unittest.TestCase):
    def test_initial_api_and_web_provenance_must_match(self) -> None:
        api_service = service(
            "carless-life-api",
            "carless-life-api-00007-aaa",
        )
        web_service = service(
            "carless-life-web",
            "carless-life-web-00005-bbb",
            commit="c" * 40,
        )

        with self.assertRaises(ProvenanceMismatch):
            assert_matching_production_provenance(
                api_service,
                revision("carless-life-api-00007-aaa", "api"),
                web_service,
                revision("carless-life-web-00005-bbb", "web"),
            )

    def test_interrupt_after_api_promotion_recovers_both_old(self) -> None:
        recovery = plan_interrupted_pair_recovery(
            lock_owner=BUILD_NEW,
            expected_owner=BUILD_NEW,
            old_pair=("api-old", "web-old"),
            new_pair=("api-new", "web-new"),
            current_pair=("api-new", "web-old"),
            foreign_candidate_present=False,
        )
        self.assertEqual(recovery, ("api-old", "web-old"))

    def test_interrupt_after_both_promotions_before_final_gate_recovers_both_old(
        self,
    ) -> None:
        recovery = plan_interrupted_pair_recovery(
            lock_owner=BUILD_NEW,
            expected_owner=BUILD_NEW,
            old_pair=("api-old", "web-old"),
            new_pair=("api-new", "web-new"),
            current_pair=("api-new", "web-new"),
            foreign_candidate_present=False,
        )
        self.assertEqual(recovery, ("api-old", "web-old"))

    def test_foreign_overlap_never_rolls_back_or_leaves_split_owned_state(
        self,
    ) -> None:
        with self.assertRaises(LockOwnershipError):
            plan_interrupted_pair_recovery(
                lock_owner=BUILD_OLD,
                expected_owner=BUILD_NEW,
                old_pair=("api-old", "web-old"),
                new_pair=("api-new", "web-new"),
                current_pair=("api-new", "web-old"),
                foreign_candidate_present=True,
            )


class CandidateChainTests(unittest.TestCase):
    def test_unique_candidate_urls_form_exact_browser_chain(self) -> None:
        api_url, web_url = candidate_urls(
            "https://carless-life-api-hash-an.a.run.app",
            "https://carless-life-web-hash-an.a.run.app",
            "candidate-abcdef1-12345678",
        )
        self.assertEqual(
            api_url,
            (
                "https://candidate-abcdef1-12345678---"
                "carless-life-api-hash-an.a.run.app"
            ),
        )
        self.assertEqual(
            web_url,
            (
                "https://candidate-abcdef1-12345678---"
                "carless-life-web-hash-an.a.run.app"
            ),
        )


if __name__ == "__main__":
    unittest.main()
