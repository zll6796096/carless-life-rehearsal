# Hakusan OTP Gate 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a local OpenTripPlanner 2.9.0 graph from a deterministic 11-route Hakusan pilot GTFS and a canonical historical OSM snapshot, without changing the application's mock runtime.

**Architecture:** Pure-Python offline preparation creates canonical OSM XML, a hash-pinned PBF derivative, and a referentially valid allowlisted GTFS before OTP sees either actual input. A bounded Java runner builds and loads the graph, queries the official GTFS GraphQL API for exact route/stop inventory and WALK+BUS round trips, and emits a sanitized evidence summary while raw artifacts remain ignored.

**Tech Stack:** Python 3.12 standard library, hash-pinned Pyosmium 4.3.1 binary wheel, `unittest`, OpenTripPlanner 2.9.0, Java 25, GTFS, OpenStreetMap XML/PBF and Overpass QL, GraphQL, Make.

---

## Scope and acceptance lock

- Real objective: prove the Hakusan fixed-route graph boundary before runtime integration.
- First-principles rule: verifiable data integrity and elderly safety before feature breadth.
- Minimal deliverable: deterministic data preparation plus one real OTP graph and query evidence run.
- Out of scope: backend provider changes, frontend changes, Docker, cloud configuration, push, and deployment.
- Guardrails: raw GTFS/OSM/JAR/graph/logs stay under ignored storage; excluded routes fail closed; Java heap is capped at 2 GiB; all processes have timeouts and cleanup.
- Final proof commands: `make test`, the explicit real-artifact
  `make hakusan-otp-evidence` invocation in Task 7, `git diff --check`, and
  `git status --short --branch`.

### Evidence-driven amendment: OTP requires PBF

The first real graph build established a factual mismatch in the approved
plan: OTP 2.9.0 discovers an `.osm` file but sends it to its binary PBF parser,
which fails on XML. JAR inspection and a controlled conversion/build probe
confirmed the smallest fix. The canonical XML remains the reproducible source;
a new `prepare_hakusan_osm_pbf.py` stage uses exactly Pyosmium 4.3.1 from a
hash-locked binary-wheel requirements file. The evidence runner accepts only
the committed `.osm.pbf` filename, size, and SHA-256. This amendment changes no
product, runtime-provider, frontend, deployment, or data-policy boundary.

### Task 1: Canonicalize historical OSM deterministically

**Files:**
- Create: `scripts/test_prepare_hakusan_osm.py`
- Create: `scripts/prepare_hakusan_osm.py`

- [ ] **Step 1: Write the canonicalization tests**

Create two semantically identical OSM XML fixtures that differ in `generator`,
`osm_base`, contributor `user`/`uid`, top-level element order, and tag order.
Assert that both produce identical bytes, fixed bounds, stable element order,
no mutable metadata, and no contributor identifiers:

```python
class CanonicalOsmTests(unittest.TestCase):
    def test_mutable_overpass_metadata_does_not_change_output(self) -> None:
        first = self._write_osm("one.osm", generator="0.7.1", osm_base="2026-09-04T00:00:00Z")
        second = self._write_osm("two.osm", generator="0.7.2", osm_base="2026-09-05T00:00:00Z", reverse=True)

        first_bytes = canonicalize_osm(first, self.root / "first-canonical.osm", BOUNDS)
        second_bytes = canonicalize_osm(second, self.root / "second-canonical.osm", BOUNDS)

        self.assertEqual(first_bytes, second_bytes)
        self.assertNotIn(b"osm_base", first_bytes)
        self.assertNotIn(b"user=", first_bytes)
        self.assertNotIn(b"uid=", first_bytes)

    def test_rejects_input_without_osm_elements(self) -> None:
        source = self.root / "empty.osm"
        source.write_text('<osm version="0.6"><meta osm_base="x"/></osm>')
        with self.assertRaisesRegex(ValueError, "no node, way, or relation elements"):
            canonicalize_osm(source, self.root / "out.osm", BOUNDS)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m unittest scripts/test_prepare_hakusan_osm.py
```

Expected: import failure because `scripts.prepare_hakusan_osm` does not exist.

- [ ] **Step 3: Implement minimal canonicalization**

Expose this public API and CLI:

```python
Bounds = tuple[str, str, str, str]

def canonicalize_osm(source: Path, destination: Path, bounds: Bounds) -> bytes:
    """Write stable OSM XML and return the exact written bytes."""

def main(argv: Sequence[str] | None = None) -> int:
    """Accept --input, --output, --south, --west, --north, and --east."""
```

Implementation rules:

- parse with `xml.etree.ElementTree`;
- keep only `node`, `way`, and `relation` top-level elements;
- remove `user` and `uid` attributes recursively;
- sort all remaining attributes by key;
- sort top-level elements as node, way, relation, then numeric ID;
- preserve `nd` and `member` order; sort `tag` children by `(k, v)`;
- emit fixed root attributes and the caller-supplied bounds;
- write through a temporary sibling and `Path.replace()` only on success.

- [ ] **Step 4: Run the tests and verify GREEN**

Run: `python3 -m unittest scripts/test_prepare_hakusan_osm.py`

Expected: all canonical OSM tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/test_prepare_hakusan_osm.py scripts/prepare_hakusan_osm.py
git diff --cached --check
git commit -m "feat: canonicalize Hakusan OSM snapshots"
```

### Task 2: Create a deterministic allowlisted GTFS

**Files:**
- Create: `scripts/test_prepare_hakusan_otp.py`
- Create: `scripts/prepare_hakusan_otp.py`

- [ ] **Step 1: Write source-hash and route-filter tests**

Build a complete synthetic 12-file GTFS containing one allowed and one excluded
route. Tests must assert source SHA enforcement and exact dependent-table
filtering:

```python
class PilotGtfsTests(unittest.TestCase):
    def test_source_sha_must_match(self) -> None:
        with self.assertRaisesRegex(PreparationError, "source GTFS sha256 mismatch"):
            prepare_pilot_gtfs(self.contract_root, self.source_zip, self.output_zip, "0" * 64)

    def test_excluded_route_and_dependencies_are_removed(self) -> None:
        summary = prepare_pilot_gtfs(
            self.contract_root,
            self.source_zip,
            self.output_zip,
            sha256_file(self.source_zip),
        )
        self.assertEqual(summary["route_ids"], ["allowed-route"])
        self.assertEqual(summary["trip_ids"], ["allowed-trip"])
        self.assertEqual(summary["shape_ids"], ["allowed-shape"])
        self.assertNotIn("excluded-stop", summary["stop_ids"])
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest scripts/test_prepare_hakusan_otp.py`

Expected: import failure because `scripts.prepare_hakusan_otp` does not exist.

- [ ] **Step 3: Implement filtering and referential validation**

Expose:

```python
class PreparationError(ValueError):
    pass

def sha256_file(path: Path) -> str:
    """Return lowercase SHA-256 hex for a file."""

def prepare_pilot_gtfs(
    contract_root: Path,
    source_zip: Path,
    output_zip: Path,
    expected_source_sha256: str,
) -> dict[str, object]:
    """Create the deterministic allowlisted ZIP and return count/id evidence."""

def inspect_pilot_gtfs(contract_root: Path, pilot_zip: Path) -> list[str]:
    """Return every policy or foreign-key error in an existing pilot ZIP."""
```

Apply the exact table rules from the approved design. Write every required file
with UTF-8, LF, source column order, source row order, ZIP entry order from the
Gate 0 manifest, `ZIP_DEFLATED`, and timestamp `(1980, 1, 1, 0, 0, 0)`.

- [ ] **Step 4: Add determinism, destination, and failure tests**

Add independent tests proving:

```python
def test_output_is_byte_identical_across_runs(self) -> None:
    prepare_pilot_gtfs(self.contract_root, self.source_zip, self.first_zip, self.source_sha)
    prepare_pilot_gtfs(self.contract_root, self.source_zip, self.second_zip, self.source_sha)
    self.assertEqual(self.first_zip.read_bytes(), self.second_zip.read_bytes())

def test_destination_access_stops_are_preserved(self) -> None:
    summary = prepare_pilot_gtfs(self.contract_root, self.source_zip, self.output_zip, self.source_sha)
    self.assertTrue(set(self.access_stop_ids).issubset(summary["stop_ids"]))

def test_unclassified_route_fails_closed(self) -> None:
    self._append_route("new-route")
    with self.assertRaisesRegex(PreparationError, "unclassified route: new-route"):
        prepare_pilot_gtfs(self.contract_root, self.source_zip, self.output_zip, self.source_sha)
```

Also cover missing allowlisted routes, broken trip/stop/shape/service/fare
references, parent-station recursion, and filtered route/stop/trip translations.

- [ ] **Step 5: Run Task 2 tests and verify GREEN**

Run: `python3 -m unittest scripts/test_prepare_hakusan_otp.py`

Expected: all GTFS preparation tests pass.

- [ ] **Step 6: Commit Task 2**

```bash
git add scripts/test_prepare_hakusan_otp.py scripts/prepare_hakusan_otp.py
git diff --cached --check
git commit -m "feat: derive allowlisted Hakusan GTFS"
```

### Task 3: Pin and validate OTP, OSM, and configuration sources

**Files:**
- Create: `config/otp/hakusan/osm-overpass.ql`
- Create: `config/otp/hakusan/osmium-requirements.txt`
- Create: `config/otp/hakusan/build-config.json`
- Create: `config/otp/hakusan/router-config.json`
- Create: `data/hakusan/otp-sources.json`
- Create: `scripts/test_prepare_hakusan_osm_pbf.py`
- Create: `scripts/prepare_hakusan_osm_pbf.py`
- Create: `scripts/test_hakusan_otp_contract.py`
- Create: `scripts/validate_hakusan_otp_contract.py`

- [ ] **Step 1: Write failing contract tests**

Test immutable OTP identity, Java version, config hashes, historical OSM query,
license, expected counts, scenario dates, and SHA formats:

```python
class OtpContractTests(unittest.TestCase):
    def test_committed_contract_is_valid(self) -> None:
        self.assertEqual(validate_otp_contract(ROOT), [])

    def test_latest_otp_url_is_rejected(self) -> None:
        payload = self._sources()
        payload["otp"]["artifact_url"] = "https://example.test/latest.jar"
        self._write_sources(payload)
        self.assertIn("OTP artifact URL must pin v2.9.0", validate_otp_contract(self.root))

    def test_config_hash_drift_is_rejected(self) -> None:
        (self.root / "config/otp/hakusan/build-config.json").write_text("{}")
        self.assertIn("OTP build-config sha256 mismatch", validate_otp_contract(self.root))
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest scripts/test_hakusan_otp_contract.py`

Expected: import failure because the contract validator does not exist.

- [ ] **Step 3: Add the three tracked configurations**

`osm-overpass.ql` must contain exactly the approved historical date and bbox,
and select highway ways plus restriction relations and their members.

`build-config.json` must contain only:

```json
{
  "configVersion": "hakusan-gate1-v1",
  "dataImportReport": true,
  "transitServiceStart": "2026-03-16",
  "transitServiceEnd": "2027-03-15"
}
```

`router-config.json` must contain only:

```json
{
  "configVersion": "hakusan-gate1-v1"
}
```

- [ ] **Step 4: Canonicalize the real historical OSM snapshot**

Run:

```bash
python3 scripts/prepare_hakusan_osm.py \
  --input data/external/hakusan/otp/hakusan-20260903.osm \
  --output data/external/hakusan/otp/hakusan-20260903-canonical.osm \
  --south 36.44917 --west 136.4535465 \
  --north 36.58471 --east 136.6223390
shasum -a 256 data/external/hakusan/otp/hakusan-20260903-canonical.osm
```

Expected: canonicalization succeeds and prints a lowercase 64-character
SHA-256. Record that exact value in `otp-sources.json`.

- [ ] **Step 4a: Convert the canonical XML to the pinned OTP PBF**

Create an ignored virtual environment, install Pyosmium 4.3.1 using
`--no-deps --require-hashes` and `config/otp/hakusan/osmium-requirements.txt`,
then run `scripts/prepare_hakusan_osm_pbf.py`. Tests must prove source hash,
converter version, output filename, output size/hash, atomic replacement, and
valid-cache reuse. Record the exact PBF hash and size in `otp-sources.json`.

- [ ] **Step 5: Add the source contract and validator**

The manifest must pin:

- OTP URL `https://github.com/opentripplanner/OpenTripPlanner/releases/download/v2.9.0/otp-shaded-2.9.0.jar`;
- OTP SHA-256 `112824122cd1a89e2dff6b5b3088ffbd4f04c3c0a400ca9f08f17b762f5325f6`;
- OTP size `183261367` bytes and Java major `25`;
- Overpass endpoint, query path/hash, historical timestamp, bbox, canonical XML
  filename/hash, derived PBF filename/hash/size, converter lock, and ODbL URL;
- source GTFS UID/hash and expected pilot counts `11`, `115`, `2867`, `205`;
- GraphQL endpoint path `/otp/gtfs/v1`, local port `18081`, service date
  `2026-09-08`, outbound time `06:50:00+09:00`, return time
  `11:00:00+09:00`, residential origin coordinates, and hospital destination ID.

Expose:

```python
def validate_otp_contract(repo_root: Path) -> list[str]:
    """Return all committed source/config contract errors."""
```

- [ ] **Step 6: Run contract tests and verify GREEN**

Run: `python3 -m unittest scripts/test_hakusan_otp_contract.py`

Expected: all contract tests pass.

- [ ] **Step 7: Commit Task 3**

```bash
git add config/otp/hakusan data/hakusan/otp-sources.json \
  scripts/test_hakusan_otp_contract.py scripts/validate_hakusan_otp_contract.py
git diff --cached --check
git commit -m "feat: pin Hakusan OTP build sources"
```

### Task 4: Add fail-closed artifact acquisition

**Files:**
- Create: `scripts/test_fetch_hakusan_otp_inputs.py`
- Create: `scripts/fetch_hakusan_otp_inputs.py`

- [ ] **Step 1: Write failing download tests**

Use fake HTTP responses and assert immutable URL validation, redirect-host
validation, atomic writes, checksum mismatch cleanup, and cached-file reuse:

```python
class FetchInputsTests(unittest.TestCase):
    def test_checksum_mismatch_does_not_replace_destination(self) -> None:
        destination = self.root / "otp.jar"
        destination.write_bytes(b"trusted")
        with self.assertRaisesRegex(FetchError, "sha256 mismatch"):
            download_checked(SOURCE, destination, "0" * 64, opener=self._opener(b"bad"))
        self.assertEqual(destination.read_bytes(), b"trusted")

    def test_unexpected_redirect_host_is_rejected(self) -> None:
        response = self._response(b"asset", final_url="https://attacker.example/otp.jar")
        with self.assertRaisesRegex(FetchError, "unexpected redirect host"):
            download_checked(SOURCE, self.root / "otp.jar", sha256_bytes(b"asset"), opener=lambda _: response)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest scripts/test_fetch_hakusan_otp_inputs.py`

Expected: import failure because the fetcher does not exist.

- [ ] **Step 3: Implement checked JAR and OSM acquisition**

Expose:

```python
class FetchError(RuntimeError):
    pass

def download_checked(source: ArtifactSource, destination: Path, opener=urlopen) -> Path:
    """Download to a temporary sibling, validate final host/size/hash, then replace."""

def fetch_overpass_snapshot(source: OsmSource, query: bytes, raw_destination: Path) -> Path:
    """POST the tracked query with timeouts and write only an ignored raw response."""
```

The CLI accepts `--repo-root`, `--output-dir`, and `--artifact otp|osm|all`.
OTP redirects are limited to `github.com` and proper
`.githubusercontent.com` hosts. OSM redirects are limited to
`overpass-api.de`. For OSM, the CLI fetches the raw response, invokes
`canonicalize_osm`, validates the canonical SHA from `otp-sources.json`, and
deletes the newly fetched raw file on validation failure. Existing canonical
files are reused only after validation.

- [ ] **Step 4: Run fetcher tests and verify GREEN**

Run: `python3 -m unittest scripts/test_fetch_hakusan_otp_inputs.py`

Expected: all acquisition tests pass without network access.

- [ ] **Step 5: Commit Task 4**

```bash
git add scripts/test_fetch_hakusan_otp_inputs.py scripts/fetch_hakusan_otp_inputs.py
git diff --cached --check
git commit -m "feat: acquire pinned Hakusan OTP inputs"
```

### Task 5: Validate GraphQL evidence and orchestrate the bounded OTP process

**Files:**
- Create: `scripts/test_run_hakusan_otp_evidence.py`
- Create: `scripts/run_hakusan_otp_evidence.py`

- [ ] **Step 1: Write failing pure validation tests**

Use captured payload-shaped fixtures for route inventory, stops, and
`planConnection` itineraries:

```python
class EvidenceValidationTests(unittest.TestCase):
    def test_route_inventory_must_equal_allowlist(self) -> None:
        errors = validate_route_inventory({"data": {"routes": [{"gtfsId": "F:allowed"}]}}, {"allowed", "other"})
        self.assertIn("OTP route inventory missing: other", errors)

    def test_plan_requires_walk_and_allowed_bus(self) -> None:
        result = validate_plan_response(self._plan(["WALK", "BUS"], route_id="F:allowed"), {"allowed"})
        self.assertEqual(result.errors, [])

    def test_excluded_bus_route_fails(self) -> None:
        result = validate_plan_response(self._plan(["WALK", "BUS"], route_id="F:excluded"), {"allowed"})
        self.assertIn("OTP itinerary uses non-allowlisted route: excluded", result.errors)
```

Also test GraphQL errors, routing errors, no itinerary, no WALK, no BUS,
missing route IDs, stop inventory gaps, Java major mismatch, config-warning log
scan, and sanitized relative-path evidence.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest scripts/test_run_hakusan_otp_evidence.py`

Expected: import failure because the evidence runner does not exist.

- [ ] **Step 3: Implement query and validation helpers**

Expose the `PlanEvidence` dataclass, the exact `normalize_gtfs_id` helper below,
and these stable typed functions: `validate_route_inventory(payload: object,
allowed_route_ids: set[str]) -> list[str]`, `validate_stop_inventory(payload:
object, access_stop_ids: set[str]) -> list[str]`,
`validate_plan_response(payload: object, allowed_route_ids: set[str]) ->
PlanEvidence`, `parse_java_major(version_output: str) -> int`, and
`scan_otp_log(text: str) -> list[str]`.

```python
@dataclass(frozen=True)
class PlanEvidence:
    errors: list[str]
    modes: list[str]
    route_ids: list[str]
    duration_seconds: int | None

def normalize_gtfs_id(value: str) -> str:
    return value.split(":", 1)[-1]
```

Use the non-deprecated `planConnection` query with `transitOnly: true`, WALK
access/egress/transfer, and BUS transit. Inventory queries request only
`gtfsId` and route names or stop names.

- [ ] **Step 4: Implement bounded orchestration**

The CLI accepts explicit `--gtfs-zip`, `--osm-source`, `--osm`, `--otp-jar`,
`--work-dir`, `--summary-output`, `--port`, `--startup-timeout`, and
`--build-timeout`.

Implementation order:

```text
validate committed contract plus canonical XML, PBF, GTFS, JAR, and config hashes
prepare and inspect pilot GTFS
copy only pilot GTFS, verified OSM PBF, build-config, router-config into work-dir
java -Xmx2g -jar OTP_JAR --build --save WORK_DIR
java -Xmx2g -jar OTP_JAR --load --serve WORK_DIR
poll POST http://127.0.0.1:PORT/otp/gtfs/v1
validate routes, stops, outbound plan, return plan
write sanitized JSON summary atomically
terminate then kill-on-timeout in finally
```

No success summary is written until the Java process is confirmed stopped and
all validations pass.

- [ ] **Step 5: Run evidence-runner tests and verify GREEN**

Run: `python3 -m unittest scripts/test_run_hakusan_otp_evidence.py`

Expected: all validation and orchestration-helper tests pass.

- [ ] **Step 6: Commit Task 5**

```bash
git add scripts/test_run_hakusan_otp_evidence.py scripts/run_hakusan_otp_evidence.py
git diff --cached --check
git commit -m "feat: verify Hakusan OTP graph evidence"
```

### Task 6: Integrate offline gates and truthful documentation

**Files:**
- Create: `scripts/test_hakusan_otp_docs.sh`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `docs/data-policy.md`
- Modify: `docs/technical-notes.md`
- Modify: `docs/open-data-challenge-2026-fit.md`

- [ ] **Step 1: Write and run the failing documentation gate**

Require these exact markers:

```text
hakusan-otp-test
hakusan-otp-fetch
hakusan-otp-evidence
OpenTripPlanner 2.9.0
Java 25
11 fixed routes
ROUTING_PROVIDER=mock
not realtime
```

Run: `bash scripts/test_hakusan_otp_docs.sh`

Expected: failure until Make targets and documentation are present.

- [ ] **Step 2: Add Make targets**

Add `hakusan-otp-test` to the normal `test` dependency chain. It runs all six
new Python test modules, committed contract validation, and the documentation
gate. Add explicit `hakusan-otp-fetch` and `hakusan-otp-evidence` targets with
operator-overridable artifact paths; neither runs in `make test`.

- [ ] **Step 3: Document exact operator workflow and boundaries**

Document acquisition, canonicalization, pilot-feed preparation, evidence
execution, attribution, static-timetable limitations, ignored artifacts,
2 GiB/timeout guards, and that Gate 1 leaves the backend on mock routing.

- [ ] **Step 4: Run documentation and offline Gate 1 tests**

Run:

```bash
bash scripts/test_hakusan_otp_docs.sh
make hakusan-otp-test
```

Expected: both commands pass with no network or Java process.

- [ ] **Step 5: Commit Task 6**

```bash
git add Makefile README.md docs/data-policy.md docs/technical-notes.md \
  docs/open-data-challenge-2026-fit.md scripts/test_hakusan_otp_docs.sh
git diff --cached --check
git commit -m "docs: add Hakusan OTP Gate 1 workflow"
```

### Task 7: Produce real OTP graph and query evidence

**Files:**
- Create: `data/hakusan/otp-validation-summary.json`
- Modify only if evidence finds a factual mismatch: `data/hakusan/otp-sources.json`

- [ ] **Step 1: Acquire and verify the pinned OTP and OSM inputs**

Run:

```bash
make hakusan-otp-fetch
```

Expected: file size `183261367` and SHA-256
`112824122cd1a89e2dff6b5b3088ffbd4f04c3c0a400ca9f08f17b762f5325f6`
for the JAR, plus canonical XML and derived PBF inputs matching their committed
hashes. The converter environment and all artifacts remain ignored.

- [ ] **Step 2: Verify real source inputs**

Run:

```bash
python3 scripts/validate_hakusan_data.py --require-evidence \
  --gtfs-zip /private/tmp/hakusan-meguru-gtfs.zip \
  --validator-report /private/tmp/hakusan-meguru-validator-jp/report.json
python3 scripts/validate_hakusan_otp_contract.py
```

Expected: Gate 0 evidence and Gate 1 source contract both pass.

- [ ] **Step 3: Build, start, query, and stop real OTP**

Run:

```bash
make hakusan-otp-evidence \
  HAKUSAN_GTFS_ZIP=/private/tmp/hakusan-meguru-gtfs.zip \
  HAKUSAN_OTP_OSM=data/external/hakusan/otp/hakusan-20260903-canonical.osm.pbf \
  HAKUSAN_OTP_JAR=data/external/hakusan/otp/otp-shaded-2.9.0.jar \
  HAKUSAN_OTP_SUMMARY=data/hakusan/otp-validation-summary.json
```

Expected: graph build succeeds, exactly 11 routes and six access stops are
observed, outbound and return plans each contain WALK and BUS, all route IDs are
allowlisted, the OTP process is stopped, and the sanitized summary is written.

- [ ] **Step 4: Inspect evidence and ignored-artifact boundary**

Run:

```bash
python3 -m json.tool data/hakusan/otp-validation-summary.json
git status --short --untracked-files=all
git check-ignore -v data/external/hakusan/otp/otp-shaded-2.9.0.jar
git check-ignore -v data/external/hakusan/otp/graph.obj
```

Expected: only the small JSON summary is trackable; all raw/build artifacts are
ignored and the summary contains no absolute local path.

- [ ] **Step 5: Commit Task 7**

```bash
git add data/hakusan/otp-validation-summary.json
git diff --cached --check
git commit -m "test: record Hakusan OTP Gate 1 evidence"
```

### Task 8: Final verification and branch handoff

**Files:**
- Modify: `docs/superpowers/plans/2026-09-05-hakusan-otp-gate1.md` (checkboxes and execution evidence only)

- [ ] **Step 1: Run all focused and repository gates fresh**

Run:

```bash
make hakusan-data-evidence \
  HAKUSAN_GTFS_ZIP=/private/tmp/hakusan-meguru-gtfs.zip \
  HAKUSAN_VALIDATOR_REPORT=/private/tmp/hakusan-meguru-validator-jp/report.json
make hakusan-otp-test
make test
git diff --check
```

Expected: every command exits zero; existing Starlette/httpx and MapLibre chunk
warnings may remain documented but no Gate 1 failure is allowed.

- [ ] **Step 2: Review scope and provenance**

Run:

```bash
git status --short --branch
git diff main...HEAD --stat
git diff main...HEAD --name-only
git log --oneline --decorate main..HEAD
```

Confirm no backend/frontend/runtime/cloud file changed, no raw artifact is
tracked, and every implementation commit belongs to Gate 1.

- [ ] **Step 3: Record execution evidence and commit the plan closeout**

Update this plan with exact test counts, graph/query evidence, warnings, and
remaining Gate 2 boundary, then run:

```bash
git add docs/superpowers/plans/2026-09-05-hakusan-otp-gate1.md
git diff --cached --check
git commit -m "docs: close Hakusan OTP Gate 1 plan"
```

- [ ] **Step 4: Use the finishing workflow**

Invoke `finishing-a-development-branch`, re-run its required verification, and
present the local merge, PR, keep, or discard choices. Do not push or deploy
without a new explicit user choice.
