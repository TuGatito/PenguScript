#!/usr/bin/env bash
# Regresión: igualdad estructural de contenedores y rebanada de un literal.
#
# Dos huecos preexistentes (confirmados contra F1) que el emisor dejaba pasar
# hasta el C generado:
#   1. `a == b` sobre contenedores (`vector`, `map`, `maybe`, `result`, `span`,
#      `array`) emitía `==` crudo sobre `PenguList`/`PenguMap`/... y gcc fallaba.
#   2. `[1, 2, 3] at 0 to 2` tomaba la dirección de un temporal
#      (`pengu_list_at(&(&__extension__(...)))`), que no es un l-valor.
#
# Este test fija el comportamiento correcto en los dos backends.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

cat > "$WORK/eq.pengu" <<'PENGU'
import std.spark

rune P:
    x as int
    s as string

weave main into int:
    var a as vector of int is [1, 2, 3]
    var b as vector of int is [1, 2, 3]
    var c as vector of int is [1, 2, 4]
    if not (a == b) or a == c:
        calling spark.println with "list wrong"
        return 1
    var m1 as map of string, int is map of string, int
    calling m1.put with "a", 1
    calling m1.put with "b", 2
    var m2 as map of string, int is map of string, int
    calling m2.put with "b", 2
    calling m2.put with "a", 1
    if not (m1 == m2):
        calling spark.println with "map wrong"
        return 2
    var r1 as result of int to string is calling ok_of with 5
    var r2 as result of int to string is calling ok_of with 5
    var r3 as result of int to string is calling err_of with "boom"
    if not (r1 == r2) or r1 == r3:
        calling spark.println with "result wrong"
        return 3
    var vv1 as vector of vector of int is [[1, 2], [3]]
    var vv2 as vector of vector of int is [[1, 2], [3]]
    if not (vv1 == vv2):
        calling spark.println with "nested wrong"
        return 4
    var p1 as P is with x is 1, s is "a"
    var p2 as P is with x is 1, s is "a"
    if not (p1 == p2):
        calling spark.println with "rune wrong"
        return 5
    var ms1 as maybe string is some "hi"
    var ms2 as maybe string is some "hi"
    var ms3 as maybe string is maybe none
    if not (ms1 == ms2) or ms1 == ms3:
        calling spark.println with "maybe string wrong"
        return 6
    var xs as vector of int is [1, 2, 3]
    var ys as vector of int is [1, 2, 3]
    var sp1 as span of int is xs at 0 to 2
    var sp2 as span of int is ys at 0 to 2
    if not (sp1 == sp2):
        calling spark.println with "span wrong"
        return 7
    var ar1 as array of int with size 3 is [4, 5, 6]
    var ar2 as array of int with size 3 is [4, 5, 6]
    if not (ar1 == ar2):
        calling spark.println with "array wrong"
        return 8
    calling spark.println with "eq ok"
    return 0
PENGU

cat > "$WORK/slice.pengu" <<'PENGU'
import std.spark

weave main into int:
    var s as span of int is [1, 2, 3, 4] at 1 to 3
    if s.len != 2:
        calling spark.println with "slice wrong"
        return 1
    if s at 0 != 2:
        calling spark.println with "slice value wrong"
        return 2
    var xs as vector of int is [10, 20, 30]
    var t as span of int is xs at 0 to 2
    if t at 1 != 20:
        calling spark.println with "slice of var wrong"
        return 3
    calling spark.println with "slice ok"
    return 0
PENGU

run_both() {
    local file="$1" want="$2"
    local out
    out="$("$PSC" run "$file" 2>&1)" || fail "$file (C): $out"
    [[ "$out" == "$want" ]] || fail "$file (C): '$out' != '$want'"
    out="$("$PSC" run "$file" --backend=cpp 2>&1)" || fail "$file (C++): $out"
    [[ "$out" == "$want" ]] || fail "$file (C++): '$out' != '$want'"
}

run_both "$WORK/eq.pengu" "eq ok"
run_both "$WORK/slice.pengu" "slice ok"
echo "OK container eq and slice literal (F2.6)"
