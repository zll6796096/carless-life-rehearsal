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

## Phase Roadmap

1. Prompt 0: project blueprint and architecture documents
2. Prompt 1: FastAPI and Vite project skeleton
3. Prompt 2: domain models and fixture data
4. Prompt 3: deterministic diagnosis and LifeScore engine
5. Prompt 4: rehearsal task generation
6. Prompt 5: elderly-user main frontend flow
7. Prompt 6: voice-first interaction
8. Prompt 7: family/admin map mode
9. Prompt 8: OTP/GTFS routing adapter
10. Prompt 9: data quality report
11. Prompt 10: contest submission docs and demo script
