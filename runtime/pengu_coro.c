/* pengu_coro.c — stackful coroutines backed by minicoro.
 *
 * The public ABI is declared in pengu_runtime.h section 21. This file owns the
 * arena/free-list so the compiler and std.coro do not need to know minicoro's
 * layout. A coroutine slot is one page-aligned block:
 *
 *   [ PenguCoro header | mco_coro | storage | coroutine stack ]
 *
 * mco_init()/mco_uninit() operate in place; mco_create()/mco_destroy() would
 * allocate and free a block per task, which defeats the free-list.
 */
#include "pengu_runtime.h"

#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <execinfo.h>
#include <sys/mman.h>
#include <unistd.h>
#endif

#define MINICORO_IMPL
#include "minicoro.h"

#if defined(_MSC_VER)
#define PENGU_CORO_TLS __declspec(thread)
#elif defined(__GNUC__) || defined(__clang__)
#define PENGU_CORO_TLS __thread
#else
#define PENGU_CORO_TLS _Thread_local
#endif

/* Defaults are overridable at runtime-build time with -D. */
#ifndef PENGU_CORO_STACK_SIZE
#define PENGU_CORO_STACK_SIZE 65536
#endif
#ifndef PENGU_CORO_STORAGE_SIZE
#define PENGU_CORO_STORAGE_SIZE 1024
#endif
#ifndef PENGU_CORO_ARENA_SIZE
#define PENGU_CORO_ARENA_SIZE (2u * 1024u * 1024u)
#endif
#ifndef PENGU_CORO_POOL_MAX
#define PENGU_CORO_POOL_MAX 1024
#endif

#define PENGU_CORO_CANARY 0xC0FFEE0DC0FFEE0DULL

typedef struct PenguCoro {
    mco_coro *co;
    void (*run)(void *);
    void *box;
    uint64_t owner;
    struct PenguCoro *next_free;
    size_t slot_size;
    /* Debug-only fiber trace: live list + last yield backtrace. */
    struct PenguCoro *live_prev;
    struct PenguCoro *live_next;
    int bt_n;
    void *bt[24];
} PenguCoro;

static _Atomic uint64_t g_owner_seq = 0;
static PENGU_CORO_TLS uint64_t t_owner = 0;
static PENGU_CORO_TLS PenguCoro *t_free_list = NULL;
static PENGU_CORO_TLS size_t t_free_count = 0;
static PENGU_CORO_TLS PenguCoro *t_live = NULL;
static PENGU_CORO_TLS int t_trace = -1;

static int pengu_coro_trace_enabled(void) {
    if (t_trace < 0) {
        const char *v = getenv("PENGU_FIBER_TRACE");
        t_trace = (v != NULL && v[0] != '\0' && v[0] != '0') ? 1 : 0;
    }
    return t_trace;
}

void pengu_c_coro_dump(void);

static void pengu_coro_panic(const char *msg) {
    fprintf(stderr, "[PENGU] coro: %s\n", msg);
    fflush(stderr);
    if (pengu_coro_trace_enabled()) {
        pengu_c_coro_dump();
    }
    abort();
}

static uint64_t pengu_coro_owner_token(void) {
    if (t_owner == 0) {
        uint64_t next = atomic_fetch_add_explicit(&g_owner_seq, 1, memory_order_relaxed) + 1;
        if (next == 0) {
            next = atomic_fetch_add_explicit(&g_owner_seq, 1, memory_order_relaxed) + 1;
        }
        t_owner = next;
    }
    return t_owner;
}

static size_t pengu_coro_page_size(void) {
#if defined(_WIN32)
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    return (size_t)si.dwPageSize;
#else
    long p = sysconf(_SC_PAGESIZE);
    return p > 0 ? (size_t)p : 4096u;
#endif
}

static size_t pengu_coro_align_up(size_t n, size_t align) {
    return (n + align - 1u) & ~(align - 1u);
}

static void *pengu_coro_arena_map(size_t size) {
#if defined(_WIN32)
    return VirtualAlloc(NULL, size, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
#else
    void *p = mmap(NULL, size, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    return p == MAP_FAILED ? NULL : p;
#endif
}

static void pengu_coro_release_pages(PenguCoro *h) {
#if !defined(_WIN32)
    if (h->co == NULL || h->co->stack_base == NULL) {
        return;
    }
    size_t page = pengu_coro_page_size();
    uintptr_t start = (uintptr_t)h->co->stack_base;
    uintptr_t end = start + h->co->stack_size;
    uintptr_t a = (start + page - 1u) & ~((uintptr_t)page - 1u);
    uintptr_t b = end & ~((uintptr_t)page - 1u);
    if (b > a) {
#if defined(MADV_DONTNEED)
        (void)madvise((void *)a, (size_t)(b - a), MADV_DONTNEED);
#elif defined(MADV_FREE)
        (void)madvise((void *)a, (size_t)(b - a), MADV_FREE);
#endif
    }
#else
    (void)h;
#endif
}

static PenguCoro *pengu_coro_arena_grow(size_t slot_size) {
    size_t pages = pengu_coro_page_size();
    size_t arena = PENGU_CORO_ARENA_SIZE;
    if (arena < slot_size) {
        arena = pengu_coro_align_up(slot_size, pages);
    }
    unsigned char *base = (unsigned char *)pengu_coro_arena_map(arena);
    if (base == NULL) {
        return NULL;
    }
    size_t n = arena / slot_size;
    if (n == 0) {
        return NULL;
    }
    for (size_t i = 1; i < n; i++) {
        PenguCoro *h = (PenguCoro *)(base + i * slot_size);
        h->slot_size = slot_size;
        h->next_free = t_free_list;
        t_free_list = h;
        t_free_count++;
    }
    PenguCoro *first = (PenguCoro *)base;
    first->slot_size = slot_size;
    first->next_free = NULL;
    return first;
}

static PenguCoro *pengu_coro_slot_alloc(void) {
    size_t pages = pengu_coro_page_size();
    mco_desc d = mco_desc_init(NULL, PENGU_CORO_STACK_SIZE);
    d.storage_size = PENGU_CORO_STORAGE_SIZE;
    size_t slot_size = pengu_coro_align_up(sizeof(PenguCoro) + d.coro_size, pages);
    if (t_free_list != NULL) {
        PenguCoro *h = t_free_list;
        t_free_list = h->next_free;
        h->next_free = NULL;
        if (t_free_count > 0) {
            t_free_count--;
        }
        return h;
    }
    return pengu_coro_arena_grow(slot_size);
}

static void pengu_coro_slot_free(PenguCoro *h) {
    if (h->live_prev != NULL) {
        h->live_prev->live_next = h->live_next;
    } else {
        t_live = h->live_next;
    }
    if (h->live_next != NULL) {
        h->live_next->live_prev = h->live_prev;
    }
    h->live_prev = NULL;
    h->live_next = NULL;
    h->bt_n = 0;
    if (h->co != NULL) {
        mco_result r = mco_uninit(h->co);
        if (r != MCO_SUCCESS) {
            pengu_coro_panic("coroutine uninit failed");
        }
    }
    h->next_free = t_free_list;
    t_free_list = h;
    t_free_count++;
    if (t_free_count > (size_t)PENGU_CORO_POOL_MAX) {
        /* The slot stays reserved, but its physical pages can go back. */
        pengu_coro_release_pages(h);
    }
    h->co = NULL;
}

static void pengu_coro_canary_set(PenguCoro *h) {
    uint64_t v = PENGU_CORO_CANARY;
    memcpy(h->co->storage + h->co->storage_size - sizeof(v), &v, sizeof(v));
}

static void pengu_coro_canary_check(PenguCoro *h) {
    uint64_t v = 0;
    memcpy(&v, h->co->storage + h->co->storage_size - sizeof(v), sizeof(v));
    if (v != PENGU_CORO_CANARY) {
        pengu_coro_panic("coroutine stack overflow; reduce recursion or move the work to a thread");
    }
}

static void pengu_coro_entry(mco_coro *co) {
    PenguCoro *h = (PenguCoro *)mco_get_user_data(co);
    h->run(h->box);
    pengu_c_coro_box_free(h->box);
    h->box = NULL;
}

void *pengu_c_coro_box_new(size_t size) {
    void *p = calloc(1, size == 0 ? 1 : size);
    if (p == NULL) {
        pengu_coro_panic("out of memory creating a coroutine");
    }
    return p;
}

void pengu_c_coro_box_free(void *box) {
    free(box);
}

void *pengu_c_box_copy(const void *src, size_t size) {
    void *p = pengu_c_coro_box_new(size);
    if (src != NULL && size > 0) {
        memcpy(p, src, size);
    }
    return p;
}

void *pengu_c_coro_new(void (*run)(void *), void *box) {
    PenguCoro *h = pengu_coro_slot_alloc();
    if (h == NULL) {
        pengu_c_coro_box_free(box);
        pengu_coro_panic("out of memory creating a coroutine");
    }
    memset(h, 0, sizeof(*h));
    h->run = run;
    h->box = box;
    h->owner = pengu_coro_owner_token();
    h->co = (mco_coro *)((unsigned char *)h + pengu_coro_align_up(sizeof(PenguCoro), 16));
    mco_desc d = mco_desc_init(pengu_coro_entry, PENGU_CORO_STACK_SIZE);
    d.storage_size = PENGU_CORO_STORAGE_SIZE;
    d.user_data = h;
    if (mco_init(h->co, &d) != MCO_SUCCESS) {
        h->co = NULL;
        pengu_c_coro_box_free(box);
        pengu_coro_panic("out of memory creating a coroutine");
    }
    pengu_coro_canary_set(h);
    h->live_prev = NULL;
    h->live_next = t_live;
    if (t_live != NULL) {
        t_live->live_prev = h;
    }
    t_live = h;
    return h;
}

int pengu_c_coro_resume(void *handle) {
    PenguCoro *h = (PenguCoro *)handle;
    if (h == NULL) {
        pengu_coro_panic("resume on an empty coroutine handle");
    }
    if (h->owner != pengu_coro_owner_token()) {
        pengu_coro_panic("coroutine resumed from another thread");
    }
    mco_state st = mco_status(h->co);
    if (st == MCO_DEAD) {
        pengu_coro_panic("resume on a finished coroutine");
    }
    if (st != MCO_SUSPENDED) {
        pengu_coro_panic("resume on a coroutine that is not suspended");
    }
    pengu_coro_canary_check(h);
    mco_result r = mco_resume(h->co);
    if (r != MCO_SUCCESS) {
        pengu_coro_panic("coroutine resume failed");
    }
    pengu_coro_canary_check(h);
    return mco_status(h->co) == MCO_DEAD ? 2 : 0;
}

void pengu_c_coro_yield(void) {
    mco_coro *co = mco_running();
    if (co == NULL) {
        pengu_coro_panic("yield outside a coroutine");
    }
    PenguCoro *h = (PenguCoro *)mco_get_user_data(co);
    pengu_coro_canary_check(h);
#if !defined(_WIN32)
    if (pengu_coro_trace_enabled()) {
        /* Do not call backtrace(): the unwinder crashes on minicoro's
         * sentinel frame (0xdeaddeaddeaddead). Walk the frame-pointer chain
         * instead; debug builds keep frame pointers (-O0 default). */
        uintptr_t lo = (uintptr_t)h->co->stack_base;
        uintptr_t hi = lo + h->co->stack_size;
        uintptr_t *fp = (uintptr_t *)__builtin_frame_address(0);
        int n = 0;
        while (fp != NULL && n < (int)(sizeof(h->bt) / sizeof(h->bt[0]))) {
            uintptr_t addr = (uintptr_t)fp;
            if (addr < lo || addr + sizeof(uintptr_t) * 2 > hi) {
                break;
            }
            h->bt[n++] = (void *)fp[1];
            uintptr_t *next = (uintptr_t *)fp[0];
            if (next <= fp) {
                break;
            }
            fp = next;
        }
        h->bt_n = n;
    }
#endif
    mco_result r = mco_yield(co);
    if (r == MCO_STACK_OVERFLOW) {
        pengu_coro_panic("coroutine stack overflow; reduce recursion or move the work to a thread");
    }
    if (r != MCO_SUCCESS) {
        pengu_coro_panic("coroutine yield failed");
    }
    pengu_coro_canary_check(h);
}

int pengu_c_coro_status(void *handle) {
    PenguCoro *h = (PenguCoro *)handle;
    if (h == NULL) {
        pengu_coro_panic("status on an empty coroutine handle");
    }
    if (h->owner != pengu_coro_owner_token()) {
        pengu_coro_panic("status queried from another thread");
    }
    switch (mco_status(h->co)) {
    case MCO_DEAD:    return 2;
    case MCO_RUNNING: return 1;
    default:          return 0;
    }
}

void pengu_c_coro_free(void *handle) {
    PenguCoro *h = (PenguCoro *)handle;
    if (h == NULL) {
        pengu_coro_panic("free on an empty coroutine handle");
    }
    if (h->owner != pengu_coro_owner_token()) {
        pengu_coro_panic("coroutine freed from another thread");
    }
    mco_state st = mco_status(h->co);
    if (st == MCO_RUNNING) {
        pengu_coro_panic("free on a running coroutine");
    }
    if (st != MCO_DEAD) {
        pengu_coro_panic("free on a suspended coroutine; call abandon to discard it");
    }
    pengu_coro_canary_check(h);
    if (h->box != NULL) {
        pengu_c_coro_box_free(h->box);
        h->box = NULL;
    }
    pengu_coro_slot_free(h);
}

void *pengu_c_coro_current(void) {
    mco_coro *co = mco_running();
    if (co == NULL) return NULL;
    return mco_get_user_data(co);
}

void pengu_c_coro_abandon(void *handle) {
    PenguCoro *h = (PenguCoro *)handle;
    if (h == NULL) {
        pengu_coro_panic("abandon on an empty coroutine handle");
    }
    if (h->owner != pengu_coro_owner_token()) {
        pengu_coro_panic("coroutine freed from another thread");
    }
    if (mco_status(h->co) == MCO_RUNNING) {
        pengu_coro_panic("abandon on a running coroutine");
    }
    pengu_coro_canary_check(h);
    if (h->box != NULL) {
        pengu_c_coro_box_free(h->box);
        h->box = NULL;
    }
    pengu_coro_slot_free(h);
}

void pengu_c_coro_dump(void) {
    size_t n = 0;
    for (PenguCoro *h = t_live; h != NULL; h = h->live_next) {
        n++;
    }
    fprintf(stderr, "[PENGU] fibers: %zu live on this thread", n);
    if (!pengu_coro_trace_enabled()) {
        fprintf(stderr, " (set PENGU_FIBER_TRACE=1 to capture yield stacks)");
    }
    fprintf(stderr, "\n");
    for (PenguCoro *h = t_live; h != NULL; h = h->live_next) {
        const char *state = "suspended";
        if (h->co != NULL) {
            mco_state st = mco_status(h->co);
            if (st == MCO_RUNNING) state = "running";
            else if (st == MCO_DEAD) state = "finished";
        }
        fprintf(stderr, "  fiber %p state=%s owner=%llu stack=%p size=%zu\n",
                (void *)h, state, (unsigned long long)h->owner,
                h->co != NULL ? h->co->stack_base : NULL,
                h->co != NULL ? h->co->stack_size : (size_t)0);
#if !defined(_WIN32)
        if (h->bt_n > 0) {
            char **syms = backtrace_symbols(h->bt, h->bt_n);
            if (syms != NULL) {
                for (int i = 0; i < h->bt_n; i++) {
                    fprintf(stderr, "    #%d %s\n", i, syms[i]);
                }
                free(syms);
            } else {
                for (int i = 0; i < h->bt_n; i++) {
                    fprintf(stderr, "    #%d %p\n", i, h->bt[i]);
                }
            }
        }
#endif
    }
    fflush(stderr);
}
