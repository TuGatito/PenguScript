#!/usr/bin/env bash
# Regresión: `padre.hijo.fn` dentro del propio módulo `padre` resuelve al
# módulo `padre.hijo`, no a la función local homónima (bug 8).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src/demo"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "module_chain"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
src_dir = "src"
cc = "gcc"
TOML
cat >"$tmp/src/demo/core.pengu" <<'PENGU'
weave default_options into int:
    return 7
PENGU
cat >"$tmp/src/demo.pengu" <<'PENGU'
import demo.core
weave default_options into int:
    return 1
weave run into int:
    return calling demo.core.default_options
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import demo
weave main into int:
    calling spark.println with "{calling demo.run}"
    return 0
PENGU
out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: llamada cualificada no compila"; echo "$out"; exit 1; }
[ "$out" = "7" ] || { echo "FAIL: imprimió '$out' (esperado 7)"; exit 1; }
echo "OK module chain"
