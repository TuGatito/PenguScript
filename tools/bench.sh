#!/usr/bin/env bash
# bench.sh — medición reproducible del compilador.
#
# Uso:
#   tools/bench.sh [PROYECTO] [--psc RUTA] [--runs N] [--gate-warm MS]
#                  [--gate-check MS] [--json]
#
# Mide:
#   cold  build sin caché (sema + codegen + cc)
#   warm  build con caché caliente (fast path < 2 s en el repo)
#   check sema únicamente
#
# La caché se aísla en un directorio temporal para no contaminar la del usuario.
# Con --gate-warm N sale 1 si la mejor pasada caliente supera N milisegundos;
# --gate-check N hace lo mismo con el segundo `psc check` (ya cacheado).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="$ROOT"
PSC="${PSC:-$ROOT/build/psc}"
RUNS=3
GATE_WARM=0
GATE_CHECK=0
JSON=0

while [ $# -gt 0 ]; do
  case "$1" in
    --psc) PSC="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --gate-warm) GATE_WARM="$2"; shift 2 ;;
    --gate-check) GATE_CHECK="$2"; shift 2 ;;
    --json) JSON=1; shift ;;
    --help|-h)
      sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    -*) echo "bench: opción desconocida: $1" >&2; exit 2 ;;
    *) PROJECT="$1"; shift ;;
  esac
done

[ -x "$PSC" ] || { echo "bench: no existe el compilador: $PSC" >&2; exit 2; }
[ -d "$PROJECT" ] || { echo "bench: no existe el proyecto: $PROJECT" >&2; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CACHE="$TMP/cache"

ms() {
  # date +%s%N no está en macOS; python3 es requisito de herramientas y CI.
  python3 - "$1" <<'PY'
import subprocess, sys, time
cmd = sys.argv[1]
t0 = time.perf_counter()
r = subprocess.run(cmd, shell=True)
dt = int((time.perf_counter() - t0) * 1000)
print(dt)
sys.exit(r.returncode)
PY
}

run_timed() { ms "$1"; }

cold="$(run_timed "PSC_CACHE_DIR='$CACHE' '$PSC' build '$PROJECT' --no-cache --out='$TMP/cold-app' >/dev/null 2>&1")"
# Precalienta la caché (no se mide): la primera compilación escribe artefacto
# y clave; a partir de ahí medimos el fast path real.
PSC_CACHE_DIR="$CACHE" "$PSC" build "$PROJECT" --out="$TMP/warm-app" >/dev/null 2>&1
warm1="$(run_timed "PSC_CACHE_DIR='$CACHE' '$PSC' build '$PROJECT' --out='$TMP/warm-app' >/dev/null 2>&1")"
best="$warm1"
for _ in $(seq 2 "$RUNS"); do
  t="$(run_timed "PSC_CACHE_DIR='$CACHE' '$PSC' build '$PROJECT' --out='$TMP/warm-app' >/dev/null 2>&1")"
  [ "$t" -lt "$best" ] && best="$t"
done
check1="$(run_timed "PSC_CACHE_DIR='$CACHE' '$PSC' check '$PROJECT' >/dev/null 2>&1")"
check="$(run_timed "PSC_CACHE_DIR='$CACHE' '$PSC' check '$PROJECT' >/dev/null 2>&1")"

if [ "$JSON" -eq 1 ]; then
  printf '{"project":"%s","cold_ms":%s,"warm_first_ms":%s,"warm_best_ms":%s,"check_ms":%s}\n' \
    "$PROJECT" "$cold" "$warm1" "$best" "$check"
else
  printf 'project : %s\n' "$PROJECT"
  printf 'cold    : %s ms\n' "$cold"
  printf 'warm #1 : %s ms\n' "$warm1"
  printf 'warm best: %s ms (runs=%s)\n' "$best" "$RUNS"
  printf 'check #1: %s ms\n' "$check1"
  printf 'check warm: %s ms\n' "$check"
fi

if [ "$GATE_CHECK" -gt 0 ] && [ "$check" -gt "$GATE_CHECK" ]; then
  echo "bench: check cacheado ${check} ms > gate ${GATE_CHECK} ms" >&2
  exit 1
fi
if [ "$GATE_WARM" -gt 0 ] && [ "$best" -gt "$GATE_WARM" ]; then
  echo "bench: gate falló: warm ${best} ms > ${GATE_WARM} ms" >&2
  exit 1
fi
