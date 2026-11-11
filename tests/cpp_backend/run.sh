#!/usr/bin/env bash
# Gate del backend C++ (F0.3): `psc emit-c --backend=cpp` sobre el propio
# compilador debe producir un bundle que `g++` acepte sin errores.
#
# No enlaza ni ejecuta: comprueba la *sintaxis* del C++ emitido contra
# `build/include` (runtime C) y el árbol del repo.  El objetivo es que el
# emisor C++ no derive en silencio mientras se trabaja en el backend C.
#
# Uso: bash tests/cpp_backend/run.sh        (PSC=... CXX=... para overrides)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1

PSC="${PSC:-$ROOT/build/psc}"
CXX="${CXX:-g++}"

if [ ! -x "$PSC" ]; then
    echo "FAIL cpp_backend: no compiler at $PSC (run ./tools/build_bootstrap.sh)" >&2
    exit 1
fi
if ! command -v "$CXX" >/dev/null 2>&1; then
    echo "FAIL cpp_backend: no C++ compiler '$CXX' in PATH" >&2
    exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

if ! "$PSC" emit-c src/main.pengu --backend=cpp --out="$tmp/psc.cpp" >"$tmp/emit.log" 2>&1; then
    echo "FAIL cpp_backend: emit-c --backend=cpp failed" >&2
    tail -20 "$tmp/emit.log" >&2
    exit 1
fi
if [ ! -s "$tmp/psc.cpp" ]; then
    echo "FAIL cpp_backend: emit-c --backend=cpp produced an empty bundle" >&2
    exit 1
fi

"$CXX" -std=gnu++20 -fsyntax-only -I"$ROOT/build/include" -I"$ROOT" "$tmp/psc.cpp" \
    >"$tmp/cxx.log" 2>&1
status=$?

errors="$(grep -c 'error:' "$tmp/cxx.log" || true)"
lines="$(wc -l < "$tmp/psc.cpp" | tr -d ' ')"

if [ "$status" -ne 0 ] || [ "$errors" -ne 0 ]; then
    echo "FAIL cpp_backend: $errors g++ error(s) in the C++ bundle ($lines lines)" >&2
    grep 'error:' "$tmp/cxx.log" | head -40 >&2
    exit 1
fi

echo "OK cpp_backend ($lines lines, 0 errors)"
