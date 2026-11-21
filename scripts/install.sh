#!/usr/bin/env bash
# Instala el ejecutable de PenguScript (pengu) en un directorio del PATH.
#
# No toca la configuración de bash, zsh, fish ni de ningún otro shell: coloca
# el binario en un directorio que ya esté en PATH (o en ~/.local/bin y avisa
# de cómo añadirlo). Así el resultado es el mismo desde cualquier shell.
#
# Uso:
#   ./scripts/install.sh                  compila e instala en un directorio del PATH
#   ./scripts/install.sh --prefix DIR     instala en DIR/bin
#   ./scripts/install.sh --system         instala en /usr/local/bin (con sudo)
#   ./scripts/install.sh --skip-build     reutiliza dist/pengu ya compilado
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${HOME}/.local"
PREFIX_GIVEN=0
USE_SUDO=0
SKIP_BUILD=0

info() { printf '→ %s\n' "$*"; }
warn() { printf 'aviso: %s\n' "$*" >&2; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Uso: scripts/install.sh [opciones]

  --prefix DIR    instala el ejecutable en DIR/bin
  --system        instala en /usr/local/bin (pide sudo si hace falta)
  --skip-build    no compila; usa dist/pengu ya existente
  -h, --help      muestra esta ayuda
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --prefix)
      [ "$#" -ge 2 ] || fail "--prefix necesita un directorio"
      PREFIX="$2"
      PREFIX_GIVEN=1
      shift 2
      ;;
    --system)
      PREFIX="/usr/local"
      PREFIX_GIVEN=1
      USE_SUDO=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "opción desconocida: $1"
      ;;
  esac
done

is_on_path() {
  case ":${PATH}:" in
    *":$1:"*) return 0 ;;
    *) return 1 ;;
  esac
}

can_write_dir() {
  [ -d "$1" ] && [ -w "$1" ]
}

pick_bin_dir() {
  if [ "${PREFIX_GIVEN}" = 1 ]; then
    printf '%s\n' "${PREFIX}/bin"
    return
  fi

  if is_on_path "${HOME}/.local/bin" && can_write_dir "${HOME}/.local/bin"; then
    printf '%s\n' "${HOME}/.local/bin"
    return
  fi

  # Primer directorio escribible del PATH que no sea el directorio actual ni
  # el propio repositorio (evita instalar el binario dentro del proyecto).
  local dir
  local old_ifs="${IFS}"
  IFS=':'
  for dir in ${PATH}; do
    IFS="${old_ifs}"
    [ -n "${dir}" ] || continue
    [ "${dir}" = "." ] && continue
    case "${dir}" in
      "${ROOT}"|"${ROOT}"/*) continue ;;
    esac
    if can_write_dir "${dir}"; then
      printf '%s\n' "${dir}"
      return
    fi
    IFS=':'
  done
  IFS="${old_ifs}"

  printf '%s\n' "${HOME}/.local/bin"
}

command -v bun >/dev/null 2>&1 || fail "no se encontró «bun» en PATH (se necesita Bun >= 1.4)"

if [ "${SKIP_BUILD}" = 0 ]; then
  info "Compilando pengu con Bun…"
  (cd "${ROOT}" && bun run build)
fi

BIN="${ROOT}/dist/pengu"
[ -x "${BIN}" ] || BIN="${ROOT}/dist/pengu.exe"
[ -f "${BIN}" ] || fail "no existe dist/pengu; ejecuta de nuevo sin --skip-build"

BIN_DIR="$(pick_bin_dir)"
TARGET="${BIN_DIR}/pengu"

install_bin() {
  if [ "${USE_SUDO}" = 1 ] && ! can_write_dir "${BIN_DIR}"; then
    command -v sudo >/dev/null 2>&1 || fail "se necesita sudo para escribir en ${BIN_DIR}"
    sudo mkdir -p "${BIN_DIR}"
    sudo install -m 0755 "${BIN}" "${TARGET}"
  else
    mkdir -p "${BIN_DIR}"
    if command -v install >/dev/null 2>&1; then
      install -m 0755 "${BIN}" "${TARGET}"
    else
      cp "${BIN}" "${TARGET}"
      chmod 0755 "${TARGET}"
    fi
  fi
}

install_bin
info "instalado en ${TARGET}"

if is_on_path "${BIN_DIR}"; then
  info "«${BIN_DIR}» ya está en PATH: puedes ejecutar «pengu» en una terminal nueva."
else
  warn "«${BIN_DIR}» no está en PATH."
  cat <<EOF

Añádelo a tu PATH desde la configuración de tu shell y vuelve a abrir la terminal:

  bash / zsh:   export PATH="${BIN_DIR}:\$PATH"
  fish:         fish_add_path "${BIN_DIR}"
  PowerShell:   \$env:Path = "${BIN_DIR};\$env:Path"

Mientras tanto, el ejecutable está en: ${TARGET}
EOF
fi

"${TARGET}" --version
