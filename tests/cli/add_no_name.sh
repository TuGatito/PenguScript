#!/usr/bin/env bash
# Regression: `psc add <path>` without --name.
#
# The name must be derived from the source without freeing it (0.28.1 fixed a
# use-after-free that corrupted pengu.toml and broke the install).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir -p "$WORK/dep/src" "$WORK/app/src"

cat > "$WORK/dep/pengu.toml" <<'TOML'
[project]
name = "dep"
version = "0.1.0"
entry = "src/dep.pengu"
output = "static"
TOML

cat > "$WORK/dep/src/dep.pengu" <<'PENGU'
## Paquete de prueba para la regresión de `psc add`.
weave forty_two into int:
    return 42
PENGU

cat > "$WORK/app/pengu.toml" <<'TOML'
[project]
name = "app"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
TOML

cat > "$WORK/app/src/main.pengu" <<'PENGU'
import std.spark
import dep

weave main into int:
    calling spark.println with "{calling dep.forty_two}"
    return 0
PENGU

cd "$WORK/app"
"$PSC" add "$WORK/dep" || fail "psc add exited non-zero"

grep -Fq "path = \"$WORK/dep\"" pengu.toml || {
  echo "--- pengu.toml ---" >&2
  cat pengu.toml >&2
  fail "pengu.toml does not contain the source path"
}
[ -f "lib/dep/src/dep.pengu" ] || fail "dependency was not installed in lib/dep"

out="$("$PSC" run src/main.pengu --no-cache)"
[ "$out" = "42" ] || fail "expected 42, got '$out'"

echo "OK psc add without --name"
