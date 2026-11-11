#!/usr/bin/env bash
# Gate del backend C++ (F0.3 + F1): `psc emit-c --backend=cpp` sobre el propio
# compilador debe producir un bundle que `g++` acepte sin errores y sin
# extensiones fuera de ISO C++20 (`-pedantic-errors`).
#
# No enlaza ni ejecuta: comprueba la *sintaxis* del C++ emitido contra
# `build/include` (runtime C) y el árbol del repo.  El objetivo es que el
# emisor C++ no derive en silencio mientras se trabaja en el backend C.
#
# Uso: bash tests/cpp_backend/run.sh [--link]
#   --link  además enlaza el binario con el runtime C y exige que `--version`
#           responda y que la suite (`test .`) pase: el psc auto-hospedado en
#           C++ debe comportarse igual que el compilado en C (F1).
#   PSC=... CXX=... para overrides.
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

# -pedantic-errors: el bundle no debe usar extensiones GNU (literales
# compuestos, familias de arrays, etc.).  Los headers vendorizados del runtime
# (sds.h) van como -isystem: son C puro y sus extensiones no son parte del
# lenguaje emitido.
"$CXX" -std=c++20 -pedantic-errors -fsyntax-only \
    -isystem "$ROOT/build/include" -I"$ROOT" "$tmp/psc.cpp" \
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

if [ "${1:-}" = "--link" ]; then
    if ! "$CXX" -std=c++20 -O0 -c "$tmp/psc.cpp" -o "$tmp/psc.o" \
            -isystem "$ROOT/build/include" -I"$ROOT" >"$tmp/obj.log" 2>&1; then
        echo "FAIL cpp_backend: $CXX could not compile the bundle to an object" >&2
        tail -20 "$tmp/obj.log" >&2
        exit 1
    fi
    if ! "$CXX" "$tmp/psc.o" \
            "$ROOT/build/lib/libpengu_runtime.a" \
            "$ROOT/build/lib/libminiz.a" "$ROOT/build/lib/libre.a" \
            -lm -pthread -ldl -o "$tmp/psc_cpp" >"$tmp/link.log" 2>&1; then
        echo "FAIL cpp_backend: link against the C runtime failed" >&2
        tail -20 "$tmp/link.log" >&2
        exit 1
    fi
    version="$("$tmp/psc_cpp" --version 2>&1 | head -1)"
    case "$version" in
        psc\ *) ;;
        *) echo "FAIL cpp_backend: unexpected --version output: $version" >&2; exit 1 ;;
    esac
    if ! "$tmp/psc_cpp" test . >"$tmp/test.log" 2>&1; then
        echo "FAIL cpp_backend: the C++-built psc failed the test suite" >&2
        tail -20 "$tmp/test.log" >&2
        exit 1
    fi
    echo "OK cpp_backend link ($version, $("$tmp/psc_cpp" test . 2>&1 | tail -1))"
fi
