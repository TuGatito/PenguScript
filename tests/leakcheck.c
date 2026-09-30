/* leakcheck.c — malloc-interposition leak detector with conservative
 * reachability marking (a valgrind substitute for environments without it).
 *
 * Every malloc/calloc/realloc is recorded in a hash table.  At process exit
 * the tracker conservatively marks every block reachable from:
 *   1. the stack (from the bottom recorded in a constructor),
 *   2. the main executable's writable data/bss,
 *   3. every loaded shared object's writable segments,
 *   4. the live blocks themselves (pointer fields).
 * Whatever stays unmarked counts as "definitely lost" — the same category
 * `valgrind --leak-check=full` reports as a real leak.
 *
 * Build:
 *   gcc -shared -fPIC -O1 -o leakcheck.so leakcheck.c -ldl
 * Use:
 *   LD_PRELOAD=./leakcheck.so ./program      # exits 42 when bytes are lost
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* ------------------------------------------------------------------ */
/* Real allocator hooks                                                */
/* ------------------------------------------------------------------ */

static void *(*real_malloc)(size_t) = NULL;
static void *(*real_calloc)(size_t, size_t) = NULL;
static void *(*real_realloc)(void *, size_t) = NULL;
static void (*real_free)(void *) = NULL;
static char *(*real_strdup)(const char *) = NULL;

extern void *__libc_malloc(size_t);
extern void *__libc_calloc(size_t, size_t);
extern void *__libc_realloc(void *, size_t);
extern void __libc_free(void *);

#define MAGIC 0xDEADBEEFUL

typedef struct blk {
    size_t size;
    unsigned long magic;
    struct blk *next;
    int mark;
} blk_t;

#define NBUCKETS 65536u
static blk_t **buckets = NULL;

static long total_allocs = 0;
static long live_count = 0;
static long long live_bytes = 0;

static void init_real(void) {
    if (real_malloc) return;
    real_malloc = (void *(*)(size_t))__libc_malloc;
    real_calloc = (void *(*)(size_t, size_t))__libc_calloc;
    real_realloc = (void *(*)(void *, size_t))__libc_realloc;
    real_free = (void (*)(void *))__libc_free;
    {
        void *m = dlsym(RTLD_NEXT, "malloc");
        void *c = dlsym(RTLD_NEXT, "calloc");
        void *r = dlsym(RTLD_NEXT, "realloc");
        void *f = dlsym(RTLD_NEXT, "free");
        void *s = dlsym(RTLD_NEXT, "strdup");
        if (m) real_malloc = (void *(*)(size_t))m;
        if (c) real_calloc = (void *(*)(size_t, size_t))c;
        if (r) real_realloc = (void *(*)(void *, size_t))r;
        if (f) real_free = (void (*)(void *))f;
        if (s) real_strdup = (char *(*)(const char *))s;
    }
    if (!buckets) {
        buckets = (blk_t **)real_calloc(NBUCKETS, sizeof(blk_t *));
    }
}

static size_t hash_ptr(void *p) {
    return (size_t)(((uintptr_t)p >> 4) ^ ((uintptr_t)p >> 17)) & (NBUCKETS - 1);
}

static void track(blk_t *h) {
    size_t i = hash_ptr(h);
    h->next = buckets[i];
    h->mark = 0;
    buckets[i] = h;
    live_count++;
    live_bytes += (long long)h->size;
    total_allocs++;
}

static void untrack(blk_t *h) {
    size_t i = hash_ptr(h);
    blk_t **pp = &buckets[i];
    while (*pp) {
        if (*pp == h) {
            *pp = h->next;
            live_count--;
            live_bytes -= (long long)h->size;
            h->magic = 0;
            return;
        }
        pp = &(*pp)->next;
    }
    h->magic = 0;
}

/* ------------------------------------------------------------------ */
/* Allocator entry points                                              */
/* ------------------------------------------------------------------ */

void *malloc(size_t size) {
    init_real();
    blk_t *h = (blk_t *)real_malloc(size + sizeof(blk_t));
    if (!h) return NULL;
    h->size = size;
    h->magic = MAGIC;
    track(h);
    return (char *)h + sizeof(blk_t);
}

void *calloc(size_t n, size_t size) {
    init_real();
    size_t total = n * size;
    blk_t *h = (blk_t *)real_malloc(total + sizeof(blk_t));
    if (!h) return NULL;
    memset((char *)h + sizeof(blk_t), 0, total);
    h->size = total;
    h->magic = MAGIC;
    track(h);
    return (char *)h + sizeof(blk_t);
}

void free(void *ptr) {
    init_real();
    if (!ptr) { real_free(ptr); return; }
    blk_t *h = (blk_t *)((char *)ptr - sizeof(blk_t));
    if (h->magic == MAGIC) {
        untrack(h);
        real_free(h);
    } else {
        real_free(ptr);
    }
}

void *realloc(void *ptr, size_t size) {
    init_real();
    if (!ptr) return malloc(size);
    blk_t *h = (blk_t *)((char *)ptr - sizeof(blk_t));
    if (h->magic != MAGIC) return real_realloc(ptr, size);
    untrack(h);
    blk_t *nh = (blk_t *)real_realloc(h, size + sizeof(blk_t));
    if (!nh) {
        /* The original block survives a failed realloc: re-track it. */
        h->magic = MAGIC;
        track(h);
        return NULL;
    }
    nh->size = size;
    nh->magic = MAGIC;
    track(nh);
    return (char *)nh + sizeof(blk_t);
}

char *strdup(const char *s) {
    init_real();
    size_t n = strlen(s) + 1;
    char *p = (char *)malloc(n);
    if (p) memcpy(p, s, n);
    return p;
}

/* ------------------------------------------------------------------ */
/* Conservative reachability                                           */
/* ------------------------------------------------------------------ */

static blk_t **worklist = NULL;
static size_t work_head = 0, work_tail = 0, work_cap = 0;

/* Live blocks sorted by user pointer, built once before marking so that
 * ``find_block`` can binary-search interior pointers. */
static blk_t **sorted_blocks = NULL;
static size_t sorted_count = 0;

static int cmp_block(const void *a, const void *b) {
    uintptr_t pa = (uintptr_t)(*(blk_t *const *)a) + sizeof(blk_t);
    uintptr_t pb = (uintptr_t)(*(blk_t *const *)b) + sizeof(blk_t);
    return (pa > pb) - (pa < pb);
}

static void push_mark(blk_t *h) {
    if (h->mark) return;
    h->mark = 1;
    if (work_tail == work_cap) {
        size_t cap = work_cap ? work_cap * 2 : 4096;
        blk_t **nw = (blk_t **)real_realloc(worklist, cap * sizeof(blk_t *));
        if (!nw) return;
        worklist = nw;
        work_cap = cap;
    }
    worklist[work_tail++] = h;
}

static blk_t *find_block(uintptr_t addr) {
    size_t lo = 0, hi = sorted_count;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        blk_t *h = sorted_blocks[mid];
        uintptr_t start = (uintptr_t)h + sizeof(blk_t);
        if (addr < start) {
            hi = mid;
        } else if (addr >= start + h->size) {
            lo = mid + 1;
        } else {
            return h;
        }
    }
    return NULL;
}

static void scan_range(const void *lo, const void *hi) {
    if ((uintptr_t)lo > (uintptr_t)hi) {
        const void *t = lo; lo = hi; hi = t;
    }
    const uintptr_t *p = (const uintptr_t *)(((uintptr_t)lo + sizeof(void *) - 1)
                                             & ~(uintptr_t)(sizeof(void *) - 1));
    for (; (uintptr_t)p + sizeof(void *) <= (uintptr_t)hi; ++p) {
        uintptr_t v = *p;
        if (!v) continue;
        blk_t *h = find_block(v);
        if (h) push_mark(h);
    }
}

/* ------------------------------------------------------------------ */
/* Roots: thread stack + every loaded object's writable segments       */
/* ------------------------------------------------------------------ */

typedef struct {
    uintptr_t lo, hi;
} range_t;

static range_t root_ranges[64];
static size_t root_count = 0;

static void add_root(uintptr_t lo, uintptr_t hi) {
    if (lo >= hi || root_count >= 64) return;
    root_ranges[root_count].lo = lo;
    root_ranges[root_count].hi = hi;
    root_count++;
}

static int collect_phdr(struct dl_phdr_info *info, size_t size, void *data) {
    (void)size; (void)data;
    for (int i = 0; i < info->dlpi_phnum; ++i) {
        const ElfW(Phdr) *ph = &info->dlpi_phdr[i];
        if (ph->p_type != PT_LOAD) continue;
        if (!(ph->p_flags & PF_W)) continue;
        add_root(info->dlpi_addr + ph->p_vaddr,
                 info->dlpi_addr + ph->p_vaddr + ph->p_memsz);
    }
    return 0;
}

static void collect_roots(void) {
    root_count = 0;
    dl_iterate_phdr(collect_phdr, NULL);
#ifdef __GLIBC__
    {
        pthread_attr_t attr;
        if (pthread_getattr_np(pthread_self(), &attr) == 0) {
            void *base = NULL;
            size_t sz = 0;
            if (pthread_attr_getstack(&attr, &base, &sz) == 0) {
                add_root((uintptr_t)base, (uintptr_t)base + sz);
            }
            pthread_attr_destroy(&attr);
        }
    }
#endif
}

__attribute__((destructor))
static void leak_report(void) {
    if (live_count == 0) {
        fprintf(stderr, "[leakcheck] OK: 0 live allocations (%ld total)\n", total_allocs);
        return;
    }
    collect_roots();

    /* Build the sorted index of live blocks before the transitive closure. */
    sorted_blocks = (blk_t **)real_malloc((size_t)(live_count > 0 ? live_count : 1) * sizeof(blk_t *));
    for (size_t i = 0; i < NBUCKETS; ++i) {
        for (blk_t *h = buckets[i]; h; h = h->next) {
            if (sorted_count < (size_t)live_count) sorted_blocks[sorted_count++] = h;
        }
    }
    qsort(sorted_blocks, sorted_count, sizeof(blk_t *), cmp_block);

    /* Scan the roots, then close transitively over the live blocks. */
    for (size_t i = 0; i < root_count; ++i) {
        scan_range((const void *)root_ranges[i].lo, (const void *)root_ranges[i].hi);
    }

    /* Transitive closure through pointers stored inside live blocks. */
    while (work_head < work_tail) {
        blk_t *h = worklist[work_head++];
        scan_range((char *)h + sizeof(blk_t), (char *)h + sizeof(blk_t) + h->size);
    }

    long lost_count = 0;
    long long lost_bytes = 0;
    long sample = 0;
    for (size_t i = 0; i < NBUCKETS; ++i) {
        for (blk_t *h = buckets[i]; h; h = h->next) {
            if (!h->mark) {
                lost_count++;
                lost_bytes += (long long)h->size;
                if (sample < 10) {
                    fprintf(stderr, "[leakcheck]   lost %zu bytes at %p\n",
                            h->size, (void *)((char *)h + sizeof(blk_t)));
                    sample++;
                }
            }
        }
    }
    if (lost_count == 0) {
        fprintf(stderr, "[leakcheck] OK: 0 lost allocations (live=%ld, total=%ld)\n",
                live_count, total_allocs);
        return;
    }
    fprintf(stderr, "[leakcheck] LEAK: %ld lost allocations, %lld bytes "
                    "(live=%ld, total=%ld)\n",
            lost_count, lost_bytes, live_count, total_allocs);
    _exit(42);
}
