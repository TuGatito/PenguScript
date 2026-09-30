#!/usr/bin/env bash
#
# Verifies that the interpolation programs release every allocation.
#
# valgrind is used when installed; otherwise the bundled tests/leakcheck.c
# malloc interposer (conservative mark-and-sweep at exit) reports the same
# "definitely lost == 0" signal.  Both paths are driven by
# tests/test_string_composition_suite.py.
set -uo pipefail

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$TESTS_DIR/../.." && pwd)"
if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PY="$REPO_ROOT/.venv/bin/python"
else
    PY="python3"
fi

cd "$REPO_ROOT"

if command -v valgrind >/dev/null 2>&1; then
    echo "🔍 Backend: valgrind"
else
    echo "🔍 Backend: bundled leakcheck.so (valgrind not installed)"
fi

exec "$PY" -m pytest tests/test_string_composition_suite.py -k no_memory_leaks -q
