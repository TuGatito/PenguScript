#!/usr/bin/env bash
# Regresión: `derive` retirado (F2.2) y `psc migrate --drop-derive`.
#
# En F2 los conceptos `Par`, `Ordo`, `Nexus`, `Imago`, `Vinculum` y `Donum`
# dejan de derivarse: sus efectos son implícitos (`==`/`!=` y `<=>`
# estructurales, RAII, copia por defecto, hash explícito). Escribirlos da
# `E0005` con el sustituto en el `help`. `Json` sobrevive hasta F5 (único
# códec) y `Drop` hasta F2.3 (`born mirror`/`die`).
#
# Cubre:
#   - `derive Par`/`Nexus`/`Imago`/`Vinculum` dan `E0005` y mencionan "retired";
#   - el `help` nombra el sustituto;
#   - `derive Json` sigue generando códec y `derive Drop` sigue siendo move-only;
#   - `psc migrate --drop-derive` reescribe la cláusula conservando `Json`/`Drop`
#     y es idempotente;
#   - `banish` funciona sin `derive Nexus`;
#   - `==` compara por contenido (string/lista/mapa), no por puntero.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- 1. conceptos retirados: E0005 con sustituto -----------------------------
for concept in Par Nexus Imago Vinculum Ordo; do
cat > "$WORK/retired.pengu" <<PENGU
rune T derive $concept:
    x as int

weave main into int:
    return 0
PENGU
    out="$("$PSC" check "$WORK/retired.pengu" 2>&1 || true)"
    echo "$out" | grep -q "E0005" || fail "derive $concept no da E0005: $out"
    echo "$out" | grep -q "is retired in the C++ dialect" || fail "derive $concept sin mensaje de retirada: $out"
    echo "$out" | grep -qi "remove the concept from the clause" || fail "derive $concept sin help: $out"
done

# --- 2. `banish` sin `derive Nexus` -----------------------------------------
cat > "$WORK/banish.pengu" <<'PENGU'
rune Box:
    name as string
    xs as vector of int

weave main into int:
    var b as Box is with name is "hola", xs is [1, 2, 3]
    banish b
    return 0
PENGU
"$PSC" run "$WORK/banish.pengu" --no-cache >/dev/null 2>&1 || fail "banish sin derive Nexus no compila"

# --- 3. `==` estructural (string / lista / mapa) ----------------------------
cat > "$WORK/eq.pengu" <<'PENGU'
rune P:
    name as string
    xs as vector of int
    m as map of string, int

weave main into int:
    var a as P is with name is "x", xs is [1, 2], m is map of string, int
    var b as P is with name is "x", xs is [1, 2], m is map of string, int
    calling a.m.put with "k", 7
    calling b.m.put with "k", 7
    if a != b:
        return 1
    calling b.m.put with "k", 8
    if a == b:
        return 2
    if a.name != "x":
        return 3
    return 0
PENGU
"$PSC" run "$WORK/eq.pengu" --no-cache >/dev/null 2>&1 || fail "== estructural falla"

# --- 4. `derive Json` y `derive Drop` siguen vivos --------------------------
cat > "$WORK/json.pengu" <<'PENGU'
rune Point derive Json:
    x as int
    y as int

weave main into int:
    var p as Point is with x is 1, y is 2
    var s as string is calling p.to_json
    if s != "{\"x\":1,\"y\":2}":
        return 1
    var back as result of Point to string is calling Point.from_json with s
    if not back.is_ok:
        return 2
    return 0
PENGU
"$PSC" run "$WORK/json.pengu" --no-cache >/dev/null 2>&1 || fail "derive Json dejó de funcionar"

cat > "$WORK/drop.pengu" <<'PENGU'
rune Res derive Drop:
    fd as int

weave main into int:
    var r as Res is with fd is 3
    if r.fd != 3:
        return 1
    return 0
PENGU
"$PSC" run "$WORK/drop.pengu" --no-cache >/dev/null 2>&1 || fail "derive Drop dejó de funcionar"

# --- 5. `psc migrate --drop-derive` ----------------------------------------
cat > "$WORK/mig.pengu" <<'PENGU'
rune A derive Par, Nexus:
    x as int

rune B derive Nexus, Json:
    y as int

rune C derive Drop:
    z as int

weave main into int:
    return 0
PENGU
"$PSC" migrate --drop-derive "$WORK/mig.pengu" >/dev/null || fail "migrate --drop-derive falla"
grep -q "^rune A:$" "$WORK/mig.pengu" || fail "rune A no quedó sin cláusula: $(grep '^rune' "$WORK/mig.pengu")"
grep -q "^rune B derive Json:$" "$WORK/mig.pengu" || fail "rune B no conservó Json: $(grep '^rune' "$WORK/mig.pengu")"
grep -q "^rune C derive Drop:$" "$WORK/mig.pengu" || fail "rune C no conservó Drop: $(grep '^rune' "$WORK/mig.pengu")"
"$PSC" migrate --check --drop-derive "$WORK/mig.pengu" >/dev/null || fail "migrate --drop-derive no es idempotente"
"$PSC" fmt --check "$WORK/mig.pengu" >/dev/null || fail "el migrado no pasa fmt --check"

echo "OK derive retired (F2.2)"
