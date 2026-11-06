#!/usr/bin/env bash
# regress_fibers.sh — pilas de fibras en gdb (`pengu-fibers`).
#
# Compila un proyecto con una corrutina suspendida en un yield, abre gdb en
# modo batch y llama al helper del runtime. Sin gdb el test se salta.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
command -v gdb >/dev/null 2>&1 || { echo "SKIP fibers: no gdb"; exit 0; }
[ -x "$PSC" ] || { echo "SKIP fibers: no psc"; exit 0; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/src"
cat > "$TMP/pengu.toml" <<'EOF'
[build]
entry = "src/main.pengu"
output = "exe"
output_name = "fib"
EOF
cat > "$TMP/src/main.pengu" <<'EOF'
import std.coro

weave worker with n as ref to int into void:
    set essence of n is 1
    calling coro.yield
    set essence of n is 2

weave main into int:
    var n as int is 0
    var co as coro.Coroutine is calling coro.start with worker, (sigil of n)
    var a as coro.CoroutineState is calling co.resume
    var b as coro.CoroutineState is calling co.status
    if a != coro.CoroutineState.suspended or b != coro.CoroutineState.suspended:
        return 1
    calling co.abandon
    return 0
EOF

PSC_CACHE_DIR="$TMP/cache" "$PSC" build "$TMP" --no-cache --profile=debug >/dev/null 2>&1
out="$(cd "$TMP" && PENGU_FIBER_TRACE=1 gdb -q -batch \
  -ex "break src/main.pengu:13" \
  -ex run \
  -ex "call (void) pengu_c_coro_dump()" \
  -ex kill \
  --args build/app 2>&1 || true)"

echo "$out" | grep -q "fibers: 1 live" || {
  echo "FAIL fibers: no live coroutine listed" >&2
  echo "$out" | tail -20 >&2
  exit 1
}
echo "$out" | grep -q "worker" || {
  echo "FAIL fibers: yield stack not symbolized" >&2
  echo "$out" | tail -20 >&2
  exit 1
}
echo "OK fiber stacks in gdb"
