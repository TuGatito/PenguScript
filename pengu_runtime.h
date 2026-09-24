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
 * @note Designed for C11/C99 compatibility with manual memory management (banish/defer).
 */

#ifndef PENGU_RUNTIME_ORGANIZED_H
#define PENGU_RUNTIME_ORGANIZED_H

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
#else
#define PENGU_WINDOWS 0
#include <unistd.h>
#include <sys/time.h>
#include <dirent.h>
#include <utime.h>
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

#ifndef PENGU_MAX_FRAMES
#define PENGU_MAX_FRAMES 64
#endif

  typedef struct
  {
    const char *func;   /* function name, e.g. "pengu_main" */
    const char *file;   /* .pengu file, e.g. "src/main.pengu" */
    int         line;   /* .pengu source line of the function declaration */
  } PenguFrame;

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
  static volatile int g_pengu_handler_installed = 0;

  /*
   * El output se escribe con write(2) / _write. El buffer intermedio se arma con
   * snprintf, que no está listado por POSIX como async-signal-safe pero funciona
   * en glibc/musl/msvcrt para los formatos usados (%s, %d, %u).
   */
  static void pengu_dump_frame_stack(const char *reason, int signo)
  {
    char buf[4096];
    int offset = 0;
    int n = snprintf(buf + offset, sizeof(buf) - (size_t)offset,
                     "\n[PENGU CRASH] %s (signal/code %d)\nStack trace (most recent call first):\n",
                     reason ? reason : "fatal error", signo);
    if (n > 0) {
      offset += (offset + n < (int)sizeof(buf)) ? n : (int)(sizeof(buf) - (size_t)offset - 1);
    }
    for (int i = g_pengu_frame_top - 1; i >= 0; i--) {
      PenguFrame *f = &g_pengu_frames[i];
      n = snprintf(buf + offset, sizeof(buf) - (size_t)offset,
                   "  at %s (%s:%d)\n",
                   (f->func && f->func[0]) ? f->func : "<?anon>",
                   (f->file && f->file[0]) ? f->file : "<unknown>",
                   f->line);
      if (n > 0) {
        offset += (offset + n < (int)sizeof(buf)) ? n : (int)(sizeof(buf) - (size_t)offset - 1);
      }
      if ((size_t)offset >= sizeof(buf) - 1) break;
    }
#if PENGU_WINDOWS
    if (offset > 0) {
      (void)_write(2, buf, (unsigned int)offset);
    }
#else
    if (offset > 0) {
      (void)write(2, buf, (size_t)offset);
    }
#endif
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

  static void pengu_unix_signal_handler(int sig)
  {
    pengu_dump_frame_stack("fatal signal", sig);
    _exit(128 + sig);
  }

  static inline void pengu_install_crash_handler(void)
  {
    if (!g_pengu_handler_installed) {
      g_pengu_handler_installed = 1;
#if PENGU_WINDOWS
      SetUnhandledExceptionFilter(pengu_win_exception_handler);
#endif
      signal(SIGSEGV, pengu_unix_signal_handler);
      signal(SIGABRT, pengu_unix_signal_handler);
    }
  }

  static inline void pengu_frame_push(const char *func, const char *file, int line)
  {
    pengu_install_crash_handler();
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
    char buf[256];
    int n = snprintf(buf, sizeof(buf),
                     "\n[PENGU] Index out of bounds: %lld (length %lld) at %s\n",
                     (long long)idx, (long long)len, loc ? loc : "?");
    if (n > 0) {
#if PENGU_WINDOWS
      (void)_write(2, buf, (unsigned int)n);
#else
      (void)write(2, buf, (size_t)n);
#endif
    }
    pengu_dump_frame_stack("bounds check failed", 0);
    _exit(134);
  }

  static inline void pengu_assert_bounds(int64_t idx, int64_t len, const char *loc)
  {
#if PENGU_FRAME_TRACE
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
   * @note PenguString NO garantiza NUL-terminación. `data` es un buffer de `len`
   *       bytes y puede no tener '\0' al final (p.ej. pengu_string_as_slice o
   *       vistas sobre buffers parciales). Los constructores internos
   *       (pengu_string_new, _copy, _from_cstr, _substring, _split, _concat,
   *       _format, _replace, _repeat, _reverse, _from_int, _from_float,
   *       _from_char, _char_at) SÍ producen buffers NUL-terminados, pero el
   *       consumidor no debe asumirlo sin comprobación explícita.
   */
  typedef struct
  {
    char *data;
    int len;
  } PenguString;

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
   * @return Newly allocated PenguString.
   */
  static inline PenguString pengu_string_new(const char *str)
  {
    PenguString s;
    if (!str)
    {
      s.len = 0;
      s.data = (char *)"";
      return s;
    }
    size_t len = strlen(str);
    if (len == 0 || len > INT_MAX)
    {
      s.len = 0;
      s.data = (char *)"";
      return s;
    }
    s.len = (int)len;
    s.data = (char *)malloc((size_t)s.len + 1);
    if (!s.data)
    {
      s.len = 0;
      s.data = (char *)"";
      return s;
    }
    memcpy(s.data, str, (size_t)s.len + 1);
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
      return s;
    }
    s.len = (int)strlen(str);
    s.data = (char *)str;
    return s;
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
    char *buf = (char *)malloc((size_t)size + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    va_start(args, fmt);
    vsnprintf(buf, (size_t)size + 1, fmt, args);
    va_end(args);
    return (PenguString){buf, size};
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
    PenguString s;
    s.len = total;
    s.data = (char *)malloc((size_t)total + 1);
    if (!s.data)
    {
      s.len = 0;
      s.data = (char *)"";
      return s;
    }
    if (a.data && a.len > 0)
    {
      memcpy(s.data, a.data, (size_t)a.len);
    }
    if (b.data && b.len > 0)
    {
      memcpy(s.data + a.len, b.data, (size_t)b.len);
    }
    s.data[s.len] = '\0';
    return s;
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
   * @brief Frees heap buffer allocated by a PenguString.
   * @param s Pointer to PenguString to deallocate.
   * @warning Solo es seguro sobre strings creados por pengu_string_new, _copy,
   *          _format, _concat, _substring, _replace, _repeat, _reverse, _from_int,
   *          _from_float, _from_char. NUNCA llamar sobre el resultado de
   *          pengu_string_from_cstr (view de rodata) ni sobre strings con len == 0
   *          (no-op). La heurística 'len > 0 ⟹ owning' NO distingue views no-owning
   *          con contenido.
   */
  static inline void pengu_banish_string(PenguString *s)
  {
    if (s && s->data && s->len > 0)
    {
      free(s->data);
      s->data = NULL;
      s->len = 0;
    }
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

  static inline int pengu_string_index_of(PenguString a, PenguString sub);

  /**
   * @brief Checks if string a contains substring b.
   * @param a Haystack string.
   * @param b Needle string.
   * @return True if substring is found, false otherwise.
   */
  static inline bool pengu_string_contains(PenguString a, PenguString b)
  {
    if (!a.data || !b.data)
      return false;
    if (b.len == 0)
      return true;
    return pengu_string_index_of(a, b) != -1;
  }

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
    char *buf = (char *)malloc((size_t)len + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    memcpy(buf, s.data + start, (size_t)len);
    buf[len] = '\0';
    return (PenguString){buf, len};
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
    char *buf = (char *)malloc((size_t)len + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    memcpy(buf, s.data + start, (size_t)len);
    buf[len] = '\0';
    return (PenguString){buf, len};
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
    char *buf = (char *)malloc((size_t)len + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    memcpy(buf, s.data, (size_t)len);
    buf[len] = '\0';
    return (PenguString){buf, len};
  }

  /**
   * @brief Checks if string a starts with prefix string.
   * @param a Haystack string.
   * @param prefix Prefix string.
   * @return True if a starts with prefix, false otherwise.
   */
  static inline bool pengu_string_starts_with(PenguString a, PenguString prefix)
  {
    if (!a.data || !prefix.data)
      return false;
    if (prefix.len == 0)
      return true;
    if (a.len < prefix.len)
      return false;
    return memcmp(a.data, prefix.data, (size_t)prefix.len) == 0;
  }

  /**
   * @brief Checks if string a ends with suffix string.
   * @param a Haystack string.
   * @param suffix Suffix string.
   * @return True if a ends with suffix, false otherwise.
   */
  static inline bool pengu_string_ends_with(PenguString a, PenguString suffix)
  {
    if (!a.data || !suffix.data)
      return false;
    if (suffix.len == 0)
      return true;
    if (a.len < suffix.len)
      return false;
    return memcmp(a.data + a.len - suffix.len, suffix.data, (size_t)suffix.len) == 0;
  }

  /**
   * @brief Returns the 0-based index of the first occurrence of sub in a, or -1 if not found.
   * @param a Haystack string.
   * @param sub Substring to search for.
   * @return 0-based index or -1.
   */
  static inline int pengu_string_index_of(PenguString a, PenguString sub)
  {
    if (!a.data || !sub.data || a.len < sub.len)
      return -1;
    if (sub.len == 0)
      return 0;
    return pengu__find_sub(a, sub, 0);
  }

  /**
   * @brief Returns the 0-based index of the last occurrence of sub in a, or -1 if not found.
   * @param a Haystack string.
   * @param sub Substring to search for.
   * @return 0-based index or -1.
   */
  static inline int pengu_string_last_index_of(PenguString a, PenguString sub)
  {
    if (!a.data || !sub.data || a.len < sub.len)
      return -1;
    if (sub.len == 0)
      return a.len;
    for (int i = a.len - sub.len; i >= 0; --i)
    {
      if (memcmp(a.data + i, sub.data, (size_t)sub.len) == 0)
      {
        return i;
      }
    }
    return -1;
  }

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
    int len = end - start;
    char *buf = (char *)malloc((size_t)len + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    memcpy(buf, s.data + start, (size_t)len);
    buf[len] = '\0';
    return (PenguString){buf, len};
  }

  /**
   * @brief Replaces all occurrences of from with to in string s.
   * @note Semántica binaria exacta NUL-aware: no trunca en bytes NUL ni en `s` ni en `from`/`to`.
   *       Strings con longitud resultante > INT_MAX se rechazan (retornan vacío).
   * @param s Source string.
   * @param from Substring to be replaced.
   * @param to Replacement substring.
   * @return Newly allocated string with replacements applied.
   */
  static inline PenguString pengu_string_replace(PenguString s, PenguString from, PenguString to)
  {
    if (!s.data)
      return pengu_string_from_cstr("");
    if (!from.data || from.len <= 0)
      return pengu_string_copy(s);

    int count = 0;
    int pos = 0;
    while ((pos = pengu__find_sub(s, from, pos)) != -1)
    {
      count++;
      pos += from.len;
    }
    if (count == 0)
      return pengu_string_copy(s);

    int64_t delta = (int64_t)to.len - (int64_t)from.len;
    int64_t new_len_64 = (int64_t)s.len + (int64_t)count * delta;
    if (new_len_64 < 0 || new_len_64 > (int64_t)INT_MAX)
      return pengu_string_from_cstr("");
    size_t new_len = (size_t)new_len_64;
    if (new_len == 0)
      return pengu_string_from_cstr("");
    char *buf = (char *)malloc(new_len + 1);
    if (!buf)
      return pengu_string_from_cstr("");

    char *dst = buf;
    int src_idx = 0;
    int next_match = 0;
    while ((next_match = pengu__find_sub(s, from, src_idx)) != -1)
    {
      int seg = next_match - src_idx;
      if (seg > 0)
      {
        memcpy(dst, s.data + src_idx, (size_t)seg);
        dst += seg;
      }
      if (to.len > 0 && to.data)
      {
        memcpy(dst, to.data, (size_t)to.len);
        dst += to.len;
      }
      src_idx = next_match + from.len;
    }
    int rem = s.len - src_idx;
    if (rem > 0)
    {
      memcpy(dst, s.data + src_idx, (size_t)rem);
      dst += rem;
    }
    *dst = '\0';
    return (PenguString){buf, (int)new_len};
  }

  /**
   * @brief Repeats string s count times.
   * @note Strings con longitud resultante > INT_MAX se rechazan (retornan vacío)
   *       para prevenir truncación de longitud y desbordamientos.
   * @param s String to repeat.
   * @param times Number of repetitions.
   * @return Repeated PenguString.
   */
  static inline PenguString pengu_string_repeat(PenguString s, int times)
  {
    if (times <= 0 || !s.data || s.len <= 0)
      return pengu_string_from_cstr("");
    if ((size_t)s.len > SIZE_MAX / (size_t)times)
      return pengu_string_from_cstr("");
    size_t total_len = (size_t)s.len * (size_t)times;
    if (total_len > (size_t)INT_MAX || total_len + 1 > SIZE_MAX / 2)
      return pengu_string_from_cstr("");
    char *buf = (char *)malloc(total_len + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    for (int i = 0; i < times; ++i)
    {
      memcpy(buf + ((size_t)i * (size_t)s.len), s.data, (size_t)s.len);
    }
    buf[total_len] = '\0';
    return (PenguString){buf, (int)total_len};
  }

  /**
   * @brief Returns a reversed copy of string s.
   * @param s Source string.
   * @return Reversed PenguString.
   */
  static inline PenguString pengu_string_reverse(PenguString s)
  {
    if (!s.data || s.len <= 0)
      return pengu_string_from_cstr("");
    char *buf = (char *)malloc((size_t)s.len + 1);
    if (!buf)
      return pengu_string_from_cstr("");
    for (int i = 0; i < s.len; ++i)
    {
      buf[i] = s.data[s.len - 1 - i];
    }
    buf[s.len] = '\0';
    return (PenguString){buf, s.len};
  }

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
    char *buf = (char *)malloc(2);
    if (!buf)
      return pengu_string_from_cstr("");
    buf[0] = s.data[idx];
    buf[1] = '\0';
    return (PenguString){buf, 1};
  }

  /**
   * @brief Formats an integer to a PenguString.
   * @param val 64-bit integer value.
   * @return Formatted PenguString.
   */
  static inline PenguString pengu_string_from_int(int64_t val)
  {
    char buf[64];
    snprintf(buf, sizeof(buf), "%lld", (long long)val);
    return pengu_string_new(buf);
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
    char *buf = (char *)malloc(2);
    if (!buf)
      return pengu_string_from_cstr("");
    buf[0] = c;
    buf[1] = '\0';
    return (PenguString){buf, 1};
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

  /**
   * @brief Parses integer from string into a Maybe container.
   * @note Copia s a un búfer temporal NUL-terminado para evitar lecturas fuera de rango
   *       si s es una vista no NUL-terminada (p.ej. pengu_string_as_slice).
   * @param s Input string.
   * @return PenguMaybe holding pointer to int32_t on success, or None.
   */
  static inline PenguMaybe pengu_parse_int(PenguString s)
  {
    if (!s.data || s.len <= 0)
      return pengu_maybe_none();
    char *tmp = (char *)malloc((size_t)s.len + 1);
    if (!tmp)
      return pengu_maybe_none();
    memcpy(tmp, s.data, (size_t)s.len);
    tmp[s.len] = '\0';
    const char *p = tmp;
    while (*p && isspace((unsigned char)*p))
      p++;
    char *endptr = NULL;
    errno = 0;
    long long val = strtoll(tmp, &endptr, 10);
    const char *end_limit = tmp + s.len;
    while (endptr < end_limit && isspace((unsigned char)*endptr))
      endptr++;
    if (p == endptr || endptr == tmp || endptr != end_limit || errno == ERANGE)
    {
      free(tmp);
      return pengu_maybe_none();
    }
    if (val > INT32_MAX || val < INT32_MIN)
    {
      free(tmp);
      return pengu_maybe_none();
    }
    free(tmp);
    int32_t *res = (int32_t *)malloc(sizeof(int32_t));
    if (!res)
      return pengu_maybe_none();
    *res = (int32_t)val;
    return pengu_maybe_some(res);
  }

  /**
   * @brief Parses double from string into a Maybe container.
   * @note Copia s a un búfer temporal NUL-terminado para evitar lecturas fuera de rango
   *       si s es una vista no NUL-terminada (p.ej. pengu_string_as_slice).
   * @param s Input string.
   * @return PenguMaybe holding pointer to double on success, or None.
   */
  static inline PenguMaybe pengu_parse_float(PenguString s)
  {
    if (!s.data || s.len <= 0)
      return pengu_maybe_none();
    char *tmp = (char *)malloc((size_t)s.len + 1);
    if (!tmp)
      return pengu_maybe_none();
    memcpy(tmp, s.data, (size_t)s.len);
    tmp[s.len] = '\0';
    const char *p = tmp;
    while (*p && isspace((unsigned char)*p))
      p++;
    char *endptr = NULL;
    errno = 0;
    double val = strtod(tmp, &endptr);
    const char *end_limit = tmp + s.len;
    while (endptr < end_limit && isspace((unsigned char)*endptr))
      endptr++;
    if (p == endptr || endptr == tmp || endptr != end_limit || errno == ERANGE)
    {
      free(tmp);
      return pengu_maybe_none();
    }
    free(tmp);
    double *res = (double *)malloc(sizeof(double));
    if (!res)
      return pengu_maybe_none();
    *res = val;
    return pengu_maybe_some(res);
  }

/**
 * @brief Generic macro converting any primitive type or PenguString to PenguString.
 */
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
    PenguString: pengu_string_identity)(x)

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
   * @brief Growable dynamic list with capacity, length, and element size.
   */
  typedef struct
  {
    void *data;
    int len;
    int cap;
    size_t elem_size;
  } PenguList;

/* NOTE: PenguList owns only its internal element buffer. When the elements are
 * pointers / structs that hold allocated memory (e.g. PenguString), the caller
 * must release each element first (e.g. pengu_banish_string) before calling
 * pengu_banish_list. */

  /**
   * @brief Creates a new dynamic list with given element size and capacity.
   * @param elem_size Size of each element in bytes.
   * @param cap Initial capacity.
   * @return Initialized PenguList.
   */
  static inline PenguList pengu_list_new(size_t elem_size, size_t cap)
  {
    PenguList list;
    list.len = 0;
    list.cap = (cap > 0) ? (int)cap : 4;
    list.elem_size = elem_size;
    list.data = malloc((size_t)list.cap * elem_size);
    if (!list.data)
    {
      list.cap = 0;
      list.len = 0;
    }
    return list;
  }

  /**
   * @brief Appends an element to the list, expanding capacity if needed.
   * @note En fallo de realloc/malloc, retorna silenciosamente sin insertar.
   *       El caller no puede distinguir entre éxito y OOM.
   * @param list Pointer to PenguList.
   * @param item Pointer to element data to copy into list.
   */
  static inline void pengu_list_push(PenguList *list, const void *item)
  {
    if (!list || !item)
      return;
    if (list->len >= list->cap)
    {
      if (list->cap > INT_MAX / 2)
        return;
      int new_cap = (list->cap == 0) ? 4 : list->cap * 2;
      if (list->elem_size != 0 && (size_t)new_cap > SIZE_MAX / list->elem_size)
        return;
      void *new_data = realloc(list->data, (size_t)new_cap * list->elem_size);
      if (!new_data)
        return;
      list->data = new_data;
      list->cap = new_cap;
    }
    char *target = (char *)list->data + ((size_t)list->len * list->elem_size);
    memcpy(target, item, list->elem_size);
    list->len++;
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
    if (!list || list->len <= 0)
      return NULL;
    list->len--;
    return (char *)list->data + ((size_t)list->len * list->elem_size);
  }

  /**
   * @brief Pops and removes the last element from the list into an output buffer.
   * @param list Pointer to PenguList.
   * @param out_item Optional destination buffer to copy popped element into.
   * @return True if an element was popped, False if list was empty.
   */
  static inline bool pengu_list_pop(PenguList *list, void *out_item)
  {
    if (!list || list->len <= 0)
      return false;
    list->len--;
    if (out_item)
    {
      char *src = (char *)list->data + ((size_t)list->len * list->elem_size);
      memcpy(out_item, src, list->elem_size);
    }
    return true;
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
    if (list)
    {
      list->len = 0;
    }
  }

  /**
   * @brief Frees memory allocated by a dynamic list.
   * @param list Pointer to PenguList.
   */
  static inline void pengu_banish_list(PenguList *list)
  {
    if (list && list->data)
    {
      free(list->data);
      list->data = NULL;
      list->len = 0;
      list->cap = 0;
    }
  }

  /**
   * @brief Frees all PenguString elements in a dynamic list, then banishes the list itself.
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
   * @note El caller es dueño de cada elemento; debe liberar cada `PenguString` con
   *       pengu_banish_string antes de pengu_banish_list.
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
        char *buf = (char *)malloc(2);
        if (buf)
        {
          buf[0] = s.data[i];
          buf[1] = '\0';
          PenguString ch = {buf, 1};
          pengu_list_push(&list, &ch);
        }
      }
      return list;
    }
    int cur = 0;
    int idx;
    while ((idx = pengu__find_sub(s, delim, cur)) != -1)
    {
      int seg_len = idx - cur;
      if (seg_len == 0)
      {
        PenguString part = pengu_string_from_cstr("");
        pengu_list_push(&list, &part);
      }
      else
      {
        char *buf = (char *)malloc((size_t)seg_len + 1);
        if (buf)
        {
          memcpy(buf, s.data + cur, (size_t)seg_len);
          buf[seg_len] = '\0';
          PenguString part = {buf, seg_len};
          pengu_list_push(&list, &part);
        }
      }
      cur = idx + delim.len;
    }
    int rem_len = s.len - cur;
    if (rem_len == 0)
    {
      PenguString part = pengu_string_from_cstr("");
      pengu_list_push(&list, &part);
    }
    else
    {
      char *buf = (char *)malloc((size_t)rem_len + 1);
      if (buf)
      {
        memcpy(buf, s.data + cur, (size_t)rem_len);
        buf[rem_len] = '\0';
        PenguString part = {buf, rem_len};
        pengu_list_push(&list, &part);
      }
    }
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
   */
  typedef struct
  {
    PenguMapEntry *entries;
    int len;
    int cap;
    size_t key_size;
    size_t val_size;
  } PenguMap;

  /**
   * @brief Creates a new hash map.
   * @param key_size Size of key type in bytes.
   * @param val_size Size of value type in bytes.
   * @return Initialized PenguMap.
   */
  static inline PenguMap pengu_map_new(size_t key_size, size_t val_size)
  {
    PenguMap map;
    map.len = 0;
    map.cap = 16;
    map.key_size = key_size;
    map.val_size = val_size;
    map.entries = (PenguMapEntry *)calloc((size_t)map.cap, sizeof(PenguMapEntry));
    if (!map.entries)
    {
      map.cap = 0;
      map.len = 0;
    }
    return map;
  }

  /**
   * @brief Allocates and initializes key/val pointers for a map entry slot.
   * @note En fallo de realloc/malloc, retorna silenciosamente sin insertar.
   *       El caller no puede distinguir entre éxito y OOM.
   */
  static inline bool pengu_map_alloc_slot(PenguMap *map, int idx,
                                          const void *key, const void *val,
                                          uint32_t h)
  {
    void *k = malloc(map->key_size);
    void *v = malloc(map->val_size);
    if (!k || !v)
    {
      free(k);
      free(v);
      return false;
    }
    if (map->key_size == sizeof(PenguString))
      *(PenguString *)k = pengu_string_copy(*(const PenguString *)key);
    else
      memcpy(k, key, map->key_size);
    if (map->val_size == sizeof(PenguString))
      *(PenguString *)v = pengu_string_copy(*(const PenguString *)val);
    else
      memcpy(v, val, map->val_size);
    map->entries[idx].hash = h;
    map->entries[idx].occupied = true;
    map->entries[idx].tombstone = false;
    map->entries[idx].key = k;
    map->entries[idx].val = v;
    map->len++;
    return true;
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
    if (!map || !key || !val)
      return;
    if (map->cap == 0)
    {
      map->cap = 16;
      map->entries = (PenguMapEntry *)calloc((size_t)map->cap, sizeof(PenguMapEntry));
      if (!map->entries)
      {
        map->cap = 0;
        map->len = 0;
        return;
      }
      map->len = 0;
    }
    if (map->len * 2 >= map->cap)
    {
      int old_cap = map->cap;
      if (old_cap > INT_MAX / 2)
        return;
      if ((size_t)old_cap > (SIZE_MAX / 2) / sizeof(PenguMapEntry))
        return;
      PenguMapEntry *old_entries = map->entries;
      map->cap = old_cap * 2;
      map->entries = (PenguMapEntry *)calloc((size_t)map->cap, sizeof(PenguMapEntry));
      if (!map->entries)
      {
        map->cap = old_cap;
        map->entries = old_entries;
        return;
      }
      map->len = 0;
      for (int i = 0; i < old_cap; ++i)
      {
        if (old_entries[i].occupied)
        {
          pengu_map_put(map, old_entries[i].key, old_entries[i].val);
          if (map->key_size == sizeof(PenguString))
            pengu_banish_string((PenguString *)old_entries[i].key);
          if (map->val_size == sizeof(PenguString))
            pengu_banish_string((PenguString *)old_entries[i].val);
          free(old_entries[i].key);
          free(old_entries[i].val);
        }
      }
      free(old_entries);
    }
    uint32_t h = (map->key_size == sizeof(PenguString)) ? (((PenguString *)key)->data && ((PenguString *)key)->len > 0 ? pengu_hash_bytes(((PenguString *)key)->data, (size_t)((PenguString *)key)->len) : 0) : pengu_hash_bytes(key, map->key_size);
    int idx = (int)(h % (uint32_t)map->cap);
    int first_tombstone = -1;
    for (int i = 0; i < map->cap; ++i)
    {
      int cur = (idx + i) % map->cap;
      if (!map->entries[cur].occupied)
      {
        if (map->entries[cur].tombstone)
        {
          if (first_tombstone == -1)
            first_tombstone = cur;
        }
        else
        {
          int insert_idx = (first_tombstone != -1) ? first_tombstone : cur;
          pengu_map_alloc_slot(map, insert_idx, key, val, h);
          return;
        }
      }
      else if (map->entries[cur].hash == h)
      {
        bool match = false;
        if (map->key_size == sizeof(PenguString))
        {
          PenguString *k1 = (PenguString *)map->entries[cur].key;
          const PenguString *k2 = (const PenguString *)key;
          match = (k1->len == k2->len && (k1->len == 0 || memcmp(k1->data, k2->data, (size_t)k1->len) == 0));
        }
        else
        {
          match = (memcmp(map->entries[cur].key, key, map->key_size) == 0);
        }
        if (match)
        {
          if (map->val_size == sizeof(PenguString))
          {
            pengu_banish_string((PenguString *)map->entries[cur].val);
            *(PenguString *)map->entries[cur].val = pengu_string_copy(*(const PenguString *)val);
          }
          else
          {
            memcpy(map->entries[cur].val, val, map->val_size);
          }
          return;
        }
      }
    }
    if (first_tombstone != -1)
    {
      pengu_map_alloc_slot(map, first_tombstone, key, val, h);
      return;
    }
  }

  /**
   * @brief Retrieves value pointer corresponding to key in hash map.
   * @param map Pointer to const PenguMap.
   * @param key Pointer to key data.
   * @return Pointer to value or NULL if key not found.
   */
  static inline void *pengu_map_get(const PenguMap *map, const void *key)
  {
    if (!map || !key || map->cap == 0)
      return NULL;
    uint32_t h = (map->key_size == sizeof(PenguString)) ? (((PenguString *)key)->data && ((PenguString *)key)->len > 0 ? pengu_hash_bytes(((PenguString *)key)->data, (size_t)((PenguString *)key)->len) : 0) : pengu_hash_bytes(key, map->key_size);
    int idx = (int)(h % (uint32_t)map->cap);
    for (int i = 0; i < map->cap; ++i)
    {
      int cur = (idx + i) % map->cap;
      if (!map->entries[cur].occupied && !map->entries[cur].tombstone)
        return NULL;
      if (map->entries[cur].occupied && map->entries[cur].hash == h)
      {
        bool match = false;
        if (map->key_size == sizeof(PenguString))
        {
          PenguString *k1 = (PenguString *)map->entries[cur].key;
          const PenguString *k2 = (const PenguString *)key;
          match = (k1->len == k2->len && (k1->len == 0 || memcmp(k1->data, k2->data, (size_t)k1->len) == 0));
        }
        else
        {
          match = (memcmp(map->entries[cur].key, key, map->key_size) == 0);
        }
        if (match)
          return map->entries[cur].val;
      }
    }
    return NULL;
  }

  /**
   * @brief Checks if hash map contains a key.
   * @param map Pointer to const PenguMap.
   * @param key Pointer to key data.
   * @return True if key exists, False otherwise.
   */
  static inline bool pengu_map_contains(const PenguMap *map, const void *key)
  {
    return pengu_map_get(map, key) != NULL;
  }

  /**
   * @brief Removes entry by key from hash map.
   * @param map Pointer to PenguMap.
   * @param key Pointer to key data.
   * @return True if entry was removed, False if not found.
   */
  static inline bool pengu_map_remove(PenguMap *map, const void *key)
  {
    if (!map || !key || map->cap == 0)
      return false;
    uint32_t h = (map->key_size == sizeof(PenguString)) ? (((PenguString *)key)->data && ((PenguString *)key)->len > 0 ? pengu_hash_bytes(((PenguString *)key)->data, (size_t)((PenguString *)key)->len) : 0) : pengu_hash_bytes(key, map->key_size);
    int idx = (int)(h % (uint32_t)map->cap);
    for (int i = 0; i < map->cap; ++i)
    {
      int cur = (idx + i) % map->cap;
      if (!map->entries[cur].occupied && !map->entries[cur].tombstone)
        return false;
      if (map->entries[cur].occupied && map->entries[cur].hash == h)
      {
        bool match = false;
        if (map->key_size == sizeof(PenguString))
        {
          PenguString *k1 = (PenguString *)map->entries[cur].key;
          const PenguString *k2 = (const PenguString *)key;
          match = (k1->len == k2->len && (k1->len == 0 || memcmp(k1->data, k2->data, (size_t)k1->len) == 0));
        }
        else
        {
          match = (memcmp(map->entries[cur].key, key, map->key_size) == 0);
        }
        if (match)
        {
          if (map->key_size == sizeof(PenguString))
          {
            pengu_banish_string((PenguString *)map->entries[cur].key);
          }
          if (map->val_size == sizeof(PenguString))
          {
            pengu_banish_string((PenguString *)map->entries[cur].val);
          }
          free(map->entries[cur].key);
          free(map->entries[cur].val);
          map->entries[cur].occupied = false;
          map->entries[cur].tombstone = true;
          map->entries[cur].key = NULL;
          map->entries[cur].val = NULL;
          map->entries[cur].hash = 0;
          map->len--;
          return true;
        }
      }
    }
    return false;
  }

  /**
   * @brief Frees memory allocated by a hash map.
   * @param map Pointer to PenguMap.
   */
  static inline void pengu_banish_map(PenguMap *map)
  {
    if (map && map->entries)
    {
      for (int i = 0; i < map->cap; ++i)
      {
        if (map->entries[i].occupied)
        {
          if (map->entries[i].key)
          {
            if (map->key_size == sizeof(PenguString))
            {
              pengu_banish_string((PenguString *)map->entries[i].key);
            }
            free(map->entries[i].key);
          }
          if (map->entries[i].val)
          {
            if (map->val_size == sizeof(PenguString))
            {
              pengu_banish_string((PenguString *)map->entries[i].val);
            }
            free(map->entries[i].val);
          }
        }
      }
      free(map->entries);
      map->entries = NULL;
      map->len = 0;
      map->cap = 0;
    }
  }

  /**
   * @brief Clears all entries in a PenguMap.
   * @param map Pointer to PenguMap.
   */
  static inline void pengu_map_clear(PenguMap *map)
  {
    if (!map || !map->entries)
      return;
    for (int i = 0; i < map->cap; ++i)
    {
      if (map->entries[i].occupied)
      {
        if (map->entries[i].key)
        {
          if (map->key_size == sizeof(PenguString))
          {
            pengu_banish_string((PenguString *)map->entries[i].key);
          }
          free(map->entries[i].key);
          map->entries[i].key = NULL;
        }
        if (map->entries[i].val)
        {
          if (map->val_size == sizeof(PenguString))
          {
            pengu_banish_string((PenguString *)map->entries[i].val);
          }
          free(map->entries[i].val);
          map->entries[i].val = NULL;
        }
        map->entries[i].occupied = false;
        map->entries[i].hash = 0;
      }
      map->entries[i].tombstone = false;
    }
    map->len = 0;
  }

  /** @brief Inserts or updates a string-to-int pair in the hash map. */
  static inline void pengu_map_put_string_int(PenguMap *m, const PenguString *k, const int32_t *v)
  {
    if (!m || !k || !v)
      return;
    if (m->cap == 0)
    {
      m->cap = 16;
      m->entries = (PenguMapEntry *)calloc((size_t)m->cap, sizeof(PenguMapEntry));
      if (!m->entries)
      {
        m->cap = 0;
        m->len = 0;
        return;
      }
      m->key_size = sizeof(PenguString);
      m->val_size = sizeof(int32_t);
      m->len = 0;
    }
    if (m->len * 2 >= m->cap)
    {
      int old_cap = m->cap;
      if (old_cap > INT_MAX / 2)
        return;
      if ((size_t)old_cap > (SIZE_MAX / 2) / sizeof(PenguMapEntry))
        return;
      PenguMapEntry *old_entries = m->entries;
      m->cap = old_cap * 2;
      m->entries = (PenguMapEntry *)calloc((size_t)m->cap, sizeof(PenguMapEntry));
      if (!m->entries)
      {
        m->cap = old_cap;
        m->entries = old_entries;
        return;
      }
      m->len = 0;
      for (int i = 0; i < old_cap; ++i)
      {
        if (old_entries[i].occupied)
        {
          PenguString *ek = (PenguString *)old_entries[i].key;
          int32_t *ev = (int32_t *)old_entries[i].val;
          pengu_map_put_string_int(m, ek, ev);
          pengu_banish_string(ek);
          free(ek);
          free(ev);
        }
      }
      free(old_entries);
    }
    uint32_t h = (k->data && k->len > 0) ? pengu_hash_bytes(k->data, (size_t)k->len) : 0;
    int idx = (int)(h % (uint32_t)m->cap);
    int first_tombstone = -1;
    for (int i = 0; i < m->cap; ++i)
    {
      int cur = (idx + i) % m->cap;
      if (!m->entries[cur].occupied)
      {
        if (m->entries[cur].tombstone)
        {
          if (first_tombstone == -1)
            first_tombstone = cur;
          continue;
        }
        int insert_idx = (first_tombstone != -1) ? first_tombstone : cur;
        pengu_map_alloc_slot(m, insert_idx, k, v, h);
        return;
      }
      else if (m->entries[cur].hash == h)
      {
        PenguString *existing = (PenguString *)m->entries[cur].key;
        if (existing->len == k->len &&
            (k->len == 0 ||
             memcmp(existing->data, k->data, (size_t)k->len) == 0))
        {
          *(int32_t *)m->entries[cur].val = *v;
          return;
        }
      }
    }
    if (first_tombstone != -1)
    {
      pengu_map_alloc_slot(m, first_tombstone, k, v, h);
      return;
    }
  }

  /** @brief Retrieves pointer to int32 value for string key in hash map. */
  static inline int32_t *pengu_map_get_string_int(const PenguMap *m, const PenguString *k)
  {
    if (!m || !k || !m->entries || m->cap == 0)
      return NULL;
    uint32_t h = (k->data && k->len > 0) ? pengu_hash_bytes(k->data, (size_t)k->len) : 0;
    int idx = (int)(h % (uint32_t)m->cap);
    for (int i = 0; i < m->cap; ++i)
    {
      int cur = (idx + i) % m->cap;
      if (!m->entries[cur].occupied && !m->entries[cur].tombstone)
        return NULL;
      if (m->entries[cur].occupied && m->entries[cur].hash == h)
      {
        PenguString *existing = (PenguString *)m->entries[cur].key;
        if (existing->len == k->len &&
            (k->len == 0 ||
             memcmp(existing->data, k->data, (size_t)k->len) == 0))
        {
          return (int32_t *)m->entries[cur].val;
        }
      }
    }
    return NULL;
  }

  /** @brief Checks if hash map contains string key. */
  static inline bool pengu_map_contains_string_int(const PenguMap *m, const PenguString *k)
  {
    return pengu_map_get_string_int(m, k) != NULL;
  }

  /** @brief Removes string key entry from hash map. */
  static inline bool pengu_map_remove_string_int(PenguMap *m, const PenguString *k)
  {
    if (!m || !k || !m->entries || m->cap == 0)
      return false;
    uint32_t h = (k->data && k->len > 0) ? pengu_hash_bytes(k->data, (size_t)k->len) : 0;
    int idx = (int)(h % (uint32_t)m->cap);
    for (int i = 0; i < m->cap; ++i)
    {
      int cur = (idx + i) % m->cap;
      if (!m->entries[cur].occupied && !m->entries[cur].tombstone)
        return false;
      if (m->entries[cur].occupied && m->entries[cur].hash == h)
      {
        PenguString *existing = (PenguString *)m->entries[cur].key;
        if (existing->len == k->len &&
            (k->len == 0 ||
             memcmp(existing->data, k->data, (size_t)k->len) == 0))
        {
          pengu_banish_string(existing);
          free(m->entries[cur].key);
          free(m->entries[cur].val);
          m->entries[cur].key = NULL;
          m->entries[cur].val = NULL;
          m->entries[cur].occupied = false;
          m->entries[cur].tombstone = true;
          m->entries[cur].hash = 0;
          m->len--;
          return true;
        }
      }
    }
    return false;
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

  /** @brief Collects the keys of a PenguString-keyed map into a list of strings. */
  static inline PenguList pengu_map_keys_string(const PenguMap *m)
  {
    if (!m || m->key_size != sizeof(PenguString) || !m->entries || m->cap == 0)
      return pengu_list_new(sizeof(PenguString), 0);
    PenguList list = pengu_list_new(sizeof(PenguString), 8);
    for (int i = 0; i < m->cap; ++i)
    {
      if (m->entries[i].occupied && m->entries[i].key)
      {
        PenguString *k = (PenguString *)m->entries[i].key;
        PenguString copy = (k->data && k->len > 0) ? pengu_string_copy(*k) : pengu_string_from_cstr("");
        pengu_list_push(&list, &copy);
      }
    }
    return list;
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

  /**
   * @brief Prints string to standard output without newline.
   * @param s String to print.
   */
  static inline void pengu_print(PenguString s)
  {
    if (s.data && s.len > 0)
      fwrite(s.data, 1, (size_t)s.len, stdout);
  }

  /**
   * @brief Prints string to standard output followed by a newline.
   * @param s String to print.
   */
  static inline void pengu_println(PenguString s)
  {
    if (s.data && s.len > 0)
      fwrite(s.data, 1, (size_t)s.len, stdout);
    fputc('\n', stdout);
  }

  /**
   * @brief Reads a line of text from standard input with an optional prompt.
   * @param prompt Prompt string printed to stdout.
   * @return User input line as PenguString.
   */
  static inline PenguString pengu_input(PenguString prompt)
  {
    if (prompt.data && prompt.len > 0)
    {
      fwrite(prompt.data, 1, (size_t)prompt.len, stdout);
      fflush(stdout);
    }
    char buf[4096];
    if (!fgets(buf, sizeof(buf), stdin))
      return pengu_string_from_cstr("");
    size_t l = strlen(buf);
    while (l > 0 && (buf[l - 1] == '\r' || buf[l - 1] == '\n'))
      buf[--l] = '\0';
    return pengu_string_new(buf);
  }

  /**
   * @brief Prints panic message to standard error and aborts process execution.
   * @param msg Error message.
   */
  static inline void pengu_panic(PenguString msg)
  {
    fprintf(stderr, "[PANIC] %.*s\n", msg.len, msg.data ? msg.data : "");
    exit(1);
  }

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
   * @param cmd Command string.
   * @param args List of PenguString argument tokens.
   * @return Return code from system(), or -1 on buffer allocation failure.
   */
  static inline int pengu_c_exec(PenguString cmd, PenguList args)
  {
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
    int res = system(cmdbuf);
    if (heap)
      free(cmdbuf);
    return res;
  }

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
          PenguString full = pengu_string_from_cstr(p);
          PenguString kstr = pengu_string_substring(full, 0, klen);
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
          PenguString full = pengu_string_from_cstr(*env);
          PenguString kstr = pengu_string_substring(full, 0, klen);
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
   * A present result holds a heap PenguString* that owns its buffer: the caller
   * must free the buffer with pengu_banish_string() and the wrapper with
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
    char *buf = (char *)malloc((size_t)sz + 1);
    if (!buf)
    {
      fclose(f);
      return pengu_maybe_none();
    }
    size_t read_bytes = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    if (read_bytes > (size_t)INT_MAX)
    {
      free(buf);
      return pengu_maybe_none();
    }
    buf[read_bytes] = '\0';
    PenguString *res = (PenguString *)malloc(sizeof(PenguString));
    if (!res)
    {
      free(buf);
      return pengu_maybe_none();
    }
    res->data = (read_bytes > 0) ? buf : (char *)"";
    if (read_bytes == 0)
      free(buf);
    res->len = (int)read_bytes;
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
    if (!map->entries)
    {
      free(map);
      return pengu_maybe_none();
    }

    char buf[64];
    PenguString k, v;

    k = pengu_string_from_cstr("size");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_size);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("is_file");
    v = S_ISREG(st.st_mode) ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("is_dir");
    v = S_ISDIR(st.st_mode) ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("is_symlink");
    v = pengu_c_archivum_is_symlink(path) ? pengu_string_from_cstr("true") : pengu_string_from_cstr("false");
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("modified");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_mtime);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("created");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_ctime);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("accessed");
    snprintf(buf, sizeof(buf), "%lld", (long long)st.st_atime);
    v = pengu_string_from_cstr(buf);
    pengu_map_put(map, &k, &v);

    k = pengu_string_from_cstr("permissions");
    snprintf(buf, sizeof(buf), "%d", (int)(st.st_mode & 0777));
    v = pengu_string_from_cstr(buf);
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

  /* =========================================================================
   * 21. Regular Expressions (Regulus)
   * ========================================================================= */

  typedef struct
  {
    int32_t start;
    int32_t end;
    PenguString matched;
  } PenguRegulusMatch;

  typedef struct
  {
    PenguString pattern;
    PenguString flags;
    void *_ptr;
  } PenguRegulusRegex;

  PenguMaybe pengu_c_regulus_compile(PenguString pattern, PenguString flags);
  PenguMaybe pengu_c_regulus_match(void *regex, PenguString text);
  PenguMaybe pengu_c_regulus_search(void *regex, PenguString text);
  /** Finds all regex matches in `text`.
 * @return PenguList of PenguRegulusMatch. Caller must free every match's
 *         `matched` PenguString with pengu_banish_string() before
 *         pengu_banish_list(). */
PenguList pengu_c_regulus_find_all(void *regex, PenguString text);
  /** Replaces matches of `regex` in `text`. The returned PenguString owns its
 * buffer: the caller must call pengu_banish_string() on it. */
PenguString pengu_c_regulus_replace(void *regex, PenguString text, PenguString replacement);
  /** Splits `text` on `regex`. Every element PenguString owns its buffer; the
 * caller must pengu_banish_string() each before pengu_banish_list(). */
  PenguList pengu_c_regulus_split(void *regex, PenguString text, int limit);
  /** Releases the PCRE2 code compiled by pengu_c_regulus_compile(). The
 * wrapper struct is normally a PenguScript value copy, so this helper frees
 * only the native code object and nulls `_ptr`; it does not free() the struct
 * or the borrowed pattern/flags strings. Direct C callers holding the heap
 * struct returned inside the PenguMaybe may free() it afterwards. */
  void pengu_c_regulus_regex_free(void *regex);
  /** Frees the owned `matched` buffer of a PenguRegulusMatch (search/match/
 * find_all results). Safe on value copies: the buffer is freed and the
 * PenguString zeroed, but the struct itself is not free()d. */
  void pengu_c_regulus_match_free(void *m);
  static inline PenguString pengu_c_regulus_escape(PenguString text) { return text; }
  static inline bool pengu_c_regulus_is_valid(void *regex) { return regex != NULL; }

  /* =========================================================================
   * 22. XML & HTML DOM Processing (Parchment)
   * ========================================================================= */

  typedef struct
  {
    PenguString tag;
    PenguString text;
    void *_ptr;
  } PenguParchmentNode;

  typedef struct
  {
    PenguParchmentNode root;
    PenguString version;
    PenguString encoding;
  } PenguParchmentDocument;

  PenguMaybe pengu_c_parchment_parse_xml(PenguString data);
  PenguMaybe pengu_c_parchment_parse_html(PenguString data);
  /** Serializes `node`. A present result holds a heap PenguString* the caller
 * must release (pengu_banish_string) after use. */
  PenguMaybe pengu_c_parchment_to_string(void *node, bool pretty);
  PenguMaybe pengu_c_parchment_find(void *node, PenguString query);
  /** Finds all children of `node` named `query`.
 * @return PenguList of PenguParchmentNode; every entry owns its tag/text
 *         PenguStrings and must be released with
 *         pengu_c_parchment_node_free() before pengu_banish_list(). */
  PenguList pengu_c_parchment_find_all(void *node, PenguString query);
  /** Reads attribute `name`. A present result holds a heap PenguString* the
 * caller must release (pengu_banish_string) after use. */
  PenguMaybe pengu_c_parchment_attr(void *node, PenguString name);
  void pengu_c_parchment_set_attr(void *node, PenguString name, PenguString value);
  /** Reads node text content. A present result holds a heap PenguString* the
 * caller must release (pengu_banish_string) after use. */
  PenguMaybe pengu_c_parchment_text(void *node);
  void pengu_c_parchment_set_text(void *node, PenguString text);
  void *pengu_c_parchment_create_element(PenguString tag);
  void *pengu_c_parchment_create_text(PenguString text);
  void pengu_c_parchment_append_child(void *parent, void *child);
  /** Releases the owned tag/text strings of a wrapper node (from find /
 * find_all / create_element / create_text). The xml node inside `_ptr` is
 * owned by its document and is NOT freed here; the struct is a PenguScript
 * value copy and is not free()d either. */
  void pengu_c_parchment_node_free(void *node);
  /** Releases a document parsed with pengu_c_parchment_parse_xml/html: frees
 * the owned wrapper strings and the whole libxml2 document tree. The wrapper
 * struct is a PenguScript value copy and is not free()d. Freeing the document
 * invalidates every node previously obtained from it (call node_free on their
 * wrapper strings first if needed). */
  void pengu_c_parchment_document_free(void *doc);
  static inline PenguString pengu_c_parchment_escape_text(PenguString text) { return text; }
  static inline PenguString pengu_c_parchment_unescape_text(PenguString text) { return text; }

  /* =========================================================================
   * 23. Compression & Cryptographic Hashing (Seal)
   * ========================================================================= */

  int pengu_c_seal_crc32(PenguString data);
  PenguString pengu_c_seal_md5(PenguString data);
  PenguString pengu_c_seal_sha1(PenguString data);
  PenguString pengu_c_seal_sha256(PenguString data);
  PenguString pengu_c_seal_sha512(PenguString data);
  /** gzip-compresses `data`. A present result holds a heap PenguString* that
 * the caller must release (pengu_banish_string) after use. */
PenguMaybe pengu_c_seal_gzip(PenguString data);
  PenguMaybe pengu_c_seal_unzip(PenguString data);
  PenguMaybe pengu_c_seal_zlib_compress(PenguString data);
  PenguMaybe pengu_c_seal_zlib_decompress(PenguString data);
  PenguMaybe pengu_c_seal_hash_file(PenguString path, PenguString hash_type);

  /* =========================================================================
   * 24. Networking & HTTP Client/Server (Precis)
   * ========================================================================= */

  typedef struct
  {
    int status_code;
    PenguMap headers;
    PenguMaybe body;
    PenguString url;
  } PenguPrecisClientResponse;

  typedef struct
  {
    PenguString method;
    PenguString path;
    PenguMap headers;
    PenguMaybe body;
    PenguMap query;
  } PenguPrecisRequest;

  typedef struct
  {
    int status_code;
    PenguMap headers;
    PenguMaybe body;
  } PenguPrecisResponse;

  typedef struct
  {
    void *_ptr;
  } PenguPrecisTCPSocket;

  /** Performs an HTTP GET. A present result holds a PenguPrecisClientResponse*
 * that owns its body/headers: release it with the corresponding
 * pengu_precis_free_response helper / body & map banish calls. */
PenguMaybe pengu_c_precis_http_get(PenguString url, PenguMap headers);
  PenguMaybe pengu_c_precis_http_post(PenguString url, PenguMap headers, PenguString body);
  PenguMaybe pengu_c_precis_http_put(PenguString url, PenguMap headers, PenguString body);
  PenguMaybe pengu_c_precis_http_delete(PenguString url, PenguMap headers);
  PenguMaybe pengu_c_precis_http_request(PenguString method, PenguString url, PenguMap headers, PenguMaybe body);
  /** Releases a PenguPrecisClientResponse obtained from a successful
 * pengu_c_precis_http_* call: frees the owned header map, body string and the
 * response struct itself. The caller-owned input URL is untouched. */
  void pengu_precis_free_response(PenguPrecisClientResponse *resp);

  void pengu_c_precis_serve_http(int port, void *handler);

  /** Opens a TCP connection. A present result holds a PenguPrecisTCPSocket* that
 * must be closed with pengu_c_precis_tcp_close(). */
PenguMaybe pengu_c_precis_tcp_connect(PenguString host, int port);
  bool pengu_c_precis_tcp_send(void *sock, PenguString data);
  PenguMaybe pengu_c_precis_tcp_recv(void *sock, int size);
  void pengu_c_precis_tcp_close(void *sock);

  PenguMaybe pengu_c_precis_dns_lookup(PenguString host);

  /** URL-encodes `s`. The returned PenguString owns its buffer: release with
 * pengu_banish_string() (or banish from PenguScript). */
  PenguString pengu_c_precis_url_encode(PenguString s);
  /** URL-decodes `s`. The returned PenguString owns its buffer: release with
 * pengu_banish_string() (or banish from PenguScript). */
  PenguString pengu_c_precis_url_decode(PenguString s);
  /** Parses a query string. The returned PenguMap owns its keys/values:
 * release with pengu_banish_map() (or banish from PenguScript). */
  PenguMap pengu_c_precis_parse_query(PenguString s);

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
  /** Owning copy of `count` bytes at `data` into a PenguList of uint8. */
  PenguList pengu_ffi_list_u8(const void *data, int count);
  /** Owning copy of `count` int32 elements at `data` into a PenguList. */
  PenguList pengu_ffi_list_i32(const void *data, int count);
  /** Owning copy of `count` double elements at `data` into a PenguList. */
  PenguList pengu_ffi_list_f64(const void *data, int count);
  /** NULL-safe owning PenguString copy of a C string (see pengu_string_new). */
  PenguString pengu_ffi_cstr_string(const char *s);
  /** Read-only view of a PenguString's internal buffer (never NULL). */
  const char *pengu_ffi_string_cstr(PenguString s);
  /** Read-only byte view of a PenguString's internal buffer (never NULL). */
  const void *pengu_ffi_string_bytes(PenguString s);
  /** Builds a map of string->int from parallel PenguString/int32 slices
 * (copies keys deeply; values copied by value). */
  PenguMap pengu_ffi_map_si(PenguSlice keys, PenguSlice vals);


#ifdef __cplusplus
}
#endif

#endif /* PENGU_RUNTIME_ORGANIZED_H */
