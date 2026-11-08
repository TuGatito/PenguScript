#!/usr/bin/env bash
# Prueba unitaria del COW del runtime (fase 6): compila tests/cow/cow_runtime_test.c
# contra la libpengu_runtime y exige que todas las comprobaciones pasen.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CC="${CC:-cc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! "$CC" -std=c11 -pedantic -Wall -Wextra -Werror \
    -DPENGU_ENABLE_THREADS=0 \
    -I"$ROOT/build/include" -I"$ROOT/std_c" -I"$ROOT/std_c/sds" -I"$ROOT/build" \
    "$ROOT/tests/cow/cow_runtime_test.c" \
    -L"$ROOT/build/lib" -lpengu_runtime -lminiz -lre -lm -pthread -ldl \
    -o "$TMP/cow_runtime_test" 2> "$TMP/cc.log"; then
  echo "FAIL cow runtime: el test C no compila"
  head -20 "$TMP/cc.log"
  exit 1
fi

if ! "$TMP/cow_runtime_test" > "$TMP/out.log" 2>&1; then
  echo "FAIL cow runtime"
  cat "$TMP/out.log"
  exit 1
fi

echo "OK cow runtime"
