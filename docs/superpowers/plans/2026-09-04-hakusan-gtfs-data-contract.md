# Hakusan GTFS Data Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a reproducible, license-auditable, fail-closed data contract for the pinned Hakusan City community bus "Meguru" GTFS feed before any production OTP integration.

**Architecture:** Commit metadata and policy, not the raw GTFS archive. A Python-standard-library validator checks the committed manifest, destination catalog, pilot-route allowlist, raw archive identity and structure, and MobilityData validator evidence. The normal test gate validates committed contracts without network access; an explicit evidence command additionally validates a locally downloaded pinned archive and validator report.

**Tech Stack:** JSON, Python 3.12 standard library, `unittest`, MobilityData GTFS Validator 8.0.1, Make.

---

### Task 1: Specify the contract behavior with failing tests

**Files:**
- Create: `scripts/test_validate_hakusan_data.py`
- Test: `scripts/test_validate_hakusan_data.py`

- [x] **Step 1: Write the failing tests**

Create tests that express these independent requirements:

```python
class ContractTests(unittest.TestCase):
    def test_committed_contract_is_valid(self) -> None:
        self.assertEqual(validate_contract(ROOT / "data/hakusan"), [])

    def test_manifest_requires_pinned_uid_and_sha256(self) -> None:
        manifest_path = self.contract_root / "manifest.json"
        manifest = _load_json(manifest_path)
        manifest["feed"]["artifact"]["uid"] = "current"
        manifest["feed"]["artifact"]["sha256"] = "mutable"
        _write_json(manifest_path, manifest)
        errors = validate_contract(self.contract_root)
        self.assertIn("manifest feed.artifact.uid must be a UUID", errors)

    def test_every_supported_destination_has_auditable_source(self) -> None:
        payload = _load_json(self.contract_root / "destinations.json")
        pharmacy = next(item for item in payload["destinations"] if item["category"] == "pharmacy")
        del pharmacy["source"]["element_id"]
        _write_json(self.contract_root / "destinations.json", payload)
        errors = validate_contract(self.contract_root)
        self.assertIn("destination pharmacy-kusuri-aoki-nunoichi OSM source requires integer element_id", errors)

    def test_non_pilot_routes_are_denied_by_default(self) -> None:
        payload = _load_json(self.contract_root / "route-rules.json")
        payload["default_policy"] = "allow"
        _write_json(self.contract_root / "route-rules.json", payload)
        self.assertIn("route-rules default_policy must be 'deny'", validate_contract(self.contract_root))
```

Add archive and report tests using temporary files:

```python
class EvidenceTests(unittest.TestCase):
    def test_archive_must_match_sha_and_required_gtfs_files(self) -> None:
        archive_path = self.root / "feed.zip"
        archive_path.write_bytes(b"not the pinned archive")
        self.assertIn(
            "GTFS archive sha256 does not match manifest",
            verify_gtfs_archive(self.contract_root, archive_path),
        )

    def test_validator_report_rejects_any_error_notice(self) -> None:
        report = {"summary": {"validatorVersion": "8.0.1"}, "notices": [
            {"severity": "ERROR", "code": "missing_required_file", "totalNotices": 1}
        ]}
        self.assertIn("validator report contains 1 ERROR notices", errors)
```

- [x] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m unittest scripts/test_validate_hakusan_data.py
```

Expected: FAIL because `scripts.validate_hakusan_data` and the committed contracts do not exist.

### Task 2: Add the pinned feed, destination, route, and validation contracts

**Files:**
- Create: `data/hakusan/manifest.json`
- Create: `data/hakusan/destinations.json`
- Create: `data/hakusan/route-rules.json`
- Create: `data/hakusan/validation-summary.json`
- Create: `scripts/validate_hakusan_data.py`
- Modify: `scripts/test_validate_hakusan_data.py`

- [x] **Step 1: Add immutable source identity**

Record the exact GTFS Data Repository organization/feed IDs, current artifact UID, UID-specific download URL, CC BY 4.0 license URL, service dates, publisher, feed version, SHA-256, and static-only status. The archive hash must be:

```text
ea1a0108c4a7f24215aa1b3811a267d85abf9777a356b8c7b3ff857edbcae740
```

- [x] **Step 2: Add the six-category destination catalog**

Use five GTFS stop records and one OSM pharmacy record:

```json
{
  "id": "pharmacy-kusuri-aoki-nunoichi",
  "category": "pharmacy",
  "name_ja": "クスリのアオキ 布市店",
  "location": {"lat": 36.5236, "lon": 136.5716559},
  "access_stop_ids": ["136_01"],
    "source": {
      "type": "openstreetmap",
      "element_type": "way",
      "element_id": 604481354,
      "element_version": 1,
      "element_timestamp": "2018-07-03T06:38:44Z",
      "license": "ODbL-1.0",
    "snapshot_at": "2026-09-04T14:16:21Z"
  }
}
```

The other entries use the pinned GTFS stop IDs for supermarket (`15_01`), hospital (`24_01`), city hall (`23_01`), station (`17_01`), and social support (`69_01`).

- [x] **Step 3: Add a deny-by-default pilot route policy**

Allow only fixed-route Matsuto/Mikawa route IDs. Explicitly identify the official reservation-required route names and make all routes outside the pilot unavailable to automated diagnosis. No route may become eligible merely because a future feed adds it.

- [x] **Step 4: Implement the validator**

Expose exactly three public validation functions: `validate_contract(Path) ->
list[str]`, `verify_gtfs_archive(Path, Path) -> list[str]`, and
`verify_validator_report(Path, Path) -> list[str]`. Each returns every detected
error and returns an empty list only for accepted input.

The CLI accepts:

```text
--contract-root PATH
--gtfs-zip PATH
--validator-report PATH
--require-evidence
```

It exits `0` only when all requested checks pass, prints one error per line to stderr otherwise, and never downloads data.

- [x] **Step 5: Run the tests and verify GREEN**

Run:

```bash
python3 -m unittest scripts/test_validate_hakusan_data.py
```

Expected: all contract/evidence tests PASS.

### Task 3: Make contract validation part of the repository gate

**Files:**
- Create: `scripts/test_hakusan_docs.sh`
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `docs/data-policy.md`
- Modify: `docs/open-data-challenge-2026-fit.md`
- Modify: `docs/technical-notes.md`

- [x] **Step 1: Write and run the failing documentation gate**

The shell test must require:

```text
hakusan-data-test
hakusan-data-evidence
765cd548-a1f3-46e6-b05b-d6168b9b85d1
CC BY 4.0
予約が必要
static timetable
```

Run:

```bash
bash scripts/test_hakusan_docs.sh
```

Expected: FAIL until Make targets and truthful documentation are present.

- [x] **Step 2: Add Make targets**

Add an offline target to the normal test chain:

```make
hakusan-data-test:
	python3 -m unittest scripts/test_validate_hakusan_data.py
	python3 scripts/validate_hakusan_data.py
	bash scripts/test_hakusan_docs.sh
```

Add an explicit local-evidence target using operator-supplied paths:

```make
hakusan-data-evidence:
	python3 scripts/validate_hakusan_data.py --require-evidence \
		--gtfs-zip "$(HAKUSAN_GTFS_ZIP)" \
		--validator-report "$(HAKUSAN_VALIDATOR_REPORT)"
```

- [x] **Step 3: Update documentation without overstating readiness**

State that Hakusan is selected and pinned, but production still uses fixture/mock routing until later gates are implemented. Document CC BY and ODbL attribution, static-only timing, reservation-route exclusion, exact evidence commands, and the fact that raw archives remain untracked.

- [x] **Step 4: Verify the documentation gate passes**

Run:

```bash
bash scripts/test_hakusan_docs.sh
```

Expected: PASS.

### Task 4: Reproduce the data evidence and close Gate 0

**Files:**
- Review only: all files changed above

- [x] **Step 1: Verify the pinned archive and validator report**

Run:

```bash
make hakusan-data-evidence \
  HAKUSAN_GTFS_ZIP=/private/tmp/hakusan-meguru-gtfs.zip \
  HAKUSAN_VALIDATOR_REPORT=/private/tmp/hakusan-meguru-validator-jp/report.json
```

Expected: contract, SHA-256, required files, route/stop references, service dates, and validator evidence all PASS with zero ERROR notices.

- [x] **Step 2: Run full verification**

Run:

```bash
make test
git diff --check
git status --short --branch
```

Expected: existing backend/frontend gates and the new offline data-contract gate pass; no whitespace errors; only scoped Gate 0 files are modified.

- [x] **Step 3: Review scope boundaries**

Confirm that no raw GTFS ZIP, validator JAR/report, OTP graph, backend routing behavior, frontend request behavior, Cloud Build deployment, or production service has changed.

Commit creation was intentionally deferred until the user selected local
integration option 1.

## Execution Evidence — 2026-09-04

- Initial contract test run failed with `ModuleNotFoundError` before the
  validator existed.
- The source/license URL regression tests failed before HTTPS and ODbL URL
  enforcement was added.
- Final contract suite: 11 tests passed, including proof that every destination
  has an access stop served by an allowed pilot route.
- Pinned archive plus MobilityData report: `Hakusan GTFS evidence: PASS`.
- Full repository gate: 19 backend tests and 32 frontend tests passed; Ruff,
  TypeScript/Vite build, and ESLint exited zero.
- Known baseline warnings remain: one Starlette/httpx deprecation warning and
  the existing MapLibre chunk-size warning.
- No raw GTFS archive, validator report/JAR, OSM extract, OTP graph, runtime
  routing code, frontend request code, or deployment configuration was added or
  changed.
