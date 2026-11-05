#!/usr/bin/env bash
# Regresión: `if c then a else b` en posición de valor debe emitir el valor
# completo de cada rama. Antes el else se bajaba un nivel y `(n) to string`
# o `some "x"` se emitían sin la conversión / sin la caja.
set -u
PSC="${PSC:-$(cd "$(dirname "$0")/.." && pwd)/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/src"
cat > "$WORK/pengu.toml" <<'TOML'
[project]
name = "if_expr_value"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
cflags = ["-Wall", "-Werror"]
TOML
cat > "$WORK/src/main.pengu" <<'PENGU'
import std.spark

weave pad with n as int into string:
    return if n < 10 then "0{(n) to string}" else (n) to string

weave pick with flag as bool, t as maybe string into maybe string:
    return if flag then t else some "/tmp"

weave main into int:
    let a as string is calling pad with 4
    let b as string is calling pad with 12
    let c as maybe string is calling pick with true, (some "x")
    let d as maybe string is calling pick with false, (maybe none)
    if ds as string is d:
        calling spark.println with "{a} {b} {c.is_present} {ds}"
    banish a
    banish b
    return 0
PENGU

OUT="$(cd "$WORK" && "$PSC" run src/main.pengu 2>&1)"
if [ "$OUT" != "04 12 true /tmp" ]; then
    echo "FAIL: se esperaba '04 12 true /tmp', se obtuvo: $OUT"
    exit 1
fi
echo "OK if expr value"
