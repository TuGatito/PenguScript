/*
 * petitio.c — libcurl transport for `std.petitio`.
 *
 * See petitio.h for the design decision (libcurl instead of naett) and the
 * ownership contract.  This file is compiled by `build_runtime.py` into
 * `build/lib/libpetitio.a`; a program that never imports `std.petitio` never
 * receives `-lpetitio` (smart linking), and one that does links `-lcurl` as
 * well.
 *
 * The code is deliberately C99 and warning-clean under
 * `-std=c99 -Wall -Wextra -Werror` (the std_c build gate).
 */
#include "petitio.h"

#include <curl/curl.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -------------------------------------------------------------------------
 * Small helpers
 * ------------------------------------------------------------------------- */

/* Copies `len` bytes plus a terminating NUL. Returns NULL on allocation
 * failure or when `len` is negative. */
static char *petitio_dup_n(const char *data, int len)
{
    char *out;
    if (len < 0 || (data == NULL && len > 0))
        return NULL;
    out = (char *)malloc((size_t)len + 1);
    if (out == NULL)
        return NULL;
    if (len > 0)
        memcpy(out, data, (size_t)len);
    out[len] = '\0';
    return out;
}

static char *petitio_dup_pengu(PenguString s)
{
    if (s.data == NULL)
        s.len = 0;
    return petitio_dup_n(s.data, s.len);
}

/* An owned PenguString over a fresh copy of `len` bytes (never NULL: an empty
 * string is a valid result and callers `banish` it unconditionally). */
static PenguString petitio_pengu_dup(const char *data, int len)
{
    char *buf = petitio_dup_n(data, len);
    PenguString out;
    if (buf == NULL) {
        out.data = (char *)"";
        out.len = 0;
        out.is_owned = 0;
        return out;
    }
    out.data = buf;
    out.len = len;
    out.is_owned = 1;
    return out;
}

/* The empty owned string: `banish` on it is a no-op because is_owned is 0. */
static PenguString petitio_pengu_empty(void)
{
    PenguString out;
    out.data = (char *)"";
    out.len = 0;
    out.is_owned = 0;
    return out;
}

static int petitio_ascii_lower(int c)
{
    if (c >= 'A' && c <= 'Z')
        return c - 'A' + 'a';
    return c;
}

/* Grows `*buf` (capacity `*cap`) so that at least `needed` bytes fit.
 * Returns 1 on success, 0 on allocation failure. */
static int petitio_reserve(char **buf, int *cap, int needed)
{
    int next;
    char *grown;
    if (needed <= *cap)
        return 1;
    next = *cap > 0 ? *cap : 64;
    while (next < needed) {
        if (next > 0x3FFFFFFF) { /* keep int arithmetic from overflowing */
            next = needed;
            break;
        }
        next *= 2;
    }
    grown = (char *)realloc(*buf, (size_t)next);
    if (grown == NULL)
        return 0;
    *buf = grown;
    *cap = next;
    return 1;
}

/* -------------------------------------------------------------------------
 * Global init (exactly once, thread-safe)
 * ------------------------------------------------------------------------- */

#if defined(_WIN32)
/* `InitOnceExecuteOnce` needs Vista or newer; the macro must be defined before
 * <windows.h> pulls in the Win32 headers, or the declaration is hidden. */
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#endif
#include <windows.h>
static INIT_ONCE petitio_once = INIT_ONCE_STATIC_INIT;
static BOOL CALLBACK petitio_once_cb(PINIT_ONCE once, PVOID param, PVOID *ctx)
{
    (void)once;
    (void)param;
    (void)ctx;
    return curl_global_init(CURL_GLOBAL_DEFAULT) == CURLE_OK ? TRUE : FALSE;
}
static void petitio_global_init(void)
{
    InitOnceExecuteOnce(&petitio_once, petitio_once_cb, NULL, NULL);
}
#else
#include <pthread.h>
static pthread_once_t petitio_once = PTHREAD_ONCE_INIT;
static void petitio_once_cb(void)
{
    /* Failure is surfaced by every curl_easy_init that follows; there is no
     * useful recovery that this layer could attempt. */
    (void)curl_global_init(CURL_GLOBAL_DEFAULT);
}
static void petitio_global_init(void)
{
    (void)pthread_once(&petitio_once, petitio_once_cb);
}
#endif

/* -------------------------------------------------------------------------
 * Request
 * ------------------------------------------------------------------------- */

typedef struct petitio_part {
    char *name;
    char *value;
    int value_len;
    char *filename;
    char *content_type;
} petitio_part;

struct petitio_request {
    char *url;
    char *method;
    struct curl_slist *headers;
    char *body;
    int body_len;
    int has_body;
    int64_t timeout_ms;
    int64_t connect_timeout_ms;
    int follow_redirects;
    int64_t max_redirects;
    int verify_tls;
    int http_version;
    int64_t max_body;
    char *username;
    char *password;
    int auth_mode;
    char *proxy;
    char *proxy_credentials;
    petitio_part *parts;
    int part_count;
    int part_cap;
    char error_buffer[CURL_ERROR_SIZE];
};

static void petitio_request_clear_error(petitio_request *request)
{
    request->error_buffer[0] = '\0';
}

petitio_request *petitio_request_new(PenguString url)
{
    petitio_request *request = (petitio_request *)calloc(1, sizeof(petitio_request));
    if (request == NULL)
        return NULL;
    request->url = petitio_dup_pengu(url);
    if (request->url == NULL) {
        free(request);
        return NULL;
    }
    request->method = petitio_dup_n("GET", 3);
    if (request->method == NULL) {
        free(request->url);
        free(request);
        return NULL;
    }
    /* Defaults mirror Python's `requests`: follow up to 30 redirects and
     * verify TLS.  `std.petitio` may tighten the limit per request. */
    request->follow_redirects = 1;
    request->max_redirects = 30;
    request->verify_tls = 1;
    request->error_buffer[0] = '\0';
    return request;
}

void petitio_request_free(petitio_request *request)
{
    int i;
    if (request == NULL)
        return;
    if (request->headers != NULL)
        curl_slist_free_all(request->headers);
    for (i = 0; i < request->part_count; ++i) {
        free(request->parts[i].name);
        free(request->parts[i].value);
        free(request->parts[i].filename);
        free(request->parts[i].content_type);
    }
    free(request->parts);
    free(request->url);
    free(request->method);
    free(request->body);
    free(request->username);
    free(request->password);
    free(request->proxy);
    free(request->proxy_credentials);
    free(request);
}

void petitio_request_set_method(petitio_request *request, PenguString method)
{
    char *fresh;
    if (request == NULL)
        return;
    fresh = petitio_dup_pengu(method);
    if (fresh == NULL)
        return;
    free(request->method);
    request->method = fresh;
}

void petitio_request_add_header(petitio_request *request, PenguString name,
                                PenguString value)
{
    struct curl_slist *next;
    char *line;
    char *name_copy;
    int name_len;
    int total;
    if (request == NULL)
        return;
    /* Build "name: value" in one allocation.  The wrapper guarantees there is
     * no CR/LF or ':' in the name, so this is a literal join. */
    name_len = name.len < 0 ? 0 : name.len;
    total = name_len + 2 + (value.len < 0 ? 0 : value.len);
    line = (char *)malloc((size_t)total + 1);
    if (line == NULL)
        return;
    name_copy = line;
    if (name_len > 0 && name.data != NULL)
        memcpy(name_copy, name.data, (size_t)name_len);
    name_copy[name_len] = ':';
    name_copy[name_len + 1] = ' ';
    if (value.len > 0 && value.data != NULL)
        memcpy(name_copy + name_len + 2, value.data, (size_t)value.len);
    line[total] = '\0';
    next = curl_slist_append(request->headers, line);
    free(line);
    if (next == NULL)
        return; /* keep the previous list: a dropped header is a visible failure */
    request->headers = next;
}

void petitio_request_set_body(petitio_request *request, PenguString body)
{
    char *fresh;
    if (request == NULL)
        return;
    fresh = petitio_dup_pengu(body);
    if (fresh == NULL)
        return;
    free(request->body);
    request->body = fresh;
    request->body_len = body.len < 0 ? 0 : body.len;
    request->has_body = 1;
}

void petitio_request_set_timeout(petitio_request *request, int64_t timeout_ms,
                                 int64_t connect_timeout_ms)
{
    if (request == NULL)
        return;
    request->timeout_ms = timeout_ms < 0 ? 0 : timeout_ms;
    request->connect_timeout_ms = connect_timeout_ms < 0 ? 0 : connect_timeout_ms;
}

void petitio_request_set_redirects(petitio_request *request, int follow,
                                   int64_t max_redirects)
{
    if (request == NULL)
        return;
    request->follow_redirects = follow != 0;
    request->max_redirects = max_redirects < 0 ? 0 : max_redirects;
}

void petitio_request_set_verify_tls(petitio_request *request, int verify)
{
    if (request == NULL)
        return;
    request->verify_tls = verify != 0;
}

void petitio_request_set_max_body(petitio_request *request, int64_t max_bytes)
{
    if (request == NULL)
        return;
    request->max_body = max_bytes < 0 ? 0 : max_bytes;
}

void petitio_request_set_http_version(petitio_request *request, int version)
{
    if (request == NULL)
        return;
    request->http_version = version < 0 || version > 3 ? 0 : version;
}

void petitio_request_set_basic_auth(petitio_request *request, PenguString user,
                                    PenguString password)
{
    char *user_copy;
    char *password_copy;
    if (request == NULL || user.len <= 0)
        return;
    user_copy = petitio_dup_pengu(user);
    password_copy = petitio_dup_pengu(password);
    if (user_copy == NULL || password_copy == NULL) {
        free(user_copy);
        free(password_copy);
        return;
    }
    free(request->username);
    free(request->password);
    request->username = user_copy;
    request->password = password_copy;
}

void petitio_request_set_auth_mode(petitio_request *request, int mode)
{
    if (request == NULL)
        return;
    request->auth_mode = mode < 0 || mode > 3 ? 0 : mode;
}

void petitio_request_set_proxy(petitio_request *request, PenguString proxy,
                               PenguString credentials)
{
    char *fresh_proxy = NULL;
    char *fresh_credentials = NULL;
    if (request == NULL)
        return;
    if (proxy.len > 0) {
        fresh_proxy = petitio_dup_pengu(proxy);
        if (fresh_proxy == NULL)
            return;
    }
    if (credentials.len > 0) {
        fresh_credentials = petitio_dup_pengu(credentials);
        if (fresh_credentials == NULL) {
            free(fresh_proxy);
            return;
        }
    }
    free(request->proxy);
    free(request->proxy_credentials);
    request->proxy = fresh_proxy;
    request->proxy_credentials = fresh_credentials;
}

int petitio_request_add_form_field(petitio_request *request, PenguString name,
                                   PenguString value, PenguString filename,
                                   PenguString content_type)
{
    petitio_part part;
    if (request == NULL)
        return 0;
    if (request->part_count == request->part_cap) {
        int next_cap = request->part_cap == 0 ? 4 : request->part_cap * 2;
        petitio_part *grown = (petitio_part *)realloc(
            request->parts, (size_t)next_cap * sizeof(petitio_part));
        if (grown == NULL)
            return 0;
        request->parts = grown;
        request->part_cap = next_cap;
    }
    memset(&part, 0, sizeof(part));
    part.name = petitio_dup_pengu(name);
    part.value = petitio_dup_pengu(value);
    part.value_len = value.len < 0 ? 0 : value.len;
    part.filename = petitio_dup_pengu(filename);
    part.content_type = petitio_dup_pengu(content_type);
    if (part.name == NULL || part.value == NULL || part.filename == NULL
        || part.content_type == NULL) {
        free(part.name);
        free(part.value);
        free(part.filename);
        free(part.content_type);
        return 0;
    }
    request->parts[request->part_count] = part;
    request->part_count += 1;
    return 1;
}

/* -------------------------------------------------------------------------
 * Response
 * ------------------------------------------------------------------------- */

typedef struct petitio_header {
    char *name;
    int name_len;
    char *value;
    int value_len;
} petitio_header;

struct petitio_response {
    int error;
    char *error_message;
    int status;
    char *body;
    int body_len;
    int body_cap;
    char *url;
    int url_len;
    double elapsed;
    int redirects;
    int http_version;
    int64_t bytes_written;
    int64_t max_body;
    int body_too_large;
    petitio_header *headers;
    int header_count;
    int header_cap;
};

static void petitio_response_clear_headers(petitio_response *response)
{
    int i;
    for (i = 0; i < response->header_count; ++i) {
        free(response->headers[i].name);
        free(response->headers[i].value);
    }
    response->header_count = 0;
}

static int petitio_response_add_header(petitio_response *response,
                                       const char *line, size_t total)
{
    const char *colon;
    const char *name_begin;
    const char *value_begin;
    const char *value_end;
    int name_len;
    int value_len;
    int i;
    petitio_header *grown;

    /* Strip the CRLF libcurl includes. */
    while (total > 0 && (line[total - 1] == '\n' || line[total - 1] == '\r'))
        total -= 1;
    if (total == 0)
        return 1;
    colon = (const char *)memchr(line, ':', total);
    if (colon == NULL)
        return 1; /* not a header line (e.g. the status line, handled earlier) */

    name_begin = line;
    name_len = (int)(colon - line);
    value_begin = colon + 1;
    value_end = line + total;
    while (value_begin < value_end && (*value_begin == ' ' || *value_begin == '\t'))
        value_begin += 1;
    while (value_end > value_begin
           && (value_end[-1] == ' ' || value_end[-1] == '\t'))
        value_end -= 1;
    value_len = (int)(value_end - value_begin);
    if (response->header_count == response->header_cap) {
        int next_cap = response->header_cap == 0 ? 16 : response->header_cap * 2;
        grown = (petitio_header *)realloc(
            response->headers, (size_t)next_cap * sizeof(petitio_header));
        if (grown == NULL)
            return 0;
        response->headers = grown;
        response->header_cap = next_cap;
    }
    grown = &response->headers[response->header_count];
    memset(grown, 0, sizeof(*grown));
    grown->name = petitio_dup_n(name_begin, name_len);
    grown->value = petitio_dup_n(value_begin, value_len);
    if (grown->name == NULL || grown->value == NULL) {
        free(grown->name);
        free(grown->value);
        return 0;
    }
    /* Header names are case-insensitive: store them lower-case so the wrapper
     * can build its map without a second pass. */
    for (i = 0; i < name_len; ++i)
        grown->name[i] = (char)petitio_ascii_lower((unsigned char)grown->name[i]);
    grown->name_len = name_len;
    grown->value_len = value_len;
    response->header_count += 1;
    return 1;
}

static size_t petitio_write_cb(char *ptr, size_t size, size_t nmemb, void *userdata)
{
    petitio_response *response = (petitio_response *)userdata;
    size_t total = size * nmemb;
    int needed;
    if (response->body_too_large)
        return 0;
    if (response->max_body > 0
        && (int64_t)response->body_len + (int64_t)total > response->max_body) {
        response->body_too_large = 1;
        return 0;
    }
    if (total > (size_t)0x3FFFFFFF)
        return 0;
    needed = response->body_len + (int)total;
    if (!petitio_reserve(&response->body, &response->body_cap, needed))
        return 0;
    if (total > 0)
        memcpy(response->body + response->body_len, ptr, total);
    response->body_len = needed;
    return total;
}

static size_t petitio_header_cb(char *ptr, size_t size, size_t nmemb, void *userdata)
{
    petitio_response *response = (petitio_response *)userdata;
    size_t total = size * nmemb;
    /* A new status line starts a new response: libcurl reports the headers of
     * intermediate redirect responses too, and `Response.headers` must describe
     * the final one (Python's `requests` does the same). */
    if (total >= 5 && strncmp(ptr, "HTTP/", 5) == 0) {
        petitio_response_clear_headers(response);
        return total;
    }
    (void)petitio_response_add_header(response, ptr, total);
    return total;
}

static int petitio_map_curl_error(CURLcode code, const petitio_response *response)
{
    if (code == CURLE_OK)
        return PETITIO_OK;
    if (response != NULL && response->body_too_large)
        return PETITIO_BODY_TOO_LARGE;
    switch (code) {
    case CURLE_OPERATION_TIMEDOUT:
        return PETITIO_TIMEOUT;
    case CURLE_TOO_MANY_REDIRECTS:
        return PETITIO_TOO_MANY_REDIRECTS;
    case CURLE_URL_MALFORMAT:
        return PETITIO_INVALID_URL;
    case CURLE_UNSUPPORTED_PROTOCOL:
        return PETITIO_UNSUPPORTED;
    case CURLE_SSL_CONNECT_ERROR:
    case CURLE_PEER_FAILED_VERIFICATION:
    case CURLE_SSL_CERTPROBLEM:
    case CURLE_SSL_CIPHER:
    case CURLE_SSL_CACERT_BADFILE:
    case CURLE_USE_SSL_FAILED:
    case CURLE_SSL_ENGINE_NOTFOUND:
    case CURLE_SSL_ENGINE_SETFAILED:
    case CURLE_SSL_CRL_BADFILE:
    case CURLE_SSL_ISSUER_ERROR:
    case CURLE_SSL_PINNEDPUBKEYNOTMATCH:
    case CURLE_SSL_INVALIDCERTSTATUS:
        return PETITIO_TLS_ERROR;
    case CURLE_COULDNT_RESOLVE_HOST:
    case CURLE_COULDNT_RESOLVE_PROXY:
    case CURLE_COULDNT_CONNECT:
    case CURLE_SEND_ERROR:
    case CURLE_RECV_ERROR:
    case CURLE_PARTIAL_FILE:
        return PETITIO_CONNECTION_FAILED;
    case CURLE_OUT_OF_MEMORY:
        return PETITIO_OUT_OF_MEMORY;
    case CURLE_FILESIZE_EXCEEDED:
        return PETITIO_BODY_TOO_LARGE;
    case CURLE_WRITE_ERROR:
    case CURLE_ABORTED_BY_CALLBACK:
        return response != NULL && response->body_too_large
                   ? PETITIO_BODY_TOO_LARGE
                   : PETITIO_PROTOCOL_ERROR;
    default:
        return PETITIO_PROTOCOL_ERROR;
    }
}

static petitio_response *petitio_response_new(void)
{
    petitio_response *response = (petitio_response *)calloc(1, sizeof(petitio_response));
    return response;
}

static void petitio_response_set_error(petitio_response *response, int code,
                                       const char *message)
{
    response->error = code;
    free(response->error_message);
    response->error_message = petitio_dup_n(message == NULL ? "" : message,
                                            message == NULL ? 0 : (int)strlen(message));
}

/* A body sink that writes to a FILE* and enforces the size cap. */
typedef struct petitio_file_sink {
    FILE *file;
    int64_t written;
    int64_t max_body;
    int too_large;
    int io_error;
} petitio_file_sink;

/* A body sink that forwards every chunk to a PenguScript callback. */
typedef struct petitio_stream_ctx {
    petitio_stream_fn callback;
    void *user;
    int64_t written;
    int64_t max_body;
    int too_large;
    int cancelled;
} petitio_stream_ctx;

static size_t petitio_file_write_cb(char *ptr, size_t size, size_t nmemb,
                                    void *userdata)
{
    petitio_file_sink *sink = (petitio_file_sink *)userdata;
    size_t total = size * nmemb;
    if (sink->too_large || sink->io_error)
        return 0;
    if (sink->max_body > 0
        && sink->written + (int64_t)total > sink->max_body) {
        sink->too_large = 1;
        return 0;
    }
    if (total > 0 && fwrite(ptr, 1, total, sink->file) != total) {
        sink->io_error = 1;
        return 0;
    }
    sink->written += (int64_t)total;
    return total;
}

static size_t petitio_stream_write_cb(char *ptr, size_t size, size_t nmemb,
                                      void *userdata)
{
    petitio_stream_ctx *ctx = (petitio_stream_ctx *)userdata;
    size_t total = size * nmemb;
    PenguString chunk;
    if (ctx->too_large || ctx->cancelled)
        return 0;
    if (ctx->max_body > 0
        && ctx->written + (int64_t)total > ctx->max_body) {
        ctx->too_large = 1;
        return 0;
    }
    /* Borrowed view: valid only during the callback, never owned. */
    chunk.data = ptr;
    chunk.len = (int)total;
    chunk.is_owned = 0;
    if (!ctx->callback(chunk, ctx->user)) {
        ctx->cancelled = 1;
        return 0;
    }
    ctx->written += (int64_t)total;
    return total;
}

/* Applies every option that is common to the four transfer modes. `write_cb`
 * and `write_data` choose the body sink; `*out_mime` receives a multipart body
 * the caller must free after the transfer (NULL when the request has none). */
static CURLcode petitio_apply_options(CURL *curl, petitio_request *request,
                                      petitio_response *response,
                                      curl_write_callback write_cb,
                                      void *write_data,
                                      struct curl_mime **out_mime)
{
    struct curl_mime *mime = NULL;
    CURLcode code;
    int i;

    *out_mime = NULL;
    if ((code = curl_easy_setopt(curl, CURLOPT_URL, request->url)) != CURLE_OK)
        return code;
    curl_easy_setopt(curl, CURLOPT_ERRORBUFFER, request->error_buffer);
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, write_data);
    curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, petitio_header_cb);
    curl_easy_setopt(curl, CURLOPT_HEADERDATA, response);
    /* Only the two protocols `requests` speaks (and the wrapper documents).
     * libcurl would otherwise accept file://, ftp://, gopher:// and friends,
     * turning a user-supplied URL into local file disclosure. */
#if LIBCURL_VERSION_NUM >= 0x075500 /* 7.85.0 */
    curl_easy_setopt(curl, CURLOPT_PROTOCOLS_STR, "http,https");
    curl_easy_setopt(curl, CURLOPT_REDIR_PROTOCOLS_STR, "http,https");
#else
    curl_easy_setopt(curl, CURLOPT_PROTOCOLS,
                     (long)(CURLPROTO_HTTP | CURLPROTO_HTTPS));
    curl_easy_setopt(curl, CURLOPT_REDIR_PROTOCOLS,
                     (long)(CURLPROTO_HTTP | CURLPROTO_HTTPS));
#endif
    /* Accept-Encoding is negotiated and decoded transparently, like `requests`.
     * The response keeps the server's `Content-Encoding` header. */
    curl_easy_setopt(curl, CURLOPT_ACCEPT_ENCODING, "");
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION,
                     request->follow_redirects ? 1L : 0L);
    if (request->follow_redirects)
        curl_easy_setopt(curl, CURLOPT_MAXREDIRS, (long)request->max_redirects);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, request->verify_tls ? 1L : 0L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, request->verify_tls ? 2L : 0L);
    if (request->http_version == 1) {
        curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_2_0);
    } else if (request->http_version == 2) {
        curl_easy_setopt(curl, CURLOPT_HTTP_VERSION,
                         CURL_HTTP_VERSION_2_PRIOR_KNOWLEDGE);
    } else if (request->http_version == 3) {
        curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_0);
    } else {
        curl_easy_setopt(curl, CURLOPT_HTTP_VERSION, CURL_HTTP_VERSION_1_1);
    }
    if (request->timeout_ms > 0)
        curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, (long)request->timeout_ms);
    if (request->connect_timeout_ms > 0)
        curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT_MS,
                         (long)request->connect_timeout_ms);
    if (request->max_body > 0 && write_cb != petitio_write_cb)
        curl_easy_setopt(curl, CURLOPT_MAXFILESIZE_LARGE,
                         (curl_off_t)request->max_body);

    if (request->proxy != NULL) {
        curl_easy_setopt(curl, CURLOPT_PROXY, request->proxy);
        if (request->proxy_credentials != NULL)
            curl_easy_setopt(curl, CURLOPT_PROXYUSERPWD,
                             request->proxy_credentials);
    }
    if (request->username != NULL) {
        long scheme = CURLAUTH_BASIC;
        if (request->auth_mode == 2)
            scheme = CURLAUTH_DIGEST;
        else if (request->auth_mode == 3)
            scheme = CURLAUTH_ANY;
        curl_easy_setopt(curl, CURLOPT_HTTPAUTH, scheme);
        curl_easy_setopt(curl, CURLOPT_USERNAME, request->username);
        curl_easy_setopt(curl, CURLOPT_PASSWORD,
                         request->password != NULL ? request->password : "");
    }

    if (request->part_count > 0) {
        mime = curl_mime_init(curl);
        if (mime == NULL)
            return CURLE_OUT_OF_MEMORY;
        for (i = 0; i < request->part_count; ++i) {
            petitio_part *part = &request->parts[i];
            curl_mimepart *entry = curl_mime_addpart(mime);
            if (entry == NULL) {
                curl_mime_free(mime);
                return CURLE_OUT_OF_MEMORY;
            }
            curl_mime_name(entry, part->name);
            curl_mime_data(entry, part->value != NULL ? part->value : "",
                           (size_t)part->value_len);
            if (part->filename != NULL && part->filename[0] != '\0')
                curl_mime_filename(entry, part->filename);
            if (part->content_type != NULL && part->content_type[0] != '\0')
                curl_mime_type(entry, part->content_type);
        }
        if ((code = curl_easy_setopt(curl, CURLOPT_MIMEPOST, mime)) != CURLE_OK) {
            curl_mime_free(mime);
            return code;
        }
        /* A method other than POST must still be sent as given. */
        if (strcmp(request->method, "POST") != 0) {
            if ((code = curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST,
                                         request->method)) != CURLE_OK) {
                curl_mime_free(mime);
                return code;
            }
        }
    } else {
        if (strcmp(request->method, "GET") == 0) {
            curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
        } else if (strcmp(request->method, "POST") == 0) {
            curl_easy_setopt(curl, CURLOPT_POST, 1L);
        } else if (strcmp(request->method, "HEAD") == 0) {
            curl_easy_setopt(curl, CURLOPT_NOBODY, 1L);
        } else if ((code = curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST,
                                            request->method)) != CURLE_OK) {
            return code;
        }
        if (request->has_body) {
            if ((code = curl_easy_setopt(curl, CURLOPT_POSTFIELDS,
                                         request->body)) != CURLE_OK)
                return code;
            if ((code = curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE_LARGE,
                                         (curl_off_t)request->body_len)) != CURLE_OK)
                return code;
        }
    }

    if (request->headers != NULL
        && (code = curl_easy_setopt(curl, CURLOPT_HTTPHEADER,
                                    request->headers)) != CURLE_OK)
        return code;

    *out_mime = mime;
    return CURLE_OK;
}

/* Copies the transfer outcome into `response`. `written` is the byte count the
 * sink observed; `override_error` wins over libcurl's own classification when a
 * callbacks-only condition (cancellation, a failed write) explains the abort. */
static void petitio_finish_response(petitio_request *request,
                                    petitio_response *response, CURL *curl,
                                    CURLcode code, int override_error,
                                    const char *override_message,
                                    int64_t written)
{
    long status = 0;
    double elapsed = 0.0;
    long redirects = 0;
    long http_version = 0;
    char *effective_url = NULL;

    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
    curl_easy_getinfo(curl, CURLINFO_TOTAL_TIME, &elapsed);
    curl_easy_getinfo(curl, CURLINFO_REDIRECT_COUNT, &redirects);
    curl_easy_getinfo(curl, CURLINFO_HTTP_VERSION, &http_version);
    if (curl_easy_getinfo(curl, CURLINFO_EFFECTIVE_URL, &effective_url) == CURLE_OK
        && effective_url != NULL) {
        response->url_len = (int)strlen(effective_url);
        response->url = petitio_dup_n(effective_url, response->url_len);
        if (response->url == NULL)
            response->url_len = 0;
    }
    response->status = (int)status;
    response->elapsed = elapsed;
    response->redirects = (int)redirects;
    response->bytes_written = written;
    if (http_version == CURL_HTTP_VERSION_1_0) {
        response->http_version = 0;   /* Http10 */
    } else if (http_version == CURL_HTTP_VERSION_2_0
               || http_version == CURL_HTTP_VERSION_2TLS) {
        response->http_version = 2;   /* Http2 */
#ifdef CURL_HTTP_VERSION_3
    } else if (http_version == CURL_HTTP_VERSION_3
               || http_version == CURL_HTTP_VERSION_3ONLY) {
        response->http_version = 4;   /* Http3, reported only */
#endif
    } else {
        response->http_version = 1;   /* Http11 */
    }

    if (code != CURLE_OK) {
        const char *message = override_message != NULL
                                  ? override_message
                                  : (request->error_buffer[0] != '\0'
                                         ? request->error_buffer
                                         : curl_easy_strerror(code));
        int mapped = override_error != 0
                         ? override_error
                         : petitio_map_curl_error(code, response);
        petitio_response_set_error(response, mapped, message);
    }
}

static petitio_response *petitio_perform(petitio_request *request)
{
    CURL *curl;
    CURLcode code;
    struct curl_mime *mime = NULL;
    petitio_response *response;

    petitio_global_init();
    petitio_request_clear_error(request);
    response = petitio_response_new();
    if (response == NULL)
        return NULL;
    response->max_body = request->max_body;

    curl = curl_easy_init();
    if (curl == NULL) {
        petitio_response_set_error(response, PETITIO_OUT_OF_MEMORY,
                                   "curl_easy_init failed");
        return response;
    }
    code = petitio_apply_options(curl, request, response, petitio_write_cb,
                                 response, &mime);
    if (code != CURLE_OK) {
        if (mime != NULL)
            curl_mime_free(mime);
        curl_easy_cleanup(curl);
        petitio_response_set_error(response, PETITIO_PROTOCOL_ERROR,
                                   "libcurl rejected a request option");
        return response;
    }

    code = curl_easy_perform(curl);
    petitio_finish_response(request, response, curl, code, 0, NULL,
                            (int64_t)response->body_len);
    if (mime != NULL)
        curl_mime_free(mime);
    curl_easy_cleanup(curl);
    return response;
}

petitio_response *petitio_request_perform(petitio_request *request)
{
    if (request == NULL)
        return NULL;
    return petitio_perform(request);
}

/* Builds the "<prefix><path>" message for a file error without requiring the
 * path to be NUL-terminated inside the caller's string. */
static void petitio_response_set_path_error(petitio_response *response, int code,
                                            const char *prefix, PenguString path)
{
    int prefix_len = (int)strlen(prefix);
    int path_len = path.data != NULL && path.len > 0 ? path.len : 0;
    char *message = (char *)malloc((size_t)prefix_len + (size_t)path_len + 1);
    if (message == NULL) {
        petitio_response_set_error(response, code, prefix);
        return;
    }
    memcpy(message, prefix, (size_t)prefix_len);
    if (path_len > 0)
        memcpy(message + prefix_len, path.data, (size_t)path_len);
    message[prefix_len + path_len] = '\0';
    petitio_response_set_error(response, code, message);
    free(message);
}

petitio_response *petitio_request_perform_to_file(petitio_request *request,
                                                  PenguString path)
{
    CURL *curl;
    CURLcode code;
    struct curl_mime *mime = NULL;
    petitio_response *response;
    petitio_file_sink sink;
    char *path_copy;

    if (request == NULL)
        return NULL;
    petitio_global_init();
    petitio_request_clear_error(request);
    response = petitio_response_new();
    if (response == NULL)
        return NULL;
    response->max_body = request->max_body;

    path_copy = petitio_dup_pengu(path);
    if (path_copy == NULL) {
        petitio_response_set_error(response, PETITIO_OUT_OF_MEMORY,
                                   "out of memory");
        return response;
    }
    memset(&sink, 0, sizeof sink);
    sink.max_body = request->max_body;
    sink.file = fopen(path_copy, "wb");
    if (sink.file == NULL) {
        petitio_response_set_path_error(response, PETITIO_IO_ERROR,
                                        "cannot open output file: ", path);
        free(path_copy);
        return response;
    }
    free(path_copy);

    curl = curl_easy_init();
    if (curl == NULL) {
        fclose(sink.file);
        petitio_response_set_error(response, PETITIO_OUT_OF_MEMORY,
                                   "curl_easy_init failed");
        return response;
    }
    code = petitio_apply_options(curl, request, response, petitio_file_write_cb,
                                 &sink, &mime);
    if (code != CURLE_OK) {
        if (mime != NULL)
            curl_mime_free(mime);
        curl_easy_cleanup(curl);
        fclose(sink.file);
        petitio_response_set_error(response, PETITIO_PROTOCOL_ERROR,
                                   "libcurl rejected a request option");
        return response;
    }

    code = curl_easy_perform(curl);
    fclose(sink.file);
    if (sink.too_large) {
        petitio_finish_response(request, response, curl, code,
                                PETITIO_BODY_TOO_LARGE,
                                "response body exceeds the configured limit",
                                sink.written);
    } else if (sink.io_error) {
        petitio_finish_response(request, response, curl, code,
                                PETITIO_IO_ERROR,
                                "cannot write output file", sink.written);
    } else {
        petitio_finish_response(request, response, curl, code, 0, NULL,
                                sink.written);
    }
    if (mime != NULL)
        curl_mime_free(mime);
    curl_easy_cleanup(curl);
    return response;
}

petitio_response *petitio_request_perform_stream(petitio_request *request,
                                                 petitio_stream_fn callback,
                                                 void *user)
{
    CURL *curl;
    CURLcode code;
    struct curl_mime *mime = NULL;
    petitio_response *response;
    petitio_stream_ctx ctx;

    if (request == NULL || callback == NULL)
        return NULL;
    petitio_global_init();
    petitio_request_clear_error(request);
    response = petitio_response_new();
    if (response == NULL)
        return NULL;
    response->max_body = request->max_body;

    memset(&ctx, 0, sizeof ctx);
    ctx.callback = callback;
    ctx.user = user;
    ctx.max_body = request->max_body;

    curl = curl_easy_init();
    if (curl == NULL) {
        petitio_response_set_error(response, PETITIO_OUT_OF_MEMORY,
                                   "curl_easy_init failed");
        return response;
    }
    code = petitio_apply_options(curl, request, response,
                                 petitio_stream_write_cb, &ctx, &mime);
    if (code != CURLE_OK) {
        if (mime != NULL)
            curl_mime_free(mime);
        curl_easy_cleanup(curl);
        petitio_response_set_error(response, PETITIO_PROTOCOL_ERROR,
                                   "libcurl rejected a request option");
        return response;
    }

    code = curl_easy_perform(curl);
    if (ctx.too_large) {
        petitio_finish_response(request, response, curl, code,
                                PETITIO_BODY_TOO_LARGE,
                                "response body exceeds the configured limit",
                                ctx.written);
    } else if (ctx.cancelled) {
        petitio_finish_response(request, response, curl, code,
                                PETITIO_CANCELLED,
                                "transfer cancelled by callback", ctx.written);
    } else {
        petitio_finish_response(request, response, curl, code, 0, NULL,
                                ctx.written);
    }
    if (mime != NULL)
        curl_mime_free(mime);
    curl_easy_cleanup(curl);
    return response;
}

/* -------------------------------------------------------------------------
 * Response accessors
 * ------------------------------------------------------------------------- */

int petitio_response_error(const petitio_response *response)
{
    return response == NULL ? PETITIO_OUT_OF_MEMORY : response->error;
}

PenguString petitio_response_error_message(const petitio_response *response)
{
    if (response == NULL || response->error_message == NULL)
        return petitio_pengu_empty();
    return petitio_pengu_dup(response->error_message,
                             (int)strlen(response->error_message));
}

int petitio_response_status(const petitio_response *response)
{
    return response == NULL ? 0 : response->status;
}

PenguString petitio_response_body(const petitio_response *response)
{
    if (response == NULL)
        return petitio_pengu_empty();
    return petitio_pengu_dup(response->body, response->body_len);
}

PenguString petitio_response_url(const petitio_response *response)
{
    if (response == NULL)
        return petitio_pengu_empty();
    return petitio_pengu_dup(response->url, response->url_len);
}

double petitio_response_elapsed(const petitio_response *response)
{
    return response == NULL ? 0.0 : response->elapsed;
}

int petitio_response_redirect_count(const petitio_response *response)
{
    return response == NULL ? 0 : response->redirects;
}

int petitio_response_http_version(const petitio_response *response)
{
    return response == NULL ? 1 : response->http_version;
}

int64_t petitio_response_bytes_written(const petitio_response *response)
{
    return response == NULL ? 0 : response->bytes_written;
}

int petitio_response_header_count(const petitio_response *response)
{
    return response == NULL ? 0 : response->header_count;
}

PenguString petitio_response_header_name(const petitio_response *response,
                                         int index)
{
    if (response == NULL || index < 0 || index >= response->header_count)
        return petitio_pengu_empty();
    return petitio_pengu_dup(response->headers[index].name,
                             response->headers[index].name_len);
}

PenguString petitio_response_header_value(const petitio_response *response,
                                          int index)
{
    if (response == NULL || index < 0 || index >= response->header_count)
        return petitio_pengu_empty();
    return petitio_pengu_dup(response->headers[index].value,
                             response->headers[index].value_len);
}

void petitio_response_free(petitio_response *response)
{
    if (response == NULL)
        return;
    petitio_response_clear_headers(response);
    free(response->headers);
    free(response->body);
    free(response->url);
    free(response->error_message);
    free(response);
}

int64_t petitio_parse_http_date(PenguString text)
{
    char *copy;
    time_t when;
    if (text.data == NULL || text.len <= 0)
        return -1;
    copy = petitio_dup_pengu(text);
    if (copy == NULL)
        return -1;
    /* curl_getdate accepts every date format RFC 7231 allows (IMF-fixdate,
     * obsolete RFC 850 and asctime) and returns -1 when it cannot parse. */
    when = curl_getdate(copy, NULL);
    free(copy);
    return (int64_t)when;
}

PenguString petitio_version(void)
{
    curl_version_info_data *info = curl_version_info(CURLVERSION_NOW);
    const char *text = (info != NULL && info->version != NULL)
                           ? info->version
                           : "libcurl (unknown)";
    return petitio_pengu_dup(text, (int)strlen(text));
}
