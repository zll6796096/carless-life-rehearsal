#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?}"
: "${DEPLOY_REGION:?}"
: "${COMMIT_SHA:?}"
service=carless-hakusan-otp-c898d7a2
repository="${DEPLOY_REGION}-docker.pkg.dev/${PROJECT_ID}/apps/${service}"
digest="$(gcloud artifacts docker images describe "${repository}:${COMMIT_SHA}" --project="${PROJECT_ID}" --format='value(image_summary.digest)')"
[[ "${digest}" =~ ^sha256:[a-f0-9]{64}$ ]]
gcloud run services update "${service}" --project="${PROJECT_ID}" --region="${DEPLOY_REGION}" \
  --image="${repository}@${digest}" --async --quiet
for attempt in $(seq 1 90); do
  state="$(gcloud run services describe "${service}" --project="${PROJECT_ID}" --region="${DEPLOY_REGION}" --format=json)"
  if printf '%s' "${state}" | python3 -c '
import json,sys
s=json.load(sys.stdin)
ready=any(c.get("type")=="Ready" and c.get("status")=="True" for c in s["status"].get("conditions",[]))
sys.exit(0 if ready and s["status"].get("observedGeneration")==s["metadata"].get("generation") else 1)
'; then
    gcloud run services describe "${service}" --project="${PROJECT_ID}" --region="${DEPLOY_REGION}" \
      --format='value(status.url)' > /workspace/carless-otp-url.txt
    echo "otp_private_service=READY image=${repository}@${digest}"
    exit 0
  fi
  sleep 2
done
echo 'OTP service did not become ready' >&2
exit 1
