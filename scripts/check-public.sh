#!/usr/bin/env bash
#
# Public-safety guard: fail if internal-only references leak into tracked files.
# Run before publishing / merging, or wire into CI:
#
#   bash scripts/check-public.sh
#
# This repo is published externally — it must not reference internal registries,
# Jira tickets, go-links, or internal hosts. The internal trail belongs in the
# Demo Review Document / Jira, not in the public repo.
set -uo pipefail

# Unambiguous internal markers. (This script is excluded so its own patterns
# don't trip the check.)
PATTERN='pypi-proxy\.dev\.databricks\.com|FEIP-[0-9]+|LPP-[0-9]+|go/lpp|go/securityexception|go/entsecintake|go/fe-workspace'

matches="$(git grep -nIE "$PATTERN" -- . ':!scripts/check-public.sh' 2>/dev/null || true)"

if [ -n "$matches" ]; then
  echo "✖ Internal-only references found in tracked files:" >&2
  echo "$matches" >&2
  echo "" >&2
  echo "Remove them before publishing — pin public registries and keep internal" >&2
  echo "tickets/links in the DRD / Jira, not in this public repo." >&2
  exit 1
fi

echo "✓ check-public: no internal-only references in tracked files."
