/**
 * @file pengu_runtime_organized.h
 * @brief PenguScript Unified C Runtime Library.
 *
 * The runtime ships with the compiler and carries no version of its own: the
 * language/toolchain version lives in `VERSION` and is exposed by
 * `pengu_version.py`.
 *
 * Provides core memory management, primitive wrappers, standard data structures
 * (strings, slices, lists, hash maps, optionals, results), and standard library
 * bindings (I/O, logging, math, time, random, OS rites, paths, filesystem,
 * JSON/Base64, CSV/TSV, concurrency, regex, XML/HTML, compression/hashing, and networking).
 *
 * `string` storage is backed by SDS (Simple Dynamic Strings), vendored in
 * `std_c/sds` under the BSD-2-Clause license; see THIRD_PARTY.md.
 *
 * @note Designed for C11/C99 compatibility with manual memory management (banish/defer).
 */

#ifndef PENGU_RUNTIME_ORGANIZED_H
#define PENGU_RUNTIME_ORGANIZED_H

/*
 * The runtime is C11: it uses `sscanf`, `getenv`, `fopen` and friends on
 * purpose, because they are standard C and available everywhere (the `*_s`
 * variants are MSVC-only).  Microsoft's CRT marks them deprecated with C4996,
 * which clang reports as `-Wdeprecated-declarations`; under the `-Werror` the
 * test suite and CI use, that turns a valid bundle into a build failure on
 * Windows (clang.exe targets the MSVC CRT there even when it is not used as
 * `clang-cl`).  The switch has to be defined before the first CRT header, so it
 * lives at the top of this header -- the first include of every generated
 * bundle -- and not in the build flags: a bundle compiled by hand
 * (`clang -c bundle.c`) must not warn either.  `_WIN32` catches every Windows
 * toolchain; MinGW and POSIX toolchains simply ignore the macro.
 */
#if defined(_WIN32) && !defined(_CRT_SECURE_NO_WARNINGS)
#define _CRT_SECURE_NO_WARNINGS 1
#endif

/* =========================================================================
 * ABI v3 — Convenient Containers backend
 *
 * PENGU_ABI_VERSION is bumped only by a breaking change to any layout below.
 * The generated C (`bundle.c`) and every prebuilt `libpengu_*.a` must agree on
 * this number; a mismatch is a link-time/UB hazard.
 *
 * v2 (manual memory management): `PenguList` and `PenguMap` dropped their
 * element cleanup/clone callbacks.  A container never clones on store and never
 * recurses on release: storing an element is a `memcpy`, and releasing a
 * container frees only the container's own buffer.
 *
 * The layouts below are the *real* ones shipped by the runtime.  Sizes are for
 * 64-bit targets (LP64 and LLP64): pointers/size_t/function pointers are 8
 * bytes and `int` is 4, so the numbers are identical on Linux/macOS x86_64 and
 * on Windows x64.  32-bit targets differ and are not covered by ABI v3.
 *
 *   PenguString  { char *data; int len; int32_t is_owned; }        size 16, align 8
 *                offsets: data=0 len=8 is_owned=12
 *   PenguSlice   { void *data; int len; size_t elem_size; }        size 24, align 8
 *                offsets: data=0 len=8 elem_size=16
 *   PenguList    { void *data; int len; int cap; size_t elem_size; }
 *                size 24, align 8
 *                offsets: data=0 len=8 cap=12 elem_size=16
 *   PenguMap     { void *state; int len; int cap;
 *                  size_t key_size; size_t val_size; }
 *                size 32, align 8
 *                offsets: state=0 len=8 cap=12 key_size=16 val_size=24
 *   PenguMaybe   { bool is_present; void *value; }                 size 16, align 8
 *                offsets: is_present=0 value=8
 *   PenguResult  { bool is_ok; void *ok_val; void *err_val; }      size 24, align 8
 *                offsets: is_ok=0 ok_val=8 err_val=16
 *   PenguRange   { int64_t start; int64_t end; }                   size 16, align 8
 *                offsets: start=0 end=8
 *
 * `tests/abi/test_abi_layout.c` asserts these values at runtime on every
 * platform the suite runs on; keep it in sync if a layout ever changes.
 *
 * v3 (Convenient Containers): `PenguList` and `PenguMap` keep their size and
 * alignment, but their first field now refers to a CC-backed allocation:
 * `PenguList.data` points into a `cc_vec` block (the CC header lives before it)
 * and `PenguMap.state` is an opaque `PenguMapState*` (a `cc_map` handle plus
 * layout/hash metadata). C extensions must not `free()` those fields or walk
 * `PenguMap` entries directly; use the runtime accessors.
 *
 * ABI v2 preserved the SDS migration: `PenguString` keeps the same 16-byte
 * layout, and an owned payload (`is_owned == 1`) is an SDS allocation.
 * ========================================================================= */
#define PENGU_ABI_VERSION 3

/*
 * Phase 3 item 3.5. Defined in `pengu_runtime.c` -- i.e. it exists as an
 * object-file symbol inside `libpengu_runtime.a`, never as an inline function in
 * this header. A consumer that calls it therefore fails to LINK when the archive
 * it is given predates this symbol, instead of silently reinterpreting struct
 * fields at the wrong offsets.
 *
 * This complements the `_Static_assert(PENGU_ABI_VERSION == N)` the codegen also
 * emits: that one compares the codegen's expectation against this header, while
 * this symbol compares a bundle against the *archive*. Neither is sufficient
 * alone.
 *
 * Note the generated bundle does *not* reference this symbol unconditionally:
 * the CLI only adds `-lpengu_runtime` when the project asks for it, so a fresh
 * project builds header-only and a mandatory reference would break it. Making
 * the reference mandatory is Phase 4 work (see docs/ABI.md).
 */
int pengu_abi_version(void);


/* =========================================================================
 * Feature-test macros
 *
 * glibc/musl hide POSIX declarations (clock_gettime, nanosleep, timespec,
 * setenv, gethostname, lstat, realpath, localtime_r, ...) unless a feature
 * macro is defined; with -std=c99/c11 they would otherwise be missing and
 * modern compilers reject their implicit use. Must precede any libc header.
 * ========================================================================= */
#if !defined(_WIN32) && !defined(_WIN64)
#if !defined(_POSIX_C_SOURCE)
#define _POSIX_C_SOURCE 200809L
#endif
#if !defined(_DEFAULT_SOURCE)
#define _DEFAULT_SOURCE 1
#endif
/*
 * Darwin: `_POSIX_C_SOURCE` puts the SDK's headers in strict POSIX mode, and
 * that hides the non-standard extensions the runtime needs -- most visibly
 * `pthread_threadid_np()`, which <pthread.h> only declares when
 * `_DARWIN_C_SOURCE` is set.  Defining it opts back into the full Darwin
 * namespace while keeping POSIX visible; without it Apple clang rejects the
 * build with "call to undeclared function 'pthread_threadid_np'".
 */
#if defined(__APPLE__) && !defined(_DARWIN_C_SOURCE)
#define _DARWIN_C_SOURCE 1
#endif
#endif

/* =========================================================================
 * Subsystem feature gates (PenguScript 2.0 binary-size reduction)
 *
 * Every subsystem whose *implementation* depends on a native library is gated
 * by a macro. Setting one to 0 compiles its declarations and `static inline`
 * helpers out of the translation unit:
 *
 *   PENGU_ENABLE_THREADS -> pthread / Win32 threads (std.filum)
 *
 * Bindings to external C libraries (PCRE2, libxml2, mbedtls, zlib, libcurl,
 * libmicrohttpd, raylib, sqlite3, ...) no longer live in this runtime: they
 * ship as satellite repositories installed with `pengu add`. See
 * docs/EXTERNAL_MODULES.md.
 *
 * The default is conservative: a plain C consumer that includes this header
 * gets the whole API. The generated `bundle.c` defines the gate to 0 or 1
 * before this include, from the `std.*` modules the program imports, and
 * `pengu_project.py` links only the matching native archives.
 *
 * The archive `libpengu_runtime.a` is always compiled with the gate at its
 * default of 1: its symbols have to exist for the linker to choose from.
 *
 * No macro gates the core (strings, slices, lists, maps, maybe/result, memory,
 * print/input, filesystem, time, math): it has no external dependency beyond
 * libc and libm.
 *
 * A gate that hides a declaration while `pengu_runtime.c` still defines the
 * function is safe. The reverse is not, which is why declarations and
 * definitions are gated together.
 * ========================================================================= */
#ifndef PENGU_ENABLE_THREADS
#define PENGU_ENABLE_THREADS 1
#endif

/* =========================================================================
 * 1. Standard C & Platform Headers
 * ========================================================================= */
#include <ctype.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>

/* SDS (Simple Dynamic Strings) backs every owned `PenguString`.  The vendored
 * copy lives in `std_c/sds`; `tools/build_runtime.sh` compiles it into
 * `libpengu_runtime.a` and copies `sds.h` next to this header, so generated
 * bundles see it through the same `-I` the runtime uses.
 *
 * MSVC has no POSIX `ssize_t`, which `sds.h` uses in two declarations.  Define
 * it before the include, guarded exactly like the CRT's own typedef. */
#if defined(_MSC_VER) && !defined(_SSIZE_T_DEFINED) && !defined(__MINGW32__)
typedef intptr_t ssize_t;
#define _SSIZE_T_DEFINED 1
#endif
#include "sds.h"

#if defined(_WIN32) || defined(_WIN64)
#define PENGU_WINDOWS 1
#define WIN32_LEAN_AND_MEAN
#define NOGDI
#define NOUSER
#define NOMINMAX
#include <windows.h>
#include <process.h>
#include <direct.h>
#include <io.h>
#include <sys/utime.h>

/* MSVC (and clang in MS mode) has no POSIX `S_ISREG`/`S_ISDIR`; MinGW does.
 * Define them from the CRT's `_S_IFMT` bits so this header compiles with every
 * Windows toolchain, not only the MinGW one the release links. */
#if !defined(S_ISREG) || !defined(S_ISDIR)
#ifndef _S_IFMT
#define _S_IFMT 0xF000
#endif
#ifndef _S_IFREG
#define _S_IFREG 0x8000
#endif
#ifndef _S_IFDIR
#define _S_IFDIR 0x4000
#endif
#ifndef S_ISREG
#define S_ISREG(m) (((m) & _S_IFMT) == _S_IFREG)
#endif
#ifndef S_ISDIR
#define S_ISDIR(m) (((m) & _S_IFMT) == _S_IFDIR)
#endif
#endif

/* The legacy Windows headers define 16-bit-era macros that are ordinary
 * identifiers in generated user code: `pascal` is `__stdcall`, `near`/`far`/
 * `huge`/`small` are memory models, and `interface` is COM's keyword.  Built
 * PenguScript code is allowed to name a variable `pascal`, so drop them once
 * the system headers have been read; nothing in this runtime uses them. */
#ifdef pascal
#undef pascal
#endif
#ifdef _pascal
#undef _pascal
#endif
#ifdef cdecl
#undef cdecl
#endif
#ifdef _cdecl
#undef _cdecl
#endif
#ifdef stdcall
#undef stdcall
#endif
#ifdef _stdcall
#undef _stdcall
#endif
#ifdef fastcall
#undef fastcall
#endif
#ifdef _fastcall
#undef _fastcall
#endif
#ifdef near
#undef near
#endif
#ifdef far
#undef far
#endif
#ifdef huge
#undef huge
#endif
#ifdef small
#undef small
#endif
#ifdef interface
#undef interface
#endif
#else
#define PENGU_WINDOWS 0
#include <unistd.h>
#include <sys/time.h>
#include <dirent.h>
#include <utime.h>
/* Phase 3 item 3.8: the crash-handler install must happen exactly once across
 * threads. `pthread_once` is the portable POSIX primitive for that and the POSIX
 * runtime already links pthreads (see `pengu_parser/pengu_runtime.c`). */
#include <pthread.h>
#endif

/* =========================================================================
 * WebAssembly / Emscripten
 *
 * `emcc` defines neither `_WIN32` nor `__linux__`, so the POSIX branch above is
 * already the correct one: the Emscripten sysroot provides <pthread.h>,
 * <dirent.h>, <unistd.h>, <sys/stat.h>, clock_gettime, nanosleep, realpath and
 * the BSD socket headers.  This macro exists only to mark the few places where
 * the WebAssembly sandbox cannot honour the POSIX contract at all -- today that
 * is process spawning (`pengu_c_exec` / `pengu_c_spawn`), which has no process
 * to spawn in a browser and must not silently call `system()`.
 *
 * Threading is real but opt-in: `-pthread` turns `pthread_create` into a Web
 * Worker backed by `SharedArrayBuffer`, and without it Emscripten emulates the
 * pthread calls as no-ops.  `pengu_project.py` therefore adds `-pthread` to a
 * wasm build exactly when the program imports `std.filum`.
 *
 * `PENGU_EMSCRIPTEN` is always 0 on Windows: emcc never defines `_WIN32`.
 * ========================================================================= */
#if defined(__EMSCRIPTEN__)
#define PENGU_EMSCRIPTEN 1
#else
#define PENGU_EMSCRIPTEN 0
#endif

#ifdef __cplusplus
extern "C"
{
#endif

  /* =========================================================================
   * 2. Primitive Type Aliases
   * ========================================================================= */

  /** @brief 32-bit signed integer. */
  typedef int32_t pengu_i32;

  /** @brief 64-bit signed integer. */
  typedef int64_t pengu_i64;

  /** @brief 32-bit single-precision floating point. */
  typedef float pengu_f32;

  /** @brief 64-bit double-precision floating point. */
  typedef double pengu_f64;

  /** @brief Boolean logical type. */
  typedef bool pengu_bool;

  /* =========================================================================
   * 3. Core Memory Management (Sigil & Banish)
   * ========================================================================= */

  /**
   * @brief Allocates zero-initialized heap memory for a reference (sigil).
   * @param size Number of bytes to allocate.
   * @return Pointer to zero-initialized allocated memory block, or NULL on failure.
   */
  static inline void *pengu_sigil_alloc(size_t size)
  {
    void *ptr = malloc(size);
    if (!ptr && size > 0)
    {
#if PENGU_OOM_ABORT
      fprintf(stderr, "\n[PENGU] out of memory: failed to allocate %zu byte(s)\n", size);
      fflush(stderr);
      abort();
#endif
      return NULL;
    }
    if (ptr)
    {
      memset(ptr, 0, size);
    }
    return ptr;
  }

  /**
   * @brief Deallocates heap memory associated with a pointer.
   * @param ptr Pointer to memory to free.
   */
  static inline void pengu_banish(void *ptr)
  {
    if (ptr)
    {
      free(ptr);
    }
  }

  /* -------------------------------------------------------------------------
   * `std.memoria` support (Phase 5).
   *
   * Manual heap primitives behind std/memoria.pengu. The compiler
   * monomorphizes the `shard T` wrappers, so every size is resolved at compile
   * time and these helpers stay byte-level and type-agnostic.
   *
   * Declarations only: the definitions live in pengu_runtime.c (core object)
   * so a generated bundle links them exactly like the FFI bridges. They are
   * purely additive and touch no struct layout, so PENGU_ABI_VERSION stays 2.
   * The aborting variants honour PENGU_OOM_ABORT exactly like pengu_sigil_alloc.
   * ------------------------------------------------------------------------- */

  /**
   * @brief Allocates a zero-initialized block of `n` bytes.
   * @param n Number of bytes to allocate.
   * @return Pointer to the zero-initialized block, or NULL when the OOM policy
   *         is not `abort` and the allocation failed.
   */
  void *pengu_memoria_alloc(size_t n);

  /**
   * @brief Allocates a zero-initialized array of `count` elements.
   * @param count Number of elements (precondition: > 0).
   * @param elem_size Size of one element in bytes.
   * @return Pointer to the zero-initialized block, or NULL under the
   *         non-aborting OOM policy.
   */
  void *pengu_memoria_alloc_array(size_t count, size_t elem_size);

  /**
   * @brief Like pengu_memoria_alloc but never aborts: returns NULL on OOM.
   */
  void *pengu_memoria_try_alloc(size_t n);

  /**
   * @brief Like pengu_memoria_alloc_array but never aborts: returns NULL on OOM.
   */
  void *pengu_memoria_try_alloc_array(size_t count, size_t elem_size);

  /**
   * @brief Resizes a block to `new_n` elements, preserving min(old_n, new_n).
   *
   * New bytes are zeroed. A NULL `p` is a fresh, zeroed allocation. Aborts on
   * OOM under the default policy. After a successful move the old pointer is
   * invalid; the caller must use the return value only.
   */
  void *pengu_memoria_resize(void *p, size_t old_n, size_t new_n, size_t elem_size);

  /**
   * @brief Like pengu_memoria_resize but never aborts: returns NULL on OOM.
   *
   * When `p` was non-NULL and the resize fails, the original block stays valid
   * and remains owned by the caller.
   */
  void *pengu_memoria_try_resize(void *p, size_t old_n, size_t new_n, size_t elem_size);

  /**
   * @brief Byte-by-byte swap of `elem_size` bytes at `a` and `b`.
   *        NULL-safe; a == b is a no-op.
   */
  void pengu_memoria_swap(void *a, void *b, size_t elem_size);

  /**
   * @brief Fills `count` elements at `dst` with a copy of the `elem_size`-byte
   *        pattern at `value`.
   *
   * Not `memset`: the pattern may be wider than one byte (a float, a pointer,
   * a rune). NULL-safe; a zero `elem_size` is a no-op.
   */
  void pengu_memoria_fill(void *dst, const void *value, size_t count, size_t elem_size);

  /* =========================================================================
   * 4. Error Handling & Optionals (Maybe & Result)
   * ========================================================================= */

  /**
   * @brief Optional union structure representing presence of a value or none.
   */
  typedef struct
  {
    bool is_present;
    void *value;
  } PenguMaybe;

  /**
   * @brief Constructs a Maybe container holding a present value.
   * @param value Pointer to the payload value.
   * @return PenguMaybe with is_present set to true.
   */
  static inline PenguMaybe pengu_maybe_some(void *value)
  {
    PenguMaybe m;
    m.is_present = true;
    m.value = value;
    return m;
  }

  /**
   * @brief Constructs an empty Maybe container (None).
   * @return PenguMaybe with is_present set to false and value set to NULL.
   */
  static inline PenguMaybe pengu_maybe_none(void)
  {
    PenguMaybe m;
    m.is_present = false;
    m.value = NULL;
    return m;
  }

  /**
   * @brief Checks if a Maybe structure contains a valid value.
   * @param m Pointer to const PenguMaybe.
   * @return True if present, false otherwise.
   */
  static inline bool pengu_maybe_is_present(const PenguMaybe *m)
  {
    return m ? m->is_present : false;
  }

  /**
   * @brief Releases the *box* of a Maybe value (never its payload).
   *
   * The payload cleanup is type-specific, so the generated code releases it
   * first (e.g. 'pengu_banish_string((PenguString *)m.value)') and then calls
   * this helper to free the allocation itself.  'some' deep-copies an owning
   * payload into the box (see OWNERSHIP notes in AUDIT_RESPONSE.md), so the
   * pair of calls owns everything the box refers to.
   *
   * @param m Pointer to the Maybe (may be NULL).
   */
  static inline void pengu_banish_maybe(PenguMaybe *m)
  {
    if (!m)
    {
      return;
    }
    if (m->is_present && m->value)
    {
      free(m->value);
    }
    m->value = NULL;
    m->is_present = false;
  }

  /**
   * @brief Container representing either a success value or an error value.
   */
  typedef struct
  {
    bool is_ok;
    void *ok_val;
    void *err_val;
  } PenguResult;

  /**
   * @brief Constructs a successful Result container.
   * @param ok_val Pointer to the success value.
   * @return PenguResult with is_ok set to true.
   */
  static inline PenguResult pengu_result_ok(void *ok_val)
  {
    PenguResult r;
    r.is_ok = true;
    r.ok_val = ok_val;
    r.err_val = NULL;
    return r;
  }

  /**
   * @brief Constructs an error Result container.
   * @param err_val Pointer to the error value.
   * @return PenguResult with is_ok set to false.
   */
  static inline PenguResult pengu_result_err(void *err_val)
  {
    PenguResult r;
    r.is_ok = false;
    r.ok_val = NULL;
    r.err_val = err_val;
    return r;
  }

  /**
   * @brief Checks if a Result represents a successful outcome.
   * @param r Pointer to const PenguResult.
   * @return True if ok, false if error.
   */
  static inline bool pengu_result_is_ok(const PenguResult *r)
  {
    return r ? r->is_ok : false;
  }

  /**
   * @brief Releases the *box* of a Result value (never its payloads).
   *
   * Like pengu_banish_maybe: the generated code releases the payload it owns
   * and then frees the allocation.  Only the active side (ok_val or err_val)
   * is non-NULL by construction.
   *
   * @param r Pointer to the Result (may be NULL).
   */
  static inline void pengu_banish_result(PenguResult *r)
  {
    if (!r)
    {
      return;
    }
    if (r->is_ok)
    {
      if (r->ok_val)
      {
        free(r->ok_val);
      }
      r->ok_val = NULL;
    }
    else
    {
      if (r->err_val)
      {
        free(r->err_val);
      }
      r->err_val = NULL;
    }
  }

  /* =========================================================================
   * Debug: runtime frame trace & crash handler
   *
   * A small, always-on thread-local frame stack. Every PenguScript weave /
   * enchanting method / lambda pushes a frame on entry and pops it before
   * returning. On SIGSEGV / SIGABRT the handler dumps the stack so the user
   * sees the chain of .pengu functions that led to the crash, with the
   * file:line recorded at push time (already resolved by codegen's #line
   * markers, so no DWARF is needed).
   * ========================================================================= */

#ifndef PENGU_FRAME_TRACE
#define PENGU_FRAME_TRACE 1
#endif

/* Bounds checking is independent from the crash-handler frame trace: a release
 * build can keep the frame trace but compile the per-index checks out (the
 * code generator also stops emitting `pengu_assert_bounds` when not in debug
 * mode, and passes -DPENGU_BOUNDS_CHECK=0). */
/* Out-of-memory policy (roadmap 5.7).
 *
 * "abort"  : print a diagnostic and abort() — the default, because continuing
 *            with a NULL allocation corrupts memory or crashes far from the
 *            cause.
 * "silent" : return NULL and let the caller decide (historical behaviour).
 * "none"   : skip the diagnostic but still return NULL (alias of silent without
 *            the message); useful when embedding.
 *
 * Override at compile time with -DPENGU_OOM_POLICY_ABORT=0 (and friends).
 */
#ifndef PENGU_OOM_ABORT
#define PENGU_OOM_ABORT 1
#endif

/* Integer-overflow checks are opt-out via --release-unsafe (roadmap 5.1). */
#ifndef PENGU_OVERFLOW_CHECK
#define PENGU_OVERFLOW_CHECK 1
#endif

#ifndef PENGU_BOUNDS_CHECK
#define PENGU_BOUNDS_CHECK 1
#endif

#ifndef PENGU_MAX_FRAMES
#define PENGU_MAX_FRAMES 64
#endif

  typedef struct
  {
    const char *func;   /* function name, e.g. "pengu_main" */
    const char *file;   /* .pengu file, e.g. "src/main.pengu" */
    int         line;   /* .pengu source line of the function declaration */
  } PenguFrame;

/* =========================================================================
 * Async-signal-safe formatting primitives (Phase 3 item 3.7)
 *
 * The crash handler runs in signal context, where almost nothing is legal:
 * POSIX lists only a few dozen async-signal-safe functions, and `snprintf` is
 * not among them (it can take a locale/stdio lock, and some libcs allocate
 * internally). The handler used to build its dump with `snprintf` while
 * LANGUAGE.md and CHANGELOG.md claimed the handler was async-signal-safe --
 * the code and the docs disagreed.
 *
 * These helpers do nothing but pointer arithmetic and integer division, so the
 * whole crash path depends on `write(2)`/`_write` and `_exit()` alone. They live
 * outside the PENGU_FRAME_TRACE guard because pengu_bounds_panic (always
 * defined) uses them too.
 * ========================================================================= */

  typedef struct
  {
    char  *buf;   /* caller-provided storage, never allocated here */
    size_t cap;   /* its capacity in bytes (including the NUL) */
    size_t len;   /* bytes written so far, excluding the NUL */
  } PenguSigBuffer;

  static inline void pengu_sig_init(PenguSigBuffer *b, char *buf, size_t cap)
  {
    b->buf = buf;
    b->cap = cap;
    b->len = 0;
    if (cap > 0) buf[0] = '\0';
  }

  /* Every append is a no-op once the buffer is full, so a very long function or
   * path name truncates instead of running past the end. */
  static inline void pengu_sig_putc(PenguSigBuffer *b, char c)
  {
    if (b->len + 1 < b->cap) {
      b->buf[b->len++] = c;
      b->buf[b->len] = '\0';
    }
  }

  static inline void pengu_sig_puts(PenguSigBuffer *b, const char *s)
  {
    if (!s) return;
    while (*s) pengu_sig_putc(b, *s++);
  }

  /* Signed decimal without <stdio.h>. `-(v + 1) + 1` negates in unsigned space
   * so LLONG_MIN does not overflow (its negation is not representable). */
  static inline void pengu_sig_putint(PenguSigBuffer *b, long long v)
  {
    char tmp[24]; /* enough for 20 digits + sign + slack */
    int n = 0;
    unsigned long long u;
    if (v < 0) {
      pengu_sig_putc(b, '-');
      u = (unsigned long long)(-(v + 1)) + 1ULL;
    } else {
      u = (unsigned long long)v;
    }
    do {
      tmp[n++] = (char)('0' + (int)(u % 10ULL));
      u /= 10ULL;
    } while (u != 0ULL && n < (int)sizeof(tmp));
    while (n > 0) pengu_sig_putc(b, tmp[--n]);
  }

  static inline void pengu_sig_flush(const PenguSigBuffer *b)
  {
    if (b->len == 0) return;
#if PENGU_WINDOWS
    (void)_write(2, b->buf, (unsigned int)b->len);
#else
    (void)write(2, b->buf, b->len);
#endif
  }

#if PENGU_FRAME_TRACE
#if defined(_MSC_VER)
#define PENGU_THREAD_LOCAL __declspec(thread)
#elif defined(__GNUC__) || defined(__clang__)
#define PENGU_THREAD_LOCAL __thread
#else
#define PENGU_THREAD_LOCAL _Thread_local
#endif

  static PENGU_THREAD_LOCAL PenguFrame g_pengu_frames[PENGU_MAX_FRAMES];
  static PENGU_THREAD_LOCAL int         g_pengu_frame_top = 0;
  /*
   * Phase 3 item 3.8. This used to be `static volatile int` guarding a
   * check-then-set in `pengu_install_crash_handler()`, which is a data race: two
   * threads can both observe 0 and both run the install. `volatile` orders
   * nothing between threads. A platform once-primitive performs the check and the
   * state transition atomically, so the handler is installed exactly once even
   * when the first frames are pushed concurrently.
   *
   * The header is included by generated code, which is compiled as C11; on POSIX
   * we use `pthread_once`, and on Windows `InitOnceExecuteOnce`.
   */
#if PENGU_WINDOWS
  static INIT_ONCE g_pengu_handler_once = INIT_ONCE_STATIC_INIT;
#else
  static pthread_once_t g_pengu_handler_once = PTHREAD_ONCE_INIT;
#endif

  /*
   * Async-signal-safe crash dump (Phase 3 items 3.6 / 3.7).
   *
   * Only pengu_sig_* (pointer arithmetic + integer division) and write(2) /
   * _write are used here: no snprintf, no malloc, no stdio, no locks. One
   * write() per line keeps a 4 KB frame stack from being silently truncated at
   * a fixed buffer size; a single over-long line degrades to a truncated line.
   */
  static void pengu_dump_frame_stack(const char *reason, int signo)
  {
    char buf[1024];
    PenguSigBuffer b;

    pengu_sig_init(&b, buf, sizeof(buf));
    pengu_sig_puts(&b, "\n[PENGU CRASH] ");
    pengu_sig_puts(&b, reason ? reason : "fatal error");
    pengu_sig_puts(&b, " (signal/code ");
    pengu_sig_putint(&b, (long long)signo);
    pengu_sig_puts(&b, ")\nStack trace (most recent call first):\n");
    pengu_sig_flush(&b);

    for (int i = g_pengu_frame_top - 1; i >= 0; i--) {
      PenguFrame *f = &g_pengu_frames[i];
      pengu_sig_init(&b, buf, sizeof(buf));
      pengu_sig_puts(&b, "  at ");
      pengu_sig_puts(&b, (f->func && f->func[0]) ? f->func : "<?anon>");
      pengu_sig_puts(&b, " (");
      pengu_sig_puts(&b, (f->file && f->file[0]) ? f->file : "<unknown>");
      pengu_sig_putc(&b, ':');
      pengu_sig_putint(&b, (long long)f->line);
      pengu_sig_puts(&b, ")\n");
      pengu_sig_flush(&b);
    }
  }

#if PENGU_WINDOWS
  static LONG WINAPI pengu_win_exception_handler(EXCEPTION_POINTERS *info)
  {
    int code = 0;
    if (info && info->ExceptionRecord) {
      code = (int)info->ExceptionRecord->ExceptionCode;
    }
    pengu_dump_frame_stack("fatal exception", code);
    return EXCEPTION_EXECUTE_HANDLER;
  }
#endif

  /*
   * POSIX-only: MinGW has neither `struct sigaction` nor `sigemptyset` /
   * `sigaction` (it only ships the SysV `signal()`), so this pair is compiled
   * out on Windows, where `SetUnhandledExceptionFilter` above covers the same
   * ground. Leaving it unguarded broke every Windows build with
   * "storage size of 'sa' isn't known".
   */
#if !PENGU_WINDOWS
  static void pengu_unix_signal_handler(int sig)
  {
    pengu_dump_frame_stack("fatal signal", sig);
    _exit(128 + sig);
  }

  /*
   * Phase 3 item 3.6: `sigaction` instead of `signal`, and the faulting signals
   * an arithmetic/memory error in generated code can actually raise.
   *
   * Why not `signal()`: its semantics differ per platform (SysV resets the
   * disposition on entry, BSD does not), so a second fault could kill the
   * process before the dump. `sigaction` pins that behaviour, and SA_RESETHAND
   * makes the reset explicit rather than accidental -- if the handler itself
   * faults, the next signal terminates the process instead of recursing.
   *
   * This runs at process start (from the generated `main`), not in signal
   * context, so it may use ordinary libc calls.
   */
  static void pengu_install_one_signal(int signo)
  {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = pengu_unix_signal_handler;
    sigemptyset(&sa.sa_mask);
#ifdef SA_RESETHAND
    sa.sa_flags = SA_RESETHAND;
#endif
    /* SA_NODEFER is deliberately NOT set: the signal stays blocked while the
     * handler runs, so a fault inside the dump cannot re-enter it. */
    (void)sigaction(signo, &sa, NULL);
  }
#endif /* !PENGU_WINDOWS */

  /* Runs exactly once, whichever thread wins the once-guard. */
  static void pengu_install_crash_handler_body(void)
  {
#if PENGU_WINDOWS
    SetUnhandledExceptionFilter(pengu_win_exception_handler);
#else
    /* Memory faults. */
    pengu_install_one_signal(SIGSEGV);
    pengu_install_one_signal(SIGABRT);
    /*
     * Arithmetic and bus faults (item 3.6). An integer division by zero raises
     * SIGFPE (signal 8; a shell reports 136 = 128+8), and before this the
     * process died with no trace at all -- `pengu eval "1/0"` surfaced exit 248
     * because the CLI turned the negative subprocess return code (-8) into
     * sys.exit(-8). `-ftrapv`, which debug builds pass, turns signed overflow
     * into a trap as well. SIGBUS covers misaligned or truncated mappings.
     */
#ifdef SIGFPE
    pengu_install_one_signal(SIGFPE);
#endif
#ifdef SIGILL
    pengu_install_one_signal(SIGILL);
#endif
#ifdef SIGBUS
    pengu_install_one_signal(SIGBUS);
#endif
#endif /* PENGU_WINDOWS */
  }

#if PENGU_WINDOWS
  static BOOL CALLBACK pengu_install_crash_handler_once_cb(PINIT_ONCE once,
                                                          PVOID param,
                                                          PVOID *ctx)
  {
    (void)once; (void)param; (void)ctx;
    pengu_install_crash_handler_body();
    return TRUE;
  }
#endif

  /*
   * Idempotent and thread-safe: the once-primitive guarantees the body runs a
   * single time, and subsequent callers observe the completed state. Calling this
   * per frame is still cheap -- that is only an atomic load -- but
   * `pengu_frame_push` no longer needs to call it at all (see below).
   */
  static inline void pengu_install_crash_handler(void)
  {
#if PENGU_WINDOWS
    InitOnceExecuteOnce(&g_pengu_handler_once,
                        pengu_install_crash_handler_once_cb, NULL, NULL);
#else
    pthread_once(&g_pengu_handler_once, pengu_install_crash_handler_body);
#endif
  }

  static inline void pengu_frame_push(const char *func, const char *file, int line)
  {
    /*
     * Phase 3 item 3.8: no install call here. The generated `main` installs the
     * handler once at process start (see pengu_codegen's entry-point wrapper), so
     * this hot path -- one call per PenguScript frame -- no longer performs a
     * check on every push. The install is still idempotent and thread-safe for any
     * caller that reaches it directly.
     */
    if (g_pengu_frame_top < PENGU_MAX_FRAMES) {
      g_pengu_frames[g_pengu_frame_top].func = func;
      g_pengu_frames[g_pengu_frame_top].file = file;
      g_pengu_frames[g_pengu_frame_top].line = line;
      g_pengu_frame_top++;
    }
  }

  static inline void pengu_frame_pop(void)
  {
    if (g_pengu_frame_top > 0) {
      g_pengu_frame_top--;
    }
  }

#else /* !PENGU_FRAME_TRACE */

  /*
   * Phase 10 / F10-N3. The generated `main` always calls this (pengu_codegen's
   * entry-point wrapper does not itself test the macro), so the symbol has to
   * exist in *both* configurations. It used to be defined only inside the
   * `#if PENGU_FRAME_TRACE` branch above, which made the knob BENCHMARKS.md
   * documents for its "1.8x vs C" measurement (`-DPENGU_FRAME_TRACE=0`) fail to
   * compile the bundle with
   *   error: implicit declaration of function 'pengu_install_crash_handler'
   * With the frame trace compiled out there is no frame stack to dump, so this
   * stays a deliberate no-op: bounds panics and the signal handler that does not
   * depend on the trace keep working, and nothing about the ABI changes.
   */
  static inline void pengu_install_crash_handler(void)
  {
  }

  static inline void pengu_frame_push(const char *func, const char *file, int line)
  {
    (void)func; (void)file; (void)line;
  }

  static inline void pengu_frame_pop(void)
  {
  }

  static inline void pengu_dump_frame_stack(const char *reason, int signo)
  {
    (void)reason; (void)signo;
  }

#endif /* PENGU_FRAME_TRACE */

  /**
   * @brief Aborts with bounds check failure diagnostic and frame stack trace.
   * @note Usa _exit(134) para evitar el doble dump del signal handler.
   *       Los buffers stdio no se flushan.
   */
  static inline void pengu_bounds_panic(int64_t idx, int64_t len, const char *loc)
  {
    char buf[512];
    PenguSigBuffer b;
    /* Phase 3 item 3.7: manual formatting, so the whole crash-reporting path is
     * snprintf-free and safe to reach from signal context. */
    pengu_sig_init(&b, buf, sizeof(buf));
    pengu_sig_puts(&b, "\n[PENGU] Index out of bounds: ");
    pengu_sig_putint(&b, (long long)idx);
    pengu_sig_puts(&b, " (length ");
    pengu_sig_putint(&b, (long long)len);
    pengu_sig_puts(&b, ") at ");
    pengu_sig_puts(&b, loc ? loc : "?");
    pengu_sig_putc(&b, '\n');
    pengu_sig_flush(&b);
    pengu_dump_frame_stack("bounds check failed", 0);
    _exit(134);
  }

  static inline void pengu_assert_bounds(int64_t idx, int64_t len, const char *loc)
  {
#if PENGU_BOUNDS_CHECK
    if (idx < 0 || idx >= len) {
      pengu_bounds_panic(idx, len, loc);
    }
#else
    (void)idx; (void)len; (void)loc;
#endif
  }

  /* =========================================================================
   * 4.5. Range Subsystem (PenguRange)
   * ========================================================================= */

#ifndef PENGU_RANGE_DEFINED
#define PENGU_RANGE_DEFINED
  /**
   * @brief Represents a half-open integer range [start, end).
   */
  typedef struct
  {
    int64_t start;
    int64_t end;
  } PenguRange;

  /**
   * @brief Constructs a new PenguRange.
   */
  static inline PenguRange pengu_range_new(int64_t start, int64_t end)
  {
    PenguRange r;
    r.start = start;
    r.end = end;
    return r;
  }
#endif

  /* =========================================================================
   * 5. String Subsystem (PenguString)
   * ========================================================================= */

  /**
   * @brief Represents an immutable UTF-8 string with explicit length and data pointer.
   * @note Toda cadena con posesión (`is_owned == 1`) es una reserva **SDS**
   *       (Simple Dynamic Strings, `std_c/sds`): `data` siempre termina en '\0'
   *       y se libera con `sdsfree` (ver `pengu_banish_string`). Las vistas
   *       (`is_owned == 0`) siguen sin garantizar NUL-terminación en su último
   *       byte (p.ej. pengu_string_as_slice o vistas sobre buffers parciales).
   *       Los constructores internos (pengu_string_new, _copy, _from_cstr,
   *       _substring, _split, _concat, _format, _replace, _repeat, _reverse,
   *       _from_int, _from_float, _from_char, _char_at) producen buffers
   *       NUL-terminados, pero el consumidor no debe asumirlo en una vista sin
   *       comprobación explícita.
   */
  typedef struct
  {
    char *data;
    int len;
    int32_t is_owned;
  } PenguString;

  /* Ownership kinds stored in `PenguString.is_owned` (see the full contract in
   * section "5.1 Ownership kinds and SDS constructors" below). */
  #define PENGU_STRING_BORROWED 0
  #define PENGU_STRING_OWNED 1
  #define PENGU_STRING_OWNED_RAW 2

  /**
   * @brief Creates a deep copy of a PenguString.
   * @note Preserva bytes NUL embebidos. La implementación NO usa strlen
   *       internamente — hace memcpy sobre s.len bytes.
   */
  PenguString pengu_string_copy(PenguString s);

  /**
   * @brief Constructs a newly allocated PenguString from a null-terminated C string.
   * @note El constructor usa strlen; los NULs embebidos se truncan. Para preservar
   *       longitud binaria exacta, usar pengu_string_copy sobre un PenguString ya
   *       construido con len correcta. Strings > INT_MAX bytes se rechazan (retornan
   *       vacío) y en ningún caso se admiten longitudes truncadas.
   * @param str Null-terminated C string buffer.
   * @return Newly allocated SDS-backed PenguString.
   */
  static inline PenguString pengu_string_new(const char *str)
  {
    PenguString s;
    if (!str)
    {
      s.len = 0;
      s.data = (char *)"";
      s.is_owned = 0;
      return s;
    }
    size_t len = strlen(str);
    if (len == 0 || len > INT_MAX)
    {
      s.len = 0;
      s.data = (char *)"";
      s.is_owned = 0;
      return s;
    }
    sds draft = sdsnewlen(str, len);
    if (!draft)
    {
      s.len = 0;
      s.data = (char *)"";
      s.is_owned = 0;
      return s;
    }
    s.len = (int)len;
    s.data = draft;
    s.is_owned = PENGU_STRING_OWNED;
    return s;
  }

  /**
   * @brief Constructs a non-owning PenguString view from a C string literal without copying.
   * @note El constructor usa strlen; los NULs embebidos se truncan. Para preservar
   *       longitud binaria exacta, usar pengu_string_copy sobre un PenguString ya
   *       construido con len correcta.
   * @param str Null-terminated C string literal.
   * @return View PenguString.
   */
  static inline PenguString pengu_string_from_cstr(const char *str)
  {
    PenguString s;
    if (!str)
    {
      s.len = 0;
      s.data = (char *)"";
      s.is_owned = 0;
      return s;
    }
    s.len = (int)strlen(str);
    s.data = (char *)str;
    s.is_owned = 0;
    return s;
  }

  /**
   * @brief Constructs a non-owning PenguString view with an explicit length.
   *
   * The compiler emits this for every string literal after decoding `\xNN`,
   * `\0` and `\u{...}` escapes itself.  Unlike `pengu_string_from_cstr`, the
   * length comes from the compiler (the C literal is emitted with unambiguous
   * octal escapes), so an embedded NUL or a byte >= 0x80 is preserved byte for
   * byte.  The C string literal has static storage duration, so the view stays
   * valid for the life of the program and must not be `banish`ed.
   *
   * @param str C string literal (borrowed, static storage).
   * @param len Exact number of bytes to expose.
   * @return Non-owning PenguString view.
   */
  static inline PenguString pengu_string_from_cstr_len(const char *str, int len)
  {
    PenguString s;
    if (!str || len < 0)
    {
      s.data = (char *)"";
      s.len = 0;
      s.is_owned = 0;
      return s;
    }
    s.data = (char *)str;
    s.len = len;
    s.is_owned = 0;
    return s;
  }

  /* -------------------------------------------------------------------------
   * 5.1 Ownership kinds and SDS constructors
   *
   * Every owned `PenguString` created by the runtime or the standard library
   * carries one of these values in `is_owned`:
   *
   *   0 (`PENGU_STRING_BORROWED`) - a view; `banish` is a no-op.
   *   1 (`PENGU_STRING_OWNED`)    - `data` is a valid `sds`; free with `sdsfree`.
   *   2 (`PENGU_STRING_OWNED_RAW`)- `data` is a non-SDS raw block owned by the
   *                                 program and allocated with the C allocator;
   *                                 free with `free`.  Reserved for blocks that
   *                                 cannot be SDS: `std/arena` (alignment) and
   *                                 `std/regulus` (opaque `re_t` from lib `re`).
   *
   * C extensions must not hand a `malloc` buffer to `pengu_banish_string` with
   * `is_owned == 1`; use `pengu_string_owned` or `pengu_string_owned_size`.
   * ------------------------------------------------------------------------- */

  /**
   * @brief Copies exactly `len` bytes into a freshly allocated SDS string.
   *
   * Binary-safe: embedded NUL bytes survive. An empty/NULL input yields the
   * borrowed empty view (so `banish` stays a no-op), matching the historical
   * constructors. On allocation failure it also returns the empty view.
   *
   * @param data Source bytes (may be NULL only when `len <= 0`).
   * @param len Exact number of bytes to copy.
   * @return Owned SDS string, or the borrowed empty view.
   */
  static inline PenguString pengu_string_owned(const void *data, int len)
  {
    if (!data || len <= 0)
      return pengu_string_from_cstr("");
    sds s = sdsnewlen(data, (size_t)len);
    if (!s)
      return pengu_string_from_cstr("");
    PenguString out;
    out.data = s;
    out.len = len;
    out.is_owned = PENGU_STRING_OWNED;
    return out;
  }

  /**
   * @brief Allocates an owned, zero-initialized SDS payload of `len` bytes.
   *
   * Use it when the bytes are written afterwards and the final length is known
   * up front. The payload is always NUL-terminated by SDS; callers may set a
   * shorter used length with `pengu_string_owned_from_sds_len`.
   *
   * @param len Number of payload bytes (<= 0 yields the empty view).
   * @return Owned SDS string, or the borrowed empty view on failure.
   */
  static inline PenguString pengu_string_owned_size(int len)
  {
    if (len <= 0)
      return pengu_string_from_cstr("");
    sds s = sdsnewlen(NULL, (size_t)len);
    if (!s)
      return pengu_string_from_cstr("");
    PenguString out;
    out.data = s;
    out.len = len;
    out.is_owned = PENGU_STRING_OWNED;
    return out;
  }

  /**
   * @brief Owned empty SDS string (`data != NULL`, `len == 0`, `is_owned == 1`).
   *
   * Only the builders that promise an owned empty result need this; every other
   * constructor returns the cheaper borrowed empty view.
   */
  static inline PenguString pengu_string_owned_empty(void)
  {
    sds s = sdsempty();
    if (!s)
      return pengu_string_from_cstr("");
    PenguString out;
    out.data = s;
    out.len = 0;
    out.is_owned = PENGU_STRING_OWNED;
    return out;
  }

  /**
   * @brief Wraps an SDS string whose length is already authoritative.
   * @param s SDS returned by `sdsnew*`/`sdscat*` (takes ownership).
   * @return Owned `PenguString`, or the empty view if `s` is NULL/too large.
   */
  static inline PenguString pengu_string_owned_from_sds(sds s)
  {
    if (!s)
      return pengu_string_from_cstr("");
    size_t n = sdslen(s);
    if (n > (size_t)INT_MAX)
    {
      sdsfree(s);
      return pengu_string_from_cstr("");
    }
    PenguString out;
    out.data = s;
    out.len = (int)n;
    out.is_owned = PENGU_STRING_OWNED;
    return out;
  }

  /**
   * @brief Wraps an SDS allocation setting an explicit used length.
   *
   * For builders that reserve capacity up front and then write fewer bytes:
   * `used` must fit the SDS allocation. The header length is updated and the
   * byte at `used` is forced to NUL.
   *
   * @param s SDS allocation (takes ownership, even on failure).
   * @param used Number of meaningful bytes (`0 <= used <= sdsalloc(s)`).
   * @return Owned `PenguString`, or the empty view on invalid length/OOM.
   */
  static inline PenguString pengu_string_owned_from_sds_len(sds s, int used)
  {
    if (!s || used < 0)
    {
      sdsfree(s);
      return pengu_string_from_cstr("");
    }
    size_t cap = sdsalloc(s);
    if ((size_t)used > cap || (size_t)used > (size_t)INT_MAX)
    {
      sdsfree(s);
      return pengu_string_from_cstr("");
    }
    sdssetlen(s, (size_t)used);
    s[used] = '\0';
    PenguString out;
    out.data = s;
    out.len = used;
    out.is_owned = PENGU_STRING_OWNED;
    return out;
  }

  /**
   * @brief Wraps a raw (non-SDS) owned block in a `PenguString` header.
   *
   * The block is released with `free`, not `sdsfree`; only use it for buffers
   * that cannot be SDS (see the ownership-kind comment above).
   *
   * @param data Raw allocation owned by the caller.
   * @param len Number of bytes represented by the block.
   * @return A `PenguString` with `is_owned == 2`.
   */
  static inline PenguString pengu_string_owned_raw(void *data, int len)
  {
    if (!data)
      return pengu_string_from_cstr("");
    PenguString out;
    out.data = (char *)data;
    out.len = len;
    out.is_owned = PENGU_STRING_OWNED_RAW;
    return out;
  }

  /** @brief Shared read-only empty C string used by the null-safe helpers. */
  #define PENGU_EMPTY_CSTR ""

  /**
   * @brief Returns a read-only pointer to the string's internal buffer.
   * @param s Pointer to a PenguString (may be NULL).
   * @return Non-NULL `char*` view. Empty / NULL strings yield a pointer to a
   *         static empty string, never NULL.
   * @warning The pointer aliases the string's internal buffer: it stays valid
   *          only while the PenguString is alive and is NOT modified or
   *          banished. Do not free the returned pointer; it is read-only.
   */
  static inline const char *pengu_string_to_cstr(const PenguString *s)
  {
    if (!s || !s->data || s->len == 0)
      return PENGU_EMPTY_CSTR;
    return s->data;
  }

  /**
   * @brief Returns a read-only byte view of a string's internal buffer.
   * @param s Pointer to a PenguString (may be NULL).
   * @return Non-NULL `void*` view. Empty / NULL strings yield a pointer to a
   *         static empty buffer, never NULL. Lifetime is bound to the
   *         PenguString, exactly like pengu_string_to_cstr().
   */
  static inline const void *pengu_string_bytes(const PenguString *s)
  {
    if (!s || !s->data || s->len == 0)
      return (const void *)PENGU_EMPTY_CSTR;
    return (const void *)s->data;
  }

  /**
   * @brief Byte-exact counterpart of pengu_string_format used by `"{expr}"`.
   *
   * printf's `%.*s` stops at the first NUL byte, so `pengu_string_format`
   * silently truncates binary strings (e.g. cipher.decode_base64 or the pure
   * Pengu hashes in std.seal).  This formatter copies `%.*s` arguments
   * byte-exactly (using their length) while formatting the scalar specifiers
   * with snprintf, so interpolation composes strings exactly like
   * pengu_string_concat did.
   *
   * Supported specifiers (the only ones the code generator emits): `%%`, `%d`,
   * `%u`, `%lld`, `%llu`, `%f`, `%c`, `%s` (C string) and `%.*s` (PenguString
   * length + data).  `%f` selects the *float* branch but renders with `%g`
   * (Phase 3 item 3.9), so interpolation, `to string` and `print` all produce
   * the same text for a given value.
   *
   * @param fmt Format specification string built by the compiler.
   * @param ... Formatting arguments (int, double, int, const char*, int, const char*).
   * @return Freshly allocated PenguString (empty static view when the result is empty).
   */
  static inline PenguString pengu_string_format_ex(const char *fmt, ...)
  {
    if (!fmt)
      return pengu_string_from_cstr("");
    sds out = sdsempty();
    if (!out)
      return pengu_string_from_cstr("");
    bool failed = false;

#define PENGU_FMT_APPEND_BYTES(SRC, N)                                        \
    do {                                                                      \
      size_t _n = (size_t)(N);                                                \
      if (!failed && _n > 0) {                                                \
        sds _next = sdscatlen(out, (SRC), _n);                                \
        if (!_next) {                                                         \
          failed = true;                                                      \
        } else {                                                              \
          out = _next;                                                        \
        }                                                                     \
      }                                                                       \
    } while (0)

    /* snprintf returns the length the whole formatted value *would* have, which
     * can exceed the small stack buffer (e.g. a 64-bit "%lld" of LLONG_MIN
     * returns 20 and fits, but "%f" of 1e300 returned ~310 while writing 63).
     * Appending the return value blindly would read out of bounds, so retry into
     * a heap buffer when the value does not fit. Phase 3 item 3.9 made floats
     * use "%g", which is always compact, but the fallback stays as the general
     * safety net for any specifier whose output can outgrow the buffer. */
#define PENGU_FMT_APPEND_FORMATTED(FMT, VAL)                                  \
    do {                                                                      \
      if (!failed) {                                                          \
        char _small[64];                                                      \
        int _k = snprintf(_small, sizeof(_small), (FMT), (VAL));              \
        if (_k > 0 && (size_t)_k < sizeof(_small)) {                          \
          PENGU_FMT_APPEND_BYTES(_small, _k);                                 \
        } else if (_k > 0) {                                                  \
          char *_big = (char *)malloc((size_t)_k + 1);                        \
          if (!_big) {                                                        \
            failed = true;                                                    \
          } else {                                                            \
            snprintf(_big, (size_t)_k + 1, (FMT), (VAL));                     \
            PENGU_FMT_APPEND_BYTES(_big, _k);                                 \
            free(_big);                                                       \
          }                                                                   \
        }                                                                     \
      }                                                                       \
    } while (0)

    va_list ap;
    va_start(ap, fmt);
    const char *p = fmt;
    while (*p) {
      if (*p != '%') {
        PENGU_FMT_APPEND_BYTES(p, 1);
        p++;
        continue;
      }
      if (p[1] == '%') {
        PENGU_FMT_APPEND_BYTES("%", 1);
        p += 2;
        continue;
      }
      if (p[1] == '.' && p[2] == '*' && p[3] == 's') {
        int n = va_arg(ap, int);
        const char *s = va_arg(ap, const char *);
        if (n > 0 && s)
          PENGU_FMT_APPEND_BYTES(s, n);
        p += 4;
        continue;
      }
      if (p[1] == 'l' && p[2] == 'l' && (p[3] == 'd' || p[3] == 'u')) {
        if (p[3] == 'd') {
          long long v = va_arg(ap, long long);
          PENGU_FMT_APPEND_FORMATTED("%lld", v);
        } else {
          unsigned long long v = va_arg(ap, unsigned long long);
          PENGU_FMT_APPEND_FORMATTED("%llu", v);
        }
        p += 4;
        continue;
      }
      if (p[1] == 'u') {
        unsigned int v = va_arg(ap, unsigned int);
        PENGU_FMT_APPEND_FORMATTED("%u", v);
        p += 2;
        continue;
      }
      if (p[1] == 'd') {
        int v = va_arg(ap, int);
        PENGU_FMT_APPEND_FORMATTED("%d", v);
        p += 2;
        continue;
      }
      if (p[1] == 'f') {
        double v = va_arg(ap, double);
        /* Phase 3 item 3.9: `%g`, matching pengu_string_from_float (`to string`)
         * and the `print` builtin. `%f` used to print 3.14 as "3.140000" here
         * while `to string` printed "3.14" -- two textual forms for the same
         * value, chosen by accident of which path formatted it. */
        PENGU_FMT_APPEND_FORMATTED("%g", v);
        p += 2;
        continue;
      }
      if (p[1] == 'c') {
        int v = va_arg(ap, int);
        char c = (char)v;
        PENGU_FMT_APPEND_BYTES(&c, 1);
        p += 2;
        continue;
      }
      if (p[1] == 's') {
        const char *s = va_arg(ap, const char *);
        if (s)
          PENGU_FMT_APPEND_BYTES(s, strlen(s));
        p += 2;
        continue;
      }
      /* Unknown specifier: emit it literally (never produced by the compiler). */
      PENGU_FMT_APPEND_BYTES(p, 1);
      p++;
    }
    va_end(ap);
#undef PENGU_FMT_APPEND_BYTES
#undef PENGU_FMT_APPEND_FORMATTED

    if (failed || sdslen(out) == 0) {
      sdsfree(out);
      return pengu_string_from_cstr("");
    }
    return pengu_string_owned_from_sds(out);
  }

  /**
   * @brief Constructs a formatted PenguString using printf-style arguments.
   * @note En C11, pasar args a vsnprintf consume su estado; el doble va_start y
   *       va_end es deliberado y requerido por el estándar para reutilizar los argumentos.
   * @param fmt Printf format specification string.
   * @param ... Variable formatting arguments.
   * @return Formatted PenguString. Returns empty string `""` on formatting
   *         failure (vsnprintf error or allocation failure); note that this
   *         cannot be distinguished from a legitimately empty formatted string.
   */
  static inline PenguString pengu_string_format(const char *fmt, ...)
  {
    if (!fmt)
      return pengu_string_from_cstr("");
    va_list args;
    va_start(args, fmt);
    int size = vsnprintf(NULL, 0, fmt, args);
    va_end(args);
    if (size <= 0)
      return pengu_string_from_cstr("");
    sds out = sdsnewlen(NULL, (size_t)size);
    if (!out)
      return pengu_string_from_cstr("");
    va_start(args, fmt);
    vsnprintf(out, (size_t)size + 1, fmt, args);
    va_end(args);
    return pengu_string_owned_from_sds(out);
  }

  /**
   * @brief Concatenates two PenguString structures into a newly allocated PenguString.
   * @note Strings > INT_MAX bytes se rechazan (retornan vacío) y en ningún caso se admiten longitudes truncadas.
   * @param a First string operand.
   * @param b Second string operand.
   * @return Combined PenguString.
   */
  static inline PenguString pengu_string_concat(PenguString a, PenguString b)
  {
    if (a.len < 0 || b.len < 0)
      return pengu_string_from_cstr("");
    if (a.len > INT_MAX - b.len)
      return pengu_string_from_cstr(""); /* evita UB y truncación */
    int total = a.len + b.len;
    if (total <= 0)
      return pengu_string_from_cstr("");
    sds out = sdsnewlen(NULL, (size_t)total);
    if (!out)
      return pengu_string_from_cstr("");
    if (a.data && a.len > 0)
    {
      memcpy(out, a.data, (size_t)a.len);
    }
    if (b.data && b.len > 0)
    {
      memcpy(out + a.len, b.data, (size_t)b.len);
    }
    return pengu_string_owned_from_sds(out);
  }

  /**
   * @brief Tests two PenguString objects for content equality.
   * @param a First string.
   * @param b Second string.
   * @return True if lengths and byte contents match, false otherwise.
   */
  static inline bool pengu_string_equal(PenguString a, PenguString b)
  {
    if (a.len != b.len)
      return false;
    if (a.len == 0)
      return true;
    if (!a.data || !b.data)
      return a.data == b.data;
    return memcmp(a.data, b.data, (size_t)a.len) == 0;
  }

  /**
   * @brief Lexicographically compares two PenguString objects.
   * @return Negative if a < b, positive if a > b, 0 if equal.
   */
  static inline int pengu_string_compare(PenguString a, PenguString b)
  {
    int min_len = a.len < b.len ? a.len : b.len;
    if (min_len > 0 && a.data && b.data) {
      int c = memcmp(a.data, b.data, (size_t)min_len);
      if (c != 0)
        return c;
    }
    if (a.len < b.len)
      return -1;
    if (a.len > b.len)
      return 1;
    return 0;
  }

  /**
   * @brief Frees heap buffer allocated by a PenguString.
   * @param s Pointer to PenguString to deallocate.
   * @warning Solo es seguro sobre strings creados por los constructores del
   *          runtime (pengu_string_new, _copy, _format, _concat, _substring,
   *          _replace, _repeat, _reverse, _from_int, _from_float, _from_char,
   *          pengu_string_owned*, o los bloques opacos con is_owned == 2).
   *          NUNCA llamar sobre el resultado de pengu_string_from_cstr (view de
   *          rodata) ni sobre strings con len == 0 (no-op). La heurística
   *          'len > 0 ⟹ owning' NO distingue views no-owning con contenido.
   *
   * A `is_owned == 1` payload is an SDS string and is released with `sdsfree`;
   * `is_owned == 2` is a raw block (arena/regulus) released with `free`.
   */
  static inline void pengu_banish_string(PenguString *s)
  {
    if (!s)
      return;
    if (s->data && s->is_owned)
    {
      if (s->is_owned == PENGU_STRING_OWNED)
        sdsfree(s->data);
      else
        free(s->data);
    }
    s->data = NULL;
    s->len = 0;
    s->is_owned = 0;
  }

  /**
   * @brief Runtime helper: invokes a PenguScript weave handed to C as a
   * function pointer (validates the C->Pengu callback direction).
   */
  static inline void pengu_call_callback_int(void (*cb)(int), int value)
  {
    if (cb)
      cb(value);
  }

  /* minicoro shim (defined in libpengu_stb.a via std_c/wrappers_minicoro.c) */
  void *pengu_mco_start(void (*body)(void *), void *user_data, size_t stack_size);
  void pengu_mco_resume(void *co);
  void pengu_mco_yield(void *co);
  int pengu_mco_status(void *co);
  void pengu_mco_destroy(void *co);

  static inline int pengu__find_sub(PenguString hay, PenguString needle, int from_idx)
  {
    if (!hay.data || !needle.data || needle.len < 0 || from_idx < 0 || from_idx > hay.len)
      return -1;
    if (needle.len == 0)
      return from_idx;
    if (needle.len > hay.len - from_idx)
      return -1; /* evita overflow en suma */
    for (int i = from_idx; i <= hay.len - needle.len; ++i)
    {
      if (memcmp(hay.data + i, needle.data, (size_t)needle.len) == 0)
        return i;
    }
    return -1;
  }

  /* pengu_string_contains, pengu_string_starts_with, pengu_string_ends_with,
   * pengu_string_index_of, pengu_string_last_index_of, pengu_string_replace,
   * pengu_string_repeat and pengu_string_reverse moved to std/scrolls.pengu
   * (Chunk 2, 2.0 migration) as `antiquus` blocks: scrolls was their only
   * consumer. pengu__find_sub stays here because pengu_string_split and the glob
   * matcher use it, and pengu_string_substring / pengu_string_char_at stay
   * because the code generator emits them. */

  /**
   * @brief Removes leading and trailing whitespace from a string.
   * @param s Source string.
   * @return Trimmed PenguString.
   */
  static inline PenguString pengu_string_trim(PenguString s)
  {
    if (!s.data || s.len <= 0)
      return pengu_string_from_cstr("");
    int start = 0;
    while (start < s.len && isspace((unsigned char)s.data[start]))
    {
      start++;
    }
    int end = s.len - 1;
    while (end >= start && isspace((unsigned char)s.data[end]))
    {
      end--;
    }
    int len = (end >= start) ? (end - start + 1) : 0;
    if (len <= 0)
      return pengu_string_from_cstr("");
    return pengu_string_owned(s.data + start, len);
  }

  /**
   * @brief Removes leading whitespace from a string.
   * @param s Source string.
   * @return Left-trimmed PenguString.
   */
  static inline PenguString pengu_string_trim_start(PenguString s)
  {
    if (!s.data || s.len <= 0)
      return pengu_string_from_cstr("");
    int start = 0;
    while (start < s.len && isspace((unsigned char)s.data[start]))
    {
      start++;
    }
    int len = s.len - start;
    if (len <= 0)
      return pengu_string_from_cstr("");
    return pengu_string_owned(s.data + start, len);
  }

  /**
   * @brief Removes trailing whitespace from a string.
   * @param s Source string.
   * @return Right-trimmed PenguString.
   */
  static inline PenguString pengu_string_trim_end(PenguString s)
  {
    if (!s.data || s.len <= 0)
      return pengu_string_from_cstr("");
    int end = s.len - 1;
    while (end >= 0 && isspace((unsigned char)s.data[end]))
    {
      end--;
    }
    int len = end + 1;
    if (len <= 0)
      return pengu_string_from_cstr("");
    return pengu_string_owned(s.data, len);
  }

  /* pengu_string_starts_with and pengu_string_ends_with moved to
   * std/scrolls.pengu (see the note above). */

  /**
   * @brief Extracts a substring from start index (inclusive) to end index (exclusive).
   * @param s Source string.
   * @param start Starting index (inclusive).
   * @param end Ending index (exclusive).
   * @return Newly allocated substring PenguString.
   */
  static inline PenguString pengu_string_substring(PenguString s, int start, int end)
  {
    if (!s.data || s.len <= 0)
      return pengu_string_from_cstr("");
    if (start < 0)
      start = 0;
    if (end > s.len)
      end = s.len;
    if (start >= end)
      return pengu_string_from_cstr("");
    return pengu_string_owned(s.data + start, end - start);
  }

  /* pengu_string_replace, pengu_string_repeat and pengu_string_reverse moved to
   * std/scrolls.pengu (see the note above). */

  /**
   * @brief Returns single character at index idx as a new PenguString.
   * @note Manejo binario-exacto: retorna una cadena de longitud 1 para cualquier byte,
   *       incluido el byte NUL ('\0').
   * @param s Source string.
   * @param idx 0-based character index.
   * @return Single character PenguString or empty string if out of bounds.
   */
  static inline PenguString pengu_string_char_at(PenguString s, int idx)
  {
    if (!s.data || idx < 0 || idx >= s.len)
      return pengu_string_from_cstr("");
    return pengu_string_owned(s.data + idx, 1);
  }

  /**
   * @brief Formats an integer to a PenguString.
   * @param val 64-bit integer value.
   * @return Formatted PenguString.
   */
  static inline PenguString pengu_string_from_int(int64_t val)
  {
    return pengu_string_owned_from_sds(sdsfromlonglong((long long)val));
  }

  /**
   * @brief Formats a floating point number to a PenguString.
   * @param val Floating point value.
   * @return Formatted PenguString.
   */
  static inline PenguString pengu_string_from_float(double val)
  {
    char buf[64];
    snprintf(buf, sizeof(buf), "%g", val);
    return pengu_string_new(buf);
  }

  /**
   * @brief Converts a single char to a PenguString.
   * @note Manejo binario-exacto: retorna una cadena de longitud 1 para cualquier byte,
   *       incluido el byte NUL ('\0').
   * @param c Character.
   * @return Formatted PenguString.
   */
  static inline PenguString pengu_string_from_char(char c)
  {
    return pengu_string_owned(&c, 1);
  }

  /**
   * @brief Converts a boolean value to string ("true" or "false").
   * @warning El resultado es un view no-owning sobre rodata. pengu_banish_string
   *          sobre este valor es UB (no-op sólo si len == 0, lo cual no es el
   *          caso). Para liberar de forma segura, copiar primero con
   *          pengu_string_copy.
   * @param val Boolean value.
   * @return PenguString view.
   */
  static inline PenguString pengu_string_from_bool(bool val)
  {
    /* rodata, no liberar */
    return val ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
  }

  /**
   * @brief Identity function for PenguString (used in _Generic macro).
   * @param s Input string.
   * @return Unchanged string.
   */
  static inline PenguString pengu_string_identity(PenguString s)
  {
    return s;
  }

  /* pengu_parse_int and pengu_parse_float moved to std/spark.pengu (Chunk 1,
   * 2.0 migration), together with pengu_print, pengu_println, pengu_input and
   * pengu_panic. The radix parser and the stderr/flush/exit helpers are new and
   * live there too. */

/**
 * @brief Generic macro converting any primitive type or PenguString to PenguString.
 *
 * Convenience for *host* C code only: the code generator never emits it (it
 * knows the static type and calls the concrete ``pengu_string_from_*``
 * producer, see roadmap 2.2.e).  It needs C11 ``_Generic``, so it is compiled
 * out under strict C99; the generated bundle therefore stays C99-clean.
 */
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
#define pengu_to_string(x) _Generic((x),       \
    char: pengu_string_from_char,              \
    signed char: pengu_string_from_char,       \
    unsigned char: pengu_string_from_int,      \
    short: pengu_string_from_int,              \
    unsigned short: pengu_string_from_int,     \
    int: pengu_string_from_int,                \
    unsigned int: pengu_string_from_int,       \
    long: pengu_string_from_int,               \
    unsigned long: pengu_string_from_int,      \
    long long: pengu_string_from_int,          \
    unsigned long long: pengu_string_from_int, \
    double: pengu_string_from_float,           \
    float: pengu_string_from_float,            \
    bool: pengu_string_from_bool,              \
    char*: pengu_string_from_cstr,             \
    const char*: pengu_string_from_cstr,       \
    PenguString: pengu_string_identity)(x)
#endif /* __STDC_VERSION__ >= 201112L */

  /* =========================================================================
   * 6. Slice Subsystem (PenguSlice)
   * ========================================================================= */

  /**
   * @brief Fat-pointer view into contiguous array or buffer memory.
   */
  typedef struct
  {
    void *data;
    int len;
    size_t elem_size;
  } PenguSlice;

  /**
   * @brief Creates a slice view over a contiguous memory buffer.
   * @param data Memory pointer.
   * @param elem_size Size of each element in bytes.
   * @param len Number of elements in slice.
   * @return Initialized PenguSlice.
   */
  static inline PenguSlice pengu_slice_new(void *data, size_t elem_size, int len)
  {
    PenguSlice slice;
    slice.data = data;
    slice.len = len;
    slice.elem_size = elem_size;
    return slice;
  }

  /**
   * @brief Retrieves pointer to element at index in slice.
   * @param slice Pointer to const PenguSlice.
   * @param idx Element index.
   * @return Pointer to element or NULL if out of bounds.
   */
  static inline void *pengu_slice_at(const PenguSlice *slice, int idx)
  {
    if (!slice || idx < 0 || idx >= slice->len)
      return NULL;
    return (char *)slice->data + ((size_t)idx * slice->elem_size);
  }

  /**
   * @brief Returns length of slice.
   * @param slice Pointer to const PenguSlice.
   * @return Element count.
   */
  static inline int pengu_slice_len(const PenguSlice *slice)
  {
    return slice ? slice->len : 0;
  }

  /**
   * @brief Returns the raw data pointer of a slice.
   * @param slice Pointer to a PenguSlice (may be NULL).
   * @return The backing buffer pointer, or NULL when the slice is NULL.
   * @note A slice is a non-owning view: the returned pointer is only valid for
   *       the lifetime of the memory the slice points into.
   */
  static inline void *pengu_slice_data(const PenguSlice *slice)
  {
    return slice ? slice->data : NULL;
  }

  /* =========================================================================
   * 7. Dynamic List Subsystem (PenguList)
   * ========================================================================= */

  /**
   * @brief Growable dynamic list with capacity, length and element size.
   *
   * The list owns exactly one allocation: its own element buffer.  Storing an
   * element is a `memcpy` of `elem_size` bytes and never clones a payload, and
   * `pengu_banish_list` frees that buffer without touching the elements.  This
   * is the manual model described in LANGUAGE.md: if an element owns memory,
   * releasing it is the caller's job.
   *
   * INVARIANT: `elem_size` is immutable once the list exists; changing it later
   * would desynchronise the element stride from every existing slot.
   */
  typedef struct
  {
    void *data;
    int len;
    int cap;
    size_t elem_size;
  } PenguList;

  /* CC-backed list primitives (runtime/pengu_containers.c).  The header keeps
   * only the field accessors; the CC header never reaches generated bundles. */
  void pengu_cc_list_init(PenguList *list, size_t elem_size, size_t cap);
  void pengu_cc_list_push(PenguList *list, const void *item);
  void *pengu_cc_list_pop_val(PenguList *list);
  bool pengu_cc_list_pop(PenguList *list, void *out_item);
  void pengu_cc_list_clear(PenguList *list);
  void pengu_cc_list_banish(PenguList *list);
  void pengu_cc_list_set_len(PenguList *list, int len);
  bool pengu_cc_list_remove_at(PenguList *list, int idx);
  void pengu_cc_list_from_data(PenguList *list, const void *data,
                               size_t elem_size, int count);

  /**
   * @brief Creates a new dynamic list with given element size and capacity.
   * @param elem_size Size of each element in bytes.
   * @param cap Initial capacity.
   * @return Initialized PenguList.
   */
  static inline PenguList pengu_list_new(size_t elem_size, size_t cap)
  {
    PenguList list;
    list.data = NULL;
    list.len = 0;
    list.cap = 0;
    list.elem_size = elem_size;
    pengu_cc_list_init(&list, elem_size, cap);
    return list;
  }

  /**
   * @brief Appends an element to the list, expanding capacity if needed.
   * @note Copies `elem_size` bytes with `memcpy`; it never clones a payload.
   * @param list Pointer to PenguList.
   * @param item Pointer to element data to copy into list.
   */
  static inline void pengu_list_push(PenguList *list, const void *item)
  {
    if (!list || !item)
      return;
    pengu_cc_list_push(list, item);
  }

  /**
   * @brief Pops and removes the last element from the list, returning a pointer to it.
   * @note Devuelve un puntero al buffer interno del list; se invalida tras un push
   *       que redimensione. El caller debe copiar si va a retenerlo.
   * @param list Pointer to PenguList.
   * @return Pointer to popped element buffer, or NULL if list was empty.
   */
  static inline void *pengu_list_pop_val(PenguList *list)
  {
    return pengu_cc_list_pop_val(list);
  }

  /**
   * @brief Pops and removes the last element from the list into an output buffer.
   * @param list Pointer to PenguList.
   * @param out_item Optional destination buffer to copy popped element into.
   * @return True if an element was popped, False if list was empty.
   */
  static inline bool pengu_list_pop(PenguList *list, void *out_item)
  {
    return pengu_cc_list_pop(list, out_item);
  }

  /**
   * @brief Accesses element at index in dynamic list.
   * @param list Pointer to const PenguList.
   * @param idx Element index.
   * @return Pointer to element or NULL if out of bounds.
   */
  static inline void *pengu_list_at(const PenguList *list, int idx)
  {
    if (!list || idx < 0 || idx >= list->len)
      return NULL;
    return (char *)list->data + ((size_t)idx * list->elem_size);
  }

  /**
   * @brief Finds the 0-based index of an item in the list.
   * @param list Pointer to const PenguList.
   * @param item Pointer to item data.
   * @return Index of element, or -1 if not found.
   */
  static inline int pengu_list_index_of(const PenguList *list, const void *item)
  {
    if (!list || !item || list->len <= 0)
      return -1;
    for (int i = 0; i < list->len; ++i)
    {
      void *elem = (char *)list->data + ((size_t)i * list->elem_size);
      if (list->elem_size == sizeof(PenguString))
      {
        PenguString *s1 = (PenguString *)elem;
        PenguString *s2 = (PenguString *)item;
        if (s1->len == s2->len && (s1->len == 0 || memcmp(s1->data, s2->data, (size_t)s1->len) == 0))
          return i;
      }
      else
      {
        if (memcmp(elem, item, list->elem_size) == 0)
          return i;
      }
    }
    return -1;
  }

  /**
   * @brief Checks if list contains an item.
   * @param list Pointer to const PenguList.
   * @param item Pointer to item data.
   * @return True if item is in list, False otherwise.
   */
  static inline bool pengu_list_contains(const PenguList *list, const void *item)
  {
    return pengu_list_index_of(list, item) != -1;
  }

  /**
   * @brief Clears all elements from the list without freeing allocated buffer.
   * @param list Pointer to PenguList.
   */
  static inline void pengu_list_clear(PenguList *list)
  {
    pengu_cc_list_clear(list);
  }

  /**
   * @brief Frees the list's own element buffer.
   *
   * Elements are *not* released: the list never owned them, it only stored
   * their bytes.  Free whatever an element owns before banishing the list.
   *
   * @param list Pointer to PenguList.
   */
  static inline void pengu_banish_list(PenguList *list)
  {
    pengu_cc_list_banish(list);
  }

  /**
   * @brief Sets the logical length of a list, updating the CC header.
   * For a non-owning arena list (`cap < 0`) only `len` changes.
   */
  static inline void pengu_list_set_len(PenguList *list, int len)
  {
    pengu_cc_list_set_len(list, len);
  }

  /** @brief Removes the element at `idx`, shifting the tail left. */
  static inline bool pengu_list_remove_at(PenguList *list, int idx)
  {
    return pengu_cc_list_remove_at(list, idx);
  }

  /* =========================================================================
   * 7b. Foreign-function helpers: C arrays -> PenguList of PenguString
   *
   * Each element is a fresh owned PenguString, but the *list* owns nothing
   * beyond its element buffer: use pengu_banish_string_list to release both.
   * ========================================================================= */

  /**
   * @brief Builds a 'list of string' from a counted array of C strings.
   * @param arr Array of NUL-terminated C strings (may contain NULL entries).
   * @param count Number of entries in @p arr.
   * @return PenguList of PenguString holding freshly allocated copies.
   */
  static inline PenguList pengu_list_of_string_from_cstrs(const char *const *arr, int count)
  {
    PenguList list = pengu_list_new(sizeof(PenguString),
                                    count > 0 ? (size_t)count : 4);
    if (!arr)
      return list;
    for (int i = 0; i < count; ++i)
    {
      /* The list owns its elements: 'from_cstr' is a non-owning view, so each
       * one is copied into a fresh buffer.  Release them with
       * pengu_banish_string_list. */
      PenguString s = pengu_string_new(arr[i] ? arr[i] : "");
      pengu_list_push(&list, &s);
    }
    return list;
  }

  /**
   * @brief Like pengu_list_of_string_from_cstrs but stops at the first NULL.
   * @param arr NULL-terminated array of C strings.
   * @return PenguList of PenguString holding freshly allocated copies.
   */
  static inline PenguList pengu_list_of_string_from_cstrv(const char *const *arr)
  {
    int n = 0;
    if (arr)
    {
      while (arr[n])
        n++;
    }
    return pengu_list_of_string_from_cstrs(arr, n);
  }

  /**
   * @brief Frees every PenguString element of a list, then the list's buffer.

   * The element-level release the container no longer performs for you.
   * @param l Pointer to PenguList containing PenguString elements.
   */
  static inline void pengu_banish_string_list(PenguList *l)
  {
    if (!l)
      return;
    for (int i = 0; i < l->len; ++i)
    {
      PenguString *s = (PenguString *)pengu_list_at(l, i);
      if (s)
        pengu_banish_string(s);
    }
    pengu_banish_list(l);
  }

  /**
   * @brief Returns the raw element-buffer pointer of a list.
   * @param list Pointer to a PenguList (may be NULL).
   * @return The internal element buffer, or NULL when the list is NULL or has
   *         no buffer. Elements live at ``(char*)ptr + i * elem_size``.
   * @warning The pointer aliases list-owned memory; do not free it and do not
   *          use it after pengu_banish_list().
   */
  static inline void *pengu_list_data(const PenguList *list)
  {
    return list ? list->data : NULL;
  }

  /**
   * @brief Splits string s by delimiter delim into a dynamic PenguList of PenguString.
   * @note Manejo binario-exacto: ni `s` ni `delim` se truncan en el primer NUL (\0).
   * @note Cada elemento es una *vista* (`is_owned == 0`) sobre el búfer de `s`, no
   *       una copia: `s` debe seguir vivo mientras se usen las partes. Basta con
   *       `pengu_banish_list`; liberar cada parte es un no-op, porque no poseen
   *       nada. Copia una parte con `pengu_string_copy` si necesita sobrevivir a `s`.
   * @param s Source string.
   * @param delim Delimiter string.
   * @return PenguList containing tokenized PenguString elements.
   */
  static inline PenguList pengu_string_split(PenguString s, PenguString delim)
  {
    PenguList list = pengu_list_new(sizeof(PenguString), 4);
    if (!s.data || s.len == 0)
    {
      PenguString empty = pengu_string_from_cstr("");
      pengu_list_push(&list, &empty);
      return list;
    }
    if (!delim.data || delim.len == 0)
    {
      for (int i = 0; i < s.len; ++i)
      {
        PenguString ch = {s.data + i, 1, 0};
        pengu_list_push(&list, &ch);
      }
      return list;
    }
    int cur = 0;
    int idx;
    while ((idx = pengu__find_sub(s, delim, cur)) != -1)
    {
      int seg_len = idx - cur;
      PenguString part = (seg_len > 0) ? (PenguString){s.data + cur, seg_len, 0} : pengu_string_from_cstr("");
      pengu_list_push(&list, &part);
      cur = idx + delim.len;
    }
    int rem_len = s.len - cur;
    PenguString rem_part = (rem_len > 0) ? (PenguString){s.data + cur, rem_len, 0} : pengu_string_from_cstr("");
    pengu_list_push(&list, &rem_part);
    return list;
  }

  /** @brief Pushes an int32 element onto dynamic list. */
  static inline void pengu_list_push_int(PenguList *l, const int32_t *item)
  {
    pengu_list_push(l, item);
  }

  /** @brief Pushes a PenguString element onto dynamic list. */
  static inline void pengu_list_push_string(PenguList *l, const PenguString *item)
  {
    pengu_list_push(l, item);
  }

  /** @brief Pops the last int32 element from dynamic list. */
  static inline bool pengu_list_pop_int(PenguList *l, int32_t *out)
  {
    return pengu_list_pop(l, out);
  }

  /** @brief Checks if dynamic list of int32 contains item. */
  static inline bool pengu_list_contains_int(const PenguList *l, const int32_t *item)
  {
    if (!l || !item || !l->data)
      return false;
    for (int i = 0; i < l->len; ++i)
    {
      const int32_t *val = (const int32_t *)pengu_list_at(l, i);
      if (val && *val == *item)
        return true;
    }
    return false;
  }

  /** @brief Returns 0-based index of item in list of int32, or -1 if not found. */
  static inline int pengu_list_index_of_int(const PenguList *l, const int32_t *item)
  {
    if (!l || !item || !l->data)
      return -1;
    for (int i = 0; i < l->len; ++i)
    {
      const int32_t *val = (const int32_t *)pengu_list_at(l, i);
      if (val && *val == *item)
        return i;
    }
    return -1;
  }

  /* =========================================================================
   * 8. Hash Map Subsystem (PenguMap)
   * ========================================================================= */

  /**
   * @brief Computes 32-bit FNV-1a hash over raw byte buffer.
   * @param data Pointer to buffer.
   * @param len Buffer length in bytes.
   * @return 32-bit hash value.
   */
  static inline uint32_t pengu_hash_bytes(const void *data, size_t len)
  {
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t hash = 2166136261u;
    for (size_t i = 0; i < len; ++i)
    {
      hash ^= bytes[i];
      hash *= 16777619u;
    }
    return hash;
  }

  /**
   * @brief Single key-value entry in open addressing hash table.
   * @note Internal open-addressing slot. Uses tombstone markers to preserve
   *       linear probing collision chains across deletions.
   */
  typedef struct
  {
    uint32_t hash;
    void *key;
    void *val;
    bool occupied;
    bool tombstone;
  } PenguMapEntry;

  /**
   * @brief Key-value hash map collection.
   *
   * Each occupied entry owns two small allocations (the key and the value
   * *bytes*), and the map owns the entry table.  Keys and values are copied
   * with `memcpy` on insert and freed without recursion on banish: a
   * PenguString key is stored by value and keeps owning (or aliasing) its own
   * buffer, exactly like a `PenguString` field of a C struct.
   */
  typedef struct
  {
    void *state;
    int len;
    int cap;
    size_t key_size;
    size_t val_size;
  } PenguMap;

  /* CC-backed map primitives (runtime/pengu_containers.c). */
  void pengu_cc_map_init(PenguMap *map, size_t key_size, size_t val_size);
  void pengu_cc_map_put(PenguMap *map, const void *key, const void *val);
  void *pengu_cc_map_get(const PenguMap *map, const void *key);
  bool pengu_cc_map_remove(PenguMap *map, const void *key);
  void pengu_cc_map_clear(PenguMap *map);
  void pengu_cc_map_banish(PenguMap *map);
  PenguList pengu_cc_map_keys(const PenguMap *map);
  PenguList pengu_cc_map_values(const PenguMap *map);
  void pengu_cc_map_pin_sizes(PenguMap *map, size_t key_size, size_t val_size);

  /** Allocation-free map iterator used by `for k in map`. */
  typedef struct
  {
    const PenguMap *map;
    void *it;
  } PenguMapIter;

  PenguMapIter pengu_map_iter_begin(const PenguMap *map);
  bool pengu_map_iter_valid(const PenguMapIter *iter);
  void pengu_map_iter_advance(PenguMapIter *iter);
  const void *pengu_map_iter_key(const PenguMapIter *iter);

  /**
   * @brief Creates a new hash map.
   * @param key_size Size of key type in bytes.
   * @param val_size Size of value type in bytes.
   * @return Initialized PenguMap.
   */
  static inline PenguMap pengu_map_new(size_t key_size, size_t val_size)
  {
    PenguMap map;
    map.state = NULL;
    map.len = 0;
    map.cap = 0;
    map.key_size = key_size;
    map.val_size = val_size;
    pengu_cc_map_init(&map, key_size, val_size);
    return map;
  }

  /**
   * @brief Inserts or updates key-value pair in hash map.
   * @note Ante fallo de realloc/calloc o si la capacidad excede INT_MAX/2, rechaza silenciosamente sin modificar.
   * @param map Pointer to PenguMap.
   * @param key Pointer to key data.
   * @param val Pointer to value data.
   */
  static inline void pengu_map_put(PenguMap *map, const void *key, const void *val)
  {
    pengu_cc_map_put(map, key, val);
  }

  /**
   * @brief Retrieves value pointer corresponding to key in hash map.
   * @param map Pointer to const PenguMap.
   * @param key Pointer to key data.
   * @return Pointer to value or NULL if key not found.
   */
  static inline void *pengu_map_get(const PenguMap *map, const void *key)
  {
    return pengu_cc_map_get(map, key);
  }

  /**
   * @brief Checks if hash map contains a key.
   * @param map Pointer to const PenguMap.
   * @param key Pointer to key data.
   * @return True if key exists, False otherwise.
   */
  static inline bool pengu_map_contains(const PenguMap *map, const void *key)
  {
    return pengu_cc_map_get(map, key) != NULL;
  }

  /**
   * @brief Removes entry by key from hash map.
   * @param map Pointer to PenguMap.
   * @param key Pointer to key data.
   * @return True if entry was removed, False if not found.
   */
  static inline bool pengu_map_remove(PenguMap *map, const void *key)
  {
    return pengu_cc_map_remove(map, key);
  }

  /**
   * @brief Frees every entry of a hash map: each key/value byte block and the
   *        entry table itself.
   *
   * Values that own memory (a PenguString buffer, a nested container) are not
   * released — the map only owned their bytes, exactly like a C struct.
   *
   * @param map Pointer to PenguMap.
   */
  static inline void pengu_banish_map(PenguMap *map)
  {
    pengu_cc_map_banish(map);
  }

  /**
   * @brief Clears all entries in a PenguMap.
   * @param map Pointer to PenguMap.
   */
  static inline void pengu_map_clear(PenguMap *map)
  {
    pengu_cc_map_clear(map);
  }

  /** @brief Inserts or updates a string-to-int pair in the hash map.
   *
   * Same ownership rule as `pengu_map_put` (ABI v3): the map copies the
   * `PenguString` *bytes* with `memcpy` and never takes over the buffer the
   * string points at.  The caller keeps owning that buffer.
   *
   * `key_size`/`val_size` are (re)asserted here because this entry point is
   * string-to-int by construction: a map produced by `pengu_map_new(0, 0)`
   * would otherwise keep a zero `key_size` and every slot allocation would be
   * a zero-byte block written with `sizeof(PenguString)` bytes.
   */
  static inline void pengu_map_put_string_int(PenguMap *m, const PenguString *k, const int32_t *v)
  {
    if (!m || !k || !v)
      return;
    if (m->len == 0)
      pengu_cc_map_pin_sizes(m, sizeof(PenguString), sizeof(int32_t));
    pengu_cc_map_put(m, k, v);
  }

  /** @brief Retrieves pointer to int32 value for string key in hash map. */
  static inline int32_t *pengu_map_get_string_int(const PenguMap *m, const PenguString *k)
  {
    if (!m || !k || m->key_size != sizeof(PenguString))
      return NULL;
    return (int32_t *)pengu_cc_map_get(m, k);
  }

  /** @brief Checks if hash map contains string key. */
  static inline bool pengu_map_contains_string_int(const PenguMap *m, const PenguString *k)
  {
    return pengu_map_get_string_int(m, k) != NULL;
  }

  /** @brief Removes string key entry from hash map. */
  static inline bool pengu_map_remove_string_int(PenguMap *m, const PenguString *k)
  {
    if (!m || !k || m->key_size != sizeof(PenguString))
      return false;
    return pengu_cc_map_remove(m, k);
  }

/* =========================================================================
 * 9. Fixed-Size Array Macro
 * ========================================================================= */

/**
 * @brief Declares a fixed-size stack array structure with explicit length.
 */
#define PENGU_ARRAY_TYPE(T, N) \
  struct                       \
  {                            \
    T data[N];                 \
    int len;                   \
  }

  /* =========================================================================
   * 10. Global Runtime State & Core I/O (Spark & Whisper)
   * ========================================================================= */

  static int g_pengu_argc = 0;
  static char **g_pengu_argv = NULL;
  static int g_pengu_log_level = 0;

  /** @brief Collects the keys of a map into a list, copying their bytes.
   *
   * The list owns its own element buffer but not what the elements point at: a
   * PenguString key is copied by value and keeps aliasing the map's buffer.  The
   * map must outlive the list, or be released after it.
   */
  static inline PenguList pengu_map_keys(const PenguMap *m)
  {
    return pengu_cc_map_keys(m);
  }

  /**
   * @brief Collects the keys of a PenguString-keyed map into a list of strings.
   *
   * Each element is a *view* of the map's own key buffer (``is_owned == 0``), so
   * the list must not outlive the map and banishing both is safe.  Iterate the
   * map yourself if you need owned copies.
   */
  static inline PenguList pengu_map_keys_string(const PenguMap *m)
  {
    /* The result is a list of PenguString views, which only makes sense for a
     * map whose keys *are* PenguString: copying 'key_size' bytes of an int key
     * into a PenguString-shaped slot would read past the key. */
    if (!m || m->key_size != sizeof(PenguString))
      return pengu_list_new(sizeof(PenguString), 0);
    return pengu_map_keys(m);
  }

  /** @brief Collects the values of a map into a list, copying their bytes.
   *
   * Same aliasing rule as :func:`pengu_map_keys`: the list owns its element
   * buffer, the elements keep pointing into the map.
   */
  static inline PenguList pengu_map_values(const PenguMap *m)
  {
    return pengu_cc_map_values(m);
  }
  /**
   * @brief Initializes runtime command-line argument tracking.
   * @param argc Argument count.
   * @param argv Argument vector.
   */
  static inline void pengu_init(int argc, char **argv)
  {
    g_pengu_argc = argc;
    g_pengu_argv = argv;
  }

  /* pengu_print, pengu_println, pengu_input and pengu_panic moved to
   * std/spark.pengu (Chunk 1, 2.0 migration). See that module for the fd-2
   * stderr helpers, the flushing helpers, pengu_read_char, pengu_parse_int_radix
   * and pengu_exit, which are new. */

  /**
   * @brief Sets active global logging level.
   * @param level Integer level (0: TRACE, 1: DEBUG, 2: INFO, 3: WARN, 4: ERROR, 5: FATAL).
   */
  static inline void pengu_log_set_level(int level)
  {
    g_pengu_log_level = level;
  }

  /**
   * @brief Gets active global logging level.
   * @return Current log level.
   */
  static inline int pengu_log_get_level(void)
  {
    return g_pengu_log_level;
  }

  /* =========================================================================
   * 11. Mathematics & Numerics (Arithmancy)
   * ========================================================================= */

  static inline double pengu_c_fabs(double x) { return fabs(x); }
  static inline double pengu_c_sqrt(double x) { return sqrt(x); }
  static inline double pengu_c_pow(double x, double y) { return pow(x, y); }
  static inline double pengu_c_floor(double x) { return floor(x); }
  static inline double pengu_c_ceil(double x) { return ceil(x); }
  static inline double pengu_c_round(double x) { return round(x); }
  static inline double pengu_c_trunc(double x) { return trunc(x); }
  static inline double pengu_c_fmod(double x, double y) { return fmod(x, y); }
  static inline double pengu_c_sin(double x) { return sin(x); }
  static inline double pengu_c_cos(double x) { return cos(x); }
  static inline double pengu_c_tan(double x) { return tan(x); }
  static inline double pengu_c_asin(double x) { return asin(x); }
  static inline double pengu_c_acos(double x) { return acos(x); }
  static inline double pengu_c_atan(double x) { return atan(x); }
  static inline double pengu_c_atan2(double y, double x) { return atan2(y, x); }
  static inline double pengu_c_exp(double x) { return exp(x); }
  static inline double pengu_c_log(double x) { return log(x); }
  static inline double pengu_c_log10(double x) { return log10(x); }
  static inline double pengu_c_log2(double x) { return log2(x); }
  static inline double pengu_c_sinh(double x) { return sinh(x); }
  static inline double pengu_c_cosh(double x) { return cosh(x); }
  static inline double pengu_c_tanh(double x) { return tanh(x); }
  static inline double pengu_c_asinh(double x) { return asinh(x); }
  static inline double pengu_c_acosh(double x) { return acosh(x); }
  static inline double pengu_c_atanh(double x) { return atanh(x); }

  /* =========================================================================
   * 12. Time, Clocks & Calendar (Chronicle)
   * ========================================================================= */

  /** @brief Returns UNIX timestamp in seconds. */
  static inline double pengu_c_time(void) { return (double)time(NULL); }

  /** @brief Returns high-resolution monotonic time in seconds. */
  static inline double pengu_c_time_monotonic(void)
  {
#if PENGU_WINDOWS
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)freq.QuadPart;
#else
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
#endif
  }

  /** @brief Sleeps current thread for specified milliseconds. */
  static inline void pengu_c_sleep_ms(int ms)
  {
    if (ms <= 0)
      return;
#if PENGU_WINDOWS
    Sleep((DWORD)ms);
#else
  struct timespec req;
  req.tv_sec = ms / 1000;
  req.tv_nsec = (long)(ms % 1000) * 1000000L;
  nanosleep(&req, NULL);
#endif
  }

  /** @brief Sleeps current thread for specified fractional seconds. */
  static inline void pengu_c_sleep_sec(double sec)
  {
    if (sec <= 0.0)
      return;
    pengu_c_sleep_ms((int)(sec * 1000.0));
  }

  /**
   * @brief Formats timestamp using strftime format pattern.
   * @note Si el timestamp está fuera de rango o gmtime falla, retorna cadena vacía.
   * @note El buffer local es de 512 bytes. Formatos que produzcan
   *       resultados mayores (p.ej. `%c` con texto local largo o formatos
   *       definidos por el usuario con mucho texto literal) pueden
   *       retornar cadena vacía por truncamiento de strftime. Los formatos
   *       estándar (`%Y-%m-%d %H:%M:%S`, `%F %T`, etc.) nunca exceden ese
   *       tamaño.
   * @note Copia fmt a un búfer temporal NUL-terminado para evitar lecturas fuera de rango.
   */
  static inline PenguString pengu_c_strftime(PenguString fmt, double timestamp)
  {
    time_t t = (time_t)timestamp;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0)
      return pengu_string_from_cstr("");
#else
    if (!gmtime_r(&t, &tm_info))
      return pengu_string_from_cstr("");
#endif
    char *cfmt = NULL;
    if (fmt.data && fmt.len > 0)
    {
      cfmt = (char *)malloc((size_t)fmt.len + 1);
      if (!cfmt)
        return pengu_string_from_cstr("");
      memcpy(cfmt, fmt.data, (size_t)fmt.len);
      cfmt[fmt.len] = '\0';
    }
    char buf[512];
    size_t len = strftime(buf, sizeof(buf), cfmt ? cfmt : "%Y-%m-%d %H:%M:%S", &tm_info);
    if (cfmt)
      free(cfmt);
    return (len > 0) ? pengu_string_new(buf) : pengu_string_from_cstr("");
  }

  /**
   * @brief Parses timestamp string into seconds.
   * @note Copia s a un búfer temporal NUL-terminado antes de invocar sscanf para
   *       evitar lecturas fuera de rango sobre vistas no NUL-terminadas.
   */
  static inline PenguMaybe pengu_c_strptime(PenguString s, PenguString fmt)
  {
    (void)fmt;
    if (!s.data || s.len <= 0)
      return pengu_maybe_none();
    char *tmp = (char *)malloc((size_t)s.len + 1);
    if (!tmp)
      return pengu_maybe_none();
    memcpy(tmp, s.data, (size_t)s.len);
    tmp[s.len] = '\0';
    struct tm tm_val;
    memset(&tm_val, 0, sizeof(tm_val));
    int y = 0, m = 0, d = 0, h = 0, min = 0, sec = 0;
    bool parsed = (sscanf(tmp, "%d-%d-%dT%d:%d:%d", &y, &m, &d, &h, &min, &sec) >= 3 ||
                   sscanf(tmp, "%d-%d-%d", &y, &m, &d) >= 3);
    free(tmp);
    if (parsed)
    {
      tm_val.tm_year = y - 1900;
      tm_val.tm_mon = m - 1;
      tm_val.tm_mday = d;
      tm_val.tm_hour = h;
      tm_val.tm_min = min;
      tm_val.tm_sec = sec;
      time_t t = mktime(&tm_val);
      if (t != (time_t)-1)
      {
        double *res = (double *)malloc(sizeof(double));
        if (!res)
          return pengu_maybe_none();
        *res = (double)t;
        return pengu_maybe_some(res);
      }
    }
    return pengu_maybe_none();
  }

  /* UTC Calendar Component Getters */
  /** @brief Returns UTC year (e.g. 2026). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_year(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_year + 1900;
  }
  /** @brief Returns UTC month (1-12). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_month(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_mon + 1;
  }
  /** @brief Returns UTC day of month (1-31). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_day(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_mday;
  }
  /** @brief Returns UTC hour (0-23). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_hour(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_hour;
  }
  /** @brief Returns UTC minute (0-59). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_minute(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_min;
  }
  /** @brief Returns UTC second (0-60). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_second(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_sec;
  }
  /** @brief Returns UTC weekday (0=Sunday .. 6=Saturday). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_weekday(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_wday;
  }
  /** @brief Returns UTC yearday (0-365). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_utc_yearday(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!gmtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_yday;
  }
  /** @brief Returns whether UTC observes DST. @note Retorna false si el timestamp es inválido/fuera de rango. */
  static inline bool pengu_c_get_utc_is_dst(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (gmtime_s(&tm_info, &t) != 0) return false;
#else
    if (!gmtime_r(&t, &tm_info)) return false;
#endif
    return tm_info.tm_isdst > 0;
  }

  /* Local Calendar Component Getters */
  /** @brief Returns local year (e.g. 2026). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_year(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_year + 1900;
  }
  /** @brief Returns local month (1-12). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_month(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_mon + 1;
  }
  /** @brief Returns local day of month (1-31). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_day(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_mday;
  }
  /** @brief Returns local hour (0-23). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_hour(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_hour;
  }
  /** @brief Returns local minute (0-59). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_minute(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_min;
  }
  /** @brief Returns local second (0-60). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_second(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_sec;
  }
  /** @brief Returns local weekday (0=Sunday .. 6=Saturday). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_weekday(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_wday;
  }
  /** @brief Returns local yearday (0-365). @note Retorna 0 si el timestamp es inválido/fuera de rango. */
  static inline int pengu_c_get_local_yearday(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return 0;
#else
    if (!localtime_r(&t, &tm_info)) return 0;
#endif
    return tm_info.tm_yday;
  }
  /** @brief Returns whether local time observes DST. @note Retorna false si el timestamp es inválido/fuera de rango. */
  static inline bool pengu_c_get_local_is_dst(double ts)
  {
    time_t t = (time_t)ts;
    struct tm tm_info;
#if PENGU_WINDOWS
    if (localtime_s(&tm_info, &t) != 0) return false;
#else
    if (!localtime_r(&t, &tm_info)) return false;
#endif
    return tm_info.tm_isdst > 0;
  }

  /* =========================================================================
   * 13. Random & Distributions (Lot)
   * ========================================================================= */

  static inline void pengu_c_srand(int seed) { srand((unsigned int)seed); }
  static inline int pengu_c_rand(void) { return rand(); }
  static inline int pengu_c_rand_max(void) { return RAND_MAX; }
  static inline double pengu_c_rand_double(void) { return (double)rand() / ((double)RAND_MAX + 1.0); }
  static inline int pengu_c_rand_range(int min, int max)
  {
    if (min >= max)
      return min;
    double range = (double)max - (double)min + 1.0;
    /* El cast a int de un double > INT_MAX es UB; usar int64_t como
       intermediario y sumar en 64 bits antes de estrechar a int. */
    int64_t offset = (int64_t)(pengu_c_rand_double() * range);
    return (int)((int64_t)min + offset);
  }
  static inline double pengu_c_rand_range_float(double min, double max)
  {
    if (min >= max)
      return min;
    return min + pengu_c_rand_double() * (max - min);
  }
  static inline double pengu_c_rand_normal(double mean, double stddev)
  {
    double u1 = pengu_c_rand_double();
    double u2 = pengu_c_rand_double();
    while (u1 <= 1e-15)
      u1 = pengu_c_rand_double();
    double z0 = sqrt(-2.0 * log(u1)) * cos(2.0 * 3.14159265358979323846 * u2);
    return mean + z0 * stddev;
  }
  static inline double pengu_c_rand_exp(double lambda)
  {
    if (lambda <= 0.0)
      return 0.0;
    double u = pengu_c_rand_double();
    while (u <= 1e-15)
      u = pengu_c_rand_double();
    return -log(u) / lambda;
  }
  static inline bool pengu_c_rand_bool(double probability) { return pengu_c_rand_double() < probability; }
  static inline int pengu_c_rand_poisson(double lambda)
  {
    if (lambda <= 0.0)
      return 0;
    double L = exp(-lambda);
    double k = 0, p = 1.0;
    do
    {
      k += 1.0;
      p *= pengu_c_rand_double();
    } while (p > L);
    return (int)(k - 1.0);
  }

  /* =========================================================================
   * 14. Process & Operating System Environment (Rites)
   * ========================================================================= */

  /**
   * @brief Retrieves environment variable value.
   * @note Copia name a un búfer temporal NUL-terminado para soportar vistas no NUL-terminadas.
   */
  static inline PenguMaybe pengu_c_getenv(PenguString name)
  {
    if (!name.data || name.len <= 0)
      return pengu_maybe_none();
    char *cname = (char *)malloc((size_t)name.len + 1);
    if (!cname)
      return pengu_maybe_none();
    memcpy(cname, name.data, (size_t)name.len);
    cname[name.len] = '\0';
    const char *val = getenv(cname);
    free(cname);
    if (!val)
      return pengu_maybe_none();
    PenguString *res = (PenguString *)malloc(sizeof(PenguString));
    if (!res)
      return pengu_maybe_none();
    *res = pengu_string_new(val);
    return pengu_maybe_some(res);
  }

  /**
   * @brief Sets environment variable.
   * @note Copia name y value a búferes temporales NUL-terminados para soportar vistas no NUL-terminadas.
   */
  static inline bool pengu_c_setenv(PenguString name, PenguString value, bool overwrite)
  {
    if (!name.data || name.len <= 0)
      return false;
    char *cname = (char *)malloc((size_t)name.len + 1);
    if (!cname)
      return false;
    memcpy(cname, name.data, (size_t)name.len);
    cname[name.len] = '\0';

    char *cval = NULL;
    if (value.data && value.len > 0)
    {
      cval = (char *)malloc((size_t)value.len + 1);
      if (!cval)
      {
        free(cname);
        return false;
      }
      memcpy(cval, value.data, (size_t)value.len);
      cval[value.len] = '\0';
    }
    const char *v = cval ? cval : "";

#if PENGU_WINDOWS
    if (!overwrite && getenv(cname) != NULL)
    {
      free(cname);
      if (cval)
        free(cval);
      return true;
    }
    int r = _putenv_s(cname, v);
#else
    int r = setenv(cname, v, overwrite ? 1 : 0);
#endif
    free(cname);
    if (cval)
      free(cval);
    return r == 0;
  }

  /**
   * @brief Unsets environment variable.
   * @note Copia name a un búfer temporal NUL-terminado para soportar vistas no NUL-terminadas.
   */
  static inline bool pengu_c_unsetenv(PenguString name)
  {
    if (!name.data || name.len <= 0)
      return false;
    char *cname = (char *)malloc((size_t)name.len + 1);
    if (!cname)
      return false;
    memcpy(cname, name.data, (size_t)name.len);
    cname[name.len] = '\0';
#if PENGU_WINDOWS
    int r = _putenv_s(cname, "");
#else
    int r = unsetenv(cname);
#endif
    free(cname);
    return r == 0;
  }

  static inline int pengu_c_get_argc(void) { return g_pengu_argc; }
  static inline PenguString pengu_c_get_argv(int idx)
  {
    if (idx < 0 || idx >= g_pengu_argc || !g_pengu_argv)
      return pengu_string_from_cstr("");
    return pengu_string_new(g_pengu_argv[idx]);
  }
  static inline PenguList pengu_c_get_args(void)
  {
    PenguList list = pengu_list_new(sizeof(PenguString), (size_t)(g_pengu_argc > 0 ? g_pengu_argc : 1));
    for (int i = 0; i < g_pengu_argc; ++i)
    {
      /* Owned copies: the returned list must not alias argv. */
      PenguString s = pengu_string_new(g_pengu_argv[i]);
      pengu_list_push(&list, &s);
    }
    return list;
  }

  static inline int pengu_c_getpid(void)
  {
#if PENGU_WINDOWS
    return (int)_getpid();
#else
  return (int)getpid();
#endif
  }
  static inline int pengu_c_getppid(void)
  {
#if PENGU_WINDOWS
    return 0;
#else
  return (int)getppid();
#endif
  }

  /**
   * @brief Gets current working directory.
   * @note En POSIX utiliza getcwd(NULL, 0) (extensión GNU/BSD) con asignación dinámica;
   *       en Windows utiliza un búfer de stack y escala dinámicamente si la ruta excede el tamaño.
   */
  static inline PenguMaybe pengu_c_getcwd(void)
  {
#if PENGU_WINDOWS
    char stack_buf[4096];
    char *cwd = _getcwd(stack_buf, sizeof(stack_buf));
    char *dyn = NULL;
    if (!cwd)
    {
      size_t sz = 8192;
      while (!cwd && sz <= 65536)
      {
        dyn = (char *)malloc(sz);
        if (!dyn)
          break;
        cwd = _getcwd(dyn, (int)sz);
        if (cwd)
          break;
        free(dyn);
        dyn = NULL;
        sz *= 2;
      }
    }
    if (cwd)
    {
      PenguString *res = (PenguString *)malloc(sizeof(PenguString));
      if (res)
      {
        *res = pengu_string_new(cwd);
        if (dyn)
          free(dyn);
        return pengu_maybe_some(res);
      }
    }
    if (dyn)
      free(dyn);
    return pengu_maybe_none();
#else
    char *cwd = getcwd(NULL, 0);
    if (!cwd)
      return pengu_maybe_none();
    PenguString *res = (PenguString *)malloc(sizeof(PenguString));
    if (!res)
    {
      free(cwd);
      return pengu_maybe_none();
    }
    *res = pengu_string_new(cwd);
    free(cwd);
    return pengu_maybe_some(res);
#endif
  }

  /**
   * @brief Changes current working directory.
   * @note Copia path a un búfer temporal NUL-terminado para soportar vistas no NUL-terminadas.
   */
  static inline bool pengu_c_chdir(PenguString path)
  {
    if (!path.data || path.len <= 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    int r = _chdir(cpath);
#else
    int r = chdir(cpath);
#endif
    free(cpath);
    return r == 0;
  }

  static inline void pengu_c_exit(int code) { exit(code); }

  /**
   * @brief Executes a command line with arguments via system().
   * @warning Uses system() internally; do NOT pass untrusted user input in cmd/args
   *          without proper sanitization.
   * @note On WebAssembly (Emscripten) there is no process to spawn: the function
   *       reports the failure on stderr and returns -1 without calling system().
   *       See `docs/WASM.md` for the rationale and the alternatives.
   * @param cmd Command string.
   * @param args List of PenguString argument tokens.
   * @return Return code from system(), or -1 on buffer allocation failure. Always
   *         -1 under `PENGU_EMSCRIPTEN`.
   */
  static inline int pengu_c_exec(PenguString cmd, PenguList args)
  {
#if PENGU_EMSCRIPTEN
    /* `system()` exists in the Emscripten libc but is a stub: in the browser it
     * cannot work at all, and in Node it would need a synchronous spawn that
     * blocks the event loop.  Failing loudly beats a silent no-op that reports
     * success (Emscripten's stub returns a status the caller would misread). */
    (void)cmd;
    (void)args;
    fprintf(stderr, "[PENGU] exec no soportado en wasm\n");
    return -1;
#else
    if (!cmd.data || cmd.len == 0)
      return -1;
    size_t total_len = (size_t)cmd.len + 1;
    for (int i = 0; i < args.len; ++i)
    {
      PenguString *a = (PenguString *)pengu_list_at(&args, i);
      if (a && a->data && a->len > 0)
      {
        total_len += (size_t)a->len + 1;
      }
    }
    char stack_buf[4096];
    char *cmdbuf = stack_buf;
    bool heap = false;
    if (total_len > sizeof(stack_buf))
    {
      cmdbuf = (char *)malloc(total_len);
      if (!cmdbuf)
        return -1;
      heap = true;
    }
    size_t pos = (size_t)cmd.len;
    memcpy(cmdbuf, cmd.data, (size_t)cmd.len);
    cmdbuf[pos] = '\0';
    for (int i = 0; i < args.len; ++i)
    {
      PenguString *a = (PenguString *)pengu_list_at(&args, i);
      if (a && a->data && a->len > 0)
      {
        cmdbuf[pos++] = ' ';
        memcpy(cmdbuf + pos, a->data, (size_t)a->len);
        pos += (size_t)a->len;
        cmdbuf[pos] = '\0';
      }
    }
    const char *script = cmdbuf;
#if PENGU_WINDOWS
    /* `system()` runs `%COMSPEC% /c <command>` and cmd.exe has a legacy
     * heuristic: when the command line starts with a quote and contains more
     * than two quotes, it strips the FIRST and LAST quote before parsing.
     * A perfectly ordinary command built with `rites.shell_escape` — e.g.
     * `"C:\mingw64\bin\gcc.exe" -c "c\x.c" -o "lib\x.o"` — therefore reaches
     * cmd.exe as `C:\mingw64\bin\gcc.exe" -c ... "lib\x.o` and fails with
     * "not recognized as an internal or external command".  This broke
     * `build.pengu` on Windows for every binding: the generated script quotes
     * the resolved `cc`/`ar`, so `pengu add --trust` warned and never produced
     * lib/lib<name>.a.
     *
     * Wrapping the whole line in one extra pair of quotes is the documented
     * workaround: cmd.exe strips that outer pair instead, leaving the intended
     * command line byte-for-byte intact.  Shell operators after the program
     * (redirection, pipes) still work because the outer quotes are removed
     * before cmd.exe parses them.  Only lines whose first character is a quote
     * need this; anything else (`echo hi > out`) is passed through untouched. */
    char *wrapped = NULL;
    if (cmdbuf[0] == '"')
    {
      wrapped = (char *)malloc(total_len + 2u);
      if (!wrapped)
      {
        if (heap)
          free(cmdbuf);
        return -1;
      }
      wrapped[0] = '"';
      memcpy(wrapped + 1, cmdbuf, total_len);
      wrapped[total_len] = '"';
      wrapped[total_len + 1] = '\0';
      script = wrapped;
    }
#endif
    int res = system(script);
#if PENGU_WINDOWS
    if (wrapped)
      free(wrapped);
#endif
    if (heap)
      free(cmdbuf);
    return res;
#endif /* PENGU_EMSCRIPTEN */
  }

  /**
   * @brief Spawns a command line with arguments (non-blocking alias of exec()).
   * @note Under `PENGU_EMSCRIPTEN` this inherits the -1 result and the stderr
   *       diagnostic of pengu_c_exec(); no process can be spawned in wasm.
   */
  static inline int pengu_c_spawn(PenguString cmd, PenguList args)
  {
    return pengu_c_exec(cmd, args);
  }

  static inline PenguString pengu_c_uname(void)
  {
#if PENGU_WINDOWS
    return pengu_string_from_cstr("Windows");
#elif defined(__APPLE__)
  return pengu_string_from_cstr("Darwin");
#elif defined(__linux__)
  return pengu_string_from_cstr("Linux");
#else
  return pengu_string_from_cstr("Unknown");
#endif
  }

  static inline PenguString pengu_c_arch(void)
  {
#if defined(__aarch64__) || defined(_M_ARM64)
    return pengu_string_from_cstr("arm64");
#elif defined(__x86_64__) || defined(_M_X64)
    return pengu_string_from_cstr("x64");
#elif defined(__i386__) || defined(_M_IX86)
    return pengu_string_from_cstr("x86");
#elif defined(__arm__) || defined(_M_ARM)
    return pengu_string_from_cstr("arm");
#else
    return pengu_string_from_cstr("unknown");
#endif
  }

  static inline PenguString pengu_c_hostname(void)
  {
    char buf[256];
#if PENGU_WINDOWS
    DWORD len = sizeof(buf);
    if (GetComputerNameA(buf, &len))
    {
      return pengu_string_new(buf);
    }
#else
  if (gethostname(buf, sizeof(buf)) == 0)
  {
    return pengu_string_new(buf);
  }
#endif
    return pengu_string_from_cstr("localhost");
  }

  /**
   * @brief Returns a list of environment variable names.
   * @note Las claves se devuelven completas y sin límite artificial en ambas plataformas.
   */
  static inline PenguList pengu_c_get_env_keys(void)
  {
    PenguList list = pengu_list_new(sizeof(PenguString), 16);
#if PENGU_WINDOWS
    char *env = GetEnvironmentStringsA();
    if (env)
    {
      char *p = env;
      while (*p)
      {
        char *eq = strchr(p, '=');
        if (eq && eq != p)
        {
          int klen = (int)(eq - p);
          /* Owned copy of the name only (the value stays in the environment
           * block, which is released right after the loop). */
          PenguString kview = {p, klen, 0};
          PenguString kstr = pengu_string_copy(kview);
          pengu_list_push(&list, &kstr);
        }
        p += strlen(p) + 1;
      }
      FreeEnvironmentStringsA(env);
    }
#else
    extern char **environ;
    if (environ)
    {
      for (char **env = environ; *env; ++env)
      {
        const char *eq = strchr(*env, '=');
        if (eq && eq != *env)
        {
          int klen = (int)(eq - *env);
          /* Owned copy of the name only: 'environ' is not ours to alias. */
          PenguString kview = {*env, klen, 0};
          PenguString kstr = pengu_string_copy(kview);
          pengu_list_push(&list, &kstr);
        }
      }
    }
#endif
    return list;
  }

  static inline void pengu_c_sleep_ms_rites(int ms) { pengu_c_sleep_ms(ms); }

  /* =========================================================================
   * NOTE: The Scrolls string utilities (scrolls_len ... scrolls_reverse) were
   * migrated to pure PenguScript in std/scrolls.pengu and are no longer
   * implemented in this header.
   * ========================================================================= */

  /* =========================================================================
   * 17. File System & I/O Operations (Archivum)
   * ========================================================================= */

  /** @brief Reads entire file into a PenguString.
   * A present result holds a heap PenguString* that owns an SDS buffer: the
   * caller must free the buffer with pengu_banish_string() and the wrapper with
   * free().
   * @note Archivos que excedan INT_MAX bytes se rechazan (retorna none) para
   *       evitar truncación silenciosa al asignarse a int len. En plataformas LLP64
   *       (Windows), ftell retorna long de 32 bits, por lo que archivos > 2 GB no son
   *       leíbles (ftell retorna -1); el chequeo sz > INT_MAX aplica plenamente en LP64. */
  static inline PenguMaybe pengu_c_archivum_read_file(PenguString path)
  {
    if (!path.data || path.len == 0)
      return pengu_maybe_none();
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "rb");
    free(cpath);
    if (!f)
      return pengu_maybe_none();
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 0 || sz > (long)INT_MAX)
    {
      fclose(f);
      return pengu_maybe_none();
    }
    sds buf = sdsnewlen(NULL, (size_t)sz);
    if (!buf)
    {
      fclose(f);
      return pengu_maybe_none();
    }
    size_t read_bytes = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    PenguString *res = (PenguString *)malloc(sizeof(PenguString));
    if (!res)
    {
      sdsfree(buf);
      return pengu_maybe_none();
    }
    if (read_bytes == 0)
    {
      sdsfree(buf);
      res->data = (char *)"";
      res->len = 0;
      res->is_owned = PENGU_STRING_BORROWED;
    }
    else
    {
      *res = pengu_string_owned_from_sds_len(buf, (int)read_bytes);
    }
    return pengu_maybe_some(res);
  }

  /** @brief Writes string content to a file, overwriting existing content. */
  static inline bool pengu_c_archivum_write_file(PenguString path, PenguString content)
  {
    if (!path.data)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "wb");
    free(cpath);
    if (!f)
      return false;
    if (content.data && content.len > 0)
    {
      fwrite(content.data, 1, (size_t)content.len, f);
    }
    fclose(f);
    return true;
  }

  /** @brief Appends string content to a file. */
  static inline bool pengu_c_archivum_append_file(PenguString path, PenguString content)
  {
    if (!path.data)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "ab");
    free(cpath);
    if (!f)
      return false;
    if (content.data && content.len > 0)
    {
      fwrite(content.data, 1, (size_t)content.len, f);
    }
    fclose(f);
    return true;
  }

  /** @brief Deletes a file. */
  static inline bool pengu_c_archivum_delete_file(PenguString path)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    int res = remove(cpath);
    free(cpath);
    return res == 0;
  }

  /** @brief Checks if a path exists. */
  static inline bool pengu_c_archivum_exists(PenguString path)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES);
#else
  struct stat st;
  int res = stat(cpath, &st);
  free(cpath);
  return res == 0;
#endif
  }

  /** @brief Checks if path is a regular file. */
  static inline bool pengu_c_archivum_is_file(PenguString path)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES) && !(attr & FILE_ATTRIBUTE_DIRECTORY);
#else
  struct stat st;
  int res = stat(cpath, &st);
  free(cpath);
  return (res == 0) && S_ISREG(st.st_mode);
#endif
  }

  /** @brief Checks if path is a directory. */
  static inline bool pengu_c_archivum_is_dir(PenguString path)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES) && (attr & FILE_ATTRIBUTE_DIRECTORY);
#else
  struct stat st;
  int res = stat(cpath, &st);
  free(cpath);
  return (res == 0) && S_ISDIR(st.st_mode);
#endif
  }

  /** @brief Checks if path is a symbolic link. */
  static inline bool pengu_c_archivum_is_symlink(PenguString path)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    DWORD attr = GetFileAttributesA(cpath);
    free(cpath);
    return (attr != INVALID_FILE_ATTRIBUTES) && (attr & FILE_ATTRIBUTE_REPARSE_POINT);
#else
  struct stat st;
  int res = lstat(cpath, &st);
  free(cpath);
  return (res == 0) && S_ISLNK(st.st_mode);
#endif
  }

  /** @brief Creates directory. */
  static inline bool pengu_c_archivum_create_dir(PenguString path, bool parents)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    if (!parents)
    {
#if PENGU_WINDOWS
      int r = _mkdir(cpath);
#else
    int r = mkdir(cpath, 0755);
#endif
      free(cpath);
      return (r == 0 || pengu_c_archivum_is_dir(path));
    }
    for (int i = 0; i < path.len; ++i)
    {
      if (cpath[i] == '/' || cpath[i] == '\\')
      {
        if (i == 0 || (i == 2 && cpath[1] == ':'))
          continue;
        char tmp = cpath[i];
        cpath[i] = '\0';
#if PENGU_WINDOWS
        _mkdir(cpath);
#else
      mkdir(cpath, 0755);
#endif
        cpath[i] = tmp;
      }
    }
#if PENGU_WINDOWS
    _mkdir(cpath);
#else
  mkdir(cpath, 0755);
#endif
    bool ok = pengu_c_archivum_is_dir(path);
    free(cpath);
    return ok;
  }

  /** @brief Lists directory entries.
 * A present result holds a heap PenguList* of heap PenguString* entries, all
 * of which the caller owns: banish each entry buffer + wrapper, then
 * pengu_banish_list() the list and free() the heap list wrapper. */
  static inline PenguMaybe pengu_c_archivum_read_dir(PenguString path);

  /**
   * @brief Removes directory optionally recursively.
   * @note Los paths se construyen con snprintf/%.*s y por tanto truncan
   *       en el primer byte NUL embebido. En sistemas POSIX/Windows reales
   *       los nombres de fichero y directorio no pueden contener NUL, así
   *       que este truncamiento es teórico.
   */
  static inline bool pengu_c_archivum_remove_dir(PenguString path, bool recursive)
  {
    if (!path.data || path.len == 0)
      return false;
    if (!recursive)
    {
      char *cpath = (char *)malloc((size_t)path.len + 1);
      if (!cpath)
        return false;
      memcpy(cpath, path.data, (size_t)path.len);
      cpath[path.len] = '\0';
#if PENGU_WINDOWS
      int r = _rmdir(cpath);
#else
    int r = rmdir(cpath);
#endif
      free(cpath);
      return r == 0;
    }
    PenguMaybe m_entries = pengu_c_archivum_read_dir(path);
    if (m_entries.is_present && m_entries.value)
    {
      PenguList *entries = (PenguList *)m_entries.value;
      for (int i = 0; i < entries->len; ++i)
      {
        PenguString *name = (PenguString *)pengu_list_at(entries, i);
        char sep =
#if PENGU_WINDOWS
            '\\';
#else
          '/';
#endif
        char subpath[4096];
        int needed = snprintf(subpath, sizeof(subpath), "%.*s%c%.*s", path.len, path.data, sep, name->len, name->data);
        char *allocated_subpath = NULL;
        char *target_path = subpath;
        if (needed < 0)
          continue;
        if ((size_t)needed >= sizeof(subpath))
        {
          allocated_subpath = (char *)malloc((size_t)needed + 1);
          if (!allocated_subpath)
            continue; /* evita operar sobre path truncado */
          snprintf(allocated_subpath, (size_t)needed + 1, "%.*s%c%.*s", path.len, path.data, sep, name->len, name->data);
          target_path = allocated_subpath;
        }
        PenguString sub_str = pengu_string_from_cstr(target_path);
        if (pengu_c_archivum_is_dir(sub_str))
        {
          pengu_c_archivum_remove_dir(sub_str, true);
        }
        else
        {
          pengu_c_archivum_delete_file(sub_str);
        }
        if (allocated_subpath)
          free(allocated_subpath);
      }
      pengu_banish_string_list(entries);
      free(entries);
    }
    return pengu_c_archivum_remove_dir(path, false);
  }

  /**
   * @brief Reads entries within a directory.
   * @note Los paths se construyen con snprintf/%.*s y por tanto truncan
   *       en el primer byte NUL embebido. En sistemas POSIX/Windows reales
   *       los nombres de fichero y directorio no pueden contener NUL, así
   *       que este truncamiento es teórico.
   */
  static inline PenguMaybe pengu_c_archivum_read_dir(PenguString path)
  {
    if (!path.data || path.len == 0)
      return pengu_maybe_none();
    PenguList *list = (PenguList *)malloc(sizeof(PenguList));
    if (!list)
      return pengu_maybe_none();
    *list = pengu_list_new(sizeof(PenguString), 16);

#if PENGU_WINDOWS
    char pattern[4096];
    int needed = snprintf(pattern, sizeof(pattern), "%.*s\\*", path.len, path.data);
    char *allocated_pattern = NULL;
    char *target_pattern = pattern;
    if (needed < 0)
    {
      pengu_banish_list(list);
      free(list);
      return pengu_maybe_none();
    }
    if ((size_t)needed >= sizeof(pattern))
    {
      allocated_pattern = (char *)malloc((size_t)needed + 1);
      if (!allocated_pattern)
      {
        pengu_banish_list(list);
        free(list);
        return pengu_maybe_none();
      }
      snprintf(allocated_pattern, (size_t)needed + 1, "%.*s\\*", path.len, path.data);
      target_pattern = allocated_pattern;
    }
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA(target_pattern, &fd);
    if (allocated_pattern)
      free(allocated_pattern);
    if (hFind == INVALID_HANDLE_VALUE)
    {
      pengu_banish_list(list);
      free(list);
      return pengu_maybe_none();
    }
    do
    {
      if (strcmp(fd.cFileName, ".") != 0 && strcmp(fd.cFileName, "..") != 0)
      {
        PenguString name = pengu_string_new(fd.cFileName);
        pengu_list_push(list, &name);
      }
    } while (FindNextFileA(hFind, &fd));
    FindClose(hFind);
#else
  char *cpath = (char *)malloc((size_t)path.len + 1);
  if (!cpath)
  {
    pengu_banish_list(list);
    free(list);
    return pengu_maybe_none();
  }
  memcpy(cpath, path.data, (size_t)path.len);
  cpath[path.len] = '\0';
  DIR *d = opendir(cpath);
  free(cpath);
  if (!d)
  {
    pengu_banish_list(list);
    free(list);
    return pengu_maybe_none();
  }
  struct dirent *dir;
  while ((dir = readdir(d)) != NULL)
  {
    if (strcmp(dir->d_name, ".") != 0 && strcmp(dir->d_name, "..") != 0)
    {
      PenguString name = pengu_string_new(dir->d_name);
      pengu_list_push(list, &name);
    }
  }
  closedir(d);
#endif
    return pengu_maybe_some(list);
  }

  static inline bool pengu_c_archivum_copy_file(PenguString src, PenguString dst, bool overwrite)
  {
    if (!src.data || !dst.data)
      return false;
    if (!overwrite && pengu_c_archivum_exists(dst))
      return false;
    PenguMaybe m_content = pengu_c_archivum_read_file(src);
    if (!m_content.is_present || !m_content.value)
      return false;
    PenguString *content = (PenguString *)m_content.value;
    bool ok = pengu_c_archivum_write_file(dst, *content);
    pengu_banish_string(content);
    free(content);
    return ok;
  }

  static inline bool pengu_c_archivum_move_file(PenguString src, PenguString dst, bool overwrite)
  {
    if (!src.data || !dst.data)
      return false;
    if (!overwrite && pengu_c_archivum_exists(dst))
      return false;
    char *csrc = (char *)malloc((size_t)src.len + 1);
    char *cdst = (char *)malloc((size_t)dst.len + 1);
    if (!csrc || !cdst)
    {
      free(csrc);
      free(cdst);
      return false;
    }
    memcpy(csrc, src.data, (size_t)src.len);
    csrc[src.len] = '\0';
    memcpy(cdst, dst.data, (size_t)dst.len);
    cdst[dst.len] = '\0';
    if (overwrite)
      remove(cdst);
    int r = rename(csrc, cdst);
    free(csrc);
    free(cdst);
    if (r == 0)
      return true;
    if (pengu_c_archivum_copy_file(src, dst, overwrite))
    {
      pengu_c_archivum_delete_file(src);
      return true;
    }
    return false;
  }

  static inline bool pengu_c_archivum_rename(PenguString old_p, PenguString new_p)
  {
    return pengu_c_archivum_move_file(old_p, new_p, true);
  }

  /** @brief Reads file metadata as a PenguString-keyed map.
 * A present result holds a heap PenguMap* the caller owns: banish the map
 * (pengu_banish_map) and free() the heap wrapper. */
  /* The returned map owns every key and value: each is an allocated copy
   * ('pengu_string_new'), because 'map.put' only stores the bytes of the
   * PenguString header and would otherwise alias 'buf'.  Release the map with
   * pengu_banish_map, then each value with pengu_banish_string. */
  static inline PenguMaybe pengu_c_archivum_metadata(PenguString path)
  {
    if (!path.data || path.len == 0)
      return pengu_maybe_none();
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    struct stat st;
    int r = stat(cpath, &st);
    free(cpath);
    if (r != 0)
      return pengu_maybe_none();

    PenguMap *map = (PenguMap *)malloc(sizeof(PenguMap));
    if (!map)
      return pengu_maybe_none();
    *map = pengu_map_new(sizeof(PenguString), sizeof(PenguString));
    if (!map->state)
    {
      free(map);
      return pengu_maybe_none();
    }

    char buf[64];
    PenguString k, v;

    k = pengu_string_new("size");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_size);
    v = pengu_string_new(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("is_file");
    v = S_ISREG(st.st_mode) ? pengu_string_new("true") : pengu_string_new("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("is_dir");
    v = S_ISDIR(st.st_mode) ? pengu_string_new("true") : pengu_string_new("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("is_symlink");
    v = pengu_c_archivum_is_symlink(path) ? pengu_string_new("true") : pengu_string_new("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("modified");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_mtime);
    v = pengu_string_new(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("created");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_ctime);
    v = pengu_string_new(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("accessed");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_atime);
    v = pengu_string_new(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_new("permissions");
    snprintf(buf, sizeof(buf), "%d", (int)(st.st_mode & 0777));
    v = pengu_string_new(buf);
    pengu_map_put(map, &k, &v);

    return pengu_maybe_some(map);
  }

  /**
   * @brief Helper recursivo para pengu_c_archivum_glob.
   * @note El matching es binario-exacto (NUL-aware) usando pengu__find_sub y memcmp.
   * @note Los paths se construyen con snprintf/%.*s y por tanto truncan
   *       en el primer byte NUL embebido. En sistemas POSIX/Windows reales
   *       los nombres de fichero y directorio no pueden contener NUL, así
   *       que este truncamiento es teórico.
   */
  static inline void pengu_c_archivum_glob_rec(const char *dir_path, PenguString pattern, PenguList *res)
  {
    PenguString p_str = pengu_string_from_cstr(dir_path);
    PenguMaybe m_entries = pengu_c_archivum_read_dir(p_str);
    if (!m_entries.is_present || !m_entries.value)
      return;
    PenguList *entries = (PenguList *)m_entries.value;
    for (int i = 0; i < entries->len; ++i)
    {
      PenguString *name = (PenguString *)pengu_list_at(entries, i);
      char full[4096];
      int needed = snprintf(full, sizeof(full), "%s/%s", dir_path, name->data);
      char *allocated_full = NULL;
      char *target_full = full;
      if (needed < 0)
        continue;
      if ((size_t)needed >= sizeof(full))
      {
        allocated_full = (char *)malloc((size_t)needed + 1);
        if (!allocated_full)
          continue;
        snprintf(allocated_full, (size_t)needed + 1, "%s/%s", dir_path, name->data);
        target_full = allocated_full;
      }
      PenguString full_s;
      full_s.data = target_full;
      full_s.len = needed;
      full_s.is_owned = 0;
      if (pengu_c_archivum_is_dir(full_s))
      {
        pengu_c_archivum_glob_rec(target_full, pattern, res);
      }
      bool match = false;
      if ((pattern.len == 1 && pattern.data[0] == '*') ||
          (pattern.len == 2 && pattern.data[0] == '*' && pattern.data[1] == '*'))
      {
        match = true;
      }
      else if (pattern.len >= 2 && pattern.data[0] == '*' && pattern.data[1] == '.')
      {
        int ext_len = pattern.len - 1;
        if (name->len >= ext_len && memcmp(name->data + name->len - ext_len, pattern.data + 1, (size_t)ext_len) == 0)
        {
          match = true;
        }
      }
      else if (pengu__find_sub(full_s, pattern, 0) != -1 ||
               (name->len == pattern.len && memcmp(name->data, pattern.data, (size_t)pattern.len) == 0))
      {
        match = true;
      }
      if (match)
      {
        PenguString match_str = pengu_string_new(target_full);
        pengu_list_push(res, &match_str);
      }
      if (allocated_full)
        free(allocated_full);
    }
    pengu_banish_string_list(entries);
    free(entries);
  }

  /**
   * @brief Matches files in directory matching pattern.
   * @note Un `pattern` con `len == 0` matchea todas las entradas
   *       (comportamiento "match all" implícito). Para "no matchear nada",
   *       pasar un pattern que no coincida con ningún nombre.
   */
  static inline PenguList pengu_c_archivum_glob(PenguString pattern)
  {
    PenguList list = pengu_list_new(sizeof(PenguString), 16);
    pengu_c_archivum_glob_rec(".", pattern, &list);
    return list;
  }

  /**
   * @brief Helper recursivo para pengu_c_archivum_walk.
   * @note Sin límite artificial de 4096 bytes tras C15b; asigna dinámicamente si la ruta excede el buffer local.
   * @note Los paths se construyen con snprintf/%.*s y por tanto truncan
   *       en el primer byte NUL embebido. En sistemas POSIX/Windows reales
   *       los nombres de fichero y directorio no pueden contener NUL, así
   *       que este truncamiento es teórico.
   */
  static inline void pengu_c_archivum_walk_rec(const char *dir_path, PenguList *res)
  {
    PenguString p_str = pengu_string_from_cstr(dir_path);
    PenguMaybe m_entries = pengu_c_archivum_read_dir(p_str);
    if (!m_entries.is_present || !m_entries.value)
      return;
    PenguList *entries = (PenguList *)m_entries.value;

    PenguList node = pengu_list_new(sizeof(PenguString), 4);
    PenguString d_str = pengu_string_new(dir_path);
    pengu_list_push(&node, &d_str);

    for (int i = 0; i < entries->len; ++i)
    {
      PenguString *name = (PenguString *)pengu_list_at(entries, i);
      char sub[4096];
      int needed = snprintf(sub, sizeof(sub), "%s/%s", dir_path, name->data);
      char *allocated_sub = NULL;
      char *target_sub = sub;
      if (needed < 0)
        continue;
      if ((size_t)needed >= sizeof(sub))
      {
        allocated_sub = (char *)malloc((size_t)needed + 1);
        if (!allocated_sub)
          continue;
        snprintf(allocated_sub, (size_t)needed + 1, "%s/%s", dir_path, name->data);
        target_sub = allocated_sub;
      }
      PenguString sub_s = pengu_string_from_cstr(target_sub);
      if (pengu_c_archivum_is_dir(sub_s))
      {
        pengu_c_archivum_walk_rec(target_sub, res);
      }
      PenguString item = pengu_string_new(name->data);
      pengu_list_push(&node, &item);
      if (allocated_sub)
        free(allocated_sub);
    }
    pengu_banish_string_list(entries);
    free(entries);
    pengu_list_push(res, &node);
  }

  static inline PenguList pengu_c_archivum_walk(PenguString root)
  {
    PenguList list = pengu_list_new(sizeof(PenguList), 8);
    char *croot = (char *)malloc((size_t)root.len + 1);
    if (!croot)
      return list;
    memcpy(croot, root.data, (size_t)root.len);
    croot[root.len] = '\0';
    pengu_c_archivum_walk_rec(croot, &list);
    free(croot);
    return list;
  }

  static inline bool pengu_c_archivum_touch(PenguString path)
  {
    if (!path.data || path.len == 0)
      return false;
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return false;
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    FILE *f = fopen(cpath, "ab");
    if (f)
    {
      fclose(f);
#if PENGU_WINDOWS
      _utime(cpath, NULL);
#else
    utime(cpath, NULL);
#endif
      free(cpath);
      return true;
    }
    free(cpath);
    return false;
  }

  static inline bool pengu_c_archivum_symlink(PenguString target, PenguString link_p)
  {
    if (!target.data || !link_p.data)
      return false;
    char *ctarget = (char *)malloc((size_t)target.len + 1);
    char *clink = (char *)malloc((size_t)link_p.len + 1);
    if (!ctarget || !clink)
    {
      free(ctarget);
      free(clink);
      return false;
    }
    memcpy(ctarget, target.data, (size_t)target.len);
    ctarget[target.len] = '\0';
    memcpy(clink, link_p.data, (size_t)link_p.len);
    clink[link_p.len] = '\0';
#if PENGU_WINDOWS
    DWORD flags = pengu_c_archivum_is_dir(target) ? 1 : 0;
    BOOLEAN r = CreateSymbolicLinkA(clink, ctarget, flags);
    free(ctarget);
    free(clink);
    return r != 0;
#else
  int r = symlink(ctarget, clink);
  free(ctarget);
  free(clink);
  return r == 0;
#endif
  }

  /**
   * @brief Reads target of a symlink.
   * @note Límite real aceptado de 4094 bytes (el buffer es 4096, se pasa 4095 a
   *       readlink, se rechaza si el retorno es exactamente 4095) para preferir
   *       ser conservador antes que devolver una ruta potencialmente truncada.
   */
  static inline PenguMaybe pengu_c_archivum_read_symlink(PenguString path)
  {
    if (!path.data || path.len == 0)
      return pengu_maybe_none();
#if !PENGU_WINDOWS
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
    char buf[4096];
    ssize_t len = readlink(cpath, buf, sizeof(buf) - 1);
    free(cpath);
    if (len >= 0 && len < (ssize_t)(sizeof(buf) - 1))
    {
      buf[len] = '\0';
      PenguString *res = (PenguString *)malloc(sizeof(PenguString));
      if (res)
      {
        *res = pengu_string_new(buf);
        return pengu_maybe_some(res);
      }
    }
#endif
    return pengu_maybe_none();
  }

  /**
   * @brief Resolves canonical absolute path.
   * @note Utiliza asignación dinámica (POSIX.1-2008 / Win32) evitando límites estáticos
   *       o truncación silenciosa ante rutas largas. Ante OOM en la asignación dinámica,
   *       se retorna none de manera segura sin leer el búfer local no inicializado.
   */
  static inline PenguMaybe pengu_c_archivum_realpath(PenguString path)
  {
    if (!path.data || path.len == 0)
      return pengu_maybe_none();
    char *cpath = (char *)malloc((size_t)path.len + 1);
    if (!cpath)
      return pengu_maybe_none();
    memcpy(cpath, path.data, (size_t)path.len);
    cpath[path.len] = '\0';
#if PENGU_WINDOWS
    char buf[4096];
    DWORD len = GetFullPathNameA(cpath, sizeof(buf), buf, NULL);
    char *target = buf;
    char *dyn = NULL;
    if (len >= sizeof(buf))
    {
      dyn = (char *)malloc((size_t)len);
      if (dyn)
      {
        DWORD len2 = GetFullPathNameA(cpath, len, dyn, NULL);
        if (len2 > 0 && len2 < len)
        {
          target = dyn;
          len = len2;
        }
        else
        {
          free(dyn);
          dyn = NULL;
          len = 0;
        }
      }
      else
      {
        /* malloc falló: no podemos re-consultar; marcar len = 0 para
           caer limpiamente en pengu_maybe_none(). NO tocar `buf`: no
           está inicializado. */
        len = 0;
      }
    }
    free(cpath);
    if (len > 0)
    {
      PenguString *res = (PenguString *)malloc(sizeof(PenguString));
      if (res)
      {
        *res = pengu_string_new(target);
        if (dyn)
          free(dyn);
        return pengu_maybe_some(res);
      }
    }
    if (dyn)
      free(dyn);
#else
    char *res_ptr = realpath(cpath, NULL);
    free(cpath);
    if (res_ptr)
    {
      PenguString *res = (PenguString *)malloc(sizeof(PenguString));
      if (res)
      {
        *res = pengu_string_new(res_ptr);
        free(res_ptr);
        return pengu_maybe_some(res);
      }
      free(res_ptr);
    }
#endif
    return pengu_maybe_none();
  }

  /* =========================================================================
   * 18. Data Encoding & JSON Parsing (Cipher)
   * ========================================================================= */

  /* =========================================================================
   * 19. Tabular Data & CSV Processing (Ledger)
   * ========================================================================= */

  /* =========================================================================
   * 20. Concurrency & Threading Primitives (Filum)
   * ========================================================================= */

#if PENGU_ENABLE_THREADS

  void pengu_c_filum_go(void *f);
  void *pengu_c_filum_chan_new(size_t elem_size, int cap);
  bool pengu_c_filum_chan_send(void *c, void *value);
  bool pengu_c_filum_chan_recv(void *c, void *out);
  void pengu_c_filum_chan_close(void *c);
  int pengu_c_filum_chan_len(void *c);
  int pengu_c_filum_chan_cap(void *c);
  /** Releases a channel created with pengu_c_filum_chan_new(): wakes and
 * destroys its condition variables / critical section and frees the ring
 * buffer and handle. Callers must ensure no goroutine is still blocked on the
 * channel (call pengu_c_filum_chan_close() first when in doubt). */
  void pengu_c_filum_chan_free(void *c);

  void *pengu_c_filum_mutex_new(void);
  void pengu_c_filum_mutex_lock(void *m);
  void pengu_c_filum_mutex_unlock(void *m);
  bool pengu_c_filum_mutex_try_lock(void *m);
  /** Releases a mutex created with pengu_c_filum_mutex_new(). */
  void pengu_c_filum_mutex_free(void *m);

  void *pengu_c_filum_wait_group_new(void);
  void pengu_c_filum_wait_group_add(void *wg, int delta);
  void pengu_c_filum_wait_group_done(void *wg);
  void pengu_c_filum_wait_group_wait(void *wg);
  /** Releases a wait group created with pengu_c_filum_wait_group_new(). */
  void pengu_c_filum_wait_group_free(void *wg);

  void *pengu_c_filum_once_new(void);
  void pengu_c_filum_once_do(void *o, void *f);
  /** Releases a once-guard created with pengu_c_filum_once_new(). */
  void pengu_c_filum_once_free(void *o);

  void *pengu_c_filum_cond_new(void);
  void pengu_c_filum_cond_wait(void *c, void *m);
  void pengu_c_filum_cond_signal(void *c);
  void pengu_c_filum_cond_broadcast(void *c);
  /** Releases a condition variable created with pengu_c_filum_cond_new(). */
  void pengu_c_filum_cond_free(void *c);

  void *pengu_c_filum_atomic_int_new(int initial);
  int pengu_c_filum_atomic_int_load(void *a);
  void pengu_c_filum_atomic_int_store(void *a, int val);
  int pengu_c_filum_atomic_int_add(void *a, int delta);
  int pengu_c_filum_atomic_int_swap(void *a, int new_val);
  bool pengu_c_filum_atomic_int_compare_swap(void *a, int old_val, int new_val);
  /** Releases an atomic integer created with pengu_c_filum_atomic_int_new(). */
  void pengu_c_filum_atomic_int_free(void *a);

  void pengu_c_filum_sleep(int ms);
  int pengu_c_filum_num_cpu(void);
  int pengu_c_filum_goroutine_id(void);
#endif /* PENGU_ENABLE_THREADS -- Filum */


  /* =========================================================================
   * 25. C <-> Pengu Conversion Bridges (FFI)
   *
   * Helpers for embedding / library code that must move data between plain C
   * buffers and PenguScript containers. All pointer-taking constructors are
   * NULL-safe (empty input yields an empty container) and every function that
   * allocates documents who owns what.
   * ========================================================================= */

  /**
   * @brief Copies a C element buffer into a newly allocated PenguList.
   * @param data Source buffer of `count` elements, each `elem_size` bytes
   *             (may be NULL when count <= 0).
   * @param elem_size Size in bytes of one element.
   * @param count Element count (<= 0 yields an empty list).
   * @return PenguList owning a byte-for-byte copy of the elements. On
   *         allocation failure an empty (NULL-buffer) list is returned.
   * @note If the elements are PenguString or hold heap memory, the caller must
   *       release each element (e.g. pengu_banish_string) before
   *       pengu_banish_list() — same contract as pengu_list_new().
   */
  PenguList pengu_list_from_data(const void *data, size_t elem_size, int count);

  /**
   * @brief Deep-copies a map from two parallel C arrays of keys and values.
   * @param keys Array of `count` keys, each `key_size` bytes.
   * @param values Array of `count` values, each `val_size` bytes.
   * @param key_size Size in bytes of one key.
   * @param val_size Size in bytes of one value.
   * @param count Pair count (<= 0, or NULL arrays, yields an empty map).
   * @return PenguMap containing deep copies (PenguString keys/values are
   *         duplicated into own buffers). On failure an empty map is returned.
   */
  PenguMap pengu_map_from_entries(const void *keys, const void *values,
                                  size_t key_size, size_t val_size, int count);

  /** @brief Parallel key/value arrays produced by pengu_map_to_entries(). */
  typedef struct
  {
    void *keys;      /**< Owned buffer of `count` keys, each `key_size` bytes. */
    void *values;    /**< Owned buffer of `count` values, each `val_size` bytes. */
    int count;       /**< Number of copied pairs. */
    size_t key_size; /**< Key size in bytes. */
    size_t val_size; /**< Value size in bytes. */
  } PenguEntryArray;

  /**
   * @brief Copies every occupied pair of a map into two freshly allocated,
   *        caller-owned parallel arrays.
   * @param map Map to export (may be NULL -> empty result).
   * @return PenguEntryArray with deep copies of the entries. PenguString
   *         keys/values are duplicated into own buffers, so the caller fully
   *         owns the result and releases it with pengu_entry_array_free().
   */
  PenguEntryArray pengu_map_to_entries(const PenguMap *map);

  /**
   * @brief Releases a PenguEntryArray returned by pengu_map_to_entries().
   * @param arr Entry array to free (may be NULL). Frees the key/value buffers
   *        and any PenguString contents they own.
   */
  void pengu_entry_array_free(PenguEntryArray *arr);

  /**
   * @brief Returns the string's internal buffer as a non-owning slice of bytes.
   * @param s String to view (by value; may hold NULL data -> empty slice).
   * @return PenguSlice over the string bytes (data never NULL for empty view).
   * @note The slice aliases the string buffer; valid while the string lives.
   */
  PenguSlice pengu_string_as_slice(PenguString s);

  /**
   * @brief Copies a PenguString's bytes into a freshly allocated, owned
   *        PenguString (never aliases the input).
   * @param s Input string (NULL data -> empty owned string).
   * @return Owning copy of `s`.
   */
  PenguString pengu_string_copy(PenguString s);

  /* -------------------------------------------------------------------------
   * Typed wrappers consumed by std/ffi.pengu. PenguScript container types are
   * nominal, so every concrete element type gets its own callable symbol; the
   * underlying C layout is the shared PenguSlice / PenguList / PenguMap.
   * All of them are NULL / count-safe and non-owning where noted.
   * ------------------------------------------------------------------------- */

  /** Non-owning generic slice view over `count` elements of size `elem_size` at `data` (NULL-safe). */
  PenguSlice pengu_ffi_slice_raw(const void *data, int elem_size, int count);
  /** Non-owning byte slice view over `count` bytes at `data` (NULL-safe). */
  PenguSlice pengu_ffi_slice_u8(const void *data, int count);
  /** Non-owning int32 slice view over `count` elements at `data` (NULL-safe). */
  PenguSlice pengu_ffi_slice_i32(const void *data, int count);
  /** Non-owning double slice view over `count` elements at `data` (NULL-safe). */
  PenguSlice pengu_ffi_slice_f64(const void *data, int count);
  /** Non-owning float32 slice view over `count` elements at `data`. */
  PenguSlice pengu_ffi_slice_f32(const void *data, int count);
  /** Owning copy of `count` bytes at `data` into a PenguList of uint8. */
  PenguList pengu_ffi_list_u8(const void *data, int count);
  /** Owning copy of `count` int32 elements at `data` into a PenguList. */
  PenguList pengu_ffi_list_i32(const void *data, int count);
  /** Owning copy of `count` double elements at `data` into a PenguList. */
  PenguList pengu_ffi_list_f64(const void *data, int count);
  /** Owning copy of `count` float32 elements at `data` into a PenguList. */
  PenguList pengu_ffi_list_f32(const void *data, int count);
  /** Raw byte offset; no bounds or provenance checks. */
  void *pengu_ffi_ptr_offset(const void *p, int n);

  /* vaqt-backed high-precision time (runtime/pengu_vaqt.c). */
  void pengu_vaqt_now(int64_t *sec, int32_t *nsec);
  void pengu_vaqt_from_unix(int64_t sec, int32_t nsec, int64_t *out_sec, int32_t *out_nsec);
  void pengu_vaqt_to_unix(int64_t sec, int32_t nsec, int64_t *out_sec, int32_t *out_nsec);
  int pengu_vaqt_year(int64_t sec, int32_t nsec);
  int pengu_vaqt_month(int64_t sec, int32_t nsec);
  int pengu_vaqt_day(int64_t sec, int32_t nsec);
  int pengu_vaqt_hour(int64_t sec, int32_t nsec);
  int pengu_vaqt_minute(int64_t sec, int32_t nsec);
  int pengu_vaqt_second(int64_t sec, int32_t nsec);
  int pengu_vaqt_nano(int64_t sec, int32_t nsec);
  int pengu_vaqt_weekday(int64_t sec, int32_t nsec);
  int pengu_vaqt_yearday(int64_t sec, int32_t nsec);
  int pengu_vaqt_compare(int64_t asec, int32_t ansec, int64_t bsec, int32_t bnsec);
  void pengu_vaqt_add(int64_t sec, int32_t nsec, int64_t add_sec, int32_t add_nsec,
                      int64_t *out_sec, int32_t *out_nsec);
  void pengu_vaqt_add_date(int64_t sec, int32_t nsec, int years, int months, int days,
                           int64_t *out_sec, int32_t *out_nsec);
  PenguString pengu_vaqt_format_iso(int64_t sec, int32_t nsec, int offset);
  PenguString pengu_vaqt_format_date(int64_t sec, int32_t nsec, int offset);
  PenguString pengu_vaqt_format_datetime(int64_t sec, int32_t nsec, int offset);
  bool pengu_vaqt_parse_iso(PenguString s, int64_t *out_sec, int32_t *out_nsec);
  /** NULL-safe owning PenguString copy of a C string (see pengu_string_new). */
  PenguString pengu_ffi_cstr_string(const char *s);
  /** Read-only view of a PenguString's internal buffer (never NULL). */
  const char *pengu_ffi_string_cstr(PenguString s);
  /** Read-only byte view of a PenguString's internal buffer (never NULL). */
  const void *pengu_ffi_string_bytes(PenguString s);
  /** Builds a map of string->int from parallel PenguString/int32 slices
 * (copies keys deeply; values copied by value). */
  PenguMap pengu_ffi_map_si(PenguSlice keys, PenguSlice vals);


  #if defined(__EMSCRIPTEN__)
  /* JS bridge callbacks (runtime/pengu_js.c; only linked for wasm). */
  typedef void (*PenguJsValueCallback)(int32_t);
  typedef void (*PenguJsStringCallback)(PenguString);
  int32_t pengu_js_callback_new(PenguJsValueCallback fn);
  void pengu_js_callback_free(int32_t id);
  int32_t pengu_js_callback_string_new(PenguJsStringCallback fn);
  void pengu_js_callback_string_free(int32_t id);
  #endif

#ifdef __cplusplus
}
#endif

#endif /* PENGU_RUNTIME_ORGANIZED_H */
