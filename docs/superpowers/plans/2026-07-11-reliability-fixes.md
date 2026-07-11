# Carless Life Rehearsal Reliability Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing fixture-based elderly flow honest and reliable when selections are empty, data is synthetic, requests overlap, or the backend is unavailable.

**Architecture:** Keep the current React context and FastAPI domain boundaries. Add validation and in-flight request deduplication at the shared state boundary, propagate fixture provenance through the diagnosis model, make MapLibre initialization cancellable, and render one reusable retry state in each affected frontend flow.

**Tech Stack:** React 19, TypeScript, Vitest, Testing Library, FastAPI, Pydantic, pytest, MapLibre GL.

---

### Task 1: Reject empty destination selections

**Files:**
- Modify: `frontend/src/test/App.flow.test.tsx`
- Modify: `frontend/src/state/AppState.tsx`
- Modify: `frontend/src/pages/OnboardingPage.tsx`

- [ ] **Step 1: Write the failing test**

Add a flow test that opens onboarding, deselects every destination, advances to the final step, and asserts that `診断する` is disabled and `少なくとも1つ選んでください。` is visible.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/test/App.flow.test.tsx -t "requires at least one destination"`

Expected: FAIL because the current wizard allows diagnosis and `selectedFixture` restores every fixture destination.

- [ ] **Step 3: Write minimal implementation**

Change `selectedFixture` to preserve an empty selection and change onboarding to render the validation message and disable diagnosis when `selectedDestinationIds.length === 0`.

- [ ] **Step 4: Run test to verify it passes**

Run the focused test again. Expected: PASS.

### Task 2: Make fixture provenance visible in diagnosis

**Files:**
- Modify: `backend/tests/test_diagnosis.py`
- Modify: `backend/app/domain/models.py`
- Modify: `backend/app/services/diagnosis/engine.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/DiagnosisPage.tsx`
- Modify: `frontend/src/pages/ResultPage.tsx`
- Modify: `frontend/src/test/App.flow.test.tsx`

- [ ] **Step 1: Write failing backend and frontend tests**

Assert that fixture-backed diagnosis includes a `fixture_data_only` warning, reports `data_source="fixture"`, and does not report high confidence. Assert that diagnosis UI renders `現在はデモデータによる判定です。`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_diagnosis.py -q`

Run: `cd frontend && npm test -- --run src/test/App.flow.test.tsx -t "shows fixture provenance"`

Expected: FAIL because provenance is currently absent.

- [ ] **Step 3: Write minimal implementation**

Add `data_source` to `LifeDiagnosis`, append a `fixture_data_only` warning when request fixture transport results are used, cap fixture confidence below the high-confidence range, and show the plain-language warning above result groups.

- [ ] **Step 4: Run focused tests**

Expected: backend and frontend focused tests PASS.

### Task 3: Deduplicate state requests and MapLibre initialization

**Files:**
- Modify: `frontend/src/test/App.flow.test.tsx`
- Modify: `frontend/src/state/AppState.tsx`
- Modify: `frontend/src/pages/MapPage.tsx`
- Modify: `frontend/src/components/MapLibreStatusMap.tsx`

- [ ] **Step 1: Write failing tests**

Render `/map` in `StrictMode` and assert each API endpoint is called once. Add a MapLibre lifecycle test that resolves the dynamic import after unmount and asserts that no map remains attached.

- [ ] **Step 2: Verify RED**

Run the new focused tests. Expected: FAIL with duplicate fetch counts or leaked map initialization.

- [ ] **Step 3: Write minimal implementation**

Store in-flight fixture, diagnosis, and rehearsal promises in refs so callers share one request. Make map initialization use a cancellation flag and remove an asynchronously created map immediately when the effect has already cleaned up. Load the map page through the single `ensureRehearsals()` dependency chain rather than three parallel chains.

- [ ] **Step 4: Verify GREEN**

Run the focused tests. Expected: PASS with one request chain and one live map.

### Task 4: Replace permanent loading with retryable error states

**Files:**
- Create: `frontend/src/components/AsyncErrorState.tsx`
- Modify: `frontend/src/pages/OnboardingPage.tsx`
- Modify: `frontend/src/pages/RehearsalPage.tsx`
- Modify: `frontend/src/pages/DailyPage.tsx`
- Modify: `frontend/src/pages/MapPage.tsx`
- Modify: `frontend/src/test/App.flow.test.tsx`

- [ ] **Step 1: Write failing tests**

Reject fixture and rehearsal fetches and assert the page shows `読み込みに失敗しました。` plus a unique `もう一度試す` button instead of permanent loading. Click retry and assert the real flow recovers when the next request succeeds.

- [ ] **Step 2: Verify RED**

Run the focused tests. Expected: FAIL because rejected promises currently remain unhandled or produce empty pages.

- [ ] **Step 3: Write minimal implementation**

Add a small accessible error component with `role="alert"` and a retry callback. Catch each affected page request, clear loading in `finally`, and reset the page error before retrying.

- [ ] **Step 4: Verify GREEN**

Run the focused tests. Expected: PASS with no unhandled rejection.

### Task 5: Full verification and visual regression pass

**Files:**
- Review only: all files changed above

- [ ] **Step 1: Run complete automated verification**

Run: `make test`

Expected: backend pytest, ruff, frontend Vitest, TypeScript/Vite build, and ESLint all exit 0. The existing Starlette/httpx deprecation and MapLibre chunk-size warnings may remain documented.

- [ ] **Step 2: Run repository hygiene checks**

Run: `git diff --check`

Run: `git status --short --branch`

Expected: no whitespace errors; only the pre-existing user changes plus this scoped plan/fix set are present.

- [ ] **Step 3: Run current-flow browser verification**

At 390×844, verify empty selection is blocked, fixture provenance is visible, backend loss offers retry, recovery succeeds, and `/map` contains exactly one canvas and seven markers.

- [ ] **Step 4: Capture accepted before/after screenshots**

Save the current accepted screenshots outside the repository unless the user explicitly asks to replace the existing untracked audit screenshot set.
