#!/usr/bin/env bash
# Regresión: llamar a un método a través de un campo que ya es `ref` no debe
# pasar la dirección del puntero (`T**`) sino el puntero.
set -u
PSC="${PSC:-$(cd "$(dirname "$0")/.." && pwd)/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/src"
cat > "$WORK/pengu.toml" <<'TOML'
[project]
name = "ref_field_method"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
cflags = ["-Wall", "-Werror"]
TOML
cat > "$WORK/src/main.pengu" <<'PENGU'
import std.spark

rune Inner:
    value as int

rune Outer:
    inner as ref to Inner

enchanting Inner:
    weave doubled into int:
        return self->value * 2

weave probe with outer as ref to Outer into int:
    return calling outer->inner.doubled

weave main into int:
    var inner as Inner is with value is 21
    var outer as Outer is with inner is sigil of inner
    calling spark.println with "{calling probe with sigil of outer}"
    return 0
PENGU

OUT="$(cd "$WORK" && "$PSC" run src/main.pengu 2>&1)"
if [ "$OUT" != "42" ]; then
    echo "FAIL: se esperaba 42, se obtuvo: $OUT"
    exit 1
fi
echo "OK ref field method"
