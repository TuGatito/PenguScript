// pengu_js.js - Emscripten JS library for std.web.js.
//
// Contract:
//   * A handle is an i32. 0 = undefined, 1 = null, >= 2 = a registered value.
//   * The PenguScript owner releases a handle exactly once. `retain` adds a
//     reference; `release` only drops one reference, so a stale handle stays
//     invalid instead of being recycled into an alias.
//   * Callback arguments are borrowed for the duration of the callback. The
//     bridge releases its reference when the callback returns, so a callback
//     that wants to keep the value must call `retain` first.
//   * Every entry point catches JavaScript exceptions and converts them into
//     an error result (-1, a null pointer, or `lastError`). Exceptions never
//     escape through the C ABI.
mergeInto(LibraryManager.library, {

    pengu_js_eval: function (codePtr) {
        try {
            return pengu_js_wrap((0, eval)(UTF8ToString(codePtr)));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_global: function () {
        try {
            return pengu_js_wrap(globalThis);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_get: function (obj, namePtr) {
        try {
            var target = pengu_js_unwrap(obj);
            if (target === null || target === undefined) {
                throw new TypeError("cannot read a property of null or undefined");
            }
            return pengu_js_wrap(target[UTF8ToString(namePtr)]);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_set: function (obj, namePtr, value) {
        try {
            var target = pengu_js_unwrap(obj);
            if (target === null || target === undefined) {
                throw new TypeError("cannot write a property of null or undefined");
            }
            target[UTF8ToString(namePtr)] = pengu_js_unwrap(value);
            return 0;
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_get_index: function (obj, index) {
        try {
            var target = pengu_js_unwrap(obj);
            if (target === null || target === undefined) {
                throw new TypeError("cannot index null or undefined");
            }
            return pengu_js_wrap(target[index]);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_set_index: function (obj, index, value) {
        try {
            var target = pengu_js_unwrap(obj);
            if (target === null || target === undefined) {
                throw new TypeError("cannot index null or undefined");
            }
            target[index] = pengu_js_unwrap(value);
            return 0;
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_call: function (fn, thisValue, argsPtr, argc) {
        try {
            var callable = pengu_js_unwrap(fn);
            if (typeof callable !== "function") {
                throw new TypeError("value is not callable");
            }
            var args = [];
            for (var i = 0; i < argc; i++) {
                args.push(pengu_js_unwrap(HEAP32[(argsPtr >> 2) + i]));
            }
            return pengu_js_wrap(callable.apply(pengu_js_unwrap(thisValue), args));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_call_method: function (obj, namePtr, argsPtr, argc) {
        try {
            var target = pengu_js_unwrap(obj);
            var name = UTF8ToString(namePtr);
            if (target === null || target === undefined) {
                throw new TypeError("cannot call a method of null or undefined");
            }
            var callable = target[name];
            if (typeof callable !== "function") {
                throw new TypeError("property '" + name + "' is not callable");
            }
            var args = [];
            for (var i = 0; i < argc; i++) {
                args.push(pengu_js_unwrap(HEAP32[(argsPtr >> 2) + i]));
            }
            return pengu_js_wrap(callable.apply(target, args));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_call_method_f64: function (obj, namePtr, a, b, c, d, e, f, count) {
        try {
            var target = pengu_js_unwrap(obj);
            var name = UTF8ToString(namePtr);
            if (target === null || target === undefined) {
                throw new TypeError("cannot call a method of null or undefined");
            }
            var callable = target[name];
            if (typeof callable !== "function") {
                throw new TypeError("property '" + name + "' is not callable");
            }
            var args = [a, b, c, d, e, f].slice(0, count);
            return pengu_js_wrap(callable.apply(target, args));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_call_method_text_f64: function (obj, namePtr, textPtr, a, b) {
        try {
            var target = pengu_js_unwrap(obj);
            var name = UTF8ToString(namePtr);
            if (target === null || target === undefined) {
                throw new TypeError("cannot call a method of null or undefined");
            }
            var callable = target[name];
            if (typeof callable !== "function") {
                throw new TypeError("property '" + name + "' is not callable");
            }
            return pengu_js_wrap(callable.call(target, UTF8ToString(textPtr), a, b));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_new: function (ctor, argsPtr, argc) {
        try {
            var constructor = pengu_js_unwrap(ctor);
            if (typeof constructor !== "function") {
                throw new TypeError("value is not a constructor");
            }
            var args = [];
            for (var i = 0; i < argc; i++) {
                args.push(pengu_js_unwrap(HEAP32[(argsPtr >> 2) + i]));
            }
            return pengu_js_wrap(Reflect.construct(constructor, args));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_typeof_string: function (value) {
        try {
            return pengu_js_alloc_utf8(typeof pengu_js_unwrap(value));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_is_undefined: function (value) {
        return value === 0 ? 1 : 0;
    },

    pengu_js_is_null: function (value) {
        return value === 1 ? 1 : 0;
    },

    pengu_js_is_valid: function (value) {
        return pengu_js_is_valid_handle(value);
    },

    pengu_js_is_truthy: function (value) {
        try {
            return pengu_js_unwrap(value) ? 1 : 0;
        } catch (e) {
            return 0;
        }
    },

    pengu_js_to_string: function (value) {
        try {
            return pengu_js_alloc_utf8(String(pengu_js_unwrap(value)));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_to_f64: function (value) {
        try {
            var n = Number(pengu_js_unwrap(value));
            if (typeof n !== "number") {
                throw new TypeError("value is not numeric");
            }
            return n;
        } catch (e) {
            pengu_js_fail(e);
            return NaN;
        }
    },

    pengu_js_to_i64: function (value) {
        try {
            return BigInt(pengu_js_unwrap(value));
        } catch (e) {
            pengu_js_fail(e);
            return BigInt(0);
        }
    },

    pengu_js_to_bool: function (value) {
        try {
            return pengu_js_unwrap(value) ? 1 : 0;
        } catch (e) {
            return 0;
        }
    },

    pengu_js_from_string: function (ptr) {
        try {
            return pengu_js_wrap(UTF8ToString(ptr));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_from_f64: function (value) {
        try {
            return pengu_js_wrap(value);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_from_i32: function (value) {
        try {
            return pengu_js_wrap(value);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_object: function () {
        try {
            return pengu_js_wrap({});
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_array: function () {
        try {
            return pengu_js_wrap([]);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_length: function (value) {
        try {
            var target = pengu_js_unwrap(value);
            if (target === null || target === undefined ||
                typeof target.length !== "number") {
                throw new TypeError("value has no length");
            }
            return target.length | 0;
        } catch (e) {
            pengu_js_fail(e);
            return -1;
        }
    },

    pengu_js_release: function (value) {
        if (value <= 1) {
            return 0;
        }
        var entry = PENGU_JS.handles.get(value);
        if (entry) {
            entry.refs--;
            if (entry.refs <= 0) {
                PENGU_JS.handles.delete(value);
            }
        }
        return 0;
    },

    pengu_js_retain: function (value) {
        if (value <= 1) {
            return value;
        }
        var entry = PENGU_JS.handles.get(value);
        if (!entry || entry.refs <= 0) {
            pengu_js_set_error("TypeError", "cannot retain an invalid handle " + value, "");
            return -1;
        }
        entry.refs++;
        return value;
    },

    pengu_js_make_callback: function (id) {
        return pengu_js_wrap(function () {
            var arg = arguments.length > 0 ? arguments[0] : undefined;
            var handle = pengu_js_wrap(arg);
            try {
                if (handle < 0) {
                    return;
                }
                _pengu_js_invoke(id, handle);
            } catch (e) {
                pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                    e && e.stack || "");
            } finally {
                if (handle > 1) {
                    pengu_js_drop_handle(handle);
                }
            }
        });
    },

    pengu_js_promise_then: function (promise, okSlot, errSlot, okHandle, errHandle) {
        var settled = false;
        function settle(ok, value) {
            if (settled) {
                return;
            }
            settled = true;
            var handle = pengu_js_wrap(value);
            if (handle < 0) {
                handle = 1;
            }
            try {
                _pengu_js_invoke_oneshot(ok ? okSlot : errSlot, handle);
            } catch (e) {
                pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                    e && e.stack || "");
            } finally {
                if (handle > 1) {
                    pengu_js_drop_handle(handle);
                }
                pengu_js_drop_handle(okHandle);
                pengu_js_drop_handle(errHandle);
                _pengu_js_callback_free(ok ? errSlot : okSlot);
            }
        }
        try {
            Promise.resolve(pengu_js_unwrap(promise)).then(function (value) {
                settle(true, value);
            }, function (reason) {
                settle(false, reason);
            });
            return 0;
        } catch (e) {
            settle(false, e);
            return 0;
        }
    },

    pengu_js_import_module: function (namePtr) {
        try {
            return pengu_js_wrap(import(UTF8ToString(namePtr)));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_last_error: function () {
        var message = PENGU_JS.lastError ? PENGU_JS.lastError.message : "";
        return pengu_js_alloc_utf8(message || "JavaScript error");
    },

    pengu_js_last_error_name: function () {
        var name = PENGU_JS.lastError ? PENGU_JS.lastError.name : "";
        return pengu_js_alloc_utf8(name || "Error");
    },

    pengu_js_last_error_stack: function () {
        var stack = PENGU_JS.lastError ? PENGU_JS.lastError.stack : "";
        return pengu_js_alloc_utf8(stack || "");
    },

    pengu_js_clear_error: function () {
        PENGU_JS.lastError = null;
    },

    pengu_js_has_error: function () {
        return PENGU_JS.lastError ? 1 : 0;
    },

    pengu_js_fetch: function (methodPtr, urlPtr, headers, body,
                            okSlot, errSlot, okHandle, errHandle, timeoutMs) {
        var id = PENGU_JS.nextRequest++;
        var record = {
            id: id,
            controller: null,
            timer: 0,
            done: false,
            timedOut: false
        };
        PENGU_JS.requests.set(id, record);
        function cleanup() {
            if (record.timer) {
                clearTimeout(record.timer);
                record.timer = 0;
            }
            record.done = true;
            PENGU_JS.requests.delete(id);
        }
        function normalizeError(error) {
            if (record.timedOut) {
                var timedOut = new Error("request timed out after " + timeoutMs + " ms");
                timedOut.name = "TimeoutError";
                return timedOut;
            }
            return error;
        }
        function finish(ok, value) {
            if (record.done) {
                return;
            }
            cleanup();
            var handle = pengu_js_wrap(ok ? value : normalizeError(value));
            if (handle < 0) {
                handle = 1;
            }
            try {
                _pengu_js_invoke_oneshot(ok ? okSlot : errSlot, handle);
            } catch (e) {
                pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                    e && e.stack || "");
            } finally {
                if (handle > 1) {
                    pengu_js_drop_handle(handle);
                }
                pengu_js_drop_handle(okHandle);
                pengu_js_drop_handle(errHandle);
                _pengu_js_callback_free(ok ? errSlot : okSlot);
            }
        }
        try {
            var init = {
                method: UTF8ToString(methodPtr) || "GET",
                headers: new Headers(),
                credentials: "same-origin"
            };
            if (headers > 1) {
                var source = pengu_js_unwrap(headers);
                for (var key in source) {
                    if (Object.prototype.hasOwnProperty.call(source, key)) {
                        init.headers.set(key, String(source[key]));
                    }
                }
            }
            if (body > 1) {
                init.body = pengu_js_unwrap(body);
            } else if (body === 1) {
                init.body = null;
            }
            if (typeof AbortController === "undefined") {
                throw new Error("AbortController is not available in this environment");
            }
            var controller = new AbortController();
            record.controller = controller;
            init.signal = controller.signal;
            if (timeoutMs > 0) {
                record.timer = setTimeout(function () {
                    record.timedOut = true;
                    controller.abort();
                }, timeoutMs);
            }
            fetch(UTF8ToString(urlPtr), init).then(function (response) {
                return response.text().then(function (text) {
                    return {
                        status: response.status,
                        status_text: response.statusText,
                        ok: response.ok,
                        url: response.url,
                        redirected: response.redirected,
                        headers: Object.fromEntries(response.headers.entries()),
                        body: text
                    };
                }, function (error) {
                    error.status = response.status;
                    error.status_text = response.statusText;
                    throw error;
                });
            }).then(function (response) {
                finish(true, response);
            }, function (error) {
                finish(false, error);
            });
            return id;
        } catch (e) {
            cleanup();
            return pengu_js_fail(e);
        }
    },

    pengu_js_abort: function (id) {
        var record = PENGU_JS.requests.get(id | 0);
        if (!record || record.done || !record.controller) {
            return 0;
        }
        record.controller.abort();
        return 1;
    },

    pengu_js_ws_open: function (urlPtr, openSlot, msgSlot, closeSlot, errSlot,
                                openHandle, msgHandle, closeHandle, errHandle) {
        try {
            if (typeof WebSocket === "undefined") {
                throw new Error("WebSocket is not available in this environment");
            }
            var id = PENGU_JS.nextWs++;
            var socket = new WebSocket(UTF8ToString(urlPtr));
            var record = {
                socket: socket,
                openSlot: openSlot,
                msgSlot: msgSlot,
                closeSlot: closeSlot,
                errSlot: errSlot,
                openHandle: openHandle,
                msgHandle: msgHandle,
                closeHandle: closeHandle,
                errHandle: errHandle,
                closed: false,
                timer: 0
            };
            PENGU_JS.ws.set(id, record);

            function finishClose(code, reason) {
                if (record.closed) {
                    return;
                }
                record.closed = true;
                if (record.timer) {
                    clearTimeout(record.timer);
                }
                PENGU_JS.ws.delete(id);
                try {
                    pengu_js_invoke_string(record.closeSlot,
                        String(code) + " " + String(reason || ""));
                } catch (e) {
                    pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                        e && e.stack || "");
                }
                _pengu_js_callback_free(record.openSlot);
                _pengu_js_callback_free(record.msgSlot);
                _pengu_js_callback_free(record.errSlot);
                _pengu_js_callback_free(record.closeSlot);
                pengu_js_drop_handle(record.openHandle);
                pengu_js_drop_handle(record.msgHandle);
                pengu_js_drop_handle(record.closeHandle);
                pengu_js_drop_handle(record.errHandle);
            }

            socket.onopen = function () {
                try {
                    _pengu_js_invoke(record.openSlot, 0);
                } catch (e) {
                    pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                        e && e.stack || "");
                }
            };
            socket.onmessage = function (event) {
                try {
                    pengu_js_invoke_string(record.msgSlot, String(event.data));
                } catch (e) {
                    pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                        e && e.stack || "");
                }
            };
            socket.onerror = function () {
                try {
                    pengu_js_invoke_string(record.errSlot, "WebSocket error");
                } catch (e) {
                    pengu_js_set_error(e && e.name || "Error", e && e.message || String(e),
                        e && e.stack || "");
                }
            };
            socket.onclose = function (event) {
                finishClose(event.code, event.reason);
            };
            record.timer = setTimeout(function () {
                finishClose(1006, "connection timeout");
            }, 10000);
            return id;
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_ws_send: function (id, textPtr) {
        try {
            var record = PENGU_JS.ws.get(id);
            if (!record || record.closed || record.socket.readyState !== 1) {
                throw new Error("WebSocket is not open");
            }
            record.socket.send(UTF8ToString(textPtr));
            return 0;
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_ws_close: function (id, code, reasonPtr) {
        try {
            var record = PENGU_JS.ws.get(id);
            if (!record || record.closed) {
                return 0;
            }
            var safeCode = code >= 1000 && code <= 4999 ? code : 1000;
            var reason = UTF8ToString(reasonPtr).slice(0, 123);
            if (record.socket.readyState === 3) {
                record.closed = true;
                PENGU_JS.ws.delete(id);
                _pengu_js_callback_free(record.openSlot);
                _pengu_js_callback_free(record.msgSlot);
                _pengu_js_callback_free(record.errSlot);
                _pengu_js_callback_free(record.closeSlot);
                pengu_js_drop_handle(record.openHandle);
                pengu_js_drop_handle(record.msgHandle);
                pengu_js_drop_handle(record.closeHandle);
                pengu_js_drop_handle(record.errHandle);
                return 0;
            }
            record.socket.close(safeCode, reason);
            return 0;
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_ws_state: function (id) {
        var record = PENGU_JS.ws.get(id);
        if (!record || record.closed) {
            return 3;
        }
        return record.socket.readyState | 0;
    },

    pengu_js_ws_count: function () {
        return PENGU_JS.ws.size | 0;
    },

    pengu_js_sha256: function (textPtr, okSlot, errSlot, okHandle, errHandle) {
        try {
            var g = typeof globalThis !== "undefined" ? globalThis : self;
            if (!g.crypto || !g.crypto.subtle || typeof TextEncoder === "undefined") {
                throw new Error("crypto.subtle is not available");
            }
            var bytes = new TextEncoder().encode(UTF8ToString(textPtr));
            g.crypto.subtle.digest("SHA-256", bytes).then(function (buffer) {
                var view = new Uint8Array(buffer);
                var hex = "";
                for (var i = 0; i < view.length; i++) {
                    hex += view[i].toString(16).padStart(2, "0");
                }
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, true, hex);
            }, function (e) {
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            });
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_hmac_sha256: function (textPtr, keyPtr, okSlot, errSlot, okHandle, errHandle) {
        try {
            var g = typeof globalThis !== "undefined" ? globalThis : self;
            if (!g.crypto || !g.crypto.subtle || typeof TextEncoder === "undefined") {
                throw new Error("crypto.subtle is not available");
            }
            var encoder = new TextEncoder();
            var keyBytes = encoder.encode(UTF8ToString(keyPtr));
            var msgBytes = encoder.encode(UTF8ToString(textPtr));
            g.crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-256" },
                false, ["sign"]).then(function (key) {
                return g.crypto.subtle.sign("HMAC", key, msgBytes);
            }).then(function (buffer) {
                var view = new Uint8Array(buffer);
                var hex = "";
                for (var i = 0; i < view.length; i++) {
                    hex += view[i].toString(16).padStart(2, "0");
                }
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, true, hex);
            }, function (e) {
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            });
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_file_pick: function (acceptPtr, okSlot, errSlot, okHandle, errHandle) {
        try {
            if (typeof document === "undefined") {
                throw new Error("document is not available");
            }
            var input = document.createElement("input");
            input.type = "file";
            var accept = UTF8ToString(acceptPtr);
            if (accept) {
                input.accept = accept;
            }
            input.style.display = "none";
            input.addEventListener("change", function () {
                var file = input.files && input.files[0];
                if (!file) {
                    pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false,
                        new Error("no file selected"));
                    return;
                }
                pengu_js_read_file(file, "text", okSlot, errSlot, okHandle, errHandle);
            });
            document.body.appendChild(input);
            input.click();
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_file_read_text: function (fileHandle, okSlot, errSlot, okHandle, errHandle) {
        try {
            var file = pengu_js_unwrap(fileHandle);
            pengu_js_read_file(file, "text", okSlot, errSlot, okHandle, errHandle);
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_file_read_data_url: function (fileHandle, okSlot, errSlot, okHandle, errHandle) {
        try {
            var file = pengu_js_unwrap(fileHandle);
            pengu_js_read_file(file, "dataurl", okSlot, errSlot, okHandle, errHandle);
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_file_save: function (textPtr, namePtr, mimePtr) {
        try {
            var text = UTF8ToString(textPtr);
            var name = UTF8ToString(namePtr) || "download.txt";
            var mime = UTF8ToString(mimePtr) || "text/plain;charset=utf-8";
            var blob = new Blob([text], { type: mime });
            var url = URL.createObjectURL(blob);
            var link = document.createElement("a");
            link.href = url;
            link.download = name;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            setTimeout(function () { URL.revokeObjectURL(url); }, 0);
            return 0;
        } catch (e) {
            pengu_js_fail(e);
            return -1;
        }
    },

    pengu_js_clipboard_write_text: function (textPtr, okSlot, errSlot, okHandle, errHandle) {
        try {
            var clipboard = navigator.clipboard;
            if (!clipboard || typeof clipboard.writeText !== "function") {
                throw new Error("navigator.clipboard.writeText is not available");
            }
            clipboard.writeText(UTF8ToString(textPtr)).then(function () {
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, true, true);
            }, function (e) {
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            });
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_clipboard_read_text: function (okSlot, errSlot, okHandle, errHandle) {
        try {
            var clipboard = navigator.clipboard;
            if (!clipboard || typeof clipboard.readText !== "function") {
                throw new Error("navigator.clipboard.readText is not available");
            }
            clipboard.readText().then(function (text) {
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, true, text);
            }, function (e) {
                pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            });
            return 0;
        } catch (e) {
            pengu_js_settle(okSlot, okHandle, errSlot, errHandle, false, e);
            return -1;
        }
    },

    pengu_js_canvas_call: function (context, methodPtr, a, b, c, d) {
        try {
            var target = pengu_js_unwrap(context);
            var name = UTF8ToString(methodPtr);
            if (target === null || target === undefined) {
                throw new TypeError("canvas context is null or undefined");
            }
            var callable = target[name];
            if (typeof callable !== "function") {
                throw new TypeError("canvas method '" + name + "' is not callable");
            }
            return pengu_js_wrap(callable.call(target, a, b, c, d));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_canvas_text: function (context, methodPtr, textPtr, a, b) {
        try {
            var target = pengu_js_unwrap(context);
            var name = UTF8ToString(methodPtr);
            if (target === null || target === undefined) {
                throw new TypeError("canvas context is null or undefined");
            }
            var callable = target[name];
            if (typeof callable !== "function") {
                throw new TypeError("canvas method '" + name + "' is not callable");
            }
            return pengu_js_wrap(callable.call(target, UTF8ToString(textPtr), a, b));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_keys: function (value) {
        try {
            var target = pengu_js_unwrap(value);
            if (target === null || target === undefined) {
                throw new TypeError("cannot enumerate null or undefined");
            }
            return pengu_js_wrap(Object.keys(target));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_json_parse: function (ptr) {
        try {
            return pengu_js_wrap(JSON.parse(UTF8ToString(ptr)));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_json_stringify: function (value) {
        try {
            return pengu_js_wrap(JSON.stringify(pengu_js_unwrap(value)));
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_random_bytes: function (count) {
        if (count <= 0) {
            return pengu_js_fail(new RangeError("random_bytes needs a positive count"));
        }
        try {
            var g = typeof globalThis !== "undefined" ? globalThis : self;
            if (!g.crypto || typeof g.crypto.getRandomValues !== "function") {
                throw new Error("crypto.getRandomValues is not available");
            }
            var bytes = new Uint8Array(count);
            g.crypto.getRandomValues(bytes);
            return pengu_js_wrap(bytes);
        } catch (e) {
            return pengu_js_fail(e);
        }
    },

    pengu_js_random_int: function (min, max) {
        try {
            if (min < 0 || max <= min) {
                throw new RangeError("random_int needs 0 <= min < max");
            }
            var g = typeof globalThis !== "undefined" ? globalThis : self;
            if (!g.crypto || typeof g.crypto.getRandomValues !== "function") {
                throw new Error("crypto.getRandomValues is not available");
            }
            var span = max - min;
            var limit = Math.floor(0x100000000 / span) * span;
            var word = new Uint32Array(1);
            do {
                g.crypto.getRandomValues(word);
            } while (word[0] >= limit);
            return min + (word[0] % span);
        } catch (e) {
            pengu_js_fail(e);
            return -1;
        }
    },

    pengu_js_handle_count: function () {
        return PENGU_JS.handles.size | 0;
    }
});
