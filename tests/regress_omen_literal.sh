#!/usr/bin/env bash
# Regresión: `return with Variante is campo` debe cerrar el literal compuesto
# del omen (tras el cambio de escapes de interpolación `"}}"` emite una sola
# llave y faltaba el cierre).
set -u
PSC="${PSC:-$(cd "$(dirname "$0")/.." && pwd)/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/src"
cat > "$WORK/pengu.toml" <<'TOML'
[project]
name = "omen_literal"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
cflags = ["-Wall", "-Werror"]
TOML
cat > "$WORK/src/main.pengu" <<'PENGU'
import std.spark

omen Value:
    Bool with b as bool
    Num with n as int

weave make_bool with b as bool into Value:
    return with Bool is b

weave main into int:
    let v as Value is calling make_bool with true
    judge v:
        when Bool with b ->
            calling spark.println with "bool={b}"
        when Num with n ->
            calling spark.println with "num={n}"
    return 0
PENGU

OUT="$(cd "$WORK" && "$PSC" run src/main.pengu 2>&1)"
if [ "$OUT" != "bool=true" ]; then
    echo "FAIL: se esperaba 'bool=true', se obtuvo: $OUT"
    exit 1
fi
echo "OK omen literal"
