#!/usr/bin/env bash
#
# Compiles and runs every runnable program under tests/test_string_composition.
#
# Programs named `err_*.pengu` are *expected* to be rejected by the checker;
# they are validated by tests/test_string_composition_suite.py, not here.
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
    log="/tmp/pengu_strcomp_$(echo "$name" | tr '/' '_').log"
    printf '🧪 %-46s ' "$name"
    if $PENGU_CMD run "$t" >"$log" 2>&1; then
        echo "✅ pass"
    else
        echo "❌ fail"
        tail -n 20 "$log" | sed 's/^/    /'
        FAIL=1
    fi
done < <(find "$TESTS_DIR" -type f \( -name 'ok_*.pengu' -o -name 'test_*.pengu' -o -name 'leak_*.pengu' \) | sort)

if [ "$FAIL" -eq 0 ]; then
    echo "🎉 All string-composition tests passed"
else
    echo "💥 Some string-composition tests failed"
    exit 1
fi
