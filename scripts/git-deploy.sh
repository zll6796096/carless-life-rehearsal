#!/usr/bin/env bash
set -euo pipefail

# Configurable defaults
PROJECT_ID="${PROJECT_ID:-zhang23-23}"
REGION="${REGION:-asia-northeast1}"
API_SERVICE="${API_SERVICE:-carless-life-api}"
WEB_SERVICE="${WEB_SERVICE:-carless-life-web}"
COMMIT_MSG="${1:-feat: update code and trigger Cloud Run remote deployment}"

echo "=== Carless Life Rehearsal Git Push & Cloud Run Deployment ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Commit:   ${COMMIT_MSG}"

# Step 1: Git Add, Commit & Push
echo "--> Staging local changes..."
git add .

if git diff-index --quiet HEAD --; then
    echo "No uncommitted local changes found. Proceeding with current commit..."
else
    echo "--> Committing changes..."
    git commit -m "${COMMIT_MSG}"
fi

echo "--> Pushing to Git remote (origin main)..."
git push origin main

# Step 2: Trigger Remote Cloud Build Deployment
echo "--> Executing Cloud Build remote deployment from Git repo..."
gcloud builds submit --config=cloudbuild.yaml --project="${PROJECT_ID}" .

# Step 3: Verification
API_URL="$(gcloud run services describe "${API_SERVICE}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
WEB_URL="$(gcloud run services describe "${WEB_SERVICE}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"

echo "=== Verification ==="
echo "Backend URL:  ${API_URL}"
echo "Frontend URL: ${WEB_URL}"

echo "Checking Backend health..."
curl -sf "${API_URL}/health" && echo " Backend Health PASSED"

echo "Checking Frontend homepage..."
curl -sf "${WEB_URL}/" >/dev/null && echo " Frontend Homepage PASSED"

echo "=== Git Push & Remote Cloud Run Deployment Complete! ==="
