/*
 * std_c/miniz_bind.h — the *configured* entry point to the vendored miniz.
 *
 * Why this file exists
 * --------------------
 * `miniz.h` is a single-header library whose behaviour is selected by macros
 * that must be defined *before* the header is preprocessed.  PenguScript has no
 * preprocessor, so a `.d.pengu` binding cannot spell `#define X 1` before
 * `include "miniz.h"`.  This shim is that missing line: it selects exactly the
 * subset `std.compressus` uses and then includes the untouched upstream header.
 *
 * The same macro set is passed to the `std_c/miniz.c` translation unit by
 * `build_runtime.py` (`STD_C_DEFINES`), so the archive and every consumer
 * bundle see one configuration.  Never define these macros anywhere else.
 *
 * The subset
 * ----------
 *   MINIZ_NO_ZLIB_COMPATIBLE_NAMES
 *       Drops the `deflate`/`inflate`/`crc32`/... aliases.  Under
 *       `-std=c99`/`-std=c11` GCC defines `__STRICT_ANSI__`, so
 *       `MZ_FORCEINLINE` expands to nothing and every `static MZ_FORCEINLINE`
 *       alias becomes a plain unused `static` function: `-Wall -Wextra -Werror`
 *       would reject every bundle that imports `std.compressus`.  The aliases
 *       add nothing: the `mz_*` names are used everywhere.
 *
 *   MINIZ_NO_ARCHIVE_APIS, MINIZ_NO_STDIO, MINIZ_NO_TIME
 *       Removes the ZIP reader/writer, its `stdio.h` use and its `time.h` use.
 *       ZIP archives are out of scope for `std.compressus` (2.14+ may add a
 *       separate `std.zip`), and the C99 strict build cannot see POSIX
 *       `ftello`/`fseeko` anyway.  Keeping the subset small also keeps
 *       `libminiz.a` small.
 *
 * The remaining surface is RFC 1950 (zlib), RFC 1951 (raw deflate), CRC-32 and
 * Adler-32.  RFC 1952 (gzip) is implemented by `std.compressus` on top of it.
 *
 * License: miniz is public domain / Unlicense (see the end of `miniz.h`).
 * This shim is part of PenguScript (MIT).
 */
#ifndef PENGU_STD_C_MINIZ_BIND_H
#define PENGU_STD_C_MINIZ_BIND_H

#ifndef MINIZ_NO_ZLIB_COMPATIBLE_NAMES
#define MINIZ_NO_ZLIB_COMPATIBLE_NAMES 1
#endif

#ifndef MINIZ_NO_ARCHIVE_APIS
#define MINIZ_NO_ARCHIVE_APIS 1
#endif

#ifndef MINIZ_NO_STDIO
#define MINIZ_NO_STDIO 1
#endif

#ifndef MINIZ_NO_TIME
#define MINIZ_NO_TIME 1
#endif

#include "miniz.h"

#endif /* PENGU_STD_C_MINIZ_BIND_H */
