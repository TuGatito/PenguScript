#!/usr/bin/env bash
# Verifica que las líneas PenguScript con código tengan entradas en la tabla
# de líneas de DWARF y que el wrapper C `main` no se atribuya al fuente.
#
# Requiere gdb; se salta si no está instalado (macOS suele traer lldb).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
GDB="${GDB:-gdb}"
if ! command -v "$GDB" >/dev/null 2>&1; then
  echo "debug: gdb no disponible; test omitido"
  exit 0
fi
if [ ! -x "$PSC" ]; then
  echo "debug: $PSC no existe; construí el compilador primero" >&2
  exit 1
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
src="$ROOT/tests/debug/line_markers.pengu"
if ! "$PSC" build "$src" --profile=debug --no-cache --out="$tmp/app" >"$tmp/build.log" 2>&1; then
  echo "debug: falló la compilación"
  tail -20 "$tmp/build.log"
  exit 1
fi
fail=0
for line in 5 6 7 8 9 10 11 12; do
  out="$(LC_ALL=C "$GDB" -q -batch \
    -ex "set debuginfod enabled off" \
    -ex "info line $src:$line" \
    "$tmp/app" 2>&1)"
  if ! grep -q "starts at address" <<<"$out"; then
    echo "FAIL línea $line sin entrada en la tabla de líneas"
    echo "$out" | tail -3
    fail=$((fail+1))
  fi
done
out="$(LC_ALL=C "$GDB" -q -batch \
  -ex "set debuginfod enabled off" \
  -ex "info line *main" \
  "$tmp/app" 2>&1)"
if ! grep -q '<psc-runtime>' <<<"$out"; then
  echo "FAIL el wrapper main no está marcado como <psc-runtime>"
  echo "$out" | tail -3
  fail=$((fail+1))
fi
if [ "$fail" -ne 0 ]; then
  echo "$fail comprobación(es) de líneas fallaron"
  exit 1
fi
echo "OK debug line markers"

if command -v python3 >/dev/null 2>&1; then
  if ! python3 "$ROOT/tests/debug/dap_smoke.py" \
      --psc "$PSC" --program "$tmp/app" --source "$src"; then
    echo "FAIL debug DAP smoke"
    exit 1
  fi
else
  echo "debug: python3 no disponible; DAP smoke omitido"
fi
