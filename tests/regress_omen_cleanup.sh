#!/usr/bin/env bash
# Regresión: `_pengu_cleanup_<omen>` debe liberar el payload de la variante
# activa (antes el emisor del switch era código muerto y ningún omen liberaba
# nada; P0-b de la auditoría de derive Json).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in
  /*) ;;
  *) PSC="$(cd "$(dirname "$PSC")" && pwd)/$(basename "$PSC")" ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/omen_cleanup.pengu" <<'PENGU'
import std.spark
omen Shape derive Nexus, Par:
    Empty
    Named with name as string
    Item with tags as list of string
weave main into int:
    var s as Shape is with Item is ["a", "b"]
    banish s
    var n as Shape is with Named is "x"
    banish n
    var e as Shape is Empty
    banish e
    calling spark.println with "cleanup-ok"
    return 0
PENGU

out="$(cd "$tmp" && "$PSC" run omen_cleanup.pengu 2>&1)" \
  || { echo "FAIL: el omen con payload no compila/ejecuta"; echo "$out"; exit 1; }
[ "$out" = "cleanup-ok" ] || { echo "FAIL: imprimió '$out'"; exit 1; }

"$PSC" emit-c "$tmp/omen_cleanup.pengu" >"$tmp/bundle.c" 2>/dev/null \
  || { echo "FAIL: emit-c falló"; exit 1; }
grep -q "case Shape_Named:" "$tmp/bundle.c" \
  || { echo "FAIL: falta el case del payload string"; exit 1; }
grep -q "pengu_banish_string(&(p->data.Named.name));" "$tmp/bundle.c" \
  || { echo "FAIL: el payload string no se libera"; exit 1; }
grep -q "pengu_banish_list(&(p->data.Item.tags));" "$tmp/bundle.c" \
  || { echo "FAIL: el payload list no se libera"; exit 1; }

if command -v gcc >/dev/null 2>&1; then
  (cd "$tmp" && "$PSC" build omen_cleanup.pengu --out="$tmp/app" >/dev/null 2>&1) \
    || { echo "FAIL: build normal falló"; exit 1; }
  gcc -fsanitize=address -g -O1 -I "$ROOT/build/include" -I "$ROOT/std_c" -I "$ROOT/std_c/sds" -I "$tmp" \
    "$tmp/build/bundle.c" -L "$ROOT/build/lib" -lpengu_runtime -lminiz -lre -lm -pthread -ldl \
    -o "$tmp/app_asan" 2>/dev/null \
    || { echo "FAIL: no se pudo compilar con ASAN"; exit 1; }
  asan_out="$("$tmp/app_asan" 2>&1)"
  if printf '%s' "$asan_out" | grep -qE 'LeakSanitizer|detected memory leaks|double-free|AddressSanitizer'; then
    echo "FAIL: ASAN detectó un problema en el cleanup del omen"
    printf '%s\n' "$asan_out" | head -20
    exit 1
  fi
fi
echo "OK omen cleanup"
