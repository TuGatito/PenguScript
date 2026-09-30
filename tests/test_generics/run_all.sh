#!/usr/bin/env bash
#
# Compiles and runs every runnable program under tests/test_generics
# (recursively, so the gap1/gap2 regression directories are included).
#
# Programs named `fail_*.pengu` / `err_*.pengu` are *expected* to be rejected by
# the checker; they are validated by tests/test_generics_suite.py, not here.
#
# The compiler under test is the one in this checkout (`python pengu_project.py`)
# unless PENGU points at another build.
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

if [ -n "${PENGU:-}" ]; then
    PENGU_CMD="$PENGU"
elif [ -f "$REPO_ROOT/pengu_project.py" ]; then
    PENGU_CMD="$PY $REPO_ROOT/pengu_project.py"
else
    PENGU_CMD="pengu"
fi

echo "Using: $PENGU_CMD"
FAIL=0

while IFS= read -r t; do
    rel="${t#"$TESTS_DIR"/}"
    name="${rel%.pengu}"
    log="/tmp/pengu_generic_$(echo "$name" | tr '/' '_').log"
    printf '🧪 %-52s ' "$name"
    if $PENGU_CMD run "$t" >"$log" 2>&1; then
        echo "✅ pass"
    else
        echo "❌ fail"
        tail -n 20 "$log" | sed 's/^/    /'
        FAIL=1
    fi
done < <(find "$TESTS_DIR" -type f \( -name 'test_*.pengu' -o -name 'leak_*.pengu' -o -name 'ok_*.pengu' -o -path '*/gap1_*/*.pengu' \) | sort)

if [ "$FAIL" -eq 0 ]; then
    echo "🎉 All generic tests passed"
else
    echo "💥 Some generic tests failed"
    exit 1
fi
