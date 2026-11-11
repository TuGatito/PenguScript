#!/usr/bin/env bash
# Regresión: bandera `--backend` (F0.1 de la migración a C++).
#
# F0.1 añade la familia de backend al driver sin cambiar la salida:
#   - `--backend=c` (o `--backend c`) se acepta y emite exactamente lo mismo
#     que sin bandera (byte a byte);
#   - `emit-c --backend=cpp`/`build --backend=cpp`/`run --backend=cpp` emiten,
#     compilan con g++/clang++ y enlazan contra el runtime C (F1);
#   - un valor desconocido se rechaza con exit 2;
#   - `--help` documenta la bandera.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

cat > "$WORK/main.pengu" <<'PENGU'
weave main into int:
    return 0
PENGU

"$PSC" emit-c "$WORK/main.pengu" --out="$WORK/plain.c" >/dev/null
"$PSC" emit-c "$WORK/main.pengu" --backend=c --out="$WORK/eq.c" >/dev/null
cmp -s "$WORK/plain.c" "$WORK/eq.c" || fail "--backend=c changed the emitted C"

"$PSC" emit-c "$WORK/main.pengu" --backend c --out="$WORK/space.c" >/dev/null
cmp -s "$WORK/plain.c" "$WORK/space.c" || fail "--backend c (space form) changed the emitted C"

# `psc build --backend=c` debe producir el mismo artefacto que sin bandera.
"$PSC" build "$WORK/main.pengu" --out="$WORK/app_plain" >/dev/null
"$PSC" build "$WORK/main.pengu" --backend=c --out="$WORK/app_flag" >/dev/null
cmp -s "$WORK/app_plain" "$WORK/app_flag" || fail "--backend=c changed the built artifact"

# `psc run` acepta la familia explícita.
out="$("$PSC" run "$WORK/main.pengu" --backend=c --no-cache)"
[ -z "$out" ] || fail "psc run --backend=c printed unexpected output: '$out'"

expect_reject() {
  local desc="$1" msg="$2"
  shift 2
  local got rc
  set +e
  got="$("$@" 2>&1)"
  rc=$?
  set -e
  [ "$rc" -eq 2 ] || fail "$desc: expected exit 2, got $rc ($got)"
  case "$got" in
    *"$msg"*) ;;
    *) fail "$desc: message does not contain '$msg': $got" ;;
  esac
}

# `emit-c --backend=cpp` es el preview del dialecto (F0.3): acepta y emite.
"$PSC" emit-c "$WORK/main.pengu" --backend=cpp --out="$WORK/cpp.c" >/dev/null
[ -s "$WORK/cpp.c" ] || fail "emit-c --backend=cpp did not write a bundle"
expect_reject "emit-c --backend=bogus" "must be 'c' or 'cpp'" \
  "$PSC" emit-c "$WORK/main.pengu" --backend=bogus
expect_reject "build --backend=bogus" "must be 'c' or 'cpp'" \
  "$PSC" build "$WORK/main.pengu" --backend=bogus
# F1: el driver compila con el compilador de C++ y enlaza con el runtime C.
"$PSC" build "$WORK/main.pengu" --backend=cpp --out="$WORK/app_cpp" >/dev/null
[ -x "$WORK/app_cpp" ] || fail "build --backend=cpp did not produce an executable"
"$WORK/app_cpp" || fail "the C++-built executable failed"
"$PSC" run "$WORK/main.pengu" --backend=cpp --no-cache >/dev/null \
  || fail "run --backend=cpp failed"
"$PSC" run "$WORK/main.pengu" --backend cpp --no-cache >/dev/null \
  || fail "run --backend cpp (space form) failed"

"$PSC" emit-c --help | grep -q -- "--backend=c|cpp" || fail "emit-c --help does not document --backend"
"$PSC" build --help | grep -q -- "--backend=c|cpp" || fail "build --help does not document --backend"

echo "OK --backend flag (F0.1+F1)"
