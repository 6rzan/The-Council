#!/usr/bin/env bash
# Secret-scan gate (T044, Constitution Principle IV).
# Fails (exit 1) if any TRACKED or staged file is a real .env, or contains a
# Google API key value (AIza... pattern) or a GOOGLE_API_KEY= assignment with a
# non-placeholder value. .env.example with an empty/placeholder key is allowed.
#
# Usage: scripts/secret-scan.sh [--staged]
#   --staged : scan only staged files (for the pre-commit hook)
#   default  : scan all tracked files (for CI / manual gate)
set -euo pipefail

if [[ "${1:-}" == "--staged" ]]; then
    mapfile -t FILES < <(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
else
    mapfile -t FILES < <(git ls-files 2>/dev/null || true)
fi

status=0
for f in "${FILES[@]}"; do
    [[ -f "$f" ]] || continue
    base=$(basename "$f")
    # (a) a real .env file tracked/staged (the .env.example exception is by name)
    if [[ "$base" == ".env" ]]; then
        echo "SECRET-SCAN FAIL: tracked/staged file '$f' is a real .env" >&2
        status=1
        continue
    fi
    # (b)/(c) scan contents for key values or live assignments
    if grep -nE 'AIza[0-9A-Za-z_-]{35}' "$f" >/dev/null 2>&1; then
        echo "SECRET-SCAN FAIL: '$f' contains a Google API key (AIza...)" >&2
        status=1
    fi
    # GOOGLE_API_KEY=<value> where value is non-empty and not a placeholder
    if grep -nE 'GOOGLE_API_KEY[[:space:]]*=[[:space:]]*[^[:space:]<]' "$f" \
        | grep -vE 'GOOGLE_API_KEY[[:space:]]*=[[:space:]]*(your[_-]?key|<|\$\{|""|'')' >/dev/null 2>&1; then
        echo "SECRET-SCAN FAIL: '$f' contains a GOOGLE_API_KEY assignment with a value" >&2
        status=1
    fi
done

if [[ $status -eq 0 ]]; then
    echo "SECRET-SCAN OK: no secrets in ${#FILES[@]} file(s)."
fi
exit $status
