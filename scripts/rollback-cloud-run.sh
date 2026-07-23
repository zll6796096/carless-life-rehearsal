#!/usr/bin/env bash
set -euo pipefail

: "${API_ROLLBACK_REVISION:?copy api_rollback_revision from a successful build log}"
: "${WEB_ROLLBACK_REVISION:?copy web_rollback_revision from a successful build log}"

project_id="${PROJECT_ID:-zhang23-23}"
region="${REGION:-asia-northeast1}"

if [[ ! "${API_ROLLBACK_REVISION}" =~ ^carless-life-api-[a-z0-9-]+$ ]]; then
  echo "ERROR: invalid API rollback revision" >&2
  exit 1
fi
if [[ ! "${WEB_ROLLBACK_REVISION}" =~ ^carless-life-web-[a-z0-9-]+$ ]]; then
  echo "ERROR: invalid Web rollback revision" >&2
  exit 1
fi

workspace="$(mktemp -d)"
trap 'rm -rf -- "${workspace}"' EXIT

gcloud run services describe carless-life-api \
  --project="${project_id}" \
  --region="${region}" \
  --format=json > "${workspace}/api-service.json"
gcloud run services describe carless-life-web \
  --project="${project_id}" \
  --region="${region}" \
  --format=json > "${workspace}/web-service.json"
gcloud run revisions describe "${API_ROLLBACK_REVISION}" \
  --project="${project_id}" \
  --region="${region}" \
  --format=json > "${workspace}/api-revision.json"
gcloud run revisions describe "${WEB_ROLLBACK_REVISION}" \
  --project="${project_id}" \
  --region="${region}" \
  --format=json > "${workspace}/web-revision.json"

python3 - "${workspace}" <<'PY'
import json
import re
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
api_service = json.loads((workspace / "api-service.json").read_text())
web_service = json.loads((workspace / "web-service.json").read_text())
api_revision = json.loads((workspace / "api-revision.json").read_text())
web_revision = json.loads((workspace / "web-revision.json").read_text())
lock_key = "release.carless-life.dev/owner"
sha_pattern = re.compile(r"^[0-9a-f]{40}$")
digest_pattern = re.compile(r"^.+@sha256:[0-9a-f]{64}$")

for service in (api_service, web_service):
    if service.get("metadata", {}).get("annotations", {}).get(lock_key):
        raise SystemExit("A release lock is active; rollback is blocked")

owners = []
for component, revision in (
    ("api", api_revision),
    ("web", web_revision),
):
    ready = any(
        item.get("type") == "Ready" and item.get("status") == "True"
        for item in revision.get("status", {}).get("conditions", [])
    )
    if not ready:
        raise SystemExit(f"{component} rollback revision is not Ready")
    digest = revision.get("status", {}).get("imageDigest", "")
    if not digest_pattern.fullmatch(digest):
        raise SystemExit(f"{component} rollback imageDigest is not immutable")
    labels = revision.get("metadata", {}).get("labels", {})
    owner = (
        labels.get("source-commit", ""),
        labels.get("release-build", ""),
        labels.get("managed-by", ""),
        labels.get("product", ""),
        labels.get("environment", ""),
    )
    if (
        not sha_pattern.fullmatch(owner[0])
        or not owner[1]
        or owner[2:] != ("cloud-build", "carless-life", "production")
        or labels.get("component") != component
    ):
        raise SystemExit(f"{component} rollback provenance is invalid")
    owners.append(owner)
    print(
        f"{component}_rollback_revision="
        f"{revision['metadata']['name']}"
    )
    print(f"{component}_rollback_imageDigest={digest}")

if owners[0] != owners[1]:
    raise SystemExit("API and Web rollback provenance owners differ")
print(f"rollback_source_commit={owners[0][0]}")
print(f"rollback_release_build={owners[0][1]}")
print("rollback_validation=PASS")
PY

cat <<EOF

Validation passed. Review the exact evidence above, then explicitly run:

gcloud run services update-traffic carless-life-api \\
  --project=${project_id} --region=${region} \\
  --to-revisions=${API_ROLLBACK_REVISION}=100
gcloud run services update-traffic carless-life-web \\
  --project=${project_id} --region=${region} \\
  --to-revisions=${WEB_ROLLBACK_REVISION}=100
EOF
