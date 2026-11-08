#!/usr/bin/env bash
# P1 (0.53.1): copiar un `string` owned ya no comparte el SDS. El binding
# copiado recibe su propio buffer (`pengu_string_share_value`) y cada `banish`
# libera lo suyo; un campo leido sigue siendo una vista. El programa debe
# quedar limpio bajo ASan.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat >"$TMP/copy.pengu" <<'PENGU'
rune Holder:
    name as string

weave main into int:
    var a as string is "hola" + " mundo"
    var b as string is a
    banish a
    banish b
    set b is b + "!"
    banish b
    var h as Holder is with name is ("cam" + "po")
    if h.name != "campo":
        return 1
    banish h.name
    return 0
PENGU

if ! "$PSC" emit-c "$TMP/copy.pengu" > "$TMP/copy.c" 2> "$TMP/emit.log"; then
  echo "FAIL cow legacy: emit-c falló"
  head -20 "$TMP/emit.log"
  exit 1
fi
if ! grep -q "pengu_string_share_value(a)" "$TMP/copy.c"; then
  echo "FAIL cow legacy: falta la copia propia del binding copiado"
  exit 1
fi
if ! grep -q "pengu_banish_string(&(b));" "$TMP/copy.c"; then
  echo "FAIL cow legacy: falta liberar el valor anterior del set"
  exit 1
fi

if ! "$PSC" build "$TMP/copy.pengu" --out "$TMP/copy" --no-cache \
    --sanitize=address > "$TMP/build.log" 2>&1; then
  echo "FAIL cow legacy: no compila"
  head -20 "$TMP/build.log"
  exit 1
fi
if ! ASAN_OPTIONS=detect_leaks=1 "$TMP/copy" > "$TMP/run.log" 2>&1; then
  echo "FAIL cow legacy: ASan se quejó"
  cat "$TMP/run.log"
  exit 1
fi

echo "OK cow legacy string"
