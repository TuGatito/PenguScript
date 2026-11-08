#!/usr/bin/env bash
# E0083: `Arc of T` solo cruza un hilo si `T` es `@shared`.
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/t.pengu" <<'P'
import std.consortium
import std.filum

rune Node:
    value as int

weave work with n as Arc of Node into void:
    return

weave main into int:
    var x as Node is with value is 1
    var a as Arc of Node is calling Arc.new with x
    calling filum.start with work, a
    return 0
P
out="$("$root/build/psc" check "$tmp/t.pengu" 2>&1)"
case "$out" in
*"[E0083]"*) echo "OK arc unshared" ;;
*) echo "FAIL arc unshared: $out"; exit 1 ;;
esac
