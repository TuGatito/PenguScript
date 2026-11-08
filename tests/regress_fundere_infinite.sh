#!/usr/bin/env bash
# `fundere` no puede crear un valor de tamaño infinito (E0050).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/self.pengu" <<'PENGU1'
rune A fundere A:
    x as int
PENGU1

if "$PSC" check "$tmp/self.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: auto-embed debería ser E0050" >&2
    exit 1
fi
if ! grep -q "error\[E0050\]: type 'A' has infinite size: A -> A" "$tmp/out"; then
    echo "FAIL: falta el diagnóstico del auto-embed" >&2
    cat "$tmp/out" >&2
    exit 1
fi

cat >"$tmp/mutual.pengu" <<'PENGU2'
rune A fundere B:
    x as int

rune B fundere A:
    y as int
PENGU2

if "$PSC" check "$tmp/mutual.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: embed mutuo debería ser E0050" >&2
    exit 1
fi
if ! grep -q "has infinite size: A -> B -> A" "$tmp/out"; then
    echo "FAIL: falta la cadena del ciclo mutuo" >&2
    cat "$tmp/out" >&2
    exit 1
fi

cat >"$tmp/byfield.pengu" <<'PENGU3'
rune A fundere B:
    x as int

rune B:
    a as A
    y as int
PENGU3

if "$PSC" check "$tmp/byfield.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: un embed que contiene al host por valor debería ser E0050" >&2
    exit 1
fi
if ! grep -q "has infinite size: A -> B -> A" "$tmp/out"; then
    echo "FAIL: falta la cadena del ciclo por campo" >&2
    cat "$tmp/out" >&2
    exit 1
fi

cat >"$tmp/ok.pengu" <<'PENGU4'
rune A fundere B:
    x as int

rune B:
    a as ref to A
    y as int

weave main into int:
    return 0
PENGU4

if ! "$PSC" check "$tmp/ok.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: 'ref to' debería romper el ciclo" >&2
    cat "$tmp/out" >&2
    exit 1
fi

echo "OK fundere tamaño finito"
