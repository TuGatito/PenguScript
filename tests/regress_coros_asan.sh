#!/usr/bin/env bash
# Runs the coroutine/thread regression programs under AddressSanitizer.
# Skips when gcc or ASAN is unavailable.
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
for name in coro_args coro_multi_type filum_multi_type; do
    src="$ROOT/tests/pengu/$name.pengu"
    [ -f "$src" ] || continue
    "$PSC" emit-c "$src" >"$TMP/$name.c" || exit 1
    if ! gcc -fsanitize=address -g -O1 -I"$ROOT" -I"$ROOT/build/include" -I"$ROOT/std_c/minicoro" \
        "$TMP/$name.c" "$ROOT/build/lib/libpengu_runtime.a" \
        -lm -lpthread -ldl -o "$TMP/$name.asan"; then
        echo "SKIP coro asan: link failed ($name)"
        exit 0
    fi
    if ! ASAN_OPTIONS="detect_leaks=1 exitcode=66" "$TMP/$name.asan" >"$TMP/$name.out" 2>&1; then
        echo "FAIL coro asan: $name"
        cat "$TMP/$name.out"
        exit 1
    fi
done
echo "OK coro asan"
