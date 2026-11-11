#!/usr/bin/env bash
# F2.5: `declare` suelto es E0116 y `psc migrate --wrap-declares` lo arregla;
# W0018 al eclipsar un tipo de la biblioteca.
set -u
PSC=${PSC:-$PWD/build/psc}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fail() { echo "FAIL declare_extern: $*"; exit 1; }

cd "$tmp" || exit 1
cat > bare.pengu <<'P'
include "stdio.h"

declare abs with x as int into int

weave main into int:
    return 0
P
"$PSC" check bare.pengu >out.txt 2>&1 && fail "un declare suelto debería ser E0116"
grep -q "E0116" out.txt || fail "falta el código E0116"
grep -q "must be inside an 'extern c:'" out.txt || fail "falta el mensaje de E0116"

"$PSC" migrate --wrap-declares bare.pengu >/dev/null 2>&1 || fail "migrate --wrap-declares falla"
grep -q "^extern c:$" bare.pengu || fail "no se insertó el bloque"
grep -q "^    declare abs" bare.pengu || fail "no se indentó el declare"
"$PSC" check bare.pengu >/dev/null 2>&1 || fail "el fuente migrado no compila"
"$PSC" migrate --wrap-declares --check bare.pengu >/dev/null 2>&1 || fail "--wrap-declares no es idempotente"
"$PSC" run bare.pengu >/dev/null 2>&1 || fail "el programa migrado no corre"
"$PSC" run bare.pengu --backend=cpp >/dev/null 2>&1 || fail "el programa migrado no corre en C++"

cat > shadowed.pengu <<'P'
rune span:
    n as int

weave main into int:
    return 0
P
"$PSC" check shadowed.pengu >warn.txt 2>&1 || true
grep -q "W0018" warn.txt || fail "falta W0018 al eclipsar un tipo de la biblioteca"
grep -q "shadows the library type" warn.txt || fail "falta el mensaje de W0018"

cat > ok.pengu <<'P'
extern c:
    declare abs with x as int into int

weave main into int:
    if (calling abs with -2) == 2:
        return 0
    return 1
P
"$PSC" run ok.pengu >/dev/null 2>&1 || fail "extern c con abs no corre en C"
"$PSC" run ok.pengu --backend=cpp >/dev/null 2>&1 || fail "extern c con abs no corre en C++"
echo "OK declare/extern (F2.5)"
