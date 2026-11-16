#!/bin/sh
# Instalador de PenguScript para Linux y macOS.
#
# Uso:
#   ./scripts/install.sh [opciones]
#   curl -fsSL https://raw.githubusercontent.com/TuGatito/PenguScript-Rust/main/scripts/install.sh | sh
#
# Opciones:
#   --version VERSION   versión a instalar (por defecto, la última publicada)
#   --prefix DIR        prefijo de instalación (por defecto "$PENGU_HOME" o ~/.pengu)
#   --from-source [DIR] compila desde el checkout DIR (por defecto, este repositorio)
#   --no-path           no modifica los archivos de inicio del shell
#   --uninstall         quita el binario, los extras y el bloque del PATH
#   --force             reinstala aunque la versión ya esté instalada
#   --yes               no pregunta nada
#   -h, --help          muestra esta ayuda
#
# Variables:
#   PENGU_HOME          prefijo por defecto
#   PENGU_REPO          repositorio de releases (por defecto el del proyecto)
#   PENGU_NO_PATH       si vale 1, equivale a --no-path
#
# El script no necesita bash ni sudo: instala en el prefijo del usuario.

set -eu

MARKER_START="# >>> pengu >>>"
MARKER_END="# <<< pengu <<<"

PENGU_REPO="${PENGU_REPO:-https://github.com/TuGatito/PenguScript-Rust}"
VERSION="${PENGU_VERSION:-}"
PREFIX="${PENGU_HOME:-$HOME/.pengu}"
FROM_SOURCE=""
NO_PATH=0
UNINSTALL=0
FORCE=0
ASSUME_YES=0
TMP_DIR=""
FAILED=0

say() {
    printf '%s\n' "$*"
}

note() {
    printf '  %s\n' "$*"
}

fail() {
    FAILED=1
    printf 'error: %s\n' "$*" >&2
    exit 1
}

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
    exit 0
}

cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
    if [ "$status" -ne 0 ] && [ "$FAILED" = "0" ]; then
        printf 'error: la instalación falló (código %s)\n' "$status" >&2
    fi
}
trap cleanup EXIT HUP INT TERM

while [ $# -gt 0 ]; do
    case "$1" in
        --version)
            [ $# -ge 2 ] || fail "--version necesita un valor"
            VERSION="$2"
            shift 2
            ;;
        --version=*)
            VERSION="${1#--version=}"
            shift
            ;;
        --prefix)
            [ $# -ge 2 ] || fail "--prefix necesita un valor"
            PREFIX="$2"
            shift 2
            ;;
        --prefix=*)
            PREFIX="${1#--prefix=}"
            shift
            ;;
        --from-source)
            FROM_SOURCE="."
            if [ $# -ge 2 ] && [ "${2#-}" = "$2" ]; then
                FROM_SOURCE="$2"
                shift 2
            else
                shift
            fi
            ;;
        --from-source=*)
            FROM_SOURCE="${1#--from-source=}"
            shift
            ;;
        --no-path)
            NO_PATH=1
            shift
            ;;
        --uninstall)
            UNINSTALL=1
            shift
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --yes | -y)
            ASSUME_YES=1
            shift
            ;;
        -h | --help)
            usage
            ;;
        *)
            fail "opción desconocida \`$1\` (usa --help)"
            ;;
    esac
done

if [ "${PENGU_NO_PATH:-0}" = "1" ]; then
    NO_PATH=1
fi

BIN_DIR="$PREFIX/bin"
SHARE_DIR="$PREFIX/share"
MAN_DIR="$SHARE_DIR/man/man1"
COMPLETION_DIR="$SHARE_DIR/completions"

target() {
    os="$(uname -s)"
    arch="$(uname -m)"
    case "$os" in
        Linux)
            case "$arch" in
                x86_64 | amd64) echo "x86_64-unknown-linux-gnu" ;;
                aarch64 | arm64) echo "aarch64-unknown-linux-gnu" ;;
                *) fail "arquitectura no soportada: $arch" ;;
            esac
            ;;
        Darwin)
            case "$arch" in
                x86_64) echo "x86_64-apple-darwin" ;;
                arm64) echo "aarch64-apple-darwin" ;;
                *) fail "arquitectura no soportada: $arch" ;;
            esac
            ;;
        *)
            fail "sistema no soportado: $os (usa scripts/install.ps1 en Windows)"
            ;;
    esac
}

# Directorio del checkout si el script se ejecuta desde un repositorio con
# Cargo.toml (o desde el directorio actual). Vacío si no hay ninguno.
source_dir() {
    if [ -n "${1:-}" ] && [ "$1" != "." ]; then
        printf '%s\n' "$1"
        return 0
    fi
    script_dir=$(cd "$(dirname "$0")" 2>/dev/null && pwd) || script_dir=""
    if [ -n "$script_dir" ] && [ -f "$script_dir/../Cargo.toml" ]; then
        printf '%s\n' "$(cd "$script_dir/.." && pwd)"
        return 0
    fi
    if [ -f "./Cargo.toml" ]; then
        pwd
        return 0
    fi
    return 1
}

download() {
    url="$1"
    dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 3 -o "$dest" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$dest" "$url"
    else
        fail "hace falta curl o wget para descargar $url"
    fi
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        return 1
    fi
}

confirm() {
    [ "$ASSUME_YES" = "1" ] && return 0
    printf '%s [s/N] ' "$1"
    read -r answer || answer=""
    case "$answer" in
        s | S | si | Si | sí | Sí | y | Y | yes) return 0 ;;
        *) return 1 ;;
    esac
}

filter_block() {
    file="$1"
    tmp="$file.pengu.$$"
    awk -v start="$MARKER_START" -v end="$MARKER_END" '
        index($0, start) { skip = 1; next }
        index($0, end) { skip = 0; next }
        !skip { print }
    ' "$file" > "$tmp"
    # Quita las líneas en blanco que el bloque pudo dejar al final.
    printf '%s\n' "$(cat "$tmp")" > "$file"
    rm -f "$tmp"
}

remove_path_block() {
    file="$1"
    [ -f "$file" ] || return 0
    grep -qF "$MARKER_START" "$file" || return 0
    filter_block "$file"
    note "PATH limpiado en $file"
}

add_path_block() {
    file="$1"
    [ -f "$file" ] || return 0
    remove_path_block "$file" >/dev/null 2>&1 || true
    {
        printf '\n%s\n' "$MARKER_START"
        printf '%s\n' "# Añadido por el instalador de PenguScript. Elimina este bloque para quitarlo."
        printf 'case ":$PATH:" in\n    *":%s:"*) ;;\n    *) PATH="%s:$PATH" ;;\nesac\nexport PATH\n' "$BIN_DIR" "$BIN_DIR"
        printf '%s\n' "$MARKER_END"
    } >> "$file"
    note "PATH actualizado en $file"
}

install_path() {
    [ "$NO_PATH" = "1" ] && return 0
    touched=0
    # `.bash_profile` tiene prioridad sobre `.profile` en bash de login; si
    # existe, es el que hay que tocar para que una terminal nueva lo vea.
    if [ -f "$HOME/.bash_profile" ]; then
        add_path_block "$HOME/.bash_profile"
        touched=1
    fi
    for file in "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.zprofile"; do
        if [ -f "$file" ]; then
            add_path_block "$file"
            touched=1
        fi
    done
    # Los shells de login leen `.profile`, así que se crea si no existe: sin
    # esto, `bash -lc 'command -v pengu'` seguía sin encontrarlo.
    if [ "$touched" = "0" ] || [ ! -f "$HOME/.profile" ]; then
        : >> "$HOME/.profile"
        add_path_block "$HOME/.profile"
    fi
    fish_config="$HOME/.config/fish/config.fish"
    if [ -d "$HOME/.config/fish" ]; then
        [ -f "$fish_config" ] && remove_path_block "$fish_config" >/dev/null 2>&1 || true
        {
            printf '\n%s\n' "$MARKER_START"
            printf 'fish_add_path %s\n' "$BIN_DIR"
            printf '%s\n' "$MARKER_END"
        } >> "$fish_config"
        note "PATH actualizado en $fish_config"
    fi
}

uninstall() {
    say "Desinstalando PenguScript de $PREFIX"
    for file in "$HOME/.bash_profile" "$HOME/.profile" "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.config/fish/config.fish"; do
        if [ -f "$file" ]; then
            remove_path_block "$file"
        fi
    done
    if [ -d "$PREFIX" ]; then
        rm -rf "$PREFIX"
        note "eliminado $PREFIX"
    else
        note "no había nada en $PREFIX"
    fi
    say "Hecho. Abre una terminal nueva para que el PATH cambie."
}

install_extras() {
    binary="$1"
    mkdir -p "$COMPLETION_DIR" "$MAN_DIR"
    "$binary" completions bash > "$COMPLETION_DIR/pengu.bash" 2>/dev/null || true
    "$binary" completions zsh > "$COMPLETION_DIR/_pengu" 2>/dev/null || true
    "$binary" completions fish > "$COMPLETION_DIR/pengu.fish" 2>/dev/null || true
    "$binary" man > "$MAN_DIR/pengu.1" 2>/dev/null || true
    note "completions en $COMPLETION_DIR"
    note "man en $MAN_DIR/pengu.1"
}

install_from_source() {
    dir="$(source_dir "${1:-}")" ||
        fail "no encontré un artefacto publicado ni un checkout con Cargo.toml; pasa --version X o clona el repositorio y usa --from-source ."
    [ -f "$dir/Cargo.toml" ] || fail "no hay Cargo.toml en $dir"
    command -v cargo >/dev/null 2>&1 || fail "hace falta cargo para compilar desde fuente (instala Rust desde https://rustup.rs)"
    say "Compilando PenguScript desde $dir (esto puede tardar unos minutos)"
    ( cd "$dir" && cargo build --release --locked -p pengu-cli ) ||
        fail "cargo build falló en $dir"
    cp "$dir/target/release/pengu" "$BIN_DIR/pengu"
    VERSION="$("$BIN_DIR/pengu" version | awk '{print $2}')"
}

# Devuelve 0 si instaló, 2 si no pudo descargar el artefacto (para poder
# recurrir a compilar desde fuente) y falla en cualquier otro caso.
install_from_release() {
    target="$1"
    version="$2"
    TMP_DIR="$(mktemp -d)"
    archive="pengu-$version-$target.tar.gz"
    url="$PENGU_REPO/releases/download/v$version/$archive"
    say "Descargando $url"
    if ! download "$url" "$TMP_DIR/$archive"; then
        say "No se pudo descargar $archive."
        return 2
    fi
    if download "$PENGU_REPO/releases/download/v$version/SHA256SUMS" "$TMP_DIR/SHA256SUMS" 2>/dev/null; then
        expected="$(awk -v name="$archive" '{ sub("^\\./", "", $2) } $2 == name { print $1 }' "$TMP_DIR/SHA256SUMS")"
        [ -n "$expected" ] || fail "SHA256SUMS no contiene $archive"
        actual="$(sha256_of "$TMP_DIR/$archive")" || fail "no hay sha256sum ni shasum"
        [ "$expected" = "$actual" ] || fail "checksum incorrecto para $archive"
        note "checksum verificado"
    else
        note "aviso: no se pudo descargar SHA256SUMS; continúo sin verificar"
    fi
    tar -xzf "$TMP_DIR/$archive" -C "$TMP_DIR"
    binary="$(find "$TMP_DIR" -type f -name pengu | head -n 1)"
    [ -n "$binary" ] || fail "el archivo no contiene el binario pengu"
    cp "$binary" "$BIN_DIR/pengu"
    return 0
}

main() {
    if [ "$UNINSTALL" = "1" ]; then
        uninstall
        exit 0
    fi

    mkdir -p "$BIN_DIR"
    if [ -x "$BIN_DIR/pengu" ] && [ "$FORCE" = "0" ] && [ -z "$FROM_SOURCE" ] && [ -n "$VERSION" ]; then
        installed="$("$BIN_DIR/pengu" version | awk '{print $2}')"
        if [ "$installed" = "$VERSION" ]; then
            say "PenguScript $installed ya está instalado en $BIN_DIR"
            say "Usa --force para reinstalar o --version para cambiar."
            if [ "$NO_PATH" = "0" ]; then install_path; fi
            exit 0
        fi
    fi

    if [ -n "$FROM_SOURCE" ]; then
        install_from_source "$FROM_SOURCE"
    else
        target_name="$(target)"
        if [ -z "$VERSION" ]; then
            latest="$(download "$PENGU_REPO/releases/latest/download/VERSION" /dev/stdout 2>/dev/null || true)"
            VERSION="$(printf '%s' "$latest" | tr -d '[:space:]v')"
        fi
        if [ -z "$VERSION" ]; then
            say "No hay una versión publicada accesible en $PENGU_REPO."
            install_from_source ""
        else
            status=0
            install_from_release "$target_name" "$VERSION" || status=$?
            if [ "$status" -eq 2 ]; then
                VERSION=""
                install_from_source ""
            elif [ "$status" -ne 0 ]; then
                exit "$status"
            fi
        fi
    fi

    chmod 755 "$BIN_DIR/pengu"
    install_extras "$BIN_DIR/pengu"
    install_path

    say ""
    say "PenguScript $VERSION instalado en $BIN_DIR/pengu"
    if [ "$NO_PATH" = "1" ]; then
        say "Añade $BIN_DIR al PATH (se omitió por --no-path)."
    else
        say "Abre una terminal nueva o ejecuta: . ~/.profile"
    fi
    say ""
    say "Comprobando la instalación:"
    if ! PATH="$BIN_DIR:$PATH" "$BIN_DIR/pengu" doctor; then
        say ""
        say "Aviso: 'pengu doctor' encontró problemas (ver arriba)."
    fi
}

main "$@"
