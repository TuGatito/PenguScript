#!/usr/bin/env bash
# Regresión: diagnósticos de los miembros especiales `born` (F2.3).
#
# El dialecto C++ exige que un constructor deje el valor completo:
#
#   E0100  `born` con `return` de un valor
#   E0105  `born` que no inicializa un campo
#   E0106  `with`/`T: …` sobre un tipo que declaró `born` (hay que usar `T.new`)
#   E0118  `born` con un único parámetro del propio tipo (eso es `born mirror`)
#
# Y el caso legítimo: un constructor con nombre (`ritual … into T`) devuelve
# `with …` para un tipo con `born`; ese `return with` no dispara E0106.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- E0100: `return` con valor dentro de `born` ------------------------------
cat > "$WORK/e0100.pengu" <<'PENGU'
rune C:
    a as int

enchanting C:
    weave born with x as int:
        set self->a is x
        return with a is x
PENGU
OUT100="$("$PSC" check "$WORK/e0100.pengu" 2>&1 || true)"
case "$OUT100" in
  *E0100*) : ;;
  *) fail "expected E0100 for 'return' inside 'born', got: $OUT100" ;;
esac

# --- E0105: campo sin inicializar en `born` ----------------------------------
cat > "$WORK/e0105.pengu" <<'PENGU'
rune C:
    a as int
    b as int

enchanting C:
    weave born with x as int:
        set self->a is x
PENGU
OUT105="$("$PSC" check "$WORK/e0105.pengu" 2>&1 || true)"
case "$OUT105" in
  *E0105*"'b'"*) : ;;
  *) fail "expected E0105 naming field 'b', got: $OUT105" ;;
esac

# --- E0106: `with` sobre un tipo con `born` ----------------------------------
cat > "$WORK/e0106.pengu" <<'PENGU'
rune P:
    a as int

rune C:
    a as int

enchanting C:
    weave born with x as int:
        set self->a is x

weave main into int:
    var p as P is with a is 1
    var c as C is with a is 2
    return p.a + c.a
PENGU
OUT106="$("$PSC" check "$WORK/e0106.pengu" 2>&1 || true)"
case "$OUT106" in
  *E0106*) : ;;
  *) fail "expected E0106 for 'with' on a 'born' type, got: $OUT106" ;;
esac
# El rune sin `born` no debe disparar el diagnóstico: un único E0106, y sobre
# la línea del tipo `C`.
N106="$(printf '%s\n' "$OUT106" | grep -c "E0106" || true)"
if [ "$N106" -ne 1 ]; then
  fail "expected exactly one E0106, got $N106: $OUT106"
fi
case "$OUT106" in
  *"as C is with"*) : ;;
  *) fail "E0106 must point at the 'born' type, got: $OUT106" ;;
esac

# --- E0118: `born` que copia -------------------------------------------------
cat > "$WORK/e0118.pengu" <<'PENGU'
rune C:
    a as int

enchanting C:
    weave born with other as C:
        set self->a is other.a
PENGU
OUT118="$("$PSC" check "$WORK/e0118.pengu" 2>&1 || true)"
case "$OUT118" in
  *E0118*) : ;;
  *) fail "expected E0118 for 'born' taking its own type, got: $OUT118" ;;
esac

# --- Casos legítimos: `born` completo y `ritual` que devuelve `with` --------
cat > "$WORK/ok.pengu" <<'PENGU'
rune C:
    a as int
    b as int

enchanting C:
    weave born with x as int:
        set self->a is x
        set self->b is 0

    weave ritual with_pair with x as int, y as int into C:
        return with a is x, b is y

weave main into int:
    var c as C is calling C.new with 1
    var d as C is calling C.with_pair with 2, 3
    if c.a == 1 and d.b == 3:
        return 0
    return 1
PENGU
"$PSC" check "$WORK/ok.pengu" >/dev/null 2>&1 || fail "legitimate 'born'/'ritual' rejected"
"$PSC" run "$WORK/ok.pengu" >/dev/null 2>&1 || fail "legitimate 'born' program failed in C"
"$PSC" run "$WORK/ok.pengu" --backend=cpp >/dev/null 2>&1 || fail "legitimate 'born' program failed in C++"

"$PSC" fmt --check "$WORK/ok.pengu" >/dev/null 2>&1 || fail "fmt --check failed on the valid fixture"

echo "OK born diagnostics (F2.3)"
