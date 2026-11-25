#!/usr/bin/env bash
# Mide el mismo programa con los dos backends y anota el factor.
#
# Uso: scripts/bench_backends.sh [vueltas]
# Requiere el compilador de C++ (para el backend nativo) y bun o node.

set -euo pipefail

vueltas="${1:-1000000}"
raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
trabajo="$(mktemp -d)"
trampa() { rm -rf "$trabajo"; }
trap trampa EXIT

cat > "$trabajo/main.pengu" <<EOF
invoke "std/io"

main = -> int
  mut total = 0
  for i = 1, ${vueltas}
    total += i * 2
  io::println("total #{total}")
  0
EOF

bun run "$raiz/src/main.ts" build "$trabajo/main.pengu" > /dev/null
bun run "$raiz/src/main.ts" build --target js --out "$trabajo/js" "$trabajo/main.pengu" > /dev/null

binario="$(find "$trabajo/.pengu-cache" -name program -type f | head -1)"
runtime=""
if command -v bun > /dev/null 2>&1; then
  runtime="bun"
elif command -v node > /dev/null 2>&1; then
  runtime="node"
else
  echo "no hay bun ni node para ejecutar el JavaScript" >&2
  exit 1
fi

medir() {
  local etiqueta="$1"
  shift
  local mejor=""
  for _ in 1 2 3 4 5; do
    local inicio fin
    inicio=$(date +%s%N)
    "$@" > /dev/null
    fin=$(date +%s%N)
    local ms=$(( (fin - inicio) / 1000000 ))
    if [ -z "$mejor" ] || [ "$ms" -lt "$mejor" ]; then mejor="$ms"; fi
  done
  echo "$etiqueta $mejor"
}

leer_ms() { echo "$1" | awk '{ print $2 }'; }

cpp_ms=$(leer_ms "$(medir cpp "$binario")")
js_ms=$(leer_ms "$(medir "$runtime" "$runtime" "$trabajo/js/index.mjs")")

echo "vueltas:  $vueltas"
echo "C++20:    ${cpp_ms} ms"
echo "JS (${runtime}): ${js_ms} ms"

awk -v c="$cpp_ms" -v j="$js_ms" 'BEGIN {
  if (c <= 0) c = 1;
  printf "factor:   %.1fx (JavaScript / C++)\n", j / c;
}'
