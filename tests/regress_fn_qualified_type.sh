#!/usr/bin/env bash
# Regresión: un tipo cualificado (mod.Type) dentro de un tipo de función debe
# emitir el tipo real, no el alias del módulo (antes: `void (*f)(js)`).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.web.dom as dom

alias E as dom.Element

weave make_el into E:
    var r as result of dom.Element to dom.JsError is calling dom.create with "div"
    return r.value

weave take_factory with f as (weave into E) into int:
    return 0

weave main into int:
    return calling take_factory with make_el
PENGU
"$PSC" build "$tmp/main.pengu" >/dev/null 2>&1 || { echo "FAIL: tipo cualificado en función no compila"; exit 1; }
echo "OK qualified fn type"
