/*
 * pengu_cc_extra.c — CC-backed helper surfaces for the new container types
 * exposed by the standard library (linked list, unordered set, ordered set and
 * ordered map).
 *
 * These are intentionally concrete for the types the current language can
 * monomorphise safely (`int` and `string`).  The language-facing runes live in
 * std/ordinal.pengu; this TU only knows sizes, a small `kind` tag and CC.
 */

#define CC_NO_SHORT_NAMES 1
#include "pengu_runtime.h"
#include "cc.h"

enum
{
  PENGU_CC_KIND_INT = 0,
  PENGU_CC_KIND_STRING = 1
};

static inline int pengu_cc_string_eq(PenguString a, PenguString b)
{
  return pengu_string_equal(a, b) ? 1 : 0;
}

static inline int pengu_cc_string_cmp(PenguString a, PenguString b)
{
  return pengu_string_compare(a, b);
}

/* =========================================================================
 * Linked list
 * ========================================================================= */

typedef struct
{
  void *cc;
  size_t elem_size;
  int kind;
} PenguCcLinkedList;

void *ccx_ll_new(int elem_size, int kind)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)calloc(1, sizeof(*state));
  if (!state)
    return NULL;
  state->elem_size = elem_size > 0 ? (size_t)elem_size : 1;
  state->kind = kind;
  state->cc = (void *)&cc_list_placeholder;
  return state;
}

void ccx_ll_push_back_int(void *handle, int32_t value)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state)
    return;
  cc_allocing_fn_result_ty result =
      cc_list_push(state->cc, &value, state->elem_size, realloc);
  if (result.other_ptr)
    state->cc = result.new_cntr;
}

void ccx_ll_push_front_int(void *handle, int32_t value)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state)
    return;
  void *first = cc_list_first(state->cc, state->elem_size, 0);
  cc_allocing_fn_result_ty result =
      cc_list_insert(state->cc, &value, &first, false, state->elem_size, 0, NULL,
                     NULL, 0.0, NULL, NULL, realloc, NULL);
  if (result.other_ptr)
    state->cc = result.new_cntr;
}

void ccx_ll_push_back_string(void *handle, PenguString value)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state)
    return;
  cc_allocing_fn_result_ty result =
      cc_list_push(state->cc, &value, state->elem_size, realloc);
  if (result.other_ptr)
    state->cc = result.new_cntr;
}

void ccx_ll_push_front_string(void *handle, PenguString value)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state)
    return;
  void *first = cc_list_first(state->cc, state->elem_size, 0);
  cc_allocing_fn_result_ty result =
      cc_list_insert(state->cc, &value, &first, false, state->elem_size, 0, NULL,
                     NULL, 0.0, NULL, NULL, realloc, NULL);
  if (result.other_ptr)
    state->cc = result.new_cntr;
}

bool ccx_ll_pop_front_int(void *handle, int32_t *out)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state || !out)
    return false;
  void *first = cc_list_first(state->cc, state->elem_size, 0);
  if (first == cc_list_end(state->cc, state->elem_size, 0))
    return false;
  *out = *(int32_t *)first;
  cc_list_erase(state->cc, &first, state->elem_size, 0, NULL, NULL, NULL, NULL,
                free);
  return true;
}

bool ccx_ll_pop_front_string(void *handle, PenguString *out)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state || !out)
    return false;
  void *first = cc_list_first(state->cc, state->elem_size, 0);
  if (first == cc_list_end(state->cc, state->elem_size, 0))
    return false;
  *out = *(PenguString *)first;
  cc_list_erase(state->cc, &first, state->elem_size, 0, NULL, NULL, NULL, NULL,
                free);
  return true;
}

int ccx_ll_len(void *handle)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  return state ? (int)cc_list_size(state->cc) : 0;
}

PenguList ccx_ll_items_int(void *handle)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  PenguList out = pengu_list_new(sizeof(int32_t), state ? (size_t)cc_list_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_list_first(state->cc, state->elem_size, 0);
       it != cc_list_end(state->cc, state->elem_size, 0);
       it = cc_list_next(state->cc, it, state->elem_size, 0))
    pengu_list_push(&out, it);
  return out;
}

PenguList ccx_ll_items_string(void *handle)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  PenguList out = pengu_list_new(sizeof(PenguString), state ? (size_t)cc_list_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_list_first(state->cc, state->elem_size, 0);
       it != cc_list_end(state->cc, state->elem_size, 0);
       it = cc_list_next(state->cc, it, state->elem_size, 0))
    pengu_list_push(&out, it);
  return out;
}

void ccx_ll_clear(void *handle)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state)
    return;
  cc_list_clear(state->cc, state->elem_size, 0, NULL, NULL, free);
}

void ccx_ll_free(void *handle)
{
  PenguCcLinkedList *state = (PenguCcLinkedList *)handle;
  if (!state)
    return;
  cc_list_cleanup(state->cc, state->elem_size, 0, NULL, NULL, free);
  free(state);
}

/* =========================================================================
 * Unordered set
 * ========================================================================= */

typedef struct
{
  void *cc;
  size_t key_size;
  uint64_t layout;
  int kind;
} PenguCcSet;

static PENGU_THREAD_LOCAL PenguCcSet *g_pengu_cc_set_ctx = NULL;

static size_t pengu_cc_set_hash(void *key)
{
  PenguCcSet *ctx = g_pengu_cc_set_ctx;
  if (!ctx || !key)
    return 0;
  if (ctx->kind == PENGU_CC_KIND_STRING)
  {
    PenguString *s = (PenguString *)key;
    if (!s->data || s->len <= 0)
      return 0;
    return (size_t)pengu_hash_bytes(s->data, (size_t)s->len);
  }
  return (size_t)pengu_hash_bytes(key, ctx->key_size);
}

static int pengu_cc_set_eq(void *a, void *b)
{
  PenguCcSet *ctx = g_pengu_cc_set_ctx;
  if (!ctx || !a || !b)
    return 0;
  if (ctx->kind == PENGU_CC_KIND_STRING)
    return pengu_cc_string_eq(*(PenguString *)a, *(PenguString *)b);
  return memcmp(a, b, ctx->key_size) == 0 ? 1 : 0;
}

static int pengu_cc_set_cmp(void *a, void *b)
{
  PenguCcSet *ctx = g_pengu_cc_set_ctx;
  if (!ctx || !a || !b)
    return a != b;
  if (ctx->kind == PENGU_CC_KIND_STRING)
    return pengu_cc_string_cmp(*(PenguString *)a, *(PenguString *)b);
  if (ctx->key_size == sizeof(int32_t))
    return (*(int32_t *)a > *(int32_t *)b) - (*(int32_t *)a < *(int32_t *)b);
  return memcmp(a, b, ctx->key_size);
}

static inline uint64_t pengu_cc_set_layout(size_t key_size, int ordered)
{
  const uint64_t align = (uint64_t)_Alignof(max_align_t);
  return cc_layout(ordered ? CC_OSET : CC_SET, key_size, align,
                   (cc_key_details_ty){key_size, align});
}

void *ccx_uset_new(int key_size, int kind)
{
  PenguCcSet *state = (PenguCcSet *)calloc(1, sizeof(*state));
  if (!state)
    return NULL;
  state->key_size = key_size > 0 ? (size_t)key_size : 1;
  state->kind = kind;
  state->layout = pengu_cc_set_layout(state->key_size, 0);
  state->cc = (void *)&cc_map_placeholder;
  return state;
}

static bool ccx_uset_insert(PenguCcSet *state, void *key)
{
  if (!state)
    return false;
  g_pengu_cc_set_ctx = state;
  cc_allocing_fn_result_ty result = cc_set_insert(
      state->cc, key, false, state->layout, pengu_cc_set_hash, pengu_cc_set_eq,
      0.75, NULL, realloc, free);
  g_pengu_cc_set_ctx = NULL;
  if (!result.other_ptr)
    return false;
  state->cc = result.new_cntr;
  return true;
}

bool ccx_uset_add_int(void *handle, int32_t value)
{
  return ccx_uset_insert((PenguCcSet *)handle, &value);
}

bool ccx_uset_add_string(void *handle, PenguString value)
{
  return ccx_uset_insert((PenguCcSet *)handle, &value);
}

static bool ccx_uset_has(PenguCcSet *state, void *key)
{
  if (!state)
    return false;
  g_pengu_cc_set_ctx = state;
  void *found = cc_set_get(state->cc, key, 0, state->layout,
                           pengu_cc_set_hash, pengu_cc_set_eq);
  g_pengu_cc_set_ctx = NULL;
  return found != NULL;
}

bool ccx_uset_has_int(void *handle, int32_t value)
{
  return ccx_uset_has((PenguCcSet *)handle, &value);
}

bool ccx_uset_has_string(void *handle, PenguString value)
{
  return ccx_uset_has((PenguCcSet *)handle, &value);
}

static bool ccx_uset_remove(PenguCcSet *state, void *key)
{
  if (!state)
    return false;
  g_pengu_cc_set_ctx = state;
  void *removed = cc_set_erase(state->cc, key, 0, state->layout,
                               pengu_cc_set_hash, pengu_cc_set_eq, NULL, NULL,
                               free);
  g_pengu_cc_set_ctx = NULL;
  return removed != NULL;
}

bool ccx_uset_remove_int(void *handle, int32_t value)
{
  return ccx_uset_remove((PenguCcSet *)handle, &value);
}

bool ccx_uset_remove_string(void *handle, PenguString value)
{
  return ccx_uset_remove((PenguCcSet *)handle, &value);
}

int ccx_uset_len(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  return state ? (int)cc_set_size(state->cc) : 0;
}

PenguList ccx_uset_items_int(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  PenguList out = pengu_list_new(sizeof(int32_t), state ? (size_t)cc_set_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_set_first(state->cc, 0, state->layout);
       it != cc_set_end(state->cc, 0, state->layout);
       it = cc_set_next(state->cc, it, 0, state->layout))
    pengu_list_push(&out, it);
  return out;
}

PenguList ccx_uset_items_string(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  PenguList out = pengu_list_new(sizeof(PenguString), state ? (size_t)cc_set_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_set_first(state->cc, 0, state->layout);
       it != cc_set_end(state->cc, 0, state->layout);
       it = cc_set_next(state->cc, it, 0, state->layout))
    pengu_list_push(&out, it);
  return out;
}

void ccx_uset_clear(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  if (!state)
    return;
  cc_set_clear(state->cc, 0, state->layout, NULL, NULL, free);
}

void ccx_uset_free(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  if (!state)
    return;
  cc_set_cleanup(state->cc, 0, state->layout, NULL, NULL, free);
  free(state);
}

/* =========================================================================
 * Ordered set
 * ========================================================================= */

void *ccx_oset_new(int key_size, int kind)
{
  PenguCcSet *state = (PenguCcSet *)calloc(1, sizeof(*state));
  if (!state)
    return NULL;
  state->key_size = key_size > 0 ? (size_t)key_size : 1;
  state->kind = kind;
  state->layout = pengu_cc_set_layout(state->key_size, 1);
  state->cc = (void *)&cc_omap_placeholder;
  return state;
}

static bool ccx_oset_insert(PenguCcSet *state, void *key)
{
  if (!state)
    return false;
  g_pengu_cc_set_ctx = state;
  cc_allocing_fn_result_ty result = cc_oset_insert(
      state->cc, key, false, state->layout, NULL, pengu_cc_set_cmp, 0.0, NULL,
      realloc, NULL);
  g_pengu_cc_set_ctx = NULL;
  if (!result.other_ptr)
    return false;
  state->cc = result.new_cntr;
  return true;
}

bool ccx_oset_add_int(void *handle, int32_t value)
{
  return ccx_oset_insert((PenguCcSet *)handle, &value);
}

bool ccx_oset_add_string(void *handle, PenguString value)
{
  return ccx_oset_insert((PenguCcSet *)handle, &value);
}

static bool ccx_oset_has(PenguCcSet *state, void *key)
{
  if (!state)
    return false;
  g_pengu_cc_set_ctx = state;
  void *found = cc_oset_get(state->cc, key, 0, state->layout, NULL,
                            pengu_cc_set_cmp);
  g_pengu_cc_set_ctx = NULL;
  return found != NULL;
}

bool ccx_oset_has_int(void *handle, int32_t value)
{
  return ccx_oset_has((PenguCcSet *)handle, &value);
}

bool ccx_oset_has_string(void *handle, PenguString value)
{
  return ccx_oset_has((PenguCcSet *)handle, &value);
}

static bool ccx_oset_remove(PenguCcSet *state, void *key)
{
  if (!state)
    return false;
  g_pengu_cc_set_ctx = state;
  void *removed = cc_oset_erase(state->cc, key, 0, state->layout, NULL,
                                pengu_cc_set_cmp, NULL, NULL, free);
  g_pengu_cc_set_ctx = NULL;
  return removed != NULL;
}

bool ccx_oset_remove_int(void *handle, int32_t value)
{
  return ccx_oset_remove((PenguCcSet *)handle, &value);
}

bool ccx_oset_remove_string(void *handle, PenguString value)
{
  return ccx_oset_remove((PenguCcSet *)handle, &value);
}

int ccx_oset_len(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  return state ? (int)cc_oset_size(state->cc) : 0;
}

PenguList ccx_oset_items_int(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  PenguList out = pengu_list_new(sizeof(int32_t), state ? (size_t)cc_oset_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_oset_first(state->cc, 0, state->layout);
       it != cc_oset_end(state->cc, 0, state->layout);
       it = cc_oset_next(state->cc, it, 0, state->layout))
    pengu_list_push(&out, it);
  return out;
}

PenguList ccx_oset_items_string(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  PenguList out = pengu_list_new(sizeof(PenguString), state ? (size_t)cc_oset_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_oset_first(state->cc, 0, state->layout);
       it != cc_oset_end(state->cc, 0, state->layout);
       it = cc_oset_next(state->cc, it, 0, state->layout))
    pengu_list_push(&out, it);
  return out;
}

void ccx_oset_clear(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  if (!state)
    return;
  cc_oset_clear(state->cc, 0, state->layout, NULL, NULL, free);
}

void ccx_oset_free(void *handle)
{
  PenguCcSet *state = (PenguCcSet *)handle;
  if (!state)
    return;
  cc_oset_cleanup(state->cc, 0, state->layout, NULL, NULL, free);
  free(state);
}

/* =========================================================================
 * Ordered map
 * ========================================================================= */

typedef struct
{
  void *cc;
  size_t key_size;
  size_t val_size;
  uint64_t layout;
  int kind;
} PenguCcOMap;

static PENGU_THREAD_LOCAL PenguCcOMap *g_ccx_omap_ctx = NULL;

static int ccx_omap_cmp(void *a, void *b)
{
  PenguCcOMap *ctx = g_ccx_omap_ctx;
  if (!ctx || !a || !b)
    return a != b;
  if (ctx->kind == PENGU_CC_KIND_STRING)
    return pengu_cc_string_cmp(*(PenguString *)a, *(PenguString *)b);
  if (ctx->key_size == sizeof(int32_t))
    return (*(int32_t *)a > *(int32_t *)b) - (*(int32_t *)a < *(int32_t *)b);
  return memcmp(a, b, ctx->key_size);
}

void *ccx_omap_new(int key_size, int val_size, int kind)
{
  PenguCcOMap *state = (PenguCcOMap *)calloc(1, sizeof(*state));
  if (!state)
    return NULL;
  state->key_size = key_size > 0 ? (size_t)key_size : 1;
  state->val_size = val_size > 0 ? (size_t)val_size : 1;
  state->kind = kind;
  const uint64_t align = (uint64_t)_Alignof(max_align_t);
  state->layout = cc_layout(CC_OMAP, state->val_size, align,
                            (cc_key_details_ty){state->key_size, align});
  state->cc = (void *)&cc_omap_placeholder;
  return state;
}

static bool ccx_omap_put(PenguCcOMap *state, void *key, void *val)
{
  if (!state)
    return false;
  g_ccx_omap_ctx = state;
  cc_allocing_fn_result_ty result = cc_omap_insert(
      state->cc, val, key, false, state->val_size, state->layout, NULL,
      ccx_omap_cmp, 0.0, NULL, NULL, realloc, free);
  g_ccx_omap_ctx = NULL;
  if (!result.other_ptr)
    return false;
  memcpy(result.other_ptr, val, state->val_size);
  state->cc = result.new_cntr;
  return true;
}

bool ccx_omap_put_int_int(void *handle, int32_t key, int32_t value)
{
  return ccx_omap_put((PenguCcOMap *)handle, &key, &value);
}

bool ccx_omap_put_string_int(void *handle, PenguString key, int32_t value)
{
  return ccx_omap_put((PenguCcOMap *)handle, &key, &value);
}

static void *ccx_omap_get_value(PenguCcOMap *state, void *key)
{
  if (!state)
    return NULL;
  g_ccx_omap_ctx = state;
  void *found = cc_omap_get(state->cc, key, state->val_size, state->layout,
                            NULL, ccx_omap_cmp);
  g_ccx_omap_ctx = NULL;
  return found;
}

PenguMaybe ccx_omap_get_int_int(void *handle, int32_t key)
{
  int32_t *found = (int32_t *)ccx_omap_get_value((PenguCcOMap *)handle, &key);
  if (!found)
    return pengu_maybe_none();
  int32_t *box = (int32_t *)pengu_sigil_alloc(sizeof(int32_t));
  if (!box)
    return pengu_maybe_none();
  *box = *found;
  return pengu_maybe_some(box);
}

PenguMaybe ccx_omap_get_string_int(void *handle, PenguString key)
{
  int32_t *found = (int32_t *)ccx_omap_get_value((PenguCcOMap *)handle, &key);
  if (!found)
    return pengu_maybe_none();
  int32_t *box = (int32_t *)pengu_sigil_alloc(sizeof(int32_t));
  if (!box)
    return pengu_maybe_none();
  *box = *found;
  return pengu_maybe_some(box);
}

static bool ccx_omap_remove(PenguCcOMap *state, void *key)
{
  if (!state)
    return false;
  g_ccx_omap_ctx = state;
  void *removed = cc_omap_erase(state->cc, key, state->val_size, state->layout,
                                NULL, ccx_omap_cmp, NULL, NULL, free);
  g_ccx_omap_ctx = NULL;
  return removed != NULL;
}

bool ccx_omap_remove_int_int(void *handle, int32_t key)
{
  return ccx_omap_remove((PenguCcOMap *)handle, &key);
}

bool ccx_omap_remove_string_int(void *handle, PenguString key)
{
  return ccx_omap_remove((PenguCcOMap *)handle, &key);
}

int ccx_omap_len(void *handle)
{
  PenguCcOMap *state = (PenguCcOMap *)handle;
  return state ? (int)cc_omap_size(state->cc) : 0;
}

PenguList ccx_omap_keys_int(void *handle)
{
  PenguCcOMap *state = (PenguCcOMap *)handle;
  PenguList out = pengu_list_new(sizeof(int32_t), state ? (size_t)cc_omap_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_omap_first(state->cc, state->val_size, state->layout);
       it != cc_omap_end(state->cc, state->val_size, state->layout);
       it = cc_omap_next(state->cc, it, state->val_size, state->layout))
    pengu_list_push(&out, cc_omap_key_for(it, state->val_size, state->layout));
  return out;
}

PenguList ccx_omap_keys_string(void *handle)
{
  PenguCcOMap *state = (PenguCcOMap *)handle;
  PenguList out = pengu_list_new(sizeof(PenguString), state ? (size_t)cc_omap_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_omap_first(state->cc, state->val_size, state->layout);
       it != cc_omap_end(state->cc, state->val_size, state->layout);
       it = cc_omap_next(state->cc, it, state->val_size, state->layout))
    pengu_list_push(&out, cc_omap_key_for(it, state->val_size, state->layout));
  return out;
}

PenguList ccx_omap_values_int(void *handle)
{
  PenguCcOMap *state = (PenguCcOMap *)handle;
  PenguList out = pengu_list_new(sizeof(int32_t), state ? (size_t)cc_omap_size(state->cc) : 0);
  if (!state)
    return out;
  for (void *it = cc_omap_first(state->cc, state->val_size, state->layout);
       it != cc_omap_end(state->cc, state->val_size, state->layout);
       it = cc_omap_next(state->cc, it, state->val_size, state->layout))
    pengu_list_push(&out, it);
  return out;
}

bool ccx_omap_has_int_int(void *handle, int32_t key)
{
  return ccx_omap_get_value((PenguCcOMap *)handle, &key) != NULL;
}

bool ccx_omap_has_string_int(void *handle, PenguString key)
{
  return ccx_omap_get_value((PenguCcOMap *)handle, &key) != NULL;
}

void ccx_omap_clear(void *handle)
{
  PenguCcOMap *state = (PenguCcOMap *)handle;
  if (!state)
    return;
  cc_omap_clear(state->cc, state->val_size, state->layout, NULL, NULL, free);
}

void ccx_omap_free(void *handle)
{
  PenguCcOMap *state = (PenguCcOMap *)handle;
  if (!state)
    return;
  cc_omap_cleanup(state->cc, state->val_size, state->layout, NULL, NULL, free);
  free(state);
}
