#!/usr/bin/env bash
# Una instancia generica conserva @packed / @align del template.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/meta.pengu" <<'PENGU1'
@packed
rune Pac shard T:
    a as T
    b as int

@align(16)
rune Ali shard T:
    a as T

weave main into int:
    var p as Pac of int is with a is 1, b is 2
    var q as Ali of int is with a is 3
    return p.a + q.a - 4
PENGU1

"$PSC" emit-c "$tmp/meta.pengu" >"$tmp/meta.c" 2>/dev/null || {
  echo "FAIL: emit-c"; exit 1; }
grep -q '} __attribute__((packed));' "$tmp/meta.c" || { echo "FAIL: falta packed en Pac__int"; exit 1; }
grep -q '} __attribute__((aligned(16)));' "$tmp/meta.c" || { echo "FAIL: falta aligned(16) en Ali__int"; exit 1; }
echo "OK generic metadata"
