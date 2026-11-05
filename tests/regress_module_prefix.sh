#!/usr/bin/env bash
# Regresión: un módulo cuyo stem termina en `route` no comparte scope con
# `route.pengu` (el slice del path perdía la última letra; bug 14).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src/portus"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "module_prefix"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
src_dir = "src"
cc = "gcc"
TOML
cat >"$tmp/src/portus/route.pengu" <<'PENGU'
weave with_prefix with p as string into string:
    return "route:{p}"
PENGU
cat >"$tmp/src/portus/router.pengu" <<'PENGU'
import portus.route
weave with_prefix with p as string into string:
    return "router:{p}"
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import portus.router
weave main into int:
    calling spark.println with (calling portus.router.with_prefix with "x")
    return 0
PENGU
out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: módulo router no compila"; echo "$out"; exit 1; }
[ "$out" = "router:x" ] || { echo "FAIL: imprimió '$out' (esperado router:x)"; exit 1; }
echo "OK module prefix"
