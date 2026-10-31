#!/usr/bin/env bash
# Regression test for --prune-native: a satellite archive is linked only when
# one of its (live) modules actually needs it.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
OUT="$(mktemp -d "${TMPDIR:-/tmp}/pengu-link-prune.XXXXXX")"
trap 'rm -rf "$OUT"' EXIT

if [ ! -x "$PSC" ]; then
  echo "link_prune: no psc at $PSC" >&2
  exit 1
fi

build_link_line() {
  local src="$1" label="$2" bin="$3"
  local work="$OUT/work-$label"
  mkdir -p "$work"
  cp "$src" "$work/$(basename "$src")"
  # Run outside the repository: the repo pengu.toml adds its own links.
  (cd "$work" && "$PSC" build "$(basename "$src")" --exe --profile debug \
    --no-cache --prune-native --verbose --out "$bin" 2>&1) | grep -E '^cc:' | tail -1
}

fail=0
check() {
  local label="$1" line="$2" expect="$3"
  if ! printf '%s\n' "$line" | grep -q -- '-lpengu_runtime'; then
    echo "FAIL $label: no link line captured" >&2
    fail=1
    return
  fi
  if [ "$expect" = yes ]; then
    if printf '%s\n' "$line" | grep -q -- '-lminiz'; then
      echo "OK   $label: -lminiz present"
    else
      echo "FAIL $label: expected -lminiz" >&2
      fail=1
    fi
  else
    if printf '%s\n' "$line" | grep -q -- '-lminiz'; then
      echo "FAIL $label: -lminiz should be pruned" >&2
      fail=1
    else
      echo "OK   $label: -lminiz pruned"
    fi
  fi
}

build_release_line() {
  local src="$1" label="$2" bin="$3"
  local work="$OUT/release-$label"
  mkdir -p "$work"
  cp "$src" "$work/$(basename "$src")"
  (cd "$work" && "$PSC" build "$(basename "$src")" --exe --profile release \
    --no-cache --verbose --out "$bin" 2>&1) | grep -E '^cc:' | tail -1
}

check "hello"           "$(build_link_line "$ROOT/tests/size/hello.pengu" hello "$OUT/hello")" no
check "unused import"   "$(build_link_line "$ROOT/tests/size/unused_import.pengu" unused "$OUT/unused")" no
check "uses compressus" "$(build_link_line "$ROOT/tests/size/compressus.pengu" compressus "$OUT/compressus")" yes
check "release default" "$(build_release_line "$ROOT/tests/size/unused_import.pengu" unused "$OUT/unused-rel")" no

if [ "$fail" -ne 0 ]; then
  echo "link_prune: FAILED" >&2
  exit 1
fi
echo "link_prune: OK"
