/*
 * pengu_js.c - small C bridge for the wasm JavaScript interop layer.
 *
 * The JS side (runtime/pengu_js.js) calls `pengu_js_invoke` /
 * `pengu_js_invoke_string`; PenguScript callbacks are plain C function
 * pointers registered here. Kept separate from the core runtime so a native
 * build never links it.
 *
 * Callback ids are generation-checked and dynamically sized. A stale id (one
 * whose slot was already freed) is rejected instead of invoking whatever
 * callback happens to occupy the slot now. `id` layout:
 *
 *     bits  0..15  slot index + 1 (1..65535)
 *     bits 16..30  generation (1..32767)
 *
 * The generation is bumped on every free, so id reuse cannot alias an old
 * callback. Both tables grow on demand; there is no fixed 256-slot ceiling.
 */
#include "pengu_runtime.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#if defined(__EMSCRIPTEN__)
#include <emscripten.h>
#else
#define EMSCRIPTEN_KEEPALIVE
#endif

#define PENGU_JS_MAX_SLOTS 65535
#define PENGU_JS_SLOT_MASK 0xffff
#define PENGU_JS_GEN_MASK 0x7fff
#define PENGU_JS_GEN_SHIFT 16

typedef struct {
    PenguJsValueCallback fn;
    uint16_t generation;
} PenguJsValueSlot;

typedef struct {
    PenguJsStringCallback fn;
    uint16_t generation;
} PenguJsStringSlot;

static PenguJsValueSlot *g_value_cb = NULL;
static int32_t g_value_cap = 0;
static int32_t g_value_used = 0;

static PenguJsStringSlot *g_string_cb = NULL;
static int32_t g_string_cap = 0;
static int32_t g_string_used = 0;

static uint16_t pengu_js_next_generation(uint16_t generation) {
    generation = (uint16_t)((generation + 1) & PENGU_JS_GEN_MASK);
    return generation == 0 ? 1 : generation;
}

static int32_t pengu_js_value_reserve(void) {
    if (g_value_used < g_value_cap) {
        return 1;
    }
    if (g_value_cap >= PENGU_JS_MAX_SLOTS) {
        return 0;
    }
    int32_t next = g_value_cap == 0 ? 16 : g_value_cap * 2;
    if (next > PENGU_JS_MAX_SLOTS) {
        next = PENGU_JS_MAX_SLOTS;
    }
    PenguJsValueSlot *grown = (PenguJsValueSlot *)realloc(
        g_value_cb, (size_t)next * sizeof(PenguJsValueSlot));
    if (grown == NULL) {
        return 0;
    }
    memset(&grown[g_value_cap], 0,
           (size_t)(next - g_value_cap) * sizeof(PenguJsValueSlot));
    g_value_cb = grown;
    g_value_cap = next;
    return 1;
}

static int32_t pengu_js_string_reserve(void) {
    if (g_string_used < g_string_cap) {
        return 1;
    }
    if (g_string_cap >= PENGU_JS_MAX_SLOTS) {
        return 0;
    }
    int32_t next = g_string_cap == 0 ? 16 : g_string_cap * 2;
    if (next > PENGU_JS_MAX_SLOTS) {
        next = PENGU_JS_MAX_SLOTS;
    }
    PenguJsStringSlot *grown = (PenguJsStringSlot *)realloc(
        g_string_cb, (size_t)next * sizeof(PenguJsStringSlot));
    if (grown == NULL) {
        return 0;
    }
    memset(&grown[g_string_cap], 0,
           (size_t)(next - g_string_cap) * sizeof(PenguJsStringSlot));
    g_string_cb = grown;
    g_string_cap = next;
    return 1;
}

int32_t pengu_js_callback_new(PenguJsValueCallback fn) {
    if (fn == NULL) {
        return 0;
    }
    int32_t slot = -1;
    for (int32_t i = 0; i < g_value_cap; i++) {
        if (g_value_cb[i].fn == NULL) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        int32_t old_cap = g_value_cap;
        if (!pengu_js_value_reserve()) {
            return 0;
        }
        slot = old_cap;
    }
    PenguJsValueSlot *entry = &g_value_cb[slot];
    entry->fn = fn;
    if (entry->generation == 0) {
        entry->generation = 1;
    }
    g_value_used++;
    return (int32_t)(((uint32_t)entry->generation << PENGU_JS_GEN_SHIFT) |
                     (uint32_t)(slot + 1));
}

int32_t pengu_js_callback_new_ptr(void *fn) {
    return pengu_js_callback_new((PenguJsValueCallback)fn);
}

void pengu_js_callback_free(int32_t id) {
    if (id <= 0) {
        return;
    }
    int32_t slot = (int32_t)(id & PENGU_JS_SLOT_MASK) - 1;
    int32_t generation = (int32_t)((uint32_t)id >> PENGU_JS_GEN_SHIFT) &
                         PENGU_JS_GEN_MASK;
    if (slot < 0 || slot >= g_value_cap) {
        return;
    }
    PenguJsValueSlot *entry = &g_value_cb[slot];
    if (entry->fn == NULL || entry->generation != generation) {
        return;
    }
    entry->fn = NULL;
    entry->generation = pengu_js_next_generation(entry->generation);
    if (g_value_used > 0) {
        g_value_used--;
    }
}

int32_t pengu_js_callback_string_new(PenguJsStringCallback fn) {
    if (fn == NULL) {
        return 0;
    }
    int32_t slot = -1;
    for (int32_t i = 0; i < g_string_cap; i++) {
        if (g_string_cb[i].fn == NULL) {
            slot = i;
            break;
        }
    }
    if (slot < 0) {
        int32_t old_cap = g_string_cap;
        if (!pengu_js_string_reserve()) {
            return 0;
        }
        slot = old_cap;
    }
    PenguJsStringSlot *entry = &g_string_cb[slot];
    entry->fn = fn;
    if (entry->generation == 0) {
        entry->generation = 1;
    }
    g_string_used++;
    return (int32_t)(((uint32_t)entry->generation << PENGU_JS_GEN_SHIFT) |
                     (uint32_t)(slot + 1));
}

int32_t pengu_js_callback_string_new_ptr(void *fn) {
    return pengu_js_callback_string_new((PenguJsStringCallback)fn);
}

void pengu_js_callback_string_free(int32_t id) {
    if (id <= 0) {
        return;
    }
    int32_t slot = (int32_t)(id & PENGU_JS_SLOT_MASK) - 1;
    int32_t generation = (int32_t)((uint32_t)id >> PENGU_JS_GEN_SHIFT) &
                         PENGU_JS_GEN_MASK;
    if (slot < 0 || slot >= g_string_cap) {
        return;
    }
    PenguJsStringSlot *entry = &g_string_cb[slot];
    if (entry->fn == NULL || entry->generation != generation) {
        return;
    }
    entry->fn = NULL;
    entry->generation = pengu_js_next_generation(entry->generation);
    if (g_string_used > 0) {
        g_string_used--;
    }
}

static PenguJsValueCallback pengu_js_value_lookup(int32_t id) {
    if (id <= 0) {
        return NULL;
    }
    int32_t slot = (int32_t)(id & PENGU_JS_SLOT_MASK) - 1;
    int32_t generation = (int32_t)((uint32_t)id >> PENGU_JS_GEN_SHIFT) &
                         PENGU_JS_GEN_MASK;
    if (slot < 0 || slot >= g_value_cap) {
        return NULL;
    }
    PenguJsValueSlot *entry = &g_value_cb[slot];
    if (entry->fn == NULL || entry->generation != generation) {
        return NULL;
    }
    return entry->fn;
}

static PenguJsStringCallback pengu_js_string_lookup(int32_t id) {
    if (id <= 0) {
        return NULL;
    }
    int32_t slot = (int32_t)(id & PENGU_JS_SLOT_MASK) - 1;
    int32_t generation = (int32_t)((uint32_t)id >> PENGU_JS_GEN_SHIFT) &
                         PENGU_JS_GEN_MASK;
    if (slot < 0 || slot >= g_string_cap) {
        return NULL;
    }
    PenguJsStringSlot *entry = &g_string_cb[slot];
    if (entry->fn == NULL || entry->generation != generation) {
        return NULL;
    }
    return entry->fn;
}

EMSCRIPTEN_KEEPALIVE
void pengu_js_invoke(int32_t id, int32_t arg) {
    PenguJsValueCallback fn = pengu_js_value_lookup(id);
    if (fn != NULL) {
        fn(arg);
    }
}

EMSCRIPTEN_KEEPALIVE
void pengu_js_invoke_string(int32_t id, const char *text) {
    PenguJsStringCallback fn = pengu_js_string_lookup(id);
    if (fn != NULL) {
        PenguString s;
        s.data = (char *)(text != NULL ? text : "");
        s.len = (int)strlen(s.data);
        s.is_owned = 0;
        fn(s);
    }
}

EMSCRIPTEN_KEEPALIVE
void pengu_js_invoke_oneshot(int32_t id, int32_t arg) {
    PenguJsValueCallback fn = pengu_js_value_lookup(id);
    if (fn != NULL) {
        pengu_js_callback_free(id);
        fn(arg);
    }
}

EMSCRIPTEN_KEEPALIVE
void pengu_js_invoke_string_oneshot(int32_t id, const char *text) {
    PenguJsStringCallback fn = pengu_js_string_lookup(id);
    if (fn != NULL) {
        pengu_js_callback_string_free(id);
        PenguString s;
        s.data = (char *)(text != NULL ? text : "");
        s.len = (int)strlen(s.data);
        s.is_owned = 0;
        fn(s);
    }
}

int32_t pengu_js_callback_count(void) {
    return g_value_used + g_string_used;
}

int32_t pengu_js_callback_capacity(void) {
    return g_value_cap + g_string_cap;
}
