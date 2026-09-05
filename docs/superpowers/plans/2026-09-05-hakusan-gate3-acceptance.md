# Gate 3 local acceptance — 2026-09-05

Historical Gate 3 checkpoint. Its rehearsal restrictions and uncommitted status are superseded by `2026-09-05-hakusan-gate4-acceptance.md`; retain this record as evidence of the original safety gate.

## Result
PASS for the scoped mobile diagnosis pilot. Not deployed, pushed, submitted or field-validated. Based on Gate 2 commit `234e2a4`; implementation is on `codex/hakusan-frontend-gate3`.

The first-principles review kept real-data claims narrower than product navigation: the old rehearsal generator hardcodes 10:00 departure. Hakusan rehearsal/daily/family-report routes now display an explicit unsupported notice instead of invoking that generator. Default demo behavior remains available. Implementing date-aware rehearsal is the next stage, not completed by this gate.

## Verified
- Frontend: 41 tests; lint and TypeScript/Vite build pass, including an opt-in Hakusan build.
- Backend and scripts: 111 tests plus 6 subtests pass. Focused Ruff check passes.
- Date guards: missing, reversed and outside GTFS service period rejected. Explicit `+09:00` serialization tested. Stale async responses cannot overwrite edited inputs.
- Mock configuration or missing OTP endpoint: pilot fixture/request rejected with 503. Pilot request containing mock journeys is rejected. A configured but unavailable OTP endpoint returns all six results as `unknown` with `data_source=routing_provider`, never mock success.
- Mobile Chromium viewport: 390 × 844. Real frontend → HTTP FastAPI → OTP 2.9 graph (no API interception).
- Public origin: 36.52725, 136.5605. Outbound `2026-09-08T06:50:00+09:00`; return `2026-09-08T11:00:00+09:00`. All six destination coordinates came from the backend contract; mock journeys were `{}`.
- `/fixtures/hakusan` and `/diagnosis/run` returned HTTP 200. Result `data_source=routing_provider`, score 55, data confidence 0.49. Five `caution`, supermarket `support_needed`; no `unknown`.
- Six result cards rendered. Document scrollWidth 390 equals viewport width 390. Supermarket disclosure shows outbound walking 25 min vs requested 15, return walking 13 min, and unverified access conditions.
- Attribution, static timetable, public-origin and entrance/accessibility caveats visible. No pilot rehearsal generation exposed. Missing-date deep links redirect to setup.

## Findings and limitations
- Initial browser request failed because checked-in runtime config overrode Vite's API URL with localhost:8000. Runtime config now defaults to empty, preserving explicit deployment overrides and otherwise using environment/local defaults. Regression test added.
- Initial favicon 404 remains cosmetic; no unrelated asset redesign performed.
- Existing MapLibre >500 kB bundle warning and Starlette/httpx deprecation remain. They did not fail checks.
- Snapshot data is not live service information. Stops may proxy destinations; entrances, stairs, opening hours and actual usability require field verification.
- No geocoding, arbitrary-home diagnosis, realtime service or date-aware rehearsal is claimed. Dates are held in memory; a reload requires setup again.
- Local pilot needs the repository data contracts and the Gate 1 graph; this does not validate deployment packaging.

## Reproduce locally
Run these in separate terminals from the repository root (dependencies and ignored Gate 1 data must already exist):

```sh
java -Xmx2048m -jar data/external/hakusan/otp/otp-shaded-2.9.0.jar --abortOnUnknownConfig --load --serve --bindAddress 127.0.0.1 --port 18081 data/external/hakusan/otp/evidence-runs/run-10u4k233
```

```sh
ROUTING_PROVIDER=otp OTP_GRAPHQL_URL=http://127.0.0.1:18081/otp/gtfs/v1 CORS_ORIGINS=http://127.0.0.1:15173 backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18000
```

```sh
VITE_DATA_PROFILE=hakusan VITE_API_BASE_URL=http://127.0.0.1:18000 npm --prefix frontend run dev -- --host 127.0.0.1 --port 15173 --strictPort
```

Open `http://127.0.0.1:15173/onboarding`; retain all six destinations, walk 15 min, transfers 1, enter the dates above, diagnose and expand the supermarket's round-trip detail.

Local browser screenshots: `output/playwright/hakusan-gate3-result-final.png` and `output/playwright/hakusan-gate3-dates-final.png`. Browser logs/screenshots are ignored local artifacts, not production assets.

Git closeout: implementation diff reviewed; `git diff --check` passed. Changes remain uncommitted on the stage branch (15 modified tracked files and 7 new source/test/document files); no merge/push. Validation servers were stopped after acceptance.

Verification commands:

```sh
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts -q
npm --prefix frontend test
npm --prefix frontend run lint
VITE_DATA_PROFILE=hakusan npm --prefix frontend run build
git diff --check
git status --short --branch
```
