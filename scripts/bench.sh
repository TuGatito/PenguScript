#!/usr/bin/env bash
# Reproducible performance benchmark for the PenguScript toolchain.
#
# It measures the scenarios quoted in docs/PERFORMANCE.md:
#   * cold run (no parser table cache) with gcc and with TCC,
#   * first run of a script with the parser tables already cached,
#   * warm run (binary cache hit),
#   * bundle.c size with and without dead-code elimination,
#   * sustained-execution time of a 10M-iteration loop,
#   * PCH on/off for a script build.
#
# Usage:
#   scripts/bench.sh [--repeat N]     # N runs per scenario, best reported
#
# Requirements: a built runtime (python build_runtime.py) and a C compiler.
# The benchmark never touches your real cache: everything lives in a temp dir.
#
# Methodology: state is reset *before every iteration* where the scenario is a
# cache miss, so "best of N" is a genuine cold/warm measurement rather than a
# warm run that happened to follow a cold one.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$REPO/.venv/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3)"
PENGU="$PY $REPO/pengu_project.py"
REPEAT=5

while [ $# -gt 0 ]; do
  case "$1" in
    --repeat) REPEAT="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

WORK="$(mktemp -d)"
export PENGU_CACHE_DIR="$WORK/cache"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

cat > hello.pengu <<'EOF'
import std.spark

weave main into void:
    calling spark.println with "hello"
EOF

cat > compute.pengu <<'EOF'
weave main into int:
    var acc as int is 0
    var i as int is 0
    while i < 10000000:
        set acc is acc + i
        set i is i + 1
    return 0
EOF

# time_ms <label> <command...>: runs N times, prints the best wall time.
time_ms() {
  local label="$1"; shift
  local best="" t0 t1 dt
  for _ in $(seq "$REPEAT"); do
    t0=$(date +%s%N)
    "$@" >/dev/null 2>&1 || true
    t1=$(date +%s%N)
    dt=$(( (t1 - t0) / 1000000 ))
    if [ -z "$best" ] || [ "$dt" -lt "$best" ]; then best="$dt"; fi
  done
  printf '%-48s %6s ms\n' "$label" "$best"
}

# time_ms_reset <reset-shell> <label> <command...>: resets before each run.
time_ms_reset() {
  local reset="$1"; shift
  local label="$1"; shift
  local best="" t0 t1 dt
  for _ in $(seq "$REPEAT"); do
    eval "$reset"
    t0=$(date +%s%N)
    "$@" >/dev/null 2>&1 || true
    t1=$(date +%s%N)
    dt=$(( (t1 - t0) / 1000000 ))
    if [ -z "$best" ] || [ "$dt" -lt "$best" ]; then best="$dt"; fi
  done
  printf '%-48s %6s ms\n' "$label" "$best"
}

echo "=== PenguScript benchmarks ($(uname -s), best of $REPEAT) ==="
echo "python: $($PY --version 2>&1)   workdir: $WORK"
echo

echo "--- CLI baseline (argparse + lazy imports, no build) ---"
time_ms "pengu gc (startup floor)" $PENGU gc --json

echo
echo "--- cold: every run rebuilds the parser tables and the binary ---"
time_ms_reset "rm -rf '$WORK/cache'" "hello.pengu cold, gcc (pre-PR flags)" \
  env PENGU_CACHE=0 PENGU_NO_DCE=1 PENGU_NO_TCC=1 PENGU_DEV_CC=gcc $PENGU run hello.pengu --quiet
time_ms_reset "rm -rf '$WORK/cache'" "hello.pengu cold, gcc (post-PR)" \
  env PENGU_NO_TCC=1 PENGU_DEV_CC=gcc $PENGU run hello.pengu --quiet
if [ -n "${PENGU_TCC:-}" ] || command -v tcc >/dev/null 2>&1; then
  time_ms_reset "rm -rf '$WORK/cache'" "hello.pengu cold, TCC (post-PR)" \
    env PENGU_NO_TCC= $PENGU run hello.pengu --quiet
else
  printf '%-48s %6s\n' "hello.pengu cold, TCC (post-PR)" "n/a (tcc not installed)"
fi

echo
echo "--- first run of a script (parser tables already cached) ---"
time_ms_reset "rm -rf '$WORK/cache/scripts'" "hello.pengu, gcc (post-PR)" \
  env PENGU_NO_TCC=1 PENGU_DEV_CC=gcc $PENGU run hello.pengu --quiet
if [ -n "${PENGU_TCC:-}" ] || command -v tcc >/dev/null 2>&1; then
  time_ms_reset "rm -rf '$WORK/cache/scripts'" "hello.pengu, TCC (post-PR)" \
    $PENGU run hello.pengu --quiet
fi

echo
echo "--- warm: binary cache hit ---"
$PENGU run hello.pengu --quiet >/dev/null 2>&1 || true
time_ms "hello.pengu warm (cache hit)" $PENGU run hello.pengu --quiet

echo
echo "--- dead-code elimination ---"
$PENGU run hello.pengu --quiet >/dev/null 2>&1 || true   # warm the parser cache
no_dce_lines=$(PENGU_NO_DCE=1 $PENGU expand hello.pengu | wc -l)
dce_lines=$($PENGU expand hello.pengu | wc -l)
printf '%-48s %6s lines\n' "bundle.c without DCE (PENGU_NO_DCE=1)" "$no_dce_lines"
printf '%-48s %6s lines\n' "bundle.c with DCE" "$dce_lines"
if [ "$no_dce_lines" -gt 0 ]; then
  printf '%-48s %5s%%\n' "reduction" "$(( (no_dce_lines - dce_lines) * 100 / no_dce_lines ))"
fi

echo
echo "--- sustained execution (10M-iteration loop) ---"
echo "compile+run forced each time (--no-cache):"
time_ms "compute.pengu (compile + run, gcc)" \
  $PENGU run compute.pengu --no-cache --quiet
echo "phase breakdown (gcc):"
$PENGU time compute.pengu 2>/dev/null | sed 's/^/  /' || true

echo
echo "--- precompiled header (project build dir, matching flags) ---"
if command -v gcc >/dev/null 2>&1 || command -v clang >/dev/null 2>&1; then
  time_ms_reset "rm -rf '$WORK/build'" "run --no-pch --keep --no-cache" \
    $PENGU run hello.pengu --no-pch --keep --no-cache --quiet
  time_ms_reset "rm -rf '$WORK/build'" "run --pch    --keep --no-cache" \
    $PENGU run hello.pengu --pch --keep --no-cache --quiet
else
  printf '%-48s %6s\n' "PCH comparison" "n/a (no gcc/clang)"
fi

echo
echo "--- doctor (informational) ---"
$PENGU doctor || true
