#!/usr/bin/env bash
# Build the PenguScript C runtime for wasm32-unknown-emscripten.
#
# Writes a *separate* tree from the host runtime:
#
#   build/wasm/lib/libpengu_runtime.a
#   build/wasm/lib/libminiz.a
#   build/wasm/lib/libre.a
#   build/wasm/include/pengu_runtime.h
#   build/wasm/obj/...
#
# A wasm object and a host object are not interchangeable, so this script never
# touches build/lib. `emar` is required: GNU `ar` cannot write an archive of
# wasm members.
#
# Usage:
#   ./tools/build_runtime_wasm.sh
#   EMCC=/path/to/emcc EMAR=/path/to/emar ./tools/build_runtime_wasm.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EMCC="${EMCC:-emcc}"
if [ -z "${EMAR:-}" ]; then
  if command -v emar >/dev/null 2>&1; then
    EMAR="$(command -v emar)"
  elif [ -x "$(dirname "$(command -v "$EMCC" 2>/dev/null || echo emcc)")/emar" ]; then
    EMAR="$(dirname "$(command -v "$EMCC")")/emar"
  else
    EMAR="emar"
  fi
fi

if ! command -v "$EMCC" >/dev/null 2>&1; then
  echo "build_runtime_wasm: '$EMCC' not found in PATH." >&2
  echo "  Install and activate the Emscripten SDK:" >&2
  echo "    git clone https://github.com/emscripten-core/emsdk.git" >&2
  echo "    cd emsdk && ./emsdk install latest && ./emsdk activate latest" >&2
  echo "    source ./emsdk_env.sh" >&2
  exit 1
fi
if ! command -v "$EMAR" >/dev/null 2>&1; then
  echo "build_runtime_wasm: '$EMAR' not found; emsdk ships emar next to emcc." >&2
  exit 1
fi

OUT="$ROOT/build/wasm"
INC="$OUT/include"
LIB="$OUT/lib"
OBJ="$OUT/obj"
mkdir -p "$INC" "$LIB" "$OBJ"

cp "$ROOT/pengu_runtime.h" "$INC/pengu_runtime.h"
cp "$ROOT/std_c/sds/sds.h" "$INC/sds.h"

FLAGS=(
  -O2 -std=c11 -D_POSIX_C_SOURCE=200809L
  -I"$ROOT" -I"$INC"
  -I"$ROOT/std_c/sds" -I"$ROOT/std_c/CC-main" -I"$ROOT/std_c/vaqt/src"
  -pthread -ffunction-sections -fdata-sections
)
CFLAGS_C99=(-O2 -std=c99 -Wall -Wextra)

rm -f "$LIB/libpengu_runtime.a" "$LIB/libminiz.a" "$LIB/libre.a"
OBJS=()

echo "[runtime-wasm] core"
"$EMCC" "${FLAGS[@]}" -DPENGU_ENABLE_THREADS=0 -DPENGU_RUNTIME_SUBSYSTEM_ONLY=0 \
  -c "$ROOT/runtime/pengu_runtime.c" -o "$OBJ/pengu_runtime.o"
OBJS+=("$OBJ/pengu_runtime.o")

echo "[runtime-wasm] filum"
"$EMCC" "${FLAGS[@]}" -DPENGU_ENABLE_THREADS=1 -DPENGU_RUNTIME_SUBSYSTEM_ONLY=1 \
  -c "$ROOT/runtime/pengu_runtime.c" -o "$OBJ/pengu_runtime_filum.o"
OBJS+=("$OBJ/pengu_runtime_filum.o")

echo "[runtime-wasm] sds"
"$EMCC" "${CFLAGS_C99[@]}" -I"$ROOT/std_c/sds" \
  -ffunction-sections -fdata-sections \
  -c "$ROOT/std_c/sds/sds.c" -o "$OBJ/sds.o"
OBJS+=("$OBJ/sds.o")

echo "[runtime-wasm] vaqt"
for src in "$ROOT"/std_c/vaqt/src/*.c; do
  name="$(basename "$src" .c)"
  "$EMCC" "${FLAGS[@]}" -Wall -Wextra \
    -c "$src" -o "$OBJ/vaqt_$name.o"
  OBJS+=("$OBJ/vaqt_$name.o")
done
"$EMCC" "${FLAGS[@]}" -Wall -Wextra \
  -c "$ROOT/runtime/pengu_vaqt.c" -o "$OBJ/pengu_vaqt.o"
OBJS+=("$OBJ/pengu_vaqt.o")

echo "[runtime-wasm] JS bridge"
"$EMCC" "${FLAGS[@]}" -Wall -Wextra \
  -c "$ROOT/runtime/pengu_js.c" -o "$OBJ/pengu_js.o"
OBJS+=("$OBJ/pengu_js.o")

echo "[runtime-wasm] containers"
"$EMCC" "${FLAGS[@]}" -Wall -Wextra \
  -c "$ROOT/runtime/pengu_containers.c" -o "$OBJ/pengu_containers.o"
OBJS+=("$OBJ/pengu_containers.o")
"$EMCC" "${FLAGS[@]}" -Wall -Wextra \
  -c "$ROOT/runtime/pengu_cc_extra.c" -o "$OBJ/pengu_cc_extra.o"
OBJS+=("$OBJ/pengu_cc_extra.o")

# Optional native bridges (libffi/libsodium) are not in the wasm sysroot. They
# are skipped; importing std.ffi_call/std.secrets on wasm is rejected by the
# driver with an actionable message.
if printf '#include <ffi.h>\n' | "$EMCC" -E -x c - >/dev/null 2>&1; then
  "$EMCC" "${FLAGS[@]}" -Wall -Wextra -c "$ROOT/runtime/pengu_ffi_call.c" -o "$OBJ/pengu_ffi_call.o"
  OBJS+=("$OBJ/pengu_ffi_call.o")
else
  echo "[runtime-wasm] libffi bridge skipped (ffi.h not in the wasm sysroot)"
fi
if printf '#include <sodium.h>\n' | "$EMCC" -E -x c - >/dev/null 2>&1; then
  "$EMCC" "${FLAGS[@]}" -Wall -Wextra -c "$ROOT/runtime/pengu_sodium.c" -o "$OBJ/pengu_sodium.o"
  OBJS+=("$OBJ/pengu_sodium.o")
else
  echo "[runtime-wasm] libsodium bridge skipped (sodium.h not in the wasm sysroot)"
fi

"$EMAR" rcs "$LIB/libpengu_runtime.a" "${OBJS[@]}"

echo "[runtime-wasm] miniz"
"$EMCC" "${CFLAGS_C99[@]}" -I"$ROOT/std_c" -I"$ROOT" -I"$INC" -I"$ROOT/std_c/sds" \
  -DMINIZ_NO_ZLIB_COMPATIBLE_NAMES -DMINIZ_NO_ARCHIVE_APIS -DMINIZ_NO_STDIO \
  -DMINIZ_NO_TIME -Wno-type-limits -ffunction-sections -fdata-sections \
  -c "$ROOT/std_c/miniz.c" -o "$OBJ/miniz.o"
"$EMAR" rcs "$LIB/libminiz.a" "$OBJ/miniz.o"

echo "[runtime-wasm] regex"
"$EMCC" "${CFLAGS_C99[@]}" -I"$ROOT/std_c" -I"$ROOT" -I"$INC" -I"$ROOT/std_c/sds" \
  -ffunction-sections -fdata-sections \
  -c "$ROOT/std_c/re.c" -o "$OBJ/re.o"
"$EMAR" rcs "$LIB/libre.a" "$OBJ/re.o"

echo "[runtime-wasm] built $LIB/libpengu_runtime.a"
ls -l "$LIB"/libpengu_runtime.a "$LIB"/libminiz.a "$LIB"/libre.a
