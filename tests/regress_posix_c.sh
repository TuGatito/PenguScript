#!/usr/bin/env bash
# Regresión: el C generado se compila con `-std=c11` estricto, así que psc debe
# definir `_POSIX_C_SOURCE`/`_DEFAULT_SOURCE`. Sin ellas, una cabecera que use
# sockets o `clock_gettime` no compila (las declaraciones POSIX quedan ocultas).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/src" "$tmp/include"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "posix_c"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"

[build]
src_dir = "src"
include_dir = "include"
cc = "gcc"
cflags = ["-Wall"]
TOML
cat >"$tmp/include/posix_probe.h" <<'C'
#ifndef POSIX_PROBE_H
#define POSIX_PROBE_H
#if !defined(_POSIX_C_SOURCE)
#error "psc debe definir _POSIX_C_SOURCE al compilar el bundle"
#endif
#include <time.h>
static int posix_probe_clock(void) {
    struct timespec ts;
    return clock_gettime(CLOCK_MONOTONIC, &ts) == 0;
}
#endif
C
cat >"$tmp/src/posix_probe.d.pengu" <<'PENGU'
include "posix_probe.h"

declare posix_probe_clock into int
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import posix_probe

weave main into int:
    let ok as int is calling posix_probe.posix_probe_clock
    calling spark.println with "{ok}"
    return 0
PENGU

out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: el bundle no compila con APIs POSIX"; echo "$out"; exit 1; }
[ "$out" = "1" ] || { echo "FAIL: posix_probe_clock imprimió '$out' (esperado 1)"; echo "$out"; exit 1; }
echo "OK posix cflags"
