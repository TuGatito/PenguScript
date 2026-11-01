#!/usr/bin/env bash
# Regression: chain steps must be methods and pipe steps must be free functions.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/dot_fn.pengu" <<'PENGU'
weave dbl with x as int into int:
    return x * 2
weave main into int:
    let x as int is 1
    let y as int is calling x.dbl
    return y
PENGU
if "$PSC" check "$tmp/dot_fn.pengu" >"$tmp/o1" 2>&1; then
    echo "FAIL: free function accepted with dot chain"
    cat "$tmp/o1"
    exit 1
fi
grep -qE "E0005|E0053" "$tmp/o1" || { echo "FAIL: wrong code for dot/free function"; cat "$tmp/o1"; exit 1; }

cat >"$tmp/pipe_method.pengu" <<'PENGU'
import std.scrolls
weave main into int:
    let s as string is "  hi  " pipe scrolls.get_trim
    return 0
PENGU
if "$PSC" check "$tmp/pipe_method.pengu" >"$tmp/o2" 2>&1; then
    echo "FAIL: method accepted as pipe step"
    cat "$tmp/o2"
    exit 1
fi
grep -q "E0053" "$tmp/o2" || { echo "FAIL: missing E0053 for pipe/method"; cat "$tmp/o2"; exit 1; }

cat >"$tmp/pipe_unknown.pengu" <<'PENGU'
weave main into int:
    let x as int is 1 pipe missing_step
    return x
PENGU
if "$PSC" check "$tmp/pipe_unknown.pengu" >"$tmp/o3" 2>&1; then
    echo "FAIL: unknown pipe step accepted"
    cat "$tmp/o3"
    exit 1
fi
grep -q "E0053" "$tmp/o3" || { echo "FAIL: missing E0053 for unknown pipe"; cat "$tmp/o3"; exit 1; }

cat >"$tmp/pipe_value.pengu" <<'PENGU'
weave main into int:
    let x as int is 1 pipe 2
    return x
PENGU
if "$PSC" check "$tmp/pipe_value.pengu" >"$tmp/o4" 2>&1; then
    echo "FAIL: non-name pipe step accepted"
    cat "$tmp/o4"
    exit 1
fi
cat >"$tmp/chain_void.pengu" <<'PENGU'
rune Box:
    v as int
enchanting Box:
    weave identity into Box:
        return with v is self.v
    weave reset into void:
        set self->v is 0
weave main into int:
    var b as Box is with v is 7
    let c as Box is calling b.reset.identity
    return c.v
PENGU
if "$PSC" check "$tmp/chain_void.pengu" >"$tmp/o5" 2>&1; then
    echo "FAIL: intermediate void chain step accepted"
    cat "$tmp/o5"
    exit 1
fi
grep -q "chain step returns void" "$tmp/o5" || { echo "FAIL: wrong diagnostic for intermediate void"; cat "$tmp/o5"; exit 1; }

cat >"$tmp/chain_mut.pengu" <<'PENGU'
rune Box:
    v as int
enchanting Box:
    @mutates
    weave bump into Box:
        return with v is self.v + 1
    weave identity into Box:
        return with v is self.v
weave main into int:
    var b as Box is with v is 7
    let c as Box is calling b.bump.identity
    return c.v
PENGU
if "$PSC" check "$tmp/chain_mut.pengu" >"$tmp/o6" 2>&1; then
    echo "FAIL: intermediate mutating chain step accepted"
    cat "$tmp/o6"
    exit 1
fi
grep -q "mutating method used in the middle" "$tmp/o6" || { echo "FAIL: wrong diagnostic for intermediate mutating step"; cat "$tmp/o6"; exit 1; }

echo "OK chain guard"
