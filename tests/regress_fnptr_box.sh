#!/usr/bin/env bash
# Regresión: un puntero a función dentro de `maybe`/`result` se boxea sin
# declarar variables con tipo de puntero a función (C inválido).
set -u
PSC="${PSC:-$(cd "$(dirname "$0")/.." && pwd)/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/src"
cat > "$WORK/pengu.toml" <<'TOML'
[project]
name = "fnptr_box"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
cflags = ["-Wall", "-Werror"]
TOML
cat > "$WORK/src/main.pengu" <<'PENGU'
import std.spark

weave cb with x as int into int:
    return x + 1

weave main into int:
    var m as maybe weave with x as int into int is some (cb)
    let f as weave with x as int into int is m.value
    var r as result of weave with x as int into int to string is calling ok_of with cb
    let g as weave with x as int into int is r.value
    let a as int is calling f with 41
    let b as int is calling g with 1
    calling spark.println with "{a}-{b}"
    return 0
PENGU

OUT="$(cd "$WORK" && "$PSC" run src/main.pengu 2>&1)"
if [ "$OUT" != "42-2" ]; then
    echo "FAIL: se esperaba 42-2, se obtuvo: $OUT"
    exit 1
fi
echo "OK fnptr box"
