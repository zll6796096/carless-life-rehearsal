#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
ERROR: direct local Cloud Run deployment is disabled.

Commit an explicit change on main and push it. The Google Cloud Build Trigger
carless-main-cloud-run owns tests, immutable digest publication, candidate
verification, release locking, traffic promotion, and rollback evidence.

For audited recovery only, copy the exact api_rollback_revision and
web_rollback_revision from a successful build log, then run:

  API_ROLLBACK_REVISION=... WEB_ROLLBACK_REVISION=... \
    bash scripts/rollback-cloud-run.sh
EOF
exit 2
