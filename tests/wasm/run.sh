#!/usr/bin/env bash
# WebAssembly/Emscripten smoke tests for psc.
#
# No Python. Skips cleanly when emcc/emar/node are not installed; the CI wasm
# job installs them and runs this script for real.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
if [ ! -x "$PSC" ] && [ -x "$PSC.exe" ]; then
  PSC="$PSC.exe"
fi

if ! command -v emcc >/dev/null 2>&1; then
  echo "SKIP wasm: emcc not on PATH (activate the Emscripten SDK)"
  exit 0
fi
if ! command -v emar >/dev/null 2>&1; then
  echo "SKIP wasm: emar not on PATH (activate the Emscripten SDK)"
  exit 0
fi
if ! command -v node >/dev/null 2>&1; then
  echo "SKIP wasm: node not on PATH"
  exit 0
fi
if [ ! -f "$ROOT/build/wasm/lib/libpengu_runtime.a" ]; then
  echo "SKIP wasm: runtime not built (run tools/build_runtime_wasm.sh)"
  exit 0
fi
[ -x "$PSC" ] || { echo "wasm tests: missing compiler: $PSC" >&2; exit 1; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/psc-wasm.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

fail=0
check() {
  local name="$1"; shift
  if "$@"; then
    echo "ok   $name"
  else
    echo "FAIL $name"
    fail=$((fail + 1))
  fi
}

HELLO="$TMP/hello.pengu"
cat > "$HELLO" <<'PENGU'
import std.spark

weave main into int:
    calling spark.println with "wasm hello"
    return 0
PENGU

check "build hello" "$PSC" build "$HELLO" --target wasm --profile=release --no-cache --out="$TMP/hello"
check "node hello" bash -c "test \"\$(node '$TMP/hello.js')\" = 'wasm hello'"
check "psc run hello" bash -c "test \"\$('$PSC' run '$HELLO' --target wasm --profile=release --no-cache)\" = 'wasm hello'"

# Copy sources to TMP so the intermediate bundle names cannot collide with
# the native suite (which runs its own copy of std_web_smoke.pengu).
cp "$ROOT/tests/wasm/js_smoke.pengu" "$TMP/js_smoke.pengu"
cp "$ROOT/tests/wasm/web_smoke.pengu" "$TMP/web_smoke.pengu"
cp "$ROOT/tests/wasm/web_compile.pengu" "$TMP/web_compile.pengu"
cp "$ROOT/tests/wasm/std_web_smoke.pengu" "$TMP/std_web_smoke.pengu"

# std.web.js: eval/get/set/call and a C callback invoked from JS.
check "std.web.js build" "$PSC" build "$TMP/js_smoke.pengu" --target wasm --profile=release --no-cache --out="$TMP/js_smoke"
js_out="$(node "$TMP/js_smoke.js" 2>/dev/null || true)"
check "std.web.js" grep -q 'JS OK' <<<"$js_out"

# std.web.dom / std.web.canvas / std.web.storage against a minimal fake DOM.
check "std.web dom build" "$PSC" build "$TMP/web_smoke.pengu" --target wasm --profile=release --no-cache --out="$TMP/web_smoke"
web_out="$(node "$TMP/web_smoke.js" 2>/dev/null || true)"
check "std.web dom/canvas/storage" grep -q 'WEB OK' <<<"$web_out"

# All web modules must compile and link together (WebSocket/fetch start code).
check "web modules compile" "$PSC" build "$TMP/web_compile.pengu" --target wasm --profile=release --no-cache --out="$TMP/web_compile"

# std.web end-to-end (main loop, timers, static var).
check "std.web wasm build" "$PSC" build "$TMP/std_web_smoke.pengu" --target wasm --profile=release --no-cache --out="$TMP/std_web_smoke"
stdweb_out="$(timeout 30 node "$TMP/std_web_smoke.js" 2>/dev/null || true)"
check "std.web wasm" grep -q 'std_web_smoke: OK' <<<"$stdweb_out"

# Integrated test runner.
TEST="$TMP/test.pengu"
cat > "$TEST" <<'PENGU'
import std.ward

test "sum":
    calling expect_eq_int with 1 + 1, 2, "sum"

test "string":
    calling expect_eq_string with "a", "a", "string"

weave main into int:
    return 0
PENGU
check "psc test wasm" bash -c "'$PSC' test '$TEST' --target wasm --profile=release | grep -q 'All 2 test(s) passed'"

# when wasm folds both ways and the wasm branch really runs.
WHEN="$TMP/when.pengu"
cat > "$WHEN" <<'PENGU'
import std.spark

weave main into int:
    when wasm:
        calling spark.println with "wasm-branch"
    when not wasm:
        calling spark.println with "native-branch"
    return 0
PENGU
check "when wasm folds" bash -c "test \"\$('$PSC' run '$WHEN' --target wasm --profile=release --no-cache)\" = 'wasm-branch'"
check "when native folds" bash -c "test \"\$('$PSC' run '$WHEN' --profile=release --no-cache)\" = 'native-branch'"

# Static archive: real wasm object members, archived with emar.
PROJ="$TMP/proj"
mkdir -p "$PROJ/src"
cat > "$PROJ/pengu.toml" <<'TOML'
[project]
name = "app"
version = "0.1.0"
entry = "src/main.pengu"
output = "static"
output_name = "app"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
includes = []
links = []
lib_dirs = []
include_dirs = []
cflags = ["-Wall", "-std=c11"]
ldflags = []
defines = []
cc = "gcc"
TOML
cat > "$PROJ/src/main.pengu" <<'PENGU'
import std.spark
weave main into int:
    calling spark.println with "static"
    return 0
PENGU
check "build static" "$PSC" build "$PROJ" --target wasm --profile=release --no-cache
if [ -f "$PROJ/build/libapp.a" ]; then
  mkdir -p "$TMP/arx"
  ( cd "$TMP/arx" && emar x "$PROJ/build/libapp.a" )
  member="$(emar t "$PROJ/build/libapp.a" | head -n1)"
  magic="$(od -An -tx1 -N4 "$TMP/arx/$member" | tr -d ' \n')"
  check "static members are wasm" test "$magic" = "0061736d"
else
  echo "FAIL static archive missing"
  fail=$((fail + 1))
fi

# shared is refused, WASI is refused.
sed -i 's/output = "static"/output = "shared"/' "$PROJ/pengu.toml"
shared_out="$("$PSC" build "$PROJ" --target wasm 2>&1 || true)"
check "shared refused" grep -q 'shared.*is not supported' <<<"$shared_out"
sed -i 's/output = "shared"/output = "exe"/' "$PROJ/pengu.toml"
wasi_out="$("$PSC" build "$PROJ" --target wasi 2>&1 || true)"
check "wasi refused" grep -q 'WASI is not supported' <<<"$wasi_out"

# Unsupported std modules get an actionable diagnostic, not a linker error.
NET="$TMP/net.pengu"
cat > "$NET" <<'PENGU'
import std.net
weave main into int:
    return 0
PENGU
check "std.net diagnostic" bash -c "'$PSC' build '$NET' --target wasm 2>&1 | grep -q 'std.net is not available on wasm'"

# doctor sees the toolchain.
check "doctor wasm" bash -c "'$PSC' doctor --target wasm | grep -q '\[ok\] emcc'"

if [ "${PSC_WASM_SLOW:-0}" = "1" ]; then
  check "filum stress wasm" bash -c "timeout 180 '$PSC' run '$ROOT/tests/wasm/filum_stress.pengu' --target wasm --profile=release --no-cache | grep -q 'filum_stress: OK'"
fi

if [ "$fail" -ne 0 ]; then
  echo "$fail wasm test(s) failed"
  exit 1
fi
echo "OK wasm smoke tests"
