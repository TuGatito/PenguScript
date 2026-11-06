#!/usr/bin/env bash
# Regresión de `psc add` para librerías: layout, import, rollback, vendor nativo
# y remove de secciones [dependencies.<name>].
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- 1) librería con src_dir="pengu" e import declarado ---------------------
mkdir -p "$WORK/mylib/pengu" "$WORK/app/src"
cat > "$WORK/mylib/pengu.toml" <<'TOML'
[project]
name = "mylib-repo"
import = "mylib"
version = "0.1.0"
entry = "pengu/mylib.pengu"
output = "static"

[build]
src_dir = "pengu"
TOML
cat > "$WORK/mylib/pengu/mylib.pengu" <<'PENGU'
weave answer into int:
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
import mylib

weave main into int:
    return calling mylib.answer
PENGU

cd "$WORK/app"
"$PSC" add "$WORK/mylib" --no-build || fail "add librería falló"
[ -d lib/mylib ] || fail "no se instaló con el nombre de import"
grep -Fq 'mylib = { path' pengu.toml || fail "manifiesto sin entrada mylib"
"$PSC" build >/dev/null || fail "build de la app falló"
"$PSC" remove mylib || fail "remove falló"
if grep -Fq '[dependencies.mylib]' pengu.toml; then fail "remove dejó la sección"; fi
[ ! -d lib/mylib ] || fail "remove dejó lib/mylib"

# --- 2) fallo de build.pengu: exit != 0 y rollback ---------------------------
mkdir -p "$WORK/badlib/src" "$WORK/app2/src"
cat > "$WORK/badlib/pengu.toml" <<'TOML'
[project]
name = "badlib"
version = "0.1.0"
entry = "src/badlib.pengu"
output = "static"
TOML
cat > "$WORK/badlib/src/badlib.pengu" <<'PENGU'
weave x into int:
    return 1
PENGU
cat > "$WORK/badlib/build.pengu" <<'PENGU'
weave main into int:
    return 3
PENGU
cat > "$WORK/app2/pengu.toml" <<'TOML'
[project]
name = "app2"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
TOML
cat > "$WORK/app2/src/main.pengu" <<'PENGU'
import badlib

weave main into int:
    return 0
PENGU
cd "$WORK/app2"
if "$PSC" add "$WORK/badlib" --trust; then fail "add aceptó un build.pengu fallido"; fi
[ ! -d lib/badlib ] || fail "rollback dejó lib/badlib"
if grep -Fq 'badlib = {' pengu.toml; then fail "rollback dejó el manifiesto sucio"; fi

# --- 3) vendor conserva la librería nativa ----------------------------------
mkdir -p "$WORK/nativelib/src" "$WORK/nativelib/lib" "$WORK/app3/src"
cat > "$WORK/nativelib/pengu.toml" <<'TOML'
[project]
name = "nativelib"
version = "0.1.0"
entry = "src/nativelib.pengu"
output = "static"
TOML
cat > "$WORK/nativelib/src/nativelib.pengu" <<'PENGU'
weave x into int:
    return 7
PENGU
printf 'fake archive' > "$WORK/nativelib/lib/libnativelib.a"
cat > "$WORK/app3/pengu.toml" <<'TOML'
[project]
name = "app3"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
TOML
cat > "$WORK/app3/src/main.pengu" <<'PENGU'
import nativelib

weave main into int:
    return 0
PENGU
cd "$WORK/app3"
"$PSC" add "$WORK/nativelib" --no-build || fail "add nativelib falló"
[ -f lib/nativelib/lib/libnativelib.a ] || fail "add no copió el .a"
"$PSC" vendor || fail "vendor falló"
[ -f vendor/nativelib/lib/libnativelib.a ] || fail "vendor no conservó el .a"

echo "OK add librerías: layout, import, rollback, vendor, remove"
