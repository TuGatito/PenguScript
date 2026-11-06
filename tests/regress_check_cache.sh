#!/usr/bin/env bash
# psc check: un proyecto sin cambios no vuelve a ejecutar sema; un cambio real
# (o un error) invalida el marcador.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export PSC_CACHE_DIR="$TMP/cache"
mkdir -p "$TMP/proj/src"
printf 'weave main into int:\n    return 0\n' > "$TMP/proj/src/main.pengu"
printf '[package]\nname = "check-cache"\nversion = "0.1.0"\n' > "$TMP/proj/pengu.toml"
"$PSC" check "$TMP/proj" >/dev/null
n1=$(find "$PSC_CACHE_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
"$PSC" check "$TMP/proj" >/dev/null
n2=$(find "$PSC_CACHE_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)
[ "$n1" -eq "$n2" ] || { echo "check hit created a new entry: $n1 -> $n2"; exit 1; }
printf 'weave main into int:\n    return "bad"\n' > "$TMP/proj/src/main.pengu"
if "$PSC" check "$TMP/proj" >/dev/null 2>&1; then
  echo "stale check hit masked a type error"; exit 1
fi
echo "OK check cache"
