/*
 * pengu_runtime.c - PenguScript C Runtime
 *
 * Implements the core primitives every PenguScript program links against plus
 * the concurrency backend:
 *   - core (strings, slices, lists, maps, maybe/result, memory, print/input,
 *     filesystem, time, math, and the C <-> Pengu conversion bridges)
 *   - filum (concurrency: Win32 threads / pthreads, channels, mutex, atomic)
 *
 * The runtime depends on nothing beyond libc, libm and pthreads / Win32.
 * Bindings to external C libraries (PCRE2, libxml2, mbedtls, zlib, libcurl,
 * libmicrohttpd, ...) live in satellite repositories installed with
 * `pengu add`; see docs/EXTERNAL_MODULES.md.
 */

#include "pengu_runtime.h"

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
#if defined(__linux__)
#include <sys/syscall.h>
#endif
#endif

/* `build_runtime.py` compiles this unit once per subsystem so the archive has
 * one member per subsystem, and the linker then pulls only what a program
 * references.  The ABI pin and the FFI bridges are non-static, so they must
 * exist in exactly one member: the core compile passes the flag as 0 and the
 * subsystem compiles as 1.  The default here keeps a plain single-TU compile
 * (tests, a manual `gcc -c`) working unchanged. */
#ifndef PENGU_RUNTIME_SUBSYSTEM_ONLY
#define PENGU_RUNTIME_SUBSYSTEM_ONLY 0
#endif
#if !PENGU_RUNTIME_SUBSYSTEM_ONLY
/* =========================================================================
 * 0. Runtime ABI version (Phase 3 item 3.5)
 *
 * The single object-file symbol behind the link-time ABI pin. It must live here
 * and not in the header: generated bundles reference it externally precisely so
 * that a stale `libpengu_runtime.a` cannot be linked against a newer bundle.
 * ========================================================================= */
int pengu_abi_version(void) {
    return PENGU_ABI_VERSION;
}
#endif /* !PENGU_RUNTIME_SUBSYSTEM_ONLY */

#if PENGU_ENABLE_THREADS
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
#elif defined(__linux__)
    /* glibc has no pthread_threadid_np; the OS thread id is the gettid. */
    long tid = syscall(SYS_gettid);
    return (int)((unsigned long)tid & 0x7fffffff);
#elif defined(__APPLE__)
    /* Darwin declares this only outside strict POSIX mode; pengu_runtime.h
     * defines _DARWIN_C_SOURCE for that (see the feature-test macros there).
     * pthread_self() is spelled out instead of passing NULL: it is the
     * documented, always-valid way to ask for the calling thread. */
    unsigned long long tid = 0;
    pthread_threadid_np(pthread_self(), &tid);
    return (int)(tid & 0x7fffffff);
#else
    /* Portable fallback -- also the Emscripten path: emcc defines `__unix__`
     * but NOT `__linux__`, so neither the syscall branch above nor the Apple
     * one is taken. `pthread_self()` is distinct per real Worker when the
     * program is linked with `-pthread`, which is exactly the guarantee the
     * callers of this function need. */
    return (int)((unsigned long)pthread_self() & 0x7fffffff);
#endif
}

void pengu_c_filum_go(void* f) {
    if (!f) return;
    PenguThreadArg* arg = (PenguThreadArg*)malloc(sizeof(PenguThreadArg));
    if (!arg) return;
    arg->fn = (void (*)(void))f;

#if PENGU_WINDOWS
    uintptr_t th = _beginthreadex(NULL, 0, pengu_win32_thread_runner, arg, 0, NULL);
    if (th) {
        /* `go` is fire-and-forget (the Go model): closing the handle detaches,
         * so the thread's resources are released when it exits and there is
         * never a join to perform. */
        CloseHandle((HANDLE)th);
    } else {
        /* No thread was created, so the runner never runs and would never free
         * the argument; this is the only chance to release it. */
        free(arg);
    }
#else
    pthread_t th;
    if (pthread_create(&th, NULL, pengu_posix_thread_runner, arg) == 0) {
        /* Detach immediately for the same reason as the Windows branch above:
         * without it the pthread_t handle leaks, and under Emscripten the Web
         * Worker is never reclaimed. */
        pthread_detach(th);
    } else {
        /* See the Windows branch: the runner cannot free what never ran. */
        free(arg);
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

/* AtomicInt.
 *
 * The POSIX side declares a real `_Atomic long` member instead of casting a
 * `volatile long` through `(atomic_long*)` at every call: accessing a
 * non-atomic object through an atomic lvalue is undefined behaviour in C11 even
 * when the layout matches, and a compiler is free to reorder or tear the access
 * on that basis.  Windows keeps `volatile long` + the Interlocked family, which
 * is the portable Win32 spelling (MSVC's <stdatomic.h> only arrived in C11
 * mode). */
typedef struct {
#if PENGU_WINDOWS
    volatile long val;
#else
    atomic_long val;
#endif
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
    return (int)atomic_load(&na->val);
#endif
}

void pengu_c_filum_atomic_int_store(void* a, int val) {
    if (!a) return;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    InterlockedExchange(&na->val, val);
#else
    atomic_store(&na->val, val);
#endif
}

int pengu_c_filum_atomic_int_add(void* a, int delta) {
    if (!a) return 0;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (int)(InterlockedExchangeAdd(&na->val, delta));
#else
    return (int)(atomic_fetch_add(&na->val, delta));
#endif
}

int pengu_c_filum_atomic_int_swap(void* a, int new_val) {
    if (!a) return 0;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (int)InterlockedExchange(&na->val, new_val);
#else
    return (int)atomic_exchange(&na->val, new_val);
#endif
}

bool pengu_c_filum_atomic_int_compare_swap(void* a, int old_val, int new_val) {
    if (!a) return false;
    PenguNativeAtomicInt* na = (PenguNativeAtomicInt*)a;
#if PENGU_WINDOWS
    return (InterlockedCompareExchange(&na->val, new_val, old_val) == old_val);
#else
    long expected = old_val;
    return atomic_compare_exchange_strong(&na->val, &expected, (long)new_val);
#endif
}

/* Channels */
typedef struct {
    uint8_t* buffer;
    size_t elem_size;
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

void* pengu_c_filum_chan_new(size_t elem_size, int cap) {
    if (cap < 1) cap = 1;
    PenguNativeChan* ch = (PenguNativeChan*)malloc(sizeof(PenguNativeChan));
    if (!ch) return NULL;
    ch->elem_size = elem_size > 0 ? elem_size : (size_t)sizeof(void*);
    ch->cap = cap;
    ch->head = 0;
    ch->tail = 0;
    ch->size = 0;
    ch->closed = false;
    ch->buffer = (uint8_t*)malloc((size_t)ch->elem_size * (size_t)cap);
    if (!ch->buffer) {
        /* Every later send/recv memcpy's into this buffer, so a NULL here would
         * turn a failed allocation into a null dereference at the first message.
         * Report the failure instead and leave no half-initialised handle. */
        free(ch);
        return NULL;
    }
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

/* ---------------------------------------------------------------------------
 * Filum resource cleanup: every pengu_c_filum_*_new handle must be released
 * with its matching *_free when the PenguScript object is disposed.
 * ------------------------------------------------------------------------- */

void pengu_c_filum_mutex_free(void* m) {
    if (!m) return;
    PenguNativeMutex* nm = (PenguNativeMutex*)m;
#if PENGU_WINDOWS
    DeleteCriticalSection(&nm->cs);
#else
    pthread_mutex_destroy(&nm->mtx);
#endif
    free(m);
}

void pengu_c_filum_wait_group_free(void* wg) {
    if (!wg) return;
    PenguNativeWaitGroup* nwg = (PenguNativeWaitGroup*)wg;
    /* Release anyone parked in `wait` before destroying the primitives they are
     * parked on: zeroing the count makes the `while (count > 0)` loop fall
     * through. Destroying a condition variable that still has waiters is
     * undefined behaviour, and it is the one teardown defect the sanitizers
     * cannot see (the object is freed, so there is no leak to report). The
     * caller must still not free a wait group another thread is about to use --
     * that contract is unchanged. */
#if PENGU_WINDOWS
    EnterCriticalSection(&nwg->cs);
    nwg->count = 0;
    WakeAllConditionVariable(&nwg->cv);
    LeaveCriticalSection(&nwg->cs);
    DeleteCriticalSection(&nwg->cs);
#else
    pthread_mutex_lock(&nwg->mtx);
    nwg->count = 0;
    pthread_cond_broadcast(&nwg->cv);
    pthread_mutex_unlock(&nwg->mtx);
    pthread_mutex_destroy(&nwg->mtx);
    pthread_cond_destroy(&nwg->cv);
#endif
    free(wg);
}

void pengu_c_filum_once_free(void* o) {
    if (!o) return;
    PenguNativeOnce* no = (PenguNativeOnce*)o;
#if PENGU_WINDOWS
    DeleteCriticalSection(&no->cs);
#else
    pthread_mutex_destroy(&no->mtx);
#endif
    free(o);
}

void pengu_c_filum_cond_free(void* c) {
    if (!c) return;
    PenguNativeCond* nc = (PenguNativeCond*)c;
    /* Wake any waiter before destroying: a condition variable destroyed with
     * waiters on it is undefined behaviour, and under Emscripten's pthread
     * emulation the waiter would never observe the wake. */
#if PENGU_WINDOWS
    WakeAllConditionVariable(&nc->cv);
#else
    pthread_cond_broadcast(&nc->cv);
    pthread_cond_destroy(&nc->cv);
#endif
    free(c);
}

void pengu_c_filum_atomic_int_free(void* a) {
    if (!a) return;
    free(a);
}

void pengu_c_filum_chan_free(void* c) {
    if (!c) return;
    PenguNativeChan* ch = (PenguNativeChan*)c;
    /* Wake every blocked sender/receiver before tearing the primitives down.
     * Destroying a condition variable that still has waiters is undefined
     * behaviour, and Emscripten's pthread emulation is particularly unforgiving
     * about it. Closing the channel first makes each blocked call return false
     * ("closed channel"), which is a result the caller already handles. The
     * caller must still not free a channel other threads are about to use. */
#if PENGU_WINDOWS
    EnterCriticalSection(&ch->cs);
    ch->closed = true;
    WakeAllConditionVariable(&ch->not_empty);
    WakeAllConditionVariable(&ch->not_full);
    LeaveCriticalSection(&ch->cs);
    DeleteCriticalSection(&ch->cs);
#else
    pthread_mutex_lock(&ch->mtx);
    ch->closed = true;
    pthread_cond_broadcast(&ch->not_empty);
    pthread_cond_broadcast(&ch->not_full);
    pthread_mutex_unlock(&ch->mtx);
    pthread_mutex_destroy(&ch->mtx);
    pthread_cond_destroy(&ch->not_empty);
    pthread_cond_destroy(&ch->not_full);
#endif
    if (ch->buffer) free(ch->buffer);
    free(c);
}

#endif /* PENGU_ENABLE_THREADS */

#if !PENGU_RUNTIME_SUBSYSTEM_ONLY
/* =========================================================================
 * 25. C <-> Pengu Conversion Bridges (FFI)
 * ========================================================================= */

PenguList pengu_list_from_data(const void *data, size_t elem_size, int count) {
    if (count <= 0 || elem_size == 0) {
        PenguList empty;
        empty.data = NULL;
        empty.len = 0;
        empty.cap = 0;
        empty.elem_size = elem_size > 0 ? elem_size : sizeof(void *);
        return empty;
    }
    if (!data) {
        PenguList empty = pengu_list_new(elem_size, 4);
        empty.len = 0;
        return empty;
    }
    PenguList list = pengu_list_new(elem_size, (size_t)count);
    if (!list.data) {
        list.len = 0;
        list.cap = 0;
        list.elem_size = elem_size;
        return list;
    }
    memcpy(list.data, data, (size_t)count * elem_size);
    list.len = count;
    return list;
}

PenguMap pengu_map_from_entries(const void *keys, const void *values,
                                size_t key_size, size_t val_size, int count) {
    PenguMap map = pengu_map_new(key_size > 0 ? key_size : sizeof(void *),
                                 val_size > 0 ? val_size : sizeof(void *));
    if (count <= 0 || !keys || !values || key_size == 0 || val_size == 0)
        return map;
    for (int i = 0; i < count; ++i) {
        const char *k = (const char *)keys + ((size_t)i * key_size);
        const char *v = (const char *)values + ((size_t)i * val_size);
        pengu_map_put(&map, k, v);
    }
    return map;
}

PenguEntryArray pengu_map_to_entries(const PenguMap *map) {
    PenguEntryArray out;
    out.keys = NULL;
    out.values = NULL;
    out.count = 0;
    out.key_size = map ? map->key_size : 0;
    out.val_size = map ? map->val_size : 0;
    if (!map || map->len <= 0 || !map->entries || map->key_size == 0 || map->val_size == 0)
        return out;

    out.keys = malloc((size_t)map->len * map->key_size);
    out.values = malloc((size_t)map->len * map->val_size);
    if (!out.keys || !out.values) {
        if (out.keys) free(out.keys);
        if (out.values) free(out.values);
        out.keys = NULL;
        out.values = NULL;
        return out;
    }

    int n = 0;
    for (int i = 0; i < map->cap && n < map->len; ++i) {
        if (!map->entries[i].occupied)
            continue;
        char *kdst = (char *)out.keys + ((size_t)n * map->key_size);
        char *vdst = (char *)out.values + ((size_t)n * map->val_size);
        if (map->key_size == sizeof(PenguString)) {
            PenguString *src = (PenguString *)map->entries[i].key;
            PenguString *dst = (PenguString *)kdst;
            if (src && src->data && src->len > 0) {
                *dst = pengu_string_owned(src->data, src->len);
            } else {
                *dst = pengu_string_from_cstr(PENGU_EMPTY_CSTR);
            }
        } else {
            memcpy(kdst, map->entries[i].key, map->key_size);
        }
        if (map->val_size == sizeof(PenguString)) {
            PenguString *src = (PenguString *)map->entries[i].val;
            PenguString *dst = (PenguString *)vdst;
            if (src && src->data && src->len > 0) {
                *dst = pengu_string_owned(src->data, src->len);
            } else {
                *dst = pengu_string_from_cstr(PENGU_EMPTY_CSTR);
            }
        } else {
            memcpy(vdst, map->entries[i].val, map->val_size);
        }
        n++;
    }
    out.count = n;
    if (n < map->len) {
        /* Should not happen (len counts occupied slots); keep defensive. */
        out.count = n;
    }
    return out;
}

void pengu_entry_array_free(PenguEntryArray *arr) {
    if (!arr)
        return;
    if (arr->keys) {
        if (arr->key_size == sizeof(PenguString)) {
            for (int i = 0; i < arr->count; ++i) {
                PenguString *s = (PenguString *)arr->keys + i;
                pengu_banish_string(s);
            }
        }
        free(arr->keys);
        arr->keys = NULL;
    }
    if (arr->values) {
        if (arr->val_size == sizeof(PenguString)) {
            for (int i = 0; i < arr->count; ++i) {
                PenguString *s = (PenguString *)arr->values + i;
                pengu_banish_string(s);
            }
        }
        free(arr->values);
        arr->values = NULL;
    }
    arr->count = 0;
}

PenguSlice pengu_string_as_slice(PenguString s) {
    PenguSlice slice;
    slice.data = s.data ? (void *)s.data : (void *)PENGU_EMPTY_CSTR;
    slice.len = s.data ? s.len : 0;
    slice.elem_size = 1;
    return slice;
}

PenguString pengu_string_copy(PenguString s) {
    if (!s.data || s.len <= 0) {
        PenguString empty;
        empty.len = 0;
        empty.data = (char *)PENGU_EMPTY_CSTR;
        empty.is_owned = PENGU_STRING_BORROWED;
        return empty;
    }
    return pengu_string_owned(s.data, s.len);
}

/* ---------------------------------------------------------------------------
 * Typed bridges used by std/ffi.pengu (one symbol per PenguScript element
 * type: the PenguScript container C layout is shared, but the language types
 * are nominal, so each concrete wrapper needs its own callable symbol).
 * ------------------------------------------------------------------------- */

PenguSlice pengu_ffi_slice_raw(const void *data, int elem_size, int count) {
    return (PenguSlice){ .data = (void *)data, .len = count > 0 ? count : 0, .elem_size = elem_size > 0 ? elem_size : 1 };
}

PenguSlice pengu_ffi_slice_u8(const void *data, int count) {
    return pengu_slice_new((void *)(data ? data : (void *)PENGU_EMPTY_CSTR), 1, count > 0 ? count : 0);
}
PenguSlice pengu_ffi_slice_i32(const void *data, int count) {
    return pengu_slice_new((void *)(data ? data : (void *)PENGU_EMPTY_CSTR), sizeof(int32_t), count > 0 ? count : 0);
}
PenguSlice pengu_ffi_slice_f64(const void *data, int count) {
    return pengu_slice_new((void *)(data ? data : (void *)PENGU_EMPTY_CSTR), sizeof(double), count > 0 ? count : 0);
}

PenguList pengu_ffi_list_u8(const void *data, int count) {
    return pengu_list_from_data(data, 1, count);
}
PenguList pengu_ffi_list_i32(const void *data, int count) {
    return pengu_list_from_data(data, sizeof(int32_t), count);
}
PenguList pengu_ffi_list_f64(const void *data, int count) {
    return pengu_list_from_data(data, sizeof(double), count);
}

PenguString pengu_ffi_cstr_string(const char *s) {
    return pengu_string_new(s); /* NULL-safe owning copy */
}
const char *pengu_ffi_string_cstr(PenguString s) {
    return pengu_string_to_cstr(&s);
}
const void *pengu_ffi_string_bytes(PenguString s) {
    return pengu_string_bytes(&s);
}

PenguMap pengu_ffi_map_si(PenguSlice keys, PenguSlice vals) {
    PenguMap map = pengu_map_new(sizeof(PenguString), sizeof(int32_t));
    int n = keys.len < vals.len ? keys.len : vals.len;
    if (n <= 0 || !keys.data || !vals.data)
        return map;
    PenguString *karr = (PenguString *)keys.data;
    int32_t *varr = (int32_t *)vals.data;
    for (int i = 0; i < n; ++i) {
        pengu_map_put(&map, &karr[i], &varr[i]);
    }
    return map;
}

/* =========================================================================
 * 26. std.memoria support (Phase 5)
 *
 * Manual heap primitives behind std/memoria.pengu: pure libc
 * (calloc/realloc/free/memcpy/memset). No struct layout is touched, so
 * PENGU_ABI_VERSION stays 2. The aborting variants route their failure
 * through pengu_memoria_oom(), which honours the same PENGU_OOM_ABORT policy
 * as pengu_sigil_alloc().
 * ========================================================================= */

/* Reports an out-of-memory condition under the configured runtime policy. */
static void pengu_memoria_oom(size_t size) {
#if PENGU_OOM_ABORT
    fprintf(stderr, "\n[PENGU] out of memory: failed to allocate %zu byte(s)\n", size);
    fflush(stderr);
    abort();
#else
    (void)size;
#endif
}

/* count * elem_size with overflow reported through *ok (0 on overflow). */
static size_t pengu_memoria_bytes(size_t count, size_t elem_size, int *ok) {
    if (elem_size != 0 && count > SIZE_MAX / elem_size) {
        if (ok) *ok = 0;
        return 0;
    }
    if (ok) *ok = 1;
    return count * elem_size;
}

void *pengu_memoria_alloc(size_t n) {
    void *p = calloc(1, n);
    if (!p && n > 0) {
        pengu_memoria_oom(n);
    }
    return p;
}

void *pengu_memoria_try_alloc(size_t n) {
    return calloc(1, n);
}

void *pengu_memoria_alloc_array(size_t count, size_t elem_size) {
    int ok = 1;
    size_t bytes = pengu_memoria_bytes(count, elem_size, &ok);
    void *p;
    if (!ok) {
        pengu_memoria_oom(SIZE_MAX);
        return NULL;
    }
    p = calloc(1, bytes);
    if (!p && bytes > 0) {
        pengu_memoria_oom(bytes);
    }
    return p;
}

void *pengu_memoria_try_alloc_array(size_t count, size_t elem_size) {
    int ok = 1;
    size_t bytes = pengu_memoria_bytes(count, elem_size, &ok);
    if (!ok) {
        return NULL;
    }
    return calloc(1, bytes);
}

/* Shared body of resize/try_resize. abort_on_oom == 0 leaves the original
 * block untouched and reports failure with NULL instead of aborting. */
static void *pengu_memoria_resize_impl(void *p, size_t old_n, size_t new_n,
                                       size_t elem_size, int abort_on_oom) {
    int ok = 1;
    size_t new_bytes = pengu_memoria_bytes(new_n, elem_size, &ok);
    size_t old_bytes;
    void *np;

    if (!ok) {
        if (abort_on_oom) {
            pengu_memoria_oom(SIZE_MAX);
        }
        return NULL;
    }

    /* A NULL block is the documented "fresh allocation" case: zeroed. */
    if (!p) {
        np = calloc(1, new_bytes);
        if (!np && new_bytes > 0) {
            if (abort_on_oom) {
                pengu_memoria_oom(new_bytes);
            }
        }
        return np;
    }

    if (new_n == old_n) {
        return p;
    }

    old_bytes = pengu_memoria_bytes(old_n, elem_size, NULL);
    np = realloc(p, new_bytes);
    if (!np) {
        /* realloc left the original block valid and owned by the caller. */
        if (abort_on_oom) {
            pengu_memoria_oom(new_bytes);
        }
        return NULL;
    }
    if (new_bytes > old_bytes) {
        memset((char *)np + old_bytes, 0, new_bytes - old_bytes);
    }
    return np;
}

void *pengu_memoria_resize(void *p, size_t old_n, size_t new_n, size_t elem_size) {
    return pengu_memoria_resize_impl(p, old_n, new_n, elem_size, 1);
}

void *pengu_memoria_try_resize(void *p, size_t old_n, size_t new_n, size_t elem_size) {
    return pengu_memoria_resize_impl(p, old_n, new_n, elem_size, 0);
}

void pengu_memoria_swap(void *a, void *b, size_t elem_size) {
    unsigned char *pa = (unsigned char *)a;
    unsigned char *pb = (unsigned char *)b;
    size_t i;
    if (!pa || !pb || pa == pb) {
        return;
    }
    for (i = 0; i < elem_size; ++i) {
        unsigned char tmp = pa[i];
        pa[i] = pb[i];
        pb[i] = tmp;
    }
}

void pengu_memoria_fill(void *dst, const void *value, size_t count, size_t elem_size) {
    char *d = (char *)dst;
    const char *v = (const char *)value;
    size_t i;
    if (!d || !v || elem_size == 0) {
        return;
    }
    for (i = 0; i < count; ++i) {
        memcpy(d + (i * elem_size), v, elem_size);
    }
}

#endif /* !PENGU_RUNTIME_SUBSYSTEM_ONLY */
