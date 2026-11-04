#!/usr/bin/env bash
# Una dependencia `path` no copia `lib/` ni `build/` (ni `.git/`).
#
# Copiarlos provoca recursión: el `lib/` instalado de un ejemplo contiene
# otra copia del paquete, que a su vez contiene ese mismo `lib/`.
set -uo pipefail
PSC="${PSC:-psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/dep/src" "$WORK/dep/lib" "$WORK/dep/build" "$WORK/app/src"
cat > "$WORK/dep/pengu.toml" <<'EOF'
[project]
name = "dep"
version = "0.1.0"
entry = "src/dep.pengu"
output = "static"
EOF
cat > "$WORK/dep/src/dep.pengu" <<'EOF'
## Dependencia de prueba.
weave ping into int:
    return 7
EOF
echo "junk" > "$WORK/dep/lib/junk.txt"
echo "junk" > "$WORK/dep/build/junk.txt"

cat > "$WORK/app/pengu.toml" <<'EOF'
[project]
name = "app"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
EOF
cat > "$WORK/app/src/main.pengu" <<'EOF'
import dep

weave main into int:
    return 0
EOF

cd "$WORK/app" || exit 1
if ! "$PSC" add "$WORK/dep" --trust >"$WORK/add.log" 2>&1; then
    echo "FAIL: psc add falló"
    cat "$WORK/add.log"
    exit 1
fi
if [ ! -f lib/dep/src/dep.pengu ]; then
    echo "FAIL: no se instaló el código de la dependencia"
    exit 1
fi
if [ -e lib/dep/lib ] || [ -e lib/dep/build ]; then
    echo "FAIL: se copiaron directorios generados (lib/build)"
    exit 1
fi
echo "OK path dep sin generados"
