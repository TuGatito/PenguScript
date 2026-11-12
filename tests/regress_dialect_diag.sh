#!/usr/bin/env bash
# Regresión de los diagnósticos del dialecto C++ añadidos en F2.7:
# E0121 (clave de mapa con payload), tipos que aún no existen (F3) y
# W0019 (atributo desconocido / @repr(c) sin efecto).
set -u

cd "$(dirname "$0")/.."
PSC="${PSC:-./build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

check_has() { # file, pattern, label
    local out
    out="$("$PSC" check "$1" 2>&1 || true)"
    case "$out" in
    *"$2"*) ;;
    *)
        echo "FAIL: $3 (no apareció '$2')"
        echo "$out" | head -6
        fail=1
        ;;
    esac
}

cat > "$TMP/key_list.pengu" <<'EOF'
weave take with m as map of vector of int, int into int:
    return m.len
EOF
check_has "$TMP/key_list.pengu" "E0121" "clave de mapa con lista"

cat > "$TMP/key_rune.pengu" <<'EOF'
rune K:
    b as string

weave take with m as map of K, int into int:
    return m.len
EOF
check_has "$TMP/key_rune.pengu" "E0121" "clave de mapa runa con string"

cat > "$TMP/pending.pengu" <<'EOF'
weave take with s as set of int into int:
    return 0
EOF
check_has "$TMP/pending.pengu" "is not available yet" "tipo pendiente 'set'"

cat > "$TMP/attr.pengu" <<'EOF'
@bogus
rune P:
    x as int

weave main into int:
    var p as P is with x is 1
    return p.x
EOF
check_has "$TMP/attr.pengu" "W0019" "atributo desconocido"

cat > "$TMP/repr.pengu" <<'EOF'
@repr(c)
rune P:
    x as int

weave main into int:
    var p as P is with x is 1
    return p.x
EOF
check_has "$TMP/repr.pengu" "has no effect yet" "@repr(c) avisa"

# Casos válidos: claves string/int y runa de campos escalares.
cat > "$TMP/ok.pengu" <<'EOF'
rune K:
    a as int

weave main into int:
    var m as map of string, int is map of string, int
    calling m.put with "a", 1
    var n as map of int, int is map of int, int
    calling n.put with 2, 3
    var r as map of K, int is map of K, int
    var k1 as K is with a is 5
    var k2 as K is with a is 5
    calling r.put with k1, 9
    if not (calling r.has with k2):
        return 1
    if not (calling m.has with "a"):
        return 2
    if not (calling n.has with 2):
        return 3
    return 0
EOF
for backend in c cpp; do
    if ! "$PSC" run "$TMP/ok.pengu" --backend="$backend" > "$TMP/ok_$backend.out" 2>&1; then
        echo "FAIL: claves válidas en backend $backend"
        head -6 "$TMP/ok_$backend.out"
        fail=1
    fi
done

if [ "$fail" -eq 0 ]; then
    echo "OK dialect diagnostics (F2.7)"
fi
exit "$fail"
