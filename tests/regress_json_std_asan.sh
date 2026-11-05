#!/usr/bin/env bash
# Regresión: `std.json` libera y clona de verdad.
#
# - `JsonValue.free` libera el árbol completo (antes sólo liberaba el primer
#   nivel, porque el cleanup derivado era superficial).
# - `JsonValue.clone` es independiente (antes compartía los buffers).
# El caso se compila con ASAN y falla si hay fugas o dobles libres.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in
  /*) ;;
  *) PSC="$(cd "$(dirname "$PSC")" && pwd)/$(basename "$PSC")" ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

command -v gcc >/dev/null 2>&1 || { echo "SKIP json std asan (no gcc)"; exit 0; }

cat >"$tmp/deep.pengu" <<'PENGU'
import std.json

weave main into int:
    var text as string is "{\"a\":[1,\"x\",{\"b\":true}],\"c\":null,\"d\":[\"y\",\"z\"]}"
    var r as result of json.JsonValue to json.JsonError is calling json.parse with text
    if not r.is_ok:
        return 1
    var v as json.JsonValue is r.value
    banish r
    var copy as json.JsonValue is calling v.clone
    calling v.free
    var t2 as string is calling json.stringify with copy
    if t2 != text:
        return 2
    banish t2
    # `as_array` entrega una lista propia de copias; `free_values` las libera
    # y libera el buffer.
    var items as maybe list of json.JsonValue is calling copy.as_array
    if items.is_present:
        calling json.free_values with items.value
    banish items
    # Falla a mitad de un objeto grande: el decodificador debe limpiar lo ya
    # reservado sin fugas.
    var bad as result of json.JsonValue to json.JsonError is calling json.parse with "{\"a\":[1,2,3],\"b\":{\"c\":\"x\"},\"d\":"
    if bad.is_ok:
        return 3
    banish bad
    calling copy.free
    return 0
PENGU

(cd "$tmp" && "$PSC" build deep.pengu --out="$tmp/app" >/dev/null 2>&1) \
  || { echo "FAIL: no compila el fixture"; exit 1; }

gcc -fsanitize=address -g -O1 -I "$ROOT/build/include" -I "$ROOT/std_c" -I "$ROOT/std_c/sds" -I "$tmp/build" \
  "$tmp/build/bundle.c" -L "$ROOT/build/lib" -lpengu_runtime -lminiz -lre -lm -pthread -ldl \
  -o "$tmp/app_asan" 2>"$tmp/cc.err" \
  || { echo "FAIL: no se pudo compilar con ASAN"; cat "$tmp/cc.err"; exit 1; }

out="$("$tmp/app_asan" 2>&1)" || { echo "FAIL: el fixture falló"; printf '%s\n' "$out"; exit 1; }
if printf '%s' "$out" | grep -qE 'LeakSanitizer|detected memory leaks|double-free|AddressSanitizer'; then
  echo "FAIL: ASAN detectó un problema en std.json"
  printf '%s\n' "$out" | head -30
  exit 1
fi
echo "OK json std asan"
