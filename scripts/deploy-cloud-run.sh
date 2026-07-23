#!/usr/bin/env bash
set -euo pipefail

# Configurable defaults
PROJECT_ID="${PROJECT_ID:-zhang23-23}"
REGION="${REGION:-asia-northeast1}"
API_SERVICE="${API_SERVICE:-carless-life-api}"
WEB_SERVICE="${WEB_SERVICE:-carless-life-web}"
AR_REPO="${AR_REPO:-carless-life}"

echo "=== Carless Life Rehearsal Cloud Run Deployment ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "API Svc:  ${API_SERVICE}"
echo "WEB Svc:  ${WEB_SERVICE}"
echo "AR Repo:  ${AR_REPO}"

# Pre-flight check: gcloud active account & project
ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
echo "Active GCP account: ${ACTIVE_ACCOUNT}"
if [[ "${ACTIVE_ACCOUNT}" != "zll6796096@gmail.com" ]]; then
    echo "ERROR: Active GCP account must be zll6796096@gmail.com, found: ${ACTIVE_ACCOUNT}"
    exit 1
fi

gcloud config set project "${PROJECT_ID}" >/dev/null

# 1. Enable required APIs
echo "--> Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${PROJECT_ID}"

# 2. Ensure Artifact Registry repository exists
echo "--> Verifying Artifact Registry repository: ${AR_REPO}..."
if ! gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Creating Artifact Registry repository ${AR_REPO} in ${REGION}..."
    gcloud artifacts repositories create "${AR_REPO}" \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --description="Docker repository for Carless Life Rehearsal"
fi

# Determine Git SHA tag
GIT_SHA="$(git rev-parse --short HEAD || echo "unknown")"
API_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${API_SERVICE}:${GIT_SHA}"
WEB_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${WEB_SERVICE}:${GIT_SHA}"

# 3. Build & Deploy Backend
echo "--> Building Backend container image: ${API_IMAGE}..."
gcloud builds submit --tag "${API_IMAGE}" ./backend --project="${PROJECT_ID}"

echo "--> Deploying Backend Cloud Run service: ${API_SERVICE}..."
gcloud run deploy "${API_SERVICE}" \
    --image="${API_IMAGE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=1 \
    --cpu=1 \
    --memory=512Mi \
    --concurrency=20 \
    --set-env-vars="ROUTING_PROVIDER=mock"

API_URL="$(gcloud run services describe "${API_SERVICE}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
echo "Backend deployed at: ${API_URL}"

# Quick health check for Backend
echo "--> Verifying Backend health..."
HTTP_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" || echo "000")"
if [[ "${HTTP_STATUS}" != "200" ]]; then
    echo "ERROR: Backend health check failed with HTTP ${HTTP_STATUS}"
    exit 1
fi
echo "Backend health check PASSED (HTTP 200)"

# 4. Build & Deploy Frontend
echo "--> Building Frontend container image with fallback config: ${WEB_IMAGE}..."
gcloud builds submit --tag "${WEB_IMAGE}" ./frontend --project="${PROJECT_ID}"

echo "--> Deploying Frontend Cloud Run service: ${WEB_SERVICE}..."
gcloud run deploy "${WEB_SERVICE}" \
    --image="${WEB_IMAGE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --min-instances=0 \
    --max-instances=1 \
    --cpu=1 \
    --memory=512Mi \
    --set-env-vars="API_BASE_URL=${API_URL}"

WEB_URL="$(gcloud run services describe "${WEB_SERVICE}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
echo "Frontend deployed at: ${WEB_URL}"

# 5. Update Backend CORS_ORIGINS to include Frontend URL
echo "--> Updating Backend CORS_ORIGINS to ${WEB_URL}..."
gcloud run deploy "${API_SERVICE}" \
    --image="${API_IMAGE}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --platform=managed \
    --update-env-vars="^#^CORS_ORIGINS=${WEB_URL},https://carless-life-web-788259830737.asia-northeast1.run.app"


# 6. Post-deployment Smoke Verification
echo "=== Smoke Tests & Verification ==="
echo "1. Checking Frontend homepage (${WEB_URL}/)..."
WEB_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "${WEB_URL}/")"
echo "   Frontend homepage HTTP: ${WEB_STATUS}"

echo "2. Checking Frontend SPA routing fallback (${WEB_URL}/onboarding)..."
SPA_STATUS="$(curl -s -o /dev/null -w "%{http_code}" "${WEB_URL}/onboarding")"
echo "   Frontend /onboarding HTTP: ${SPA_STATUS}"

echo "3. Checking Backend CORS preflight..."
CORS_HEADER="$(curl -s -I -X OPTIONS "${API_URL}/diagnosis/run" \
    -H "Origin: ${WEB_URL}" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type" \
    | grep -i "access-control-allow-origin" || echo "NONE")"
echo "   CORS header: ${CORS_HEADER}"

if [[ "${WEB_STATUS}" == "200" && "${SPA_STATUS}" == "200" ]]; then
    echo "=== Deployment Completed Successfully ==="
    echo "Frontend URL: ${WEB_URL}"
    echo "Backend URL:  ${API_URL}"
else
    echo "ERROR: Post-deployment checks failed!"
    exit 1
fi
