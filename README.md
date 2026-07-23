# 車なし生活リハーサル / Carless Life Rehearsal

Web app concept for the Open Data Challenge for Public Transportation 2026.

The product helps an elderly person and their family rehearse daily life without a private car before a voluntary driver's-license return. After license return, the same app becomes a simple voice-first outing assistant.

This is not a generic route planner and does not decide whether a person should return their license. It only reports mobility feasibility based on deterministic transport data or a mock router.

## Current Status

Implemented phases:

- Prompt 0: product and architecture baseline
- Prompt 1: runnable FastAPI and Vite skeleton
- Prompt 2: domain models and fixture data
- Prompt 3: deterministic LifeScore and feasibility engine
- Prompt 4: rehearsal task generation
- Prompt 5: elderly-user main frontend flow
- Prompt 6: voice-first interaction
- Prompt 7: family/admin map mode
- Prompt 8: OTP/GTFS routing adapter
- Prompt 9: data quality report
- Prompt 10: contest submission docs and demo script

The first-stage product loop runs with fixture data and the deterministic mock router. OTP/GTFS integration is available behind configuration but is not required for the demo.

## Monorepo Structure

```text
.
├── backend/                  # FastAPI + Python 3.12-compatible + Pydantic + pytest
├── frontend/                 # Vite + React + TypeScript
├── docs/
│   ├── architecture.md
│   ├── data-policy.md
│   ├── open-data-challenge-2026-fit.md
│   └── product-blueprint.md
├── docker-compose.yml        # Local development services
├── Makefile                  # Test, build, and dev commands
└── README.md
```

## Product Boundary

The app must:

- show whether everyday destinations can be reached without a private car
- surface missing data as warnings or `判定不能`
- keep the elderly user's main UI simple, large-button, voice-friendly, and not map-first
- use fixture data and a deterministic mock router in the initial implementation
- keep public transport data provenance auditable

The app must not:

- promote license return as a conclusion
- make medical, care, legal, or safety-critical decisions
- hallucinate routes with an LLM
- redistribute raw ODPT or challenge data
- require production secrets for the fixture-based demo

## Local Development

```bash
make check-docs
make dev
make test
make backend-test
make frontend-build
```

Local service URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Backend health check: `http://localhost:8000/health`

No production secrets or API keys are required for the initial fixture demo.

Implemented backend API:

- `GET /health`
- `GET /fixtures/demo`
- `POST /diagnosis/run`
- `POST /rehearsals/generate`
- `GET /rehearsals/{id}`
- `GET /data-quality`

## Documentation

- [Product blueprint](docs/product-blueprint.md)
- [Architecture](docs/architecture.md)
- [Data policy](docs/data-policy.md)
- [Open Data Challenge 2026 fit](docs/open-data-challenge-2026-fit.md)
- [Japanese demo script](docs/demo-script-ja.md)
- [Chinese demo script](docs/demo-script-zh.md)
- [Japanese submission summary](docs/submission-summary-ja.md)
- [Technical notes](docs/technical-notes.md)

## Cloud Run Deployment (DEMO_ONLY)

Production deployment is owned exclusively by the `main` branch Cloud Build
Trigger. The local `make deploy-cloud-run` target is an intentional fail-closed
guard and cannot build or mutate Cloud Run.

### Infrastructure Configuration

- **GCP Project**: `zhang23-23`
- **Region**: `asia-northeast1`
- **Backend Service**: `carless-life-api` (FastAPI, 1 CPU, 512 MiB, concurrency 20, min 0, max 1)
- **Frontend Service**: `carless-life-web` (Nginx SPA, 1 CPU, 512 MiB, min 0, max 1)
- **Artifact Registry**: `apps`

## Production delivery

Pushes to `main` are built by the Google Cloud Build Trigger
`carless-main-cloud-run`. The build runs backend and frontend acceptance,
publishes full-Git-SHA images into `apps`, then acquires an owner-checked,
resource-version-conditional release lock before any Cloud Run candidate
mutation. It first tests an isolated browser chain in which the candidate Web
revision points to the exact candidate API URL and that API allows only the
exact candidate Web origin in addition to the stable origins. It then creates
production-configured zero-traffic candidates, verifies their immutable image
digests, fixture diagnosis, CORS preflight, and SPA/onboarding entry, and only
then promotes both services. Any interruption before the final pair gate
restores both exact old revisions while the lock is still owned.

`scripts/git-deploy.sh` performs an explicit clean-tree push; it does not stage
files or deploy local source.

The public app requires no account or login:

- Web: <https://carless-life-web-788259830737.asia-northeast1.run.app/>
- API health: <https://carless-life-api-788259830737.asia-northeast1.run.app/health>

Each successful release log records the exact pair:

- `api_rollback_revision=...`
- `web_rollback_revision=...`

Do not infer rollback targets from creation order. Copy both exact values from
the same successful Cloud Build log and run the validation-only helper:

```bash
API_ROLLBACK_REVISION=carless-life-api-... \
WEB_ROLLBACK_REVISION=carless-life-web-... \
  bash scripts/rollback-cloud-run.sh
```

The helper refuses an active release lock and verifies that both named
revisions are Ready, immutable-digest backed, component-correct, and owned by
the same source commit and Cloud Build release. It prints the two exact traffic
commands for explicit operator review; it does not execute a rollback.

### Operational Limitations & Guidelines

- **DEMO_ONLY**: This deployment uses deterministic fixture/mock routing data for demonstration purposes only.
- **Stateless**: No database or persistent storage is attached; memory data resets on instance restart.
- **Rollback**: Use only the exact validated API/Web pair from one successful
  release log; never select a revision by recency.
