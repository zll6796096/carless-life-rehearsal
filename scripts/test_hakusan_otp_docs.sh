#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
makefile="$root/Makefile"
readme="$root/README.md"
data_policy="$root/docs/data-policy.md"
challenge_fit="$root/docs/open-data-challenge-2026-fit.md"
technical_notes="$root/docs/technical-notes.md"
sources="$root/data/hakusan/otp-sources.json"

grep -Fq 'hakusan-otp-test:' "$makefile"
grep -Fq 'hakusan-otp-fetch:' "$makefile"
grep -Fq 'hakusan-otp-evidence:' "$makefile"

grep -Fq 'OpenTripPlanner 2.9.0' "$readme"
grep -Fq 'Java 25' "$readme"
grep -Fq '11 fixed routes' "$readme"
grep -Fq 'ROUTING_PROVIDER=mock' "$readme"
grep -Fq 'not realtime' "$readme"

grep -Fq 'CC BY 4.0' "$data_policy"
grep -Fq 'ODbL' "$data_policy"
grep -Fq 'data/external/' "$data_policy"
grep -Fq '2 GiB' "$technical_notes"
grep -Fq 'planConnection' "$technical_notes"
grep -Fq 'Gate 1' "$challenge_fit"
grep -Fq '11' "$sources"

echo "Hakusan OTP documentation checks passed."
