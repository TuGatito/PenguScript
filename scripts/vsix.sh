#!/usr/bin/env bash
# Empaqueta la extensión de VS Code (editors/vscode) como .vsix y la instala.
#
# Uso:
#   ./scripts/vsix.sh                    empaqueta e instala con el CLI `code`
#   ./scripts/vsix.sh --package-only     solo genera el .vsix
#   ./scripts/vsix.sh --skip-deps        no ejecuta npm install (usa node_modules)
#   ./scripts/vsix.sh --out DIR          deja el .vsix en DIR (por defecto dist/)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_DIR="${ROOT}/editors/vscode"
OUT_DIR="${ROOT}/dist"
PACKAGE_ONLY=0
SKIP_DEPS=0

info() { printf '→ %s\n' "$*"; }
warn() { printf 'aviso: %s\n' "$*" >&2; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Uso: scripts/vsix.sh [opciones]

  --package-only   genera el .vsix pero no lo instala
  --skip-deps      no ejecuta «npm install»
  --out DIR        directorio de salida del .vsix (por defecto dist/)
  -h, --help       muestra esta ayuda
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --package-only) PACKAGE_ONLY=1; shift ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    --out)
      [ "$#" -ge 2 ] || fail "--out necesita un directorio"
      OUT_DIR="$2"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; fail "opción desconocida: $1" ;;
  esac
done

command -v node >/dev/null 2>&1 || fail "no se encontró «node» en PATH"
command -v npm >/dev/null 2>&1 || fail "no se encontró «npm» en PATH"
[ -f "${EXT_DIR}/package.json" ] || fail "no existe ${EXT_DIR}/package.json"

if [ "${SKIP_DEPS}" = 0 ] && [ ! -d "${EXT_DIR}/node_modules" ]; then
  info "Instalando dependencias de la extensión…"
  (cd "${EXT_DIR}" && npm install --no-audit --no-fund)
fi

VERSION="$(node -p "require('${EXT_DIR}/package.json').version")"
mkdir -p "${OUT_DIR}"
VSIX="${OUT_DIR}/penguscript-${VERSION}.vsix"

info "Empaquetando la extensión ${VERSION}…"
(cd "${EXT_DIR}" && npx --yes @vscode/vsce package --allow-missing-repository --out "${VSIX}")

[ -f "${VSIX}" ] || fail "no se generó el .vsix"
info "generado ${VSIX}"

if [ "${PACKAGE_ONLY}" = 1 ]; then
  exit 0
fi

CODE_CLI=""
for candidate in code code-insiders codium; do
  if command -v "${candidate}" >/dev/null 2>&1; then
    CODE_CLI="${candidate}"
    break
  fi
done

if [ -z "${CODE_CLI}" ]; then
  warn "no se encontró el CLI de VS Code (code/code-insiders/codium)."
  cat <<EOF

Instálala manualmente desde VS Code:
  Extensiones → «...» → Instalar desde VSIX… → ${VSIX}
O instala el CLI y vuelve a ejecutar este script.
EOF
  exit 0
fi

info "Instalando en VS Code con «${CODE_CLI}»…"
"${CODE_CLI}" --install-extension "${VSIX}" --force
info "extensión instalada. Recarga VS Code para activarla."
