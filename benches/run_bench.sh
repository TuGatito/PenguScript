#!/usr/bin/env bash
# Thin POSIX wrapper around run_bench.py (roadmap 6.1).
# On Windows call `python benches/run_bench.py` directly.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$REPO/.venv/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3)"
exec "$PY" "$REPO/benches/run_bench.py" "$@"
