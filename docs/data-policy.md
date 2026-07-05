# Data Policy

## Policy Objective

Use public transportation open data responsibly while keeping the fixture demo runnable, auditable, and secret-free.

## Data Sources

Allowed future source categories:

- GTFS static data
- ODPT public transportation data
- OpenTripPlanner output derived from authorized local feeds
- optional demand transport metadata when available and legally usable
- fixture data created for this repository

The phase-1 demo uses fixture data and a deterministic mock router by default.

The backend also includes an optional OpenTripPlanner GraphQL adapter for later GTFS/ODPT integration. It is disabled unless configured with environment variables.

## Raw Data Redistribution

The repository must not redistribute raw ODPT or challenge data.

Committed fixture data must be synthetic, minimal, and clearly labeled as demo data. It must not be a copied subset of licensed feed files.

## Secrets

No production secrets or API keys are required for the initial implementation.

Future secret rules:

- API keys must come from the current process environment or untracked local files.
- Secret values must never be committed.
- Logs and reports must redact tokenized URLs.
- Token presence does not imply feed readiness.

## Missing Data

Missing, stale, or unsupported data must be surfaced to the user as:

- `判定不能`
- `unknown`
- data quality warning
- reduced data confidence

The app must not silently replace missing transport data with LLM guesses.

## Data Quality Levels

Implemented levels:

- `high`: enough current data exists to make a reliable feasibility judgment
- `medium`: usable data exists but has notable gaps
- `low`: important data is missing or stale
- `unknown`: no reliable data quality evidence is available

## Minimum Data Quality Checks

GTFS/OTP phases should check:

- `feed_info` exists
- `calendar` or `calendar_dates` exists
- stops have coordinates
- routes, trips, and stop_times exist
- target weekday service is available
- demand transport booking fields exist when demand transit is evaluated
- text-to-speech friendly names exist when available

The project can ingest MobilityData GTFS Validator JSON output when available. It does not build a full validator from scratch.

Implemented `/data-quality` behavior:

- returns `unknown` with warnings when GTFS is absent
- checks required GTFS files when a future integration supplies a GTFS directory
- can translate validator notices into warnings

## User-Facing Data Policy

The elderly user should see simple warnings, not technical feed details.

Family/admin mode may show more detail, including:

- data confidence
- warning category
- affected destination
- last checked time
- provider used

Raw feed IDs and internal route IDs must not appear in elderly-facing memos.
