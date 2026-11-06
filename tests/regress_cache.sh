#!/usr/bin/env bash
# Regresión: la caché de build es incremental, content-addressed y no se
# invalida por artefactos del build dir (bugs 2 y 3 de la auditoría 0.33.0).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in /*) ;; *) PSC="$ROOT/$PSC" ;; esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cache="$tmp/cache"
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[build]
name = "cache_probe"
entry = "src/main.pengu"

[profiles.debug]
cflags = ["-g", "-O0"]
TOML
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark

weave main into int:
    calling spark.println with "one"
    return 0
PENGU

build() {
    ( cd "$tmp" && PSC_CACHE_DIR="$cache" "$PSC" build . --verbose 2>&1 )
}

out="$(build)" || { echo "FAIL: primer build falló"; echo "$out"; exit 1; }
case "$out" in *"cc:"*) ;; *) echo "FAIL: el primer build no compiló"; exit 1;; esac
[ "$("$tmp/build/app")" = "one" ] || { echo "FAIL: salida inicial incorrecta"; exit 1; }

out="$(build)" || { echo "FAIL: segundo build falló"; echo "$out"; exit 1; }
case "$out" in *"cc:"*) echo "FAIL: el segundo build recompiló (debería ser cache hit)"; exit 1;; esac

# Un archivo ajeno dentro del build dir no debe cambiar la clave.
printf 'noise\n' >"$tmp/build/unrelated.txt"
out="$(build)" || { echo "FAIL: build tras ruido falló"; exit 1; }
case "$out" in *"cc:"*) echo "FAIL: un archivo del build dir invalidó la caché"; exit 1;; esac
rm -f "$tmp/build/unrelated.txt"

# Editar la fuente sí invalida y produce el binario nuevo.
sed -i 's/"one"/"two"/' "$tmp/src/main.pengu"
out="$(build)" || { echo "FAIL: build tras editar fuente falló"; exit 1; }
case "$out" in *"cc:"*) ;; *) echo "FAIL: editar la fuente no invalidó la caché"; exit 1;; esac
[ "$("$tmp/build/app")" = "two" ] || { echo "FAIL: salida tras editar incorrecta"; exit 1; }

# Cambiar cflags (un -D) debe invalidar: antes se reutilizaba el binario viejo.
sed -i 's/\["-g", "-O0"\]/["-g", "-O0", "-DREGRESS_CACHE_EXTRA=1"]/' "$tmp/pengu.toml"
out="$(build)" || { echo "FAIL: build con cflags nuevos falló"; exit 1; }
case "$out" in *"cc:"*) ;; *) echo "FAIL: cambiar cflags no invalidó la caché"; exit 1;; esac

# Y vuelve a estabilizarse.
out="$(build)" || { echo "FAIL: build estabilizado falló"; exit 1; }
case "$out" in *"cc:"*) echo "FAIL: la caché no se estabilizó"; exit 1;; esac

# --no-cache debe compilar siempre.
out="$( cd "$tmp" && PSC_CACHE_DIR="$cache" "$PSC" build . --no-cache --verbose 2>&1 )" || { echo "FAIL: build --no-cache falló"; exit 1; }
case "$out" in *"cc:"*) ;; *) echo "FAIL: --no-cache no compiló"; exit 1;; esac

echo "OK build cache incremental"
