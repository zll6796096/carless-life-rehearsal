# Hakusan OTP Gate 2

Authorized by the user: enter the next stage after the Gate 1 local merge.

Objective: connect the backend to the proven OTP 2.9.0 graph and verify round
trips for all six destination categories. Data integrity precedes apparent
coverage. The minimum deliverable is the adapter, explicit journey times,
fail-closed errors, and reproducible local evidence through the diagnosis API.

Scope: backend routing, diagnosis request/engine, regression tests, local
evidence script, operator documentation. UI redesign, public deployment,
realtime feeds and challenge submission are outside this stage.

Acceptance:

- Use the actual OTP 2.9.0 planConnection schema; swap coordinates for return.
- Require an explicit timezone-aware outbound/return datetime for live diagnosis.
- Validate allowed route IDs; no silent mock fallback when OTP is selected.
- Reject GraphQL errors, malformed responses, unsupported modes and missing data.
- Preserve fixture behavior and report unverified stair accessibility honestly.
- Verify six categories from a residential origin in both directions using the
  pinned Gate 1 graph. Unavailable results remain unknown, never fabricated.
- Run backend regression tests, full make test, and git diff --check.

Risks: small street islands, sparse services, missing accessibility attributes,
and stop coordinates used as destination proxies. Routing success is not proof
of an accessible building entrance or suitability for an individual.

Implementation sequence: adapter and regression tests; explicit dates and
provider selection; six-destination API evidence; documentation and full gate.

## Verification completed

- Used the exact Gate 1 graph with SHA-256
  `c898d7a2fa96cf3d944783f2b7f525830260533012da44d0e7038e74f952014d`.
  Started OTP 2.9.0 locally with a 2 GiB heap and stopped it after verification.
- Queried the running schema to verify field names before adapting the client.
- All six categories returned outbound and return routes (12/12); the actual
  FastAPI diagnosis endpoint returned six live-provider results. Missing dates
  yielded unknown for every destination. The summary is recorded in
  `data/hakusan/gate2-validation-summary.json`.
- Hospital: 21/25 minutes total, 13 minutes walking each way. Social centre:
  27/19 minutes total, 17/13 minutes walking. These are route computations to
  the contracted points; the Gate 1 pruning notices do not establish a present
  routing failure or prove an accessible entrance.
- Supermarket outbound required 25 minutes walking and was correctly classified
  support_needed under a 15-minute walking profile. The remaining categories
  received caution, including unverified accessibility. Confidence was 0.49.
- Fixed first-result bias by ranking alternatives using profile-limit excess
  then arrival time. Accepted WALKING_BETTER_THAN_TRANSIT only with valid pure
  walking alternatives. All other routing errors remain unavailable.
- Added a chronological round-trip check: outbound arrival after the requested
  return departure produces unknown.
- `make test` passed: Gate 0 11, Gate 1 54, backend 34, frontend 32 tests;
  backend/frontend lint and frontend production build passed. Existing
  Starlette/httpx and MapLibre chunk warnings remain.
- Diff review and `git diff --check` passed. No raw feed or graph is tracked.

Next boundary: connect the frontend to explicit journey dates and Hakusan
destinations, show source/quality limitations, then verify the complete mobile
user flow. Default fixture mode remains available. No public deployment or
competition submission was performed in Gate 2.
