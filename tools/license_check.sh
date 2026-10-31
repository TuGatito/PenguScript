#!/usr/bin/env bash
# Enforce the vendor license allowlist for std_c/.
#
# Checks:
#   1. every std_c/<dir>/ has a LICENSE/LICENCE/COPYING file;
#   2. its text matches an allowed permissive license;
#   3. THIRD_PARTY.md documents the component;
#   4. the root single-file components are documented too.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALLOWED="MIT BSD-2-Clause BSD-3-Clause ISC Apache-2.0 Zlib CC0-1.0 Unlicense BSL-1.0 Unicode-3.0 OpenLDAP-2.8 PostgreSQL X11"
fail=0

detect_spdx() {
  local text="$1"
  # Order matters: ISC text is short and could match other patterns.
  if printf '%s' "$text" | grep -qi 'ISC License'; then echo "ISC"; return; fi
  if printf '%s' "$text" | grep -qi 'Apache License'; then echo "Apache-2.0"; return; fi
  if printf '%s' "$text" | grep -qi 'Boost Software License'; then echo "BSL-1.0"; return; fi
  if printf '%s' "$text" | grep -qi 'CC0 1.0'; then echo "CC0-1.0"; return; fi
  if printf '%s' "$text" | grep -qi 'OpenLDAP Public License'; then echo "OpenLDAP-2.8"; return; fi
  if printf '%s' "$text" | grep -qi 'UNICODE, INC. LICENSE'; then echo "Unicode-3.0"; return; fi
  if printf '%s' "$text" | grep -qi 'PostgreSQL License'; then echo "PostgreSQL"; return; fi
  if printf '%s' "$text" | grep -qi 'zlib License\|altered source versions'; then echo "Zlib"; return; fi
  if printf '%s' "$text" | grep -qi 'free and unencumbered software released into the public domain'; then echo "Unlicense"; return; fi
  if printf '%s' "$text" | grep -qi 'MIT License\|Permission is hereby granted, free of charge'; then echo "MIT"; return; fi
  if printf '%s' "$text" | grep -qi 'Redistribution and use in source and binary forms'; then
    if printf '%s' "$text" | grep -qi 'Neither the name\|endorse'; then echo "BSD-3-Clause"; else echo "BSD-2-Clause"; fi
    return
  fi
  echo "UNKNOWN"
}

check_allowed() {
  local spdx="$1" name="$2"
  case " $ALLOWED " in
    *" $spdx "*) return 0 ;;
  esac
  echo "FAIL $name: license '$spdx' is not in the allowlist" >&2
  fail=1
  return 1
}

echo "component              license"
for dir in "$ROOT"/std_c/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  license_file="$(find "$dir" -maxdepth 1 -type f \( -iname 'LICENSE*' -o -iname 'LICENCE*' -o -iname 'COPYING*' \) | sort | head -1)"
  if [ -z "$license_file" ]; then
    printf '%-22s %s\n' "$name" "MISSING LICENSE"
    echo "FAIL $name: no LICENSE/LICENCE/COPYING file" >&2
    fail=1
    continue
  fi
  spdx="$(detect_spdx "$(cat "$license_file")")"
  printf '%-22s %s\n' "$name" "$spdx"
  check_allowed "$spdx" "$name" || true
  if ! grep -qi -- "$name" "$ROOT/THIRD_PARTY.md"; then
    echo "FAIL $name: not documented in THIRD_PARTY.md" >&2
    fail=1
  fi
done

# Single-file components: no directory license file, but they must be credited.
for needle in "miniz" "tiny-regex-c" "utf8.h" "petitio" "toml_min"; do
  if ! grep -qi -- "$needle" "$ROOT/THIRD_PARTY.md"; then
    echo "FAIL std_c/$needle: not documented in THIRD_PARTY.md" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "license_check: FAILED" >&2
  exit 1
fi
echo "license_check: OK ($ALLOWED)"
