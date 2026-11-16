#!/usr/bin/env bash
# Ejecuta la sonda sobre cada .pengu y muestra el primer error por etapa.
cd "$(dirname "$0")/../../.." || exit 1
PROBE=./scratch/tools/probe/target/debug/pengu-probe
for f in scratch/probes/limits/*.pengu; do
  printf '\n=== %s\n' "$(basename "$f")"
  "$PROBE" "$f" 2>&1 | head -5
  if [ ${PIPESTATUS[0]} -eq 0 ]; then echo "OK"; fi
done
