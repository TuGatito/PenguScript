#!/bin/sh
# Empaqueta la extensión de VS Code y la instala (atajo de vsix.mjs --install).
#
# Uso: scripts/install-extension.sh [--code RUTA] [--out RUTA]

set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
command -v node >/dev/null 2>&1 || { printf 'error: hace falta node\n' >&2; exit 1; }
exec node "$here/vsix.mjs" --install "$@"
