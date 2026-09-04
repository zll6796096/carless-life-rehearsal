#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$root/data/hakusan/manifest.json"
rules="$root/data/hakusan/route-rules.json"
makefile="$root/Makefile"
readme="$root/README.md"
data_policy="$root/docs/data-policy.md"
challenge_fit="$root/docs/open-data-challenge-2026-fit.md"
technical_notes="$root/docs/technical-notes.md"

grep -Fq '765cd548-a1f3-46e6-b05b-d6168b9b85d1' "$manifest"
grep -Fq 'CC BY 4.0' "$manifest"
grep -Fq '静的時刻表' "$manifest"
grep -Fq '"default_policy": "deny"' "$rules"
grep -Fq '予約が必要' "$rules"

grep -Fq 'hakusan-data-test:' "$makefile"
grep -Fq 'hakusan-data-evidence:' "$makefile"
grep -Fq 'Hakusan Gate 0' "$readme"
grep -Fq 'CC BY 4.0' "$data_policy"
grep -Fq 'ODbL' "$data_policy"
grep -Fq '予約が必要' "$challenge_fit"
grep -Fq 'static timetable' "$technical_notes"
grep -Fq 'ROUTING_PROVIDER=mock' "$technical_notes"

echo "Hakusan data documentation checks passed."
