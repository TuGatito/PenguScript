#!/usr/bin/env bash
# Sube la versión en todos los sitios que la nombran (no toca CHANGELOG).
#
# Uso: tools/bump_version.sh 0.28.2
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
old="$(tr -d '[:space:]' <"$ROOT/VERSION")"
new="${1:?uso: tools/bump_version.sh NUEVA_VERSION}"
if [ "$old" = "$new" ]; then
    echo "VERSION ya es $new"
    exit 0
fi
files=(
    VERSION
    pengu.toml
    release.toml
    src/main.pengu
    src/psc/lsp/server.pengu
    vscode-extension/README.md
    docs/README.md
    docs/LANGUAGE.md
    docs/LANGUAGE.es.md
    docs/STDLIB.md
    docs/STDLIB.es.md
    docs/PENGUNIC.md
    docs/PENGUNIC.es.md
    docs/LIBRARIES.md
    docs/LIBRARIES.es.md
)
for f in "${files[@]}"; do
    if [ ! -f "$ROOT/$f" ]; then
        echo "FALTA: $f" >&2
        exit 1
    fi
    python3 - "$ROOT/$f" "$old" "$new" <<'PY'
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
if old not in text:
    print(f"sin cambio: {path}")
else:
    open(path, "w", encoding="utf-8").write(text.replace(old, new))
    print(f"ok: {path}")
PY
done
echo "VERSION -> $new"
