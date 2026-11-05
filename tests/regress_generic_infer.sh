#!/usr/bin/env bash
# Regresión: una llamada a una función genérica sin `of T` debe resolver (o
# crear) la especialización inferida por los argumentos. Antes, si la plantilla
# vivía en el mismo módulo que la llamada, se emitía el nombre base.
set -u
PSC="${PSC:-$(cd "$(dirname "$0")/.." && pwd)/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/src"
cat > "$WORK/pengu.toml" <<'TOML'
[project]
name = "generic_infer"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
cflags = ["-Wall", "-Werror"]
TOML
cat > "$WORK/src/main.pengu" <<'PENGU'
import std.spark

weave keys shard V with m as map of string to V into list of string:
    var ks as list of string is list of string
    for k in m:
        calling ks.push with k
    return ks

weave count_keys with m as map of string to bool into int:
    var ks as list of string is calling keys with m
    return ks.len

weave main into int:
    var m as map of string to bool is map of string to bool
    calling m.put with "a", true
    calling m.put with "b", false
    calling spark.println with "{calling count_keys with m}"
    return 0
PENGU

OUT="$(cd "$WORK" && "$PSC" run src/main.pengu 2>&1)"
if [ "$OUT" != "2" ]; then
    echo "FAIL: se esperaba 2, se obtuvo: $OUT"
    exit 1
fi
echo "OK generic infer"
