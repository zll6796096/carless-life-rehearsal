#!/usr/bin/env bash
set -Eeuo pipefail

: "${API_SERVICE:?API_SERVICE is required}"
: "${BUILD_ID:?BUILD_ID is required}"
: "${COMMIT_SHA:?COMMIT_SHA is required}"
: "${DEPLOY_REGION:?DEPLOY_REGION is required}"
: "${PROJECT_ID:?PROJECT_ID is required}"
: "${SHORT_SHA:?SHORT_SHA is required}"
: "${WEB_SERVICE:?WEB_SERVICE is required}"

release_workspace="${RELEASE_WORKSPACE:-/workspace}"
repository_url="${REPOSITORY_URL:-https://github.com/zll6796096/carless-life-rehearsal.git}"
build_token="${BUILD_ID%%-*}"
candidate_tag="candidate-${SHORT_SHA}-${build_token}"
production_tag="production-${SHORT_SHA}-${build_token}"
api_image="$(tr -d '\n' < "${release_workspace}/carless-api-image.txt")"
web_image="$(tr -d '\n' < "${release_workspace}/carless-web-image.txt")"
api_initial="${release_workspace}/carless-api-initial.json"
web_initial="${release_workspace}/carless-web-initial.json"
api_locked="${release_workspace}/carless-api-locked.json"
api_candidate="${release_workspace}/carless-api-candidate.json"
web_candidate="${release_workspace}/carless-web-candidate.json"
api_production_candidate="${release_workspace}/carless-api-production-candidate.json"
web_production_candidate="${release_workspace}/carless-web-production-candidate.json"
api_isolated_revision=""
web_isolated_revision=""
api_revision=""
web_revision=""
api_candidate_url=""
web_candidate_url=""
api_production_candidate_url=""
web_production_candidate_url=""
api_rollback_revision=""
web_rollback_revision=""
access_token=""
lock_acquired=0
final_gates_passed=0

for immutable_image in "${api_image}" "${web_image}"; do
  if [[ ! "${immutable_image}" =~ @sha256:[0-9a-f]{64}$ ]]; then
    printf 'invalid_immutable_image=%s\n' "${immutable_image}" >&2
    exit 1
  fi
done
if [[ ! "${candidate_tag}" =~ ^[a-z0-9-]{1,63}$ ]]; then
  printf 'invalid_candidate_tag=%s\n' "${candidate_tag}" >&2
  exit 1
fi
if [[ ! "${production_tag}" =~ ^[a-z0-9-]{1,63}$ ]]; then
  printf 'invalid_production_tag=%s\n' "${production_tag}" >&2
  exit 1
fi

service_api() {
  local service="$1"
  printf 'https://%s-run.googleapis.com/apis/serving.knative.dev/v1/namespaces/%s/services/%s' \
    "${DEPLOY_REGION}" "${PROJECT_ID}" "${service}"
}

api_get_service() {
  local service="$1"
  local destination="$2"
  curl --fail --silent --show-error \
    --header "Authorization: Bearer ${access_token}" \
    --output "${destination}" \
    "$(service_api "${service}")"
}

conditional_put_raw() {
  local service="$1"
  local payload="$2"
  local response="$3"
  curl --fail --silent --show-error \
    --request PUT \
    --header "Authorization: Bearer ${access_token}" \
    --header "Content-Type: application/json" \
    --data-binary "@${payload}" \
    --output "${response}" \
    "$(service_api "${service}")"
}

assert_release_lock() {
  local destination="${release_workspace}/carless-lock-owner-check.json"
  api_get_service "${API_SERVICE}" "${destination}"
  python3 - "${destination}" "${BUILD_ID}" "${COMMIT_SHA}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import assert_lock_owner

path, owner, commit_sha = sys.argv[1:]
assert_lock_owner(json.loads(Path(path).read_text()), owner, commit_sha)
PY
}

locked_conditional_put() {
  local service="$1"
  local payload="$2"
  local response="$3"
  assert_release_lock
  conditional_put_raw "${service}" "${payload}" "${response}"
  assert_release_lock
}

remote_main_sha() {
  git ls-remote --exit-code "${repository_url}" refs/heads/main |
    awk 'NR == 1 {print $1}'
}

assert_current_main() {
  local remote_sha
  remote_sha="$(remote_main_sha)"
  if [[ "${remote_sha}" != "${COMMIT_SHA}" ]]; then
    printf 'stale_build=BLOCKED expected=%s actual=%s\n' \
      "${COMMIT_SHA}" "${remote_sha}" >&2
    return 1
  fi
}

assert_initial_pair_provenance() {
  local api_revision_json="${release_workspace}/carless-api-initial-revision.json"
  local web_revision_json="${release_workspace}/carless-web-initial-revision.json"

  gcloud run revisions describe "${api_rollback_revision}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format=json > "${api_revision_json}"
  gcloud run revisions describe "${web_rollback_revision}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format=json > "${web_revision_json}"
  python3 - \
    "${api_initial}" \
    "${api_revision_json}" \
    "${web_initial}" \
    "${web_revision_json}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import assert_matching_production_provenance

api_service_path, api_revision_path, web_service_path, web_revision_path = (
    sys.argv[1:]
)
owner = assert_matching_production_provenance(
    json.loads(Path(api_service_path).read_text()),
    json.loads(Path(api_revision_path).read_text()),
    json.loads(Path(web_service_path).read_text()),
    json.loads(Path(web_revision_path).read_text()),
)
print(f"initial_pair_source_commit={owner['source-commit']}")
print(f"initial_pair_release_build={owner['release-build']}")
PY
}

assert_initial_pair_unchanged() {
  local api_current="${release_workspace}/carless-api-post-lock.json"
  local web_current="${release_workspace}/carless-web-post-lock.json"

  assert_release_lock
  api_get_service "${API_SERVICE}" "${api_current}"
  api_get_service "${WEB_SERVICE}" "${web_current}"
  python3 - \
    "${api_initial}" \
    "${api_current}" \
    "${web_initial}" \
    "${web_current}" <<'PY'
import json
import sys
from pathlib import Path

api_initial_path, api_current_path, web_initial_path, web_current_path = (
    sys.argv[1:]
)
for component, initial_path, current_path in (
    ("api", api_initial_path, api_current_path),
    ("web", web_initial_path, web_current_path),
):
    initial = json.loads(Path(initial_path).read_text())
    current = json.loads(Path(current_path).read_text())
    if (
        current.get("metadata", {}).get("labels", {})
        != initial.get("metadata", {}).get("labels", {})
        or current.get("spec", {}) != initial.get("spec", {})
        or current.get("status", {}).get("traffic", [])
        != initial.get("status", {}).get("traffic", [])
    ):
        raise SystemExit(
            f"{component} changed between provenance check and lock"
        )
print("post_lock_pair=UNCHANGED")
PY
  assert_release_lock
}

assert_final_pair_provenance() {
  local api_service_json="${release_workspace}/carless-api-final-service.json"
  local web_service_json="${release_workspace}/carless-web-final-service.json"
  local api_revision_json="${release_workspace}/carless-api-final-revision.json"
  local web_revision_json="${release_workspace}/carless-web-final-revision.json"

  assert_release_lock
  api_get_service "${API_SERVICE}" "${api_service_json}"
  api_get_service "${WEB_SERVICE}" "${web_service_json}"
  gcloud run revisions describe "${api_revision}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format=json > "${api_revision_json}"
  gcloud run revisions describe "${web_revision}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format=json > "${web_revision_json}"
  python3 - \
    "${api_service_json}" \
    "${api_revision_json}" \
    "${web_service_json}" \
    "${web_revision_json}" \
    "${COMMIT_SHA}" \
    "${BUILD_ID}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import assert_matching_production_provenance

(
    api_service_path,
    api_revision_path,
    web_service_path,
    web_revision_path,
    commit_sha,
    build_id,
) = sys.argv[1:]
owner = assert_matching_production_provenance(
    json.loads(Path(api_service_path).read_text()),
    json.loads(Path(api_revision_path).read_text()),
    json.loads(Path(web_service_path).read_text()),
    json.loads(Path(web_revision_path).read_text()),
)
if owner["source-commit"] != commit_sha or owner["release-build"] != build_id:
    raise SystemExit("Final pair provenance is not owned by this build")
print("final_pair_provenance=PASS")
PY
  assert_release_lock
}

wait_for_lock_state() {
  local expected="$1"
  local destination="$2"
  local attempt
  local result_code=0

  for ((attempt = 1; attempt <= 60; attempt += 1)); do
    api_get_service "${API_SERVICE}" "${destination}"
    if python3 - \
      "${destination}" \
      "${expected}" \
      "${BUILD_ID}" \
      "${COMMIT_SHA}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import (
    LOCK_COMMIT_ANNOTATION,
    LOCK_OWNER_ANNOTATION,
    assert_lock_owner,
)

path, expected, owner, commit_sha = sys.argv[1:]
service = json.loads(Path(path).read_text())
annotations = service.get("metadata", {}).get("annotations", {})
if expected == "owned":
    try:
        assert_lock_owner(service, owner, commit_sha)
    except Exception:
        raise SystemExit(10)
elif expected == "absent":
    if (
        annotations.get(LOCK_OWNER_ANNOTATION)
        or annotations.get(LOCK_COMMIT_ANNOTATION)
    ):
        raise SystemExit(10)
else:
    raise SystemExit("Invalid lock state expectation")
PY
    then
      return 0
    else
      result_code=$?
      if [[ "${result_code}" -ne 10 ]]; then
        return "${result_code}"
      fi
    fi
    sleep 1
  done
  printf 'release_lock_resolution=timeout expected=%s\n' "${expected}" >&2
  return 1
}

acquire_release_lock() {
  local current="${release_workspace}/carless-lock-acquire-current.json"
  local payload="${release_workspace}/carless-lock-acquire-payload.json"
  local response="${release_workspace}/carless-lock-acquire-response.json"

  api_get_service "${API_SERVICE}" "${current}"
  python3 - \
    "${current}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import acquire_lock_payload

current_path, payload_path, owner, commit_sha = sys.argv[1:]
payload = acquire_lock_payload(
    json.loads(Path(current_path).read_text()),
    owner,
    commit_sha,
)
Path(payload_path).write_text(json.dumps(payload) + "\n")
PY
  lock_acquired=1
  conditional_put_raw "${API_SERVICE}" "${payload}" "${response}"
  wait_for_lock_state owned "${api_locked}"
  printf 'release_lock=ACQUIRED owner=%s\n' "${BUILD_ID}"
}

release_release_lock() {
  local current="${release_workspace}/carless-lock-release-current.json"
  local payload="${release_workspace}/carless-lock-release-payload.json"
  local response="${release_workspace}/carless-lock-release-response.json"
  local verified="${release_workspace}/carless-lock-release-verified.json"

  assert_release_lock
  api_get_service "${API_SERVICE}" "${current}"
  python3 - \
    "${current}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import release_lock_payload

current_path, payload_path, owner, commit_sha = sys.argv[1:]
payload = release_lock_payload(
    json.loads(Path(current_path).read_text()),
    owner,
    commit_sha,
)
Path(payload_path).write_text(json.dumps(payload) + "\n")
PY
  conditional_put_raw "${API_SERVICE}" "${payload}" "${response}"
  wait_for_lock_state absent "${verified}"
  lock_acquired=0
  printf 'release_lock=RELEASED owner=%s\n' "${BUILD_ID}"
}

capture_initial_state() {
  local service="$1"
  local destination="$2"
  api_get_service "${service}" "${destination}"
  python3 - "${destination}" "${service}" <<'PY'
import json
import sys
from pathlib import Path

path, expected_name = sys.argv[1:]
service = json.loads(Path(path).read_text())
metadata = service.get("metadata", {})
if metadata.get("name") != expected_name:
    raise SystemExit("Unexpected Cloud Run service")
if not metadata.get("resourceVersion"):
    raise SystemExit("Cloud Run service resourceVersion is missing")
conditions = service.get("status", {}).get("conditions", [])
if not any(
    item.get("type") == "Ready" and item.get("status") == "True"
    for item in conditions
):
    raise SystemExit("Cloud Run service is not ready before candidate deployment")
production = [
    item
    for item in service.get("status", {}).get("traffic", [])
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
if len(production) != 1:
    raise SystemExit("Expected one exclusive production revision")
if sum(
    item.get("percent", 0)
    for item in service.get("status", {}).get("traffic", [])
) != 100:
    raise SystemExit("Production traffic must total 100 percent")
containers = (
    service.get("spec", {})
    .get("template", {})
    .get("spec", {})
    .get("containers", [])
)
if len(containers) != 1:
    raise SystemExit("Expected one service container")
if not service.get("status", {}).get("url"):
    raise SystemExit("Stable service URL is missing")
print(production[0]["revisionName"])
PY
}

derive_candidate_urls() {
  read -r api_candidate_url web_candidate_url < <(
    python3 - \
      "${api_initial}" \
      "${web_initial}" \
      "${candidate_tag}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import candidate_urls

api_path, web_path, tag = sys.argv[1:]
api = json.loads(Path(api_path).read_text())
web = json.loads(Path(web_path).read_text())
print(
    *candidate_urls(
        api["status"]["url"],
        web["status"]["url"],
        tag,
    )
)
PY
  )
  read -r api_production_candidate_url web_production_candidate_url < <(
    python3 - \
      "${api_initial}" \
      "${web_initial}" \
      "${production_tag}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import candidate_urls

api_path, web_path, tag = sys.argv[1:]
api = json.loads(Path(api_path).read_text())
web = json.loads(Path(web_path).read_text())
print(
    *candidate_urls(
        api["status"]["url"],
        web["status"]["url"],
        tag,
    )
)
PY
  )
}

prepare_candidate_payload() {
  local current="$1"
  local payload="$2"
  local image="$3"
  local rollback_revision="$4"
  local product_component="$5"
  local traffic_tag="$6"
  local phase="$7"
  python3 - \
    "${current}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" \
    "${traffic_tag}" \
    "${image}" \
    "${rollback_revision}" \
    "${product_component}" \
    "${phase}" \
    "${api_candidate_url}" \
    "${web_candidate_url}" \
    "${api_initial}" \
    "${web_initial}" <<'PY'
import copy
import json
import sys
from pathlib import Path

from scripts.release_state import candidate_cors_origins

(
    current_path,
    payload_path,
    build_id,
    commit_sha,
    traffic_tag,
    image_digest,
    rollback_revision,
    product_component,
    phase,
    candidate_api_url,
    candidate_web_url,
    api_initial_path,
    web_initial_path,
) = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
api_initial = json.loads(Path(api_initial_path).read_text())
web_initial = json.loads(Path(web_initial_path).read_text())
metadata = current["metadata"]
resource_version = metadata.get("resourceVersion")
if not resource_version:
    raise SystemExit("Candidate service resourceVersion is missing")
status_traffic = current.get("status", {}).get("traffic", [])
if status_traffic != [
    {"percent": 100, "revisionName": rollback_revision}
]:
    raise SystemExit("Candidate creation requires the unchanged old pair")
if phase not in ("isolated", "production"):
    raise SystemExit("Invalid candidate phase")

spec = copy.deepcopy(current["spec"])
template = spec["template"]
template_metadata = template.setdefault("metadata", {})
template_labels = dict(template_metadata.get("labels", {}))
for key in (
    "commit-sha",
    "gcb-build-id",
    "gcb-trigger-id",
    "gcb-trigger-region",
):
    template_labels.pop(key, None)
template_labels.update(
    {
        "source-commit": commit_sha,
        "managed-by": "cloud-build",
        "product": "carless-life",
        "environment": "production",
        "release-build": build_id,
        "component": product_component,
    }
)
template_metadata["labels"] = template_labels

containers = template.get("spec", {}).get("containers", [])
if len(containers) != 1:
    raise SystemExit("Expected one service container for candidate")
containers[0]["image"] = image_digest
env = {
    item["name"]: copy.deepcopy(item)
    for item in containers[0].get("env", [])
}
api_stable = (
    "https://carless-life-api-788259830737."
    "asia-northeast1.run.app"
)
stable_web_origins = (
    candidate_cors_origins(
        web_initial["status"]["url"],
        candidate_web_url,
        phase,
    )
)
if product_component == "api":
    env["ROUTING_PROVIDER"] = {
        "name": "ROUTING_PROVIDER",
        "value": "mock",
    }
    env["CORS_ORIGINS"] = {
        "name": "CORS_ORIGINS",
        "value": ",".join(stable_web_origins),
    }
else:
    env["API_BASE_URL"] = {
        "name": "API_BASE_URL",
        "value": candidate_api_url if phase == "isolated" else api_stable,
    }
containers[0]["env"] = [env[name] for name in sorted(env)]

spec["traffic"] = [
    {
        "revisionName": rollback_revision,
        "percent": 100,
    },
    {
        "latestRevision": True,
        "percent": 0,
        "tag": traffic_tag,
    },
]
payload = {
    "apiVersion": current["apiVersion"],
    "kind": current["kind"],
    "metadata": {
        "name": metadata["name"],
        "namespace": metadata["namespace"],
        "labels": metadata.get("labels", {}),
        "annotations": metadata.get("annotations", {}),
        "resourceVersion": resource_version,
    },
    "spec": spec,
}
Path(payload_path).write_text(json.dumps(payload) + "\n")
PY
}

deploy_candidate() {
  local service="$1"
  local image="$2"
  local rollback_revision="$3"
  local component="$4"
  local traffic_tag="$5"
  local phase="$6"
  local current="${release_workspace}/${component}-${phase}-current.json"
  local payload="${release_workspace}/${component}-${phase}-payload.json"
  local response="${release_workspace}/${component}-${phase}-response.json"

  assert_release_lock
  api_get_service "${service}" "${current}"
  prepare_candidate_payload \
    "${current}" "${payload}" "${image}" "${rollback_revision}" \
    "${component}" "${traffic_tag}" "${phase}"
  locked_conditional_put "${service}" "${payload}" "${response}"
}

resolve_candidate() {
  local service="$1"
  local initial="$2"
  local rollback_revision="$3"
  local destination="$4"
  local traffic_tag="$5"
  local expected_url="$6"
  local attempt
  local resolution=""
  local resolution_code=0

  for ((attempt = 1; attempt <= 90; attempt += 1)); do
    api_get_service "${service}" "${destination}"
    if resolution="$(
      python3 - \
        "${destination}" \
        "${initial}" \
        "${traffic_tag}" \
        "${rollback_revision}" \
        "${expected_url}" <<'PY'
import json
import sys
from pathlib import Path

(
    current_path,
    initial_path,
    traffic_tag,
    rollback_revision,
    expected_url,
) = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
initial = json.loads(Path(initial_path).read_text())
if (
    current.get("metadata", {}).get("labels", {})
    != initial.get("metadata", {}).get("labels", {})
):
    raise SystemExit("Candidate deployment changed service labels")
conditions = current.get("status", {}).get("conditions", [])
if any(
    item.get("type") == "Ready" and item.get("status") == "False"
    for item in conditions
):
    raise SystemExit("Candidate service reconciliation failed")

spec_traffic = current.get("spec", {}).get("traffic", [])
status_traffic = current.get("status", {}).get("traffic", [])
spec_candidate = [
    item for item in spec_traffic if item.get("tag") == traffic_tag
]
status_candidate = [
    item for item in status_traffic if item.get("tag") == traffic_tag
]
production = [
    item
    for item in status_traffic
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
if not status_candidate:
    raise SystemExit(10)
if (
    len(spec_traffic) != 2
    or len(status_traffic) != 2
    or len(spec_candidate) != 1
    or spec_candidate[0].get("percent", 0) != 0
    or len(status_candidate) != 1
    or status_candidate[0].get("percent", 0) != 0
    or not status_candidate[0].get("revisionName")
    or status_candidate[0].get("url") != expected_url
    or len(production) != 1
    or production[0]["revisionName"] != rollback_revision
):
    raise SystemExit("Unique zero-traffic candidate state is invalid")
if not any(
    item.get("type") == "Ready" and item.get("status") == "True"
    for item in conditions
):
    raise SystemExit(10)
print(status_candidate[0]["revisionName"], status_candidate[0]["url"])
PY
    )"; then
      read -r resolved_revision resolved_url <<< "${resolution}"
      assert_release_lock
      printf '%s %s\n' "${resolved_revision}" "${resolved_url}"
      return 0
    else
      resolution_code=$?
      if [[ "${resolution_code}" -ne 10 ]]; then
        return "${resolution_code}"
      fi
    fi
    sleep 2
  done
  printf 'candidate_resolution=timeout service=%s\n' "${service}" >&2
  return 1
}

remove_candidate_target() {
  local service="$1"
  local rollback_revision="$2"
  local component="$3"
  local traffic_tag="$4"
  local candidate_revision="$5"
  local current="${release_workspace}/${component}-remove-${traffic_tag}-current.json"
  local payload="${release_workspace}/${component}-remove-${traffic_tag}-payload.json"
  local response="${release_workspace}/${component}-remove-${traffic_tag}-response.json"
  local verified="${release_workspace}/${component}-remove-${traffic_tag}-verified.json"
  local attempt

  assert_release_lock
  api_get_service "${service}" "${current}"
  python3 - \
    "${current}" \
    "${payload}" \
    "${traffic_tag}" \
    "${candidate_revision}" \
    "${rollback_revision}" <<'PY'
import copy
import json
import sys
from pathlib import Path

current_path, payload_path, tag, candidate_revision, rollback_revision = (
    sys.argv[1:]
)
current = json.loads(Path(current_path).read_text())
metadata = current["metadata"]
status_traffic = current.get("status", {}).get("traffic", [])
candidate = [item for item in status_traffic if item.get("tag") == tag]
production = [
    item
    for item in status_traffic
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
if (
    len(status_traffic) != 2
    or len(candidate) != 1
    or candidate[0].get("revisionName") != candidate_revision
    or candidate[0].get("percent", 0) != 0
    or len(production) != 1
    or production[0]["revisionName"] != rollback_revision
):
    raise SystemExit("Candidate removal state is invalid")
spec = copy.deepcopy(current["spec"])
spec["traffic"] = [
    {"revisionName": rollback_revision, "percent": 100}
]
payload = {
    "apiVersion": current["apiVersion"],
    "kind": current["kind"],
    "metadata": {
        "name": metadata["name"],
        "namespace": metadata["namespace"],
        "labels": metadata.get("labels", {}),
        "annotations": metadata.get("annotations", {}),
        "resourceVersion": metadata["resourceVersion"],
    },
    "spec": spec,
}
Path(payload_path).write_text(json.dumps(payload) + "\n")
PY
  locked_conditional_put "${service}" "${payload}" "${response}"
  for ((attempt = 1; attempt <= 60; attempt += 1)); do
    api_get_service "${service}" "${verified}"
    if python3 - \
      "${verified}" \
      "${rollback_revision}" \
      "${traffic_tag}" <<'PY'
import json
import sys
from pathlib import Path

path, rollback_revision, tag = sys.argv[1:]
service = json.loads(Path(path).read_text())
expected = [{"revisionName": rollback_revision, "percent": 100}]
if service.get("spec", {}).get("traffic", []) != expected:
    raise SystemExit(10)
status = service.get("status", {}).get("traffic", [])
if status != [{"revisionName": rollback_revision, "percent": 100}]:
    raise SystemExit(10)
if any(item.get("tag") == tag for item in status):
    raise SystemExit(10)
PY
    then
      assert_release_lock
      return 0
    else
      result_code=$?
      if [[ "${result_code}" -ne 10 ]]; then
        return "${result_code}"
      fi
    fi
    sleep 1
  done
  printf 'candidate_removal=timeout service=%s tag=%s\n' \
    "${service}" "${traffic_tag}" >&2
  return 1
}

verify_candidate_revision() {
  local revision="$1"
  local image="$2"
  local initial="$3"
  local component="$4"
  local phase="$5"
  local revision_json="${release_workspace}/${component}-${phase}-candidate-revision.json"

  gcloud run revisions describe "${revision}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format=json > "${revision_json}"
  python3 - \
    "${revision_json}" \
    "${initial}" \
    "${image}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" \
    "${component}" \
    "${phase}" \
    "${api_candidate_url}" \
    "${web_candidate_url}" \
    "${web_initial}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import candidate_cors_origins

(
    revision_path,
    initial_path,
    expected_image,
    build_id,
    commit_sha,
    component,
    phase,
    candidate_api_url,
    candidate_web_url,
    web_initial_path,
) = sys.argv[1:]
revision = json.loads(Path(revision_path).read_text())
initial = json.loads(Path(initial_path).read_text())
web_initial = json.loads(Path(web_initial_path).read_text())
if phase not in ("isolated", "production"):
    raise SystemExit("Invalid candidate verification phase")
if revision.get("status", {}).get("imageDigest") != expected_image:
    raise SystemExit("Candidate revision digest does not match pushed image")
if not any(
    item.get("type") == "Ready" and item.get("status") == "True"
    for item in revision.get("status", {}).get("conditions", [])
):
    raise SystemExit("Candidate revision is not Ready")
labels = revision.get("metadata", {}).get("labels", {})
expected_labels = {
    "source-commit": commit_sha,
    "release-build": build_id,
    "managed-by": "cloud-build",
    "product": "carless-life",
    "environment": "production",
    "component": component,
}
for key, value in expected_labels.items():
    if labels.get(key) != value:
        raise SystemExit(f"Candidate revision label mismatch: {key}")

candidate_spec = revision.get("spec", {})
initial_spec = (
    initial.get("spec", {})
    .get("template", {})
    .get("spec", {})
)
for field in (
    "containerConcurrency",
    "serviceAccountName",
    "timeoutSeconds",
):
    if candidate_spec.get(field) != initial_spec.get(field):
        raise SystemExit(f"Candidate runtime setting changed: {field}")
candidate_containers = candidate_spec.get("containers", [])
initial_containers = initial_spec.get("containers", [])
if len(candidate_containers) != 1 or len(initial_containers) != 1:
    raise SystemExit("Expected one container")
for field in ("ports", "resources", "startupProbe", "livenessProbe"):
    if candidate_containers[0].get(field) != initial_containers[0].get(field):
        raise SystemExit(f"Candidate container setting changed: {field}")
env = {
    item["name"]: item.get("value")
    for item in candidate_containers[0].get("env", [])
}
if component == "api":
    if env.get("ROUTING_PROVIDER") != "mock":
        raise SystemExit("API candidate routing provider changed")
    origins = set((env.get("CORS_ORIGINS") or "").split(","))
    expected_origins = set(
        candidate_cors_origins(
            web_initial["status"]["url"],
            candidate_web_url,
            phase,
        )
    )
    if origins != expected_origins:
        raise SystemExit("API candidate CORS origins are not exact")
else:
    stable_api_url = (
        "https://carless-life-api-788259830737."
        "asia-northeast1.run.app"
    )
    expected_api_url = (
        candidate_api_url if phase == "isolated" else stable_api_url
    )
    if env.get("API_BASE_URL") != expected_api_url:
        raise SystemExit("Web candidate API target changed")
print(f"candidate_runtime=PASS component={component} phase={phase}")
PY
}

verify_candidate_endpoints() {
  curl --fail --silent --show-error \
    --retry 8 --retry-all-errors --retry-delay 5 \
    --header "Origin: ${web_candidate_url}" \
    --output "${release_workspace}/carless-isolated-health.json" \
    "${api_candidate_url}/health"
  curl --fail --silent --show-error \
    --retry 4 --retry-all-errors --retry-delay 5 \
    --header "Origin: ${web_candidate_url}" \
    --output "${release_workspace}/carless-isolated-fixture.json" \
    "${api_candidate_url}/fixtures/demo"
  curl --fail --silent --show-error \
    --retry 2 --retry-all-errors --retry-delay 5 \
    --header "Content-Type: application/json" \
    --header "Origin: ${web_candidate_url}" \
    --data-binary "@${release_workspace}/carless-isolated-fixture.json" \
    --output "${release_workspace}/carless-isolated-diagnosis.json" \
    "${api_candidate_url}/diagnosis/run"
  curl --fail --silent --show-error \
    --retry 8 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-isolated-web-home.html" \
    "${web_candidate_url}/"
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-isolated-web-onboarding.html" \
    "${web_candidate_url}/onboarding"
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-isolated-web-config.js" \
    "${web_candidate_url}/config.js"
  curl --fail --silent --show-error \
    --request OPTIONS \
    --dump-header "${release_workspace}/carless-isolated-cors-headers.txt" \
    --output /dev/null \
    --header "Origin: ${web_candidate_url}" \
    --header "Access-Control-Request-Method: POST" \
    "${api_candidate_url}/diagnosis/run"

  python3 - \
    "${release_workspace}" \
    "${api_candidate_url}" \
    "${web_candidate_url}" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
api_url = sys.argv[2]
web_url = sys.argv[3]
health = json.loads(
    (workspace / "carless-isolated-health.json").read_text()
)
fixture = json.loads(
    (workspace / "carless-isolated-fixture.json").read_text()
)
diagnosis = json.loads(
    (workspace / "carless-isolated-diagnosis.json").read_text()
)
if health != {"status": "ok"}:
    raise SystemExit("Candidate health response is not ok")
if len(fixture.get("destinations", [])) < 5:
    raise SystemExit("Candidate demo fixture is incomplete")
required_categories = {
    "supermarket",
    "hospital",
    "pharmacy",
    "city_hall",
    "station",
    "social",
}
categories = {
    item.get("category")
    for item in diagnosis.get("item_results", [])
}
if categories != required_categories:
    raise SystemExit("Candidate diagnosis categories are incomplete")
if diagnosis.get("data_source") != "fixture":
    raise SystemExit("Candidate diagnosis data boundary changed")
if not diagnosis.get("summary_ja"):
    raise SystemExit("Candidate diagnosis summary is missing")
config = (workspace / "carless-isolated-web-config.js").read_text()
if f'API_BASE_URL: "{api_url}"' not in config:
    raise SystemExit("Candidate web runtime API target is incorrect")
for page_name in (
    "carless-isolated-web-home.html",
    "carless-isolated-web-onboarding.html",
):
    page = (workspace / page_name).read_text()
    if '<div id="root"></div>' not in page or 'src="/config.js"' not in page:
        raise SystemExit(f"Candidate SPA entry is incomplete: {page_name}")
headers = (
    workspace / "carless-isolated-cors-headers.txt"
).read_text().lower()
if f"access-control-allow-origin: {web_url}".lower() not in headers:
    raise SystemExit("Candidate API CORS response is incomplete")
allow_methods = next(
    (
        line
        for line in headers.splitlines()
        if line.startswith("access-control-allow-methods:")
    ),
    "",
)
if "post" not in allow_methods:
    raise SystemExit("Candidate API preflight does not allow POST")
print(
    "candidate_smoke=PASS "
    "fixture_diagnosis=true exact_browser_chain=true"
)
PY
}

verify_production_candidate_endpoints() {
  local stable_api_url=\
"https://carless-life-api-788259830737.asia-northeast1.run.app"
  local stable_web_origin=\
"https://carless-life-web-788259830737.asia-northeast1.run.app"

  curl --fail --silent --show-error \
    --retry 8 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-production-candidate-health.json" \
    "${api_production_candidate_url}/health"
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-production-candidate-config.js" \
    "${web_production_candidate_url}/config.js"
  curl --fail --silent --show-error \
    --output \
      "${release_workspace}/carless-production-candidate-onboarding.html" \
    "${web_production_candidate_url}/onboarding"
  curl --fail --silent --show-error \
    --request OPTIONS \
    --dump-header \
      "${release_workspace}/carless-production-candidate-cors.txt" \
    --output /dev/null \
    --header "Origin: ${stable_web_origin}" \
    --header "Access-Control-Request-Method: POST" \
    "${api_production_candidate_url}/diagnosis/run"

  python3 - \
    "${release_workspace}" \
    "${stable_api_url}" \
    "${stable_web_origin}" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
stable_api_url = sys.argv[2]
stable_web_origin = sys.argv[3]
health = json.loads(
    (workspace / "carless-production-candidate-health.json").read_text()
)
if health != {"status": "ok"}:
    raise SystemExit("Production-config candidate health is not ok")
config = (
    workspace / "carless-production-candidate-config.js"
).read_text()
if f'API_BASE_URL: "{stable_api_url}"' not in config:
    raise SystemExit("Production-config Web candidate target is incorrect")
onboarding = (
    workspace / "carless-production-candidate-onboarding.html"
).read_text()
if '<div id="root"></div>' not in onboarding or 'src="/config.js"' not in onboarding:
    raise SystemExit("Production-config onboarding entry is incomplete")
headers = (
    workspace / "carless-production-candidate-cors.txt"
).read_text().lower()
if f"access-control-allow-origin: {stable_web_origin}" not in headers:
    raise SystemExit("Production-config API origin is incomplete")
print("production_candidate_smoke=PASS stable_chain=true")
PY
}

validate_prepromotion_state() {
  local service="$1"
  local initial="$2"
  local revision="$3"
  local rollback_revision="$4"
  local current="$5"
  local traffic_tag="$6"
  assert_release_lock
  api_get_service "${service}" "${current}"
  python3 - \
    "${current}" \
    "${initial}" \
    "${traffic_tag}" \
    "${revision}" \
    "${rollback_revision}" <<'PY'
import json
import sys
from pathlib import Path

current_path, initial_path, tag, revision, rollback = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
initial = json.loads(Path(initial_path).read_text())
if (
    current.get("metadata", {}).get("labels", {})
    != initial.get("metadata", {}).get("labels", {})
):
    raise SystemExit("Service labels changed before promotion")
traffic = current.get("status", {}).get("traffic", [])
candidate = [item for item in traffic if item.get("tag") == tag]
production = [
    item for item in traffic
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
if (
    len(traffic) != 2
    or len(candidate) != 1
    or candidate[0].get("revisionName") != revision
    or candidate[0].get("percent", 0) != 0
    or len(production) != 1
    or production[0]["revisionName"] != rollback
):
    raise SystemExit("Candidate state changed before promotion")
PY
  assert_release_lock
}

prepare_promotion_payload() {
  local current="$1"
  local initial="$2"
  local payload="$3"
  local revision="$4"
  local rollback_revision="$5"
  local component="$6"
  python3 - \
    "${current}" \
    "${initial}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" \
    "${production_tag}" \
    "${revision}" \
    "${rollback_revision}" \
    "${component}" <<'PY'
import copy
import json
import sys
from pathlib import Path

(
    current_path,
    initial_path,
    payload_path,
    build_id,
    commit_sha,
    production_tag,
    revision,
    rollback_revision,
    component,
) = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
initial = json.loads(Path(initial_path).read_text())
metadata = current["metadata"]
if (
    metadata.get("labels", {})
    != initial.get("metadata", {}).get("labels", {})
):
    raise SystemExit("Service labels changed during promotion")
status_traffic = current.get("status", {}).get("traffic", [])
candidate = [
    item for item in status_traffic if item.get("tag") == production_tag
]
production = [
    item
    for item in status_traffic
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
if (
    len(status_traffic) != 2
    or len(candidate) != 1
    or candidate[0].get("revisionName") != revision
    or candidate[0].get("percent", 0) != 0
    or len(production) != 1
    or production[0]["revisionName"] != rollback_revision
):
    raise SystemExit("Candidate state changed during promotion")
labels = dict(metadata.get("labels", {}))
for key in (
    "commit-sha",
    "gcb-build-id",
    "gcb-trigger-id",
    "gcb-trigger-region",
):
    labels.pop(key, None)
labels.update(
    {
        "source-commit": commit_sha,
        "managed-by": "cloud-build",
        "product": "carless-life",
        "environment": "production",
        "release-build": build_id,
    }
)
spec = copy.deepcopy(current["spec"])
spec["traffic"] = [{"revisionName": revision, "percent": 100}]
payload = {
    "apiVersion": current["apiVersion"],
    "kind": current["kind"],
    "metadata": {
        "name": metadata["name"],
        "namespace": metadata["namespace"],
        "labels": labels,
        "annotations": metadata.get("annotations", {}),
        "resourceVersion": metadata["resourceVersion"],
    },
    "spec": spec,
}
Path(payload_path).write_text(json.dumps(payload) + "\n")
PY
}

wait_for_promotion() {
  local service="$1"
  local revision="$2"
  local component="$3"
  local destination="$4"
  local attempt
  local result_code=0

  for ((attempt = 1; attempt <= 90; attempt += 1)); do
    api_get_service "${service}" "${destination}"
    if python3 - \
      "${destination}" \
      "${BUILD_ID}" \
      "${COMMIT_SHA}" \
      "${revision}" \
      "${component}" <<'PY'
import json
import sys
from pathlib import Path

path, build_id, commit_sha, revision, component = sys.argv[1:]
service = json.loads(Path(path).read_text())
labels = service.get("metadata", {}).get("labels", {})
expected = {
    "source-commit": commit_sha,
    "managed-by": "cloud-build",
    "product": "carless-life",
    "environment": "production",
    "release-build": build_id,
}
for key, value in expected.items():
    if labels.get(key) != value:
        raise SystemExit(10)
traffic = service.get("status", {}).get("traffic", [])
if traffic != [{"percent": 100, "revisionName": revision}]:
    raise SystemExit(10)
conditions = service.get("status", {}).get("conditions", [])
if any(
    item.get("type") == "Ready" and item.get("status") == "False"
    for item in conditions
):
    raise SystemExit("Promoted service reconciliation failed")
if not any(
    item.get("type") == "Ready" and item.get("status") == "True"
    for item in conditions
):
    raise SystemExit(10)
print(f"promotion_verified=PASS component={component}")
PY
    then
      return 0
    else
      result_code=$?
      if [[ "${result_code}" -ne 10 ]]; then
        return "${result_code}"
      fi
    fi
    sleep 2
  done
  printf 'promotion_resolution=timeout service=%s\n' "${service}" >&2
  return 1
}

promote_service() {
  local service="$1"
  local initial="$2"
  local revision="$3"
  local rollback_revision="$4"
  local component="$5"
  local current="${release_workspace}/${component}-prepromotion.json"
  local payload="${release_workspace}/${component}-promotion-payload.json"
  local response="${release_workspace}/${component}-promotion-response.json"
  local verified="${release_workspace}/${component}-promotion-verified.json"

  api_get_service "${service}" "${current}"
  prepare_promotion_payload \
    "${current}" "${initial}" "${payload}" "${revision}" \
    "${rollback_revision}" "${component}"
  locked_conditional_put "${service}" "${payload}" "${response}"
  wait_for_promotion "${service}" "${revision}" "${component}" "${verified}"
  assert_release_lock
}

prepare_cleanup_payload() {
  local current="$1"
  local initial="$2"
  local payload="$3"
  local isolated_revision="$4"
  local production_revision="$5"
  local rollback_revision="$6"
  python3 - \
    "${current}" \
    "${initial}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" \
    "${candidate_tag}" \
    "${production_tag}" \
    "${isolated_revision}" \
    "${production_revision}" \
    "${rollback_revision}" <<'PY'
import copy
import json
import sys
from pathlib import Path

(
    current_path,
    initial_path,
    payload_path,
    build_id,
    commit_sha,
    candidate_tag,
    production_tag,
    isolated_revision,
    production_revision,
    rollback_revision,
) = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
initial = json.loads(Path(initial_path).read_text())
metadata = current["metadata"]
labels = metadata.get("labels", {})
spec_traffic = current.get("spec", {}).get("traffic", [])
status_traffic = current.get("status", {}).get("traffic", [])
allowed_tags = {candidate_tag, production_tag}
for item in (*spec_traffic, *status_traffic):
    tag = item.get("tag")
    if tag and tag not in allowed_tags:
        raise SystemExit("Foreign candidate tag blocks automatic recovery")
production = [
    item
    for item in status_traffic
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
if len(production) != 1:
    raise SystemExit("Ambiguous production traffic blocks recovery")
allowed_production = {rollback_revision}
if production_revision:
    allowed_production.add(production_revision)
if production[0]["revisionName"] not in allowed_production:
    raise SystemExit("Foreign production revision blocks recovery")

known_revisions = {
    value
    for value in (
        rollback_revision,
        isolated_revision,
        production_revision,
    )
    if value
}
for item in (*spec_traffic, *status_traffic):
    revision = item.get("revisionName")
    tag = item.get("tag")
    if revision and revision not in known_revisions and not tag:
        raise SystemExit("Foreign untagged revision blocks recovery")

owned_labels = (
    labels.get("release-build") == build_id
    and labels.get("source-commit") == commit_sha
    and labels.get("managed-by") == "cloud-build"
    and labels.get("product") == "carless-life"
    and labels.get("environment") == "production"
)
initial_labels = labels == initial.get("metadata", {}).get("labels", {})
if not (initial_labels or owned_labels):
    raise SystemExit("Foreign service provenance blocks recovery")

expected_traffic = [{"revisionName": rollback_revision, "percent": 100}]
if (
    initial_labels
    and current.get("spec", {}) == initial.get("spec", {})
    and status_traffic
    == [{"percent": 100, "revisionName": rollback_revision}]
):
    print("clean")
    raise SystemExit

spec = copy.deepcopy(initial["spec"])
spec["traffic"] = expected_traffic
payload = {
    "apiVersion": current["apiVersion"],
    "kind": current["kind"],
    "metadata": {
        "name": metadata["name"],
        "namespace": metadata["namespace"],
        "labels": initial.get("metadata", {}).get("labels", {}),
        "annotations": metadata.get("annotations", {}),
        "resourceVersion": metadata["resourceVersion"],
    },
    "spec": spec,
}
Path(payload_path).write_text(json.dumps(payload) + "\n")
print("restore")
PY
}

wait_for_rollback() {
  local service="$1"
  local initial="$2"
  local rollback_revision="$3"
  local destination="$4"
  local attempt
  local result_code=0

  for ((attempt = 1; attempt <= 90; attempt += 1)); do
    api_get_service "${service}" "${destination}"
    if python3 - \
      "${destination}" \
      "${initial}" \
      "${rollback_revision}" <<'PY'
import json
import sys
from pathlib import Path

current_path, initial_path, rollback_revision = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
initial = json.loads(Path(initial_path).read_text())
if (
    current.get("metadata", {}).get("labels", {})
    != initial.get("metadata", {}).get("labels", {})
):
    raise SystemExit(10)
if (
    current.get("spec", {}).get("template", {})
    != initial.get("spec", {}).get("template", {})
):
    raise SystemExit(10)
expected_traffic = [
    {"revisionName": rollback_revision, "percent": 100}
]
if current.get("spec", {}).get("traffic", []) != expected_traffic:
    raise SystemExit(10)
status_traffic = current.get("status", {}).get("traffic", [])
if status_traffic != [
    {"percent": 100, "revisionName": rollback_revision}
]:
    raise SystemExit(10)
conditions = current.get("status", {}).get("conditions", [])
if not any(
    item.get("type") == "Ready" and item.get("status") == "True"
    for item in conditions
):
    raise SystemExit(10)
PY
    then
      return 0
    else
      result_code=$?
      if [[ "${result_code}" -ne 10 ]]; then
        return "${result_code}"
      fi
    fi
    sleep 2
  done
  printf 'rollback_resolution=timeout service=%s\n' "${service}" >&2
  return 1
}

cleanup_service() {
  local service="$1"
  local initial="$2"
  local isolated_revision="$3"
  local production_revision="$4"
  local rollback_revision="$5"
  local component="$6"
  local current="${release_workspace}/${component}-cleanup-current.json"
  local payload="${release_workspace}/${component}-cleanup-payload.json"
  local response="${release_workspace}/${component}-cleanup-response.json"
  local mode=""

  assert_release_lock || return 1
  api_get_service "${service}" "${current}" || return 1
  mode="$(
    prepare_cleanup_payload \
      "${current}" "${initial}" "${payload}" \
      "${isolated_revision}" "${production_revision}" \
      "${rollback_revision}"
  )"
  if [[ "${mode}" == "clean" ]]; then
    wait_for_rollback \
      "${service}" "${initial}" "${rollback_revision}" \
      "${release_workspace}/${component}-cleanup-verified.json"
    printf 'cleanup_result=PASS component=%s already_rollback_revision=%s\n' \
      "${component}" "${rollback_revision}" >&2
    return 0
  fi
  if [[ "${mode}" != "restore" ]]; then
    printf 'cleanup_result=FAILED component=%s unsafe_state\n' \
      "${component}" >&2
    return 1
  fi
  locked_conditional_put "${service}" "${payload}" "${response}"
  wait_for_rollback \
    "${service}" "${initial}" "${rollback_revision}" \
    "${release_workspace}/${component}-cleanup-verified.json"
  assert_release_lock
  printf 'cleanup_result=PASS component=%s rollback_revision=%s\n' \
    "${component}" "${rollback_revision}" >&2
}

assert_owned_recovery_pair() {
  local api_current="${release_workspace}/api-recovery-pair.json"
  local web_current="${release_workspace}/web-recovery-pair.json"

  assert_release_lock
  api_get_service "${API_SERVICE}" "${api_current}"
  api_get_service "${WEB_SERVICE}" "${web_current}"
  python3 - \
    "${api_current}" \
    "${web_current}" \
    "${BUILD_ID}" \
    "${candidate_tag}" \
    "${production_tag}" \
    "${api_rollback_revision}" \
    "${web_rollback_revision}" \
    "${api_revision}" \
    "${web_revision}" <<'PY'
import json
import sys
from pathlib import Path

from scripts.release_state import plan_interrupted_pair_recovery

(
    api_path,
    web_path,
    build_id,
    candidate_tag,
    production_tag,
    api_old,
    web_old,
    api_new,
    web_new,
) = sys.argv[1:]
services = (
    json.loads(Path(api_path).read_text()),
    json.loads(Path(web_path).read_text()),
)
current_pair = []
foreign_candidate_present = False
for service in services:
    traffic = service.get("status", {}).get("traffic", [])
    production = [
        item.get("revisionName")
        for item in traffic
        if item.get("percent", 0) == 100 and item.get("revisionName")
    ]
    if len(production) != 1:
        raise SystemExit("Recovery pair has ambiguous production traffic")
    current_pair.append(production[0])
    for item in (
        *service.get("spec", {}).get("traffic", []),
        *traffic,
    ):
        if item.get("tag") not in (
            None,
            "",
            candidate_tag,
            production_tag,
        ):
            foreign_candidate_present = True

planned = plan_interrupted_pair_recovery(
    lock_owner=build_id,
    expected_owner=build_id,
    old_pair=(api_old, web_old),
    new_pair=(api_new, web_new),
    current_pair=tuple(current_pair),
    foreign_candidate_present=foreign_candidate_present,
)
if planned != (api_old, web_old):
    raise SystemExit("Recovery planner did not select the exact old pair")
print("recovery_pair_plan=PASS target=both-old")
PY
  assert_release_lock
}

cleanup_failed_release() {
  local cleanup_failed=0
  assert_owned_recovery_pair || return 1
  cleanup_service \
    "${WEB_SERVICE}" "${web_initial}" "${web_isolated_revision}" \
    "${web_revision}" "${web_rollback_revision}" web || cleanup_failed=1
  cleanup_service \
    "${API_SERVICE}" "${api_initial}" "${api_isolated_revision}" \
    "${api_revision}" "${api_rollback_revision}" api || cleanup_failed=1
  return "${cleanup_failed}"
}

on_exit() {
  local exit_code="$1"
  local recovery_code=0

  trap - ERR INT TERM EXIT
  if [[ "${lock_acquired}" -eq 1 ]]; then
    set +e
    assert_release_lock
    recovery_code=$?
    if [[ "${recovery_code}" -eq 0 ]]; then
      if [[ "${final_gates_passed}" -eq 0 ]]; then
        cleanup_failed_release
        recovery_code=$?
      fi
      if [[ "${recovery_code}" -eq 0 ]]; then
        release_release_lock
        recovery_code=$?
      fi
    fi
    if [[ "${recovery_code}" -ne 0 ]]; then
      printf \
        'release_recovery=FAILED original_exit=%s recovery_exit=%s lock_left_fail_closed=true\n' \
        "${exit_code}" "${recovery_code}" >&2
      if [[ "${exit_code}" -eq 0 ]]; then
        exit_code=1
      fi
    fi
  fi
  exit "${exit_code}"
}

verify_production_endpoints() {
  local api_url="$1"
  local web_url="$2"
  curl --fail --silent --show-error \
    --retry 3 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-production-health.json" \
    "${api_url}/health"
  curl --fail --silent --show-error \
    --retry 3 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-production-fixture.json" \
    "${api_url}/fixtures/demo"
  curl --fail --silent --show-error \
    --retry 2 --retry-all-errors --retry-delay 5 \
    --header "Content-Type: application/json" \
    --data-binary "@${release_workspace}/carless-production-fixture.json" \
    --output "${release_workspace}/carless-production-diagnosis.json" \
    "${api_url}/diagnosis/run"
  curl --fail --silent --show-error \
    --retry 3 --retry-all-errors --retry-delay 5 \
    "${web_url}/" >/dev/null
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-production-onboarding.html" \
    "${web_url}/onboarding"
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-production-config.js" \
    "${web_url}/config.js"
  curl --fail --silent --show-error \
    --request OPTIONS \
    --dump-header "${release_workspace}/carless-production-cors.txt" \
    --output /dev/null \
    --header \
      "Origin: https://carless-life-web-788259830737.asia-northeast1.run.app" \
    --header "Access-Control-Request-Method: POST" \
    "${api_url}/diagnosis/run"
  python3 - "${release_workspace}" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
health = json.loads(
    (workspace / "carless-production-health.json").read_text()
)
diagnosis = json.loads(
    (workspace / "carless-production-diagnosis.json").read_text()
)
if health != {"status": "ok"}:
    raise SystemExit("Production health response is not ok")
if diagnosis.get("data_source") != "fixture":
    raise SystemExit("Production diagnosis data boundary changed")
if len(diagnosis.get("item_results", [])) != 6:
    raise SystemExit("Production diagnosis is incomplete")
config = (workspace / "carless-production-config.js").read_text()
if (
    "https://carless-life-api-788259830737."
    "asia-northeast1.run.app"
) not in config:
    raise SystemExit("Production web runtime API target is incorrect")
onboarding = (
    workspace / "carless-production-onboarding.html"
).read_text()
if '<div id="root"></div>' not in onboarding or 'src="/config.js"' not in onboarding:
    raise SystemExit("Production onboarding entry is incomplete")
headers = (workspace / "carless-production-cors.txt").read_text().lower()
expected_origin = (
    "access-control-allow-origin: "
    "https://carless-life-web-788259830737."
    "asia-northeast1.run.app"
)
if expected_origin not in headers:
    raise SystemExit("Production API CORS response is incomplete")
print("production_smoke=PASS fixture_diagnosis=true")
PY
}

trap 'exit $?' ERR
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'on_exit $?' EXIT

access_token="$(gcloud auth print-access-token)"
assert_current_main
api_rollback_revision="$(
  capture_initial_state "${API_SERVICE}" "${api_initial}"
)"
web_rollback_revision="$(
  capture_initial_state "${WEB_SERVICE}" "${web_initial}"
)"
assert_initial_pair_provenance
derive_candidate_urls
acquire_release_lock
if ! assert_initial_pair_unchanged; then
  printf 'post_lock_pair=CHANGED release_aborted=true\n' >&2
  release_release_lock
  exit 1
fi
assert_current_main

deploy_candidate \
  "${API_SERVICE}" "${api_image}" "${api_rollback_revision}" \
  api "${candidate_tag}" isolated
read -r api_isolated_revision api_candidate_url < <(
  resolve_candidate \
    "${API_SERVICE}" "${api_initial}" "${api_rollback_revision}" \
    "${api_candidate}" "${candidate_tag}" "${api_candidate_url}"
)

deploy_candidate \
  "${WEB_SERVICE}" "${web_image}" "${web_rollback_revision}" \
  web "${candidate_tag}" isolated
read -r web_isolated_revision web_candidate_url < <(
  resolve_candidate \
    "${WEB_SERVICE}" "${web_initial}" "${web_rollback_revision}" \
    "${web_candidate}" "${candidate_tag}" "${web_candidate_url}"
)

verify_candidate_revision \
  "${api_isolated_revision}" "${api_image}" "${api_initial}" api isolated
verify_candidate_revision \
  "${web_isolated_revision}" "${web_image}" "${web_initial}" web isolated
assert_current_main
verify_candidate_endpoints

remove_candidate_target \
  "${WEB_SERVICE}" "${web_rollback_revision}" web \
  "${candidate_tag}" "${web_isolated_revision}"
remove_candidate_target \
  "${API_SERVICE}" "${api_rollback_revision}" api \
  "${candidate_tag}" "${api_isolated_revision}"

deploy_candidate \
  "${API_SERVICE}" "${api_image}" "${api_rollback_revision}" \
  api "${production_tag}" production
read -r api_revision api_production_candidate_url < <(
  resolve_candidate \
    "${API_SERVICE}" "${api_initial}" "${api_rollback_revision}" \
    "${api_production_candidate}" "${production_tag}" \
    "${api_production_candidate_url}"
)

deploy_candidate \
  "${WEB_SERVICE}" "${web_image}" "${web_rollback_revision}" \
  web "${production_tag}" production
read -r web_revision web_production_candidate_url < <(
  resolve_candidate \
    "${WEB_SERVICE}" "${web_initial}" "${web_rollback_revision}" \
    "${web_production_candidate}" "${production_tag}" \
    "${web_production_candidate_url}"
)

verify_candidate_revision \
  "${api_revision}" "${api_image}" "${api_initial}" api production
verify_candidate_revision \
  "${web_revision}" "${web_image}" "${web_initial}" web production
assert_current_main
verify_production_candidate_endpoints

validate_prepromotion_state \
  "${API_SERVICE}" "${api_initial}" "${api_revision}" \
  "${api_rollback_revision}" \
  "${release_workspace}/api-prepromotion-validated.json" \
  "${production_tag}"
validate_prepromotion_state \
  "${WEB_SERVICE}" "${web_initial}" "${web_revision}" \
  "${web_rollback_revision}" \
  "${release_workspace}/web-prepromotion-validated.json" \
  "${production_tag}"
assert_current_main

promote_service \
  "${API_SERVICE}" "${api_initial}" "${api_revision}" \
  "${api_rollback_revision}" api
assert_current_main
promote_service \
  "${WEB_SERVICE}" "${web_initial}" "${web_revision}" \
  "${web_rollback_revision}" web

api_production_url=\
"https://carless-life-api-788259830737.asia-northeast1.run.app"
web_production_url=\
"https://carless-life-web-788259830737.asia-northeast1.run.app"
verify_production_endpoints "${api_production_url}" "${web_production_url}"
assert_current_main
assert_final_pair_provenance
final_gates_passed=1
release_release_lock

trap - ERR INT TERM EXIT
printf 'promotion_result=PASS\n'
printf 'source_commit=%s\n' "${COMMIT_SHA}"
printf 'api_image=%s\n' "${api_image}"
printf 'web_image=%s\n' "${web_image}"
printf 'api_isolated_revision=%s\n' "${api_isolated_revision}"
printf 'web_isolated_revision=%s\n' "${web_isolated_revision}"
printf 'api_revision=%s\n' "${api_revision}"
printf 'web_revision=%s\n' "${web_revision}"
printf 'api_rollback_revision=%s\n' "${api_rollback_revision}"
printf 'web_rollback_revision=%s\n' "${web_rollback_revision}"
printf 'api_url=%s\n' "${api_production_url}"
printf 'web_url=%s\n' "${web_production_url}"
