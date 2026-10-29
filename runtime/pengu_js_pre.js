/*
 * pengu_js_pre.js - helper globals for the Emscripten JS library.
 *
 * Loaded with `emcc --pre-js` before the generated runtime. Every value
 * crossing the boundary is an int32 handle: 0 = undefined, 1 = null, >= 2 is
 * an entry in the registry. Strings are UTF-8; the C side copies them.
 *
 * No EM_ASM/EM_JS: this file is C11-compatible by construction.
 */
var PENGU_JS = {
  handles: [undefined, null],
  free: [],
  lastError: "",
  ws: [null]
};

function pengu_js_wrap(v) {
  if (v === undefined) return 0;
  if (v === null) return 1;
  if (PENGU_JS.free.length > 0) {
    var i = PENGU_JS.free.pop();
    PENGU_JS.handles[i] = v;
    return i;
  }
  PENGU_JS.handles.push(v);
  return PENGU_JS.handles.length - 1;
}

function pengu_js_unwrap(h) {
  return PENGU_JS.handles[h];
}

function pengu_js_fail(e) {
  PENGU_JS.lastError = String(e && e.stack ? e.stack : e);
  return -1;
}

function pengu_js_alloc_utf8(s) {
  var text = String(s);
  var len = lengthBytesUTF8(text) + 1;
  var ptr = _malloc(len);
  stringToUTF8(text, ptr, len);
  return ptr;
}

function pengu_js_invoke_string(id, text) {
  var ptr = pengu_js_alloc_utf8(text);
  _pengu_js_invoke_string(id, ptr);
  _free(ptr);
}

