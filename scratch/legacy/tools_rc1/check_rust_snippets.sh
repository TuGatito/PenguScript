#!/usr/bin/env bash
# Extrae los bloques ```rust de docs/LANGUAGE.md y los compila con rustc.
#
# Uso:
#   scratch/tools/check_rust_snippets.sh [docs/LANGUAGE.md]
#
# Un bloque con `fn main` se compila como binario; uno con solo items se
# compila como librería. Si un bloque contiene sentencias sueltas, se intenta
# envolver en `fn main` como último recurso.

set -u

DOC="${1:-docs/LANGUAGE.md}"
if [[ ! -f "$DOC" ]]; then
    echo "ERROR: no existe $DOC" >&2
    exit 2
fi

if ! command -v rustc >/dev/null 2>&1; then
    echo "ERROR: rustc no está en PATH" >&2
    exit 2
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/pengu-rust-snippets.XXXXXX")" || exit 2
trap 'rm -rf "$TMP"' EXIT

awk -v out="$TMP" '
    /^[[:space:]]*```rust[[:space:]]*$/ { inside = 1; n++; file = sprintf("%s/snippet_%03d.rs", out, n); next }
    inside && /^[[:space:]]*```[[:space:]]*$/ { inside = 0; next }
    inside { print > file }
    END { print n + 0 > (out "/count") }
' "$DOC"

COUNT="$(cat "$TMP/count" 2>/dev/null || echo 0)"
if [[ "$COUNT" -eq 0 ]]; then
    echo "OK: no hay bloques rust en $DOC."
    exit 0
fi

fail=0
index=0
for file in "$TMP"/snippet_*.rs; do
    [[ -e "$file" ]] || continue
    index=$((index + 1))
    err="$TMP/err_$index.txt"
    out="$TMP/out_$index"

    if grep -qE '\bfn[[:space:]]+main\b' "$file"; then
        if ! rustc --edition 2024 -o "$out" "$file" 2>"$err"; then
            echo "FALLO: bloque rust #$index (binario)" >&2
            cat "$err" >&2
            fail=$((fail + 1))
            continue
        fi
    else
        if ! rustc --edition 2024 --crate-type lib --out-dir "$TMP" "$file" 2>"$err"; then
            # Último recurso: el bloque puede ser un fragmento de sentencias.
            {
                echo "fn main() {"
                cat "$file"
                echo "}"
            } >"$TMP/wrapped_$index.rs"
            if ! rustc --edition 2024 -o "$out" "$TMP/wrapped_$index.rs" 2>"$err"; then
                echo "FALLO: bloque rust #$index (items o fragmento)" >&2
                cat "$err" >&2
                fail=$((fail + 1))
                continue
            fi
        fi
    fi
    echo "OK: bloque rust #$index"
done

if [[ "$fail" -ne 0 ]]; then
    echo "FALLARON $fail de $COUNT bloques rust." >&2
    exit 1
fi

echo "OK: $COUNT/$COUNT bloques rust compilan con rustc --edition 2024."
