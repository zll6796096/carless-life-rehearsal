# Apple-style web slice — local acceptance

Date: 2026-09-05 (Asia/Tokyo)

## Outcome and source binding

Implemented the approved home and diagnosis design in the running React application. This is not the earlier static mockup. Local acceptance passed; production release is **not performed or authorized by this checkpoint**.

- Application base: `c4f32568106e2144d97151f9babb9376cff50a64`.
- Execution baseline: `deaeaa91070bc435ae479ff5da8667c3e96d94a0` (approved specification and implementation plan).
- Implementation: `04725ad22a6e4d36896a0fc338720f3b7d93a8f1`.
- Branch: `codex/apple-web-preview`; ordinary checkout, not a linked worktree.
- Starting worktree was clean; implementation checkpoint worktree is clean.
- Execution was inline as selected by the user. Review was an inline source/requirements review, not an independent subagent review.
- Local app: <http://127.0.0.1:5174/>. API: <http://127.0.0.1:18000>. These URLs require the local processes to remain running.

Scope is the home, diagnosis and existing Hakusan `/result` alias only. Onboarding, Daily, rehearsal, map/report, API/state ownership, scoring, GTFS, routing, dependencies and cloud configuration were not redesigned or changed.

## Changed paths

| Path | Responsibility |
| --- | --- |
| `frontend/src/pages/HomePage.tsx` | Approved hero, public test-origin notice, original four links, single primary bottom action |
| `frontend/src/pages/DiagnosisPage.tsx` | Wire presentation and loading/error accessibility; preserve request effect |
| `frontend/src/components/AppleDiagnosisSummary.tsx` | Dynamic dates, status groups, journeys, speech, evidence and attribution |
| `frontend/src/styles/apple-web.css` | Scoped styles only; no global CSS changes |
| `frontend/src/test/AppleWeb.test.tsx` | Five new contract tests with deliberately different dates/score/data from the mockup |
| `frontend/src/test/App.flow.test.tsx` | Assert approved home copy; expand disclosure before asserting its speech action |

The implementation commit contains 6 files, 332 insertions and 68 deletions. `git diff --name-only c4f3256 --` for AppState, App, MobileAppShell, ResultCards, PilotNotice, types, API service, global CSS, backend and frontend package/lockfiles returned no paths.

## Verification commands and results

All commands below were run against the implementation source, with no remaining source edits at commit time.

| Gate | Command | Observed result |
| --- | --- | --- |
| Frontend | `cd frontend && npm test` | Exit 0; **48 passed**, 5 files (baseline: 43) |
| Lint | `cd frontend && npm run lint` | Exit 0 |
| TypeScript / bundle | `cd frontend && npm run build` | Exit 0 |
| Hakusan-profile bundle | `cd frontend && VITE_DATA_PROFILE=hakusan VITE_API_BASE_URL=http://127.0.0.1:18000 npm run build` | Exit 0; local-check artifact only, not a deployable production-API bundle |
| Backend/scripts | `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts -q` | Exit 0; **119 passed, 6 subtests passed** |
| Python lint | `backend/.venv/bin/ruff check backend` | Exit 0; all checks passed |
| Cloud config safety | `bash scripts/test_cloudbuild_config.sh` | Exit 0; cloud build safety checks passed; this is a local check, not a deployment |
| Real routing | `backend/.venv/bin/python scripts/smoke_hakusan_release.py http://127.0.0.1:18000` | Exit 0; `hakusan_real_smoke=PASS destinations=6 dated_rehearsals=6` |
| Diff | `git diff --check` and `git diff --cached --check` | Exit 0 |

Local routing used Java 25 / OTP 2.9.0, the existing validated graph at `data/external/hakusan/otp/evidence-runs/run-10u4k233`, and `ROUTING_PROVIDER=otp`. Frontend ran with `VITE_DATA_PROFILE=hakusan` and the local API; local CORS was set only on the local backend process. No cloud CORS or credentials were changed.

## Browser acceptance

Playwright sessions: `apple-implementation` (happy path), `apple-failure` (local request interception and recovery). Browser title was `車なし生活リハーサル`; served URL was port 5174, not the mockup server.

- Home → five-step onboarding → **2026-09-08 06:50 / 11:00 Japan time** → real diagnosis.
- Six actual destinations rendered: one support-needed, five caution, zero independently feasible. Evidence showed **55 points / 49% data completeness**, with the explicit caveat that completeness is not safety or arrival probability. These values came from the API; tests also verify a different 47 / 31% response and October dates.
- Hospital disclosure opened with Enter and closed with Space, then opened by click. Both actual journey summaries and all reasons remained available.
- Speech action invoked the real browser `speechSynthesis.speak` with `ja-JP` and actual reasons. Audible output / pronunciation was **not independently heard or certified**.
- Rehearsal produced six dated candidates. Family sharing was **preview only**; no external send, clipboard write or share app launch.
- Saved a support-needed test note: `UI動作確認のみ・実際の外出はしていません。家族への入口確認が必要。`. It appeared in the family report. No outdoor trip was performed.
- Changed to **2026-09-09 07:10 / 11:20** in onboarding. A fresh diagnosis response was observed; new rehearsal dates appeared, old note/outcome disappeared, and family report showed `まだ記録はありません。`.
- `/result` rendered the same new diagnosis with the current selected dates. This alias was exercised through client history navigation without reloading or injecting application state.
- Original home links reached `/daily`, `/map` and `/data-quality`; home-return navigation remained available. These pages keep their existing design.
- In the separate failure session, only local `/diagnosis/run` was intercepted with 503. The alert and setup link remained, with **no success cards or rehearsal CTA**. Interception was removed; returning through setup restored a real diagnosis without the old alert. Backend was never stopped to simulate failure.

## Visual and accessibility checks

Compared actual rendered pages with the approved HTML/mobile screenshots: neutral gray background, white grouped surfaces, green primary action, system Japanese type, restrained separators, collapsed route details and visible public-origin/static-data limitations. Production intentionally omits mockup controls/labels and retains the existing mobile-width desktop shell.

- Viewports **320×844, 390×844 and 1440×844**: no document horizontal overflow, no visible home/diagnosis controls below 44px high, and the final link can be scrolled above the fixed bottom action.
- Normal-size last-link bottom was about 674px; dock top 726px.
- **200% text scaling** was verified by a computed root font of **32px**, at 320px width. After the fix, last-link bottom was about 524px and dock top 607px on both pages. Reduced-motion preference was exercised on diagnosis.
- This is Chromium automation with enlarged text, not certification on physical iOS/Safari, native browser zoom, VoiceOver or an elderly-user field trial.

Validation found and fixed these bounded regressions before the commit:

1. Old exact home copy assertion no longer matched the approved design; updated the expected copy without deleting navigation assertions. Restored the original family/supporter landmark, which the retained test caught.
2. Later-loaded shared `.mobile-shell` CSS overrode the scoped background and bottom padding. Increased specificity only inside the new page class; verified computed gray background `rgb(245, 246, 243)`.
3. At 200% text, the final license link extended to 674px while the dock began at 607px. Changed the content reserve to a relative-size-aware value; repeated measurement passed. Waited for the computed font and final scroll position to settle before taking the accepted measurements.
4. Error-state setup link was only 19px high. Scoped its hit area to at least 44px; verified 44px and successful recovery.
5. Balanced the diagnosis summary wrapping so a single Japanese character is not left on its own line at the normal mobile viewport.

### Local screenshots

Screenshots are local ignored artifacts in `output/playwright/`, not committed assets. These named files reflect the accepted source and were visually inspected:

- `apple-implementation-home-390.png`, `apple-implementation-home-320.png`, `apple-implementation-home-1440.png`
- `apple-implementation-home-bottom-390.png`, `apple-implementation-home-200-text.png`
- `apple-implementation-diagnosis-390.png`, `apple-implementation-diagnosis-320.png`, `apple-implementation-diagnosis-1440.png`
- `apple-implementation-diagnosis-bottom-390.png`, `apple-implementation-diagnosis-200-text.png`
- `apple-implementation-expanded-mobile.png`, `apple-implementation-evidence-mobile.png`, `apple-implementation-error-320.png`
- `apple-implementation-rehearsal-record.png`, `apple-implementation-family-record.png`, `apple-implementation-after-date-change.png`

Earlier generic `*-mobile.png` full-page captures and `*-before.png` captures may show intermediate state or a fixed dock in the middle of a full-page image; use the viewport-specific files above for final appearance.

## Warnings, guardrails and next checkpoint

- Existing MapLibre bundle remains above Vite's 500 kB warning threshold; no dependency or bundling remediation was included.
- Backend tests emit the existing Starlette/httpx deprecation warning.
- Happy-path development browser logged a missing `favicon.ico` 404; no application JavaScript exception was observed. Failure session additionally logged the intentionally simulated 503.
- The UI remains a static-timetable public-point trial. Entrances, stairs, facility opening hours, delays and actual travel safety are not established by these tests.
- Real devices, audible speech and user usability validation remain external/manual acceptance work.
- No main merge, push, PR, Cloud Build submission, Cloud Run update or production traffic change was performed. Local tests do not prove a new production release.
- Keep `codex/apple-web-preview` and the local preview for the user's review. A later production push/deployment requires a separate explicit authorization and its own release/smoke gates.
