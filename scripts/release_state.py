from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

LOCK_OWNER_ANNOTATION = "release.carless-life.dev/owner"
LOCK_COMMIT_ANNOTATION = "release.carless-life.dev/commit"
PROVENANCE_KEYS = (
    "source-commit",
    "release-build",
    "managed-by",
    "product",
    "environment",
)
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
TAG_PATTERN = re.compile(r"^[a-z0-9-]{1,63}$")
STABLE_WEB_ORIGIN = (
    "https://carless-life-web-788259830737.asia-northeast1.run.app"
)


class ReleaseStateError(RuntimeError):
    pass


class LockConflict(ReleaseStateError):
    pass


class LockOwnershipError(ReleaseStateError):
    pass


class ProvenanceMismatch(ReleaseStateError):
    pass


def _metadata(service: dict[str, Any]) -> dict[str, Any]:
    metadata = service.get("metadata", {})
    if not metadata.get("resourceVersion"):
        raise ReleaseStateError("Cloud Run resourceVersion is missing")
    return metadata


def _service_payload(
    current: dict[str, Any],
    *,
    annotations: dict[str, str],
) -> dict[str, Any]:
    metadata = _metadata(current)
    return {
        "apiVersion": current["apiVersion"],
        "kind": current["kind"],
        "metadata": {
            "name": metadata["name"],
            "namespace": metadata["namespace"],
            "labels": copy.deepcopy(metadata.get("labels", {})),
            "annotations": annotations,
            "resourceVersion": metadata["resourceVersion"],
        },
        "spec": copy.deepcopy(current["spec"]),
    }


def acquire_lock_payload(
    coordinator: dict[str, Any],
    owner: str,
    commit_sha: str,
) -> dict[str, Any]:
    if not owner:
        raise LockConflict("Release lock owner is required")
    if not SHA_PATTERN.fullmatch(commit_sha):
        raise LockConflict("Release lock commit must be a full Git SHA")
    metadata = _metadata(coordinator)
    annotations = copy.deepcopy(metadata.get("annotations", {}))
    existing_owner = annotations.get(LOCK_OWNER_ANNOTATION)
    existing_commit = annotations.get(LOCK_COMMIT_ANNOTATION)
    if existing_owner or existing_commit:
        raise LockConflict(
            "A release lock already exists; stale locks require explicit audit"
        )
    annotations[LOCK_OWNER_ANNOTATION] = owner
    annotations[LOCK_COMMIT_ANNOTATION] = commit_sha
    return _service_payload(coordinator, annotations=annotations)


def assert_lock_owner(
    coordinator: dict[str, Any],
    owner: str,
    commit_sha: str,
) -> None:
    annotations = _metadata(coordinator).get("annotations", {})
    if (
        annotations.get(LOCK_OWNER_ANNOTATION) != owner
        or annotations.get(LOCK_COMMIT_ANNOTATION) != commit_sha
    ):
        raise LockOwnershipError("Release lock is not owned by this build")


def release_lock_payload(
    coordinator: dict[str, Any],
    owner: str,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    annotations = copy.deepcopy(_metadata(coordinator).get("annotations", {}))
    actual_owner = annotations.get(LOCK_OWNER_ANNOTATION)
    actual_commit = annotations.get(LOCK_COMMIT_ANNOTATION)
    if actual_owner != owner:
        raise LockOwnershipError("Only the release lock owner may release it")
    if commit_sha is not None and actual_commit != commit_sha:
        raise LockOwnershipError("Release lock commit does not match")
    annotations.pop(LOCK_OWNER_ANNOTATION, None)
    annotations.pop(LOCK_COMMIT_ANNOTATION, None)
    return _service_payload(coordinator, annotations=annotations)


def _ready(document: dict[str, Any]) -> bool:
    return any(
        item.get("type") == "Ready" and item.get("status") == "True"
        for item in document.get("status", {}).get("conditions", [])
    )


def _exclusive_revision(service: dict[str, Any]) -> str:
    traffic = service.get("status", {}).get("traffic", [])
    production = [
        item
        for item in traffic
        if item.get("percent", 0) == 100 and item.get("revisionName")
    ]
    if len(production) != 1 or sum(
        item.get("percent", 0) for item in traffic
    ) != 100:
        raise ProvenanceMismatch("Expected one exclusive production revision")
    return production[0]["revisionName"]


def _provenance(labels: dict[str, str]) -> tuple[str, ...]:
    values = tuple(labels.get(key, "") for key in PROVENANCE_KEYS)
    if (
        not all(values)
        or not SHA_PATTERN.fullmatch(values[0])
        or values[2:] != ("cloud-build", "carless-life", "production")
    ):
        raise ProvenanceMismatch("Production provenance is incomplete")
    return values


def assert_matching_production_provenance(
    api_service: dict[str, Any],
    api_revision: dict[str, Any],
    web_service: dict[str, Any],
    web_revision: dict[str, Any],
) -> dict[str, str]:
    if not _ready(api_service) or not _ready(web_service):
        raise ProvenanceMismatch("Both services must be Ready")
    if not _ready(api_revision) or not _ready(web_revision):
        raise ProvenanceMismatch("Both production revisions must be Ready")

    api_revision_name = _exclusive_revision(api_service)
    web_revision_name = _exclusive_revision(web_service)
    if api_revision.get("metadata", {}).get("name") != api_revision_name:
        raise ProvenanceMismatch("API production revision does not match traffic")
    if web_revision.get("metadata", {}).get("name") != web_revision_name:
        raise ProvenanceMismatch("Web production revision does not match traffic")

    api_service_owner = _provenance(
        api_service.get("metadata", {}).get("labels", {})
    )
    web_service_owner = _provenance(
        web_service.get("metadata", {}).get("labels", {})
    )
    api_revision_labels = api_revision.get("metadata", {}).get("labels", {})
    web_revision_labels = web_revision.get("metadata", {}).get("labels", {})
    api_revision_owner = _provenance(api_revision_labels)
    web_revision_owner = _provenance(web_revision_labels)
    if not (
        api_service_owner
        == web_service_owner
        == api_revision_owner
        == web_revision_owner
    ):
        raise ProvenanceMismatch(
            "API and Web production provenance owners differ"
        )
    if api_revision_labels.get("component") != "api":
        raise ProvenanceMismatch("API revision component label is invalid")
    if web_revision_labels.get("component") != "web":
        raise ProvenanceMismatch("Web revision component label is invalid")

    for service, revision in (
        (api_service, api_revision),
        (web_service, web_revision),
    ):
        service_image = (
            service.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [{}])[0]
            .get("image", "")
        )
        revision_digest = revision.get("status", {}).get("imageDigest", "")
        if (
            service_image != revision_digest
            or not DIGEST_PATTERN.fullmatch(revision_digest)
        ):
            raise ProvenanceMismatch(
                "Production service and revision digests differ"
            )

    return dict(zip(PROVENANCE_KEYS, api_service_owner, strict=True))


def _tagged_url(stable_url: str, tag: str) -> str:
    if not TAG_PATTERN.fullmatch(tag):
        raise ReleaseStateError("Candidate tag is invalid")
    parsed = urlsplit(stable_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise ReleaseStateError("Stable Cloud Run URL is invalid")
    return urlunsplit(
        (
            "https",
            f"{tag}---{parsed.netloc}",
            "",
            "",
            "",
        )
    )


def candidate_urls(
    api_stable_url: str,
    web_stable_url: str,
    tag: str,
) -> tuple[str, str]:
    return (
        _tagged_url(api_stable_url, tag),
        _tagged_url(web_stable_url, tag),
    )


def candidate_cors_origins(
    stable_web_url: str,
    candidate_web_url: str,
    phase: str,
) -> tuple[str, ...]:
    if phase not in ("isolated", "production"):
        raise ReleaseStateError("Candidate phase is invalid")
    for name, value in (
        ("stable Web", stable_web_url),
        ("candidate Web", candidate_web_url),
    ):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ReleaseStateError(f"{name} origin is invalid")
    origins = [STABLE_WEB_ORIGIN, stable_web_url.rstrip("/")]
    if phase == "isolated":
        origins.append(candidate_web_url.rstrip("/"))
    return tuple(dict.fromkeys(origins))


def plan_interrupted_pair_recovery(
    *,
    lock_owner: str,
    expected_owner: str,
    old_pair: tuple[str, str],
    new_pair: tuple[str, str],
    current_pair: tuple[str, str],
    foreign_candidate_present: bool,
) -> tuple[str, str]:
    if lock_owner != expected_owner:
        raise LockOwnershipError("Cannot recover without the owned release lock")
    if foreign_candidate_present:
        raise LockOwnershipError("Foreign release state blocks safe recovery")
    allowed = (
        (old_pair[0], old_pair[1]),
        (new_pair[0], old_pair[1]),
        (old_pair[0], new_pair[1]),
        (new_pair[0], new_pair[1]),
    )
    if current_pair not in allowed:
        raise ReleaseStateError("Current production pair is not owned")
    return old_pair
