#!/usr/bin/env bash
# Build the PenguScript C runtime and std_c satellites without Python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CC="${CC:-cc}"
AR="${AR:-ar}"
OUT="$ROOT/build"
INC="$OUT/include"
LIB="$OUT/lib"
OBJ="$OUT/obj_runtime"
SOBJ="$OUT/obj_std_c"
mkdir -p "$INC" "$LIB" "$OBJ" "$SOBJ"
cp "$ROOT/pengu_runtime.h" "$INC/pengu_runtime.h"

FLAGS=(-O2 -I"$ROOT" -I"$INC" -ffunction-sections -fdata-sections)
OBJS=()
for pair in "pengu_runtime.o:0" "pengu_runtime_filum.o:1"; do
  obj="${pair%%:*}"
  gate="${pair##*:}"
  "$CC" "${FLAGS[@]}" -DPENGU_ENABLE_THREADS="$gate" \
    -DPENGU_RUNTIME_SUBSYSTEM_ONLY="$gate" \
    -c "$ROOT/runtime/pengu_runtime.c" -o "$OBJ/$obj"
  OBJS+=("$OBJ/$obj")
done
rm -f "$LIB/libpengu_runtime.a"
"$AR" rcs "$LIB/libpengu_runtime.a" "${OBJS[@]}"

for src in "$ROOT"/std_c/*.c; do
  [ -e "$src" ] || continue
  name="$(basename "$src" .c)"
  cp "$ROOT"/std_c/*.h "$INC"/ 2>/dev/null || true
  case "$name" in
    petitio)
      if ! printf '#include <curl/curl.h>\n' | "$CC" -E -x c - >/dev/null 2>&1; then
        echo "[runtime] skipping petitio (curl headers missing)"
        continue
      fi ;;
  esac
  extra=()
  [ "$name" = "miniz" ] && extra=(-DMINIZ_NO_ZLIB_COMPATIBLE_NAMES -DMINIZ_NO_ARCHIVE_APIS -DMINIZ_NO_STDIO -DMINIZ_NO_TIME -Wno-type-limits)
  "$CC" -O2 -std=c99 -Wall -Wextra -Werror -I"$ROOT/std_c" -I"$ROOT" -I"$INC" \
    -ffunction-sections -fdata-sections "${extra[@]}" -c "$src" -o "$SOBJ/$name.o"
  rm -f "$LIB/lib$name.a"
  "$AR" rcs "$LIB/lib$name.a" "$SOBJ/$name.o"
done

echo "[runtime] built $LIB/libpengu_runtime.a and std_c archives"
