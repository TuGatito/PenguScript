#!/usr/bin/env bash
# Regresión: un local llamado como una keyword de C (`double`) se emite con
# el nombre mangleado que registró el scope C.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/c_keyword.pengu" <<'PENGU'
import std.spark

weave main into int:
    let double as weave with x as int into int is lambda x as int into x * 2
    let n as int is calling double with 21
    calling spark.println with "{n}"
    return 0
PENGU
out="$("$PSC" run "$tmp/c_keyword.pengu" 2>&1)" || { echo "FAIL: local con keyword de C no compila"; echo "$out"; exit 1; }
[ "$out" = "42" ] || { echo "FAIL: local con keyword de C imprime '$out' (esperado 42)"; exit 1; }
echo "OK c keyword"
