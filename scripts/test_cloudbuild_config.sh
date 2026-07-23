#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$root/cloudbuild.yaml"
helper="$root/scripts/git-deploy.sh"
release="$root/scripts/promote-and-verify.sh"

grep -Fq '${COMMIT_SHA}' "$config"
grep -Fq 'resolve-image-digests' "$config"
grep -Fq 'orchestrate-candidate-release' "$config"
grep -Fq 'BUILD_ID=$BUILD_ID' "$config"
grep -Fq 'serviceAccount: projects/zhang23-23/serviceAccounts/apps-cloud-build@zhang23-23.iam.gserviceaccount.com' "$config"
grep -Fq 'logging: CLOUD_LOGGING_ONLY' "$config"

grep -Fq 'candidate-${SHORT_SHA}-${build_token}' "$release"
grep -Fq '@sha256:' "$release"
grep -Fq 'resourceVersion' "$release"
grep -Fq 'git ls-remote' "$release"
grep -Fq 'source-commit' "$release"
grep -Fq 'managed-by' "$release"
grep -Fq 'percent": 0' "$release"
grep -Fq 'cleanup_failed_release' "$release"
grep -Fq 'rollback_revision' "$release"
grep -Fq '/health' "$release"
grep -Fq '/onboarding' "$release"

if grep -Eq "_COMMIT_SHA:[[:space:]]*['\"]?latest" "$config"; then
  echo "mutable latest tag is forbidden" >&2
  exit 1
fi
if grep -Eq 'git add[[:space:]]+\.' "$helper"; then
  echo "broad staging is forbidden" >&2
  exit 1
fi

echo "cloud build safety checks passed"
