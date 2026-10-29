mergeInto(LibraryManager.library, {
  pengu_js_eval: function(ptr) {
    try {
      return pengu_js_wrap((0, eval)(UTF8ToString(ptr)));
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_global: function() {
    return pengu_js_wrap(globalThis);
  },

  pengu_js_get: function(obj, namePtr) {
    try {
      return pengu_js_wrap(pengu_js_unwrap(obj)[UTF8ToString(namePtr)]);
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_set: function(obj, namePtr, value) {
    try {
      pengu_js_unwrap(obj)[UTF8ToString(namePtr)] = pengu_js_unwrap(value);
      return 0;
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_get_index: function(obj, index) {
    try {
      return pengu_js_wrap(pengu_js_unwrap(obj)[index]);
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_set_index: function(obj, index, value) {
    try {
      pengu_js_unwrap(obj)[index] = pengu_js_unwrap(value);
      return 0;
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_call: function(fn, this_v, args, argc) {
    try {
      var argv = [];
      for (var i = 0; i < argc; i++) {
        argv.push(pengu_js_unwrap(HEAP32[(args >> 2) + i]));
      }
      return pengu_js_wrap(pengu_js_unwrap(fn).apply(pengu_js_unwrap(this_v), argv));
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_new: function(ctor, args, argc) {
    try {
      var argv = [];
      for (var i = 0; i < argc; i++) {
        argv.push(pengu_js_unwrap(HEAP32[(args >> 2) + i]));
      }
      return pengu_js_wrap(Reflect.construct(pengu_js_unwrap(ctor), argv));
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_typeof_string: function(v) {
    try {
      return pengu_js_alloc_utf8(typeof pengu_js_unwrap(v));
    } catch (e) {
      pengu_js_fail(e);
      return 0;
    }
  },

  pengu_js_is_undefined: function(v) {
    return v === 0 ? 1 : 0;
  },

  pengu_js_is_null: function(v) {
    return v === 1 ? 1 : 0;
  },

  pengu_js_is_truthy: function(v) {
    return pengu_js_unwrap(v) ? 1 : 0;
  },

  pengu_js_to_string: function(v) {
    try {
      return pengu_js_alloc_utf8(String(pengu_js_unwrap(v)));
    } catch (e) {
      pengu_js_fail(e);
      return 0;
    }
  },

  pengu_js_to_f64: function(v) {
    try {
      var n = Number(pengu_js_unwrap(v));
      if (Number.isNaN(n)) {
        PENGU_JS.lastError = "value is not a number";
      }
      return n;
    } catch (e) {
      pengu_js_fail(e);
      return 0;
    }
  },

  pengu_js_to_i64: function(v) {
    try {
      return BigInt(pengu_js_unwrap(v));
    } catch (e) {
      pengu_js_fail(e);
      return 0n;
    }
  },

  pengu_js_to_bool: function(v) {
    return pengu_js_unwrap(v) ? 1 : 0;
  },

  pengu_js_from_string: function(ptr) {
    try {
      return pengu_js_wrap(UTF8ToString(ptr));
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_object: function() {
    return pengu_js_wrap({});
  },

  pengu_js_array: function() {
    return pengu_js_wrap([]);
  },

  pengu_js_length: function(v) {
    try {
      var x = pengu_js_unwrap(v);
      return x && typeof x.length === "number" ? x.length : 0;
    } catch (e) {
      pengu_js_fail(e);
      return 0;
    }
  },

  pengu_js_release: function(v) {
    if (v > 1) {
      PENGU_JS.handles[v] = undefined;
      PENGU_JS.free.push(v);
    }
    return 0;
  },

  pengu_js_retain: function(v) {
    return v;
  },

  pengu_js_make_callback: function(id) {
    return pengu_js_wrap(function() {
      var v;
      if (arguments.length === 0) v = undefined;
      else if (arguments.length === 1) v = arguments[0];
      else v = Array.prototype.slice.call(arguments);
      _pengu_js_invoke(id, pengu_js_wrap(v));
    });
  },

  pengu_js_promise_then: function(p, ok_id, err_id) {
    try {
      Promise.resolve(pengu_js_unwrap(p)).then(
        function(v) { _pengu_js_invoke(ok_id, pengu_js_wrap(v)); },
        function(e) { _pengu_js_invoke(err_id, pengu_js_wrap(e)); }
      );
    } catch (e) {
      _pengu_js_invoke(err_id, pengu_js_wrap(e));
    }
  },

  pengu_js_import_module: function(urlPtr) {
    try {
      return pengu_js_wrap(import(UTF8ToString(urlPtr)));
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_canvas_call: function(ctx, methodPtr, a, b, c, d, n) {
    try {
      var fn = pengu_js_unwrap(ctx)[UTF8ToString(methodPtr)];
      fn.apply(pengu_js_unwrap(ctx), [a, b, c, d].slice(0, n));
      return 0;
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_canvas_text: function(ctx, methodPtr, textPtr, a, b) {
    try {
      var fn = pengu_js_unwrap(ctx)[UTF8ToString(methodPtr)];
      fn.call(pengu_js_unwrap(ctx), UTF8ToString(textPtr), a, b);
      return 0;
    } catch (e) {
      return pengu_js_fail(e);
    }
  },

  pengu_js_last_error: function() {
    return pengu_js_alloc_utf8(PENGU_JS.lastError || "JavaScript error");
  },

  pengu_js_fetch_text: function(urlPtr, ok_id, err_id) {
    fetch(UTF8ToString(urlPtr)).then(
      function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      }
    ).then(
      function(t) { pengu_js_invoke_string(ok_id, t); },
      function(e) { pengu_js_invoke_string(err_id, String(e)); }
    );
    return 0;
  },

  pengu_js_fetch_post: function(urlPtr, bodyPtr, ok_id, err_id) {
    fetch(UTF8ToString(urlPtr), { method: "POST", body: UTF8ToString(bodyPtr) }).then(
      function(r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      }
    ).then(
      function(t) { pengu_js_invoke_string(ok_id, t); },
      function(e) { pengu_js_invoke_string(err_id, String(e)); }
    );
    return 0;
  },

  pengu_js_ws_open: function(urlPtr, open_id, message_id, error_id) {
    try {
      var ws = new WebSocket(UTF8ToString(urlPtr));
      var id = PENGU_JS.ws.length;
      PENGU_JS.ws.push(ws);
      ws.onopen = function() { pengu_js_invoke_string(open_id, ""); };
      ws.onmessage = function(e) { pengu_js_invoke_string(message_id, String(e.data)); };
      ws.onerror = function() { pengu_js_invoke_string(error_id, "WebSocket error"); };
      ws.onclose = function(e) { pengu_js_invoke_string(error_id, "WebSocket closed (" + e.code + ")"); };
      return id;
    } catch (e) {
      pengu_js_fail(e);
      return -1;
    }
  },

  pengu_js_ws_send: function(id, textPtr) {
    try {
      var ws = PENGU_JS.ws[id];
      if (!ws) return -1;
      ws.send(UTF8ToString(textPtr));
      return 0;
    } catch (e) {
      pengu_js_fail(e);
      return -1;
    }
  },

  pengu_js_ws_close: function(id) {
    try {
      var ws = PENGU_JS.ws[id];
      if (ws) ws.close();
      PENGU_JS.ws[id] = null;
      return 0;
    } catch (e) {
      pengu_js_fail(e);
      return -1;
    }
  }
});
