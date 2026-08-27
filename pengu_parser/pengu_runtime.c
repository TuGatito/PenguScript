/*
 * pengu_runtime.c - PenguScript C Runtime with External Library Integration
 *
 * Implements real backends for:
 *   - filum (concurrency: Win32 threads / pthreads, channels, mutex, atomic)
 *   - regulus (regex: PCRE2 10.47)
 *   - parchment (XML/HTML: libxml2 2.9.0)
 */

#include "pengu_runtime.h"

#define PCRE2_CODE_UNIT_WIDTH 8
#define PCRE2_STATIC
#include <pcre2.h>

#define LIBXML_STATIC
#include <libxml/parser.h>
#include <libxml/HTMLparser.h>
#include <libxml/tree.h>
#include <libxml/xpath.h>
#include <libxml/xpathInternals.h>
#include <libxml/xmlsave.h>

#include <zlib.h>
#include <mbedtls/private/md5.h>
#include <mbedtls/private/sha1.h>
#include <mbedtls/private/sha256.h>
#include <mbedtls/private/sha512.h>

#define CURL_STATICLIB
#include <curl/curl.h>

#include <microhttpd.h>

#if PENGU_WINDOWS
#include <process.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <pthread.h>
#include <stdatomic.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#endif

/* =========================================================================
 * 1. Filum (Concurrency Real Implementation)
 * ========================================================================= */

typedef struct {
    void (*fn)(void);
} PenguThreadArg;

#if PENGU_WINDOWS
static unsigned __stdcall pengu_win32_thread_runner(void* arg) {
    PenguThreadArg* targ = (PenguThreadArg*)arg;
    if (targ && targ->fn) {
        targ->fn();
    }
    free(targ);
    return 0;
}
#else
static void* pengu_posix_thread_runner(void* arg) {
    PenguThreadArg* targ = (PenguThreadArg*)arg;
    if (targ && targ->fn) {
        targ->fn();
    }
    free(targ);
    return NULL;
}
#endif

void pengu_c_filum_sleep(int ms) {
    pengu_c_sleep_ms(ms);
}

int pengu_c_filum_num_cpu(void) {
#if PENGU_WINDOWS
    SYSTEM_INFO sysinfo;
    GetSystemInfo(&sysinfo);
    return (int)sysinfo.dwNumberOfProcessors;
#else
    return 4;
#endif
}

int pengu_c_filum_goroutine_id(void) {
#if PENGU_WINDOWS
    return (int)GetCurrentThreadId();
#else
    return (int)pthread_self();
#endif
}

void pengu_c_filum_go(void* f) {
    if (!f) return;
    PenguThreadArg* arg = (PenguThreadArg*)malloc(sizeof(PenguThreadArg));
    if (!arg) return;
    arg->fn = (void (*)(void))f;

#if PENGU_WINDOWS
    uintptr_t th = _beginthreadex(NULL, 0, pengu_win32_thread_runner, arg, 0, NULL);
    if (th) CloseHandle((HANDLE)th);
#else
    pthread_t th;
    if (pthread_create(&th, NULL, pengu_posix_thread_runner, arg) == 0) {
        pthread_detach(th);
    }
#endif
}

/* Mutex */
typedef struct {
#if PENGU_WINDOWS
    CRITICAL_SECTION cs;
#else
    pthread_mutex_t mtx;
#endif
} PenguNativeMutex;

void* pengu_c_filum_mutex_new(void) {
    PenguNativeMutex* m = (PenguNativeMutex*)malloc(sizeof(PenguNativeMutex));
    if (!m) return NULL;
#if PENGU_WINDOWS
    InitializeCriticalSection(&m->cs);
#else
    pthread_mutex_init(&m->mtx, NULL);
#endif
    return m;
}

void pengu_c_filum_mutex_lock(void* m) {
    if (!m) return;
    PenguNativeMutex* nm = (PenguNativeMutex*)m;
#if PENGU_WINDOWS
    EnterCriticalSection(&nm->cs);
#else
    pthread_mutex_lock(&nm->mtx);
#endif
}

void pengu_c_filum_mutex_unlock(void* m) {
    if (!m) return;
    PenguNativeMutex* nm = (PenguNativeMutex*)m;
#if PENGU_WINDOWS
    LeaveCriticalSection(&nm->cs);
#else
    pthread_mutex_unlock(&nm->mtx);
#endif
}

bool pengu_c_filum_mutex_try_lock(void* m) {
    if (!m) return false;
    PenguNativeMutex* nm = (PenguNativeMutex*)m;
#if PENGU_WINDOWS
    return TryEnterCriticalSection(&nm->cs) != 0;
#else
    return pthread_mutex_trylock(&nm->mtx) == 0;
#endif
}

/* WaitGroup */
typedef struct {
    int count;
#if PENGU_WINDOWS
    CRITICAL_SECTION cs;
    CONDITION_VARIABLE cv;
#else
    pthread_mutex_t mtx;
    pthread_cond_t cv;
#endif
} PenguNativeWaitGroup;

void* pengu_c_filum_wait_group_new(void) {
    PenguNativeWaitGroup* wg = (PenguNativeWaitGroup*)malloc(sizeof(PenguNativeWaitGroup));
    if (!wg) return NULL;
    wg->count = 0;
#if PENGU_WINDOWS
    InitializeCriticalSection(&wg->cs);
    InitializeConditionVariable(&wg->cv);
#else
    pthread_mutex_init(&wg->mtx, NULL);
    pthread_cond_init(&wg->cv, NULL);
#endif
    return wg;
}

void pengu_c_filum_wait_group_add(void* wg, int delta) {
    if (!wg) return;
    PenguNativeWaitGroup* nwg = (PenguNativeWaitGroup*)wg;
#if PENGU_WINDOWS
    EnterCriticalSection(&nwg->cs);
    nwg->count += delta;
    if (nwg->count <= 0) {
        nwg->count = 0;
        WakeAllConditionVariable(&nwg->cv);
    }
    LeaveCriticalSection(&nwg->cs);
#else
    pthread_mutex_lock(&nwg->mtx);
    nwg->count += delta;
    if (nwg->count <= 0) {
        nwg->count = 0;
        pthread_cond_broadcast(&nwg->cv);
    }
    pthread_mutex_unlock(&nwg->mtx);
#endif
}

void pengu_c_filum_wait_group_done(void* wg) {
    pengu_c_filum_wait_group_add(wg, -1);
}

void pengu_c_filum_wait_group_wait(void* wg) {
    if (!wg) return;
    PenguNativeWaitGroup* nwg = (PenguNativeWaitGroup*)wg;
#if PENGU_WINDOWS
    EnterCriticalSection(&nwg->cs);
    while (nwg->count > 0) {
        SleepConditionVariableCS(&nwg->cv, &nwg->cs, INFINITE);
    }
    LeaveCriticalSection(&nwg->cs);
#else
    pthread_mutex_lock(&nwg->mtx);
    while (nwg->count > 0) {
        pthread_cond_wait(&nwg->cv, &nwg->mtx);
    }
    pthread_mutex_unlock(&nwg->mtx);
#endif
}

/* Once */
typedef struct {
    volatile long done;
#if PENGU_WINDOWS
    CRITICAL_SECTION cs;
#else
    pthread_mutex_t mtx;
#endif
} PenguNativeOnce;

void* pengu_c_filum_once_new(void) {
    PenguNativeOnce* o = (PenguNativeOnce*)malloc(sizeof(PenguNativeOnce));
    if (!o) return NULL;
    o->done = 0;
#if PENGU_WINDOWS
    InitializeCriticalSection(&o->cs);
#else
    pthread_mutex_init(&o->mtx, NULL);
#endif
    return o;
}

void pengu_c_filum_once_do(void* o, void* f) {
    if (!o || !f) return;
    PenguNativeOnce* no = (PenguNativeOnce*)o;
    if (no->done) return;
    void (*fn)(void) = (void (*)(void))f;
#if PENGU_WINDOWS
    EnterCriticalSection(&no->cs);
    if (!no->done) {
        fn();
        no->done = 1;
    }
    LeaveCriticalSection(&no->cs);
#else
    pthread_mutex_lock(&no->mtx);
    if (!no->done) {
        fn();
        no->done = 1;
    }
    pthread_mutex_unlock(&no->mtx);
#endif
}

/* Cond */
typedef struct {
#if PENGU_WINDOWS
    CONDITION_VARIABLE cv;
#else
    pthread_cond_t cv;
#endif
} PenguNativeCond;

void* pengu_c_filum_cond_new(void) {
    PenguNativeCond* c = (PenguNativeCond*)malloc(sizeof(PenguNativeCond));
    if (!c) return NULL;
#if PENGU_WINDOWS
    InitializeConditionVariable(&c->cv);
#else
    pthread_cond_init(&c->cv, NULL);
#endif
    return c;
}

void pengu_c_filum_cond_wait(void* c, void* m) {
    if (!c || !m) return;
    PenguNativeCond* nc = (PenguNativeCond*)c;
    PenguNativeMutex* nm = (PenguNativeMutex*)m;
#if PENGU_WINDOWS
    SleepConditionVariableCS(&nc->cv, &nm->cs, INFINITE);
#else
    pthread_cond_wait(&nc->cv, &nm->mtx);
#endif
}

void pengu_c_filum_cond_signal(void* c) {
    if (!c) return;
    PenguNativeCond* nc = (PenguNativeCond*)c;
#if PENGU_WINDOWS
    WakeConditionVariable(&nc->cv);
#else
    pthread_cond_signal(&nc->cv);
#endif
}

void pengu_c_filum_cond_broadcast(void* c) {
    if (!c) return;
    PenguNativeCond* nc = (PenguNativeCond*)c;
#if PENGU_WINDOWS
    WakeAllConditionVariable(&nc->cv);
#else
    pthread_cond_broadcast(&nc->cv);
#endif
}

/* AtomicInt */
typedef struct {
    volatile long val;
} PenguNativeAtomicInt;

void* pengu_c_filum_atomic_int_new(int initial) {
    PenguNativeAtomicInt* a = (PenguNativeAtomicInt*)malloc(sizeof(PenguNativeAtomicInt));
    if (!a) return NULL;
    a->val = initial;
    return a;
}

int pengu_c_filum_atomic_int_load(void* a) {
    if (!a) return 0;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (int)InterlockedCompareExchange(&na->val, 0, 0);
#else
    return (int)atomic_load((atomic_long*)&na->val);
#endif
}

void pengu_c_filum_atomic_int_store(void* a, int val) {
    if (!a) return;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    InterlockedExchange(&na->val, val);
#else
    atomic_store((atomic_long*)&na->val, val);
#endif
}

int pengu_c_filum_atomic_int_add(void* a, int delta) {
    if (!a) return 0;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (int)(InterlockedExchangeAdd(&na->val, delta));
#else
    return (int)(atomic_fetch_add((atomic_long*)&na->val, delta));
#endif
}

int pengu_c_filum_atomic_int_swap(void* a, int new_val) {
    if (!a) return 0;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (int)InterlockedExchange(&na->val, new_val);
#else
    return (int)atomic_exchange((atomic_long*)&na->val, new_val);
#endif
}

bool pengu_c_filum_atomic_int_compare_swap(void* a, int old_val, int new_val) {
    if (!a) return false;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (InterlockedCompareExchange(&na->val, new_val, old_val) == old_val);
#else
    long expected = old_val;
    return atomic_compare_exchange_strong((atomic_long*)&na->val, &expected, (long)new_val);
#endif
}

/* Channels */
typedef struct {
    uint8_t* buffer;
    int elem_size;
    int cap;
    int head;
    int tail;
    int size;
    bool closed;
#if PENGU_WINDOWS
    CRITICAL_SECTION cs;
    CONDITION_VARIABLE not_empty;
    CONDITION_VARIABLE not_full;
#else
    pthread_mutex_t mtx;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
#endif
} PenguNativeChan;

void* pengu_c_filum_chan_new(int elem_size, int cap) {
    if (cap < 1) cap = 1;
    PenguNativeChan* ch = (PenguNativeChan*)malloc(sizeof(PenguNativeChan));
    if (!ch) return NULL;
    ch->elem_size = elem_size > 0 ? elem_size : (int)sizeof(void*);
    ch->cap = cap;
    ch->head = 0;
    ch->tail = 0;
    ch->size = 0;
    ch->closed = false;
    ch->buffer = (uint8_t*)malloc((size_t)ch->elem_size * (size_t)cap);
#if PENGU_WINDOWS
    InitializeCriticalSection(&ch->cs);
    InitializeConditionVariable(&ch->not_empty);
    InitializeConditionVariable(&ch->not_full);
#else
    pthread_mutex_init(&ch->mtx, NULL);
    pthread_cond_init(&ch->not_empty, NULL);
    pthread_cond_init(&ch->not_full, NULL);
#endif
    return ch;
}

bool pengu_c_filum_chan_send(void* c, void* value) {
    if (!c || !value) return false;
    PenguNativeChan* ch = (PenguNativeChan*)c;
#if PENGU_WINDOWS
    EnterCriticalSection(&ch->cs);
    while (ch->size == ch->cap && !ch->closed) {
        SleepConditionVariableCS(&ch->not_full, &ch->cs, INFINITE);
    }
    if (ch->closed) {
        LeaveCriticalSection(&ch->cs);
        return false;
    }
    memcpy(ch->buffer + (ch->tail * ch->elem_size), value, (size_t)ch->elem_size);
    ch->tail = (ch->tail + 1) % ch->cap;
    ch->size++;
    WakeConditionVariable(&ch->not_empty);
    LeaveCriticalSection(&ch->cs);
    return true;
#else
    pthread_mutex_lock(&ch->mtx);
    while (ch->size == ch->cap && !ch->closed) {
        pthread_cond_wait(&ch->not_full, &ch->mtx);
    }
    if (ch->closed) {
        pthread_mutex_unlock(&ch->mtx);
        return false;
    }
    memcpy(ch->buffer + (ch->tail * ch->elem_size), value, (size_t)ch->elem_size);
    ch->tail = (ch->tail + 1) % ch->cap;
    ch->size++;
    pthread_cond_signal(&ch->not_empty);
    pthread_mutex_unlock(&ch->mtx);
    return true;
#endif
}

bool pengu_c_filum_chan_recv(void* c, void* out) {
    if (!c || !out) return false;
    PenguNativeChan* ch = (PenguNativeChan*)c;
#if PENGU_WINDOWS
    EnterCriticalSection(&ch->cs);
    while (ch->size == 0 && !ch->closed) {
        SleepConditionVariableCS(&ch->not_empty, &ch->cs, INFINITE);
    }
    if (ch->size == 0 && ch->closed) {
        LeaveCriticalSection(&ch->cs);
        return false;
    }
    memcpy(out, ch->buffer + (ch->head * ch->elem_size), (size_t)ch->elem_size);
    ch->head = (ch->head + 1) % ch->cap;
    ch->size--;
    WakeConditionVariable(&ch->not_full);
    LeaveCriticalSection(&ch->cs);
    return true;
#else
    pthread_mutex_lock(&ch->mtx);
    while (ch->size == 0 && !ch->closed) {
        pthread_cond_wait(&ch->not_empty, &ch->mtx);
    }
    if (ch->size == 0 && ch->closed) {
        pthread_mutex_unlock(&ch->mtx);
        return false;
    }
    memcpy(out, ch->buffer + (ch->head * ch->elem_size), (size_t)ch->elem_size);
    ch->head = (ch->head + 1) % ch->cap;
    ch->size--;
    pthread_cond_signal(&ch->not_full);
    pthread_mutex_unlock(&ch->mtx);
    return true;
#endif
}

void pengu_c_filum_chan_close(void* c) {
    if (!c) return;
    PenguNativeChan* ch = (PenguNativeChan*)c;
#if PENGU_WINDOWS
    EnterCriticalSection(&ch->cs);
    ch->closed = true;
    WakeAllConditionVariable(&ch->not_empty);
    WakeAllConditionVariable(&ch->not_full);
    LeaveCriticalSection(&ch->cs);
#else
    pthread_mutex_lock(&ch->mtx);
    ch->closed = true;
    pthread_cond_broadcast(&ch->not_empty);
    pthread_cond_broadcast(&ch->not_full);
    pthread_mutex_unlock(&ch->mtx);
#endif
}

int pengu_c_filum_chan_len(void* c) {
    if (!c) return 0;
    PenguNativeChan* ch = (PenguNativeChan*)c;
#if PENGU_WINDOWS
    EnterCriticalSection(&ch->cs);
    int len = ch->size;
    LeaveCriticalSection(&ch->cs);
    return len;
#else
    pthread_mutex_lock(&ch->mtx);
    int len = ch->size;
    pthread_mutex_unlock(&ch->mtx);
    return len;
#endif
}

int pengu_c_filum_chan_cap(void* c) {
    if (!c) return 0;
    PenguNativeChan* ch = (PenguNativeChan*)c;
    return ch->cap;
}

/* =========================================================================
 * 2. Regulus (PCRE2 Real Implementation)
 * ========================================================================= */

static inline pcre2_code* pengu_get_pcre2_code(void* regex) {
    if (!regex) return NULL;
    PenguRegulusRegex* re = (PenguRegulusRegex*)regex;
    return (pcre2_code*)re->_ptr;
}

static uint32_t pengu_regulus_parse_flags(PenguString flags) {
    uint32_t options = 0;
    if (!flags.data) return options;
    for (int i = 0; i < flags.len; ++i) {
        char f = flags.data[i];
        if (f == 'i' || f == 'I') options |= PCRE2_CASELESS;
        else if (f == 'm' || f == 'M') options |= PCRE2_MULTILINE;
        else if (f == 's' || f == 'S') options |= PCRE2_DOTALL;
        else if (f == 'u' || f == 'U') options |= PCRE2_UTF;
        else if (f == 'x' || f == 'X') options |= PCRE2_EXTENDED;
    }
    return options;
}

PenguMaybe pengu_c_regulus_compile(PenguString pattern, PenguString flags) {
    if (!pattern.data) return pengu_maybe_none();
    uint32_t options = pengu_regulus_parse_flags(flags);
    int errorcode = 0;
    PCRE2_SIZE erroroffset = 0;
    pcre2_code* code = pcre2_compile(
        (PCRE2_SPTR8)pattern.data,
        (PCRE2_SIZE)pattern.len,
        options,
        &errorcode,
        &erroroffset,
        NULL
    );
    if (!code) return pengu_maybe_none();

    PenguRegulusRegex* re = (PenguRegulusRegex*)malloc(sizeof(PenguRegulusRegex));
    if (!re) {
        pcre2_code_free(code);
        return pengu_maybe_none();
    }
    re->pattern = pattern;
    re->flags = flags;
    re->_ptr = code;
    return pengu_maybe_some(re);
}

PenguMaybe pengu_c_regulus_search(void* regex, PenguString text) {
    pcre2_code* code = pengu_get_pcre2_code(regex);
    if (!code || !text.data) return pengu_maybe_none();

    pcre2_match_data* match_data = pcre2_match_data_create_from_pattern(code, NULL);
    if (!match_data) return pengu_maybe_none();

    int rc = pcre2_match(
        code,
        (PCRE2_SPTR8)text.data,
        (PCRE2_SIZE)text.len,
        0,
        0,
        match_data,
        NULL
    );

    if (rc < 0) {
        pcre2_match_data_free(match_data);
        return pengu_maybe_none();
    }

    PCRE2_SIZE* ovector = pcre2_get_ovector_pointer(match_data);
    int start = (int)ovector[0];
    int end = (int)ovector[1];
    int match_len = end - start;

    char* match_buf = (char*)malloc((size_t)match_len + 1);
    if (match_buf) {
        memcpy(match_buf, text.data + start, (size_t)match_len);
        match_buf[match_len] = '\0';
    }

    pcre2_match_data_free(match_data);

    PenguRegulusMatch* m = (PenguRegulusMatch*)malloc(sizeof(PenguRegulusMatch));
    if (!m) { free(match_buf); return pengu_maybe_none(); }
    m->start = start;
    m->end = end;
    m->matched = (PenguString){ match_buf, match_len };
    return pengu_maybe_some(m);
}

PenguMaybe pengu_c_regulus_match(void* regex, PenguString text) {
    pcre2_code* code = pengu_get_pcre2_code(regex);
    if (!code || !text.data) return pengu_maybe_none();

    pcre2_match_data* match_data = pcre2_match_data_create_from_pattern(code, NULL);
    if (!match_data) return pengu_maybe_none();

    int rc = pcre2_match(
        code,
        (PCRE2_SPTR8)text.data,
        (PCRE2_SIZE)text.len,
        0,
        PCRE2_ANCHORED,
        match_data,
        NULL
    );

    if (rc < 0) {
        pcre2_match_data_free(match_data);
        return pengu_maybe_none();
    }

    PCRE2_SIZE* ovector = pcre2_get_ovector_pointer(match_data);
    int start = (int)ovector[0];
    int end = (int)ovector[1];
    int match_len = end - start;

    char* match_buf = (char*)malloc((size_t)match_len + 1);
    if (match_buf) {
        memcpy(match_buf, text.data + start, (size_t)match_len);
        match_buf[match_len] = '\0';
    }

    pcre2_match_data_free(match_data);

    PenguRegulusMatch* m = (PenguRegulusMatch*)malloc(sizeof(PenguRegulusMatch));
    if (!m) { free(match_buf); return pengu_maybe_none(); }
    m->start = start;
    m->end = end;
    m->matched = (PenguString){ match_buf, match_len };
    return pengu_maybe_some(m);
}

PenguList pengu_c_regulus_find_all(void* regex, PenguString text) {
    PenguList list = pengu_list_new(sizeof(PenguRegulusMatch), 4);
    pcre2_code* code = pengu_get_pcre2_code(regex);
    if (!code || !text.data) return list;

    pcre2_match_data* match_data = pcre2_match_data_create_from_pattern(code, NULL);
    if (!match_data) return list;

    PCRE2_SIZE start_offset = 0;
    while (start_offset < (PCRE2_SIZE)text.len) {
        int rc = pcre2_match(
            code,
            (PCRE2_SPTR8)text.data,
            (PCRE2_SIZE)text.len,
            start_offset,
            0,
            match_data,
            NULL
        );
        if (rc < 0) break;

        PCRE2_SIZE* ovector = pcre2_get_ovector_pointer(match_data);
        int start = (int)ovector[0];
        int end = (int)ovector[1];
        int match_len = end - start;

        char* match_buf = (char*)malloc((size_t)match_len + 1);
        if (match_buf) {
            memcpy(match_buf, text.data + start, (size_t)match_len);
            match_buf[match_len] = '\0';
        }

        PenguRegulusMatch m;
        m.start = start;
        m.end = end;
        m.matched = (PenguString){ match_buf, match_len };
        pengu_list_push(&list, &m);

        start_offset = (ovector[1] > start_offset) ? ovector[1] : (start_offset + 1);
    }

    pcre2_match_data_free(match_data);
    return list;
}

PenguString pengu_c_regulus_replace(void* regex, PenguString text, PenguString replacement) {
    pcre2_code* code = pengu_get_pcre2_code(regex);
    if (!code || !text.data) return text;

    PCRE2_SIZE out_len = (PCRE2_SIZE)(text.len * 2 + replacement.len * 2 + 1024);
    PCRE2_UCHAR* out_buf = (PCRE2_UCHAR*)malloc(out_len);
    if (!out_buf) return text;

    int rc = pcre2_substitute(
        code,
        (PCRE2_SPTR8)text.data,
        (PCRE2_SIZE)text.len,
        0,
        PCRE2_SUBSTITUTE_GLOBAL,
        NULL,
        NULL,
        (PCRE2_SPTR8)(replacement.data ? replacement.data : ""),
        (PCRE2_SIZE)replacement.len,
        out_buf,
        &out_len
    );

    if (rc < 0) {
        free(out_buf);
        return text;
    }

    return (PenguString){ (char*)out_buf, (int)out_len };
}

PenguList pengu_c_regulus_split(void* regex, PenguString text, int limit) {
    PenguList list = pengu_list_new(sizeof(PenguString), 4);
    pcre2_code* code = pengu_get_pcre2_code(regex);
    if (!code || !text.data) {
        pengu_list_push(&list, &text);
        return list;
    }

    pcre2_match_data* match_data = pcre2_match_data_create_from_pattern(code, NULL);
    if (!match_data) {
        pengu_list_push(&list, &text);
        return list;
    }

    PCRE2_SIZE start_offset = 0;
    int last_end = 0;
    int splits = 0;

    while (start_offset < (PCRE2_SIZE)text.len && (limit <= 0 || splits < limit - 1)) {
        int rc = pcre2_match(
            code,
            (PCRE2_SPTR8)text.data,
            (PCRE2_SIZE)text.len,
            start_offset,
            0,
            match_data,
            NULL
        );
        if (rc < 0) break;

        PCRE2_SIZE* ovector = pcre2_get_ovector_pointer(match_data);
        int match_start = (int)ovector[0];
        int part_len = match_start - last_end;

        char* part = (char*)malloc((size_t)part_len + 1);
        if (part) {
            memcpy(part, text.data + last_end, (size_t)part_len);
            part[part_len] = '\0';
            PenguString s = { part, part_len };
            pengu_list_push(&list, &s);
        }

        last_end = (int)ovector[1];
        start_offset = (ovector[1] > start_offset) ? ovector[1] : (start_offset + 1);
        splits++;
    }

    pcre2_match_data_free(match_data);

    int remain_len = text.len - last_end;
    char* remain = (char*)malloc((size_t)remain_len + 1);
    if (remain) {
        memcpy(remain, text.data + last_end, (size_t)remain_len);
        remain[remain_len] = '\0';
        PenguString s = { remain, remain_len };
        pengu_list_push(&list, &s);
    }

    return list;
}

/* =========================================================================
 * 3. Parchment (libxml2 Real Implementation)
 * ========================================================================= */

PenguMaybe pengu_c_parchment_parse_xml(PenguString data) {
    if (!data.data || data.len == 0) return pengu_maybe_none();
    xmlDocPtr doc = xmlReadMemory(data.data, data.len, "noname.xml", NULL, XML_PARSE_NOBLANKS | XML_PARSE_NONET);
    if (!doc) return pengu_maybe_none();

    xmlNodePtr root = xmlDocGetRootElement(doc);
    if (!root) {
        xmlFreeDoc(doc);
        return pengu_maybe_none();
    }

    PenguParchmentDocument* pdoc = (PenguParchmentDocument*)malloc(sizeof(PenguParchmentDocument));
    if (!pdoc) {
        xmlFreeDoc(doc);
        return pengu_maybe_none();
    }

    pdoc->root.tag = root->name ? pengu_string_new((const char*)root->name) : pengu_string_new("");
    xmlChar* text_content = xmlNodeGetContent(root);
    pdoc->root.text = text_content ? pengu_string_new((const char*)text_content) : pengu_string_new("");
    if (text_content) xmlFree(text_content);
    pdoc->root._ptr = root;

    pdoc->version = doc->version ? pengu_string_new((const char*)doc->version) : pengu_string_new("1.0");
    pdoc->encoding = doc->encoding ? pengu_string_new((const char*)doc->encoding) : pengu_string_new("UTF-8");

    return pengu_maybe_some(pdoc);
}

PenguMaybe pengu_c_parchment_parse_html(PenguString data) {
    if (!data.data || data.len == 0) return pengu_maybe_none();
    htmlDocPtr doc = htmlReadMemory(data.data, data.len, "noname.html", NULL, HTML_PARSE_NOBLANKS | HTML_PARSE_NOWARNING | HTML_PARSE_NOERROR);
    if (!doc) return pengu_maybe_none();

    xmlNodePtr root = xmlDocGetRootElement(doc);
    if (!root) {
        xmlFreeDoc(doc);
        return pengu_maybe_none();
    }

    PenguParchmentDocument* pdoc = (PenguParchmentDocument*)malloc(sizeof(PenguParchmentDocument));
    if (!pdoc) {
        xmlFreeDoc(doc);
        return pengu_maybe_none();
    }

    pdoc->root.tag = root->name ? pengu_string_new((const char*)root->name) : pengu_string_new("");
    xmlChar* text_content = xmlNodeGetContent(root);
    pdoc->root.text = text_content ? pengu_string_new((const char*)text_content) : pengu_string_new("");
    if (text_content) xmlFree(text_content);
    pdoc->root._ptr = root;

    pdoc->version = pengu_string_new("HTML");
    pdoc->encoding = pengu_string_new("UTF-8");

    return pengu_maybe_some(pdoc);
}

PenguMaybe pengu_c_parchment_to_string(void* node, bool pretty) {
    if (!node) return pengu_maybe_none();
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (!xnode) {
        char buf[4096];
        snprintf(buf, sizeof(buf), "<%.*s>%.*s</%.*s>", pn->tag.len, pn->tag.data, pn->text.len, pn->text.data, pn->tag.len, pn->tag.data);
        PenguString* res = (PenguString*)malloc(sizeof(PenguString));
        if (!res) return pengu_maybe_none();
        *res = pengu_string_new(buf);
        return pengu_maybe_some(res);
    }

    xmlBufferPtr buf = xmlBufferCreate();
    if (!buf) return pengu_maybe_none();

    xmlSaveCtxtPtr saveCtx = xmlSaveToBuffer(buf, "UTF-8", pretty ? XML_SAVE_FORMAT : 0);
    if (saveCtx) {
        xmlSaveTree(saveCtx, xnode);
        xmlSaveClose(saveCtx);
    }

    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) {
        xmlBufferFree(buf);
        return pengu_maybe_none();
    }

    *res = pengu_string_new((const char*)xmlBufferContent(buf));
    xmlBufferFree(buf);
    return pengu_maybe_some(res);
}

PenguMaybe pengu_c_parchment_find(void* node, PenguString query) {
    if (!node || !query.data) return pengu_maybe_none();
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (!xnode) return pengu_maybe_none();

    for (xmlNodePtr cur = xnode->children; cur; cur = cur->next) {
        if (cur->type == XML_ELEMENT_NODE && cur->name && strncmp((const char*)cur->name, query.data, (size_t)query.len) == 0 && cur->name[query.len] == '\0') {
            PenguParchmentNode* found = (PenguParchmentNode*)malloc(sizeof(PenguParchmentNode));
            if (!found) return pengu_maybe_none();
            found->tag = pengu_string_new((const char*)cur->name);
            xmlChar* content = xmlNodeGetContent(cur);
            found->text = content ? pengu_string_new((const char*)content) : pengu_string_new("");
            if (content) xmlFree(content);
            found->_ptr = cur;
            return pengu_maybe_some(found);
        }
    }
    return pengu_maybe_none();
}

PenguList pengu_c_parchment_find_all(void* node, PenguString query) {
    PenguList list = pengu_list_new(sizeof(PenguParchmentNode), 4);
    if (!node || !query.data) return list;
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (!xnode) return list;

    for (xmlNodePtr cur = xnode->children; cur; cur = cur->next) {
        if (cur->type == XML_ELEMENT_NODE && cur->name && strncmp((const char*)cur->name, query.data, (size_t)query.len) == 0 && cur->name[query.len] == '\0') {
            PenguParchmentNode item;
            item.tag = pengu_string_new((const char*)cur->name);
            xmlChar* content = xmlNodeGetContent(cur);
            item.text = content ? pengu_string_new((const char*)content) : pengu_string_new("");
            if (content) xmlFree(content);
            item._ptr = cur;
            pengu_list_push(&list, &item);
        }
    }
    return list;
}

PenguMaybe pengu_c_parchment_attr(void* node, PenguString name) {
    if (!node || !name.data) return pengu_maybe_none();
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (!xnode) return pengu_maybe_none();

    char buf[256];
    int len = name.len < 255 ? name.len : 255;
    memcpy(buf, name.data, (size_t)len);
    buf[len] = '\0';

    xmlChar* val = xmlGetProp(xnode, (const xmlChar*)buf);
    if (!val) return pengu_maybe_none();

    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) { xmlFree(val); return pengu_maybe_none(); }
    *res = pengu_string_new((const char*)val);
    xmlFree(val);
    return pengu_maybe_some(res);
}

void pengu_c_parchment_set_attr(void* node, PenguString name, PenguString value) {
    if (!node || !name.data) return;
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (!xnode) return;

    char nbuf[256];
    int nlen = name.len < 255 ? name.len : 255;
    memcpy(nbuf, name.data, (size_t)nlen);
    nbuf[nlen] = '\0';

    char vbuf[4096];
    int vlen = (value.data && value.len < 4095) ? value.len : 0;
    if (value.data && vlen > 0) memcpy(vbuf, value.data, (size_t)vlen);
    vbuf[vlen] = '\0';

    xmlSetProp(xnode, (const xmlChar*)nbuf, (const xmlChar*)vbuf);
}

PenguMaybe pengu_c_parchment_text(void* node) {
    if (!node) return pengu_maybe_none();
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (!xnode) return pengu_maybe_some(&pn->text);

    xmlChar* content = xmlNodeGetContent(xnode);
    if (!content) return pengu_maybe_none();

    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    if (!res) { xmlFree(content); return pengu_maybe_none(); }
    *res = pengu_string_new((const char*)content);
    xmlFree(content);
    return pengu_maybe_some(res);
}

void pengu_c_parchment_set_text(void* node, PenguString text) {
    if (!node) return;
    PenguParchmentNode* pn = (PenguParchmentNode*)node;
    pn->text = text;
    xmlNodePtr xnode = (xmlNodePtr)pn->_ptr;
    if (xnode) {
        char buf[4096];
        int len = (text.data && text.len < 4095) ? text.len : 0;
        if (text.data && len > 0) memcpy(buf, text.data, (size_t)len);
        buf[len] = '\0';
        xmlNodeSetContent(xnode, (const xmlChar*)buf);
    }
}

void* pengu_c_parchment_create_element(PenguString tag) {
    PenguParchmentNode* n = (PenguParchmentNode*)malloc(sizeof(PenguParchmentNode));
    if (!n) return NULL;
    n->tag = tag;
    n->text = pengu_string_new("");

    char buf[256];
    int len = tag.len < 255 ? tag.len : 255;
    if (tag.data && len > 0) memcpy(buf, tag.data, (size_t)len);
    buf[len] = '\0';

    n->_ptr = xmlNewNode(NULL, (const xmlChar*)(len > 0 ? buf : "element"));
    return n;
}

void* pengu_c_parchment_create_text(PenguString text) {
    PenguParchmentNode* n = (PenguParchmentNode*)malloc(sizeof(PenguParchmentNode));
    if (!n) return NULL;
    n->tag = pengu_string_new("text");
    n->text = text;

    char buf[4096];
    int len = (text.data && text.len < 4095) ? text.len : 0;
    if (text.data && len > 0) memcpy(buf, text.data, (size_t)len);
    buf[len] = '\0';

    n->_ptr = xmlNewText((const xmlChar*)buf);
    return n;
}

void pengu_c_parchment_append_child(void* parent, void* child) {
    if (!parent || !child) return;
    PenguParchmentNode* p = (PenguParchmentNode*)parent;
    PenguParchmentNode* c = (PenguParchmentNode*)child;
    if (p->_ptr && c->_ptr) {
        xmlAddChild((xmlNodePtr)p->_ptr, (xmlNodePtr)c->_ptr);
    }
}

/* =========================================================================
 * 4. Seal (Compression & Hashing Real Implementation)
 * ========================================================================= */

int pengu_c_seal_crc32(PenguString data) {
    return (int)crc32(0L, (const Bytef*)(data.data ? data.data : ""), (uInt)data.len);
}

PenguString pengu_c_seal_md5(PenguString data) {
    unsigned char output[16];
    mbedtls_md5((const unsigned char*)(data.data ? data.data : ""), (size_t)data.len, output);
    char hex[33];
    for (int i = 0; i < 16; i++) sprintf(hex + i * 2, "%02x", output[i]);
    hex[32] = '\0';
    return pengu_string_new(hex);
}

PenguString pengu_c_seal_sha1(PenguString data) {
    unsigned char output[20];
    mbedtls_sha1((const unsigned char*)(data.data ? data.data : ""), (size_t)data.len, output);
    char hex[41];
    for (int i = 0; i < 20; i++) sprintf(hex + i * 2, "%02x", output[i]);
    hex[40] = '\0';
    return pengu_string_new(hex);
}

PenguString pengu_c_seal_sha256(PenguString data) {
    unsigned char output[32];
    mbedtls_sha256((const unsigned char*)(data.data ? data.data : ""), (size_t)data.len, output, 0);
    char hex[65];
    for (int i = 0; i < 32; i++) sprintf(hex + i * 2, "%02x", output[i]);
    hex[64] = '\0';
    return pengu_string_new(hex);
}

PenguString pengu_c_seal_sha512(PenguString data) {
    unsigned char output[64];
    mbedtls_sha512((const unsigned char*)(data.data ? data.data : ""), (size_t)data.len, output, 0);
    char hex[129];
    for (int i = 0; i < 64; i++) sprintf(hex + i * 2, "%02x", output[i]);
    hex[128] = '\0';
    return pengu_string_new(hex);
}

PenguMaybe pengu_c_seal_gzip(PenguString data) {
    z_stream strm;
    memset(&strm, 0, sizeof(strm));
    if (deflateInit2(&strm, Z_DEFAULT_COMPRESSION, Z_DEFLATED, 15 + 16, 8, Z_DEFAULT_STRATEGY) != Z_OK) {
        return pengu_maybe_none();
    }
    uLong bound = deflateBound(&strm, (uLong)data.len) + 64;
    unsigned char* out_buf = (unsigned char*)malloc(bound);
    if (!out_buf) {
        deflateEnd(&strm);
        return pengu_maybe_none();
    }
    strm.next_in = (Bytef*)(data.data ? data.data : "");
    strm.avail_in = (uInt)data.len;
    strm.next_out = out_buf;
    strm.avail_out = (uInt)bound;
    deflate(&strm, Z_FINISH);
    uLong out_len = strm.total_out;
    deflateEnd(&strm);

    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    res->data = (char*)out_buf;
    res->len = (int)out_len;
    return pengu_maybe_some(res);
}

PenguMaybe pengu_c_seal_unzip(PenguString data) {
    if (data.len <= 0 || !data.data) return pengu_maybe_none();
    z_stream strm;
    memset(&strm, 0, sizeof(strm));
    if (inflateInit2(&strm, 15 + 32) != Z_OK) {
        return pengu_maybe_none();
    }
    size_t cap = (size_t)data.len * 4 + 1024;
    unsigned char* out_buf = (unsigned char*)malloc(cap);
    if (!out_buf) {
        inflateEnd(&strm);
        return pengu_maybe_none();
    }
    strm.next_in = (Bytef*)data.data;
    strm.avail_in = (uInt)data.len;
    strm.next_out = out_buf;
    strm.avail_out = (uInt)cap;

    int ret = inflate(&strm, Z_NO_FLUSH);
    while (ret == Z_OK && strm.avail_out == 0) {
        size_t old_len = strm.total_out;
        cap *= 2;
        out_buf = (unsigned char*)realloc(out_buf, cap);
        strm.next_out = out_buf + old_len;
        strm.avail_out = (uInt)(cap - old_len);
        ret = inflate(&strm, Z_NO_FLUSH);
    }
    if (ret != Z_STREAM_END && ret != Z_OK) {
        free(out_buf);
        inflateEnd(&strm);
        return pengu_maybe_none();
    }
    uLong out_len = strm.total_out;
    inflateEnd(&strm);
    out_buf[out_len] = '\0';

    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    res->data = (char*)out_buf;
    res->len = (int)out_len;
    return pengu_maybe_some(res);
}

PenguMaybe pengu_c_seal_zlib_compress(PenguString data) {
    uLong bound = compressBound((uLong)data.len);
    unsigned char* out_buf = (unsigned char*)malloc(bound);
    if (!out_buf) return pengu_maybe_none();
    uLong out_len = bound;
    if (compress(out_buf, &out_len, (const Bytef*)(data.data ? data.data : ""), (uLong)data.len) != Z_OK) {
        free(out_buf);
        return pengu_maybe_none();
    }
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    res->data = (char*)out_buf;
    res->len = (int)out_len;
    return pengu_maybe_some(res);
}

PenguMaybe pengu_c_seal_zlib_decompress(PenguString data) {
    if (data.len <= 0 || !data.data) return pengu_maybe_none();
    uLong cap = (uLong)data.len * 4 + 1024;
    unsigned char* out_buf = (unsigned char*)malloc(cap);
    if (!out_buf) return pengu_maybe_none();
    uLong out_len = cap;
    int ret = uncompress(out_buf, &out_len, (const Bytef*)data.data, (uLong)data.len);
    while (ret == Z_BUF_ERROR) {
        cap *= 2;
        out_buf = (unsigned char*)realloc(out_buf, cap);
        out_len = cap;
        ret = uncompress(out_buf, &out_len, (const Bytef*)data.data, (uLong)data.len);
    }
    if (ret != Z_OK) {
        free(out_buf);
        return pengu_maybe_none();
    }
    out_buf[out_len] = '\0';
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    res->data = (char*)out_buf;
    res->len = (int)out_len;
    return pengu_maybe_some(res);
}

PenguMaybe pengu_c_seal_hash_file(PenguString path, PenguString hash_type) {
    char path_buf[1024];
    int len = path.len < 1023 ? path.len : 1023;
    if (path.data && len > 0) memcpy(path_buf, path.data, (size_t)len);
    path_buf[len] = '\0';

    FILE* f = fopen(path_buf, "rb");
    if (!f) return pengu_maybe_none();

    unsigned char buf[4096];
    size_t bytes_read = 0;
    char hex[130];
    hex[0] = '\0';

    if (strcmp(hash_type.data, "md5") == 0) {
        mbedtls_md5_context ctx;
        mbedtls_md5_init(&ctx);
        mbedtls_md5_starts(&ctx);
        while ((bytes_read = fread(buf, 1, sizeof(buf), f)) > 0) {
            mbedtls_md5_update(&ctx, buf, bytes_read);
        }
        unsigned char out[16];
        mbedtls_md5_finish(&ctx, out);
        mbedtls_md5_free(&ctx);
        for (int i = 0; i < 16; i++) sprintf(hex + i * 2, "%02x", out[i]);
    } else if (strcmp(hash_type.data, "sha1") == 0) {
        mbedtls_sha1_context ctx;
        mbedtls_sha1_init(&ctx);
        mbedtls_sha1_starts(&ctx);
        while ((bytes_read = fread(buf, 1, sizeof(buf), f)) > 0) {
            mbedtls_sha1_update(&ctx, buf, bytes_read);
        }
        unsigned char out[20];
        mbedtls_sha1_finish(&ctx, out);
        mbedtls_sha1_free(&ctx);
        for (int i = 0; i < 20; i++) sprintf(hex + i * 2, "%02x", out[i]);
    } else if (strcmp(hash_type.data, "sha256") == 0) {
        mbedtls_sha256_context ctx;
        mbedtls_sha256_init(&ctx);
        mbedtls_sha256_starts(&ctx, 0);
        while ((bytes_read = fread(buf, 1, sizeof(buf), f)) > 0) {
            mbedtls_sha256_update(&ctx, buf, bytes_read);
        }
        unsigned char out[32];
        mbedtls_sha256_finish(&ctx, out);
        mbedtls_sha256_free(&ctx);
        for (int i = 0; i < 32; i++) sprintf(hex + i * 2, "%02x", out[i]);
    } else if (strcmp(hash_type.data, "sha512") == 0) {
        mbedtls_sha512_context ctx;
        mbedtls_sha512_init(&ctx);
        mbedtls_sha512_starts(&ctx, 0);
        while ((bytes_read = fread(buf, 1, sizeof(buf), f)) > 0) {
            mbedtls_sha512_update(&ctx, buf, bytes_read);
        }
        unsigned char out[64];
        mbedtls_sha512_finish(&ctx, out);
        mbedtls_sha512_free(&ctx);
        for (int i = 0; i < 64; i++) sprintf(hex + i * 2, "%02x", out[i]);
    } else {
        fclose(f);
        return pengu_maybe_none();
    }
    fclose(f);
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    *res = pengu_string_new(hex);
    return pengu_maybe_some(res);
}

/* =========================================================================
 * 5. Precis (Networking & HTTP Real Implementation)
 * ========================================================================= */

typedef struct {
    char* data;
    size_t size;
    size_t cap;
} PenguCurlBuffer;

static size_t pengu_curl_write_cb(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total = size * nmemb;
    PenguCurlBuffer* mem = (PenguCurlBuffer*)userp;
    if (mem->size + total + 1 > mem->cap) {
        size_t new_cap = (mem->cap + total + 1) * 2;
        char* ptr = (char*)realloc(mem->data, new_cap);
        if (!ptr) return 0;
        mem->data = ptr;
        mem->cap = new_cap;
    }
    memcpy(&(mem->data[mem->size]), contents, total);
    mem->size += total;
    mem->data[mem->size] = 0;
    return total;
}

static PenguMaybe pengu_curl_do_request(const char* method, PenguString url, PenguMap headers, const char* body_data, int body_len) {
    CURL* curl = curl_easy_init();
    if (!curl) return pengu_maybe_none();

    char url_buf[2048];
    int ulen = url.len < 2047 ? url.len : 2047;
    if (url.data && ulen > 0) memcpy(url_buf, url.data, (size_t)ulen);
    url_buf[ulen] = '\0';

    PenguCurlBuffer chunk;
    chunk.data = (char*)malloc(4096);
    chunk.size = 0;
    chunk.cap = 4096;
    if (chunk.data) chunk.data[0] = '\0';

    curl_easy_setopt(curl, CURLOPT_URL, url_buf);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, pengu_curl_write_cb);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, (void*)&chunk);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "PenguScript/0.6");
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);

    struct curl_slist* header_list = NULL;
    for (int i = 0; i < headers.cap; i++) {
        if (headers.entries && headers.entries[i].occupied) {
            PenguString* k = (PenguString*)headers.entries[i].key;
            PenguString* v = (PenguString*)headers.entries[i].val;
            if (k && k->data && v && v->data) {
                char hdr_line[1024];
                snprintf(hdr_line, sizeof(hdr_line), "%s: %s", k->data, v->data);
                header_list = curl_slist_append(header_list, hdr_line);
            }
        }
    }
    if (header_list) curl_easy_setopt(curl, CURLOPT_HTTPHEADER, header_list);

    if (strcmp(method, "POST") == 0) {
        curl_easy_setopt(curl, CURLOPT_POST, 1L);
        if (body_data && body_len > 0) {
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body_data);
            curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)body_len);
        }
    } else if (strcmp(method, "PUT") == 0) {
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "PUT");
        if (body_data && body_len > 0) {
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body_data);
            curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)body_len);
        }
    } else if (strcmp(method, "DELETE") == 0) {
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "DELETE");
    } else if (strcmp(method, "GET") != 0) {
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, method);
        if (body_data && body_len > 0) {
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body_data);
            curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)body_len);
        }
    }

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        free(chunk.data);
        if (header_list) curl_slist_free_all(header_list);
        curl_easy_cleanup(curl);
        return pengu_maybe_none();
    }

    long response_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &response_code);

    PenguPrecisClientResponse* resp = (PenguPrecisClientResponse*)malloc(sizeof(PenguPrecisClientResponse));
    resp->status_code = (int)response_code;
    resp->headers = pengu_map_new(sizeof(PenguString), sizeof(PenguString));
    resp->url = url;

    PenguString* body_str = (PenguString*)malloc(sizeof(PenguString));
    body_str->data = chunk.data;
    body_str->len = (int)chunk.size;
    resp->body = pengu_maybe_some(body_str);

    if (header_list) curl_slist_free_all(header_list);
    curl_easy_cleanup(curl);

    return pengu_maybe_some(resp);
}

PenguMaybe pengu_c_precis_http_get(PenguString url, PenguMap headers) {
    return pengu_curl_do_request("GET", url, headers, NULL, 0);
}

PenguMaybe pengu_c_precis_http_post(PenguString url, PenguMap headers, PenguString body) {
    return pengu_curl_do_request("POST", url, headers, body.data, body.len);
}

PenguMaybe pengu_c_precis_http_put(PenguString url, PenguMap headers, PenguString body) {
    return pengu_curl_do_request("PUT", url, headers, body.data, body.len);
}

PenguMaybe pengu_c_precis_http_delete(PenguString url, PenguMap headers) {
    return pengu_curl_do_request("DELETE", url, headers, NULL, 0);
}

PenguMaybe pengu_c_precis_http_request(PenguString method, PenguString url, PenguMap headers, PenguMaybe body) {
    char method_buf[32];
    int len = method.len < 31 ? method.len : 31;
    if (method.data && len > 0) memcpy(method_buf, method.data, (size_t)len);
    method_buf[len] = '\0';

    const char* b_data = NULL;
    int b_len = 0;
    if (body.is_present && body.value) {
        PenguString* s = (PenguString*)body.value;
        b_data = s->data;
        b_len = s->len;
    }
    return pengu_curl_do_request(method_buf, url, headers, b_data, b_len);
}

/* Embedded HTTP Server */
typedef struct {
    void* handler_fn;
} PenguServerCtx;

static enum MHD_Result pengu_mhd_access_handler(
    void *cls, struct MHD_Connection *connection,
    const char *url, const char *method,
    const char *version, const char *upload_data,
    size_t *upload_data_size, void **con_cls)
{
    (void)version; (void)upload_data; (void)upload_data_size; (void)con_cls;
    PenguServerCtx* ctx = (PenguServerCtx*)cls;
    if (!ctx || !ctx->handler_fn) return MHD_NO;

    PenguPrecisRequest req;
    req.method = pengu_string_new(method ? method : "GET");
    req.path = pengu_string_new(url ? url : "/");
    req.headers = pengu_map_new(sizeof(PenguString), sizeof(PenguString));
    req.query = pengu_map_new(sizeof(PenguString), sizeof(PenguString));
    req.body = pengu_maybe_none();

    typedef PenguPrecisResponse (*ServerHandlerFn)(PenguPrecisRequest);
    ServerHandlerFn fn = (ServerHandlerFn)ctx->handler_fn;
    PenguPrecisResponse res = fn(req);

    const char* body_str = "OK";
    size_t body_len = 2;
    if (res.body.is_present && res.body.value) {
        PenguString* bs = (PenguString*)res.body.value;
        body_str = bs->data ? bs->data : "";
        body_len = (size_t)bs->len;
    }

    struct MHD_Response *response = MHD_create_response_from_buffer(
        body_len, (void*)body_str, MHD_RESPMEM_MUST_COPY
    );
    if (!response) return MHD_NO;

    int status = res.status_code > 0 ? res.status_code : 200;
    enum MHD_Result ret = MHD_queue_response(connection, status, response);
    MHD_destroy_response(response);
    return ret;
}

void pengu_c_precis_serve_http(int port, void* handler) {
    if (!handler) return;
    PenguServerCtx ctx;
    ctx.handler_fn = handler;
    struct MHD_Daemon *daemon = MHD_start_daemon(
        MHD_USE_INTERNAL_POLLING_THREAD, (uint16_t)port, NULL, NULL,
        &pengu_mhd_access_handler, &ctx, MHD_OPTION_END
    );
    if (!daemon) return;
    // Keep running
    while (1) {
        pengu_c_sleep_ms(1000);
    }
    MHD_stop_daemon(daemon);
}

/* Sockets & DNS */
static int pengu_sockets_inited = 0;
static void pengu_ensure_sockets(void) {
#if PENGU_WINDOWS
    if (!pengu_sockets_inited) {
        WSADATA wsa;
        WSAStartup(MAKEWORD(2, 2), &wsa);
        pengu_sockets_inited = 1;
    }
#else
    pengu_sockets_inited = 1;
#endif
}

PenguMaybe pengu_c_precis_tcp_connect(PenguString host, int port) {
    pengu_ensure_sockets();
    char host_buf[256];
    int len = host.len < 255 ? host.len : 255;
    if (host.data && len > 0) memcpy(host_buf, host.data, (size_t)len);
    host_buf[len] = '\0';

    char port_buf[16];
    snprintf(port_buf, sizeof(port_buf), "%d", port);

    struct addrinfo hints, *res, *p;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    if (getaddrinfo(host_buf, port_buf, &hints, &res) != 0) {
        return pengu_maybe_none();
    }

    int sockfd = -1;
    for (p = res; p != NULL; p = p->ai_next) {
        sockfd = (int)socket(p->ai_family, p->ai_socktype, p->ai_protocol);
        if (sockfd < 0) continue;
        if (connect(sockfd, p->ai_addr, (int)p->ai_addrlen) == 0) {
            break;
        }
#if PENGU_WINDOWS
        closesocket(sockfd);
#else
        close(sockfd);
#endif
        sockfd = -1;
    }
    freeaddrinfo(res);

    if (sockfd < 0) return pengu_maybe_none();

    PenguPrecisTCPSocket* sock = (PenguPrecisTCPSocket*)malloc(sizeof(PenguPrecisTCPSocket));
    sock->_ptr = (void*)(intptr_t)sockfd;
    return pengu_maybe_some(sock);
}

bool pengu_c_precis_tcp_send(void* sock, PenguString data) {
    if (!sock) return false;
    PenguPrecisTCPSocket* s = (PenguPrecisTCPSocket*)sock;
    int fd = (int)(intptr_t)s->_ptr;
    if (fd <= 0 || !data.data || data.len <= 0) return false;
    int sent = send(fd, data.data, data.len, 0);
    return sent == data.len;
}

PenguMaybe pengu_c_precis_tcp_recv(void* sock, int size) {
    if (!sock || size <= 0) return pengu_maybe_none();
    PenguPrecisTCPSocket* s = (PenguPrecisTCPSocket*)sock;
    int fd = (int)(intptr_t)s->_ptr;
    if (fd <= 0) return pengu_maybe_none();

    char* buf = (char*)malloc((size_t)size + 1);
    if (!buf) return pengu_maybe_none();
    int recvd = recv(fd, buf, size, 0);
    if (recvd <= 0) {
        free(buf);
        return pengu_maybe_none();
    }
    buf[recvd] = '\0';
    PenguString* res = (PenguString*)malloc(sizeof(PenguString));
    res->data = buf;
    res->len = recvd;
    return pengu_maybe_some(res);
}

void pengu_c_precis_tcp_close(void* sock) {
    if (!sock) return;
    PenguPrecisTCPSocket* s = (PenguPrecisTCPSocket*)sock;
    int fd = (int)(intptr_t)s->_ptr;
    if (fd > 0) {
#if PENGU_WINDOWS
        closesocket(fd);
#else
        close(fd);
#endif
        s->_ptr = NULL;
    }
}

PenguMaybe pengu_c_precis_dns_lookup(PenguString host) {
    pengu_ensure_sockets();
    char host_buf[256];
    int len = host.len < 255 ? host.len : 255;
    if (host.data && len > 0) memcpy(host_buf, host.data, (size_t)len);
    host_buf[len] = '\0';

    struct addrinfo hints, *res;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET; // IPv4
    hints.ai_socktype = SOCK_STREAM;

    if (getaddrinfo(host_buf, NULL, &hints, &res) != 0 || !res) {
        return pengu_maybe_none();
    }

    struct sockaddr_in* ipv4 = (struct sockaddr_in*)res->ai_addr;
    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &(ipv4->sin_addr), ip_str, INET_ADDRSTRLEN);
    freeaddrinfo(res);

    PenguString* res_str = (PenguString*)malloc(sizeof(PenguString));
    *res_str = pengu_string_new(ip_str);
    return pengu_maybe_some(res_str);
}

/* URL Encoding & Decoding */
PenguString pengu_c_precis_url_encode(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_new("");
    size_t cap = (size_t)s.len * 3 + 1;
    char* buf = (char*)malloc(cap);
    size_t pos = 0;
    const char hex_chars[] = "0123456789ABCDEF";

    for (int i = 0; i < s.len; i++) {
        unsigned char c = (unsigned char)s.data[i];
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
            c == '-' || c == '_' || c == '.' || c == '~') {
            buf[pos++] = c;
        } else {
            buf[pos++] = '%';
            buf[pos++] = hex_chars[(c >> 4) & 0x0F];
            buf[pos++] = hex_chars[c & 0x0F];
        }
    }
    buf[pos] = '\0';
    PenguString res;
    res.data = buf;
    res.len = (int)pos;
    return res;
}

PenguString pengu_c_precis_url_decode(PenguString s) {
    if (!s.data || s.len == 0) return pengu_string_new("");
    size_t cap = (size_t)s.len + 1;
    char* buf = (char*)malloc(cap);
    size_t pos = 0;

    for (int i = 0; i < s.len; i++) {
        char c = s.data[i];
        if (c == '+') {
            buf[pos++] = ' ';
        } else if (c == '%' && i + 2 < s.len) {
            char h1 = s.data[i + 1];
            char h2 = s.data[i + 2];
            int v1 = (h1 >= '0' && h1 <= '9') ? h1 - '0' : (h1 >= 'a' && h1 <= 'f') ? h1 - 'a' + 10 : (h1 >= 'A' && h1 <= 'F') ? h1 - 'A' + 10 : -1;
            int v2 = (h2 >= '0' && h2 <= '9') ? h2 - '0' : (h2 >= 'a' && h2 <= 'f') ? h2 - 'a' + 10 : (h2 >= 'A' && h2 <= 'F') ? h2 - 'A' + 10 : -1;
            if (v1 >= 0 && v2 >= 0) {
                buf[pos++] = (char)((v1 << 4) | v2);
                i += 2;
            } else {
                buf[pos++] = c;
            }
        } else {
            buf[pos++] = c;
        }
    }
    buf[pos] = '\0';
    PenguString res;
    res.data = buf;
    res.len = (int)pos;
    return res;
}

PenguMap pengu_c_precis_parse_query(PenguString s) {
    PenguMap m = pengu_map_new(sizeof(PenguString), sizeof(PenguString));
    if (!s.data || s.len == 0) return m;

    int cur_start = 0;
    for (int i = 0; i <= s.len; i++) {
        if (i == s.len || s.data[i] == '&') {
            int param_len = i - cur_start;
            if (param_len > 0) {
                int eq_pos = -1;
                for (int j = cur_start; j < i; j++) {
                    if (s.data[j] == '=') { eq_pos = j; break; }
                }
                if (eq_pos >= 0) {
                    PenguString k_enc;
                    k_enc.data = s.data + cur_start;
                    k_enc.len = eq_pos - cur_start;
                    PenguString v_enc;
                    v_enc.data = s.data + eq_pos + 1;
                    v_enc.len = i - (eq_pos + 1);
                    PenguString k = pengu_c_precis_url_decode(k_enc);
                    PenguString v = pengu_c_precis_url_decode(v_enc);
                    pengu_map_put(&m, &k, &v);
                }
            }
            cur_start = i + 1;
        }
    }
    return m;
}


