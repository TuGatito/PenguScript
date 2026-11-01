#!/usr/bin/env bash
# Regression: a concrete list method must not run on a list with another
# element type.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/bad.pengu" <<'PENGU'
enchanting list of int:
    ## Only valid for list of int.
    weave only_int into int:
        return 1

weave main into int:
    var ws as list of string is ["a"]
    let v as int is calling ws.only_int
    return v
PENGU
if "$PSC" check "$tmp/bad.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: list-of-string accepted list-of-int method"
    cat "$tmp/out"
    exit 1
fi
if ! grep -q "not defined for this receiver type" "$tmp/out"; then
    echo "FAIL: wrong diagnostic for receiver mismatch"
    cat "$tmp/out"
    exit 1
fi
echo "OK receiver guard"
