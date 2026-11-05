#!/usr/bin/env bash
# Regresión: `alias` de un tipo importado como retorno acepta el subyacente
# (bug 18; el caso del informe ya funcionaba en 0.28.9, se fija aquí).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "alias_return"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
src_dir = "src"
cc = "gcc"
TOML
cat >"$tmp/src/a.pengu" <<'PENGU'
rune Thing:
    n as int
weave make into Thing:
    return with n is 1
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import a
alias Wrapped as a.Thing
weave build into Wrapped:
    return calling a.make
weave main into int:
    var w as Wrapped is calling build
    calling spark.println with "{w.n}"
    return 0
PENGU
out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: alias en retorno no compila"; echo "$out"; exit 1; }
[ "$out" = "1" ] || { echo "FAIL: imprimió '$out' (esperado 1)"; exit 1; }
echo "OK alias return"
