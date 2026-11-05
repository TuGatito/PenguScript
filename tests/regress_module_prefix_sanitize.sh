#!/usr/bin/env bash
# Regresión: el prefijo de módulo del codegen debe ser un identificador C válido.
# Un archivo en `sub-dir/` generaba `sub-dir_app_main()` y gcc fallaba con
# `expected '=' ... before '-' token` (P0-a de la auditoría de derive Json).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in
  /*) ;;
  *) PSC="$(cd "$(dirname "$PSC")" && pwd)/$(basename "$PSC")" ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/mi-proyecto.v1/src/sub-dir" "$tmp/mi-proyecto.v1/src/9lives"
cat >"$tmp/mi-proyecto.v1/pengu.toml" <<'TOML'
[project]
name = "prefix_sanitize"
version = "0.1.0"
entry = "src/sub-dir/app.pengu"
output = "exe"
[build]
src_dir = "src"
cc = "gcc"
TOML
cat >"$tmp/mi-proyecto.v1/src/sub-dir/app.pengu" <<'PENGU'
import std.spark
weave helper with x as int into int:
    return x + 1
weave main into int:
    calling spark.println with "sub={calling helper with 1}"
    return 0
PENGU
cat >"$tmp/mi-proyecto.v1/src/9lives/app.pengu" <<'PENGU'
import std.spark
weave helper with x as int into int:
    return x + 2
weave main into int:
    calling spark.println with "nine={calling helper with 1}"
    return 0
PENGU

out="$(cd "$tmp/mi-proyecto.v1" && "$PSC" run src/sub-dir/app.pengu 2>&1)" \
  || { echo "FAIL: módulo en directorio con guión no compila"; echo "$out"; exit 1; }
[ "$out" = "sub=2" ] || { echo "FAIL: imprimió '$out' (esperado sub=2)"; exit 1; }

bundle="$tmp/mi-proyecto.v1/build/bundle.c"
[ -f "$bundle" ] || { echo "FAIL: no se generó build/bundle.c"; exit 1; }
grep -v '^#line ' "$bundle" | grep -q 'sub_dir_app_helper' \
  || { echo "FAIL: falta sub_dir_app_helper en el bundle"; exit 1; }
cp "$bundle" "$tmp/first.c"

out="$(cd "$tmp/mi-proyecto.v1" && "$PSC" run src/9lives/app.pengu 2>&1)" \
  || { echo "FAIL: módulo con dígito inicial no compila"; echo "$out"; exit 1; }
[ "$out" = "nine=3" ] || { echo "FAIL: imprimió '$out' (esperado nine=3)"; exit 1; }
grep -v '^#line ' "$bundle" | grep -q '_9lives_app_helper' \
  || { echo "FAIL: falta _9lives_app_helper en el bundle"; exit 1; }

for f in "$tmp/first.c" "$bundle"; do
  if grep -v '^#line ' "$f" | grep -qE '(^|[^A-Za-z0-9_])sub-dir_app_|(^|[^A-Za-z0-9_])9lives_app_'; then
    echo "FAIL: el bundle conserva identificadores C inválidos"
    exit 1
  fi
done
echo "OK module prefix sanitize"
