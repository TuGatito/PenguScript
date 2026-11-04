#!/usr/bin/env bash
# `psc add` actualiza `[dependencies.<nombre>]` en vez de duplicar el manifiesto.
set -uo pipefail
PSC="${PSC:-psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/dep/src" "$WORK/app/src"
cat > "$WORK/dep/pengu.toml" <<'TOML'
[project]
name = "dep"
version = "0.1.0"
entry = "src/dep.pengu"
output = "static"
TOML
cat > "$WORK/dep/src/dep.pengu" <<'PENGU'
## Dependencia de prueba.
weave ping into int:
    return 7
PENGU
cat > "$WORK/app/pengu.toml" <<'TOML'
[project]
name = "app"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[dependencies.dep]
path = "../dep"
TOML
cat > "$WORK/app/src/main.pengu" <<'PENGU'
import dep

weave main into int:
    return 0
PENGU

cd "$WORK/app" || exit 1
if ! "$PSC" add "$WORK/dep" --trust --name dep >"$WORK/add.log" 2>&1; then
    echo "FAIL: psc add falló"
    cat "$WORK/add.log"
    exit 1
fi
if grep -q '^\[dependencies\]$' pengu.toml; then
    echo "FAIL: se añadió una segunda tabla [dependencies]"
    cat pengu.toml
    exit 1
fi
if ! grep -q '^\[dependencies.dep\]$' pengu.toml; then
    echo "FAIL: desapareció [dependencies.dep]"
    cat pengu.toml
    exit 1
fi
if ! grep -q "^path = \"$WORK/dep\"$" pengu.toml; then
    echo "FAIL: la ruta no se actualizó"
    cat pengu.toml
    exit 1
fi
echo "OK dep manifest section"
