# Technical Notes

## Architecture

The project is a monorepo:

- `backend/`: FastAPI + Pydantic + pytest
- `frontend/`: Vite + React + TypeScript
- `docs/`: product, architecture, data policy, demo, and submission documents

## Backend API

- `GET /health`
- `GET /fixtures/demo`
- `POST /diagnosis/run`
- `POST /rehearsals/generate`
- `GET /rehearsals/{id}`
- `GET /data-quality`

## Diagnosis Engine

The diagnosis engine is deterministic. It evaluates outbound feasibility, return feasibility, walking time, transfer count, waiting time, missing return option, fragile one-option route, and missing data.

It returns Japanese reasons and one of `ok`, `caution`, `support_needed`, or `unknown`.

LifeScore uses category weights for supermarket, hospital, pharmacy, city hall, station, and social destinations.

## Routing

Routing is behind a provider interface:

```text
plan_trip(origin, destination, departure_time, profile, direction) -> TripPlanResult
```

Providers:

- `MockRoutingProvider`: default for fixture demo and tests
- `OTPRoutingProvider`: OpenTripPlanner GraphQL over HTTP

Configuration:

- `ROUTING_PROVIDER=mock|otp`
- `OTP_GRAPHQL_URL`

If OTP is unavailable, the app returns `unknown` with a data quality warning. It does not crash diagnosis and does not expose raw internal IDs to elderly-facing UI.

## Data Quality

`GET /data-quality` returns level, warnings, feed summary, and last checked time. When GTFS data is absent, it returns `unknown` with warnings instead of crashing.

## Hakusan Data Contract

`data/hakusan/` contains tracked metadata and policy only. It pins the exact
Hakusan `めぐーる` feed UID and SHA-256, records CC BY 4.0/ODbL attribution,
defines six destination records, classifies all 21 feed routes, and stores the
reviewed MobilityData validator summary.

The feed is a static timetable. There is no GTFS-RT endpoint, so no component
may represent results as live operation or delay information.

The contract validator is offline and uses only the Python standard library:

```bash
make hakusan-data-test
```

Reproducing raw evidence is an explicit local operation because raw archives
and reports are not committed:

```bash
make hakusan-data-evidence \
  HAKUSAN_GTFS_ZIP=/path/to/pinned-feed.zip \
  HAKUSAN_VALIDATOR_REPORT=/path/to/validator/report.json
```

This Gate 0 contract does not change runtime routing. `ROUTING_PROVIDER=mock`
remains the current demo default until the OTP integration plan is executed and
verified.

## Frontend

Implemented routes:

- `/`
- `/onboarding`
- `/diagnosis`
- `/result`
- `/rehearsal`
- `/daily`
- `/map`
- `/data-quality`

The elderly-user path is not map-first. It uses large buttons, short Japanese text, speech synthesis, speech-recognition fallback, and fixture-backed API calls.

The family/admin map mode uses MapLibre with a local blank style, so it does not require an external map API key for the demo.

## Verification Commands

```bash
make test
make backend-test
make frontend-build
cd backend && uv run ruff check .
cd frontend && npm run lint
```
