#!/usr/bin/env bash
# E0082: un `Rc` no cruza la frontera de un hilo.
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/t.pengu" <<'P'
import std.consortium
import std.filum

rune Node:
    value as int

weave work with n as Rc of Node into void:
    return

weave main into int:
    var x as Node is with value is 1
    var a as Rc of Node is calling Rc.new with x
    calling filum.start with work, a
    return 0
P
out="$("$root/build/psc" check "$tmp/t.pengu" 2>&1)"
case "$out" in
*"[E0082]"*) echo "OK rc thread" ;;
*) echo "FAIL rc thread: $out"; exit 1 ;;
esac
