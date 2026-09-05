# Gate 3: Hakusan mobile pilot integration

## Objective and boundary
Make the verified Gate 2 routing usable through the existing mobile flow. Goal before options; verifiable value before surface output. Preserve the default demo. No geocoding, arbitrary origins, realtime service, accessibility guarantees, deployment, submission, push or unrelated refactor.

## Minimal deliverable
Opt-in `VITE_DATA_PROFILE=hakusan`, six contracted destinations from the backend, a fixed public test origin, explicit outbound/return dates in Japan time, and visible provenance/limitations in the result. Reject missing, reversed or out-of-service dates. Reject the pilot when OTP is not configured; never substitute mock routing.

## Files and guardrails
Backend fixture/model/API and focused tests; frontend types/API/state/onboarding/result/data-quality pages and tests; this plan and browser acceptance record. Read source JSON without rewriting it. Do not touch external graph/data artifacts or secrets. Keep async results from superseded inputs out of state.

## Acceptance and verification
- Demo regression suite remains passing.
- Pilot payload has contracted coordinates, explicit +09:00 dates and no mock journeys.
- Date validation and cache invalidation tested; pilot mock configuration fails closed.
- Real OTP -> HTTP backend -> 390px mobile browser flow reaches six results, displays caveats, and has no horizontal overflow.
- Run `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests scripts`, `npm --prefix frontend test`, `npm --prefix frontend run lint`, `npm --prefix frontend run build`, `git diff --check`, and review `git status`.
- Browser artifacts and exact tested dates recorded; successful local acceptance is not deployment or field accessibility validation.
