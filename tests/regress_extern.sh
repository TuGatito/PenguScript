#!/usr/bin/env bash
# Bloque `extern c:` / `extern cpp:` + `regnum` (F2.3).
set -u
PSC=${PSC:-$PWD/build/psc}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL extern: $*"; exit 1; }

cd "$tmp" || exit 1
cat > include_mylib.hpp <<'H'
#pragma once
namespace mylib { int open(const char* path); }
H

cat > cdecl.pengu <<'P'
extern c:
    declare abs with x as int into int

weave main into int:
    var r as int is calling abs with -3
    if r == 3:
        return 0
    return 1
P

"$PSC" run cdecl.pengu >/dev/null 2>&1 || fail "extern c no corre en C"
"$PSC" run cdecl.pengu --backend=cpp >/dev/null 2>&1 || fail "extern c no corre en C++"
"$PSC" emit-c cdecl.pengu --no-line-markers --out="$tmp/cdecl.c" >/dev/null 2>&1 || fail "emit-c falla"
grep -q 'extern "C"' "$tmp/cdecl.c" && fail "el backend C emitió extern \"C\""
grep -q 'int32_t abs(int32_t' "$tmp/cdecl.c" || fail "falta la declaración de abs"

"$PSC" emit-c cdecl.pengu --backend=cpp --no-line-markers --out="$tmp/cdecl.cpp" >/dev/null 2>&1 || fail "emit-c --backend=cpp falla"
grep -q 'extern "C" {' "$tmp/cdecl.cpp" || fail "el backend C++ no aísla el linkage C"
grep -q 'int32_t abs(int32_t' "$tmp/cdecl.cpp" || fail "falta abs en C++"

cat > cppdecl.pengu <<'P'
extern cpp:
    include "include_mylib.hpp"
    regnum mylib
    declare open with path as ref to frozen char into int

weave main into int:
    return 0
P

"$PSC" emit-c cppdecl.pengu --backend=cpp --no-line-markers --out="$tmp/cppdecl.cpp" >/dev/null 2>&1 || fail "emit-c --backend=cpp falla con extern cpp"
grep -q '#include "include_mylib.hpp"' "$tmp/cppdecl.cpp" || fail "falta el include de extern cpp"
grep -q 'mylib::open' "$tmp/cppdecl.cpp" || fail "falta el regnum en el nombre"
grep -q 'extern "C" {' "$tmp/cppdecl.cpp" && fail "extern cpp no debe llevar extern \"C\""

# El backend C no puede traducir `extern cpp`: el bundle debe fallar con un
# mensaje que diga qué hacer.
"$PSC" emit-c cppdecl.pengu --no-line-markers --out="$tmp/cppdecl.c" >/dev/null 2>&1 || fail "emit-c falla"
grep -q '#error "extern cpp: this module requires --backend=cpp"' "$tmp/cppdecl.c" || fail "falta el #error en C"

# `regnum` fuera de `extern cpp:` no compila.
cat > bad.pengu <<'P'
regnum mylib

weave main into int:
    return 0
P
if "$PSC" check bad.pengu >/dev/null 2>&1; then fail "regnum fuera de extern cpp debería fallar"; fi

"$PSC" fmt --check cdecl.pengu cppdecl.pengu >/dev/null 2>&1 || fail "fmt --check no está limpio"
echo "OK extern (F2.3)"
