# Gate 4 — rehearsal loop acceptance (2026-09-05)

## Scoped result
PASS: real dated diagnosis → six independent rehearsal candidates → voice/share text → session-only completed/needs-support records → family report → change dates and regenerate without old records. Gate 3's pilot route restrictions are removed. Default demo remains supported.

No deployment, remote push, actual outing, accessibility certification, account/cloud persistence or external sharing is claimed. The authorized local commit includes the reviewed Gate 3 prerequisites and Gate 4 implementation on `codex/hakusan-frontend-gate3`, based on `234e2a4`.

## Automated verification
- Backend/scripts: 114 tests and 6 subtests pass.
- Frontend: 43 tests pass; ESLint, TypeScript and both default/Hakusan Vite builds pass.
- Focused Ruff and `git diff --check` pass.
- Test-first failures observed for real schedule preservation/date rejection, missing rehearsal entry and outcome state, empty-result repeated generation, missing station/social choices, and home-vs-public-origin map label. Corresponding checks now pass.
- Missing/reversed/naive real dates rejected; unknown-route results are not offered as rehearsals. Demo generation still uses its original contract.
- All real text channels use the same Japanese-time dates, origin and route summaries; missing alternatives are marked unverified instead of inventing another bus. Support/caution records never upgrade route feasibility.
- Record invalidation on changed dates and stale-response protection tested. An empty successful generation is cached. Sharing failure is caught; preview never implies sending.

## Live browser acceptance
Headed Chromium, 390×844, real local services: frontend 15173 → FastAPI 18000 → OTP 2.9 at 18081 using the verified Gate 1 graph. No mocked routing or browser network interception.

1. Public origin 36.52725, 136.5605; all six contracted destinations; walk 15 min / transfers 1. Entered 2026-09-08 06:50 and 11:00 Japan time.
2. Diagnosis and generation returned HTTP 200. Six real tasks displayed the exact dates, actual walking summaries and unknown-access/alternative-service caveats. No hardcoded 10:00 departure.
3. Share button displayed a readable preview containing the same dates and restrictions, explicitly not sent. Did not invoke native external sharing or clipboard in the real browser.
4. Entered explicitly synthetic notes: pharmacy needs-support; station completed (screen rehearsal, not a real trip). Family report displayed both outcomes and notes. Browser document width and scrollWidth both 390 on rehearsal and report.
5. Changed dates to 2026-09-09 06:50 and 11:00; a new diagnosis and generation returned HTTP 200. Six tasks contained the new date, no old date or recorded status. Records do not become claims about the new itinerary.

Screenshots (ignored local acceptance artifacts):
- `output/playwright/hakusan-gate4-task.png`: dated task, share preview, support record.
- `output/playwright/hakusan-gate4-records.png`: report of two explicitly synthetic outcomes.

## Boundaries / remaining risk
- Records survive in-app navigation only. Reload, tab closure or condition changes clear them. No sensitive home address collected; pilot origin remains public and fixed.
- Static timetable/stop-proxy destinations are not realtime service or verified building entrances. The position map has no road basemap or route geometry and is labeled accordingly.
- Hardware microphone recognition, audibility and recipient delivery were not tested; generated voice text and UI controls are tested, and external sending was intentionally not performed.
- Existing MapLibre large-chunk warning, Starlette/httpx deprecation and cosmetic favicon 404 remain. No application API failure or test failure remains in acceptance.
- Backend rehearsal GET storage remains the existing process-local store, not durable persistence or a multi-user production contract.

## Reproduce / commit gate
Local startup commands are in the Gate 3 acceptance record. Run:

```sh
PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts -q
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
VITE_DATA_PROFILE=hakusan npm --prefix frontend run build
git diff --check
```

Diff reviewed and staged by explicit paths, excluding ignored GTFS/OSM/OTP/browser files. Commit only after these checks, then confirm `git status --short --branch`. No merge/push is authorized in this stage.
