/*
 * pengu_containers.c — CC-backed implementation of PenguList and PenguMap.
 *
 * Convenient Containers (CC) is a type-generic, header-only library.  The
 * generated PenguScript bundles must not see cc.h (its macros and `typeof`
 * requirements are far too invasive), so this translation unit is the only one
 * that includes it and the public header keeps small wrappers around the
 * functions below.
 *
 * CC's internal functions (cc_vec_*, cc_map_*, cc_set_*, ...) are type-erased
 * `static inline` functions taking element sizes and callbacks, which is
 * exactly what a runtime with `PenguList`/`PenguMap` value headers needs.
 */

#define CC_NO_SHORT_NAMES 1
#include "pengu_runtime.h"
#include "cc.h"

/* =========================================================================
 * List: CC vec underneath the historical PenguList layout
 * ========================================================================= */

static inline cc_vec_hdr_ty *pengu_cc_vec_hdr(const PenguList *list)
{
  return (cc_vec_hdr_ty *)((char *)list->data - sizeof(cc_vec_hdr_ty));
}

static inline void pengu_cc_vec_refresh(PenguList *list, void *cntr)
{
  list->data = (char *)cntr + sizeof(cc_vec_hdr_ty);
  list->len = (int)cc_vec_size(cntr);
  list->cap = (int)cc_vec_cap(cntr);
}

void pengu_cc_list_init(PenguList *list, size_t elem_size, size_t cap)
{
  if (!list)
    return;
  list->len = 0;
  list->cap = 0;
  list->elem_size = elem_size;
  list->data = NULL;
  size_t wanted = cap > 0 ? cap : 4;
  cc_allocing_fn_result_ty result = cc_vec_reserve(
      (void *)&cc_vec_placeholder, wanted, elem_size, 0, NULL, 0.0, realloc, NULL);
  if (!result.other_ptr)
    return;
  pengu_cc_vec_refresh(list, result.new_cntr);
}

void pengu_cc_list_push(PenguList *list, const void *item)
{
  if (!list || !item || list->cap < 0 || !list->data)
    return;
  cc_allocing_fn_result_ty result = cc_vec_push(
      pengu_cc_vec_hdr(list), (void *)item, list->elem_size, realloc);
  if (!result.other_ptr)
    return;
  pengu_cc_vec_refresh(list, result.new_cntr);
}

void *pengu_cc_list_pop_val(PenguList *list)
{
  if (!list || list->len <= 0 || !list->data)
    return NULL;
  if (list->cap < 0)
  {
    list->len--;
    return (char *)list->data + ((size_t)list->len * list->elem_size);
  }
  cc_vec_hdr_ty *hdr = pengu_cc_vec_hdr(list);
  if (cc_vec_size(hdr) == 0)
    return NULL;
  hdr->size--;
  list->len = (int)hdr->size;
  return (char *)list->data + ((size_t)list->len * list->elem_size);
}

bool pengu_cc_list_pop(PenguList *list, void *out_item)
{
  void *src = pengu_cc_list_pop_val(list);
  if (!src)
    return false;
  if (out_item)
    memcpy(out_item, src, list->elem_size);
  return true;
}

void pengu_cc_list_clear(PenguList *list)
{
  if (!list)
    return;
  if (list->cap < 0)
  {
    list->len = 0;
    return;
  }
  if (list->data)
  {
    cc_vec_clear(pengu_cc_vec_hdr(list), list->elem_size, 0, NULL, NULL, free);
    list->len = 0;
  }
}

void pengu_cc_list_banish(PenguList *list)
{
  if (!list)
    return;
  if (list->data && list->cap >= 0)
    cc_vec_cleanup(pengu_cc_vec_hdr(list), list->elem_size, 0, NULL, NULL, free);
  list->data = NULL;
  list->len = 0;
  list->cap = 0;
}

void pengu_cc_list_set_len(PenguList *list, int len)
{
  if (!list)
    return;
  if (len < 0)
    len = 0;
  if (list->cap < 0)
  {
    list->len = len;
    return;
  }
  if (!list->data)
  {
    list->len = 0;
    return;
  }
  if (len > list->cap)
    len = list->cap;
  pengu_cc_vec_hdr(list)->size = (size_t)len;
  list->len = len;
}

bool pengu_cc_list_remove_at(PenguList *list, int idx)
{
  if (!list || idx < 0 || idx >= list->len || !list->data)
    return false;
  if (list->cap >= 0)
  {
    char *p = (char *)list->data + ((size_t)idx * list->elem_size);
    memmove(p, p + list->elem_size,
            (size_t)(list->len - idx - 1) * list->elem_size);
    pengu_cc_list_set_len(list, list->len - 1);
  }
  else
  {
    char *p = (char *)list->data + ((size_t)idx * list->elem_size);
    memmove(p, p + list->elem_size,
            (size_t)(list->len - idx - 1) * list->elem_size);
    list->len--;
  }
  return true;
}

void pengu_cc_list_from_data(PenguList *list, const void *data,
                             size_t elem_size, int count)
{
  if (!list)
    return;
  pengu_cc_list_init(list, elem_size, count > 0 ? (size_t)count : 0);
  if (count <= 0 || !data || !list->data || list->cap <= 0)
    return;
  memcpy(list->data, data, (size_t)count * elem_size);
  pengu_cc_list_set_len(list, count);
}

/* =========================================================================
 * Map: CC map behind an opaque PenguMapState
 * ========================================================================= */

typedef struct
{
  void *cc;
  uint64_t layout;
  uint64_t key_align;
  uint64_t val_align;
  size_t key_size;
  size_t val_size;
  int key_kind; /* 1 = PenguString, 0 = bytes */
} PenguMapState;

static PENGU_THREAD_LOCAL PenguMapState *g_pengu_cc_map_ctx = NULL;

static inline uint64_t pengu_cc_map_layout(size_t key_size, size_t val_size)
{
  const uint64_t align = (uint64_t)_Alignof(max_align_t);
  return cc_layout(CC_MAP, val_size, align,
                   (cc_key_details_ty){key_size, align});
}

static inline PenguMapState *pengu_cc_map_state(const PenguMap *map)
{
  return map ? (PenguMapState *)map->state : NULL;
}

static size_t pengu_cc_map_hash(void *key)
{
  PenguMapState *ctx = g_pengu_cc_map_ctx;
  if (!ctx || !key)
    return 0;
  if (ctx->key_kind == 1)
  {
    const PenguString *s = (const PenguString *)key;
    if (!s->data || s->len <= 0)
      return 0;
    return (size_t)pengu_hash_bytes(s->data, (size_t)s->len);
  }
  return (size_t)pengu_hash_bytes(key, ctx->key_size);
}

static int pengu_cc_map_cmp(void *a, void *b)
{
  PenguMapState *ctx = g_pengu_cc_map_ctx;
  if (!ctx || !a || !b)
    return a != b;
  /* CC uses an equality predicate for unordered maps/sets (1 = equal) and a
   * three-way comparator for ordered containers.  This is the unordered one. */
  if (ctx->key_kind == 1)
    return pengu_string_equal(*(const PenguString *)a,
                              *(const PenguString *)b) ? 1 : 0;
  return memcmp(a, b, ctx->key_size) == 0 ? 1 : 0;
}

static void pengu_cc_map_context_enter(PenguMapState *state)
{
  g_pengu_cc_map_ctx = state;
}

static void pengu_cc_map_context_leave(void)
{
  g_pengu_cc_map_ctx = NULL;
}

void pengu_cc_map_init(PenguMap *map, size_t key_size, size_t val_size)
{
  if (!map)
    return;
  map->state = NULL;
  map->len = 0;
  map->cap = 0;
  map->key_size = key_size;
  map->val_size = val_size;
  PenguMapState *state = (PenguMapState *)calloc(1, sizeof(PenguMapState));
  if (!state)
    return;
  state->cc = (void *)&cc_map_placeholder;
  state->key_size = key_size;
  state->val_size = val_size;
  state->key_align = (uint64_t)_Alignof(max_align_t);
  state->val_align = (uint64_t)_Alignof(max_align_t);
  state->key_kind = key_size == sizeof(PenguString) ? 1 : 0;
  state->layout = pengu_cc_map_layout(key_size, val_size);
  map->state = state;
}

void pengu_cc_map_pin_sizes(PenguMap *map, size_t key_size, size_t val_size)
{
  if (!map)
    return;
  PenguMapState *state = pengu_cc_map_state(map);
  if (!state || map->len > 0)
    return;
  state->key_size = key_size;
  state->val_size = val_size;
  state->key_kind = key_size == sizeof(PenguString) ? 1 : 0;
  state->layout = pengu_cc_map_layout(key_size, val_size);
  map->key_size = key_size;
  map->val_size = val_size;
}

void pengu_cc_map_put(PenguMap *map, const void *key, const void *val)
{
  if (!map || !key || !val)
    return;
  PenguMapState *state = pengu_cc_map_state(map);
  if (!state)
  {
    pengu_cc_map_init(map, map->key_size, map->val_size);
    state = pengu_cc_map_state(map);
  }
  if (!state || state->key_size == 0 || state->val_size == 0)
    return;
  pengu_cc_map_context_enter(state);
  cc_allocing_fn_result_ty result = cc_map_insert(
      state->cc, (void *)val, (void *)key, false, state->val_size,
      state->layout, pengu_cc_map_hash, pengu_cc_map_cmp, 0.75, NULL, NULL,
      realloc, free);
  if (result.other_ptr)
  {
    /* With replace=false, CC returns the existing element when the key is
     * already present and copies the value only for a new entry.  Copying the
     * value unconditionally preserves the historical "overwrite the value,
     * keep the original key" behaviour (owned string keys rely on it). */
    memcpy(result.other_ptr, val, state->val_size);
    state->cc = result.new_cntr;
    map->len = (int)cc_map_size(state->cc);
    map->cap = (int)cc_map_cap(state->cc);
  }
  pengu_cc_map_context_leave();
}

void *pengu_cc_map_get(const PenguMap *map, const void *key)
{
  PenguMapState *state = pengu_cc_map_state(map);
  if (!state || !key || state->key_size == 0 || state->val_size == 0)
    return NULL;
  pengu_cc_map_context_enter(state);
  void *out = cc_map_get(state->cc, (void *)key, state->val_size, state->layout,
                         pengu_cc_map_hash, pengu_cc_map_cmp);
  pengu_cc_map_context_leave();
  return out;
}

bool pengu_cc_map_remove(PenguMap *map, const void *key)
{
  PenguMapState *state = pengu_cc_map_state(map);
  if (!state || !key || state->key_size == 0 || state->val_size == 0)
    return false;
  pengu_cc_map_context_enter(state);
  void *removed = cc_map_erase(state->cc, (void *)key, state->val_size,
                               state->layout, pengu_cc_map_hash,
                               pengu_cc_map_cmp, NULL, NULL, free);
  map->len = (int)cc_map_size(state->cc);
  map->cap = (int)cc_map_cap(state->cc);
  pengu_cc_map_context_leave();
  return removed != NULL;
}

void pengu_cc_map_clear(PenguMap *map)
{
  PenguMapState *state = pengu_cc_map_state(map);
  if (!state)
    return;
  pengu_cc_map_context_enter(state);
  cc_map_clear(state->cc, state->val_size, state->layout, NULL, NULL, free);
  pengu_cc_map_context_leave();
  map->len = 0;
}

void pengu_cc_map_banish(PenguMap *map)
{
  if (!map)
    return;
  PenguMapState *state = pengu_cc_map_state(map);
  if (state)
  {
    pengu_cc_map_context_enter(state);
    cc_map_cleanup(state->cc, state->val_size, state->layout, NULL, NULL, free);
    pengu_cc_map_context_leave();
    free(state);
  }
  map->state = NULL;
  map->len = 0;
  map->cap = 0;
}

PenguList pengu_cc_map_keys(const PenguMap *map)
{
  PenguMapState *state = pengu_cc_map_state(map);
  size_t key_size = state ? state->key_size : (map ? map->key_size : sizeof(void *));
  PenguList list = pengu_list_new(key_size, state ? (size_t)cc_map_size(state->cc) : 0);
  if (!state || state->key_size == 0)
    return list;
  pengu_cc_map_context_enter(state);
  for (void *it = cc_map_first(state->cc, state->val_size, state->layout);
       it != cc_map_end(state->cc, state->val_size, state->layout);
       it = cc_map_next(state->cc, it, state->val_size, state->layout))
  {
    pengu_list_push(&list, cc_map_key_for(it, state->val_size, state->layout));
  }
  pengu_cc_map_context_leave();
  return list;
}

PenguList pengu_cc_map_values(const PenguMap *map)
{
  PenguMapState *state = pengu_cc_map_state(map);
  size_t val_size = state ? state->val_size : (map ? map->val_size : sizeof(void *));
  PenguList list = pengu_list_new(val_size, state ? (size_t)cc_map_size(state->cc) : 0);
  if (!state || state->val_size == 0)
    return list;
  pengu_cc_map_context_enter(state);
  for (void *it = cc_map_first(state->cc, state->val_size, state->layout);
       it != cc_map_end(state->cc, state->val_size, state->layout);
       it = cc_map_next(state->cc, it, state->val_size, state->layout))
  {
    pengu_list_push(&list, it);
  }
  pengu_cc_map_context_leave();
  return list;
}

PenguMapIter pengu_map_iter_begin(const PenguMap *map)
{
  PenguMapIter iter;
  iter.map = map;
  iter.it = NULL;
  PenguMapState *state = pengu_cc_map_state(map);
  if (state)
    iter.it = cc_map_first(state->cc, state->val_size, state->layout);
  return iter;
}

bool pengu_map_iter_valid(const PenguMapIter *iter)
{
  if (!iter || !iter->map)
    return false;
  PenguMapState *state = pengu_cc_map_state(iter->map);
  if (!state || !iter->it)
    return false;
  return iter->it != cc_map_end(state->cc, state->val_size, state->layout);
}

void pengu_map_iter_advance(PenguMapIter *iter)
{
  if (!iter || !iter->map)
    return;
  PenguMapState *state = pengu_cc_map_state(iter->map);
  if (!state || !iter->it)
    return;
  iter->it = cc_map_next(state->cc, iter->it, state->val_size, state->layout);
}

const void *pengu_map_iter_key(const PenguMapIter *iter)
{
  if (!iter || !iter->map)
    return NULL;
  PenguMapState *state = pengu_cc_map_state(iter->map);
  if (!state || !iter->it)
    return NULL;
  return cc_map_key_for(iter->it, state->val_size, state->layout);
}
