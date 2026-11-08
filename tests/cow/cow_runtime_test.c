/*
 * Prueba unitaria del COW del runtime (fase 6, ABI 4).
 *
 * Comprueba las tres capas del runtime sin pasar por el compilador:
 *   - strings: compartir, ensure_unique, drop, y mezcla con un string legacy;
 *   - listas: compartir, clonar al mutar, drop recursivo de elementos y
 *     listas de arena (`cap < 0`) que nunca llevan cabecera;
 *   - mapas: compartir, clonar al insertar, conservar entradas y drop.
 *
 * Devuelve 0 si todo pasa; imprime el primer fallo y devuelve 1.
 */
#include "pengu_runtime.h"

#include <stdio.h>
#include <string.h>

static int g_failures = 0;

static void check(bool cond, const char *what)
{
  if (!cond)
  {
    printf("FAIL %s\n", what);
    g_failures++;
  }
}

static int g_dropped = 0;

static void count_drop(void *p)
{
  (void)p;
  g_dropped++;
}

static void test_strings(void)
{
  PenguString a = pengu_cow_string_new("hola", 4);
  PenguString b = a;
  check(pengu_cow_string_ref_count(a) == 1, "string: rc inicial 1");
  check(!pengu_cow_string_is_shared(a), "string: no compartido");
  pengu_cow_string_share(&a);
  check(pengu_cow_string_ref_count(a) == 2, "string: rc 2 tras share");
  check(pengu_cow_string_is_shared(b), "string: compartido");

  pengu_cow_string_ensure_unique(&a);
  check(pengu_cow_string_ref_count(a) == 1, "string: rc 1 tras unique");
  check(a.data != b.data, "string: ensure_unique separa el buffer");
  check(a.len == 4 && memcmp(a.data, "hola", 4) == 0, "string: contenido tras unique");
  check(pengu_cow_string_ref_count(b) == 1, "string: el original queda con rc 1");

  /* Mezcla: un string legacy convive con uno COW. */
  {
    PenguString legacy = pengu_string_from_cstr("legacy");
    check(legacy.is_owned == PENGU_STRING_BORROWED, "string: la vista no es owned");
    pengu_cow_string_share(&legacy);
    check(legacy.is_owned == PENGU_STRING_OWNED_COW, "string: la vista se promociona a COW");
    check(pengu_cow_string_ref_count(legacy) == 1, "string: promocion con rc 1");
    pengu_banish_string(&legacy);
    check(legacy.data == NULL, "string: banish de un COW lo vacia");
  }

  b = a;
  pengu_banish_string(&a);
  check(a.data == NULL, "string: banish del primer handle");
  check(b.data != NULL && b.len == 4, "string: el segundo handle sigue vivo");
  pengu_banish_string(&b);
}

static void test_lists(void)
{
  PenguList a = pengu_cow_list_new(sizeof(int), 2);
  PenguList b;
  int v = 10;
  check(a.len == 0 && a.cap >= 2, "list: arranca vacia");
  pengu_cow_list_push(&a, &v);
  v = 20;
  pengu_cow_list_push(&a, &v);
  check(a.len == 2, "list: dos elementos");
  check(*(int *)pengu_cow_list_at(&a, 1) == 20, "list: at devuelve el elemento");

  b = a;
  pengu_cow_list_share(&b);
  check(pengu_cow_list_ref_count(&a) == 2, "list: rc 2 tras share");

  v = 30;
  pengu_cow_list_push(&b, &v);
  check(b.len == 3, "list: el que muta crece");
  check(a.len == 2, "list: el original no cambia");
  check(pengu_cow_list_ref_count(&b) == 1, "list: el que muta se separa");
  check(*(int *)pengu_cow_list_at(&a, 1) == 20, "list: el original conserva datos");
  check(*(int *)pengu_cow_list_at(&b, 2) == 30, "list: el nuevo tiene el dato");

  pengu_cow_list_drop(&a);
  check(a.data == NULL, "list: drop deja el handle vacio");
  check(pengu_cow_list_at(&b, 0) != NULL, "list: el otro handle sigue vivo");
  pengu_cow_list_drop(&b);

  /* Drop recursivo: cada elemento se libera una sola vez. */
  {
    PenguList owned = pengu_cow_list_new(sizeof(PenguString), 2);
    PenguString *slot;
    PenguString s;
    g_dropped = 0;
    pengu_cow_list_drop_elem_hook(&owned, count_drop);
    s = pengu_cow_string_new("x", 1);
    pengu_cow_list_push(&owned, &s);
    s = pengu_cow_string_new("y", 1);
    pengu_cow_list_push(&owned, &s);
    slot = (PenguString *)pengu_cow_list_at(&owned, 0);
    pengu_banish_string(slot);
    slot = (PenguString *)pengu_cow_list_at(&owned, 1);
    pengu_banish_string(slot);
    pengu_cow_list_drop(&owned);
    check(g_dropped == 2, "list: drop recursivo llama al hook por elemento");
  }

  /* Lista de arena: cap < 0, sin cabecera COW, banish normal. */
  {
    int arena_storage[3];
    PenguList arena;
    arena.data = arena_storage;
    arena.len = 3;
    arena.cap = -3;
    arena.elem_size = sizeof(int);
    arena_storage[0] = 1;
    pengu_banish_list(&arena);
    check(arena.data == NULL && arena.cap == 0, "list: banish de arena no revienta");
  }
}

static void test_maps(void)
{
  PenguMap a = pengu_cow_map_new(sizeof(int), sizeof(int));
  PenguMap b;
  int k = 1;
  int v = 100;
  check(pengu_cow_map_ref_count(&a) == 1, "map: rc inicial 1");
  pengu_cow_map_put(&a, &k, &v);
  check(a.len == 1, "map: una entrada");

  b = a;
  pengu_cow_map_share(&b);
  check(pengu_cow_map_ref_count(&a) == 2, "map: rc 2 tras share");

  k = 2;
  v = 200;
  pengu_cow_map_put(&b, &k, &v);
  check(b.len == 2, "map: el que muta crece");
  check(a.len == 1, "map: el original no cambia");
  check(pengu_cow_map_ref_count(&b) == 1, "map: el que muta se separa");
  k = 1;
  v = 0;
  check(pengu_cow_map_get(&a, &k) != NULL && *(int *)pengu_cow_map_get(&a, &k) == 100,
        "map: el original conserva el valor");
  k = 2;
  check(pengu_cow_map_get(&b, &k) != NULL && *(int *)pengu_cow_map_get(&b, &k) == 200,
        "map: el nuevo tiene la entrada");

  pengu_cow_map_drop(&a);
  check(a.state == NULL, "map: drop deja el handle vacio");
  pengu_cow_map_drop(&b);
}

int main(void)
{
  test_strings();
  test_lists();
  test_maps();
  if (g_failures != 0)
  {
    printf("cow runtime: %d fallo(s)\n", g_failures);
    return 1;
  }
  printf("cow runtime ok\n");
  return 0;
}
