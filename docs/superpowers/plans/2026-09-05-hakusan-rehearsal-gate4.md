# Gate 4 — dated rehearsal and session feedback loop

Objective: connect verified diagnosis dates and route summaries to rehearsal, voice/share preview, session-only outcome records and family report; enable safe re-planning. Goal and evidence before surface completion.

Scope: backend diagnosis/task contracts and generator; frontend task rendering, shared state, daily/family views and tests. Include the reviewed uncommitted Gate 3 prerequisites in the authorized Git commit. Preserve other work. No push, merge, deployment, account/storage integration, automatic share, real outing claims or accessibility guarantees.

Acceptance:
- Routing-provider diagnosis carries explicit aware outbound/return dates and origin label. Missing/reversed dates cannot generate real rehearsals; unknown routes are not offered.
- Structured task dates/summaries used in screen, voice and share; no hardcoded demo departure or invented next bus. Each destination is an independent round trip, not a multi-stop tour.
- Pilot daily/category view and family report reuse the same task set. Outcomes completed/needs-support and optional notes are session-only, shown in family report, cleared when inputs change. They do not modify route feasibility or claim verified accessibility.
- Native share/clipboard failure is handled honestly; preview remains readable. No external sending during verification.
- Demo regressions pass; real OTP → HTTP API → mobile browser diagnosis/rehearsal/record/report/re-plan tested. Build, lint, backend/scripts tests, diff review and clean post-commit Git status required.

Verification: `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts -q`; frontend `npm test`, `npm run lint`, demo and Hakusan `npm run build`; focused Ruff; Playwright 390x844; `git diff --check`, explicit staging, `git diff --cached`, commit and `git status`.

Risks: service snapshot is not realtime; no verified entrances/step-free paths; user-entered outcomes are not safety clearance. Dates changing invalidate tasks and records; stale responses must not restore old state. Browser refresh loses session notes (disclose in UI).
