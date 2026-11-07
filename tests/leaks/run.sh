#!/usr/bin/env bash
# Gate de fugas: compila cada programa con ASan y exige cero leaks.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
cd "$ROOT" || exit 1
if [ ! -x "$PSC" ]; then
  echo "leaks: $PSC no existe; construí el compilador primero" >&2
  exit 1
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail=0
count=0
for f in tests/leaks/l*.pengu; do
  [ -e "$f" ] || continue
  n="$(basename "$f" .pengu)"
  count=$((count+1))
  if ! "$PSC" build "$f" --out "$tmp/$n" --no-cache --sanitize=address > "$tmp/$n.build" 2>&1; then
    echo "FAIL $n: build"
    tail -5 "$tmp/$n.build"
    fail=$((fail+1))
    continue
  fi
  if ! ASAN_OPTIONS=detect_leaks=1 "$tmp/$n" > "$tmp/$n.out" 2>&1; then
    if grep -q "LeakSanitizer" "$tmp/$n.out"; then
      echo "FAIL $n: fuga de memoria"
      grep -E "SUMMARY|Direct leak|Indirect leak" "$tmp/$n.out" | head -4
    else
      echo "FAIL $n: salida no cero"
      tail -5 "$tmp/$n.out"
    fi
    fail=$((fail+1))
    continue
  fi
done
if [ "$fail" -ne 0 ]; then
  echo "$fail of $count leak test(s) failed"
  exit 1
fi
echo "OK $count leak test(s)"
