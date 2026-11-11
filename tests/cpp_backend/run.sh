#!/usr/bin/env bash
# Gate del backend C++ (F0.3 + F1): `psc emit-c --backend=cpp` sobre el propio
# compilador debe producir un bundle que `g++` acepte sin errores y sin
# extensiones fuera de ISO C++20 (`-pedantic-errors`).
#
# Modos:
#   (sin modo)  compila el bundle del propio psc con -fsyntax-only.
#   --link      además enlaza el binario con el runtime C y exige que
#               `--version` responda y que la suite (`test .`) pase: el psc
#               auto-hospedado en C++ debe comportarse igual que el de C (F1).
#   --stage0    emite los tres bundles C++ (linux/macos/windows), comprueba que
#               son reproducibles y compila con -fsyntax-only los que no
#               dependen de headers del host (windows_x64 necesita un SDK de
#               Windows y solo se verifica la reproducibilidad).
#
# Uso: bash tests/cpp_backend/run.sh [--link|--stage0]   (PSC=... CXX=...)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1

PSC="${PSC:-$ROOT/build/psc}"
CXX="${CXX:-g++}"
MODE="${1:-}"

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

# -pedantic-errors: el bundle no debe usar extensiones GNU (literales
# compuestos, familias de arrays, etc.).  Los headers vendorizados del runtime
# (sds.h) van como -isystem: son C puro y sus extensiones no son parte del
# lenguaje emitido.
syntax_check() {
    local file="$1" log="$2"
    "$CXX" -std=c++20 -pedantic-errors -fsyntax-only \
        -isystem "$ROOT/build/include" -I"$ROOT" "$file" >"$log" 2>&1
}

if [ "$MODE" = "--stage0" ]; then
    stage="$tmp/stage0"
    mkdir -p "$stage"
    if ! bash "$ROOT/tools/gen_stage0.sh" --family=cpp --dir="$stage" >"$tmp/stage0.log" 2>&1; then
        echo "FAIL cpp_backend: --family=cpp stage0 generation failed" >&2
        tail -20 "$tmp/stage0.log" >&2
        exit 1
    fi
    if ! bash "$ROOT/tools/gen_stage0.sh" --family=cpp --dir="$stage" --check >"$tmp/stage0chk.log" 2>&1; then
        echo "FAIL cpp_backend: C++ stage0 bundles are not reproducible" >&2
        tail -20 "$tmp/stage0chk.log" >&2
        exit 1
    fi
    checked=0
    for f in "$stage"/*.cpp; do
        case "$f" in
            *windows*) continue ;;
        esac
        if ! syntax_check "$f" "$tmp/stage0cxx.log"; then
            echo "FAIL cpp_backend: $CXX rejects $(basename "$f")" >&2
            grep 'error:' "$tmp/stage0cxx.log" | head -20 >&2
            exit 1
        fi
        checked=$((checked + 1))
    done
    echo "OK cpp_backend stage0 (3 targets reproducible, $checked ISO C++20 checked)"
    exit 0
fi

if ! "$PSC" emit-c src/main.pengu --backend=cpp --out="$tmp/psc.cpp" >"$tmp/emit.log" 2>&1; then
    echo "FAIL cpp_backend: emit-c --backend=cpp failed" >&2
    tail -20 "$tmp/emit.log" >&2
    exit 1
fi
if [ ! -s "$tmp/psc.cpp" ]; then
    echo "FAIL cpp_backend: emit-c --backend=cpp produced an empty bundle" >&2
    exit 1
fi

syntax_check "$tmp/psc.cpp" "$tmp/cxx.log"
status=$?

errors="$(grep -c 'error:' "$tmp/cxx.log" || true)"
lines="$(wc -l < "$tmp/psc.cpp" | tr -d ' ')"

if [ "$status" -ne 0 ] || [ "$errors" -ne 0 ]; then
    echo "FAIL cpp_backend: $errors g++ error(s) in the C++ bundle ($lines lines)" >&2
    grep 'error:' "$tmp/cxx.log" | head -40 >&2
    exit 1
fi

echo "OK cpp_backend ($lines lines, 0 errors)"

if [ "$MODE" = "--link" ]; then
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
    suite="$("$tmp/psc_cpp" test . 2>&1 | tail -1)"
    case "$suite" in
        *"passed"*) ;;
        *) echo "FAIL cpp_backend: the C++-built psc failed the test suite: $suite" >&2; exit 1 ;;
    esac
    echo "OK cpp_backend link ($version, $suite)"
fi
