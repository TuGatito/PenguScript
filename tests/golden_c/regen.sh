#!/usr/bin/env bash
# Regenera los .c y .out de los goldens. Usar SOLO tras un cambio de codegen
# intencional, y revisar el diff antes de commitear.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
cd "$ROOT"
for f in tests/golden_c/g*.pengu; do
  n="$(basename "$f" .pengu)"
  "$PSC" emit-c "$f" > "tests/golden_c/$n.c"
  "$PSC" run "$f" --no-cache > "tests/golden_c/$n.out"
done
echo "regenerados $(ls tests/golden_c/g*.c | wc -l) goldens"
