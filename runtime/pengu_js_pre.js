// pengu_js_pre.js - JavaScript-side handle registry for the PenguScript bridge.
//
// Handles are integers >= 2. 0 is `undefined` and 1 is `null`, exactly as the
// PenguScript `JsValue` seal documents. Every other value is an entry in a
// Map with an explicit reference count:
//
//   refs == 1  the PenguScript owner must call release (or retain first)
//   refs == 0  the entry is stale; using it is an error, never a silent alias
//
// Handles are never reused. A double release therefore cannot make two live
// values share one handle, which used to be the source of type confusion.
var PENGU_JS = {
    handles: new Map(),
    lastError: null,
    ws: new Map(),
    nextWs: 1,
    nextHandle: 2
};

var PENGU_JS_MAX_HANDLES = 0x3fffffff;

function pengu_js_set_error(name, message, stack) {
    PENGU_JS.lastError = {
        name: String(name || "Error"),
        message: String(message || ""),
        stack: String(stack || "")
    };
}

function pengu_js_fail(e) {
    if (e && typeof e === "object") {
        pengu_js_set_error(e.name || "Error", e.message || String(e), e.stack || "");
    } else {
        pengu_js_set_error("Error", String(e), "");
    }
    return -1;
}

function pengu_js_wrap(value) {
    if (value === undefined) {
        return 0;
    }
    if (value === null) {
        return 1;
    }
    if (PENGU_JS.nextHandle >= PENGU_JS_MAX_HANDLES) {
        pengu_js_set_error("RangeError", "JavaScript handle space exhausted", "");
        return -1;
    }
    var handle = PENGU_JS.nextHandle++;
    PENGU_JS.handles.set(handle, { value: value, refs: 1 });
    return handle;
}

function pengu_js_unwrap(handle) {
    handle = handle | 0;
    if (handle === 0) {
        return undefined;
    }
    if (handle === 1) {
        return null;
    }
    var entry = PENGU_JS.handles.get(handle);
    if (!entry || entry.refs <= 0) {
        throw new Error("invalid or released JavaScript handle " + handle);
    }
    return entry.value;
}

function pengu_js_is_valid_handle(handle) {
    handle = handle | 0;
    if (handle === 0 || handle === 1) {
        return 1;
    }
    var entry = PENGU_JS.handles.get(handle);
    return entry && entry.refs > 0 ? 1 : 0;
}

function pengu_js_alloc_utf8(text) {
    var s = String(text === undefined ? "" : text);
    var size = lengthBytesUTF8(s) + 1;
    var ptr = _malloc(size);
    if (!ptr) {
        return 0;
    }
    stringToUTF8(s, ptr, size);
    return ptr;
}

function pengu_js_invoke_string(id, text) {
    var ptr = pengu_js_alloc_utf8(text);
    if (!ptr) {
        return;
    }
    try {
        _pengu_js_invoke_string(id, ptr);
    } finally {
        _free(ptr);
    }
}

function pengu_js_invoke_string_oneshot(id, text) {
    var ptr = pengu_js_alloc_utf8(text);
    if (!ptr) {
        _pengu_js_callback_string_free(id);
        return;
    }
    try {
        _pengu_js_invoke_string_oneshot(id, ptr);
    } finally {
        _free(ptr);
    }
}

function pengu_js_drop_handle(handle) {
    if (handle <= 1) {
        return;
    }
    var entry = PENGU_JS.handles.get(handle);
    if (!entry) {
        return;
    }
    entry.refs--;
    if (entry.refs <= 0) {
        PENGU_JS.handles.delete(handle);
    }
}

function pengu_js_drop_slot(slot) {
    if (slot > 0) {
        _pengu_js_callback_free(slot);
    }
}
