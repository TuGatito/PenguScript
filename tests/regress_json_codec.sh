#!/usr/bin/env bash
# Regresión: codecs de `derive Json` — C emitido, ida y vuelta y diagnósticos.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in
  /*) ;;
  *) PSC="$(cd "$(dirname "$PSC")" && pwd)/$(basename "$PSC")" ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

cat >"$tmp/ok.pengu" <<'PENGU'
import std.spark

rune Address derive Json:
    city as string
    zip as int

rune User derive Json:
    id as i64
    name as string
    @json("e-mail") email as string
    tags as list of string
    nick as maybe string
    address as Address

weave main into int:
    var address as Address is with city is "Madrid", zip is 28001
    var user as User is with id is 7, name is "Ana", email is "a@b.c", tags is ["x"], nick is (maybe none), address is (address)
    var text as string is calling user.to_json
    calling spark.println with text
    var back as result of User to string is calling User.from_json with text
    if not back.is_ok:
        return 1
    var again as string is calling back.value.to_json
    if again != text:
        return 2
    return 0
PENGU

out="$(cd "$tmp" && "$PSC" run ok.pengu --no-cache 2>&1)" || fail "el programa no compila/ejecuta: $out"
[ "$out" = '{"id":7,"name":"Ana","e-mail":"a@b.c","tags":["x"],"nick":null,"address":{"city":"Madrid","zip":28001}}' ] \
  || fail "JSON inesperado: $out"

"$PSC" emit-c "$tmp/ok.pengu" >"$tmp/ok.c" 2>/dev/null || fail "emit-c falló"
for sym in _pengu_json_encode_User _pengu_json_write_User _pengu_json_decode_User _pengu_json_read_User _pengu_json_free_User; do
  grep -q "$sym" "$tmp/ok.c" || fail "falta $sym en el C emitido"
done
grep -q "pengu_json_in_at_end(in)) break;" "$tmp/ok.c" || fail "el lector no inicializa contenedores con la guarda de cierre"
grep -q 'pengu_list_new' "$tmp/ok.c" || fail "el lector no reserva la lista"
grep -q 'pengu_json_box_error' "$tmp/ok.c" || fail "el decodificador no devuelve un error boxeado"
if grep -q 'implicit declaration' "$tmp/ok.c"; then
  fail "el C emitido tiene declaraciones implícitas"
fi

# --- Diagnósticos ---------------------------------------------------------
expect_error() {
  local name="$1" needle="$2"
  local src="$tmp/$name.pengu" log="$tmp/$name.log"
  shift 2
  : >"$src"
  for line in "$@"; do printf '%s\n' "$line" >>"$src"; done
  if "$PSC" check "$src" >"$log" 2>&1; then
    fail "$name: se aceptó y debía fallar"
  fi
  grep -qF "$needle" "$log" || { sed -n '1,12p' "$log" >&2; fail "$name: falta '$needle'"; }
}

expect_error "echo" "echo types cannot derive Json" \
  'echo Point derive Json:' '    x as int'

expect_error "generic" "generic runes cannot derive Json" \
  'rune Box shard T derive Json:' '    value as T'

expect_error "omen" "omen types cannot derive Json" \
  'omen Shape derive Json:' '    Empty' '    Named with name as string'

expect_error "omen_payload_field" "omen with payload cannot be serialized" \
  'omen Shape:' '    Empty' '    Named with name as string' \
  'rune User derive Json:' '    shape as Shape'

expect_error "nested" "does not derive Json" \
  'rune Inner:' '    n as int' 'rune Outer derive Json:' '    inner as Inner'

expect_error "attr" "is not supported by derive Json" \
  'rune User derive Json:' '    @format("email") mail as string'

expect_error "duplicate" "duplicate JSON name 'x' in this rune" \
  'rune User derive Json:' '    @json("x") a as int' '    @json("x") b as int'

expect_error "empty_name" "requires a non-empty string literal" \
  'rune User derive Json:' '    @json("") a as int'

expect_error "both" "are mutually exclusive" \
  'rune User derive Json:' '    @json("a") @skip b as int'

expect_error "unsupported" "does not support" \
  'rune User derive Json:' '    raw as result of int to string'

# Un rune que NO deriva Json sigue ignorando `@json` (compatibilidad).
cat >"$tmp/plain.pengu" <<'PENGU'
rune Plain:
    @json("x") n as int
weave main into int:
    return 0
PENGU
"$PSC" check "$tmp/plain.pengu" >"$tmp/plain.log" 2>&1 \
  || { cat "$tmp/plain.log" >&2; fail "un rune sin derive Json dejó de aceptar @json"; }

echo "OK json codec"
