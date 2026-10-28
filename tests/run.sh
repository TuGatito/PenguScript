#!/usr/bin/env bash
# PSC-native test runner (no Python). Requires psc + cc.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
cd "$ROOT"
fail=0
count=0
run_one() {
  local f="$1"
  grep -q 'weave main' "$f" || return 0
  case "$(basename "$f")" in bench_*|fuzz_*) return 0 ;; esac
  count=$((count+1))
  if ! "$PSC" run "$f" --no-cache >/tmp/psc-test.out 2>/tmp/psc-test.err; then
    echo "FAIL $f"
    tail -20 /tmp/psc-test.err
    fail=$((fail+1))
  fi
}
for f in tests/pengu/*.pengu; do [ -e "$f" ] && run_one "$f"; done
while IFS= read -r f; do run_one "$f"; done < <(find tests/conformance -name '*.pengu' -type f | sort)
if [ "$fail" -ne 0 ]; then
  echo "$fail of $count test file(s) failed"
  exit 1
fi
echo "OK $count PSC test file(s)"
