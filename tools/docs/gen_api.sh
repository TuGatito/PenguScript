#!/usr/bin/env bash
# Regenera docs/api/ a partir de los comentarios `##` del proyecto y de std/.
#
#   tools/docs/gen_api.sh [--check]
#
# --check regenera en un directorio temporal y compara con docs/api: sirve
# como puerta de CI para detectar documentación desactualizada.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
psc=${PSC:-$root/build/psc}
if [ ! -x "$psc" ]; then
  echo "gen_api: falta $psc (ejecuta tools/build.sh)" >&2
  exit 1
fi

if [ "${1:-}" = "--check" ]; then
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  "$psc" doc --include-std --html --output "$tmp" >/dev/null
  if ! diff -rq "$root/docs/api" "$tmp" >/dev/null; then
    echo "gen_api: docs/api está desactualizado; ejecuta tools/docs/gen_api.sh" >&2
    diff -rq "$root/docs/api" "$tmp" >&2 || true
    exit 1
  fi
  echo "gen_api: docs/api al día"
  exit 0
fi

rm -rf "$root/docs/api"
"$psc" doc --include-std --html --output "$root/docs/api"
