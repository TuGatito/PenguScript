#!/usr/bin/env bash
# Regresión: miembros especiales `born`, `born mirror` y `die` (F2.3).
#
# F2.3 introduce la sintaxis del dialecto C++ para los tres miembros
# especiales, que se declaran dentro de `enchanting`:
#
#   weave born with ...:              constructor que escribe en `self`
#   weave born mirror with other ...: copia propia (la usa `_pengu_clone_T`)
#   weave die:                        destructor (corre dentro del cleanup)
#
# `calling T.new` sigue siendo el nombre de llamada del constructor.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

cat > "$WORK/trio.pengu" <<'PENGU'
rune Buffer:
    data as string
    size as int
    tag as int

enchanting Buffer:
    weave born with cap as int:
        set self->data is ""
        set self->size is cap
        set self->tag is 0

    weave born mirror with other as ref to frozen Buffer:
        set self->data is other->data
        set self->size is other->size
        set self->tag is other->tag

    weave die:
        set self->tag is 0

weave main into int:
    var a as Buffer is calling Buffer.new with 7
    if a.size != 7:
        return 1
    var ar as ref to frozen Buffer is sigil of a
    var b as Buffer is calling Buffer.mirror with ar
    if b.size != 7:
        return 2
    set b.size is 9
    if a.size != 7:
        return 3
    banish b
    banish a
    return 0
PENGU

# 1. Los tres miembros compilan y corren en los dos backends.
"$PSC" run "$WORK/trio.pengu" --no-cache >/dev/null || fail "psc run (C) failed"
"$PSC" run "$WORK/trio.pengu" --backend=cpp --no-cache >/dev/null || fail "psc run (C++) failed"

# 2. El emisor conecta los tres: constructor con `self`, clon que delega en
#    `mirror`, y destructor como primera línea del cleanup.
"$PSC" emit-c "$WORK/trio.pengu" --no-line-markers --out="$WORK/trio.c" >/dev/null
grep -q 'Buffer\* self = &_pengu_self;' "$WORK/trio.c" || fail "born does not declare self"
grep -q 'return _pengu_self;' "$WORK/trio.c" || fail "born does not return the built value"
grep -q '\*out = Buffer_mirror(v);' "$WORK/trio.c" || fail "clone does not delegate to mirror"
# `die` corre antes de que la cleanup libere los campos.
die_line="$(grep -n 'Buffer_die(p);' "$WORK/trio.c" | tail -1 | cut -d: -f1)"
release_line="$(grep -n 'pengu_banish_string(&(p->data));' "$WORK/trio.c" | tail -1 | cut -d: -f1)"
[ -n "$die_line" ] && [ -n "$release_line" ] || fail "die/release not found in the cleanup"
[ "$die_line" -lt "$release_line" ] || fail "die runs after the fields are released"

# 3. `mirror` sin el modificador `born` es un método normal, no la copia:
#    el clon NO delega en él.
cat > "$WORK/plain_mirror.pengu" <<'PENGU'
rune Bad:
    n as int

enchanting Bad:
    weave mirror with other as ref to frozen Bad into Bad:
        return with n is other->n

weave main into int:
    var b as Bad is with n is 1
    var br as ref to frozen Bad is sigil of b
    var c as Bad is calling Bad.mirror with br
    banish c
    banish b
    return 0
PENGU
"$PSC" run "$WORK/plain_mirror.pengu" --no-cache >/dev/null || fail "plain mirror method failed"
"$PSC" emit-c "$WORK/plain_mirror.pengu" --no-line-markers --out="$WORK/plain_mirror.c" >/dev/null
if grep -q 'Bad_mirror(v)' "$WORK/plain_mirror.c"; then
  fail "clone delegated to a plain 'mirror' method"
fi

# 4. `born` sin nombre de miembro no es un método válido.
cat > "$WORK/bad2.pengu" <<'PENGU'
rune Bad:
    n as int

enchanting Bad:
    weave born helper with x as int:
        set self->n is x

weave main into int:
    return 0
PENGU
if out2="$("$PSC" check "$WORK/bad2.pengu" 2>&1)"; then
  fail "'born helper' was accepted"
fi
case "$out2" in
  *"member modifier"*) ;;
  *) fail "'born helper': unexpected diagnostic: $out2" ;;
esac

echo "OK born/die/mirror (F2.3)"
