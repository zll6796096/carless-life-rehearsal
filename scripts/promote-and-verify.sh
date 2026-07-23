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
api_image="$(tr -d '\n' < "${release_workspace}/carless-api-image.txt")"
web_image="$(tr -d '\n' < "${release_workspace}/carless-web-image.txt")"
api_initial="${release_workspace}/carless-api-initial.json"
web_initial="${release_workspace}/carless-web-initial.json"
api_candidate="${release_workspace}/carless-api-candidate.json"
web_candidate="${release_workspace}/carless-web-candidate.json"
api_revision=""
web_revision=""
api_candidate_url=""
web_candidate_url=""
api_rollback_revision=""
web_rollback_revision=""
access_token=""
candidate_mutation_started=0

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

conditional_put() {
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

prepare_candidate_payload() {
  local service="$1"
  local initial="$2"
  local payload="$3"
  local image="$4"
  local rollback_revision="$5"
  local product_component="$6"
  python3 - \
    "${initial}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" \
    "${candidate_tag}" \
    "${image}" \
    "${rollback_revision}" \
    "${product_component}" \
    "${API_SERVICE}" \
    "${WEB_SERVICE}" <<'PY'
import copy
import json
import sys
from pathlib import Path

(
    initial_path,
    payload_path,
    build_id,
    commit_sha,
    candidate_tag,
    image_digest,
    rollback_revision,
    product_component,
    api_service,
    web_service,
) = sys.argv[1:]
current = json.loads(Path(initial_path).read_text())
metadata = current["metadata"]
resource_version = metadata.get("resourceVersion")
if not resource_version:
    raise SystemExit("Candidate service resourceVersion is missing")

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
web_origins = ",".join(
    (
        "https://carless-life-web-788259830737."
        "asia-northeast1.run.app",
        current.get("status", {}).get("url", "")
        if product_component == "web"
        else "",
    )
)
if product_component == "api":
    web_origins = ",".join(
        (
            "https://carless-life-web-788259830737."
            "asia-northeast1.run.app",
            "https://carless-life-web-sxielk4wua-an.a.run.app",
        )
    )
    env["ROUTING_PROVIDER"] = {
        "name": "ROUTING_PROVIDER",
        "value": "mock",
    }
    env["CORS_ORIGINS"] = {
        "name": "CORS_ORIGINS",
        "value": web_origins,
    }
else:
    env["API_BASE_URL"] = {
        "name": "API_BASE_URL",
        "value": api_stable,
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
        "tag": candidate_tag,
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
  local initial="$2"
  local image="$3"
  local rollback_revision="$4"
  local component="$5"
  local payload="${release_workspace}/${component}-candidate-payload.json"
  local response="${release_workspace}/${component}-candidate-response.json"

  prepare_candidate_payload \
    "${service}" "${initial}" "${payload}" "${image}" \
    "${rollback_revision}" "${component}"
  candidate_mutation_started=1
  conditional_put "${service}" "${payload}" "${response}"
}

resolve_candidate() {
  local service="$1"
  local initial="$2"
  local rollback_revision="$3"
  local destination="$4"
  local attempt
  local resolution=""
  local resolution_code=0

  for ((attempt = 1; attempt <= 90; attempt += 1)); do
    api_get_service "${service}" "${destination}"
    if resolution="$(
      python3 - \
        "${destination}" \
        "${initial}" \
        "${candidate_tag}" \
        "${rollback_revision}" <<'PY'
import json
import sys
from pathlib import Path

current_path, initial_path, candidate_tag, rollback_revision = sys.argv[1:]
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
    item for item in spec_traffic if item.get("tag") == candidate_tag
]
status_candidate = [
    item for item in status_traffic if item.get("tag") == candidate_tag
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
    or not status_candidate[0].get("url")
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

verify_candidate_revision() {
  local revision="$1"
  local image="$2"
  local initial="$3"
  local component="$4"
  local revision_json="${release_workspace}/${component}-candidate-revision.json"

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
    "${component}" <<'PY'
import json
import sys
from pathlib import Path

(
    revision_path,
    initial_path,
    expected_image,
    build_id,
    commit_sha,
    component,
) = sys.argv[1:]
revision = json.loads(Path(revision_path).read_text())
initial = json.loads(Path(initial_path).read_text())
if revision.get("status", {}).get("imageDigest") != expected_image:
    raise SystemExit("Candidate revision digest does not match pushed image")
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
    required = {
        "https://carless-life-web-788259830737.asia-northeast1.run.app",
        "https://carless-life-web-sxielk4wua-an.a.run.app",
    }
    if not required.issubset(origins):
        raise SystemExit("API candidate CORS origins are incomplete")
else:
    if env.get("API_BASE_URL") != (
        "https://carless-life-api-788259830737."
        "asia-northeast1.run.app"
    ):
        raise SystemExit("Web candidate API target changed")
print(f"candidate_runtime=PASS component={component}")
PY
}

verify_candidate_endpoints() {
  curl --fail --silent --show-error \
    --retry 8 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-health.json" \
    "${api_candidate_url}/health"
  curl --fail --silent --show-error \
    --retry 4 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-fixture.json" \
    "${api_candidate_url}/fixtures/demo"
  curl --fail --silent --show-error \
    --retry 2 --retry-all-errors --retry-delay 5 \
    --header "Content-Type: application/json" \
    --data-binary "@${release_workspace}/carless-fixture.json" \
    --output "${release_workspace}/carless-diagnosis.json" \
    "${api_candidate_url}/diagnosis/run"
  curl --fail --silent --show-error \
    --retry 8 --retry-all-errors --retry-delay 5 \
    --output "${release_workspace}/carless-web-home.html" \
    "${web_candidate_url}/"
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-web-onboarding.html" \
    "${web_candidate_url}/onboarding"
  curl --fail --silent --show-error \
    --output "${release_workspace}/carless-web-config.js" \
    "${web_candidate_url}/config.js"
  curl --fail --silent --show-error \
    --dump-header "${release_workspace}/carless-cors-headers.txt" \
    --output /dev/null \
    --header \
      "Origin: https://carless-life-web-788259830737.asia-northeast1.run.app" \
    "${api_candidate_url}/health"

  python3 - "${release_workspace}" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
health = json.loads((workspace / "carless-health.json").read_text())
fixture = json.loads((workspace / "carless-fixture.json").read_text())
diagnosis = json.loads((workspace / "carless-diagnosis.json").read_text())
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
config = (workspace / "carless-web-config.js").read_text()
if (
    "https://carless-life-api-788259830737."
    "asia-northeast1.run.app"
) not in config:
    raise SystemExit("Candidate web runtime API target is incorrect")
headers = (workspace / "carless-cors-headers.txt").read_text().lower()
expected_origin = (
    "access-control-allow-origin: "
    "https://carless-life-web-788259830737."
    "asia-northeast1.run.app"
)
if expected_origin not in headers:
    raise SystemExit("Candidate API CORS response is incomplete")
print("candidate_smoke=PASS fixture_diagnosis=true")
PY
}

validate_prepromotion_state() {
  local service="$1"
  local initial="$2"
  local revision="$3"
  local rollback_revision="$4"
  local current="$5"
  api_get_service "${service}" "${current}"
  python3 - \
    "${current}" \
    "${initial}" \
    "${candidate_tag}" \
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
    "${candidate_tag}" \
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
    candidate_tag,
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
    item for item in status_traffic if item.get("tag") == candidate_tag
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
  conditional_put "${service}" "${payload}" "${response}"
  wait_for_promotion "${service}" "${revision}" "${component}" "${verified}"
}

prepare_cleanup_payload() {
  local current="$1"
  local initial="$2"
  local payload="$3"
  local own_revision="$4"
  local rollback_revision="$5"
  python3 - \
    "${current}" \
    "${initial}" \
    "${payload}" \
    "${BUILD_ID}" \
    "${COMMIT_SHA}" \
    "${candidate_tag}" \
    "${own_revision}" \
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
    own_revision,
    rollback_revision,
) = sys.argv[1:]
current = json.loads(Path(current_path).read_text())
initial = json.loads(Path(initial_path).read_text())
metadata = current["metadata"]
labels = metadata.get("labels", {})
traffic = current.get("status", {}).get("traffic", [])
spec_traffic = current.get("spec", {}).get("traffic", [])
own_candidate = [
    item for item in spec_traffic if item.get("tag") == candidate_tag
]
other_candidates = [
    item
    for item in spec_traffic
    if item.get("tag") and item.get("tag") != candidate_tag
]
production = [
    item
    for item in traffic
    if item.get("percent", 0) == 100 and item.get("revisionName")
]
owned_labels = (
    labels.get("release-build") == build_id
    and labels.get("source-commit") == commit_sha
    and labels.get("managed-by") == "cloud-build"
)
initial_labels = labels == initial.get("metadata", {}).get("labels", {})
owned_candidate_state = (
    initial_labels
    and len(own_candidate) == 1
    and len(production) == 1
    and production[0]["revisionName"] == rollback_revision
    and not other_candidates
)
owned_promotion_state = (
    owned_labels
    and own_revision
    and len(production) == 1
    and production[0]["revisionName"] == own_revision
    and not other_candidates
)
if not (owned_candidate_state or owned_promotion_state):
    print("skip")
    raise SystemExit

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
  local revision="$3"
  local rollback_revision="$4"
  local component="$5"
  local current="${release_workspace}/${component}-cleanup-current.json"
  local payload="${release_workspace}/${component}-cleanup-payload.json"
  local response="${release_workspace}/${component}-cleanup-response.json"
  local mode=""

  api_get_service "${service}" "${current}" || return 1
  mode="$(
    prepare_cleanup_payload \
      "${current}" "${initial}" "${payload}" \
      "${revision}" "${rollback_revision}"
  )"
  if [[ "${mode}" != "restore" ]]; then
    printf 'cleanup_result=SKIPPED component=%s newer_owner_or_no_candidate\n' \
      "${component}" >&2
    return 0
  fi
  conditional_put "${service}" "${payload}" "${response}"
  wait_for_rollback \
    "${service}" "${initial}" "${rollback_revision}" \
    "${release_workspace}/${component}-cleanup-verified.json"
  printf 'cleanup_result=PASS component=%s rollback_revision=%s\n' \
    "${component}" "${rollback_revision}" >&2
}

cleanup_failed_release() {
  local cleanup_failed=0
  cleanup_service \
    "${WEB_SERVICE}" "${web_initial}" "${web_revision}" \
    "${web_rollback_revision}" web || cleanup_failed=1
  cleanup_service \
    "${API_SERVICE}" "${api_initial}" "${api_revision}" \
    "${api_rollback_revision}" api || cleanup_failed=1
  return "${cleanup_failed}"
}

on_exit() {
  local exit_code="$1"
  local cleanup_code=0

  trap - ERR INT TERM EXIT
  if [[ "${exit_code}" -ne 0 && "${candidate_mutation_started}" -eq 1 ]]; then
    set +e
    cleanup_failed_release
    cleanup_code=$?
    if [[ "${cleanup_code}" -ne 0 ]]; then
      printf 'cleanup_result=FAILED original_exit=%s cleanup_exit=%s\n' \
        "${exit_code}" "${cleanup_code}" >&2
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
    --output "${release_workspace}/carless-production-config.js" \
    "${web_url}/config.js"
  curl --fail --silent --show-error \
    --dump-header "${release_workspace}/carless-production-cors.txt" \
    --output /dev/null \
    --header \
      "Origin: https://carless-life-web-788259830737.asia-northeast1.run.app" \
    "${api_url}/health"
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

deploy_candidate \
  "${API_SERVICE}" "${api_initial}" "${api_image}" \
  "${api_rollback_revision}" api
read -r api_revision api_candidate_url < <(
  resolve_candidate \
    "${API_SERVICE}" "${api_initial}" "${api_rollback_revision}" \
    "${api_candidate}"
)

deploy_candidate \
  "${WEB_SERVICE}" "${web_initial}" "${web_image}" \
  "${web_rollback_revision}" web
read -r web_revision web_candidate_url < <(
  resolve_candidate \
    "${WEB_SERVICE}" "${web_initial}" "${web_rollback_revision}" \
    "${web_candidate}"
)

verify_candidate_revision \
  "${api_revision}" "${api_image}" "${api_initial}" api
verify_candidate_revision \
  "${web_revision}" "${web_image}" "${web_initial}" web
verify_candidate_endpoints

validate_prepromotion_state \
  "${API_SERVICE}" "${api_initial}" "${api_revision}" \
  "${api_rollback_revision}" \
  "${release_workspace}/api-prepromotion-validated.json"
validate_prepromotion_state \
  "${WEB_SERVICE}" "${web_initial}" "${web_revision}" \
  "${web_rollback_revision}" \
  "${release_workspace}/web-prepromotion-validated.json"
assert_current_main

promote_service \
  "${API_SERVICE}" "${api_initial}" "${api_revision}" \
  "${api_rollback_revision}" api
assert_current_main
promote_service \
  "${WEB_SERVICE}" "${web_initial}" "${web_revision}" \
  "${web_rollback_revision}" web

api_production_url="$(
  gcloud run services describe "${API_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format='value(status.url)'
)"
web_production_url="$(
  gcloud run services describe "${WEB_SERVICE}" \
    --project="${PROJECT_ID}" \
    --region="${DEPLOY_REGION}" \
    --format='value(status.url)'
)"
verify_production_endpoints "${api_production_url}" "${web_production_url}"
assert_current_main

trap - INT TERM EXIT
printf 'promotion_result=PASS\n'
printf 'source_commit=%s\n' "${COMMIT_SHA}"
printf 'api_image=%s\n' "${api_image}"
printf 'web_image=%s\n' "${web_image}"
printf 'api_revision=%s\n' "${api_revision}"
printf 'web_revision=%s\n' "${web_revision}"
printf 'api_rollback_revision=%s\n' "${api_rollback_revision}"
printf 'web_rollback_revision=%s\n' "${web_rollback_revision}"
printf 'api_url=%s\n' "${api_production_url}"
printf 'web_url=%s\n' "${web_production_url}"
