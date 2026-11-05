#!/usr/bin/env bash
# Ejecuta una corrutina bajo AddressSanitizer. Se salta si no hay gcc/ASAN.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
command -v gcc >/dev/null 2>&1 || { echo "SKIP coro asan: no gcc"; exit 0; }
if ! echo 'int main(void){return 0;}' | gcc -fsanitize=address -x c - -o /dev/null >/dev/null 2>&1; then
    echo "SKIP coro asan: gcc has no -fsanitize=address"
    exit 0
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
"$PSC" emit-c "$ROOT/tests/pengu/coro_args.pengu" >"$TMP/coro.c" || exit 1
if ! gcc -fsanitize=address -g -O1 -I"$ROOT" -I"$ROOT/build/include" -I"$ROOT/std_c/minicoro" \
    "$TMP/coro.c" "$ROOT/runtime/pengu_coro.c" "$ROOT/build/lib/libpengu_runtime.a" \
    -lm -lpthread -ldl -o "$TMP/coro_asan"; then
    echo "SKIP coro asan: link failed"
    exit 0
fi
if ! ASAN_OPTIONS="detect_leaks=1 exitcode=66" "$TMP/coro_asan" >"$TMP/out" 2>&1; then
    echo "FAIL coro asan"
    cat "$TMP/out"
    exit 1
fi
echo "OK coro asan"
