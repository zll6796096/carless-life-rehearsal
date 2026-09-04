# Hakusan OTP Gate 1 Design

**Status:** Approved by the user on 2026-09-05; implementation authorized.

## Objective

Prove that the pinned Hakusan `めぐーる` data can produce a local,
license-auditable OpenTripPlanner graph that supports walking plus fixed-route
bus journeys while making reservation-required and out-of-pilot routes
impossible to return.

The first-principles rule is data integrity and elderly-user safety before
feature breadth. Gate 1 therefore proves the graph and its route boundary
before any application runtime switches from the deterministic mock provider.

## Selected Approach

Use the official OpenTripPlanner 2.9.0 shaded JAR with Java 25. The release
asset, source GTFS, historical OSM extract, configuration, and route policy are
all pinned by SHA-256 before graph construction.

The build input is not the full Hakusan feed. A deterministic preparation step
creates a derived GTFS ZIP containing only the 11 fixed routes explicitly
allowed by `data/hakusan/route-rules.json`. This moves the safety policy to the
graph boundary: excluded routes cannot leak through a missing GraphQL filter or
a later backend mistake because they do not exist in the graph.

Two alternatives were rejected:

- A pinned OTP container would be portable, but adds a Docker-daemon dependency
  when the host already has the required Java 25 runtime.
- Building the full 21-route feed and filtering query results would be simpler,
  but leaves reservation-required services inside the graph and is not
  fail-closed.

## Scope

Gate 1 includes:

- pinned OTP 2.9.0 release identity and SHA-256;
- a fixed historical OpenStreetMap street snapshot and SHA-256;
- deterministic creation and validation of the 11-route pilot GTFS;
- local OTP graph build and server startup;
- GraphQL inventory, stop-presence, and walking-plus-bus journey evidence;
- a committed evidence summary containing only metadata and results;
- offline tests, Make targets, and operator documentation.

Gate 1 excludes:

- changing `ROUTING_PROVIDER=mock` or the backend routing provider;
- frontend or elderly-facing copy changes;
- GTFS-Realtime, delay, vehicle, or service-alert claims;
- Docker Compose, Cloud Build, Cloud Run, production secrets, push, or deploy;
- committing raw GTFS, OSM, the OTP JAR, graph binary, or full OTP logs.

## Source and Artifact Contract

### GTFS

The source remains the Gate 0 artifact UID
`765cd548-a1f3-46e6-b05b-d6168b9b85d1` with SHA-256
`ea1a0108c4a7f24215aa1b3811a267d85abf9777a356b8c7b3ff857edbcae740`.
The source archive is read from an operator-supplied path and never copied into
tracked storage.

The derived ZIP is deterministic:

- entries use a fixed order and fixed ZIP timestamp;
- CSV output is UTF-8 with LF line endings;
- source row order is preserved within every retained table;
- `routes.txt` retains exactly the 11 allowlisted route IDs;
- `trips.txt` retains trips on those routes;
- `stop_times.txt` retains rows for those trips;
- `shapes.txt` retains shapes referenced by those trips;
- `stops.txt` retains referenced stops and any parent stations recursively;
- `calendar.txt` and `calendar_dates.txt` retain referenced service IDs;
- `fare_rules.txt` retains rows for retained routes and
  `fare_attributes.txt` retains referenced fares;
- agency, feed information, and applicable translations are retained;
- every retained foreign-key reference is validated before the ZIP is accepted.

The preparation command fails on a source checksum mismatch, any unclassified
route, a missing allowlisted route, an excluded route in the output, a broken
reference, or a destination access stop missing from the output.

### OpenStreetMap

The street snapshot is fetched through a tracked Overpass QL file at historical
timestamp `2026-09-03T00:00:00Z`. Its bounding box is the allowed-route stop
extent plus an approximately two-kilometre margin:

```text
south=36.44917
west=136.4535465
north=36.58471
east=136.6223390
```

The query retains highway ways, required member nodes, and restriction
relations. Overpass adds mutable server metadata such as `osm_base` even for a
historical query, so the raw response is not used as the reproducibility hash.
A deterministic canonicalization step removes the root generator, note, meta,
and contributor `user`/`uid` attributes, writes fixed bounds, sorts top-level
OSM elements by type and numeric ID, sorts tags by key/value, and preserves way
node order and relation member order. The exact query text, endpoint, timestamp,
canonical snapshot SHA-256, and ODbL attribution are stored in the tracked
source manifest. Both the raw response and canonical `.osm` snapshot remain
under ignored `data/external/hakusan/otp/` storage; OTP receives only the
canonical snapshot.

### OpenTripPlanner

The source manifest records:

- version `2.9.0`;
- official GitHub release asset URL;
- locally verified JAR SHA-256;
- required Java major version `25`;
- build and router configuration SHA-256 values.

Acquisition never trusts a mutable `latest` URL. A download is accepted only
after its checksum matches the committed manifest.

## Components

### `data/hakusan/otp-sources.json`

Tracked machine-readable contract for OTP, OSM, derived-feed policy, service
test date, expected route/stop counts, and all immutable hashes.

### `config/otp/hakusan/`

Contains:

- `osm-overpass.ql`: fixed historical OSM query;
- `build-config.json`: absolute transit service range, import report enabled,
  and a version label;
- `router-config.json`: minimal versioned configuration with no production
  updater or realtime source.

OTP configuration is intentionally minimal because its JSON schema changes
between releases. Unknown configuration parameters are a hard evidence failure.

### `scripts/prepare_hakusan_otp.py`

Pure-Python, standard-library preparation and validation. Its core functions
accept explicit paths, return structured errors, and perform no network access.
The CLI writes the deterministic pilot ZIP only after all checks pass.

### `scripts/prepare_hakusan_osm.py`

Pure-Python, standard-library OSM canonicalization. It checks the requested
historical date and bounds against the tracked query contract, removes mutable
Overpass response metadata and unnecessary contributor identifiers, and writes
a stable XML snapshot before its SHA-256 is validated.

### `scripts/fetch_hakusan_otp_inputs.py`

Explicit network command for the pinned JAR and historical OSM query. It writes
only ignored external storage, uses timeouts, refuses redirects to an
unexpected host, and validates committed hashes. Normal tests never invoke it.

### `scripts/run_hakusan_otp_evidence.py`

Orchestrates one bounded local evidence run:

1. Verify Java 25 and every input/config checksum.
2. Create and validate the pilot GTFS.
3. Run OTP with a 2 GiB JVM heap cap to build and save `graph.obj`.
4. Start the saved graph on `127.0.0.1:18081`.
5. Poll the GTFS GraphQL endpoint until ready or the startup deadline expires.
6. Query route inventory and require exactly the 11 allowlisted route IDs.
7. Query all six destination access stops and require each to be present.
8. Run an outbound and return journey between a residential point near 松任駅
   and 公立松任石川中央病院 on Tuesday 2026-09-08.
9. Require each accepted journey to contain both WALK and BUS legs and require
   every BUS route ID to be allowlisted.
10. Terminate the child OTP process in a `finally` block and write a sanitized
    evidence summary.

The runner fails on GraphQL errors, an excluded route, missing destination
stops, a bus-free itinerary, a walk-free itinerary, unexpected OTP config
warnings, process timeout, or unsuccessful cleanup. It never falls back to mock
results.

### Tests and Make targets

Offline tests use synthetic minimal GTFS and captured GraphQL-shaped payloads.
They cover:

- source hash enforcement;
- route/dependent-table filtering;
- deterministic ZIP bytes;
- deterministic canonical OSM bytes despite changing Overpass `osm_base` and
  generator metadata;
- missing route and broken-reference rejection;
- destination access-stop preservation;
- exact route-inventory enforcement;
- excluded-route rejection;
- WALK plus BUS journey enforcement;
- GraphQL error and timeout failure behavior;
- evidence redaction and process cleanup helpers.

`make test` includes only the offline `hakusan-otp-test` target. The explicit
`make hakusan-otp-evidence` target requires local artifact paths and starts the
real Java process. A separate acquisition target is the only command permitted
to use the network.

## Data Flow

```text
pinned GTFS + route policy
          |
          v
deterministic 11-route pilot GTFS ----+
                                      |
canonical pinned OSM + pinned OTP JAR +--> OTP graph build
                                                |
                                                v
                                      local GTFS GraphQL
                                                |
                     +--------------------------+------------------+
                     |                          |                  |
              exact route set          six access stops    WALK+BUS round trip
                     +--------------------------+------------------+
                                                |
                                                v
                                   sanitized evidence summary
```

## Failure Semantics

Every stage is fail-closed. Missing files, changed hashes, new/unclassified
routes, invalid references, unavailable OSM history, OTP startup failure, or an
unexpected GraphQL result stops the run and produces no success summary.
Partial output stays in ignored storage and is not treated as evidence.

The graph hash is recorded for traceability, but byte-identical graph output is
not asserted because OTP serialization may embed build-specific values.
Reproducibility means identical validated inputs, configuration, transformation
rules, OTP version, and acceptance queries.

## Acceptance Criteria

Gate 1 is accepted only when fresh evidence shows:

1. Offline unit and documentation gates pass.
2. Source GTFS, canonical OSM, OTP JAR, and configs match committed hashes.
3. The derived GTFS contains 11 allowed and zero excluded routes.
4. OTP 2.9.0 builds and reloads the graph under the bounded Java process.
5. GraphQL exposes exactly 11 allowlisted routes and all six destination stops.
6. The hospital outbound and return scenarios each contain WALK and BUS legs,
   with no route outside the allowlist.
7. The committed summary contains no raw feed records, personal data, secrets,
   mutable download URL, or unredacted local absolute path.
8. Full repository tests, lint, build, `git diff --check`, diff review, and Git
   status review complete without a Gate 1 regression.

## Risks and Guardrails

- **OSM coverage:** all 205 pilot stops must fall inside the query extent; stop
  linking or route evidence failure blocks acceptance rather than silently
  expanding to mutable data.
- **Sparse timetable:** scenarios use a known weekday inside the pinned service
  period and do not imply realtime availability.
- **Reservation leakage:** route removal happens before graph build and is
  independently checked in the derived ZIP and GraphQL inventory.
- **Resource use:** build and server processes use a 2 GiB heap cap and bounded
  timeouts; raising the limit requires evidence that the small Hakusan graph
  needs it.
- **Version drift:** no `latest` URL or unpinned OTP configuration is accepted.
- **Product truthfulness:** Gate 1 evidence does not authorize runtime, UI, or
  production claims; `ROUTING_PROVIDER=mock` remains unchanged.

## Authoritative References

- OpenTripPlanner 2.9.0 release:
  <https://github.com/opentripplanner/OpenTripPlanner/releases/tag/v2.9.0>
- OTP graph build configuration:
  <https://docs.opentripplanner.org/en/v2.9.0/BuildConfiguration/>
- OTP GTFS GraphQL endpoint and examples:
  <https://docs.opentripplanner.org/en/v2.9.0/apis/GTFS-GraphQL-API/>
- OpenStreetMap Overpass historical `date` query semantics:
  <https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL>
