# Data Policy

## Policy Objective

Use public transportation open data responsibly while keeping the fixture demo runnable, auditable, and secret-free.

## Selected Data Sources

The first real-data candidate is pinned in `data/hakusan/manifest.json`:

- 白山市コミュニティバス「めぐーる」 GTFS static feed
- GTFS Data Repository artifact UID
  `765cd548-a1f3-46e6-b05b-d6168b9b85d1`
- publisher: 白山市
- license: CC BY 4.0 (`CC-BY-4.0`)
- service period: 2026-03-16 through 2027-03-15
- one pharmacy POI from OpenStreetMap under ODbL; the remaining pilot
  destinations use records from the pinned GTFS feed

The current application still uses fixture data and a deterministic mock router
by default. A pinned data contract is not evidence that OTP or production
routing is connected.

Hakusan Gate 1 derives a deterministic pilot GTFS containing exactly the 11
allowlisted fixed routes before OpenTripPlanner sees the feed. Trips,
stop-times, shapes, stops and parent stations, service calendars, fares, and
applicable translations are filtered with retained-reference validation. A new
or unclassified route fails closed; filtering GraphQL output after building a
larger graph is not accepted as the policy boundary.

Pedestrian routing uses a canonical historical OpenStreetMap XML snapshot for
`2026-09-03T00:00:00Z`, bounded to the reviewed pilot area. The tracked query,
canonical hash, and ODbL 1.0 attribution are part of the source contract. The
source is a static timetable and is not realtime; it cannot support delay,
vehicle-position, or live-operation claims.

The backend also includes an optional OpenTripPlanner GraphQL adapter for later GTFS/ODPT integration. It is disabled unless configured with environment variables.

## Raw Data Redistribution

The repository must not redistribute raw ODPT or challenge data.

Raw GTFS archives, validator reports/JARs, OSM extracts, and OTP graphs stay in
ignored `data/external/` or operator-owned temporary storage. Only source
identity, derived validation summaries, checksums, and policy are committed.

The OTP JAR, canonical OSM, deterministic pilot ZIP, `graph.obj`, build report,
and full OTP logs also stay in `data/external/`. The only Gate 1 output eligible
for tracking is a sanitized JSON summary containing hashes, aggregate counts,
allowlisted identifiers, and pass/fail evidence. It must not contain absolute
local paths, secrets, raw GTFS rows, or mutable download URLs.

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

## Attribution

The family/admin data-information surface must display:

> 本サービスは、白山市が公開する「白山市コミュニティバス『めぐーる』GTFSデータ」（CC BY 4.0）を加工して利用しています。

When OpenStreetMap-derived destination or pedestrian data is used, it must also
display:

> © OpenStreetMap contributors, ODbL

## Pilot Route Policy

`data/hakusan/route-rules.json` is deny-by-default. Only the explicitly listed
Matsuto/Mikawa fixed routes may be considered by the first real-data pilot.
Hakusan-roku routes outside the pilot remain unavailable, and routes identified
by the city as reservation-required must never be presented as ordinary
walk-up service. Missing or changed classifications produce `unknown` rather
than a mock fallback.
