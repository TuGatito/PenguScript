#!/usr/bin/env bash
# Regresión: los métodos de un tipo reexportado con `alias` se resuelven
# también cuando el receptor es `ref to Alias` (antes solo funcionaba por
# valor: la resolución desenvolvía el `ref` pero no volvía a resolver el alias).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/src/demo"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "ref_alias_method"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
include_dir = "include"
cc = "gcc"
cflags = ["-Wall"]
TOML
cat >"$tmp/src/demo/core.pengu" <<'PENGU'
rune Widget:
    name as string

enchanting Widget:
    weave label with suffix as string into string:
        return "{self->name}{suffix}"

weave make_widget with label as string into Widget:
    return with name is label
PENGU
cat >"$tmp/src/demo.pengu" <<'PENGU'
import demo.core

alias Widget as demo.core.Widget

weave probe with w as ref to Widget into string:
    return calling w.label with "!"
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import demo

weave main into int:
    var w as demo.Widget is calling demo.core.make_widget with "portus"
    calling spark.println with "{calling demo.probe with sigil of w}"
    return 0
PENGU

out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: método sobre ref to alias no resuelve"; echo "$out"; exit 1; }
[ "$out" = "portus!" ] || { echo "FAIL: imprimió '$out' (esperado portus!)"; echo "$out"; exit 1; }
echo "OK ref alias method"
