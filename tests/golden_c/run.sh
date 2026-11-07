#!/usr/bin/env bash
# Golden C tests: fija el C emitido y verifica que compila y corre igual.
#
# Para cada tests/golden_c/gNN_*.pengu:
#   1. `psc emit-c` debe coincidir byte a byte con el .c versionado;
#   2. el .c debe compilar con `-std=c11 -pedantic -Wall -Wextra -Werror`;
#   3. el binario debe imprimir exactamente el .out versionado.
#
# Regenerar tras un cambio intencional de codegen:
#   tests/golden_c/regen.sh
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
CC="${CC:-cc}"
cd "$ROOT" || exit 1
if [ ! -x "$PSC" ]; then
  echo "golden_c: $PSC no existe; construí el compilador primero" >&2
  exit 1
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail=0
count=0
for f in tests/golden_c/g*.pengu; do
  [ -e "$f" ] || continue
  n="$(basename "$f" .pengu)"
  count=$((count+1))
  if ! "$PSC" emit-c "$f" > "$tmp/$n.c" 2> "$tmp/$n.err"; then
    echo "FAIL $n: emit-c"
    tail -5 "$tmp/$n.err"
    fail=$((fail+1))
    continue
  fi
  if ! diff -u "tests/golden_c/$n.c" "$tmp/$n.c" > "$tmp/$n.diff"; then
    echo "FAIL $n: el C emitido cambió (regenerá con tests/golden_c/regen.sh)"
    head -20 "$tmp/$n.diff"
    fail=$((fail+1))
    continue
  fi
  if ! "$CC" -std=c11 -pedantic -Wall -Wextra -Werror \
      -DPENGU_ENABLE_THREADS=0 \
      -I"$ROOT/build/include" -I"$ROOT/std_c" -I"$ROOT/std_c/sds" -I"$ROOT/build" \
      "$tmp/$n.c" -L"$ROOT/build/lib" -lpengu_runtime -lminiz -lre -lm -pthread -ldl \
      -o "$tmp/$n.bin" 2> "$tmp/$n.cc"; then
    echo "FAIL $n: el C no compila con -std=c11 -pedantic -Werror"
    head -20 "$tmp/$n.cc"
    fail=$((fail+1))
    continue
  fi
  "$tmp/$n.bin" > "$tmp/$n.out" 2>&1
  if ! diff -u "tests/golden_c/$n.out" "$tmp/$n.out"; then
    echo "FAIL $n: la salida no coincide"
    fail=$((fail+1))
  fi
done
if [ "$fail" -ne 0 ]; then
  echo "$fail of $count golden(s) failed"
  exit 1
fi
echo "OK $count golden C test(s)"
