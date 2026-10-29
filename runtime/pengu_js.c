/*
 * pengu_js.c - small C bridge for the wasm JavaScript interop layer.
 *
 * The JS side (runtime/pengu_js.js) calls `pengu_js_invoke` /
 * `pengu_js_invoke_string`; PenguScript callbacks are plain C function
 * pointers registered here. Kept separate from the core runtime so a native
 * build never links it.
 */
#include "pengu_runtime.h"

#if defined(__EMSCRIPTEN__)
#include <emscripten.h>
#else
#define EMSCRIPTEN_KEEPALIVE
#endif

#define PENGU_JS_MAX_CALLBACKS 256

static PenguJsValueCallback g_value_cb[PENGU_JS_MAX_CALLBACKS];
static PenguJsStringCallback g_string_cb[PENGU_JS_MAX_CALLBACKS];

int32_t pengu_js_callback_new(PenguJsValueCallback fn) {
    if (fn == NULL) {
        return 0;
    }
    for (int32_t i = 0; i < PENGU_JS_MAX_CALLBACKS; i++) {
        if (g_value_cb[i] == NULL) {
            g_value_cb[i] = fn;
            return i + 1;
        }
    }
    return 0;
}

int32_t pengu_js_callback_new_ptr(void *fn) {
    return pengu_js_callback_new((PenguJsValueCallback)fn);
}

void pengu_js_callback_free(int32_t id) {
    if (id > 0 && id <= PENGU_JS_MAX_CALLBACKS) {
        g_value_cb[id - 1] = NULL;
    }
}

int32_t pengu_js_callback_string_new(PenguJsStringCallback fn) {
    if (fn == NULL) {
        return 0;
    }
    for (int32_t i = 0; i < PENGU_JS_MAX_CALLBACKS; i++) {
        if (g_string_cb[i] == NULL) {
            g_string_cb[i] = fn;
            return i + 1;
        }
    }
    return 0;
}

int32_t pengu_js_callback_string_new_ptr(void *fn) {
    return pengu_js_callback_string_new((PenguJsStringCallback)fn);
}

void pengu_js_callback_string_free(int32_t id) {
    if (id > 0 && id <= PENGU_JS_MAX_CALLBACKS) {
        g_string_cb[id - 1] = NULL;
    }
}

EMSCRIPTEN_KEEPALIVE
void pengu_js_invoke(int32_t id, int32_t arg) {
    if (id > 0 && id <= PENGU_JS_MAX_CALLBACKS) {
        PenguJsValueCallback fn = g_value_cb[id - 1];
        if (fn != NULL) {
            fn(arg);
        }
    }
}

EMSCRIPTEN_KEEPALIVE
void pengu_js_invoke_string(int32_t id, const char *text) {
    if (id > 0 && id <= PENGU_JS_MAX_CALLBACKS) {
        PenguJsStringCallback fn = g_string_cb[id - 1];
        if (fn != NULL) {
            PenguString s;
            s.data = (char *)(text != NULL ? text : "");
            s.len = (int)strlen(s.data);
            s.is_owned = 0;
            fn(s);
        }
    }
}
