#!/usr/bin/env bash
# La caché es por programa completo, pero con --verbose debe explicar qué
# módulo invalidó la clave. Sin esto, un miss de 20 s es opaco.
set -euo pipefail
PSC="${PSC:-./build/psc}"
case "$PSC" in /*) ;; *) PSC="$PWD/$PSC" ;; esac
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/proj/src"
cat > "$TMP/proj/pengu.toml" <<'TOML'
[build]
name = "explain"
entry = "src/main.pengu"
TOML
cat > "$TMP/proj/src/lib.pengu" <<'PENGU'
weave twice with n as int into int:
    return n * 2
PENGU
cat > "$TMP/proj/src/main.pengu" <<'PENGU'
import src.lib
import std.spark

weave main into int:
    calling spark.println with "hi"
    return 0
PENGU
export PSC_CACHE_DIR="$TMP/cache"
cd "$TMP/proj"
"$PSC" build . --verbose >/dev/null 2>&1
"$PSC" build . --verbose >"$TMP/warm.log" 2>&1
if grep -q "cache: module" "$TMP/warm.log"; then
    echo "FAIL: warm hit printed module changes" >&2
    exit 1
fi
printf '\n# changed\n' >> src/lib.pengu
"$PSC" build . --verbose >"$TMP/cold.log" 2>&1
grep -q "cache: module changed src/lib.pengu" "$TMP/cold.log" || {
    echo "FAIL: missing changed-module diagnostic" >&2
    cat "$TMP/cold.log" >&2
    exit 1
}
if grep -q "cache: module added src/main.pengu" "$TMP/cold.log"; then
    echo "FAIL: spurious added-module diagnostic" >&2
    exit 1
fi
echo "OK cache miss explains changed modules"
