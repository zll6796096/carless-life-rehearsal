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

## Hakusan OTP Gate 1

Gate 1 is a local evidence layer, not a backend/provider switch. It pins
OpenTripPlanner 2.9.0, its release SHA-256 and size, Java 25, the Gate 0 source
GTFS identity, three configuration/query files, a hash-locked Pyosmium 4.3.1
converter, and both canonical historical OSM XML and derived PBF identities.
The deterministic pilot contains 11 fixed routes, 115 trips, 2,867 stop-times,
and 205 stops. Raw and generated inputs remain ignored.

The normal offline gate is:

```bash
make hakusan-otp-test
```

It runs six standard-library test modules, validates the committed source
contract, and checks these documentation markers. It does not access the
network, execute Java, or write an evidence summary.

Acquisition is deliberately separate:

```bash
make hakusan-otp-fetch
```

The fetcher accepts only HTTPS and allowlisted GitHub/Overpass redirect hosts,
writes through temporary sibling files, verifies pinned size and SHA-256 before
replacement, and canonicalizes changing Overpass response metadata. The Make
workflow then creates an ignored virtual environment, installs Pyosmium 4.3.1
from a hash-locked binary-wheel requirement, and converts the verified XML to
the exact hash-pinned OSM PBF. All generated files remain under ignored
`data/external/`.

The explicit evidence command is:

```bash
make hakusan-otp-evidence \
  HAKUSAN_GTFS_ZIP=/path/to/pinned-feed.zip
```

It validates every input, rejects XML in place of the pinned OSM PBF, creates
the allowlisted GTFS, builds and reloads an OTP graph with a 2 GiB heap cap and
bounded timeouts, and binds the server to `127.0.0.1:18081`. It queries the GTFS
GraphQL endpoint `/otp/gtfs/v1` using
the non-deprecated `planConnection` API with transit-only BUS plus WALK
access/egress/transfer. Acceptance requires exactly the 11 route IDs, all six
destination access stops, and WALK+BUS outbound and return itineraries on
2026-09-08. The Java process is terminated before the sanitized summary is
written.

Gate 1 does not modify `ROUTING_PROVIDER=mock`, the current backend adapter,
frontend behavior, Cloud Run configuration, or deployment. Those are separate
Gate 2 and release acceptance decisions.

## Frontend

Gate 2 backend integration uses the live OTP 2.9.0 schema (`planConnection`,
`numberOfTransfers`, and leg `start/end.scheduledTime`). The adapter validates
all returned alternatives against the fixed-route allowlist and exposes no
internal route IDs. A valid walking-only route with
`WALKING_BETTER_THAN_TRANSIT` is accepted; other routing/GraphQL errors fail
closed. Explicit request datetimes replace the former fixed July date, and
return coordinates are reversed. The acquisition and graph policy from Gate 1
remain prerequisites.

The six-category API evidence is reproducible using
`scripts/run_hakusan_gate2_evidence.py` with the backend virtual environment.
It verifies provider selection, all twelve directional plans, and missing-date
unknown results. `accessibility_verified` is false for OTP plans and contributes
a warning and caution to diagnosis when stair avoidance is requested.

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
make hakusan-otp-test
make backend-test
make frontend-build
cd backend && uv run ruff check .
cd frontend && npm run lint
```
