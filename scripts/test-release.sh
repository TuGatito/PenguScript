#!/bin/sh
# Prueba de humo del ciclo de release completo, sin red.
#
# Construye el paquete, monta un "repositorio de releases" local, instala desde
# ese repositorio con scripts/install.sh, ejecuta `pengu doctor` y un programa,
# empaqueta el .vsix y desinstala.
#
# Uso: scripts/test-release.sh [--skip-build]

set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skip_build=no
while [ $# -gt 0 ]; do
    case "$1" in
        --skip-build) skip_build=yes; shift ;;
        -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) printf 'error: opción desconocida %s\n' "$1" >&2; exit 1 ;;
    esac
done

work=$(mktemp -d "${TMPDIR:-/tmp}/pengu-release.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

version=0.1.0
target=x86_64-unknown-linux-gnu
case "$(uname -s):$(uname -m)" in
    Darwin:arm64) target=aarch64-apple-darwin ;;
    Darwin:x86_64) target=x86_64-apple-darwin ;;
    Linux:aarch64|Linux:arm64) target=aarch64-unknown-linux-gnu ;;
esac

printf '== empaquetando ==\n'
if [ "$skip_build" = yes ]; then
    "$root/scripts/package.sh" --skip-build --version "$version" --target "$target" --out "$work/dist"
else
    "$root/scripts/package.sh" --version "$version" --target "$target" --out "$work/dist"
fi

printf '== montando el repositorio local ==\n'
release="$work/repo/releases/download/v$version"
mkdir -p "$release"
cp "$work/dist"/*.tar.gz "$release"/
cp "$work/dist/SHA256SUMS" "$release/SHA256SUMS"

printf '== instalando desde el repositorio ==\n'
PENGU_REPO="file://$work/repo" "$root/scripts/install.sh" \
    --version "$version" --prefix "$work/prefix" --no-path

printf '== ejecutando un programa ==\n'
mkdir -p "$work/project"
cat > "$work/project/Tome.toml" <<'TOME'
[tome]
name = "humo"
version = "0.1.0"
pengu = "0.6"
edition = "2024"

[[bin]]
name = "humo"
path = "main.pengu"
TOME
cat > "$work/project/main.pengu" <<'PENGU'
suma = (a: Int, b: Int) -> Int
    a + b

grimoire
    print(suma(2, 3))
PENGU
output=$(cd "$work/project" && "$work/prefix/bin/pengu" run)
if [ "$output" != "5" ]; then
    printf 'error: el programa instalado imprimió "%s" (esperaba 5)\n' "$output" >&2
    exit 1
fi

printf '== doctor ==\n'
PATH="$work/prefix/bin:$PATH" "$work/prefix/bin/pengu" doctor

printf '== extensión de VS Code ==\n'
node "$root/scripts/vsix.mjs" --out "$work/pengu-lsp.vsix"

printf '== desinstalando ==\n'
HOME="$work/home" "$root/scripts/install.sh" --prefix "$work/prefix" --uninstall --no-path
if [ -e "$work/prefix/bin/pengu" ]; then
    printf 'error: el binario sigue tras desinstalar\n' >&2
    exit 1
fi

printf 'todo listo: el ciclo de release funciona\n'
