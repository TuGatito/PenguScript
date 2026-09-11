# C Bind Stubs (`c_bind_stubs/`)

Minimal C standard and POSIX header stubs for `pengu bind`.

## Purpose
When `pengu bind` runs the preprocessor (`gcc -E -nostdinc -I...`), these stubs provide standard types (`size_t`, `int32_t`, `pthread_t`, `ssize_t`, `FILE`, etc.) without pulling in vendor/OS headers that contain GCC/MSVC extensions or platform-specific inline assembly that `pycparser` cannot parse.

## Included Stubs
- Standard C: `assert.h`, `ctype.h`, `errno.h`, `inttypes.h`, `limits.h`, `math.h`, `stdarg.h`, `stdbool.h`, `stddef.h`, `stdint.h`, `stdio.h`, `stdlib.h`, `string.h`, `time.h`
- POSIX: `pthread.h`, `sys/types.h`, `unistd.h`, `fcntl.h`

## How to Extend
1. If a C vendor header `#include`s a missing header (e.g. `<sys/stat.h>`), add a stub file with that name under `c_bind_stubs/` (e.g. `c_bind_stubs/sys/stat.h`).
2. Add only the `typedef`s, `struct` declarations, or `#define` constants required by the target library headers.
3. Keep function prototypes minimal with basic C99 types.
