#!/usr/bin/env bash
#
# Verifies that the container-ownership programs release every allocation.
#
# valgrind is used when it is installed.  On machines without it (e.g. minimal
# CI images) the bundled `tests/leakcheck.c` malloc interposer runs instead: it
# performs a conservative mark-and-sweep at exit and fails when anything is
# *definitely lost*, which is the same category `valgrind --leak-check=full`
# reports.  Both paths are driven by tests/test_generics_suite.py.
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

exec "$PY" -m pytest tests/test_generics_suite.py -k no_memory_leaks -q
