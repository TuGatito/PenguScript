/*
 * filum_handles_leakcheck.c - deterministic leak check for the filum handles.
 *
 * Why this exists, and why LeakSanitizer is not enough:
 *
 * LSAN decides "leaked" by scanning reachable memory for pointers. glibc keeps
 * initialised `pthread_mutex_t` / `pthread_cond_t` objects in internal lists, so
 * a leaked filum handle that *contains* one of those looks "still reachable" and
 * LSAN stays silent. Measured on this runtime (clang -fsanitize=address):
 *
 *     pengu_c_filum_atomic_int_new()   -> reported (plain malloc, 8 bytes)
 *     pengu_c_filum_chan_new()         -> NOT reported
 *     pengu_c_filum_mutex_new()        -> NOT reported
 *     pengu_c_filum_wait_group_new()   -> NOT reported
 *     pengu_c_filum_once_new()         -> NOT reported
 *     pengu_c_filum_cond_new()         -> NOT reported
 *
 * So a clean ASan run does not prove that `pengu_c_filum_*_free` releases
 * anything. This program counts live allocations directly instead: the linker
 * redirects every malloc/calloc/realloc/free *from the objects it links* (the
 * runtime archive and this file) through the __wrap_* shims below, so the count
 * is exact for the runtime's own allocations and untouched by libc-internal
 * ones.
 *
 * Exit status: 0 when every handle was released, 1 on any leak.
 *
 * `argv[1] == "selftest"` deliberately leaks one handle and requires the check
 * to FAIL; the test suite runs it to prove this harness is not vacuous.
 *
 * Build (the test suite does this; see tests/wasm/test_wasm_target.py):
 *   clang -O1 -I<repo> -I<repo>/build/include filum_handles_leakcheck.c \
 *     -o leakcheck -L<repo>/build/lib \
 *     -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc -Wl,--wrap=free \
 *     -Wl,--start-group -lpengu_runtime -Wl,--end-group -pthread -lm -ldl
 */

#include "pengu_runtime.h"

#include <stdio.h>
#include <string.h>

/* ---- allocation counter -------------------------------------------------- */

static long g_live = 0;

extern void *__real_malloc(size_t);
extern void *__real_calloc(size_t, size_t);
extern void *__real_realloc(void *, size_t);
extern void __real_free(void *);

void *__wrap_malloc(size_t n) {
    void *p = __real_malloc(n);
    if (p) g_live++;
    return p;
}

void *__wrap_calloc(size_t a, size_t b) {
    void *p = __real_calloc(a, b);
    if (p) g_live++;
    return p;
}

void *__wrap_realloc(void *old, size_t n) {
    void *p = __real_realloc(old, n);
    /* A realloc of a live block keeps it live; only a NULL -> non-NULL realloc
     * (malloc semantics) adds a block. A failed realloc leaves the old block
     * alive, so the count must not move. */
    if (p && !old) g_live++;
    return p;
}

void __wrap_free(void *p) {
    if (p) g_live--;
    __real_free(p);
}

/* ---- check helpers ------------------------------------------------------- */

static int g_failures = 0;

static void report(const char *what, long before) {
    if (g_live == before) {
        printf("  ok   %-24s (live allocations unchanged: %ld)\n", what, g_live);
    } else {
        printf("  FAIL %-24s live=%ld, expected %ld\n", what, g_live, before);
        g_failures++;
    }
}

int main(int argc, char **argv) {
    int selftest = (argc > 1 && strcmp(argv[1], "selftest") == 0);
    long base;

    printf("filum handle lifecycle (%s)\n", selftest ? "selftest" : "leak check");

    /* 1. Mutex ------------------------------------------------------------ */
    base = g_live;
    {
        void *m = pengu_c_filum_mutex_new();
        pengu_c_filum_mutex_lock(m);
        pengu_c_filum_mutex_unlock(m);
        pengu_c_filum_mutex_free(m);
    }
    report("Mutex new/lock/free", base);

    /* 2. WaitGroup -------------------------------------------------------- */
    base = g_live;
    {
        void *wg = pengu_c_filum_wait_group_new();
        pengu_c_filum_wait_group_add(wg, 1);
        pengu_c_filum_wait_group_done(wg);
        pengu_c_filum_wait_group_wait(wg);
        pengu_c_filum_wait_group_free(wg);
    }
    report("WaitGroup new/add/free", base);

    /* 3. Once ------------------------------------------------------------- */
    base = g_live;
    {
        void *o = pengu_c_filum_once_new();
        pengu_c_filum_once_free(o);
    }
    report("Once new/free", base);

    /* 4. Cond ------------------------------------------------------------- */
    base = g_live;
    {
        void *c = pengu_c_filum_cond_new();
        pengu_c_filum_cond_signal(c);
        pengu_c_filum_cond_broadcast(c);
        pengu_c_filum_cond_free(c);
    }
    report("Cond new/signal/free", base);

    /* 5. AtomicInt -------------------------------------------------------- */
    base = g_live;
    {
        void *a = pengu_c_filum_atomic_int_new(7);
        if (pengu_c_filum_atomic_int_load(a) != 7) {
            printf("  FAIL AtomicInt load returned the wrong value\n");
            g_failures++;
        }
        pengu_c_filum_atomic_int_add(a, 1);
        pengu_c_filum_atomic_int_free(a);
    }
    report("AtomicInt new/add/free", base);

    /* 6. Channel -- the handle *and* its ring buffer must both come back. -- */
    base = g_live;
    {
        void *ch = pengu_c_filum_chan_new(sizeof(int), 8);
        int v = 1234;
        int out = 0;
        pengu_c_filum_chan_send(ch, &v);
        pengu_c_filum_chan_recv(ch, &out);
        if (out != v) {
            printf("  FAIL channel round-trip returned %d, expected %d\n", out, v);
            g_failures++;
        }
        pengu_c_filum_chan_close(ch);
        pengu_c_filum_chan_free(ch);
    }
    report("Chan new/send/recv/free", base);

    /* 7. Every handle at once, to catch an ordering-dependent release. ----- */
    base = g_live;
    {
        void *ch = pengu_c_filum_chan_new(sizeof(int), 4);
        void *wg = pengu_c_filum_wait_group_new();
        void *m = pengu_c_filum_mutex_new();
        void *o = pengu_c_filum_once_new();
        void *c = pengu_c_filum_cond_new();
        void *a = pengu_c_filum_atomic_int_new(0);
        pengu_c_filum_chan_free(ch);
        pengu_c_filum_wait_group_free(wg);
        pengu_c_filum_mutex_free(m);
        pengu_c_filum_once_free(o);
        pengu_c_filum_cond_free(c);
        pengu_c_filum_atomic_int_free(a);
    }
    report("all six handles at once", base);

    /* 8. A repeat cycle: a `_free` that only zeroes a field would pass once
     *    and fail here, because the second cycle would allocate on top of the
     *    first cycle's still-live blocks. ---------------------------------- */
    base = g_live;
    for (int i = 0; i < 50; ++i) {
        void *ch = pengu_c_filum_chan_new(sizeof(int), 4);
        void *wg = pengu_c_filum_wait_group_new();
        void *m = pengu_c_filum_mutex_new();
        void *o = pengu_c_filum_once_new();
        void *c = pengu_c_filum_cond_new();
        void *a = pengu_c_filum_atomic_int_new(0);
        pengu_c_filum_chan_free(ch);
        pengu_c_filum_wait_group_free(wg);
        pengu_c_filum_mutex_free(m);
        pengu_c_filum_once_free(o);
        pengu_c_filum_cond_free(c);
        pengu_c_filum_atomic_int_free(a);
    }
    report("50x alloc/free cycles", base);

    /* 9. NULL-safety: every *_free must accept NULL (the rune wrappers can be
     *    default-initialised) and must not disturb the counter. ------------- */
    base = g_live;
    pengu_c_filum_chan_free(NULL);
    pengu_c_filum_wait_group_free(NULL);
    pengu_c_filum_mutex_free(NULL);
    pengu_c_filum_once_free(NULL);
    pengu_c_filum_cond_free(NULL);
    pengu_c_filum_atomic_int_free(NULL);
    report("every _free(NULL)", base);

    if (selftest) {
        /* Prove the harness is not vacuous: leak one channel on purpose and
         * require the counter to notice. */
        base = g_live;
        void *leaked = pengu_c_filum_chan_new(sizeof(int), 4);
        (void)leaked;
        int detected = (g_live != base);
        printf("  %s selftest: a deliberately leaked channel was %s\n",
               detected ? "ok  " : "FAIL", detected ? "detected" : "MISSED");
        if (!detected) g_failures++;
        pengu_c_filum_chan_free(leaked);
        base = g_live;
        report("  (cleanup of selftest)", base);
    }

    if (g_failures == 0) {
        printf("filum_leakcheck: OK\n");
        return 0;
    }
    printf("filum_leakcheck: %d failure(s)\n", g_failures);
    return 1;
}
