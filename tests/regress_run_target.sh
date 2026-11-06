#!/usr/bin/env bash
# Regresión B-01/B-02/B-13: `psc run`/`psc test` respetan el target resuelto
# del manifiesto y propagan el exit code del programa (sin fallback silencioso
# a Chromium que convertía un fallo en 0).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in /*) ;; *) PSC="$ROOT/$PSC" ;; esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"

cat >"$tmp/pengu.toml" <<'TOML'
[build]
name = "run_native"
entry = "src/main.pengu"
TOML
cat >"$tmp/src/main.pengu" <<'PENGU'
weave main into int:
    return 7
PENGU
( cd "$tmp" && "$PSC" run . --no-cache >/dev/null 2>&1 ); code=$?
[ "$code" = 7 ] || { echo "FAIL: nativo devolvió $code (esperado 7)"; exit 1; }

if ! command -v emcc >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1 || [ ! -f "$ROOT/build/wasm/lib/libpengu_runtime.a" ]; then
    echo "OK run target (wasm omitido: falta emcc/node/runtime)"
    exit 0
fi

mkdir -p "$tmp/wasm/src"
cat >"$tmp/wasm/pengu.toml" <<'TOML'
[build]
name = "run_wasm"
entry = "src/main.pengu"
target = "wasm32-unknown-emscripten"
TOML
cat >"$tmp/wasm/src/main.pengu" <<'PENGU'
weave main into int:
    return 3
PENGU

# El manifiesto resuelve wasm: debe ejecutar el .js con Node, no intentar
# ejecutar el .html (127) ni caer a Chromium (0).
( cd "$tmp/wasm" && "$PSC" run . --no-cache >/dev/null 2>&1 ); code=$?
[ "$code" = 3 ] || { echo "FAIL: wasm con manifiesto devolvió $code (esperado 3)"; exit 1; }

( cd "$tmp/wasm" && "$PSC" run . --no-cache --target wasm >/dev/null 2>&1 ); code=$?
[ "$code" = 3 ] || { echo "FAIL: wasm --target devolvió $code (esperado 3)"; exit 1; }

out="$( cd "$tmp/wasm" && "$PSC" test . --no-cache 2>&1 )"; code=$?
[ "$code" = 0 ] || { echo "FAIL: psc test wasm devolvió $code"; echo "$out"; exit 1; }
case "$out" in *"No tests to run"*) ;; *) echo "FAIL: psc test wasm no ejecutó el binario"; echo "$out"; exit 1;; esac

echo "OK run target y exit codes"
