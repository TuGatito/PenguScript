#!/usr/bin/env bash
# Ejecuta una corrutina bajo ThreadSanitizer. Se salta si no hay gcc/TSAN.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
command -v gcc >/dev/null 2>&1 || { echo "SKIP coro tsan: no gcc"; exit 0; }
if ! echo 'int main(void){return 0;}' | gcc -fsanitize=thread -x c - -o /dev/null >/dev/null 2>&1; then
    echo "SKIP coro tsan: gcc has no -fsanitize=thread"
    exit 0
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
"$PSC" emit-c "$ROOT/tests/pengu/coro_basic.pengu" >"$TMP/coro.c" || exit 1
if ! gcc -fsanitize=thread -g -O1 -I"$ROOT" -I"$ROOT/build/include" -I"$ROOT/std_c/minicoro" \
    "$TMP/coro.c" "$ROOT/runtime/pengu_coro.c" "$ROOT/build/lib/libpengu_runtime.a" \
    -lm -lpthread -ldl -o "$TMP/coro_tsan"; then
    echo "SKIP coro tsan: link failed"
    exit 0
fi
if ! TSAN_OPTIONS="halt_on_error=1 exitcode=66" "$TMP/coro_tsan" >"$TMP/out" 2>&1; then
    echo "FAIL coro tsan"
    cat "$TMP/out"
    exit 1
fi
echo "OK coro tsan"
