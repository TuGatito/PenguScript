#!/bin/sh
# Empaqueta un binario de PenguScript para una plataforma.
#
# Uso:
#   scripts/package.sh [--version X.Y.Z] [--target TRIPLE] [--out DIR] [--skip-build]
#
# Genera en el directorio de salida:
#   pengu-<version>-<target>.tar.gz   (o .zip en Windows, vía CI)
#   SHA256SUMS
#   VERSION
#   sbom.json
#
# El artefacto contiene el binario `pengu` y la licencia si existe.

set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out="$root/dist"
version=""
target=""
skip_build=no

fail() {
    printf 'error: %s\n' "$1" >&2
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --version) [ $# -ge 2 ] || fail "--version necesita un valor"; version=$2; shift 2 ;;
        --version=*) version=${1#--version=}; shift ;;
        --target) [ $# -ge 2 ] || fail "--target necesita un valor"; target=$2; shift 2 ;;
        --target=*) target=${1#--target=}; shift ;;
        --out) [ $# -ge 2 ] || fail "--out necesita un directorio"; out=$2; shift 2 ;;
        --out=*) out=${1#--out=}; shift ;;
        --skip-build) skip_build=yes; shift ;;
        -h|--help)
            sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) fail "opción desconocida \`$1\`" ;;
    esac
done

if [ -z "$version" ]; then
    version=$(sed -n 's/^version = "\(.*\)"/\1/p' "$root/crates/pengu-cli/Cargo.toml" | head -1)
    [ -n "$version" ] || fail "no se pudo leer la versión de crates/pengu-cli/Cargo.toml"
fi

if [ -z "$target" ]; then
    os=$(uname -s)
    arch=$(uname -m)
    case "$os:$arch" in
        Linux:x86_64) target=x86_64-unknown-linux-gnu ;;
        Linux:aarch64|Linux:arm64) target=aarch64-unknown-linux-gnu ;;
        Darwin:x86_64) target=x86_64-apple-darwin ;;
        Darwin:arm64) target=aarch64-apple-darwin ;;
        MINGW*:x86_64|MSYS*:x86_64) target=x86_64-pc-windows-msvc ;;
        *) fail "no sé qué target corresponde a $os/$arch; pasa --target" ;;
    esac
fi

binary="pengu"
case "$target" in
    *windows*) binary="pengu.exe" ;;
esac

if [ "$skip_build" = no ]; then
    printf 'compilando pengu %s para %s\n' "$version" "$target"
    ( cd "$root" && cargo build --release --locked -p pengu-cli )
fi

built="$root/target/release/$binary"
[ -f "$built" ] || fail "no existe $built (¿compilaste con --release?)"

stage=$(mktemp -d "${TMPDIR:-/tmp}/pengu-package.XXXXXX")
trap 'rm -rf "$stage"' EXIT HUP INT TERM

prefix="pengu-$version-$target"
mkdir -p "$stage/$prefix"
cp "$built" "$stage/$prefix/$binary"
if [ -f "$root/LICENSE" ]; then
    cp "$root/LICENSE" "$stage/$prefix/LICENSE"
fi
if [ -f "$root/README.md" ]; then
    cp "$root/README.md" "$stage/$prefix/README.md"
fi
printf '%s\n' "$version" > "$stage/$prefix/VERSION"

mkdir -p "$out"
(
    cd "$stage"
    if [ "${target#*windows}" != "$target" ]; then
        zip -q -X -r "$out/$prefix.zip" "$prefix"
    else
        tar -czf "$out/$prefix.tar.gz" "$prefix"
    fi
)

if [ "${target#*windows}" != "$target" ]; then
    archive="$out/$prefix.zip"
else
    archive="$out/$prefix.tar.gz"
fi

printf '%s\n' "$version" > "$out/VERSION"

# SHA256SUMS se ordena para que la salida sea determinista entre plataformas.
sums=$(mktemp "${TMPDIR:-/tmp}/pengu-sums.XXXXXX")
trap 'rm -rf "$stage" "$sums"' EXIT HUP INT TERM
if command -v sha256sum >/dev/null 2>&1; then
    ( cd "$out" && sha256sum ./*.tar.gz ./*.zip 2>/dev/null || true ) > "$sums"
else
    ( cd "$out" && shasum -a 256 ./*.tar.gz ./*.zip 2>/dev/null || true ) > "$sums"
fi
sed 's|  \./|  |' "$sums" | sort > "$out/SHA256SUMS"
rm -f "$sums"

# SBOM mínimo (SPDX-lite): paquetes del workspace con su versión.
if command -v node >/dev/null 2>&1; then
    ( cd "$root" && cargo metadata --no-deps --format-version 1 2>/dev/null ) > "$stage/metadata.json" || true
    if [ -s "$stage/metadata.json" ]; then
        node - "$stage/metadata.json" "$out/sbom.json" <<'JS'
const fs = require("node:fs");
const [input, output] = process.argv.slice(2);
const metadata = JSON.parse(fs.readFileSync(input, "utf8"));
const packages = metadata.packages
  .map((pkg) => ({ name: pkg.name, version: pkg.version, license: pkg.license ?? "MIT" }))
  .sort((a, b) => a.name.localeCompare(b.name));
const sbom = { format: "pengu-sbom-1", packages };
fs.writeFileSync(output, `${JSON.stringify(sbom, null, 2)}\n`);
JS
    fi
else
    printf 'aviso: node no está disponible; no genero sbom.json\n' >&2
fi

printf 'artefacto %s\n' "$(basename "$archive")"
printf 'sumas    %s\n' "$out/SHA256SUMS"
