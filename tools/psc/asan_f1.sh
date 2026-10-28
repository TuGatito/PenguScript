#!/usr/bin/env bash
# Build ASan/UBSan de PSC y pasada por el corpus. Uso: psc/tools/asan_f1.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -g" \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
../.venv/bin/python ../pengu_project.py build || exit 2
export ASAN_OPTIONS="detect_leaks=1:halt_on_error=1"
status=0
while IFS= read -r -d '' f; do
  ./build/psc lex "$f" --quiet --check >/dev/null 2>/tmp/psc_asan.err
  rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then
    echo "ASan/crash rc=$rc: $f"
    cat /tmp/psc_asan.err
    status=1
  elif grep -qE "AddressSanitizer|LeakSanitizer|runtime error:" /tmp/psc_asan.err; then
    echo "sanitizer: $f"
    cat /tmp/psc_asan.err
    status=1
  fi
done < <(find src ../std ../tests -name '*.pengu' -print0)
exit "$status"
