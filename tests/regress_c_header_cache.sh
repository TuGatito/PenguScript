#!/usr/bin/env bash
# Regresión: la caché de `psc build` incluye los headers/C del proyecto; tras
# editar `include/val.h` el binario se recompila (bug 20).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src" "$tmp/include" "$tmp/c"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "c_header_cache"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
src_dir = "src"
include_dir = "include"
c_dir = "c"
cc = "gcc"
TOML
cat >"$tmp/src/main.pengu" <<'PENGU'
include "val.h"
import std.spark
declare val into int
weave main into int:
    calling spark.println with "{calling val}"
    return 0
PENGU
printf '#include "val.h"\nint val(void) { return VAL; }\n' >"$tmp/c/val.c"
printf '#define VAL 1\n' >"$tmp/include/val.h"
out1="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: build inicial"; echo "$out1"; exit 1; }
[ "$out1" = "1" ] || { echo "FAIL: imprimió '$out1' (esperado 1)"; exit 1; }
sleep 1
printf '#define VAL 2\n' >"$tmp/include/val.h"
out2="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: build tras editar el header"; echo "$out2"; exit 1; }
[ "$out2" = "2" ] || { echo "FAIL: caché reutilizó el binario viejo ('$out2', esperado 2)"; exit 1; }
echo "OK c header cache"
