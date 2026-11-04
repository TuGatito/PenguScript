#!/usr/bin/env bash
# Ejecuta todas las regresiones de compilador (tests/regress_*.sh).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
status=0
for f in "$ROOT"/tests/regress_*.sh; do
    [ -f "$f" ] || continue
    if ! bash "$f"; then
        status=1
    fi
done
exit "$status"
