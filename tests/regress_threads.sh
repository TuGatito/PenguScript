#!/usr/bin/env bash
# Comprueba que `filum.start` rechaza refs sin @shared y valores movidos.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

cat >"$TMP/not_shared.pengu" <<'PENGU'
import std.filum
rune Conn:
    fd as int
weave worker with c as ref to Conn into void:
    set c->fd is 0
weave main into int:
    var c as Conn is with fd is 7
    let h as Thread is calling filum.start with worker, (sigil of c)
    calling h.free
    return 0
PENGU
if "$PSC" check "$TMP/not_shared.pengu" >"$TMP/out1" 2>&1; then
    echo "FAIL: ref to a rune without @shared was accepted"
    fail=1
elif ! grep -q "@shared" "$TMP/out1"; then
    echo "FAIL: missing @shared diagnostic"
    cat "$TMP/out1"
    fail=1
fi

cat >"$TMP/moved.pengu" <<'PENGU'
import std.filum
weave worker with s as string into void:
    calling print with s
weave main into int:
    var s as string is "hello"
    let h as Thread is calling filum.start with worker, s
    var r as result of void to ThreadError is calling h.join
    calling print with s
    calling h.free
    return 0
PENGU
if "$PSC" check "$TMP/moved.pengu" >"$TMP/out2" 2>&1; then
    echo "FAIL: moved value was accepted after start"
    fail=1
elif ! grep -q "moved into a thread" "$TMP/out2"; then
    echo "FAIL: missing moved-value diagnostic"
    cat "$TMP/out2"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    exit 1
fi
echo "OK thread ownership checks"
