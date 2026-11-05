#!/usr/bin/env bash
# Comprueba los diagnósticos de propiedad de @coroutine y los panics del runtime.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

expect_error() {
    local name="$1" needle="$2" file="$TMP/$1.pengu"
    if "$PSC" check "$file" >"$TMP/$name.out" 2>&1; then
        echo "FAIL $name: compiled, expected error"
        fail=$((fail + 1))
        return
    fi
    if ! grep -q "$needle" "$TMP/$name.out"; then
        echo "FAIL $name: missing '$needle'"
        cat "$TMP/$name.out"
        fail=$((fail + 1))
    fi
}

expect_panic() {
    local name="$1" needle="$2" file="$TMP/$1.pengu"
    "$PSC" run "$file" --no-cache >"$TMP/$name.out" 2>&1
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "FAIL $name: exited 0, expected panic"
        fail=$((fail + 1))
        return
    fi
    if ! grep -q "$needle" "$TMP/$name.out"; then
        echo "FAIL $name: missing '$needle'"
        cat "$TMP/$name.out"
        fail=$((fail + 1))
    fi
}

cat >"$TMP/param.pengu" <<'PENGU'
import std.coro

weave worker with s as string into void:
    banish s

weave relay with s as string into int:
    var co as coro.Coroutine is calling coro.start with worker, s
    calling co.abandon
    return 0
PENGU

cat >"$TMP/moved.pengu" <<'PENGU'
import std.coro
import std.scrolls

weave worker with s as string into void:
    banish s

weave main into int:
    var s as string is calling scrolls.join with ["he", "llo"], ""
    var co as coro.Coroutine is calling coro.start with worker, s
    banish s
    calling co.abandon
    return 0
PENGU

cat >"$TMP/cross_thread.pengu" <<'PENGU'
import std.coro
import std.filum

weave taker with co as coro.Coroutine into void:
    return

weave main into int:
    var co as coro.Coroutine is with _ptr is null
    calling filum.start with taker, co
    return 0
PENGU

expect_error param "owning values must be local bindings"
expect_error moved "value was moved into a coroutine"
expect_error cross_thread "value contains a ref to a type that is not @shared"

cat >"$TMP/yield_out.pengu" <<'PENGU'
import std.coro

weave main into int:
    calling coro.yield
    return 0
PENGU

cat >"$TMP/free_suspended.pengu" <<'PENGU'
import std.coro

weave w into void:
    calling coro.yield

weave main into int:
    var co as coro.Coroutine is calling coro.start0 with w
    calling co.free
    return 0
PENGU

cat >"$TMP/resume_finished.pengu" <<'PENGU'
import std.coro

weave w into void:
    return

weave main into int:
    var co as coro.Coroutine is calling coro.start0 with w
    calling co.resume
    calling co.resume
    return 0
PENGU

cat >"$TMP/empty_free.pengu" <<'PENGU'
import std.coro

weave main into int:
    var co as coro.Coroutine is with _ptr is null
    calling co.free
    return 0
PENGU

expect_panic yield_out "yield outside a coroutine"
expect_panic free_suspended "free on a suspended coroutine"
expect_panic resume_finished "resume on a finished coroutine"
expect_panic empty_free "free on an empty coroutine handle"

if [ "$fail" -ne 0 ]; then
    echo "$fail coroutine regression test(s) failed"
    exit 1
fi
echo "OK coroutine ownership and panics"
