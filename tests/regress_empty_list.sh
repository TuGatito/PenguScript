#!/usr/bin/env bash
# Regresión: una lista vacía `[]` no debe emitir una variable temporal sin usar.
# El proyecto compila con -Wall -Werror, así que el aviso rompería el build.
set -u
PSC="${PSC:-$(cd "$(dirname "$0")/.." && pwd)/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/src"
cat > "$WORK/pengu.toml" <<'TOML'
[project]
name = "empty_list"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
cflags = ["-Wall", "-Werror"]
TOML
cat > "$WORK/src/main.pengu" <<'PENGU'
import std.spark

weave main into int:
    var xs as list of int is []
    calling xs.push with 7
    calling spark.println with "{xs.len}"
    return 0
PENGU

OUT="$(cd "$WORK" && "$PSC" run src/main.pengu 2>&1)"
if [ "$OUT" != "1" ]; then
    echo "FAIL: se esperaba 1, se obtuvo: $OUT"
    exit 1
fi
echo "OK empty list"
