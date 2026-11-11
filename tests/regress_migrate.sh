#!/usr/bin/env bash
# Regresión: `psc migrate` (F2.1, migración mecánica de sintaxis).
#
# `psc migrate` solo cambia grafías que producen el mismo AST, así que el C
# emitido antes y después de migrar un archivo debe ser **byte a byte** igual
# (mismo nombre de archivo, mismas marcas `#line`).
#
# Cubre:
#   - `list of` -> `vector of`, `slice of` -> `span of`, `map of K to V` ->
#     `map of K, V`, también anidados;
#   - `--check` no escribe y sale con 1; sin `--check` escribe;
#   - idempotencia (`--check` a continuación sale con 0);
#   - el código migrado compila y corre igual (backend C y C++);
#   - `psc fmt --check` sigue limpio (la migración no rompe el formato);
#   - `to` de rangos (`for i in 0 to 5`) y de `result of T to E` no se tocan;
#   - comentarios y strings no se tocan.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

cat > "$WORK/app.pengu" <<'PENGU'
## `list of` en un comentario no debe cambiar: list of map of to.
rune Box:
    xs as list of int
    table as map of string to map of int to list of byte
    raw as slice of byte

weave main into int:
    var s as string is "list of map of to slice of"
    var xs as list of int is list of int
    var table as map of string to int is map of string to int
    calling xs.push with 2
    calling table.put with "k", 7
    var total as int is 0
    for i in 0 to 3:
        set total is total + i
    var r as result of int to string is calling ok_of with 1
    if s == "list of map of to slice of" and (xs at 0) == 2 and (table at "k") == 7 and total == 3:
        return 0
    return 1
PENGU

"$PSC" emit-c "$WORK/app.pengu" --out="$WORK/before.c" >/dev/null
cp "$WORK/app.pengu" "$WORK/before.pengu"
"$PSC" run "$WORK/app.pengu" --no-cache >/dev/null || fail "baseline C run failed"

# `--check` no escribe y avisa.
if "$PSC" migrate --check "$WORK" >/dev/null; then
  fail "--check returned 0 with pending migrations"
fi
cmp -s "$WORK/app.pengu" "$WORK/before.pengu" || fail "--check modified the file"

# Migrar.
"$PSC" migrate "$WORK" >/dev/null
grep -q 'xs as vector of int' "$WORK/app.pengu" || fail "list of was not migrated"
grep -q 'map of string, map of int, vector of byte' "$WORK/app.pengu" || fail "nested map was not migrated"
grep -q 'raw as span of byte' "$WORK/app.pengu" || fail "slice of was not migrated"
grep -q 'for i in 0 to 3:' "$WORK/app.pengu" || fail "range to was rewritten"
grep -q 'result of int to string' "$WORK/app.pengu" || fail "result of to was rewritten"
grep -q '## `list of` en un comentario' "$WORK/app.pengu" || fail "comment was rewritten"
grep -q '"list of map of to slice of"' "$WORK/app.pengu" || fail "string literal was rewritten"

# Idempotencia.
"$PSC" migrate --check "$WORK" >/dev/null || fail "migrate is not idempotent"

# Mismo C byte a byte (mismo nombre de archivo, mismas marcas #line).
"$PSC" emit-c "$WORK/app.pengu" --out="$WORK/after.c" >/dev/null
cmp -s "$WORK/before.c" "$WORK/after.c" || fail "migrating changed the emitted C"

# El código migrado corre igual en los dos backends.
"$PSC" run "$WORK/app.pengu" --no-cache >/dev/null || fail "migrated C run failed"
"$PSC" run "$WORK/app.pengu" --backend=cpp --no-cache >/dev/null || fail "migrated C++ run failed"

# Y sigue formateado.
"$PSC" fmt --check "$WORK" >/dev/null || fail "migrated file is not fmt-clean"

# Renombrados de palabras retiradas: solo identificadores, no strings.
cat > "$WORK/renames.pengu" <<'PENGU'
weave main into int:
    var nasci as int is 1
    var mori as int is nasci
    var imago as int is mori
    var namespace as int is imago
    if namespace == 1:
        return 0
    return 1
PENGU
"$PSC" migrate "$WORK/renames.pengu" >/dev/null
grep -q 'var born as int is 1' "$WORK/renames.pengu" || fail "nasci was not renamed"
grep -q 'var die as int is born' "$WORK/renames.pengu" || fail "mori was not renamed"
grep -q 'var mirror as int is die' "$WORK/renames.pengu" || fail "imago was not renamed"
grep -q 'var regnum as int is mirror' "$WORK/renames.pengu" || fail "namespace was not renamed"
"$PSC" run "$WORK/renames.pengu" --no-cache >/dev/null || fail "renamed file does not run"

echo "OK migrate (F2.1)"
