/* Regression probe for the 2.0.1 audit runtime fixes.
 *
 * Covers two heap-use-after-frees in the specialized string-to-int map entry
 * points (`pengu_map_put_string_int` / `pengu_map_remove_string_int`): under
 * ABI v2 a map owns only the key/value *bytes*, so freeing the `PenguString`
 * payload of a stored key freed memory that belonged to the caller.
 *
 * Compiled by `tests/stdlib/audit/test_runtime_memory.py` with ASan+UBSan.
 * Exits 0 when every check passes, 1 otherwise; ASan aborts on a memory error.
 */
#include "pengu_runtime.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      g_failures++;                                                          \
      fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, (msg));        \
    }                                                                        \
  } while (0)

static void test_put_string_int_rehash(void) {
  PenguMap m = pengu_map_new(sizeof(PenguString), sizeof(int32_t));
  PenguString keys[12];
  for (int i = 0; i < 12; ++i) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "key-%d", i);
    keys[i] = pengu_string_new(tmp); /* caller-owned payload */
    int32_t v = i * 10;
    pengu_map_put_string_int(&m, &keys[i], &v);
  }
  CHECK(m.len == 12, "12 inserts through put_string_int");
  for (int i = 0; i < 12; ++i) {
    int32_t *got = pengu_map_get_string_int(&m, &keys[i]);
    CHECK(got != NULL && *got == i * 10, "value survives the rehash");
    CHECK(keys[i].data != NULL && keys[i].is_owned == 1,
          "caller key payload survives the rehash");
  }
  for (int i = 0; i < 12; ++i)
    pengu_banish_string(&keys[i]);
  pengu_banish_map(&m);
}

static void test_remove_string_int(void) {
  PenguMap m = pengu_map_new(sizeof(PenguString), sizeof(int32_t));
  PenguString k = pengu_string_new("solo");
  int32_t v = 7;
  pengu_map_put_string_int(&m, &k, &v);
  CHECK(pengu_map_remove_string_int(&m, &k), "remove finds the key");
  CHECK(m.len == 0, "remove decrements len");
  CHECK(k.data != NULL && strcmp(k.data, "solo") == 0,
        "caller key payload survives remove");
  pengu_banish_string(&k); /* would double-free before the fix */
  pengu_banish_map(&m);
}

static void test_generic_map_owned_keys(void) {
  PenguMap m = pengu_map_new(sizeof(PenguString), sizeof(int32_t));
  PenguString keys[12];
  for (int i = 0; i < 12; ++i) {
    char tmp[32];
    snprintf(tmp, sizeof(tmp), "g-%d", i);
    keys[i] = pengu_string_new(tmp);
    int32_t v = i;
    pengu_map_put(&m, &keys[i], &v);
  }
  for (int i = 0; i < 12; ++i) {
    int32_t *got = (int32_t *)pengu_map_get(&m, &keys[i]);
    CHECK(got != NULL && *got == i, "generic map survives rehash");
  }
  for (int i = 0; i < 12; ++i)
    pengu_banish_string(&keys[i]);
  pengu_banish_map(&m);
}

static void test_zero_sized_map_layout(void) {
  /* pengu_map_new(0, 0) leaves key_size/val_size at 0; put_string_int must
   * pin the string-to-int layout instead of allocating zero-byte slots. */
  PenguMap m = pengu_map_new(0, 0);
  PenguString k = pengu_string_new("layout");
  int32_t v = 5;
  pengu_map_put_string_int(&m, &k, &v);
  int32_t *got = pengu_map_get_string_int(&m, &k);
  CHECK(got != NULL && *got == 5, "put_string_int fixes a zero-size map");
  pengu_banish_string(&k);
  pengu_banish_map(&m);
}

int main(void) {
  test_put_string_int_rehash();
  test_remove_string_int();
  test_generic_map_owned_keys();
  test_zero_sized_map_layout();
  if (g_failures != 0) {
    fprintf(stderr, "runtime_map_probe: %d failure(s)\n", g_failures);
    return 1;
  }
  printf("runtime_map_probe: ok\n");
  return 0;
}
