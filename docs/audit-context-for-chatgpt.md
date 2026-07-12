# Audit Context for ChatGPT

This audit was produced under a read-only code review scope: no business source files were changed, no files were staged, and no commit was created. The only intended new artifacts are this file and screenshots under `docs/audit-screenshots/`.

## 1. Repository Snapshot

- Current path: `/Users/zhanglonglong/Projects/apps/Carless Life Rehearsal`
- Git branch: `main`
- Initial `git status --short` before audit artifacts: clean output
- Latest commit: `b15d99ea9eeda9319ba5e72755c43ce3b6fb3c71 Implement carless life rehearsal app`
- Audit-generated files: `docs/audit-context-for-chatgpt.md`, `docs/audit-screenshots/*.png`

Project tree, max depth 4, excluding `node_modules`, `.venv`, `dist`, `build`, `__pycache__`, `.git`, `.pytest_cache`, and `.ruff_cache`:

```text
.
.gitignore
Makefile
README.md
backend
backend/Dockerfile
backend/README.md
backend/app
backend/app/__init__.py
backend/app/api
backend/app/api/__init__.py
backend/app/api/routes
backend/app/core
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/domain
backend/app/domain/__init__.py
backend/app/domain/models.py
backend/app/fixtures
backend/app/fixtures/__init__.py
backend/app/fixtures/demo.py
backend/app/main.py
backend/app/services
backend/app/services/__init__.py
backend/app/services/data_quality
backend/app/services/diagnosis
backend/app/services/rehearsal
backend/app/services/routing
backend/pyproject.toml
backend/tests
backend/tests/test_data_quality.py
backend/tests/test_diagnosis.py
backend/tests/test_health.py
backend/tests/test_models_and_fixtures.py
backend/tests/test_rehearsals.py
backend/tests/test_routing.py
backend/uv.lock
docker-compose.yml
docs
docs/architecture.md
docs/data-policy.md
docs/demo-script-ja.md
docs/demo-script-zh.md
docs/open-data-challenge-2026-fit.md
docs/product-blueprint.md
docs/submission-summary-ja.md
docs/technical-notes.md
frontend
frontend/Dockerfile
frontend/README.md
frontend/eslint.config.js
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/src
frontend/src/App.tsx
frontend/src/components
frontend/src/main.tsx
frontend/src/pages
frontend/src/services
frontend/src/state
frontend/src/styles.css
frontend/src/test
frontend/src/types
frontend/src/types.ts
frontend/src/utils
frontend/src/vite-env.d.ts
frontend/tsconfig.app.json
frontend/tsconfig.app.tsbuildinfo
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/tsconfig.node.tsbuildinfo
frontend/vite.config.d.ts
frontend/vite.config.js
frontend/vite.config.ts
```

## 2. Intended Product Goal Found in Docs

The documented goal is clear: `README.md` and `docs/product-blueprint.md` define `車なし生活リハーサル / Carless Life Rehearsal` as a product for reducing anxiety before and after voluntary driver's-license return. The product is not a generic route planner and must not decide whether the person should return their license.

Core target flow found in `docs/product-blueprint.md`, `docs/demo-script-ja.md`, and `docs/demo-script-zh.md`:

1. Before license return, family enters home and common destinations.
2. App diagnoses whether daily life without a car is feasible.
3. App generates up to three rehearsal tasks.
4. Elderly user can hear results by voice.
5. Family/municipality can review a map and report.
6. After return, elderly user can use a voice-first daily outing assistant.

Primary users from `docs/product-blueprint.md`:

- Elderly person considering or having completed license return.
- Family members helping configure and discuss destinations.
- Municipality/community staff reviewing local mobility gaps.

MVP scope from `docs/product-blueprint.md`:

- Fixture home/destination data.
- Deterministic mock router.
- Mobility profile inputs.
- LifeScore diagnosis.
- Japanese reasons.
- Rehearsal task generation.
- Voice reading and speech-command fallback.
- Family/admin map.
- Visible data quality warnings.

Non-goals from `README.md`, `docs/product-blueprint.md`, and `docs/open-data-challenge-2026-fit.md`:

- Not a generic route planner.
- Not a license-return promotion page.
- Not medical, care, legal, or safety-critical decision support.
- Not an LLM route generator.
- Not a demand-transit operation system.
- No raw ODPT/challenge data redistribution.

Run instructions are documented in `README.md`, `Makefile`, `docker-compose.yml`, `backend/Dockerfile`, and `frontend/Dockerfile`. The standard local URLs are frontend `http://localhost:5173` and backend `http://localhost:8000`. The Docker compose config sets `ROUTING_PROVIDER=mock`, `CORS_ORIGINS=http://localhost:5173`, and `VITE_API_BASE_URL=http://localhost:8000`.

Data source policy from `docs/data-policy.md`:

- Phase 1 uses synthetic fixture data and deterministic mock router.
- Future allowed sources include GTFS static, ODPT, OTP output derived from authorized feeds, demand transit metadata, and GTFS Validator JSON.
- Missing data must surface as `判定不能`, `unknown`, warning, or reduced confidence.

Contest fit from `docs/open-data-challenge-2026-fit.md` and `docs/submission-summary-ja.md`:

- The app translates public transportation data into the life question: can this person's everyday destinations still be reached without a car?
- Contest demo should work without production secrets or user-owned API keys.
- Evidence should include fixture demo, deterministic routing boundary, data quality warnings, elderly voice UI, family/admin map report, and technical notes.

## 3. Frontend Structure

Frontend stack:

- `frontend/package.json`: Vite, React 19, TypeScript, React Router, MapLibre GL, `react-speech-recognition`, lucide icons, Vitest, Testing Library, ESLint.
- `frontend/vite.config.ts`: React plugin and Vitest `jsdom` setup.
- `frontend/index.html`: Japanese document language and mobile viewport meta.
- `frontend/src/main.tsx`: `BrowserRouter` wraps `App`.
- `frontend/src/App.tsx`: route table.
- `frontend/src/state/AppState.tsx`: shared fixture, diagnosis, rehearsal state and API orchestration.
- `frontend/src/services/api.ts`: API base defaults to `http://localhost:8000`, override via `VITE_API_BASE_URL`.
- `frontend/src/styles.css`: plain CSS. No Tailwind config found.
- PWA: no service worker, manifest, or install handling found in `frontend/index.html`, `frontend/package.json`, or `frontend/src`.

Implemented routes from `frontend/src/App.tsx`:

| Route | File | Actual implementation |
|---|---|---|
| `/` | `frontend/src/pages/HomePage.tsx` | Elderly-first landing with two large actions: try carless life and daily destination voice mode. |
| `/onboarding` | `frontend/src/pages/OnboardingPage.tsx` | 4-step wizard: home address text, destination selection from fixture, walk minutes, transfer tolerance. No geocoding or custom destination creation. |
| `/diagnosis` | `frontend/src/pages/DiagnosisPage.tsx` | Auto-runs fixture-backed diagnosis, shows LifeScore, summary, result cards, voice buttons, and link to rehearsal. |
| `/result` | `frontend/src/pages/ResultPage.tsx` | Diagnosis result page with score band, result cards, diagnosis warnings if present, and rehearsal link. |
| `/rehearsal` | `frontend/src/pages/RehearsalPage.tsx` | Generates rehearsal task cards with `voice_script_ja` playback and Web Share/clipboard family text. |
| `/daily` | `frontend/src/pages/DailyPage.tsx` | Daily voice-first mode with microphone button, speech-recognition support check, fixed category buttons, and speech synthesis. |
| `/map` | `frontend/src/pages/MapPage.tsx` | Family/admin mode with MapLibre map and report grouping destinations by status. |
| `/data-quality` | `frontend/src/pages/DataQualityPage.tsx` | Calls `/data-quality` and displays level, feed summary, and warning messages. |

Voice-related code:

- `frontend/src/pages/DailyPage.tsx` uses `react-speech-recognition` and fixed Japanese keyword detection for supermarket, hospital, pharmacy, and city hall.
- `frontend/src/utils/speech.ts` uses `window.speechSynthesis` and `SpeechSynthesisUtterance` with `ja-JP`.
- `frontend/src/components/ResultCards.tsx` speaks Japanese reasons.
- `frontend/src/pages/RehearsalPage.tsx` speaks task `voice_script_ja`.

Map-related code:

- `frontend/src/components/MapLibreStatusMap.tsx` imports MapLibre dynamically and uses a local blank style, so no external map API key is needed.
- The component intends to add a home marker and status-colored destination markers.
- In actual screenshots, `desktop-map.png` and `mobile-map.png` show the family report with destination statuses, but the map canvas visibly shows only the home marker. This may be a render/timing issue or insufficient marker visibility, and should be treated as a map-mode gap.

Elderly-friendly frontend evidence:

- Large buttons and low input count exist in `frontend/src/styles.css`: `.large-button`, `.choice-button`, `.mic-button`, and `.icon-text-button` have `min-height: 76px`; `.mic-button` has `min-height: 112px`.
- The main flow is not map-first: `/`, `/onboarding`, `/diagnosis`, `/result`, `/rehearsal`, and `/daily` all work without opening `/map`.
- Japanese UI is broadly complete across page files and labels in `frontend/src/utils/labels.ts`.

Frontend gaps against the target prototype:

- Onboarding remains fixture-driven; it does not support real home geocoding, adding real common destinations, or editing all destination categories from scratch.
- Daily voice mode is command/category matching, not a robust outing assistant.
- The UI is mobile-responsive but still presented as centered card panels, so it feels partly like a web prototype rather than a native app shell.
- Map visualization is secondary as intended, but current visible map evidence is weak because destination markers/routes are not clearly shown.
- PWA/mobile app features are absent.

## 4. Backend Structure

Backend stack:

- `backend/pyproject.toml`: FastAPI, httpx, Pydantic, pydantic-settings, uvicorn; dev dependencies pytest, pytest-asyncio, ruff.
- `backend/app/main.py`: FastAPI app, CORS middleware, `/health`, and routers.
- `backend/app/core/config.py`: settings for app name, `ROUTING_PROVIDER`, `CORS_ORIGINS`, and `OTP_GRAPHQL_URL`.
- `backend/app/domain/models.py`: domain enums and Pydantic models.
- `backend/app/fixtures/demo.py`: synthetic fixture home, six destinations, time windows, and mock round-trip plans.
- `backend/app/services/diagnosis/engine.py`: deterministic diagnosis and LifeScore engine.
- `backend/app/services/rehearsal/engine.py`: deterministic rehearsal task generator.
- `backend/app/services/routing/mock.py`: fixture/mock routing provider.
- `backend/app/services/routing/otp.py`: OTP GraphQL adapter.
- `backend/app/services/data_quality/service.py`: GTFS presence and validator JSON warning support.
- `backend/tests/*.py`: backend unit and API tests.

Current API endpoints from `backend/app/main.py` and `backend/app/api/routes/*.py`:

- `GET /health`
- `GET /fixtures/demo`
- `POST /diagnosis/run`
- `POST /rehearsals/generate`
- `GET /rehearsals/{task_id}`
- `GET /data-quality`

Current domain model coverage in `backend/app/domain/models.py`:

- Destination categories exist: `supermarket`, `hospital`, `pharmacy`, `city_hall`, `station`, `social`.
- Status enum exists: `ok`, `caution`, `support_needed`, `unknown`.
- `FeasibilityResult` includes `reasons_ja`, outbound/return summaries, and warnings.
- `LifeDiagnosis` includes `life_score`, `summary_ja`, `item_results`, `data_confidence`, `data_quality_warnings`, and `next_recommended_action`.
- `RehearsalTask` includes `voice_script_ja` and `family_share_text_ja`.
- `DataQualityReport` and `DataQualityWarning` exist.

Diagnosis status:

- The diagnosis is real deterministic business logic, not a pure mock. `backend/app/services/diagnosis/engine.py` evaluates missing coordinates, missing transport plans, provider failure, missing return trips, walking time, transfers, wait time, fragile single-option routes, and stairs.
- The actual routing inputs are fixture/mock by default. `backend/app/fixtures/demo.py` supplies `mock_transport_results`; `backend/app/services/routing/provider.py` returns `MockRoutingProvider` unless `ROUTING_PROVIDER=otp` and `OTP_GRAPHQL_URL` are configured.
- Actual local API run returned `life_score 75.0`, summary `車なし生活は一部成立します。注意点を確認しながら試せます。`, and statuses: supermarket `ok`, hospital `caution`, pharmacy `ok`, city hall `support_needed`, station `caution`, social `caution`.

Rehearsal engine status:

- `backend/app/services/rehearsal/engine.py` generates up to three tasks, preferring `ok`/`caution` destinations and easier categories.
- Actual local API run generated 3 tasks: supermarket `ok`, pharmacy `ok`, hospital `caution`.
- Each task included Japanese title, memo, voice script, and family share text.

Data quality status:

- `backend/app/api/routes/data_quality.py` hardcodes `build_data_quality_report(gtfs_root=None, validator_json_path=None)`.
- Actual `/data-quality` returned `level: unknown`, warning `gtfs_data_absent`, and feed summary that GTFS is not connected and only fixture/mock confirmation is possible.
- Diagnosis warnings are present when a specific destination or route is missing, but the default fixture diagnosis returned no `data_quality_warnings`. The separate `/data-quality` page does surface the fixture/mock limitation.

Backend gaps against the target prototype:

- No live GTFS/ODPT data is loaded in the default app path.
- OTP is adapter-only unless externally configured; no live OTP server or GTFS graph was verified.
- `/data-quality` does not currently accept or read a configured GTFS root from settings.
- Rehearsal task storage is in-memory `_TASK_STORE` in `backend/app/api/routes/rehearsals.py`.
- No persistent user profile, family account, destination database, or municipality dataset exists.

## 5. Data / Routing / Mock Status

Current data path:

- `frontend/src/services/api.ts` calls backend APIs.
- `frontend/src/state/AppState.tsx` loads `GET /fixtures/demo`, optionally filters selected destinations, then posts the fixture payload to `POST /diagnosis/run`.
- `backend/app/fixtures/demo.py` provides all default destination and route data.
- `backend/app/services/diagnosis/engine.py` uses `mock_transport_results` directly when present.

Routing providers:

- `MockRoutingProvider` in `backend/app/services/routing/mock.py` is the current default and returns fixture plans or unavailable mock plans.
- `OTPRoutingProvider` in `backend/app/services/routing/otp.py` posts a GraphQL `plan` query and parses itinerary duration, walk time, waiting time, transfers, route names, and legs.
- `backend/tests/test_routing.py` mocks OTP HTTP responses and validates parsing and failure behavior.

Real-data status:

- GTFS/ODPT/OTP are not live-connected by default.
- `docs/data-policy.md` and `docs/technical-notes.md` correctly describe planned/optional real-data integration.
- `backend/app/services/data_quality/service.py` can inspect a GTFS directory if one is passed in code, but the route currently passes `None`.
- No raw ODPT/challenge data was found in the repo; `.gitignore` excludes `data/raw/` and `data/external/`.

Data quality warning status:

- `/data-quality` clearly warns about absent GTFS.
- Diagnosis-level warnings exist for missing coordinates, missing transport plans, and provider unavailable cases.
- The default demo diagnosis does not show a fixture/mock warning on `/result` because `diagnosis.data_quality_warnings` is empty for the complete synthetic fixture.

## 6. Voice / Accessibility / Elderly UX

Voice support:

- `frontend/src/pages/DailyPage.tsx` has a primary microphone button and starts speech recognition with `language: "ja-JP"`.
- It handles unsupported speech recognition with a Japanese fallback message and large category buttons.
- `frontend/src/utils/speech.ts` speaks Japanese text with `speechSynthesis`, `ja-JP`, and slower rate `0.88`.
- `frontend/src/components/ResultCards.tsx` and `frontend/src/pages/RehearsalPage.tsx` provide voice playback buttons.

Accessibility and elderly UX strengths:

- Short Japanese UI text is used throughout `frontend/src/pages/*.tsx`.
- Buttons are large and visually clear in screenshots.
- The home page offers the daily voice mode as a first-class action.
- Map mode is explicitly secondary in `frontend/src/pages/MapPage.tsx`.
- Status labels in `frontend/src/utils/labels.ts` translate enum states into elderly-readable Japanese: `行けそう`, `注意あり`, `支援が必要`, `判定不能`.

Accessibility and elderly UX gaps:

- Speech recognition only detects four fixed categories in `frontend/src/pages/DailyPage.tsx`; station and social are not available as spoken command buttons.
- The first onboarding step still requires text input for the home address.
- There is no screen-reader-specific audit, focus-order audit, or keyboard-only report beyond Testing Library route tests.
- Share behavior in `frontend/src/pages/RehearsalPage.tsx` falls back to clipboard/display, but there is no full family contact workflow.
- The design uses `clamp(...vw...)` font sizing in `frontend/src/styles.css`, which can cause viewport-dependent type changes. This is a mobile design risk.

## 7. Mobile UI Assessment

Evidence:

- `frontend/index.html` sets `<meta name="viewport" content="width=device-width, initial-scale=1.0" />`.
- `frontend/src/styles.css` has `body { min-width: 320px; }` and a `@media (max-width: 760px)` block.
- Browser check at `390x844` showed no horizontal scrolling on `/`, `/onboarding`, `/diagnosis`, `/result`, `/rehearsal`, `/daily`, `/map`, or `/data-quality`: `documentElement.scrollWidth`, `window.innerWidth`, and `body.scrollWidth` all returned `390`.
- Screenshots were captured at `390x844` and `1440x900`.

Mobile strengths:

- Home screen has two large vertical actions and readable Japanese text (`docs/audit-screenshots/mobile-home.png`).
- Onboarding first step has a large input and large next button (`docs/audit-screenshots/mobile-onboarding.png`).
- Diagnosis displays score and status cards clearly (`docs/audit-screenshots/mobile-diagnosis.png`).
- Daily mode puts the microphone button and destination buttons in the main flow (`docs/audit-screenshots/mobile-daily.png`).
- No route showed horizontal scroll at 390px.

Mobile risks:

- The UI is responsive, but not fully mobile-first: most screens are still centered bordered panels from `frontend/src/styles.css`.
- The design can feel like a desktop web prototype scaled to phone because there is no mobile app shell, bottom navigation, persistent primary action, safe-area treatment, or PWA install flow.
- Multi-card pages become long scroll pages on mobile, especially `/diagnosis`, `/result`, and `/rehearsal`.
- Map mode on mobile shows a large map area before the family report, while the visible map itself provides limited information.
- Font sizing uses viewport width in several `clamp()` calls, which can produce inconsistent text scale across devices.

## 8. Build and Test Results

Commands requested and results:

| Command | Result | Evidence summary |
|---|---:|---|
| `make test` | PASS | Ran docs check, backend pytest, ruff, frontend vitest, frontend build, and eslint. Backend: 18 passed, 1 Starlette/httpx deprecation warning. Frontend: 14 tests passed. |
| `make backend-test` | PASS | `cd backend && uv run pytest`; 18 passed, 1 Starlette/httpx deprecation warning. |
| `make frontend-build` | PASS with Vite chunk warning | `tsc -b && vite build`; build succeeded. Vite warned `maplibre-gl-B77VEHuT.js` is larger than 500 kB after minification. |

Additional runtime validation:

- Local backend for screenshots was started at `http://127.0.0.1:8001` because port 8000 was already occupied by a different FastAPI service where `/fixtures/demo` returned 404.
- Local frontend for screenshots was started at `http://127.0.0.1:5174` because port 5173 was already occupied.
- Backend required `CORS_ORIGINS=http://127.0.0.1:5174,http://localhost:5174` for the alternate screenshot port. Default `docker-compose.yml` is configured for 5173/8000.
- Actual API calls to `GET /fixtures/demo`, `POST /diagnosis/run`, `POST /rehearsals/generate`, and `GET /data-quality` succeeded on the audit ports.

Warnings to keep:

- Backend test warning: Starlette `TestClient` deprecation warning about `httpx`.
- Frontend build warning: MapLibre chunk over 500 kB.

## 9. Screenshots

Screenshots were saved to `docs/audit-screenshots/`. Each listed route has a desktop `1440x900` screenshot and a mobile `390x844` screenshot.

| Route | Desktop screenshot | Mobile screenshot |
|---|---|---|
| `/` | `docs/audit-screenshots/desktop-home.png` | `docs/audit-screenshots/mobile-home.png` |
| `/onboarding` | `docs/audit-screenshots/desktop-onboarding.png` | `docs/audit-screenshots/mobile-onboarding.png` |
| `/diagnosis` | `docs/audit-screenshots/desktop-diagnosis.png` | `docs/audit-screenshots/mobile-diagnosis.png` |
| `/result` | `docs/audit-screenshots/desktop-result.png` | `docs/audit-screenshots/mobile-result.png` |
| `/rehearsal` | `docs/audit-screenshots/desktop-rehearsal.png` | `docs/audit-screenshots/mobile-rehearsal.png` |
| `/daily` | `docs/audit-screenshots/desktop-daily.png` | `docs/audit-screenshots/mobile-daily.png` |
| `/map` | `docs/audit-screenshots/desktop-map.png` | `docs/audit-screenshots/mobile-map.png` |
| `/data-quality` | `docs/audit-screenshots/desktop-data-quality.png` | `docs/audit-screenshots/mobile-data-quality.png` |

Screenshot observations:

- Home, onboarding, diagnosis, rehearsal, and daily pages render as expected.
- The data-quality page renders the GTFS-not-connected warning.
- Map screenshots show the report data, but the map canvas visibly shows only the home marker; destination markers are not clearly visible.

## 10. Goal Achievement Scorecard

Scores use 0-5, where 5 means strong evidence from current code and runtime validation.

| Area | Score | Evidence |
|---|---:|---|
| Product positioning clarity | 5 | `README.md`, `docs/product-blueprint.md`, and `docs/open-data-challenge-2026-fit.md` consistently define a rehearsal/feasibility product, not route search or license-return persuasion. |
| Pre-return diagnosis loop | 4 | `/onboarding` to `/diagnosis` works with fixture data; `backend/app/services/diagnosis/engine.py` has deterministic logic and actual API returned LifeScore 75. Missing real destination/geocoding keeps it below 5. |
| Pre-return rehearsal loop | 4 | `/rehearsal` and `backend/app/services/rehearsal/engine.py` generate 3 tasks with voice/family text. Still fixture-derived and not tied to real calendars or trip execution feedback. |
| Post-return daily voice entry | 3 | `/daily` has a strong mobile voice entry, but command parsing is fixed-category and limited; no real-time route validation or natural language handling. |
| Elderly-friendly UI | 4 | Large buttons, Japanese text, voice playback, non-map-first flow in `frontend/src/styles.css` and page files. Address text input and web-card feel remain. |
| Mobile completion | 3 | Viewport and responsive layout work; no horizontal scroll at 390px; screenshots are readable. Still not a full app-like mobile shell and uses viewport-scaled fonts. |
| Family mode | 3 | `frontend/src/components/FamilyReport.tsx` groups status and next tasks; share text exists. No family account, export, invite, contact, or persistent report flow. |
| Map/municipality mode | 2 | MapLibre exists and family report works, but visible map evidence is weak and there is no municipality-level coverage analysis, filters, or route overlays. |
| Backend domain model completeness | 4 | Categories, statuses, LifeDiagnosis, reasons, warnings, voice scripts, and family share text exist in `backend/app/domain/models.py`. Persistence and real data config are missing. |
| Data quality handling | 3 | `/data-quality` returns `unknown` with `gtfs_data_absent`; service can inspect GTFS files if passed. Main diagnosis demo does not surface fixture/mock data-quality warning. |
| GTFS/ODPT/OTP integration | 2 | OTP adapter and tests exist; no live GTFS/ODPT/OTP run verified; route hardcodes absent GTFS. |
| Contest submission usability | 3 | Docs, demo script, build/test pass, no secrets needed. Needs public deployment evidence, stronger screenshots, visible data-quality narrative in main flow, and real/open-data integration story. |

## 11. Critical Gaps

MVP judgment:

The project has reached a runnable phase-1 fixture/mock demo MVP. It has not reached a real-data MVP for the full target of public-transport-backed carless-life rehearsal. For a ChatGPT/product evaluation, the honest label should be: `Phase-1 demo MVP: yes; real GTFS/ODPT/OTP MVP: no`.

Top gaps, priority order:

1. Real GTFS/ODPT/OTP is not connected to the default product path. Evidence: `backend/app/api/routes/data_quality.py` passes `gtfs_root=None`; `backend/app/services/routing/provider.py` defaults to mock unless env is configured.
2. Main diagnosis result does not warn that the default result is fixture/mock-only. Evidence: actual `POST /diagnosis/run` returned no `data_quality_warnings`, while `/data-quality` separately returned `gtfs_data_absent`.
3. Onboarding cannot create real user destinations. Evidence: `frontend/src/pages/OnboardingPage.tsx` selects from fixture destinations and only edits home address text.
4. Daily voice mode is limited to four fixed category commands. Evidence: `frontend/src/pages/DailyPage.tsx` only detects `スーパー`, `病院`, `薬局`, and `市役所`.
5. Map mode is visually underpowered. Evidence: `frontend/src/components/MapLibreStatusMap.tsx` intends markers, but screenshots show only the home marker and no route/coverage overlays.
6. No persistence exists for user profile, selected destinations, diagnosis history, rehearsal tasks, or family reports. Evidence: frontend state is in `frontend/src/state/AppState.tsx`; backend rehearsal store is `_TASK_STORE` in memory.
7. Mobile UX is responsive but still web-card oriented. Evidence: `frontend/src/styles.css` uses centered bordered panels and viewport-based `clamp()` font sizes.
8. PWA/app readiness is absent. Evidence: no manifest, service worker, offline support, or install behavior found in `frontend/index.html` or `frontend/src`.
9. Family/municipality mode is a report display, not a decision workflow. Evidence: `frontend/src/components/FamilyReport.tsx` groups results but has no filters, export, notes, support assignment, or local coverage analytics.
10. Real deployment/public demo was not verified. Evidence: validation was local only; no hosted URL, CI status, or production build serving was checked.

## 12. Recommended Next Development Steps

Recommended next round:

1. Make the fixture/mock limitation visible in the main diagnosis/result flow, not only `/data-quality`.
2. Wire configurable GTFS/data-quality inputs into settings and `/data-quality`, then add a small checked-in synthetic GTFS or documented local fixture path for repeatable real-data-style validation.
3. Add an integration path that runs diagnosis through `OTPRoutingProvider` against a known local OTP test endpoint or mocked service at app level, not only unit tests.
4. Expand onboarding from fixture selection to real-life setup: add/edit destinations by category, validate required categories, and keep manual address fallback.
5. Fix or verify MapLibre destination marker rendering; add legend, route/coverage lines, and clearer family/municipality evidence.
6. Improve mobile app feel: remove viewport-width font scaling, reduce desktop-card framing on mobile, add an app-like primary flow, and keep buttons at elderly-friendly touch sizes.
7. Expand daily voice mode to include station/social, confirm recognized command on screen, and handle unknown destination requests more explicitly.
8. Add persistence strategy appropriate for MVP: local storage for frontend demo or backend store for profile/diagnosis/rehearsal history.
9. Add lightweight E2E screenshot checks for all routes at desktop and mobile widths.
10. Prepare contest demo package: hosted URL, demo script with screenshots, fixture/mock disclosure, data policy statement, and optional OTP/GTFS setup notes.

Unable to verify in this audit:

- Live GTFS/ODPT feed ingestion.
- A running OpenTripPlanner server or real OTP GraphQL endpoint.
- Public deployment, CI, or hosted contest URL.
- Browser microphone permission behavior with a real microphone.
- Actual speech synthesis audio output quality.
- Screen-reader output, keyboard-only flow, contrast measurements, or formal WCAG checks.
- Real elderly-user usability testing.
- Production privacy/security posture.

## 13. Files Read

Documentation and root:

- `README.md`
- `Makefile`
- `.gitignore`
- `docker-compose.yml`
- `docs/architecture.md`
- `docs/data-policy.md`
- `docs/demo-script-ja.md`
- `docs/demo-script-zh.md`
- `docs/open-data-challenge-2026-fit.md`
- `docs/product-blueprint.md`
- `docs/submission-summary-ja.md`
- `docs/technical-notes.md`

Frontend:

- `frontend/README.md`
- `frontend/Dockerfile`
- `frontend/package.json`
- `frontend/package-lock.json` was included in file inventory and dependency evidence; full lockfile was not line-by-line summarized.
- `frontend/eslint.config.js`
- `frontend/index.html`
- `frontend/tsconfig.json`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `frontend/vite.config.js`
- `frontend/vite.config.d.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/state/AppState.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/OnboardingPage.tsx`
- `frontend/src/pages/DiagnosisPage.tsx`
- `frontend/src/pages/ResultPage.tsx`
- `frontend/src/pages/RehearsalPage.tsx`
- `frontend/src/pages/DailyPage.tsx`
- `frontend/src/pages/MapPage.tsx`
- `frontend/src/pages/DataQualityPage.tsx`
- `frontend/src/components/FamilyReport.tsx`
- `frontend/src/components/MapLibreStatusMap.tsx`
- `frontend/src/components/ResultCards.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/types.ts`
- `frontend/src/types/react-speech-recognition.d.ts`
- `frontend/src/utils/labels.ts`
- `frontend/src/utils/speech.ts`
- `frontend/src/styles.css`
- `frontend/src/test/App.flow.test.tsx`
- `frontend/src/test/App.routes.test.tsx`
- `frontend/src/test/setup.ts`

Backend:

- `backend/README.md`
- `backend/Dockerfile`
- `backend/pyproject.toml`
- `backend/uv.lock` was included in file inventory and dependency evidence; full lockfile was not line-by-line summarized.
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/domain/models.py`
- `backend/app/fixtures/demo.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/api/routes/data_quality.py`
- `backend/app/api/routes/diagnosis.py`
- `backend/app/api/routes/fixtures.py`
- `backend/app/api/routes/rehearsals.py`
- `backend/app/services/data_quality/__init__.py`
- `backend/app/services/data_quality/service.py`
- `backend/app/services/diagnosis/__init__.py`
- `backend/app/services/diagnosis/engine.py`
- `backend/app/services/rehearsal/__init__.py`
- `backend/app/services/rehearsal/engine.py`
- `backend/app/services/routing/__init__.py`
- `backend/app/services/routing/base.py`
- `backend/app/services/routing/mock.py`
- `backend/app/services/routing/otp.py`
- `backend/app/services/routing/provider.py`
- `backend/tests/test_data_quality.py`
- `backend/tests/test_diagnosis.py`
- `backend/tests/test_health.py`
- `backend/tests/test_models_and_fixtures.py`
- `backend/tests/test_rehearsals.py`
- `backend/tests/test_routing.py`
