# Hakusan cloud release

User authorized cloud OTP, added resource costs, packaging and production-gate changes.

Objective: publicly usable real Hakusan diagnosis/rehearsal, not a refreshed demo. Preserve paired API/Web lock, zero-traffic candidates, exact rollback and digest provenance.

Scope: private graph-versioned OTP service `carless-hakusan-otp-c898d7a2`, 2 CPU / 4 GiB, min 0 / max 1, concurrency 8. One-time private placeholder service provisioning establishes the service-scoped Cloud Build deploy permission without broad project IAM. No API/Web traffic change during bootstrap. Actual OTP image and API/Web deployment remain owned by the main Cloud Build trigger.

Artifacts: upload only the validated graph and pinned JAR to immutable hash-named objects in a dedicated private regional bucket, `zhang23-23-carless-hakusan-artifacts`; grant the build identity object-viewer on this bucket only and verify SHA256 again in Cloud Build. Do not commit raw data or tokens. OTP is IAM protected; grant only the existing API runtime identity invocation. Retain graph-versioned service for exact rollback; never expose OTP publicly.

Implementation: backend metadata-server identity token when configured; repository-root API Docker build includes only source and data contracts; opt-in Hakusan web build; extra authenticated real-routing and rehearsal smoke in every candidate/production phase. Keep existing demo smoke as compatibility checks, not proof of real routing.

Acceptance: current-source tests/lint/build, artifact checks, unauthenticated OTP denial, Cloud Build success with both real and demo smoke, production digest/provenance, real browser at public URL, clean committed/pushed main. Failure before promotion retains/restores the previous API/Web pair. No accounts, persistent records, new external messaging, or unrelated service changes.

Verification commands: backend pytest/Ruff, frontend test/lint/build, shell config guards, hash checks, Cloud Build status/logs, Cloud Run revision/traffic inspection, public API and browser checks. Official auth contract: https://docs.cloud.google.com/run/docs/authenticating/service-to-service .
