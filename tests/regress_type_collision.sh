#!/usr/bin/env bash
# Regresión: un tipo nominal local con el mismo nombre que uno importado no
# comparte struct C (bug 17).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "type_collision"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
src_dir = "src"
cc = "gcc"
TOML
cat >"$tmp/src/a.pengu" <<'PENGU'
rune Handler:
    invoke as int
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import a
rune Handler:
    local as int
weave take with h as ref to Handler into int:
    return h->local
weave main into int:
    var h as Handler is with local is 3
    calling spark.println with "{calling take with sigil of h}"
    return 0
PENGU
out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: colisión de tipos no compila"; echo "$out"; exit 1; }
[ "$out" = "3" ] || { echo "FAIL: imprimió '$out' (esperado 3)"; exit 1; }
echo "OK type collision"
