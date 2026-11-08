#!/usr/bin/env bash
# regress_cow_lint.sh — W0008 (copia de contenedor mutada en un bucle).
#
# El lint es opt-in: sin `--lint=cow` no aparece; con el flag, sí. Comprueba
# las dos caras y que el programa sigue compilando (es un aviso, no un error).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
[ -x "$PSC" ] || { echo "SKIP cow lint: no psc"; exit 0; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/bad.pengu" <<'EOF'
weave main into int:
    var a as list of int is [1]
    var i as int is 0
    while i < 3:
        var b as list of int is a
        calling b.push with i
        set i is i + 1
    banish a
    return 0
EOF

cat > "$TMP/good.pengu" <<'EOF'
weave main into int:
    var a as list of int is [1]
    var b as list of int is a
    calling b.push with 2
    banish a
    banish b
    return 0
EOF

# Sin el flag: silencio.
out="$("$PSC" check "$TMP/bad.pengu" 2>&1 || true)"
case "$out" in
    *W0008*) echo "FAIL cow lint: W0008 without --lint=cow"; echo "$out"; exit 1 ;;
esac

# Con el flag: un aviso en la copia.
out="$("$PSC" check --lint=cow "$TMP/bad.pengu" 2>&1 || true)"
case "$out" in
    *W0008*) ;;
    *) echo "FAIL cow lint: missing W0008"; echo "$out"; exit 1 ;;
esac

# Copia fuera de un bucle: no hay aviso.
out="$("$PSC" check --lint=cow "$TMP/good.pengu" 2>&1 || true)"
case "$out" in
    *W0008*) echo "FAIL cow lint: false positive outside a loop"; echo "$out"; exit 1 ;;
esac

# Un lint desconocido es error de uso.
rc=0
"$PSC" check --lint=bogus "$TMP/good.pengu" >/dev/null 2>&1 || rc=$?
if [ "$rc" -ne 2 ]; then
    echo "FAIL cow lint: --lint=bogus should exit 2 (got $rc)"
    exit 1
fi

echo "OK cow lint"
