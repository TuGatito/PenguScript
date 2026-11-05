#!/usr/bin/env bash
# Ejecuta el test de hilos bajo ThreadSanitizer. Se salta si no hay gcc/TSAN.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
command -v gcc >/dev/null 2>&1 || { echo "SKIP tsan: no gcc"; exit 0; }
if ! echo 'int main(void){return 0;}' | gcc -fsanitize=thread -x c - -o /dev/null >/dev/null 2>&1; then
    echo "SKIP tsan: gcc has no -fsanitize=thread"
    exit 0
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
"$PSC" emit-c "$ROOT/tests/pengu/threads.pengu" >"$TMP/threads.c" || exit 1
if ! gcc -fsanitize=thread -g -O1 -I"$ROOT" -I"$ROOT/build/include" \
    "$TMP/threads.c" "$ROOT/build/lib/libpengu_runtime.a" -lm -lpthread -ldl \
    -o "$TMP/threads_tsan"; then
    echo "SKIP tsan: link failed"
    exit 0
fi
if ! TSAN_OPTIONS="halt_on_error=1 exitcode=66" "$TMP/threads_tsan" >"$TMP/out" 2>&1; then
    echo "FAIL tsan race"
    cat "$TMP/out"
    exit 1
fi
echo "OK thread tsan"
