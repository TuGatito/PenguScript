#!/usr/bin/env bash
# `psc test --coverage` must emit gcov data mapped to .pengu sources.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
command -v gcov >/dev/null 2>&1 || { echo "SKIP coverage: gcov not found"; exit 0; }
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[build]
entry = "src/main.pengu"
name = "cov"
output = "exe"
TOML
cat >"$tmp/src/main.pengu" <<'PENGU'
weave add with a as int, b as int into int:
    return a + b

test "add works":
    var r as int is calling add with 1, 2
    if r != 3:
        calling print with "bad"
PENGU
cd "$tmp"
"$PSC" test . --coverage --no-cache >"$tmp/out.log" 2>&1 || { cat "$tmp/out.log"; exit 1; }
[ -f main.pengu.gcov ] || { echo "no main.pengu.gcov"; ls; exit 1; }
grep -q 'Source:.*src/main.pengu' main.pengu.gcov
grep -q 'coverage: src/main.pengu' "$tmp/out.log" || {
  echo "coverage summary missing"; cat "$tmp/out.log"; exit 1; }
grep -q 'coverage: pengu_runtime' "$tmp/out.log" && {
  echo "runtime header leaked into summary"; exit 1; }
echo "OK coverage mapped to .pengu"
