#!/usr/bin/env bash
# Verifica la emisión multi-TU (`emit-c --split-dir`): una cabecera, core y una
# unidad por módulo; se compilan por separado, se enlazan y el binario corre.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
CC="${CC:-cc}"

for cmd in "$CC"; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "SKIP: $cmd no disponible"; exit 0; }
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

mkdir -p "$work/proj/src"
cat > "$work/proj/pengu.toml" <<'TOML'
[build]
name = "split"
entry = "src/main.pengu"
TOML
cat > "$work/proj/src/main.pengu" <<'PENGU'
import std.spark

weave main into int:
    calling println with "split-ok"
    return 0
PENGU

"$PSC" emit-c "$work/proj/src/main.pengu" --split-dir="$work/out" >/dev/null
test -f "$work/out/bundle.h"
test -f "$work/out/core.c"
test "$(ls "$work"/out/u*.c | wc -l)" -ge 1

incflags=(-I"$ROOT/build/include" -I"$ROOT/std_c" -I"$ROOT/std_c/sds")
objs=()
for src in "$work"/out/*.c; do
  obj="${src%.c}.o"
  "$CC" -std=c11 -O0 -c "$src" "${incflags[@]}" -o "$obj"
  objs+=("$obj")
done

"$CC" "${objs[@]}" -o "$work/app" -L"$ROOT/build/lib" -lpengu_runtime -lm -pthread -ldl
out="$("$work/app")"
test "$out" = "split-ok"

# El driver también sabe emitir y compilar unidades en paralelo.
"$PSC" build "$work/proj" --split-codegen --jobs=2 --no-cache --out="$work/app2" >/dev/null
out2="$("$work/app2")"
test "$out2" = "split-ok"
echo "OK split units"
