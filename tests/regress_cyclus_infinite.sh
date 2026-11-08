#!/usr/bin/env bash
# `cyclus` no exime del chequeo de tamaño: un campo del propio tipo por valor
# sigue siendo E0050.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/bad.pengu" <<'PENGU1'
rune Node cyclus:
    next as Node
    value as int
PENGU1

if "$PSC" check "$tmp/bad.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: 'cyclus' con un campo del propio tipo debería ser E0050" >&2
    exit 1
fi
if ! grep -q "error\[E0050\]: type 'Node' has infinite size: Node -> Node" "$tmp/out"; then
    echo "FAIL: falta el diagnóstico de tamaño infinito" >&2
    cat "$tmp/out" >&2
    exit 1
fi
if ! grep -q "help: Break the cycle with 'ref to Node'" "$tmp/out"; then
    echo "FAIL: falta la ayuda con la indirección" >&2
    cat "$tmp/out" >&2
    exit 1
fi

cat >"$tmp/ok.pengu" <<'PENGU2'
rune Node cyclus:
    value as int
    next as maybe ref to Node

weave main into int:
    return 0
PENGU2

if ! "$PSC" check "$tmp/ok.pengu" >"$tmp/out" 2>&1; then
    echo "FAIL: 'maybe ref to' debería romper el ciclo" >&2
    cat "$tmp/out" >&2
    exit 1
fi

echo "OK cyclus tamaño finito"
