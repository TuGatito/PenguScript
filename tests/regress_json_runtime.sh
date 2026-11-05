#!/usr/bin/env bash
# Regresión: los helpers `pengu_json_*` del runtime (escritor, lector, escapes,
# errores con posición, `skip`, guardia de profundidad y `pengu_map_iter_value`).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

command -v gcc >/dev/null 2>&1 || { echo "SKIP json runtime (no gcc)"; exit 0; }

cat >"$tmp/rt.c" <<'C'
#include <pengu_runtime.h>

static int fails = 0;

static void check(bool ok, const char *what)
{
  if (!ok)
  {
    fails++;
    fprintf(stderr, "FAIL: %s\n", what);
  }
}

static char *finish(PenguJsonOut *o)
{
  PenguString s = pengu_json_out_finish(o);
  char *out = (char *)malloc((size_t)s.len + 1);
  memcpy(out, s.data, (size_t)s.len);
  out[s.len] = '\0';
  pengu_banish_string(&s);
  return out;
}

static bool parse_bad(const char *text, const char *needle, PenguString *err)
{
  PenguJsonIn in;
  pengu_json_in_init(&in, pengu_string_from_cstr(text));
  if (err->is_owned)
    pengu_banish_string(err);
  *err = pengu_json_no_error();
  bool ok = pengu_json_in_skip(&in, err);
  if (ok)
    return false;
  return err->data != NULL && strstr(err->data, needle) != NULL;
}

int main(void)
{
  /* Escritor: objetos, arrays, strings escapados y números. */
  PenguJsonOut o;
  pengu_json_out_init(&o);
  pengu_json_out_char(&o, '{');
  pengu_json_out_string(&o, pengu_string_from_cstr("k\"y"));
  pengu_json_out_char(&o, ':');
  pengu_json_out_char(&o, '[');
  pengu_json_out_i64(&o, -12);
  pengu_json_out_char(&o, ',');
  pengu_json_out_u64(&o, 18446744073709551615ULL);
  pengu_json_out_char(&o, ',');
  pengu_json_out_f64(&o, 1.5);
  pengu_json_out_char(&o, ',');
  pengu_json_out_cstr(&o, "true");
  pengu_json_out_char(&o, ']');
  pengu_json_out_char(&o, '}');
  char *text = finish(&o);
  check(strcmp(text, "{\"k\\\"y\":[-12,18446744073709551615,1.5,true]}") == 0,
        "escritor: objeto anidado");
  free(text);

  /* Lector: recorrido completo con `more`/`key`/`in_object_end`. */
  PenguJsonIn in;
  PenguString err = pengu_json_no_error();
  pengu_json_in_init(&in, pengu_string_from_cstr("{\"a\":[1,2],\"b\":\"x\\u00e9\"}"));
  check(pengu_json_in_object_begin(&in, &err), "lector: abre objeto");
  bool more = false;
  PenguString key;
  check(pengu_json_in_key(&in, &key, &err), "lector: lee clave 'a'");
  check(pengu_json_key_eq(key, "a"), "lector: clave 'a' coincide");
  pengu_banish_string(&key);
  check(pengu_json_in_skip(&in, &err), "lector: skip de array");
  check(pengu_json_in_more(&in, &more, &err) && more, "lector: sigue segundo campo");
  check(pengu_json_in_key(&in, &key, &err) && pengu_json_key_eq(key, "b"), "lector: clave 'b'");
  pengu_banish_string(&key);
  PenguString val;
  check(pengu_json_in_string(&in, &val, &err), "lector: string con \\u");
  check(val.len == 3 && memcmp(val.data, "x\xc3\xa9", 3) == 0, "lector: UTF-8 desde \\u00e9");
  pengu_banish_string(&val);
  check(pengu_json_in_more(&in, &more, &err) && !more, "lector: cierre de objeto");
  check(pengu_json_in_object_end(&in, &err), "lector: cierra objeto");
  check(pengu_json_in_finish(&in, &err), "lector: sin basura final");
  if (err.is_owned)
    pengu_banish_string(&err);

  /* Surrogantes y NUL embebido. */
  pengu_json_in_init(&in, pengu_string_from_cstr("\"\\ud83d\\ude00\\u0000z\""));
  err = pengu_json_no_error();
  check(pengu_json_in_string(&in, &val, &err), "lector: surrogantes");
  check(val.len == 6 && memcmp(val.data, "\xf0\x9f\x98\x80\x00z", 6) == 0,
        "lector: emoji + NUL embebido");
  pengu_banish_string(&val);
  if (err.is_owned)
    pengu_banish_string(&err);

  /* Errores de sintaxis con línea/columna. */
  err = pengu_json_no_error();
  check(parse_bad("\"\\q\"", "escape", &err), "error: escape inválido");
  check(parse_bad("\"\x01\"", "control", &err), "error: control crudo");
  check(parse_bad("\"\xff\"", "UTF-8", &err), "error: UTF-8 inválido");
  check(parse_bad("[1,]", "expected a JSON value", &err), "error: coma colgante");
  check(parse_bad("[1,2", "line 1", &err), "error: posición en el mensaje");
  if (err.is_owned)
    pengu_banish_string(&err);

  /* Gramática numérica estricta y rangos. */
  err = pengu_json_no_error();
  int64_t i = 0;
  pengu_json_in_init(&in, pengu_string_from_cstr("1.5"));
  check(!pengu_json_in_integer(&in, &i, &err), "error: decimal no es entero");
  pengu_json_in_init(&in, pengu_string_from_cstr("-0"));
  check(pengu_json_in_integer(&in, &i, &err) && i == 0, "lector: -0 entero");
  uint64_t u = 0;
  pengu_json_in_init(&in, pengu_string_from_cstr("18446744073709551615"));
  check(pengu_json_in_uinteger(&in, &u, &err), "lector: u64 máximo");
  double d = 0;
  pengu_json_in_init(&in, pengu_string_from_cstr("1e+300"));
  check(pengu_json_in_f64(&in, &d, &err) && d > 1e299, "lector: exponente f64");
  check(!pengu_json_range_i64(300, 8, &err, "x"), "rango: 300 no cabe en i8");
  check(pengu_json_range_u64(255, 8, false, &err, "x"), "rango: 255 cabe en u8");
  if (err.is_owned)
    pengu_banish_string(&err);

  /* Guardia de profundidad. */
  {
    char deep[256];
    int n = 0;
    for (int k = 0; k < 70; k++)
      deep[n++] = '[';
    deep[n] = '\0';
    err = pengu_json_no_error();
    check(parse_bad(deep, "depth", &err), "error: profundidad máxima");
    if (err.is_owned)
      pengu_banish_string(&err);
  }

  /* Mapas: `pengu_map_iter_value` devuelve el valor del iterador actual. */
  {
    PenguMap m = pengu_map_new(sizeof(PenguString), sizeof(int));
    PenguString mk = pengu_string_from_cstr("k");
    int mv = 7;
    pengu_map_put(&m, &mk, &mv);
    PenguMapIter it = pengu_map_iter_begin(&m);
    check(pengu_map_iter_valid(&it), "mapa: iterador válido");
    check(*(int *)pengu_map_iter_value(&it) == 7, "mapa: iter_value");
    check(pengu_json_key_eq(*(PenguString *)pengu_map_iter_key(&it), "k"), "mapa: iter_key");
    pengu_banish_map(&m);
  }

  /* Caja del error. */
  {
    PenguString msg = pengu_string_owned("boom", 4);
    PenguString *boxed = pengu_json_box_error(&msg);
    check(boxed->len == 4 && memcmp(boxed->data, "boom", 4) == 0, "error: box");
    pengu_banish_string(boxed);
    free(boxed);
  }

  if (fails != 0)
    return 1;
  printf("rt-json-ok\n");
  return 0;
}
C

gcc -std=c11 -Wall -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE -fsanitize=address -g -O1 \
  -I "$ROOT/build/include" -I "$ROOT/std_c" -I "$ROOT/std_c/sds" \
  "$tmp/rt.c" -L "$ROOT/build/lib" -lpengu_runtime -lminiz -lre -lm -pthread -ldl \
  -o "$tmp/rt" 2>"$tmp/cc.err" || { echo "FAIL: no compila el test del runtime"; cat "$tmp/cc.err"; exit 1; }

out="$("$tmp/rt" 2>&1)" || { echo "FAIL: el test del runtime falló"; printf '%s\n' "$out"; exit 1; }
printf '%s' "$out" | grep -q 'rt-json-ok' || { echo "FAIL: sin salida OK"; printf '%s\n' "$out"; exit 1; }
if printf '%s' "$out" | grep -qE 'LeakSanitizer|detected memory leaks|AddressSanitizer'; then
  echo "FAIL: ASAN detectó una fuga en el runtime JSON"
  printf '%s\n' "$out" | head -20
  exit 1
fi
echo "OK json runtime"
