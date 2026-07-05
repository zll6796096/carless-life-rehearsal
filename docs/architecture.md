# Architecture

## Architecture Goal

Build a small, auditable monorepo where routing and diagnosis are deterministic, explainable, and testable before any real GTFS/ODPT/OTP integration.

## Monorepo Layout

```text
frontend/
  Vite + React + TypeScript app
  Elderly-first flow, voice UI, and family/admin map mode

backend/
  FastAPI + Python 3.12 service
  Pydantic models, deterministic engines, router adapters, and pytest

docs/
  Product, architecture, data policy, contest fit, demo scripts, and technical notes
```

## Backend Responsibilities

The backend owns:

- domain models
- fixture data
- deterministic mock routing
- diagnosis engine
- LifeScore aggregation
- rehearsal task generation
- data quality warnings
- OTP GraphQL adapter

The backend must never return hallucinated route details.

## Frontend Responsibilities

The frontend owns:

- elderly-user main flow
- large-button onboarding
- diagnosis result display
- voice synthesis and speech-command fallback
- rehearsal task display
- family/admin map and report

The elderly flow must remain usable without opening a map.

## Backend Modules

```text
backend/app/
  main.py
  core/config.py
  domain/models.py
  fixtures/demo.py
  services/routing/base.py
  services/routing/mock.py
  services/routing/otp.py
  services/diagnosis/engine.py
  services/rehearsal/engine.py
  services/data_quality/service.py
  api/routes/
```

## Frontend Modules

```text
frontend/src/
  main.tsx
  App.tsx
  components/
  pages/
  services/api.ts
  state/AppState.tsx
  utils/
```

## Data Flow

```text
Home and common destinations
        ↓
Mobility profile and time windows
        ↓
RoutingProvider
  ├─ MockRoutingProvider for phase-1 fixtures
  └─ OTPRoutingProvider for later GTFS/OTP integration
        ↓
Feasibility engine
        ↓
LifeDiagnosis with reasons and data warnings
        ↓
Rehearsal engine
        ↓
Elderly UI, voice memo, and family/admin report
```

## Routing Provider Boundary

All route plans must pass through a `RoutingProvider` interface:

```text
plan_trip(origin, destination, departure_time, profile, direction) -> TripPlanResult
```

Provider rules:

- `mock` is the default for tests and fixture demo.
- `otp` is optional and configured by environment variables.
- provider failure must return `unknown` plus data quality warnings, not crash diagnosis.
- raw internal route IDs must not be shown in elderly UI.

## Implemented API Surface

- `GET /health`
- `GET /fixtures/demo`
- `POST /diagnosis/run`
- `POST /rehearsals/generate`
- `GET /rehearsals/{id}`
- `GET /data-quality`

The implemented diagnosis path defaults to fixture data and deterministic mock transport results. It evaluates outbound and return feasibility, walking time, transfers, wait time, return availability, fragile single-option routes, and missing data.

## Configuration

Initial fixture demo:

- no secrets
- no external API keys
- `ROUTING_PROVIDER=mock`

Optional OTP integration:

- `ROUTING_PROVIDER=mock|otp`
- `OTP_GRAPHQL_URL`

Secrets must come from the current process environment or local untracked files, never from committed files.

## Testing Strategy

Backend:

- Pydantic model tests are implemented.
- health check test is implemented.
- diagnosis engine unit tests are implemented.
- rehearsal engine unit tests are implemented.
- mock router tests are implemented.
- OTP adapter tests with mocked HTTP responses are implemented.

Frontend:

- route rendering tests are implemented.
- build check is implemented.
- focused interaction tests for primary flow are implemented.

Documentation:

- phase-specific document presence and keyword checks

## Guardrails

- No raw ODPT/challenge data in the repository.
- No route generation by LLM.
- Missing data becomes `unknown`, `判定不能`, or explicit warning.
- Back-end status and front-end status labels must use the same enum semantics.
- Family/admin map mode must not replace the elderly main flow.
