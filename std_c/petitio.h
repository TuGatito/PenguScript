/*
 * petitio.h — the C transport layer behind `std.petitio`.
 *
 * ## Why libcurl and not naett
 *
 * `naett` was evaluated first (single header, MIT, vendored in this repository
 * at one point).  Its public API — `naettRequest`, `naettMethod`, `naettHeader`,
 * `naettBody`, `naettTimeout`, `naettMake`, `naettComplete`, `naettGetStatus`,
 * `naettGetBody`, `naettClose` — cannot express what a `requests`-shaped client
 * needs:
 *
 *   - `naettTimeout` is a *connect* timeout only; there is no total deadline;
 *   - redirection is hard-wired to on (the Linux backend passes
 *     `CURLOPT_FOLLOWLOCATION, 1`) with no limit control and no way to see
 *     intermediate statuses;
 *   - there is no cookie engine, no TLS-verification toggle, no proxy, no
 *     multipart, no streaming controls, and the response header list is
 *     read-only per name (duplicate `Set-Cookie` lines are lost);
 *   - worse, the Linux backend *is* libcurl, so "avoiding the dependency" was
 *     never true; and the vendored copy did not compile under the repository's
 *     `-std=c99 -Wall -Wextra -Werror` gate (`strndup` is POSIX, an unused
 *     parameter, implicit declarations).
 *
 * libcurl has the same licence family (MIT-like), is preinstalled on Linux,
 * macOS and the supported Linux CI images, and exposes every knob this wrapper
 * documents.  `std.petitio` therefore links `-lcurl` directly.  See
 * `docs/PETITIO.md` §"Why libcurl".
 *
 * ## Contract
 *
 * This header is *not* the public PenguScript API.  `std/petitio.pengu` owns
 * the `Request`/`Response`/`Session` types, the error model and ownership; this
 * layer only moves bytes and reports transport failures.  Every string that
 * crosses the boundary is either borrowed for the duration of the call (the
 * `PenguString` arguments) or returned as an owned `PenguString`
 * (`is_owned == 1`, release with `banish`).
 *
 * The request object is a builder: create it, configure it, call
 * `petitio_request_perform` once (or more), then `petitio_request_free`.
 * The response object owns its body, its URL and its header block; release it
 * with `petitio_response_free`.  Both are plain C allocations, not PenguScript
 * values, because libcurl needs a stable address across callbacks.
 */
#ifndef PETITIO_H
#define PETITIO_H

#ifdef PETITIO_BIND
/* Reduced, ABI-identical surface used only to regenerate `std/petitio.d.pengu`:
 * `pengu bind` runs pycparser, which cannot digest the GNU extensions inside
 * `pengu_runtime.h` (`__builtin_va_list`, `__attribute__`, …). Regenerate with
 *
 *     pengu bind std_c/petitio.h --output std/petitio.d.pengu \
 *         --cpp-flags "-DPETITIO_BIND=1" --links petitio curl
 *
 * then hand-tune the result (`PenguString` -> `string`, `int64_t` -> `i64`,
 * `double` -> `f64`) as documented in docs/PETITIO.md. The real build always
 * takes the branch below and sees the genuine runtime definition. */
#include <stdint.h>
typedef struct { char *data; int len; int32_t is_owned; } PenguString;
#else
/* `pengu_runtime.h` first: it defines `_POSIX_C_SOURCE`/`_DEFAULT_SOURCE`
 * before any system header is seen. A `<stdint.h>` above it would pull in
 * `features.h` first and hide `clock_gettime`, `sigaction`, … under -std=c99. */
#include "pengu_runtime.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* Error classes. Mirrored one-to-one by `omen HttpError` in std/petitio.pengu;
 * keep the two lists in sync (tests/stdlib/test_petitio.py checks the order). */
typedef enum petitio_error {
    PETITIO_OK = 0,
    PETITIO_CONNECTION_FAILED = 1,
    PETITIO_TIMEOUT = 2,
    PETITIO_TOO_MANY_REDIRECTS = 3,
    PETITIO_INVALID_URL = 4,
    PETITIO_TLS_ERROR = 5,
    PETITIO_PROTOCOL_ERROR = 6,
    PETITIO_BODY_TOO_LARGE = 7,
    PETITIO_OUT_OF_MEMORY = 8,
    PETITIO_UNSUPPORTED = 9
} petitio_error;

typedef struct petitio_request petitio_request;
typedef struct petitio_response petitio_response;

/* --- Request builder ---------------------------------------------------- */

/* Creates a request for `url`. Returns NULL only when the allocator fails. */
petitio_request *petitio_request_new(PenguString url);

/* Releases the request and everything it copied. Call once. */
void petitio_request_free(petitio_request *request);

/* Sets the HTTP method ("GET", "POST", …). Defaults to "GET". */
void petitio_request_set_method(petitio_request *request, PenguString method);

/* Adds one request header. The name must not contain ':' or CR/LF; the value
 * must not contain CR/LF (rejected by the wrapper before it gets here). */
void petitio_request_add_header(petitio_request *request, PenguString name,
                                PenguString value);

/* Sets the request body (copied; may contain NUL bytes). */
void petitio_request_set_body(petitio_request *request, PenguString body);

/* Total and connect deadlines in milliseconds; 0 disables that deadline. */
void petitio_request_set_timeout(petitio_request *request, int64_t timeout_ms,
                                 int64_t connect_timeout_ms);

/* Protocol version: 0 = HTTP/1.1 (default), 1 = HTTP/2 over ALPN,
 * 2 = HTTP/2 prior knowledge (no fallback). */
void petitio_request_set_http_version(petitio_request *request, int version);

/* Redirect policy. `max_redirects` is only meaningful when `follow` is non-zero. */
void petitio_request_set_redirects(petitio_request *request, int follow,
                                   int64_t max_redirects);

/* 0 disables peer/host verification (documented as insecure). */
void petitio_request_set_verify_tls(petitio_request *request, int verify);

/* Aborts the transfer once the body exceeds `max_bytes` (0 = unlimited). */
void petitio_request_set_max_body(petitio_request *request, int64_t max_bytes);

/* Basic authentication (RFC 7617). Empty user disables it. */
void petitio_request_set_basic_auth(petitio_request *request, PenguString user,
                                    PenguString password);

/* HTTP proxy, e.g. "http://127.0.0.1:8080". Empty disables it. */
void petitio_request_set_proxy(petitio_request *request, PenguString proxy,
                               PenguString credentials);

/* Adds one multipart/form-data part held in memory. `filename` and
 * `content_type` may be empty. Returns 1 on success, 0 on allocation failure. */
int petitio_request_add_form_field(petitio_request *request, PenguString name,
                                   PenguString value, PenguString filename,
                                   PenguString content_type);

/* Performs the request. Never returns NULL: an allocation failure is reported
 * as PETITIO_OUT_OF_MEMORY on a response object with no body. */
petitio_response *petitio_request_perform(petitio_request *request);

/* --- Response ----------------------------------------------------------- */

/* One of `petitio_error`. */
int petitio_response_error(const petitio_response *response);

/* Human-readable transport error, or "" when the request completed. Owned. */
PenguString petitio_response_error_message(const petitio_response *response);

/* HTTP status code, or 0 when no response line was received. */
int petitio_response_status(const petitio_response *response);

/* Response body bytes (decoded when the server compressed it). Owned. */
PenguString petitio_response_body(const petitio_response *response);

/* Effective URL after redirects. Owned. */
PenguString petitio_response_url(const petitio_response *response);

/* Wall-clock duration of the transfer, in seconds. */
double petitio_response_elapsed(const petitio_response *response);

/* Number of redirects followed. */
int petitio_response_redirect_count(const petitio_response *response);

/* Negotiated protocol version: 0 = HTTP/1.0, 1 = HTTP/1.1, 2 = HTTP/2,
 * 4 = HTTP/3. */
int petitio_response_http_version(const petitio_response *response);

/* Final-response header count. Duplicates are preserved in receipt order and
 * names are lower-case. */
int petitio_response_header_count(const petitio_response *response);
PenguString petitio_response_header_name(const petitio_response *response,
                                         int index);
PenguString petitio_response_header_value(const petitio_response *response,
                                          int index);

/* Releases the response and its body/header block. Call once. */
void petitio_response_free(petitio_response *response);

/* Parses an HTTP date (`Wed, 21 Oct 2015 07:28:00 GMT`) into a Unix timestamp
 * with libcurl's own parser, or -1 when the text is not a valid HTTP date. */
int64_t petitio_parse_http_date(PenguString text);

/* libcurl runtime version, for diagnostics ("libcurl/8.22.0"). Owned. */
PenguString petitio_version(void);

#ifdef __cplusplus
}
#endif

#endif /* PETITIO_H */
