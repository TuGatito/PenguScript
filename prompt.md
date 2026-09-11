Nuevo fallo en Github Actions en todas las plataformas, por favor reparalo sin romper lo demas que ya funciona

error de macos:
Run python make_release.py
================================================================
  PenguScript Automated Release & PyInstaller Packaging Script
================================================================

[1/7] Verifying virtual environment (.venv)...
  [VENV] Creating .venv virtual environment...
  [EXEC] /Library/Frameworks/Python.framework/Versions/3.14/bin/python -m venv /Users/runner/work/PenguScript/PenguScript/.venv
  [PYTHON] Using /Users/runner/work/PenguScript/PenguScript/.venv/bin/python

[2/7] Installing / verifying build dependencies (PyInstaller, Lark, PyYAML)...
  [PIP] Checking / installing required packages...
  [EXEC] /Users/runner/work/PenguScript/PenguScript/.venv/bin/python -m pip install --upgrade pyinstaller>=6.0 lark>=1.1.0 pyyaml>=6.0 pygls>=2.0.0 lsprotocol>=2023.0.0 pycparser>=2.21 pytest>=7.0.0
Collecting pyinstaller>=6.0
  Using cached pyinstaller-6.22.2-py3-none-macosx_10_13_universal2.whl.metadata (8.5 kB)
Collecting lark>=1.1.0
  Using cached lark-1.3.1-py3-none-any.whl.metadata (1.8 kB)
Collecting pyyaml>=6.0
  Using cached pyyaml-6.0.3-cp314-cp314-macosx_11_0_arm64.whl.metadata (2.4 kB)
Collecting pygls>=2.0.0
  Using cached pygls-2.1.1-py3-none-any.whl.metadata (4.5 kB)
Collecting lsprotocol>=2023.0.0
  Using cached lsprotocol-2025.0.0-py3-none-any.whl.metadata (2.2 kB)
Collecting pycparser>=2.21
  Using cached pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
Collecting pytest>=7.0.0
  Using cached pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
Collecting altgraph (from pyinstaller>=6.0)
  Using cached altgraph-0.17.5-py2.py3-none-any.whl.metadata (7.5 kB)
Collecting macholib>=1.8 (from pyinstaller>=6.0)
  Using cached macholib-1.16.4-py2.py3-none-any.whl.metadata (12 kB)
Collecting packaging>=22.0 (from pyinstaller>=6.0)
  Using cached packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
Collecting pyinstaller-hooks-contrib>=2026.6 (from pyinstaller>=6.0)
  Using cached pyinstaller_hooks_contrib-2026.7-py3-none-any.whl.metadata (16 kB)
Collecting setuptools>=42.0.0 (from pyinstaller>=6.0)
  Using cached setuptools-84.0.0-py3-none-any.whl.metadata (6.6 kB)
Collecting attrs>=24.3.0 (from pygls>=2.0.0)
  Using cached attrs-26.1.0-py3-none-any.whl.metadata (8.8 kB)
Collecting cattrs>=23.1.2 (from pygls>=2.0.0)
  Using cached cattrs-26.2.0-py3-none-any.whl.metadata (8.5 kB)
Collecting iniconfig>=1.0.1 (from pytest>=7.0.0)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
Collecting pluggy<2,>=1.5 (from pytest>=7.0.0)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest>=7.0.0)
  Using cached pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
Collecting typing-extensions>=4.14.0 (from cattrs>=23.1.2->pygls>=2.0.0)
  Using cached typing_extensions-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Using cached pyinstaller-6.22.2-py3-none-macosx_10_13_universal2.whl (1.1 MB)
Using cached lark-1.3.1-py3-none-any.whl (113 kB)
Using cached pyyaml-6.0.3-cp314-cp314-macosx_11_0_arm64.whl (173 kB)
Using cached pygls-2.1.1-py3-none-any.whl (68 kB)
Using cached lsprotocol-2025.0.0-py3-none-any.whl (76 kB)
Using cached pycparser-3.0-py3-none-any.whl (48 kB)
Using cached pytest-9.1.1-py3-none-any.whl (386 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached attrs-26.1.0-py3-none-any.whl (67 kB)
Using cached cattrs-26.2.0-py3-none-any.whl (74 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached macholib-1.16.4-py2.py3-none-any.whl (38 kB)
Using cached altgraph-0.17.5-py2.py3-none-any.whl (21 kB)
Using cached packaging-26.3-py3-none-any.whl (129 kB)
Using cached pygments-2.21.0-py3-none-any.whl (1.3 MB)
Using cached pyinstaller_hooks_contrib-2026.7-py3-none-any.whl (459 kB)
Using cached setuptools-84.0.0-py3-none-any.whl (818 kB)
Using cached typing_extensions-4.16.0-py3-none-any.whl (45 kB)
Installing collected packages: altgraph, typing-extensions, setuptools, pyyaml, pygments, pycparser, pluggy, packaging, macholib, lark, iniconfig, attrs, pytest, pyinstaller-hooks-contrib, cattrs, pyinstaller, lsprotocol, pygls

Successfully installed altgraph-0.17.5 attrs-26.1.0 cattrs-26.2.0 iniconfig-2.3.0 lark-1.3.1 lsprotocol-2025.0.0 macholib-1.16.4 packaging-26.3 pluggy-1.6.0 pycparser-3.0 pygls-2.1.1 pygments-2.21.0 pyinstaller-6.22.2 pyinstaller-hooks-contrib-2026.7 pytest-9.1.1 pyyaml-6.0.3 setuptools-84.0.0 typing-extensions-4.16.0

[3/7] Compiling static runtime libraries (build_runtime.py)...
=== Checking external C libraries in: /Users/runner/work/PenguScript/PenguScript/extern ===
  [OK] curl already present at curl-8.21.0
  [OK] libmicrohttpd already present at libmicrohttpd-1.0.1
  [OK] libxml2 already present at libxml2-2.9.0
  [OK] mbedtls already present at mbedtls-4.2.0
  [OK] pcre2 already present at pcre2-10.47
  [OK] zlib already present at zlib-1.3.2
  [OK] raylib already present at raylib-6.0
  [OK] webui already present at webui-2.5.0-beta.3
  [OK] sqlite3 already present at sqlite-autoconf-3530400
  [OK] libuv already present at libuv-1.52.1
  [OK] xlsxio already present at xlsxio-0.2.36
  [OK] libcyaml already present at libcyaml-1.4.2
  [OK] tomlc17 already present at tomlc17-R260821
  [OK] libzip already present at libzip-1.11.3
  [OK] libexpat already present at expat-2.6.4
  [OK] libyaml already present at yaml-0.2.5
=== All external C libraries verified. ===

  [EXEC] /Users/runner/work/PenguScript/PenguScript/.venv/bin/python /Users/runner/work/PenguScript/PenguScript/build_runtime.py --rebuild
[RAYLIB] skipped (best-effort on this platform): 6.0/src/external/dirent.h:83:10: fatal error: 'io.h' file not found
   83 | #include <io.h>         // _findfirst and _findnext set errno iff they return -1
      |          ^~~~~~
1 error generated.

=== Checking external C libraries in: /Users/runner/work/PenguScript/PenguScript/extern ===
  [OK] curl already present at curl-8.21.0
  [OK] libmicrohttpd already present at libmicrohttpd-1.0.1
  [OK] libxml2 already present at libxml2-2.9.0
  [OK] mbedtls already present at mbedtls-4.2.0
  [OK] pcre2 already present at pcre2-10.47
  [OK] zlib already present at zlib-1.3.2
  [OK] raylib already present at raylib-6.0
  [OK] webui already present at webui-2.5.0-beta.3
  [OK] sqlite3 already present at sqlite-autoconf-3530400
  [OK] libuv already present at libuv-1.52.1
  [OK] xlsxio already present at xlsxio-0.2.36
  [OK] libcyaml already present at libcyaml-1.4.2
  [OK] tomlc17 already present at tomlc17-R260821
  [OK] libzip already present at libzip-1.11.3
  [OK] libexpat already present at expat-2.6.4
  [OK] libyaml already present at yaml-0.2.5
=== All external C libraries verified. ===

=== Building PenguScript Runtime (CC: /usr/bin/gcc, AR: /usr/bin/ar) ===
[ZLIB] Compiling zlib-1.3.2...
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/adler32.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/adler32.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/compress.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/compress.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/crc32.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/crc32.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/deflate.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/deflate.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzclose.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzclose.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzlib.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzlib.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzread.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzread.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzwrite.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzwrite.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/infback.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/infback.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/inffast.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/inffast.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/inflate.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/inflate.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/inftrees.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/inftrees.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/trees.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/trees.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/uncompr.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/uncompr.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /Users/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/zutil.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/zutil.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libz.a /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/adler32.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/compress.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/crc32.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/deflate.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzclose.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzlib.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzread.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/gzwrite.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/infback.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/inffast.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/inflate.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/inftrees.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/trees.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/uncompr.o /Users/runner/work/PenguScript/PenguScript/build/obj_zlib/zutil.o
[ZLIB] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libz.a
[PCRE2] Compiling pcre2-10.47 (8-bit)...
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_auto_possess.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_auto_possess.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_chkdint.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chkdint.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_compile.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_compile_cgroup.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_cgroup.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_compile_class.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_class.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_config.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_config.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_context.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_context.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_convert.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_convert.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_dfa_match.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_dfa_match.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_error.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_error.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_extuni.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_extuni.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_find_bracket.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_find_bracket.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_match.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_match_data.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_data.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_match_next.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_next.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_newline.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_newline.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_ord2utf.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ord2utf.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_pattern_info.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_pattern_info.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_script_run.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_script_run.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_serialize.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_serialize.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_string_utils.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_string_utils.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_study.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_study.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_substitute.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substitute.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_substring.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substring.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_tables.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_tables.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_ucd.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ucd.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_valid_utf.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_valid_utf.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_xclass.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_xclass.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /Users/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_chartables.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chartables.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libpcre2-8.a /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_auto_possess.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chkdint.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_cgroup.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_class.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_config.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_context.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_convert.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_dfa_match.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_error.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_extuni.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_find_bracket.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_data.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_next.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_newline.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ord2utf.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_pattern_info.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_script_run.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_serialize.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_string_utils.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_study.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substitute.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substring.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_tables.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ucd.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_valid_utf.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_xclass.o /Users/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chartables.o
[PCRE2] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libpcre2-8.a
[LIBXML2] Skipped on this platform (uses system libxml2).
[MBEDTLS] Compiling mbedtls-4.2.0 crypto...
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/md5.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/md5.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/sha1.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha1.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/sha256.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha256.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/sha512.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha512.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform/platform_util.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform_util.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /Users/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform/platform.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libmbedcrypto.a /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/md5.o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha1.o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha256.o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha512.o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform_util.o /Users/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform.o
[MBEDTLS] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libmbedcrypto.a
[CURL] Skipped on this platform (uses system libcurl).
[MICROHTTPD] Skipped on this platform (uses system libmicrohttpd).
[SQLITE3] Compiling SQLite3 amalgamation...
  [EXEC] /usr/bin/gcc -O2 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_ENABLE_FTS5 -Wno-unused-but-set-variable -I/Users/runner/work/PenguScript/PenguScript/extern/sqlite-autoconf-3530400 -c /Users/runner/work/PenguScript/PenguScript/extern/sqlite-autoconf-3530400/sqlite3.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_sqlite3/sqlite3.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libsqlite3.a /Users/runner/work/PenguScript/PenguScript/build/obj_sqlite3/sqlite3.o
[SQLITE3] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libsqlite3.a
[WEBUI] Skipped: no prebuilt Apple Silicon WebUI asset (x64-only).
[RAYLIB] Compiling Raylib (desktop, OpenGL 3.3)...
  [EXEC] /usr/bin/gcc -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -I/Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src -I/Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external/glfw/include -I/Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external/glad/include -I/Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external -Wno-implicit-function-declaration -c /Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/rcore.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_raylib/rcore.o
[ERROR] Command failed with exit code 1:
In file included from /Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/rcore.c:195:
/Users/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external/dirent.h:83:10: fatal error: 'io.h' file not found
   83 | #include <io.h>         // _findfirst and _findnext set errno iff they return -1
      |          ^~~~~~
1 error generated.

[RAYMATH] Compiling raymath shim...
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_raymath.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_raymath/wrappers_raymath.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libpengu_raymath.a /Users/runner/work/PenguScript/PenguScript/build/obj_raymath/wrappers_raymath.o
[RAYMATH] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libpengu_raymath.a
[LIBUV] Building libuv with CMake...
  [EXEC] cmake -S /Users/runner/work/PenguScript/PenguScript/extern/libuv-1.52.1 -B /Users/runner/work/PenguScript/PenguScript/build/libuv_cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DCMAKE_C_COMPILER=/usr/bin/gcc -G Ninja
  [EXEC] cmake --build /Users/runner/work/PenguScript/PenguScript/build/libuv_cmake --config Release -j 4
[LIBUV] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libuv.a
[LIBYAML] Compiling libyaml sources...
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/api.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/api.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/dumper.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/dumper.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/emitter.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/emitter.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/loader.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/loader.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/parser.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/parser.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/reader.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/reader.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/scanner.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/scanner.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/writer.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/writer.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libyaml.a /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/api.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/dumper.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/emitter.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/loader.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/parser.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/reader.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/scanner.o /Users/runner/work/PenguScript/PenguScript/build/obj_yaml/writer.o
[LIBYAML] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libyaml.a
[LIBCYAML] Compiling libcyaml sources...
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/free.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/free.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/load.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/load.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/mem.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/mem.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/save.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/save.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/utf8.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/utf8.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/util.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/util.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libcyaml.a /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/free.o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/load.o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/mem.o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/save.o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/utf8.o /Users/runner/work/PenguScript/PenguScript/build/obj_cyaml/util.o
[LIBCYAML] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libcyaml.a
[LIBZIP] Building libzip-1.11.3 with CMake...
  [EXEC] cmake -S /Users/runner/work/PenguScript/PenguScript/extern/libzip-1.11.3 -B /Users/runner/work/PenguScript/PenguScript/build/libzip_cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/gcc -G Ninja -DENABLE_BZIP2=OFF -DENABLE_LZMA=OFF -DENABLE_ZSTD=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TOOLS=OFF -DBUILD_REGRESS=OFF -DBUILD_DOC=OFF -DZLIB_INCLUDE_DIR=/Users/runner/work/PenguScript/PenguScript/build/include -DZLIB_LIBRARY=/Users/runner/work/PenguScript/PenguScript/build/lib/libz.a
  [EXEC] cmake --build /Users/runner/work/PenguScript/PenguScript/build/libzip_cmake --config Release -j 4 --target zip
[LIBZIP] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libzip.a
[LIBEXPAT] Building expat-2.6.4 with CMake...
  [EXEC] cmake -S /Users/runner/work/PenguScript/PenguScript/extern/expat-2.6.4 -B /Users/runner/work/PenguScript/PenguScript/build/expat_cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/gcc -G Ninja -DEXPAT_BUILD_TOOLS=OFF -DEXPAT_BUILD_EXAMPLES=OFF -DEXPAT_BUILD_TESTS=OFF -DEXPAT_SHARED_LIBS=OFF
  [EXEC] cmake --build /Users/runner/work/PenguScript/PenguScript/build/expat_cmake --config Release -j 4 --target expat
[LIBEXPAT] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libexpat.a
  [EXEC] /usr/bin/gcc -O2 -DSTATIC -I/Users/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/include -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/lib/xlsxio_read.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read.o
  [EXEC] /usr/bin/gcc -O2 -DSTATIC -I/Users/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/include -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/lib/xlsxio_read_sharedstrings.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read_sharedstrings.o
  [EXEC] /usr/bin/gcc -O2 -DSTATIC -I/Users/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/include -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/lib/xlsxio_write.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_write.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libxlsxio_read.a /Users/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read.o /Users/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read_sharedstrings.o
[XLSXIO] Created libxlsxio_read.a
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libxlsxio_write.a /Users/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_write.o
[XLSXIO] Created libxlsxio_write.a
[TOMLC17] Compiling tomlc17...
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/extern/tomlc17-R260821/src -Wno-array-bounds -Wno-stringop-overflow -c /Users/runner/work/PenguScript/PenguScript/extern/tomlc17-R260821/src/tomlc17.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_tomlc17/tomlc17.o
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_tomlc17.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_tomlc17/wrappers_tomlc17.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libtomlc17.a /Users/runner/work/PenguScript/PenguScript/build/obj_tomlc17/tomlc17.o /Users/runner/work/PenguScript/PenguScript/build/obj_tomlc17/wrappers_tomlc17.o
[TOMLC17] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libtomlc17.a
[PENGU_STB] Compiling single-header wrappers...
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_stb.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_stb.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_xxhash.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_xxhash.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_uuid.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_uuid.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_minicoro.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_minicoro.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/wrappers_raygui.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_raygui.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/tinyfiledialogs.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfiledialogs.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/Users/runner/work/PenguScript/PenguScript/std_c -I/Users/runner/work/PenguScript/PenguScript/build/include -c /Users/runner/work/PenguScript/PenguScript/std_c/tinyfd_moredialogs.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfd_moredialogs.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libpengu_stb.a /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_stb.o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_xxhash.o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_uuid.o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_minicoro.o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_raygui.o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfiledialogs.o /Users/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfd_moredialogs.o
[PENGU_STB] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libpengu_stb.a
[RUNTIME] Compiling pengu_runtime.c...
  [EXEC] /usr/bin/gcc -O2 -I/Users/runner/work/PenguScript/PenguScript -I/Users/runner/work/PenguScript/PenguScript/build/include -DPCRE2_STATIC -DPCRE2_CODE_UNIT_WIDTH=8 -DLIBXML_STATIC -DCURL_STATICLIB -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -I/opt/homebrew/opt/libxml2/include/libxml2 -I/opt/homebrew/Cellar/libmicrohttpd/1.0.10/include -I/opt/homebrew/opt/gnutls/include -I/opt/homebrew/Cellar/nettle/4.0/include -I/opt/homebrew/Cellar/libtasn1/4.21.0/include -I/opt/homebrew/Cellar/libidn2/2.3.8/include -I/opt/homebrew/Cellar/p11-kit/0.26.5/include/p11-kit-1 -I/opt/homebrew/Cellar/mbedtls/4.2.0/include -I/opt/homebrew/include -c /Users/runner/work/PenguScript/PenguScript/pengu_parser/pengu_runtime.c -o /Users/runner/work/PenguScript/PenguScript/build/obj_runtime/pengu_runtime.o
  [EXEC] /usr/bin/ar rcs /Users/runner/work/PenguScript/PenguScript/build/lib/libpengu_runtime.a /Users/runner/work/PenguScript/PenguScript/build/obj_runtime/pengu_runtime.o
[RUNTIME] Created /Users/runner/work/PenguScript/PenguScript/build/lib/libpengu_runtime.a
=== Runtime build finished. Built: ZLIB, PCRE2, MBEDTLS, SQLITE3, RAYMATH, LIBUV, LIBYAML, LIBCYAML, LIBZIP, LIBEXPAT, XLSXIO, TOMLC17, PENGU_STB, RUNTIME ===

[4/7] Assembling distribution assets in /Users/runner/work/PenguScript/PenguScript/pengucc_build...
  [STD] Copied standard library to /Users/runner/work/PenguScript/PenguScript/pengucc_build/std
  [LIB] Copied libpengu_stb.a to runtime/
  [LIB] Copied libtomlc17.a to runtime/
  [LIB] Copied libz.a to runtime/
  [LIB] Copied libpengu_runtime.a to runtime/
  [LIB] Copied libcyaml.a to runtime/
  [LIB] Copied libxlsxio_write.a to runtime/
  [LIB] Copied libpengu_raymath.a to runtime/
  [LIB] Copied libzip.a to runtime/
  [LIB] Copied libpcre2-8.a to runtime/
  [LIB] Copied libmbedcrypto.a to runtime/
  [LIB] Copied libuv.a to runtime/
  [LIB] Copied libyaml.a to runtime/
  [LIB] Copied libexpat.a to runtime/
  [LIB] Copied libxlsxio_read.a to runtime/
  [LIB] Copied libsqlite3.a to runtime/
  [INC] Copied dependency headers to /Users/runner/work/PenguScript/PenguScript/pengucc_build/runtime/include

[5/7] Building and packaging VS Code Extension (.vsix)...
  [VSCODE] Packaging VS Code extension...
  [EXEC] npm --version
  [VSCODE] Installing npm dependencies...
  [EXEC] npm install
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/abort-controller@2.2.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-auth@1.11.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-client@1.11.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-process@1.0.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-rest-pipeline@1.25.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-tracing@1.4.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-util@1.14.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/identity@4.13.2',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/logger@1.4.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@typespec/ts-http-runtime@0.3.8',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn deprecated whatwg-encoding@3.1.1: Use @exodus/bytes instead for a more spec-conformant and faster implementation
npm warn deprecated inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
npm warn deprecated glob@7.2.3: Old versions of glob are not supported, and contain widely publicized security vulnerabilities, which have been fixed in the current version. Please update. Support for old versions may be purchased (at exorbitant rates) by contacting i@izs.me
npm warn deprecated prebuild-install@7.1.3: No longer maintained. Please contact the author of the relevant native addon; alternatives are available.

added 192 packages, and audited 193 packages in 7s

50 packages are looking for funding
  run `npm fund` for details

5 vulnerabilities (3 moderate, 2 high)

To address issues that do not require attention, run:
  npm audit fix

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
  [VSCODE] Bundling extension with esbuild...
  [EXEC] npm run bundle

> pengus@0.10.0 bundle
> esbuild ./src/extension.ts --bundle --outfile=out/extension.js --external:vscode --format=cjs --platform=node


  out/extension.js  771.2kb

⚡ Done in 74ms
  [VSCODE] Generating .vsix package with vsce...
  [EXEC] npx -y @vscode/vsce package
Executing prepublish script 'npm run vscode:prepublish'...

> pengus@0.10.0 vscode:prepublish
> npm run bundle


> pengus@0.10.0 bundle
> esbuild ./src/extension.ts --bundle --outfile=out/extension.js --external:vscode --format=cjs --platform=node


  out/extension.js  771.2kb

⚡ Done in 26ms
Warning: This extension consists of 326 files, out of which 166 are JavaScript files. For performance reasons, you should bundle your extension: https://aka.ms/vscode-bundle-extension. You should also exclude unnecessary files by adding them to your .vscodeignore: https://aka.ms/vscode-vscodeignore.

Files included in the VSIX:
pengus-0.10.0.vsix
├─ [Content_Types].xml 
├─ extension.vsixmanifest 
└─ extension/
   ├─ LICENSE.txt 
   ├─ README.md [3.86 KB]
   ├─ language-configuration.json [0.82 KB]
   ├─ package.json [8.33 KB]
   ├─ icons/
   │  ├─ pengu_icon.png [3 MB]
   │  └─ pengu_icon_white.png [27.75 KB]
   ├─ node_modules/
   │  ├─ balanced-match/ (5 files) [6.78 KB]
   │  ├─ brace-expansion/ (5 files) [16.5 KB]
   │  ├─ minimatch/ (6 files) [41.37 KB]
   │  ├─ semver/ (53 files) [98.7 KB]
   │  ├─ vscode-jsonrpc/ (48 files) [203.49 KB]
   │  ├─ vscode-languageclient/ (121 files) [637.35 KB]
   │  ├─ vscode-languageserver-protocol/ (68 files) [356.78 KB]
   │  └─ vscode-languageserver-types/ (9 files) [367.87 KB]
   ├─ out/
   │  └─ extension.js [771.15 KB]
   ├─ snippets/
   │  └─ pengus.json [31.29 KB]
   └─ syntaxes/
      └─ pengus.tmLanguage.json [6.6 KB]

=> Run vsce ls --tree to see all included files.

Packaged: /Users/runner/work/PenguScript/PenguScript/vscode-extension/pengus-0.10.0.vsix (326 files, 3.57 MB)
  [VSCODE] Copied pengus-0.10.0.vsix -> /Users/runner/work/PenguScript/PenguScript/pengucc_build/pengus-0.10.0.vsix

[6/7] Packaging standalone CLI executable with PyInstaller...
  [EXEC] /Users/runner/work/PenguScript/PenguScript/.venv/bin/python -m PyInstaller --clean --name pengu --onefile --console --distpath /Users/runner/work/PenguScript/PenguScript/pengucc_build --workpath /Users/runner/work/PenguScript/PenguScript/build/pyinstaller_work --specpath /Users/runner/work/PenguScript/PenguScript/build --noconfirm --add-data /Users/runner/work/PenguScript/PenguScript/std:std --add-data /Users/runner/work/PenguScript/PenguScript/pengu_runtime.h:. --add-data /Users/runner/work/PenguScript/PenguScript/VERSION:. --add-data /Users/runner/work/PenguScript/PenguScript/c_bind_stubs:c_bind_stubs --hidden-import pygls --hidden-import pygls.lsp --hidden-import pygls.lsp.server --hidden-import pygls.protocol --hidden-import pygls.capabilities --hidden-import lsprotocol --hidden-import lsprotocol.types --hidden-import lsprotocol.converters --hidden-import cattrs --hidden-import attrs --hidden-import pycparser --hidden-import pycparser.c_parser --hidden-import pycparser.c_lexer --hidden-import pycparser.c_ast --hidden-import pycparser.plyparser --hidden-import pycparser.ast_transforms --hidden-import lark --hidden-import lark.parsers --hidden-import lark.parsers.lalr_parser --hidden-import pengu_bind --hidden-import pengu_lsp --hidden-import pengu_lsp.server --hidden-import pengu_lsp.completions --hidden-import pengu_lsp.hover --hidden-import pengu_lsp.code_actions --hidden-import pengu_lsp.formatting --hidden-import pengu_parser --hidden-import pengu_parser.pengu_parser --hidden-import pengu_parser.pengu_checker --hidden-import pengu_parser.pengu_codegen --hidden-import pengu_parser.pengu_symbols --hidden-import pengu_parser.pengu_types --hidden-import pengu_parser.pengu_errors --hidden-import pengu_parser.pengu_infer --hidden-import pengu_parser.pengu_grammar --collect-submodules lsprotocol --collect-submodules pygls --collect-submodules cattrs --collect-submodules attrs /Users/runner/work/PenguScript/PenguScript/pengu_project.py
126 INFO: PyInstaller: 6.22.2, contrib hooks: 2026.7
127 INFO: Python: 3.14.7
170 INFO: Platform: macOS-26.6.2-arm64-arm-64bit-Mach-O
171 INFO: Python environment: /Users/runner/work/PenguScript/PenguScript/.venv
173 INFO: wrote /Users/runner/work/PenguScript/PenguScript/build/pengu.spec
181 INFO: Removing temporary files and cleaning cache in /Users/runner/Library/Application Support/pyinstaller
1905 INFO: Module search paths (PYTHONPATH):
['/Users/runner/work/PenguScript/PenguScript',
 '/Library/Frameworks/Python.framework/Versions/3.14/lib/python314.zip',
 '/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14',
 '/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/lib-dynload',
 '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages',
 '/Users/runner/work/PenguScript/PenguScript']
2171 INFO: Appending 'datas' from .spec
2184 INFO: checking Analysis
2184 INFO: Building Analysis because Analysis-00.toc is non existent
2184 INFO: Looking for Python shared library...
2214 INFO: Using Python shared library: /Library/Frameworks/Python.framework/Versions/3.14/Python
2214 INFO: Running Analysis Analysis-00.toc
2214 INFO: Target bytecode optimization level: 0
2215 INFO: Initializing module dependency graph...
2218 INFO: Initializing module graph hook caches...
2240 INFO: Analyzing modules for base_library.zip ...
4076 INFO: Processing standard module hook 'hook-encodings.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
4530 INFO: Processing standard module hook 'hook-pickle.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
4863 INFO: Processing standard module hook 'hook-math.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
4989 INFO: Processing standard module hook 'hook-difflib.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
5011 INFO: Processing standard module hook 'hook-heapq.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9011 INFO: Caching module dependency graph...
9064 INFO: Analyzing /Users/runner/work/PenguScript/PenguScript/pengu_project.py
9168 INFO: Processing pre-safe-import-module hook 'hook-tomli.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9169 INFO: SetuptoolsInfo: initializing cached setuptools info...
9575 INFO: Setuptools: 'tomli' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.tomli'!
9590 INFO: Processing standard module hook 'hook-setuptools.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9637 INFO: Processing standard module hook 'hook-platform.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9676 INFO: Processing standard module hook 'hook-xml.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9726 INFO: Processing standard module hook 'hook-sysconfig.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9740 INFO: Processing standard module hook 'hook-_osx_support.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9754 INFO: Processing standard module hook 'hook-_ctypes.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9769 INFO: Processing pre-safe-import-module hook 'hook-distutils.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9814 INFO: Processing pre-safe-import-module hook 'hook-jaraco.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9815 INFO: Setuptools: 'jaraco' appears to be a full setuptools-vendored copy - creating alias to 'setuptools._vendor.jaraco'!
9826 INFO: Processing pre-safe-import-module hook 'hook-more_itertools.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9826 INFO: Setuptools: 'more_itertools' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.more_itertools'!
10015 INFO: Processing pre-safe-import-module hook 'hook-typing_extensions.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
10330 INFO: Processing standard module hook 'hook-multiprocessing.util.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
11159 INFO: Processing pre-safe-import-module hook 'hook-packaging.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
11565 INFO: Processing standard module hook 'hook-setuptools._vendor.jaraco.text.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
11568 INFO: Processing pre-safe-import-module hook 'hook-importlib_resources.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
11590 INFO: Processing pre-safe-import-module hook 'hook-backports.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
11592 INFO: Setuptools: 'backports' appears to be a full setuptools-vendored copy - creating alias to 'setuptools._vendor.backports'!
12912 INFO: Processing pre-safe-import-module hook 'hook-wheel.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
12914 INFO: Setuptools: 'wheel' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.wheel'!
13422 INFO: Processing standard module hook 'hook-lark.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/lark/__pyinstaller'
14916 INFO: Processing standard module hook 'hook-pycparser.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/_pyinstaller_hooks_contrib/stdhooks'
16612 INFO: Analyzing hidden import 'pycparser.plyparser'
16612 ERROR: Hidden import 'pycparser.plyparser' not found
16613 INFO: Analyzing hidden import 'pygls.cli'
16616 INFO: Analyzing hidden import 'pygls.client'
16625 INFO: Analyzing hidden import 'pygls.lsp._base_client'
16671 INFO: Analyzing hidden import 'pygls.lsp.client'
16672 INFO: Analyzing hidden import 'cattrs.preconf'
16676 INFO: Analyzing hidden import 'cattrs.preconf.bson'
16699 INFO: Analyzing hidden import 'cattrs.preconf.cbor2'
16704 INFO: Analyzing hidden import 'cattrs.preconf.json'
16708 INFO: Analyzing hidden import 'cattrs.preconf.msgpack'
16714 INFO: Analyzing hidden import 'cattrs.preconf.msgspec'
16726 INFO: Analyzing hidden import 'cattrs.preconf.orjson'
16732 INFO: Analyzing hidden import 'cattrs.preconf.pyyaml'
16735 INFO: Analyzing hidden import 'cattrs.preconf.tomlkit'
16744 INFO: Analyzing hidden import 'cattrs.preconf.tomllib'
16752 INFO: Analyzing hidden import 'cattrs.preconf.ujson'
16760 INFO: Processing module hooks (post-graph stage)...
16761 WARNING: Hidden import "pycparser.lextab" not found!
16761 WARNING: Hidden import "pycparser.yacctab" not found!
17234 INFO: Processing standard module hook 'hook-webbrowser.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
17714 INFO: Performing binary vs. data reclassification (81 entries)
17756 INFO: Looking for ctypes DLLs
17789 INFO: Analyzing run-time hooks ...
17792 INFO: Including run-time hook 'pyi_rth_inspect.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
17795 INFO: Including run-time hook 'pyi_rth_pkgutil.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
17796 INFO: Including run-time hook 'pyi_rth_multiprocessing.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
17797 INFO: Including run-time hook 'pyi_rth_setuptools.py' from '/Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
17806 INFO: Creating base_library.zip...
17821 INFO: Looking for dynamic libraries
18121 INFO: Warnings written to /Users/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/warn-pengu.txt
18143 INFO: Graph cross-reference written to /Users/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/xref-pengu.html
18230 INFO: checking PYZ
18230 INFO: Building PYZ because PYZ-00.toc is non existent
18230 INFO: Building PYZ (ZlibArchive) /Users/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/PYZ-00.pyz
18962 INFO: Building PYZ (ZlibArchive) /Users/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/PYZ-00.pyz completed successfully.
18981 INFO: EXE target arch: arm64
18981 INFO: Code signing identity: None
18991 INFO: checking PKG
18991 INFO: Building PKG because PKG-00.toc is non existent
18991 INFO: Building PKG (CArchive) pengu.pkg
35884 INFO: Building PKG (CArchive) pengu.pkg completed successfully.
35891 INFO: Bootloader /Users/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/bootloader/Darwin-64bit/run
35891 INFO: checking EXE
35891 INFO: Building EXE because EXE-00.toc is non existent
35891 INFO: Building EXE from EXE-00.toc
35892 INFO: Copying bootloader EXE to /Users/runner/work/PenguScript/PenguScript/pengucc_build/pengu
35893 INFO: Converting EXE to target arch (arm64)
35921 INFO: Removing signature(s) from EXE
35946 INFO: Modifying Mach-O image UUID(s) in EXE
35970 INFO: Appending PKG archive to EXE
35989 INFO: Fixing EXE headers for code signing
36021 INFO: Re-signing the EXE
36111 INFO: Building EXE from EXE-00.toc completed successfully.
36140 INFO: Build complete! The results are available in: /Users/runner/work/PenguScript/PenguScript/pengucc_build
  [DOCS] Generated README_RELEASE.md and /Users/runner/work/PenguScript/PenguScript/pengucc_build/README.md

[7/7] Running release verification & smoke tests...
  [TEST 1] Verifying pengu --help...
  [EXEC] /Users/runner/work/PenguScript/PenguScript/pengucc_build/pengu --help
usage: pengu [-h] [-V]
             {init,add,build,run,test,check,update,bind,fmt,clean,lsp,doc} ...

PenguScript v0.10.0 Package & Build Manager

positional arguments:
  {init,add,build,run,test,check,update,bind,fmt,clean,lsp,doc}
                        Available subcommands
    init                Create a new PenguScript project template
    add                 Add an external dependency or binding to the project
    build               Compile the project according to configuration
    run                 Build and execute the project target, or run a
                        standalone .pengu script
    test                Compile and run the project's integrated unit tests
    check               Parse and type-check every module without generating
                        code (CI)
    update              Update dependencies: git pull + re-run build scripts
    bind                Generate a .d.pengu binding from a C header
    fmt                 Format .pengu files or directories (standard style)
    clean               Remove build directory and generated artifacts
    lsp                 Launch the PenguScript Language Server Protocol (LSP)
    doc                 Generate Markdown documentation from ## comments

options:
  -h, --help            show this help message and exit
  -V, --version         Print the PenguScript toolchain version and exit

Examples: pengu init my_game --type exe pengu add https://github.com/webui-
dev/webui pengu add ../local_binding -n my_binding pengu build --profile
release pengu build --cc clang --verbose pengu check # parse + type-check
without codegen (CI) pengu fmt src/ tests/ # format files/directories pengu
fmt --check src/ # verify formatting (exit 1 if changes) pengu run --profile
debug pengu run hello.pengu # run a standalone script (when main: enabled)
pengu update # git pull + rebuild every dependency pengu bind webui.h --prefix
webui_ --links webui-2-static ole32 stdc++ uuid pengu clean

  [TEST 2] Testing project initialization...
  [EXEC] /Users/runner/work/PenguScript/PenguScript/pengucc_build/pengu init smoke_proj --type exe --links pengu_runtime
     Created exe project 'smoke_proj' at /Users/runner/work/PenguScript/PenguScript/scratch/smoke_release_test/smoke_proj
  [TEST 3] Testing standalone compilation and execution ('pengu run')...
  [EXEC] /Users/runner/work/PenguScript/PenguScript/pengucc_build/pengu run

[ERROR] Command failed with exit code 1: /Users/runner/work/PenguScript/PenguScript/pengucc_build/pengu run
Stderr: Traceback (most recent call last):
  File "pengu_project.py", line 2301, in <module>
  File "pengu_project.py", line 2199, in main
  File "pengu_project.py", line 1874, in run_project
  File "pengu_project.py", line 1257, in build_project
  File "pengu_project.py", line 1173, in compile
  File "pengu_project.py", line 892, in bundle
  File "pengu_parser/pengu_checker.py", line 196, in check
  File "pengu_parser/pengu_checker.py", line 1717, in _check_node
  File "pengu_parser/pengu_infer.py", line 2368, in infer
  File "pengu_parser/pengu_infer.py", line 511, in _reject_list_glued_operator
pengu_parser.pengu_errors.TypeMismatchError: [line 6, col 5] Ambiguous 'and' after a call with arguments
[PYI-20373:ERROR] Failed to execute script 'pengu_project' due to unhandled exception!

Stdout:    Compiling smoke_proj v0.1.0 (exe) [debug]

Error: Process completed with exit code 1.

error de linux:
Run python make_release.py
================================================================
  PenguScript Automated Release & PyInstaller Packaging Script
================================================================

[1/7] Verifying virtual environment (.venv)...
  [VENV] Creating .venv virtual environment...
  [EXEC] /opt/hostedtoolcache/Python/3.14.7/x64/bin/python -m venv /home/runner/work/PenguScript/PenguScript/.venv
  [PYTHON] Using /home/runner/work/PenguScript/PenguScript/.venv/bin/python

[2/7] Installing / verifying build dependencies (PyInstaller, Lark, PyYAML)...
  [PIP] Checking / installing required packages...
  [EXEC] /home/runner/work/PenguScript/PenguScript/.venv/bin/python -m pip install --upgrade pyinstaller>=6.0 lark>=1.1.0 pyyaml>=6.0 pygls>=2.0.0 lsprotocol>=2023.0.0 pycparser>=2.21 pytest>=7.0.0
Collecting pyinstaller>=6.0
  Using cached pyinstaller-6.22.2-py3-none-manylinux2014_x86_64.whl.metadata (8.5 kB)
Collecting lark>=1.1.0
  Using cached lark-1.3.1-py3-none-any.whl.metadata (1.8 kB)
Collecting pyyaml>=6.0
  Using cached pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Collecting pygls>=2.0.0
  Using cached pygls-2.1.1-py3-none-any.whl.metadata (4.5 kB)
Collecting lsprotocol>=2023.0.0
  Using cached lsprotocol-2025.0.0-py3-none-any.whl.metadata (2.2 kB)
Collecting pycparser>=2.21
  Using cached pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
Collecting pytest>=7.0.0
  Using cached pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
Collecting altgraph (from pyinstaller>=6.0)
  Using cached altgraph-0.17.5-py2.py3-none-any.whl.metadata (7.5 kB)
Collecting packaging>=22.0 (from pyinstaller>=6.0)
  Using cached packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
Collecting pyinstaller-hooks-contrib>=2026.6 (from pyinstaller>=6.0)
  Using cached pyinstaller_hooks_contrib-2026.7-py3-none-any.whl.metadata (16 kB)
Collecting setuptools>=42.0.0 (from pyinstaller>=6.0)
  Using cached setuptools-84.0.0-py3-none-any.whl.metadata (6.6 kB)
Collecting attrs>=24.3.0 (from pygls>=2.0.0)
  Using cached attrs-26.1.0-py3-none-any.whl.metadata (8.8 kB)
Collecting cattrs>=23.1.2 (from pygls>=2.0.0)
  Using cached cattrs-26.2.0-py3-none-any.whl.metadata (8.5 kB)
Collecting iniconfig>=1.0.1 (from pytest>=7.0.0)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
Collecting pluggy<2,>=1.5 (from pytest>=7.0.0)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest>=7.0.0)
  Using cached pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
Collecting typing-extensions>=4.14.0 (from cattrs>=23.1.2->pygls>=2.0.0)
  Using cached typing_extensions-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Using cached pyinstaller-6.22.2-py3-none-manylinux2014_x86_64.whl (762 kB)
Using cached lark-1.3.1-py3-none-any.whl (113 kB)
Using cached pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (794 kB)
Using cached pygls-2.1.1-py3-none-any.whl (68 kB)
Using cached lsprotocol-2025.0.0-py3-none-any.whl (76 kB)
Using cached pycparser-3.0-py3-none-any.whl (48 kB)
Using cached pytest-9.1.1-py3-none-any.whl (386 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached attrs-26.1.0-py3-none-any.whl (67 kB)
Using cached cattrs-26.2.0-py3-none-any.whl (74 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached packaging-26.3-py3-none-any.whl (129 kB)
Using cached pygments-2.21.0-py3-none-any.whl (1.3 MB)
Using cached pyinstaller_hooks_contrib-2026.7-py3-none-any.whl (459 kB)
Using cached setuptools-84.0.0-py3-none-any.whl (818 kB)
Using cached typing_extensions-4.16.0-py3-none-any.whl (45 kB)
Using cached altgraph-0.17.5-py2.py3-none-any.whl (21 kB)
Installing collected packages: altgraph, typing-extensions, setuptools, pyyaml, pygments, pycparser, pluggy, packaging, lark, iniconfig, attrs, pytest, pyinstaller-hooks-contrib, cattrs, pyinstaller, lsprotocol, pygls

Successfully installed altgraph-0.17.5 attrs-26.1.0 cattrs-26.2.0 iniconfig-2.3.0 lark-1.3.1 lsprotocol-2025.0.0 packaging-26.3 pluggy-1.6.0 pycparser-3.0 pygls-2.1.1 pygments-2.21.0 pyinstaller-6.22.2 pyinstaller-hooks-contrib-2026.7 pytest-9.1.1 pyyaml-6.0.3 setuptools-84.0.0 typing-extensions-4.16.0

[3/7] Compiling static runtime libraries (build_runtime.py)...
=== Checking external C libraries in: /home/runner/work/PenguScript/PenguScript/extern ===
  [OK] curl already present at curl-8.21.0
  [OK] libmicrohttpd already present at libmicrohttpd-1.0.1
  [OK] libxml2 already present at libxml2-2.9.0
  [OK] mbedtls already present at mbedtls-4.2.0
  [OK] pcre2 already present at pcre2-10.47
  [OK] zlib already present at zlib-1.3.2
  [OK] raylib already present at raylib-6.0
  [OK] webui already present at webui-2.5.0-beta.3
  [OK] sqlite3 already present at sqlite-autoconf-3530400
  [OK] libuv already present at libuv-1.52.1
  [OK] xlsxio already present at xlsxio-0.2.36
  [OK] libcyaml already present at libcyaml-1.4.2
  [OK] tomlc17 already present at tomlc17-R260821
  [OK] libzip already present at libzip-1.11.3
  [OK] libexpat already present at expat-2.6.4
  [OK] libyaml already present at yaml-0.2.5
=== All external C libraries verified. ===

  [EXEC] /home/runner/work/PenguScript/PenguScript/.venv/bin/python /home/runner/work/PenguScript/PenguScript/build_runtime.py --rebuild
[RAYLIB] skipped (best-effort on this platform): l/dirent.h:83:10: fatal error: io.h: No such file or directory
   83 | #include <io.h>         // _findfirst and _findnext set errno iff they return -1
      |          ^~~~~~
compilation terminated.

=== Checking external C libraries in: /home/runner/work/PenguScript/PenguScript/extern ===
  [OK] curl already present at curl-8.21.0
  [OK] libmicrohttpd already present at libmicrohttpd-1.0.1
  [OK] libxml2 already present at libxml2-2.9.0
  [OK] mbedtls already present at mbedtls-4.2.0
  [OK] pcre2 already present at pcre2-10.47
  [OK] zlib already present at zlib-1.3.2
  [OK] raylib already present at raylib-6.0
  [OK] webui already present at webui-2.5.0-beta.3
  [OK] sqlite3 already present at sqlite-autoconf-3530400
  [OK] libuv already present at libuv-1.52.1
  [OK] xlsxio already present at xlsxio-0.2.36
  [OK] libcyaml already present at libcyaml-1.4.2
  [OK] tomlc17 already present at tomlc17-R260821
  [OK] libzip already present at libzip-1.11.3
  [OK] libexpat already present at expat-2.6.4
  [OK] libyaml already present at yaml-0.2.5
=== All external C libraries verified. ===

=== Building PenguScript Runtime (CC: /usr/bin/gcc, AR: /usr/bin/ar) ===
[ZLIB] Compiling zlib-1.3.2...
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/adler32.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/adler32.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/compress.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/compress.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/crc32.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/crc32.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/deflate.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/deflate.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzclose.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzclose.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzlib.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzlib.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzread.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzread.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/gzwrite.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzwrite.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/infback.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/infback.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/inffast.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/inffast.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/inflate.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/inflate.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/inftrees.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/inftrees.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/trees.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/trees.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/uncompr.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/uncompr.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2 -include unistd.h -c /home/runner/work/PenguScript/PenguScript/extern/zlib-1.3.2/zutil.c -o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/zutil.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libz.a /home/runner/work/PenguScript/PenguScript/build/obj_zlib/adler32.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/compress.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/crc32.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/deflate.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzclose.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzlib.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzread.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/gzwrite.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/infback.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/inffast.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/inflate.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/inftrees.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/trees.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/uncompr.o /home/runner/work/PenguScript/PenguScript/build/obj_zlib/zutil.o
[ZLIB] Created /home/runner/work/PenguScript/PenguScript/build/lib/libz.a
[PCRE2] Compiling pcre2-10.47 (8-bit)...
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_auto_possess.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_auto_possess.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_chkdint.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chkdint.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_compile.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_compile_cgroup.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_cgroup.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_compile_class.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_class.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_config.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_config.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_context.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_context.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_convert.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_convert.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_dfa_match.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_dfa_match.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_error.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_error.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_extuni.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_extuni.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_find_bracket.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_find_bracket.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_match.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_match_data.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_data.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_match_next.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_next.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_newline.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_newline.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_ord2utf.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ord2utf.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_pattern_info.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_pattern_info.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_script_run.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_script_run.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_serialize.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_serialize.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_string_utils.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_string_utils.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_study.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_study.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_substitute.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substitute.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_substring.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substring.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_tables.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_tables.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_ucd.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ucd.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_valid_utf.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_valid_utf.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_xclass.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_xclass.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -I/home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src -c /home/runner/work/PenguScript/PenguScript/extern/pcre2-10.47/src/pcre2_chartables.c -o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chartables.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libpcre2-8.a /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_auto_possess.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chkdint.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_cgroup.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_compile_class.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_config.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_context.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_convert.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_dfa_match.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_error.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_extuni.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_find_bracket.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_data.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_match_next.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_newline.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ord2utf.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_pattern_info.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_script_run.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_serialize.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_string_utils.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_study.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substitute.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_substring.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_tables.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_ucd.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_valid_utf.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_xclass.o /home/runner/work/PenguScript/PenguScript/build/obj_pcre2/pcre2_chartables.o
[PCRE2] Created /home/runner/work/PenguScript/PenguScript/build/lib/libpcre2-8.a
[LIBXML2] Skipped on this platform (uses system libxml2).
[MBEDTLS] Compiling mbedtls-4.2.0 crypto...
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/md5.c -o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/md5.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/sha1.c -o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha1.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/sha256.c -o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha256.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/src/sha512.c -o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha512.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform/platform_util.c -o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform_util.o
  [EXEC] /usr/bin/gcc -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/drivers/builtin/include -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/core -I/home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform -c /home/runner/work/PenguScript/PenguScript/extern/mbedtls-4.2.0/tf-psa-crypto/platform/platform.c -o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libmbedcrypto.a /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/md5.o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha1.o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha256.o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/sha512.o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform_util.o /home/runner/work/PenguScript/PenguScript/build/obj_mbedtls/platform.o
[MBEDTLS] Created /home/runner/work/PenguScript/PenguScript/build/lib/libmbedcrypto.a
[CURL] Skipped on this platform (uses system libcurl).
[MICROHTTPD] Skipped on this platform (uses system libmicrohttpd).
[SQLITE3] Compiling SQLite3 amalgamation...
  [EXEC] /usr/bin/gcc -O2 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_ENABLE_FTS5 -Wno-unused-but-set-variable -I/home/runner/work/PenguScript/PenguScript/extern/sqlite-autoconf-3530400 -c /home/runner/work/PenguScript/PenguScript/extern/sqlite-autoconf-3530400/sqlite3.c -o /home/runner/work/PenguScript/PenguScript/build/obj_sqlite3/sqlite3.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libsqlite3.a /home/runner/work/PenguScript/PenguScript/build/obj_sqlite3/sqlite3.o
[SQLITE3] Created /home/runner/work/PenguScript/PenguScript/build/lib/libsqlite3.a
[WEBUI] Installed /home/runner/work/PenguScript/PenguScript/build/lib/libwebui.a
[RAYLIB] Compiling Raylib (desktop, OpenGL 3.3)...
  [EXEC] /usr/bin/gcc -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -I/home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src -I/home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external/glfw/include -I/home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external/glad/include -I/home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external -Wno-implicit-function-declaration -D_GLFW_X11 -c /home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/rcore.c -o /home/runner/work/PenguScript/PenguScript/build/obj_raylib/rcore.o
[ERROR] Command failed with exit code 1:
In file included from /home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/rcore.c:195:
/home/runner/work/PenguScript/PenguScript/extern/raylib-6.0/src/external/dirent.h:83:10: fatal error: io.h: No such file or directory
   83 | #include <io.h>         // _findfirst and _findnext set errno iff they return -1
      |          ^~~~~~
compilation terminated.

[RAYMATH] Compiling raymath shim...
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_raymath.c -o /home/runner/work/PenguScript/PenguScript/build/obj_raymath/wrappers_raymath.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libpengu_raymath.a /home/runner/work/PenguScript/PenguScript/build/obj_raymath/wrappers_raymath.o
[RAYMATH] Created /home/runner/work/PenguScript/PenguScript/build/lib/libpengu_raymath.a
[LIBUV] Building libuv with CMake...
  [EXEC] cmake -S /home/runner/work/PenguScript/PenguScript/extern/libuv-1.52.1 -B /home/runner/work/PenguScript/PenguScript/build/libuv_cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DCMAKE_C_COMPILER=/usr/bin/gcc -G Ninja
  [EXEC] cmake --build /home/runner/work/PenguScript/PenguScript/build/libuv_cmake --config Release -j 4
[LIBUV] Created /home/runner/work/PenguScript/PenguScript/build/lib/libuv.a
[LIBYAML] Compiling libyaml sources...
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/api.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/api.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/dumper.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/dumper.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/emitter.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/emitter.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/loader.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/loader.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/parser.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/parser.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/reader.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/reader.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/scanner.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/scanner.o
  [EXEC] /usr/bin/gcc -O2 -DHAVE_CONFIG_H -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/include -I/home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/yaml-0.2.5/src/writer.c -o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/writer.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libyaml.a /home/runner/work/PenguScript/PenguScript/build/obj_yaml/api.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/dumper.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/emitter.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/loader.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/parser.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/reader.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/scanner.o /home/runner/work/PenguScript/PenguScript/build/obj_yaml/writer.o
[LIBYAML] Created /home/runner/work/PenguScript/PenguScript/build/lib/libyaml.a
[LIBCYAML] Compiling libcyaml sources...
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/free.c -o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/free.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/load.c -o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/load.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/mem.c -o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/mem.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/save.c -o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/save.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/utf8.c -o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/utf8.o
  [EXEC] /usr/bin/gcc -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/include -I/home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/libcyaml-1.4.2/src/util.c -o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/util.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libcyaml.a /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/free.o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/load.o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/mem.o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/save.o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/utf8.o /home/runner/work/PenguScript/PenguScript/build/obj_cyaml/util.o
[LIBCYAML] Created /home/runner/work/PenguScript/PenguScript/build/lib/libcyaml.a
[LIBZIP] Building libzip-1.11.3 with CMake...
  [EXEC] cmake -S /home/runner/work/PenguScript/PenguScript/extern/libzip-1.11.3 -B /home/runner/work/PenguScript/PenguScript/build/libzip_cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/gcc -G Ninja -DENABLE_BZIP2=OFF -DENABLE_LZMA=OFF -DENABLE_ZSTD=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TOOLS=OFF -DBUILD_REGRESS=OFF -DBUILD_DOC=OFF -DZLIB_INCLUDE_DIR=/home/runner/work/PenguScript/PenguScript/build/include -DZLIB_LIBRARY=/home/runner/work/PenguScript/PenguScript/build/lib/libz.a
  [EXEC] cmake --build /home/runner/work/PenguScript/PenguScript/build/libzip_cmake --config Release -j 4 --target zip
[LIBZIP] Created /home/runner/work/PenguScript/PenguScript/build/lib/libzip.a
[LIBEXPAT] Building expat-2.6.4 with CMake...
  [EXEC] cmake -S /home/runner/work/PenguScript/PenguScript/extern/expat-2.6.4 -B /home/runner/work/PenguScript/PenguScript/build/expat_cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/usr/bin/gcc -G Ninja -DEXPAT_BUILD_TOOLS=OFF -DEXPAT_BUILD_EXAMPLES=OFF -DEXPAT_BUILD_TESTS=OFF -DEXPAT_SHARED_LIBS=OFF
  [EXEC] cmake --build /home/runner/work/PenguScript/PenguScript/build/expat_cmake --config Release -j 4 --target expat
[LIBEXPAT] Created /home/runner/work/PenguScript/PenguScript/build/lib/libexpat.a
  [EXEC] /usr/bin/gcc -O2 -DSTATIC -I/home/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/include -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/lib/xlsxio_read.c -o /home/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read.o
  [EXEC] /usr/bin/gcc -O2 -DSTATIC -I/home/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/include -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/lib/xlsxio_read_sharedstrings.c -o /home/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read_sharedstrings.o
  [EXEC] /usr/bin/gcc -O2 -DSTATIC -I/home/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/include -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/extern/xlsxio-0.2.36/lib/xlsxio_write.c -o /home/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_write.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libxlsxio_read.a /home/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read.o /home/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_read_sharedstrings.o
[XLSXIO] Created libxlsxio_read.a
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libxlsxio_write.a /home/runner/work/PenguScript/PenguScript/build/obj_xlsxio_lib/xlsxio_write.o
[XLSXIO] Created libxlsxio_write.a
[TOMLC17] Compiling tomlc17...
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/extern/tomlc17-R260821/src -Wno-array-bounds -Wno-stringop-overflow -c /home/runner/work/PenguScript/PenguScript/extern/tomlc17-R260821/src/tomlc17.c -o /home/runner/work/PenguScript/PenguScript/build/obj_tomlc17/tomlc17.o
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_tomlc17.c -o /home/runner/work/PenguScript/PenguScript/build/obj_tomlc17/wrappers_tomlc17.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libtomlc17.a /home/runner/work/PenguScript/PenguScript/build/obj_tomlc17/tomlc17.o /home/runner/work/PenguScript/PenguScript/build/obj_tomlc17/wrappers_tomlc17.o
[TOMLC17] Created /home/runner/work/PenguScript/PenguScript/build/lib/libtomlc17.a
[PENGU_STB] Compiling single-header wrappers...
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_stb.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_stb.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_xxhash.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_xxhash.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_uuid.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_uuid.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_minicoro.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_minicoro.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/wrappers_raygui.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_raygui.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/tinyfiledialogs.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfiledialogs.o
  [EXEC] /usr/bin/gcc -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -I/home/runner/work/PenguScript/PenguScript/std_c -I/home/runner/work/PenguScript/PenguScript/build/include -c /home/runner/work/PenguScript/PenguScript/std_c/tinyfd_moredialogs.c -o /home/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfd_moredialogs.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libpengu_stb.a /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_stb.o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_xxhash.o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_uuid.o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_minicoro.o /home/runner/work/PenguScript/PenguScript/build/obj_stb/wrappers_raygui.o /home/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfiledialogs.o /home/runner/work/PenguScript/PenguScript/build/obj_stb/tinyfd_moredialogs.o
[PENGU_STB] Created /home/runner/work/PenguScript/PenguScript/build/lib/libpengu_stb.a
[RUNTIME] Compiling pengu_runtime.c...
  [EXEC] /usr/bin/gcc -O2 -I/home/runner/work/PenguScript/PenguScript -I/home/runner/work/PenguScript/PenguScript/build/include -DPCRE2_STATIC -DPCRE2_CODE_UNIT_WIDTH=8 -DLIBXML_STATIC -DCURL_STATICLIB -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -I/usr/include/libxml2 -I/usr/include/x86_64-linux-gnu -I/usr/include/p11-kit-1 -I/usr/local/include -c /home/runner/work/PenguScript/PenguScript/pengu_parser/pengu_runtime.c -o /home/runner/work/PenguScript/PenguScript/build/obj_runtime/pengu_runtime.o
  [EXEC] /usr/bin/ar rcs /home/runner/work/PenguScript/PenguScript/build/lib/libpengu_runtime.a /home/runner/work/PenguScript/PenguScript/build/obj_runtime/pengu_runtime.o
[RUNTIME] Created /home/runner/work/PenguScript/PenguScript/build/lib/libpengu_runtime.a
=== Runtime build finished. Built: ZLIB, PCRE2, MBEDTLS, SQLITE3, WEBUI, RAYMATH, LIBUV, LIBYAML, LIBCYAML, LIBZIP, LIBEXPAT, XLSXIO, TOMLC17, PENGU_STB, RUNTIME ===

[4/7] Assembling distribution assets in /home/runner/work/PenguScript/PenguScript/pengucc_build...
  [STD] Copied standard library to /home/runner/work/PenguScript/PenguScript/pengucc_build/std
  [LIB] Copied libyaml.a to runtime/
  [LIB] Copied libmbedcrypto.a to runtime/
  [LIB] Copied libexpat.a to runtime/
  [LIB] Copied libuv.a to runtime/
  [LIB] Copied libwebui.a to runtime/
  [LIB] Copied libtomlc17.a to runtime/
  [LIB] Copied libxlsxio_read.a to runtime/
  [LIB] Copied libz.a to runtime/
  [LIB] Copied libxlsxio_write.a to runtime/
  [LIB] Copied libpengu_raymath.a to runtime/
  [LIB] Copied libzip.a to runtime/
  [LIB] Copied libcyaml.a to runtime/
  [LIB] Copied libpengu_runtime.a to runtime/
  [LIB] Copied libpengu_stb.a to runtime/
  [LIB] Copied libpcre2-8.a to runtime/
  [LIB] Copied libsqlite3.a to runtime/
  [INC] Copied dependency headers to /home/runner/work/PenguScript/PenguScript/pengucc_build/runtime/include

[5/7] Building and packaging VS Code Extension (.vsix)...
  [VSCODE] Packaging VS Code extension...
  [EXEC] npm --version
  [VSCODE] Installing npm dependencies...
  [EXEC] npm install
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/abort-controller@2.2.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-auth@1.11.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-client@1.11.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-process@1.0.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-rest-pipeline@1.25.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-tracing@1.4.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-util@1.14.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/identity@4.13.2',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/logger@1.4.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@typespec/ts-http-runtime@0.3.8',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn deprecated whatwg-encoding@3.1.1: Use @exodus/bytes instead for a more spec-conformant and faster implementation
npm warn deprecated inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
npm warn deprecated glob@7.2.3: Old versions of glob are not supported, and contain widely publicized security vulnerabilities, which have been fixed in the current version. Please update. Support for old versions may be purchased (at exorbitant rates) by contacting i@izs.me
npm warn deprecated prebuild-install@7.1.3: No longer maintained. Please contact the author of the relevant native addon; alternatives are available.

added 192 packages, and audited 193 packages in 4s

50 packages are looking for funding
  run `npm fund` for details

5 vulnerabilities (3 moderate, 2 high)

To address issues that do not require attention, run:
  npm audit fix

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
  [VSCODE] Bundling extension with esbuild...
  [EXEC] npm run bundle

> pengus@0.10.0 bundle
> esbuild ./src/extension.ts --bundle --outfile=out/extension.js --external:vscode --format=cjs --platform=node


  out/extension.js  771.2kb

⚡ Done in 46ms
  [VSCODE] Generating .vsix package with vsce...
  [EXEC] npx -y @vscode/vsce package
Executing prepublish script 'npm run vscode:prepublish'...

> pengus@0.10.0 vscode:prepublish
> npm run bundle


> pengus@0.10.0 bundle
> esbuild ./src/extension.ts --bundle --outfile=out/extension.js --external:vscode --format=cjs --platform=node


  out/extension.js  771.2kb

⚡ Done in 44ms
Warning: This extension consists of 326 files, out of which 166 are JavaScript files. For performance reasons, you should bundle your extension: https://aka.ms/vscode-bundle-extension. You should also exclude unnecessary files by adding them to your .vscodeignore: https://aka.ms/vscode-vscodeignore.

Files included in the VSIX:
pengus-0.10.0.vsix
├─ [Content_Types].xml 
├─ extension.vsixmanifest 
└─ extension/
   ├─ LICENSE.txt 
   ├─ README.md [3.86 KB]
   ├─ language-configuration.json [0.82 KB]
   ├─ package.json [8.33 KB]
   ├─ icons/
   │  ├─ pengu_icon.png [3 MB]
   │  └─ pengu_icon_white.png [27.75 KB]
   ├─ node_modules/
   │  ├─ balanced-match/ (5 files) [6.78 KB]
   │  ├─ brace-expansion/ (5 files) [16.5 KB]
   │  ├─ minimatch/ (6 files) [41.37 KB]
   │  ├─ semver/ (53 files) [98.7 KB]
   │  ├─ vscode-jsonrpc/ (48 files) [203.49 KB]
   │  ├─ vscode-languageclient/ (121 files) [637.35 KB]
   │  ├─ vscode-languageserver-protocol/ (68 files) [356.78 KB]
   │  └─ vscode-languageserver-types/ (9 files) [367.87 KB]
   ├─ out/
   │  └─ extension.js [771.15 KB]
   ├─ snippets/
   │  └─ pengus.json [31.29 KB]
   └─ syntaxes/
      └─ pengus.tmLanguage.json [6.6 KB]

=> Run vsce ls --tree to see all included files.

Packaged: /home/runner/work/PenguScript/PenguScript/vscode-extension/pengus-0.10.0.vsix (326 files, 3.57 MB)
  [VSCODE] Copied pengus-0.10.0.vsix -> /home/runner/work/PenguScript/PenguScript/pengucc_build/pengus-0.10.0.vsix

[6/7] Packaging standalone CLI executable with PyInstaller...
  [EXEC] /home/runner/work/PenguScript/PenguScript/.venv/bin/python -m PyInstaller --clean --name pengu --onefile --console --distpath /home/runner/work/PenguScript/PenguScript/pengucc_build --workpath /home/runner/work/PenguScript/PenguScript/build/pyinstaller_work --specpath /home/runner/work/PenguScript/PenguScript/build --noconfirm --add-data /home/runner/work/PenguScript/PenguScript/std:std --add-data /home/runner/work/PenguScript/PenguScript/pengu_runtime.h:. --add-data /home/runner/work/PenguScript/PenguScript/VERSION:. --add-data /home/runner/work/PenguScript/PenguScript/c_bind_stubs:c_bind_stubs --hidden-import pygls --hidden-import pygls.lsp --hidden-import pygls.lsp.server --hidden-import pygls.protocol --hidden-import pygls.capabilities --hidden-import lsprotocol --hidden-import lsprotocol.types --hidden-import lsprotocol.converters --hidden-import cattrs --hidden-import attrs --hidden-import pycparser --hidden-import pycparser.c_parser --hidden-import pycparser.c_lexer --hidden-import pycparser.c_ast --hidden-import pycparser.plyparser --hidden-import pycparser.ast_transforms --hidden-import lark --hidden-import lark.parsers --hidden-import lark.parsers.lalr_parser --hidden-import pengu_bind --hidden-import pengu_lsp --hidden-import pengu_lsp.server --hidden-import pengu_lsp.completions --hidden-import pengu_lsp.hover --hidden-import pengu_lsp.code_actions --hidden-import pengu_lsp.formatting --hidden-import pengu_parser --hidden-import pengu_parser.pengu_parser --hidden-import pengu_parser.pengu_checker --hidden-import pengu_parser.pengu_codegen --hidden-import pengu_parser.pengu_symbols --hidden-import pengu_parser.pengu_types --hidden-import pengu_parser.pengu_errors --hidden-import pengu_parser.pengu_infer --hidden-import pengu_parser.pengu_grammar --collect-submodules lsprotocol --collect-submodules pygls --collect-submodules cattrs --collect-submodules attrs /home/runner/work/PenguScript/PenguScript/pengu_project.py
107 INFO: PyInstaller: 6.22.2, contrib hooks: 2026.7
107 INFO: Python: 3.14.7
108 INFO: Platform: Linux-6.17.0-1022-azure-x86_64-with-glibc2.39
108 INFO: Python environment: /home/runner/work/PenguScript/PenguScript/.venv
109 INFO: wrote /home/runner/work/PenguScript/PenguScript/build/pengu.spec
219 INFO: UPX is available but is disabled on non-Windows due to known compatibility problems.
219 INFO: Removing temporary files and cleaning cache in /home/runner/.cache/pyinstaller
1276 INFO: Module search paths (PYTHONPATH):
['/home/runner/work/PenguScript/PenguScript',
 '/opt/hostedtoolcache/Python/3.14.7/x64/lib/python314.zip',
 '/opt/hostedtoolcache/Python/3.14.7/x64/lib/python3.14',
 '/opt/hostedtoolcache/Python/3.14.7/x64/lib/python3.14/lib-dynload',
 '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages',
 '/home/runner/work/PenguScript/PenguScript']
1437 INFO: Appending 'datas' from .spec
1439 INFO: checking Analysis
1439 INFO: Building Analysis because Analysis-00.toc is non existent
1439 INFO: Looking for Python shared library...
1448 INFO: Using Python shared library: /opt/hostedtoolcache/Python/3.14.7/x64/lib/libpython3.14.so.1.0
1448 INFO: Running Analysis Analysis-00.toc
1448 INFO: Target bytecode optimization level: 0
1448 INFO: Initializing module dependency graph...
1449 INFO: Initializing module graph hook caches...
1457 INFO: Analyzing modules for base_library.zip ...
2211 INFO: Processing standard module hook 'hook-math.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
2261 INFO: Processing standard module hook 'hook-heapq.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
3225 INFO: Processing standard module hook 'hook-encodings.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
3603 INFO: Processing standard module hook 'hook-pickle.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
4073 INFO: Processing standard module hook 'hook-difflib.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
8352 INFO: Caching module dependency graph...
8393 INFO: Analyzing /home/runner/work/PenguScript/PenguScript/pengu_project.py
8580 INFO: Processing pre-safe-import-module hook 'hook-tomli.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
8581 INFO: SetuptoolsInfo: initializing cached setuptools info...
8902 INFO: Setuptools: 'tomli' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.tomli'!
8911 INFO: Processing standard module hook 'hook-setuptools.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
8978 INFO: Processing standard module hook 'hook-platform.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9036 INFO: Processing standard module hook 'hook-sysconfig.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9042 INFO: Processing standard module hook 'hook-_ctypes.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9053 INFO: Processing pre-safe-import-module hook 'hook-distutils.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9091 INFO: Processing pre-safe-import-module hook 'hook-jaraco.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9091 INFO: Setuptools: 'jaraco' appears to be a full setuptools-vendored copy - creating alias to 'setuptools._vendor.jaraco'!
9106 INFO: Processing pre-safe-import-module hook 'hook-more_itertools.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9106 INFO: Setuptools: 'more_itertools' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.more_itertools'!
9345 INFO: Processing standard module hook 'hook-_osx_support.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9350 INFO: Processing pre-safe-import-module hook 'hook-typing_extensions.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
9722 INFO: Processing standard module hook 'hook-multiprocessing.util.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
9880 INFO: Processing standard module hook 'hook-xml.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
10797 INFO: Processing pre-safe-import-module hook 'hook-packaging.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
11196 INFO: Processing standard module hook 'hook-setuptools._vendor.jaraco.text.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
11197 INFO: Processing pre-safe-import-module hook 'hook-importlib_resources.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
11208 INFO: Processing pre-safe-import-module hook 'hook-backports.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
11208 INFO: Setuptools: 'backports' appears to be a full setuptools-vendored copy - creating alias to 'setuptools._vendor.backports'!
12684 INFO: Processing pre-safe-import-module hook 'hook-wheel.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/pre_safe_import_module'
12684 INFO: Setuptools: 'wheel' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.wheel'!
13049 INFO: Processing standard module hook 'hook-lark.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/lark/__pyinstaller'
14614 INFO: Processing standard module hook 'hook-pycparser.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/_pyinstaller_hooks_contrib/stdhooks'
16650 INFO: Analyzing hidden import 'pycparser.plyparser'
16650 ERROR: Hidden import 'pycparser.plyparser' not found
16651 INFO: Analyzing hidden import 'pygls.cli'
16653 INFO: Analyzing hidden import 'pygls.client'
16662 INFO: Analyzing hidden import 'pygls.lsp._base_client'
16729 INFO: Analyzing hidden import 'pygls.lsp.client'
16730 INFO: Analyzing hidden import 'cattrs.preconf'
16735 INFO: Analyzing hidden import 'cattrs.preconf.bson'
16770 INFO: Analyzing hidden import 'cattrs.preconf.cbor2'
16774 INFO: Analyzing hidden import 'cattrs.preconf.json'
16779 INFO: Analyzing hidden import 'cattrs.preconf.msgpack'
16784 INFO: Analyzing hidden import 'cattrs.preconf.msgspec'
16797 INFO: Analyzing hidden import 'cattrs.preconf.orjson'
16803 INFO: Analyzing hidden import 'cattrs.preconf.pyyaml'
16807 INFO: Analyzing hidden import 'cattrs.preconf.tomlkit'
16813 INFO: Analyzing hidden import 'cattrs.preconf.tomllib'
16820 INFO: Analyzing hidden import 'cattrs.preconf.ujson'
16825 INFO: Processing module hooks (post-graph stage)...
16825 WARNING: Hidden import "pycparser.lextab" not found!
16826 WARNING: Hidden import "pycparser.yacctab" not found!
17366 INFO: Processing standard module hook 'hook-webbrowser.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks'
17974 INFO: Performing binary vs. data reclassification (80 entries)
18099 INFO: Looking for ctypes DLLs
18146 INFO: Analyzing run-time hooks ...
18149 INFO: Including run-time hook 'pyi_rth_inspect.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
18152 INFO: Including run-time hook 'pyi_rth_pkgutil.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
18154 INFO: Including run-time hook 'pyi_rth_multiprocessing.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
18157 INFO: Including run-time hook 'pyi_rth_setuptools.py' from '/home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/hooks/rthooks'
18167 INFO: Creating base_library.zip...
18185 INFO: Looking for dynamic libraries
18949 INFO: Warnings written to /home/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/warn-pengu.txt
18978 INFO: Graph cross-reference written to /home/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/xref-pengu.html
19000 INFO: checking PYZ
19000 INFO: Building PYZ because PYZ-00.toc is non existent
19000 INFO: Building PYZ (ZlibArchive) /home/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/PYZ-00.pyz
19552 INFO: Building PYZ (ZlibArchive) /home/runner/work/PenguScript/PenguScript/build/pyinstaller_work/pengu/PYZ-00.pyz completed successfully.
19570 INFO: checking PKG
19570 INFO: Building PKG because PKG-00.toc is non existent
19570 INFO: Building PKG (CArchive) pengu.pkg
31705 INFO: Building PKG (CArchive) pengu.pkg completed successfully.
31708 INFO: Bootloader /home/runner/work/PenguScript/PenguScript/.venv/lib/python3.14/site-packages/PyInstaller/bootloader/Linux-64bit-intel/run
31708 INFO: checking EXE
31708 INFO: Building EXE because EXE-00.toc is non existent
31708 INFO: Building EXE from EXE-00.toc
31709 INFO: Copying bootloader EXE to /home/runner/work/PenguScript/PenguScript/pengucc_build/pengu
31709 INFO: Appending PKG archive to custom ELF section in EXE
31800 INFO: Building EXE from EXE-00.toc completed successfully.
31803 INFO: Build complete! The results are available in: /home/runner/work/PenguScript/PenguScript/pengucc_build
  [DOCS] Generated README_RELEASE.md and /home/runner/work/PenguScript/PenguScript/pengucc_build/README.md

[7/7] Running release verification & smoke tests...
  [TEST 1] Verifying pengu --help...
  [EXEC] /home/runner/work/PenguScript/PenguScript/pengucc_build/pengu --help
usage: pengu [-h] [-V]
             {init,add,build,run,test,check,update,bind,fmt,clean,lsp,doc} ...

PenguScript v0.10.0 Package & Build Manager

positional arguments:
  {init,add,build,run,test,check,update,bind,fmt,clean,lsp,doc}
                        Available subcommands
    init                Create a new PenguScript project template
    add                 Add an external dependency or binding to the project
    build               Compile the project according to configuration
    run                 Build and execute the project target, or run a
                        standalone .pengu script
    test                Compile and run the project's integrated unit tests
    check               Parse and type-check every module without generating
                        code (CI)
    update              Update dependencies: git pull + re-run build scripts
    bind                Generate a .d.pengu binding from a C header
    fmt                 Format .pengu files or directories (standard style)
    clean               Remove build directory and generated artifacts
    lsp                 Launch the PenguScript Language Server Protocol (LSP)
    doc                 Generate Markdown documentation from ## comments

options:
  -h, --help            show this help message and exit
  -V, --version         Print the PenguScript toolchain version and exit

Examples: pengu init my_game --type exe pengu add https://github.com/webui-
dev/webui pengu add ../local_binding -n my_binding pengu build --profile
release pengu build --cc clang --verbose pengu check # parse + type-check
without codegen (CI) pengu fmt src/ tests/ # format files/directories pengu
fmt --check src/ # verify formatting (exit 1 if changes) pengu run --profile
debug pengu run hello.pengu # run a standalone script (when main: enabled)
pengu update # git pull + rebuild every dependency pengu bind webui.h --prefix
webui_ --links webui-2-static ole32 stdc++ uuid pengu clean

  [TEST 2] Testing project initialization...
  [EXEC] /home/runner/work/PenguScript/PenguScript/pengucc_build/pengu init smoke_proj --type exe --links pengu_runtime
     Created exe project 'smoke_proj' at /home/runner/work/PenguScript/PenguScript/scratch/smoke_release_test/smoke_proj
  [TEST 3] Testing standalone compilation and execution ('pengu run')...
  [EXEC] /home/runner/work/PenguScript/PenguScript/pengucc_build/pengu run

[ERROR] Command failed with exit code 1: /home/runner/work/PenguScript/PenguScript/pengucc_build/pengu run
Stderr: Traceback (most recent call last):
  File "pengu_project.py", line 2301, in <module>
  File "pengu_project.py", line 2199, in main
  File "pengu_project.py", line 1874, in run_project
  File "pengu_project.py", line 1257, in build_project
  File "pengu_project.py", line 1173, in compile
  File "pengu_project.py", line 892, in bundle
  File "pengu_parser/pengu_checker.py", line 196, in check
  File "pengu_parser/pengu_checker.py", line 1717, in _check_node
  File "pengu_parser/pengu_infer.py", line 2368, in infer
  File "pengu_parser/pengu_infer.py", line 511, in _reject_list_glued_operator
pengu_parser.pengu_errors.TypeMismatchError: [line 6, col 5] Ambiguous 'and' after a call with arguments
[PYI-8222:ERROR] Failed to execute script 'pengu_project' due to unhandled exception!

Stdout:    Compiling smoke_proj v0.1.0 (exe) [debug]

Error: Process completed with exit code 1.

error de window:
Run python make_release.py
================================================================
  PenguScript Automated Release & PyInstaller Packaging Script
================================================================

[1/7] Verifying virtual environment (.venv)...
  [VENV] Creating .venv virtual environment...
  [EXEC] C:\hostedtoolcache\windows\Python\3.14.7\x64\python.exe -m venv D:\a\PenguScript\PenguScript\.venv
  [PYTHON] Using D:\a\PenguScript\PenguScript\.venv\Scripts\python.exe

[2/7] Installing / verifying build dependencies (PyInstaller, Lark, PyYAML)...
  [PIP] Checking / installing required packages...
  [EXEC] D:\a\PenguScript\PenguScript\.venv\Scripts\python.exe -m pip install --upgrade pyinstaller>=6.0 lark>=1.1.0 pyyaml>=6.0 pygls>=2.0.0 lsprotocol>=2023.0.0 pycparser>=2.21 pytest>=7.0.0
Collecting pyinstaller>=6.0
  Using cached pyinstaller-6.22.2-py3-none-win_amd64.whl.metadata (8.5 kB)
Collecting lark>=1.1.0
  Using cached lark-1.3.1-py3-none-any.whl.metadata (1.8 kB)
Collecting pyyaml>=6.0
  Using cached pyyaml-6.0.3-cp314-cp314-win_amd64.whl.metadata (2.4 kB)
Collecting pygls>=2.0.0
  Using cached pygls-2.1.1-py3-none-any.whl.metadata (4.5 kB)
Collecting lsprotocol>=2023.0.0
  Using cached lsprotocol-2025.0.0-py3-none-any.whl.metadata (2.2 kB)
Collecting pycparser>=2.21
  Using cached pycparser-3.0-py3-none-any.whl.metadata (8.2 kB)
Collecting pytest>=7.0.0
  Using cached pytest-9.1.1-py3-none-any.whl.metadata (7.6 kB)
Collecting altgraph (from pyinstaller>=6.0)
  Using cached altgraph-0.17.5-py2.py3-none-any.whl.metadata (7.5 kB)
Collecting packaging>=22.0 (from pyinstaller>=6.0)
  Using cached packaging-26.3-py3-none-any.whl.metadata (3.5 kB)
Collecting pefile>=2022.5.30 (from pyinstaller>=6.0)
  Using cached pefile-2024.8.26-py3-none-any.whl.metadata (1.4 kB)
Collecting pyinstaller-hooks-contrib>=2026.6 (from pyinstaller>=6.0)
  Using cached pyinstaller_hooks_contrib-2026.7-py3-none-any.whl.metadata (16 kB)
Collecting pywin32-ctypes>=0.2.1 (from pyinstaller>=6.0)
  Using cached pywin32_ctypes-0.2.3-py3-none-any.whl.metadata (3.9 kB)
Collecting setuptools>=42.0.0 (from pyinstaller>=6.0)
  Using cached setuptools-84.0.0-py3-none-any.whl.metadata (6.6 kB)
Collecting attrs>=24.3.0 (from pygls>=2.0.0)
  Using cached attrs-26.1.0-py3-none-any.whl.metadata (8.8 kB)
Collecting cattrs>=23.1.2 (from pygls>=2.0.0)
  Using cached cattrs-26.2.0-py3-none-any.whl.metadata (8.5 kB)
Collecting colorama>=0.4 (from pytest>=7.0.0)
  Using cached colorama-0.4.6-py2.py3-none-any.whl.metadata (17 kB)
Collecting iniconfig>=1.0.1 (from pytest>=7.0.0)
  Using cached iniconfig-2.3.0-py3-none-any.whl.metadata (2.5 kB)
Collecting pluggy<2,>=1.5 (from pytest>=7.0.0)
  Using cached pluggy-1.6.0-py3-none-any.whl.metadata (4.8 kB)
Collecting pygments>=2.7.2 (from pytest>=7.0.0)
  Using cached pygments-2.21.0-py3-none-any.whl.metadata (2.5 kB)
Collecting typing-extensions>=4.14.0 (from cattrs>=23.1.2->pygls>=2.0.0)
  Using cached typing_extensions-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Using cached pyinstaller-6.22.2-py3-none-win_amd64.whl (1.4 MB)
Using cached lark-1.3.1-py3-none-any.whl (113 kB)
Using cached pyyaml-6.0.3-cp314-cp314-win_amd64.whl (156 kB)
Using cached pygls-2.1.1-py3-none-any.whl (68 kB)
Using cached lsprotocol-2025.0.0-py3-none-any.whl (76 kB)
Using cached pycparser-3.0-py3-none-any.whl (48 kB)
Using cached pytest-9.1.1-py3-none-any.whl (386 kB)
Using cached pluggy-1.6.0-py3-none-any.whl (20 kB)
Using cached attrs-26.1.0-py3-none-any.whl (67 kB)
Using cached cattrs-26.2.0-py3-none-any.whl (74 kB)
Using cached colorama-0.4.6-py2.py3-none-any.whl (25 kB)
Using cached iniconfig-2.3.0-py3-none-any.whl (7.5 kB)
Using cached packaging-26.3-py3-none-any.whl (129 kB)
Using cached pefile-2024.8.26-py3-none-any.whl (74 kB)
Using cached pygments-2.21.0-py3-none-any.whl (1.3 MB)
Using cached pyinstaller_hooks_contrib-2026.7-py3-none-any.whl (459 kB)
Using cached pywin32_ctypes-0.2.3-py3-none-any.whl (30 kB)
Using cached setuptools-84.0.0-py3-none-any.whl (818 kB)
Using cached typing_extensions-4.16.0-py3-none-any.whl (45 kB)
Using cached altgraph-0.17.5-py2.py3-none-any.whl (21 kB)
Installing collected packages: altgraph, typing-extensions, setuptools, pyyaml, pywin32-ctypes, pygments, pycparser, pluggy, pefile, packaging, lark, iniconfig, colorama, attrs, pytest, pyinstaller-hooks-contrib, cattrs, pyinstaller, lsprotocol, pygls

Successfully installed altgraph-0.17.5 attrs-26.1.0 cattrs-26.2.0 colorama-0.4.6 iniconfig-2.3.0 lark-1.3.1 lsprotocol-2025.0.0 packaging-26.3 pefile-2024.8.26 pluggy-1.6.0 pycparser-3.0 pygls-2.1.1 pygments-2.21.0 pyinstaller-6.22.2 pyinstaller-hooks-contrib-2026.7 pytest-9.1.1 pywin32-ctypes-0.2.3 pyyaml-6.0.3 setuptools-84.0.0 typing-extensions-4.16.0

[3/7] Compiling static runtime libraries (build_runtime.py)...
=== Checking external C libraries in: D:\a\PenguScript\PenguScript\extern ===
  [OK] curl already present at curl-8.21.0
  [OK] libmicrohttpd already present at libmicrohttpd-1.0.1
  [OK] libxml2 already present at libxml2-2.9.0
  [OK] mbedtls already present at mbedtls-4.2.0
  [OK] pcre2 already present at pcre2-10.47
  [OK] zlib already present at zlib-1.3.2
  [OK] raylib already present at raylib-6.0
  [OK] webui already present at webui-2.5.0-beta.3
  [OK] sqlite3 already present at sqlite-autoconf-3530400
  [OK] libuv already present at libuv-1.52.1
  [OK] xlsxio already present at xlsxio-0.2.36
  [OK] libcyaml already present at libcyaml-1.4.2
  [OK] tomlc17 already present at tomlc17-R260821
  [OK] libzip already present at libzip-1.11.3
  [OK] libexpat already present at expat-2.6.4
  [OK] libyaml already present at yaml-0.2.5
=== All external C libraries verified. ===

  [EXEC] D:\a\PenguScript\PenguScript\.venv\Scripts\python.exe D:\a\PenguScript\PenguScript\build_runtime.py --rebuild
=== Checking external C libraries in: D:\a\PenguScript\PenguScript\extern ===
  [OK] curl already present at curl-8.21.0
  [OK] libmicrohttpd already present at libmicrohttpd-1.0.1
  [OK] libxml2 already present at libxml2-2.9.0
  [OK] mbedtls already present at mbedtls-4.2.0
  [OK] pcre2 already present at pcre2-10.47
  [OK] zlib already present at zlib-1.3.2
  [OK] raylib already present at raylib-6.0
  [OK] webui already present at webui-2.5.0-beta.3
  [OK] sqlite3 already present at sqlite-autoconf-3530400
  [OK] libuv already present at libuv-1.52.1
  [OK] xlsxio already present at xlsxio-0.2.36
  [OK] libcyaml already present at libcyaml-1.4.2
  [OK] tomlc17 already present at tomlc17-R260821
  [OK] libzip already present at libzip-1.11.3
  [OK] libexpat already present at expat-2.6.4
  [OK] libyaml already present at yaml-0.2.5
=== All external C libraries verified. ===

=== Building PenguScript Runtime (CC: C:\mingw64\bin\gcc.EXE, AR: C:\mingw64\bin\ar.EXE) ===
[ZLIB] Compiling zlib-1.3.2...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\adler32.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\adler32.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\compress.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\compress.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\crc32.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\crc32.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\deflate.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\deflate.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\gzclose.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\gzclose.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\gzlib.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\gzlib.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\gzread.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\gzread.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\gzwrite.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\gzwrite.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\infback.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\infback.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\inffast.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\inffast.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\inflate.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\inflate.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\inftrees.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\inftrees.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\trees.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\trees.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\uncompr.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\uncompr.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\zlib-1.3.2 -c D:\a\PenguScript\PenguScript\extern\zlib-1.3.2\zutil.c -o D:\a\PenguScript\PenguScript\build\obj_zlib\zutil.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libz.a D:\a\PenguScript\PenguScript\build\obj_zlib\adler32.o D:\a\PenguScript\PenguScript\build\obj_zlib\compress.o D:\a\PenguScript\PenguScript\build\obj_zlib\crc32.o D:\a\PenguScript\PenguScript\build\obj_zlib\deflate.o D:\a\PenguScript\PenguScript\build\obj_zlib\gzclose.o D:\a\PenguScript\PenguScript\build\obj_zlib\gzlib.o D:\a\PenguScript\PenguScript\build\obj_zlib\gzread.o D:\a\PenguScript\PenguScript\build\obj_zlib\gzwrite.o D:\a\PenguScript\PenguScript\build\obj_zlib\infback.o D:\a\PenguScript\PenguScript\build\obj_zlib\inffast.o D:\a\PenguScript\PenguScript\build\obj_zlib\inflate.o D:\a\PenguScript\PenguScript\build\obj_zlib\inftrees.o D:\a\PenguScript\PenguScript\build\obj_zlib\trees.o D:\a\PenguScript\PenguScript\build\obj_zlib\uncompr.o D:\a\PenguScript\PenguScript\build\obj_zlib\zutil.o
[ZLIB] Created D:\a\PenguScript\PenguScript\build\lib\libz.a
[PCRE2] Compiling pcre2-10.47 (8-bit)...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_auto_possess.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_auto_possess.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_chkdint.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_chkdint.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_compile.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_compile.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_compile_cgroup.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_compile_cgroup.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_compile_class.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_compile_class.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_config.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_config.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_context.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_context.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_convert.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_convert.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_dfa_match.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_dfa_match.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_error.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_error.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_extuni.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_extuni.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_find_bracket.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_find_bracket.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_match.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_match.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_match_data.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_match_data.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_match_next.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_match_next.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_newline.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_newline.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_ord2utf.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_ord2utf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_pattern_info.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_pattern_info.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_script_run.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_script_run.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_serialize.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_serialize.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_string_utils.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_string_utils.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_study.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_study.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_substitute.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_substitute.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_substring.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_substring.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_tables.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_tables.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_ucd.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_ucd.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_valid_utf.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_valid_utf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_xclass.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_xclass.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -DPCRE2_CODE_UNIT_WIDTH=8 -DPCRE2_STATIC -DSUPPORT_UNICODE -ID:\a\PenguScript\PenguScript\extern\pcre2-10.47\src -c D:\a\PenguScript\PenguScript\extern\pcre2-10.47\src\pcre2_chartables.c -o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_chartables.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libpcre2-8.a D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_auto_possess.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_chkdint.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_compile.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_compile_cgroup.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_compile_class.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_config.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_context.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_convert.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_dfa_match.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_error.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_extuni.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_find_bracket.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_match.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_match_data.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_match_next.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_newline.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_ord2utf.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_pattern_info.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_script_run.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_serialize.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_string_utils.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_study.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_substitute.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_substring.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_tables.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_ucd.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_valid_utf.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_xclass.o D:\a\PenguScript\PenguScript\build\obj_pcre2\pcre2_chartables.o
[PCRE2] Created D:\a\PenguScript\PenguScript\build\lib\libpcre2-8.a
[LIBXML2] Compiling libxml2-2.9.0...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\SAX.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\SAX.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\SAX2.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\SAX2.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\DOCBparser.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\DOCBparser.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\HTMLparser.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\HTMLparser.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\HTMLtree.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\HTMLtree.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\buf.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\buf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\c14n.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\c14n.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\catalog.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\catalog.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\chvalid.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\chvalid.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\debugXML.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\debugXML.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\dict.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\dict.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\encoding.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\encoding.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\entities.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\entities.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\error.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\error.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\globals.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\globals.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\hash.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\hash.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\legacy.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\legacy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\list.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\list.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\nanoftp.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\nanoftp.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\nanohttp.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\nanohttp.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\parser.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\parser.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\parserInternals.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\parserInternals.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\pattern.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\pattern.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\relaxng.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\relaxng.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\schematron.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\schematron.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\threads.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\threads.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\tree.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\tree.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\uri.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\uri.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\valid.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\valid.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xinclude.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xinclude.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xlink.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xlink.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlIO.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlIO.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlmemory.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlmemory.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlmodule.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlmodule.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlreader.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlreader.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlregexp.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlregexp.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlsave.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlsave.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlschemas.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlschemas.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlschemastypes.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlschemastypes.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlstring.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlstring.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlunicode.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlunicode.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xmlwriter.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlwriter.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xpath.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xpath.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xpointer.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xpointer.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DLIBXML_STATIC -DWITHOUT_TRIO -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -Wno-int-conversion -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0 -ID:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libxml2-2.9.0\xzlib.c -o D:\a\PenguScript\PenguScript\build\obj_libxml2\xzlib.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libxml2.a D:\a\PenguScript\PenguScript\build\obj_libxml2\SAX.o D:\a\PenguScript\PenguScript\build\obj_libxml2\SAX2.o D:\a\PenguScript\PenguScript\build\obj_libxml2\DOCBparser.o D:\a\PenguScript\PenguScript\build\obj_libxml2\HTMLparser.o D:\a\PenguScript\PenguScript\build\obj_libxml2\HTMLtree.o D:\a\PenguScript\PenguScript\build\obj_libxml2\buf.o D:\a\PenguScript\PenguScript\build\obj_libxml2\c14n.o D:\a\PenguScript\PenguScript\build\obj_libxml2\catalog.o D:\a\PenguScript\PenguScript\build\obj_libxml2\chvalid.o D:\a\PenguScript\PenguScript\build\obj_libxml2\debugXML.o D:\a\PenguScript\PenguScript\build\obj_libxml2\dict.o D:\a\PenguScript\PenguScript\build\obj_libxml2\encoding.o D:\a\PenguScript\PenguScript\build\obj_libxml2\entities.o D:\a\PenguScript\PenguScript\build\obj_libxml2\error.o D:\a\PenguScript\PenguScript\build\obj_libxml2\globals.o D:\a\PenguScript\PenguScript\build\obj_libxml2\hash.o D:\a\PenguScript\PenguScript\build\obj_libxml2\legacy.o D:\a\PenguScript\PenguScript\build\obj_libxml2\list.o D:\a\PenguScript\PenguScript\build\obj_libxml2\nanoftp.o D:\a\PenguScript\PenguScript\build\obj_libxml2\nanohttp.o D:\a\PenguScript\PenguScript\build\obj_libxml2\parser.o D:\a\PenguScript\PenguScript\build\obj_libxml2\parserInternals.o D:\a\PenguScript\PenguScript\build\obj_libxml2\pattern.o D:\a\PenguScript\PenguScript\build\obj_libxml2\relaxng.o D:\a\PenguScript\PenguScript\build\obj_libxml2\schematron.o D:\a\PenguScript\PenguScript\build\obj_libxml2\threads.o D:\a\PenguScript\PenguScript\build\obj_libxml2\tree.o D:\a\PenguScript\PenguScript\build\obj_libxml2\uri.o D:\a\PenguScript\PenguScript\build\obj_libxml2\valid.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xinclude.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xlink.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlIO.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlmemory.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlmodule.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlreader.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlregexp.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlsave.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlschemas.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlschemastypes.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlstring.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlunicode.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xmlwriter.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xpath.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xpointer.o D:\a\PenguScript\PenguScript\build\obj_libxml2\xzlib.o
[LIBXML2] Created D:\a\PenguScript\PenguScript\build\lib\libxml2.a
[MBEDTLS] Compiling mbedtls-4.2.0 crypto...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\core -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform -c D:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\src\md5.c -o D:\a\PenguScript\PenguScript\build\obj_mbedtls\md5.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\core -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform -c D:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\src\sha1.c -o D:\a\PenguScript\PenguScript\build\obj_mbedtls\sha1.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\core -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform -c D:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\src\sha256.c -o D:\a\PenguScript\PenguScript\build\obj_mbedtls\sha256.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\core -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform -c D:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\src\sha512.c -o D:\a\PenguScript\PenguScript\build\obj_mbedtls\sha512.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\core -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform -c D:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform\platform_util.c -o D:\a\PenguScript\PenguScript\build\obj_mbedtls\platform_util.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMBEDTLS_MD5_C -DMBEDTLS_SHA1_C -DMBEDTLS_SHA256_C -DMBEDTLS_SHA512_C -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\drivers\builtin\include -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\core -ID:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform -c D:\a\PenguScript\PenguScript\extern\mbedtls-4.2.0\tf-psa-crypto\platform\platform.c -o D:\a\PenguScript\PenguScript\build\obj_mbedtls\platform.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libmbedcrypto.a D:\a\PenguScript\PenguScript\build\obj_mbedtls\md5.o D:\a\PenguScript\PenguScript\build\obj_mbedtls\sha1.o D:\a\PenguScript\PenguScript\build\obj_mbedtls\sha256.o D:\a\PenguScript\PenguScript\build\obj_mbedtls\sha512.o D:\a\PenguScript\PenguScript\build\obj_mbedtls\platform_util.o D:\a\PenguScript\PenguScript\build\obj_mbedtls\platform.o
[MBEDTLS] Created D:\a\PenguScript\PenguScript\build\lib\libmbedcrypto.a
[CURL] Compiling curl-8.21.0...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\altsvc.c -o D:\a\PenguScript\PenguScript\build\obj_curl\altsvc.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\asyn-base.c -o D:\a\PenguScript\PenguScript\build\obj_curl\asyn-base.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\asyn-thrdd.c -o D:\a\PenguScript\PenguScript\build\obj_curl\asyn-thrdd.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\bufq.c -o D:\a\PenguScript\PenguScript\build\obj_curl\bufq.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\bufref.c -o D:\a\PenguScript\PenguScript\build\obj_curl\bufref.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-dns.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-dns.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-h1-proxy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-h1-proxy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-haproxy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-haproxy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-https-connect.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-https-connect.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-ip-happy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-ip-happy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-recvbuf.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-recvbuf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-setup.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-setup.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cf-socket.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cf-socket.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cfilters.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cfilters.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\conncache.c -o D:\a\PenguScript\PenguScript\build\obj_curl\conncache.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\connect.c -o D:\a\PenguScript\PenguScript\build\obj_curl\connect.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\content_encoding.c -o D:\a\PenguScript\PenguScript\build\obj_curl\content_encoding.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cookie.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cookie.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\creds.c -o D:\a\PenguScript\PenguScript\build\obj_curl\creds.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cshutdn.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cshutdn.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_addrinfo.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_addrinfo.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_endian.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_endian.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_fnmatch.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_fnmatch.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_fopen.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_fopen.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_get_line.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_get_line.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_gethostname.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_gethostname.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_memrchr.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_memrchr.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_range.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_range.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_sasl.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_sasl.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_sha512_256.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_sha512_256.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_share.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_share.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_threads.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_threads.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curl_trc.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curl_trc.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cw-out.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cw-out.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\cw-pause.c -o D:\a\PenguScript\PenguScript\build\obj_curl\cw-pause.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\dnscache.c -o D:\a\PenguScript\PenguScript\build\obj_curl\dnscache.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\doh.c -o D:\a\PenguScript\PenguScript\build\obj_curl\doh.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\dynhds.c -o D:\a\PenguScript\PenguScript\build\obj_curl\dynhds.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\easy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\easy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\easygetopt.c -o D:\a\PenguScript\PenguScript\build\obj_curl\easygetopt.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\easyoptions.c -o D:\a\PenguScript\PenguScript\build\obj_curl\easyoptions.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\escape.c -o D:\a\PenguScript\PenguScript\build\obj_curl\escape.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\fake_addrinfo.c -o D:\a\PenguScript\PenguScript\build\obj_curl\fake_addrinfo.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\file.c -o D:\a\PenguScript\PenguScript\build\obj_curl\file.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\fileinfo.c -o D:\a\PenguScript\PenguScript\build\obj_curl\fileinfo.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\formdata.c -o D:\a\PenguScript\PenguScript\build\obj_curl\formdata.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\getenv.c -o D:\a\PenguScript\PenguScript\build\obj_curl\getenv.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\getinfo.c -o D:\a\PenguScript\PenguScript\build\obj_curl\getinfo.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\hash.c -o D:\a\PenguScript\PenguScript\build\obj_curl\hash.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\headers.c -o D:\a\PenguScript\PenguScript\build\obj_curl\headers.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\hmac.c -o D:\a\PenguScript\PenguScript\build\obj_curl\hmac.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\hostip.c -o D:\a\PenguScript\PenguScript\build\obj_curl\hostip.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\hostip4.c -o D:\a\PenguScript\PenguScript\build\obj_curl\hostip4.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\hostip6.c -o D:\a\PenguScript\PenguScript\build\obj_curl\hostip6.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\hsts.c -o D:\a\PenguScript\PenguScript\build\obj_curl\hsts.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\http.c -o D:\a\PenguScript\PenguScript\build\obj_curl\http.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\http1.c -o D:\a\PenguScript\PenguScript\build\obj_curl\http1.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\http_aws_sigv4.c -o D:\a\PenguScript\PenguScript\build\obj_curl\http_aws_sigv4.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\http_chunks.c -o D:\a\PenguScript\PenguScript\build\obj_curl\http_chunks.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\http_digest.c -o D:\a\PenguScript\PenguScript\build\obj_curl\http_digest.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\http_proxy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\http_proxy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\httpsrr.c -o D:\a\PenguScript\PenguScript\build\obj_curl\httpsrr.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\idn.c -o D:\a\PenguScript\PenguScript\build\obj_curl\idn.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\if2ip.c -o D:\a\PenguScript\PenguScript\build\obj_curl\if2ip.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\llist.c -o D:\a\PenguScript\PenguScript\build\obj_curl\llist.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\md5.c -o D:\a\PenguScript\PenguScript\build\obj_curl\md5.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\memdebug.c -o D:\a\PenguScript\PenguScript\build\obj_curl\memdebug.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\mime.c -o D:\a\PenguScript\PenguScript\build\obj_curl\mime.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\mprintf.c -o D:\a\PenguScript\PenguScript\build\obj_curl\mprintf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\multi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\multi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\multi_ev.c -o D:\a\PenguScript\PenguScript\build\obj_curl\multi_ev.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\multi_ntfy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\multi_ntfy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\netrc.c -o D:\a\PenguScript\PenguScript\build\obj_curl\netrc.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\parsedate.c -o D:\a\PenguScript\PenguScript\build\obj_curl\parsedate.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\peer.c -o D:\a\PenguScript\PenguScript\build\obj_curl\peer.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\progress.c -o D:\a\PenguScript\PenguScript\build\obj_curl\progress.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\protocol.c -o D:\a\PenguScript\PenguScript\build\obj_curl\protocol.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\proxy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\proxy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\rand.c -o D:\a\PenguScript\PenguScript\build\obj_curl\rand.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\ratelimit.c -o D:\a\PenguScript\PenguScript\build\obj_curl\ratelimit.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\request.c -o D:\a\PenguScript\PenguScript\build\obj_curl\request.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\select.c -o D:\a\PenguScript\PenguScript\build\obj_curl\select.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\sendf.c -o D:\a\PenguScript\PenguScript\build\obj_curl\sendf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\setopt.c -o D:\a\PenguScript\PenguScript\build\obj_curl\setopt.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\sha256.c -o D:\a\PenguScript\PenguScript\build\obj_curl\sha256.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\slist.c -o D:\a\PenguScript\PenguScript\build\obj_curl\slist.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\socketpair.c -o D:\a\PenguScript\PenguScript\build\obj_curl\socketpair.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\socks.c -o D:\a\PenguScript\PenguScript\build\obj_curl\socks.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\splay.c -o D:\a\PenguScript\PenguScript\build\obj_curl\splay.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\strcase.c -o D:\a\PenguScript\PenguScript\build\obj_curl\strcase.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\strequal.c -o D:\a\PenguScript\PenguScript\build\obj_curl\strequal.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\strerror.c -o D:\a\PenguScript\PenguScript\build\obj_curl\strerror.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\system_win32.c -o D:\a\PenguScript\PenguScript\build\obj_curl\system_win32.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\thrdpool.c -o D:\a\PenguScript\PenguScript\build\obj_curl\thrdpool.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\thrdqueue.c -o D:\a\PenguScript\PenguScript\build\obj_curl\thrdqueue.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\transfer.c -o D:\a\PenguScript\PenguScript\build\obj_curl\transfer.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\uint-bset.c -o D:\a\PenguScript\PenguScript\build\obj_curl\uint-bset.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\uint-hash.c -o D:\a\PenguScript\PenguScript\build\obj_curl\uint-hash.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\uint-spbset.c -o D:\a\PenguScript\PenguScript\build\obj_curl\uint-spbset.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\uint-table.c -o D:\a\PenguScript\PenguScript\build\obj_curl\uint-table.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\url.c -o D:\a\PenguScript\PenguScript\build\obj_curl\url.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\urlapi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\urlapi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\version.c -o D:\a\PenguScript\PenguScript\build\obj_curl\version.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\ws.c -o D:\a\PenguScript\PenguScript\build\obj_curl\ws.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\base64.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_base64.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\basename.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_basename.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\dynbuf.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_dynbuf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\fopen.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_fopen.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\inet_ntop.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_inet_ntop.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\inet_pton.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_inet_pton.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\multibyte.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_multibyte.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\nonblock.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_nonblock.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\snprintf.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_snprintf.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\strcopy.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strcopy.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\strdup.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strdup.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\strerr.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strerr.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\strparse.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strparse.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\timediff.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_timediff.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\timeval.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_timeval.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\version_win32.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_version_win32.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\wait.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_wait.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\warnless.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_warnless.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\curlx\winapi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_winapi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\cleartext.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_cleartext.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\cram.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_cram.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\digest.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_digest.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\digest_sspi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_digest_sspi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\gsasl.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_gsasl.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\krb5_gssapi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_krb5_gssapi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\krb5_sspi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_krb5_sspi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\ntlm.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_ntlm.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\ntlm_sspi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_ntlm_sspi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\oauth2.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_oauth2.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\spnego_gssapi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_spnego_gssapi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\spnego_sspi.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_spnego_sspi.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vauth\vauth.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_vauth.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\cipher_suite.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_cipher_suite.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\hostcheck.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_hostcheck.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\keylog.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_keylog.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\schannel.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_schannel.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\schannel_verify.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_schannel_verify.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\vtls.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\vtls_config.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls_config.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\vtls_scache.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls_scache.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\vtls_spack.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls_spack.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vtls\x509asn1.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_x509asn1.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vquic\capsule.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_capsule.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vquic\cf-capsule.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_cf-capsule.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vquic\vquic-tls.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_vquic-tls.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DBUILDING_LIBCURL -DCURL_STATICLIB -DHTTP_ONLY -DUSE_WIN32_LARGE_FILES -DHAVE_CONFIG_H -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\include -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib -ID:\a\PenguScript\PenguScript\extern\curl-8.21.0 -c D:\a\PenguScript\PenguScript\extern\curl-8.21.0\lib\vquic\vquic.c -o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_vquic.o
[LIBUV] build not feasible on this toolchain, skipping: [CMakeFiles\uv_a.dir\build.make:589: CMakeFiles/uv_a.dir/src/win/util.c.obj] Error 1
mingw32-make.EXE[1]: *** [CMakeFiles\Makefile2:160: CMakeFiles/uv_a.dir/all] Error 2
mingw32-make.EXE: *** [Makefile:135: all] Error 2

  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libcurl.a D:\a\PenguScript\PenguScript\build\obj_curl\altsvc.o D:\a\PenguScript\PenguScript\build\obj_curl\asyn-base.o D:\a\PenguScript\PenguScript\build\obj_curl\asyn-thrdd.o D:\a\PenguScript\PenguScript\build\obj_curl\bufq.o D:\a\PenguScript\PenguScript\build\obj_curl\bufref.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-dns.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-h1-proxy.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-haproxy.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-https-connect.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-ip-happy.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-recvbuf.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-setup.o D:\a\PenguScript\PenguScript\build\obj_curl\cf-socket.o D:\a\PenguScript\PenguScript\build\obj_curl\cfilters.o D:\a\PenguScript\PenguScript\build\obj_curl\conncache.o D:\a\PenguScript\PenguScript\build\obj_curl\connect.o D:\a\PenguScript\PenguScript\build\obj_curl\content_encoding.o D:\a\PenguScript\PenguScript\build\obj_curl\cookie.o D:\a\PenguScript\PenguScript\build\obj_curl\creds.o D:\a\PenguScript\PenguScript\build\obj_curl\cshutdn.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_addrinfo.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_endian.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_fnmatch.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_fopen.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_get_line.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_gethostname.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_memrchr.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_range.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_sasl.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_sha512_256.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_share.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_threads.o D:\a\PenguScript\PenguScript\build\obj_curl\curl_trc.o D:\a\PenguScript\PenguScript\build\obj_curl\cw-out.o D:\a\PenguScript\PenguScript\build\obj_curl\cw-pause.o D:\a\PenguScript\PenguScript\build\obj_curl\dnscache.o D:\a\PenguScript\PenguScript\build\obj_curl\doh.o D:\a\PenguScript\PenguScript\build\obj_curl\dynhds.o D:\a\PenguScript\PenguScript\build\obj_curl\easy.o D:\a\PenguScript\PenguScript\build\obj_curl\easygetopt.o D:\a\PenguScript\PenguScript\build\obj_curl\easyoptions.o D:\a\PenguScript\PenguScript\build\obj_curl\escape.o D:\a\PenguScript\PenguScript\build\obj_curl\fake_addrinfo.o D:\a\PenguScript\PenguScript\build\obj_curl\file.o D:\a\PenguScript\PenguScript\build\obj_curl\fileinfo.o D:\a\PenguScript\PenguScript\build\obj_curl\formdata.o D:\a\PenguScript\PenguScript\build\obj_curl\getenv.o D:\a\PenguScript\PenguScript\build\obj_curl\getinfo.o D:\a\PenguScript\PenguScript\build\obj_curl\hash.o D:\a\PenguScript\PenguScript\build\obj_curl\headers.o D:\a\PenguScript\PenguScript\build\obj_curl\hmac.o D:\a\PenguScript\PenguScript\build\obj_curl\hostip.o D:\a\PenguScript\PenguScript\build\obj_curl\hostip4.o D:\a\PenguScript\PenguScript\build\obj_curl\hostip6.o D:\a\PenguScript\PenguScript\build\obj_curl\hsts.o D:\a\PenguScript\PenguScript\build\obj_curl\http.o D:\a\PenguScript\PenguScript\build\obj_curl\http1.o D:\a\PenguScript\PenguScript\build\obj_curl\http_aws_sigv4.o D:\a\PenguScript\PenguScript\build\obj_curl\http_chunks.o D:\a\PenguScript\PenguScript\build\obj_curl\http_digest.o D:\a\PenguScript\PenguScript\build\obj_curl\http_proxy.o D:\a\PenguScript\PenguScript\build\obj_curl\httpsrr.o D:\a\PenguScript\PenguScript\build\obj_curl\idn.o D:\a\PenguScript\PenguScript\build\obj_curl\if2ip.o D:\a\PenguScript\PenguScript\build\obj_curl\llist.o D:\a\PenguScript\PenguScript\build\obj_curl\md5.o D:\a\PenguScript\PenguScript\build\obj_curl\memdebug.o D:\a\PenguScript\PenguScript\build\obj_curl\mime.o D:\a\PenguScript\PenguScript\build\obj_curl\mprintf.o D:\a\PenguScript\PenguScript\build\obj_curl\multi.o D:\a\PenguScript\PenguScript\build\obj_curl\multi_ev.o D:\a\PenguScript\PenguScript\build\obj_curl\multi_ntfy.o D:\a\PenguScript\PenguScript\build\obj_curl\netrc.o D:\a\PenguScript\PenguScript\build\obj_curl\parsedate.o D:\a\PenguScript\PenguScript\build\obj_curl\peer.o D:\a\PenguScript\PenguScript\build\obj_curl\progress.o D:\a\PenguScript\PenguScript\build\obj_curl\protocol.o D:\a\PenguScript\PenguScript\build\obj_curl\proxy.o D:\a\PenguScript\PenguScript\build\obj_curl\rand.o D:\a\PenguScript\PenguScript\build\obj_curl\ratelimit.o D:\a\PenguScript\PenguScript\build\obj_curl\request.o D:\a\PenguScript\PenguScript\build\obj_curl\select.o D:\a\PenguScript\PenguScript\build\obj_curl\sendf.o D:\a\PenguScript\PenguScript\build\obj_curl\setopt.o D:\a\PenguScript\PenguScript\build\obj_curl\sha256.o D:\a\PenguScript\PenguScript\build\obj_curl\slist.o D:\a\PenguScript\PenguScript\build\obj_curl\socketpair.o D:\a\PenguScript\PenguScript\build\obj_curl\socks.o D:\a\PenguScript\PenguScript\build\obj_curl\splay.o D:\a\PenguScript\PenguScript\build\obj_curl\strcase.o D:\a\PenguScript\PenguScript\build\obj_curl\strequal.o D:\a\PenguScript\PenguScript\build\obj_curl\strerror.o D:\a\PenguScript\PenguScript\build\obj_curl\system_win32.o D:\a\PenguScript\PenguScript\build\obj_curl\thrdpool.o D:\a\PenguScript\PenguScript\build\obj_curl\thrdqueue.o D:\a\PenguScript\PenguScript\build\obj_curl\transfer.o D:\a\PenguScript\PenguScript\build\obj_curl\uint-bset.o D:\a\PenguScript\PenguScript\build\obj_curl\uint-hash.o D:\a\PenguScript\PenguScript\build\obj_curl\uint-spbset.o D:\a\PenguScript\PenguScript\build\obj_curl\uint-table.o D:\a\PenguScript\PenguScript\build\obj_curl\url.o D:\a\PenguScript\PenguScript\build\obj_curl\urlapi.o D:\a\PenguScript\PenguScript\build\obj_curl\version.o D:\a\PenguScript\PenguScript\build\obj_curl\ws.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_base64.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_basename.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_dynbuf.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_fopen.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_inet_ntop.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_inet_pton.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_multibyte.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_nonblock.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_snprintf.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strcopy.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strdup.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strerr.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_strparse.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_timediff.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_timeval.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_version_win32.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_wait.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_warnless.o D:\a\PenguScript\PenguScript\build\obj_curl\curlx_winapi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_cleartext.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_cram.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_digest.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_digest_sspi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_gsasl.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_krb5_gssapi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_krb5_sspi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_ntlm.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_ntlm_sspi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_oauth2.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_spnego_gssapi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_spnego_sspi.o D:\a\PenguScript\PenguScript\build\obj_curl\vauth_vauth.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_cipher_suite.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_hostcheck.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_keylog.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_schannel.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_schannel_verify.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls_config.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls_scache.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_vtls_spack.o D:\a\PenguScript\PenguScript\build\obj_curl\vtls_x509asn1.o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_capsule.o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_cf-capsule.o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_vquic-tls.o D:\a\PenguScript\PenguScript\build\obj_curl\vquic_vquic.o
[CURL] Created D:\a\PenguScript\PenguScript\build\lib\libcurl.a
[MICROHTTPD] Compiling libmicrohttpd-1.0.1...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\basicauth.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\basicauth.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\connection.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\connection.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\daemon.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\daemon.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\digestauth.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\digestauth.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\gen_auth.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\gen_auth.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\internal.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\internal.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\memorypool.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\memorypool.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_compat.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_compat.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_itc.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_itc.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_mono_clock.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_mono_clock.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_panic.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_panic.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_send.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_send.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_sockets.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_sockets.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_str.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_str.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\mhd_threads.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_threads.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\postprocessor.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\postprocessor.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\reason_phrase.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\reason_phrase.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\response.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\response.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\sha256.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\sha256.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\sysfdsetsize.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\sysfdsetsize.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DMHD_W32LIB -D_REENTRANT -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\include -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd -ID:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1 -c D:\a\PenguScript\PenguScript\extern\libmicrohttpd-1.0.1\src\microhttpd\tsearch.c -o D:\a\PenguScript\PenguScript\build\obj_microhttpd\tsearch.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libmicrohttpd.a D:\a\PenguScript\PenguScript\build\obj_microhttpd\basicauth.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\connection.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\daemon.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\digestauth.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\gen_auth.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\internal.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\memorypool.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_compat.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_itc.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_mono_clock.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_panic.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_send.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_sockets.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_str.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\mhd_threads.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\postprocessor.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\reason_phrase.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\response.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\sha256.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\sysfdsetsize.o D:\a\PenguScript\PenguScript\build\obj_microhttpd\tsearch.o
[MICROHTTPD] Created D:\a\PenguScript\PenguScript\build\lib\libmicrohttpd.a
[SQLITE3] Compiling SQLite3 amalgamation...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION -DSQLITE_ENABLE_FTS5 -Wno-unused-but-set-variable -ID:\a\PenguScript\PenguScript\extern\sqlite-autoconf-3530400 -c D:\a\PenguScript\PenguScript\extern\sqlite-autoconf-3530400\sqlite3.c -o D:\a\PenguScript\PenguScript\build\obj_sqlite3\sqlite3.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libsqlite3.a D:\a\PenguScript\PenguScript\build\obj_sqlite3\sqlite3.o
[SQLITE3] Created D:\a\PenguScript\PenguScript\build\lib\libsqlite3.a
[WEBUI] Installed D:\a\PenguScript\PenguScript\build\lib\libwebui.a
[RAYLIB] Compiling Raylib (desktop, OpenGL 3.3)...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\rcore.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\rcore.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\rshapes.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\rshapes.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\rtextures.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\rtextures.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\rtext.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\rtext.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\rmodels.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\rmodels.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\raudio.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\raudio.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DPLATFORM_DESKTOP -DGRAPHICS_API_OPENGL_33 -D_CRT_SECURE_NO_WARNINGS -fno-strict-aliasing -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glfw\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external\glad\include -ID:\a\PenguScript\PenguScript\extern\raylib-6.0\src\external -Wno-implicit-function-declaration -D_GLFW_WIN32 -c D:\a\PenguScript\PenguScript\extern\raylib-6.0\src\rglfw.c -o D:\a\PenguScript\PenguScript\build\obj_raylib\rglfw.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libraylib.a D:\a\PenguScript\PenguScript\build\obj_raylib\rcore.o D:\a\PenguScript\PenguScript\build\obj_raylib\rshapes.o D:\a\PenguScript\PenguScript\build\obj_raylib\rtextures.o D:\a\PenguScript\PenguScript\build\obj_raylib\rtext.o D:\a\PenguScript\PenguScript\build\obj_raylib\rmodels.o D:\a\PenguScript\PenguScript\build\obj_raylib\raudio.o D:\a\PenguScript\PenguScript\build\obj_raylib\rglfw.o
[RAYLIB] Created D:\a\PenguScript\PenguScript\build\lib\libraylib.a
[RAYMATH] Compiling raymath shim...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_raymath.c -o D:\a\PenguScript\PenguScript\build\obj_raymath\wrappers_raymath.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libpengu_raymath.a D:\a\PenguScript\PenguScript\build\obj_raymath\wrappers_raymath.o
[RAYMATH] Created D:\a\PenguScript\PenguScript\build\lib\libpengu_raymath.a
[LIBUV] Building libuv with CMake...
  [EXEC] cmake -S D:\a\PenguScript\PenguScript\extern\libuv-1.52.1 -B D:\a\PenguScript\PenguScript\build\libuv_cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DCMAKE_C_COMPILER=C:\mingw64\bin\gcc.EXE -G MinGW Makefiles -DCMAKE_MAKE_PROGRAM=C:\mingw64\bin\mingw32-make.EXE
  [EXEC] cmake --build D:\a\PenguScript\PenguScript\build\libuv_cmake --config Release -j 4
[ERROR] Command failed with exit code 2:
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c: In function 'uv_cpu_info':
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:630:31: error: passing argument 3 of 'uv__convert_utf16_to_utf8' from incompatible pointer type [-Wincompatible-pointer-types]
  630 |                               &(cpu_info->model));
      |                               ^~~~~~~~~~~~~~~~~~
      |                               |
      |                               const char **
In file included from D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:31:
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\internal.h:260:75: note: expected 'char **' but argument is of type 'const char **'
  260 | int uv__convert_utf16_to_utf8(const WCHAR* utf16, size_t utf16len, char** utf8);
      |                                                                    ~~~~~~~^~~~
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:580:12: warning: variable 'len' set but not used [-Wunused-but-set-variable]
  580 |     size_t len;
      |            ^~~
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:644:28: warning: passing argument 1 of 'uv__free' discards 'const' qualifier from pointer target type [-Wdiscarded-qualifiers]
  644 |       uv__free(cpu_infos[i].model);
      |                ~~~~~~~~~~~~^~~~~~
In file included from D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\internal.h:26:
D:/a/PenguScript/PenguScript/extern/libuv-1.52.1/src/uv-common.h:392:21: note: expected 'void *' but argument is of type 'const char *'
  392 | void uv__free(void* ptr);
      |               ~~~~~~^~~
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c: In function 'uv_cpu_info':
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:630:31: error: passing argument 3 of 'uv__convert_utf16_to_utf8' from incompatible pointer type [-Wincompatible-pointer-types]
  630 |                               &(cpu_info->model));
      |                               ^~~~~~~~~~~~~~~~~~
      |                               |
      |                               const char **
In file included from D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:31:
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\internal.h:260:75: note: expected 'char **' but argument is of type 'const char **'
  260 | int uv__convert_utf16_to_utf8(const WCHAR* utf16, size_t utf16len, char** utf8);
      |                                                                    ~~~~~~~^~~~
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:580:12: warning: variable 'len' set but not used [-Wunused-but-set-variable]
  580 |     size_t len;
      |            ^~~
D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\util.c:644:28: warning: passing argument 1 of 'uv__free' discards 'const' qualifier from pointer target type [-Wdiscarded-qualifiers]
  644 |       uv__free(cpu_infos[i].model);
      |                ~~~~~~~~~~~~^~~~~~
In file included from D:\a\PenguScript\PenguScript\extern\libuv-1.52.1\src\win\internal.h:26:
D:/a/PenguScript/PenguScript/extern/libuv-1.52.1/src/uv-common.h:392:21: note: expected 'void *' but argument is of type 'const char *'
  392 | void uv__free(void* ptr);
      |               ~~~~~~^~~
mingw32-make.EXE[2]: *** [CMakeFiles\uv.dir\build.make:589: CMakeFiles/uv.dir/src/win/util.c.obj] Error 1
mingw32-make.EXE[1]: *** [CMakeFiles\Makefile2:128: CMakeFiles/uv.dir/all] Error 2
mingw32-make.EXE[1]: *** Waiting for unfinished jobs....
mingw32-make.EXE[2]: *** [CMakeFiles\uv_a.dir\build.make:589: CMakeFiles/uv_a.dir/src/win/util.c.obj] Error 1
mingw32-make.EXE[1]: *** [CMakeFiles\Makefile2:160: CMakeFiles/uv_a.dir/all] Error 2
mingw32-make.EXE: *** [Makefile:135: all] Error 2

[LIBYAML] Compiling libyaml sources...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\api.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\api.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\dumper.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\dumper.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\emitter.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\emitter.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\loader.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\loader.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\parser.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\parser.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\reader.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\reader.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\scanner.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\scanner.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DHAVE_CONFIG_H -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\include -ID:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\yaml-0.2.5\src\writer.c -o D:\a\PenguScript\PenguScript\build\obj_yaml\writer.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libyaml.a D:\a\PenguScript\PenguScript\build\obj_yaml\api.o D:\a\PenguScript\PenguScript\build\obj_yaml\dumper.o D:\a\PenguScript\PenguScript\build\obj_yaml\emitter.o D:\a\PenguScript\PenguScript\build\obj_yaml\loader.o D:\a\PenguScript\PenguScript\build\obj_yaml\parser.o D:\a\PenguScript\PenguScript\build\obj_yaml\reader.o D:\a\PenguScript\PenguScript\build\obj_yaml\scanner.o D:\a\PenguScript\PenguScript\build\obj_yaml\writer.o
[LIBYAML] Created D:\a\PenguScript\PenguScript\build\lib\libyaml.a
[LIBCYAML] Compiling libcyaml sources...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\include -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src\free.c -o D:\a\PenguScript\PenguScript\build\obj_cyaml\free.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\include -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src\load.c -o D:\a\PenguScript\PenguScript\build\obj_cyaml\load.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\include -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src\mem.c -o D:\a\PenguScript\PenguScript\build\obj_cyaml\mem.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\include -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src\save.c -o D:\a\PenguScript\PenguScript\build\obj_cyaml\save.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\include -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src\utf8.c -o D:\a\PenguScript\PenguScript\build\obj_cyaml\utf8.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DVERSION_MAJOR=1 -DVERSION_MINOR=4 -DVERSION_PATCH=2 -DVERSION_DEVEL=0 -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\include -ID:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\libcyaml-1.4.2\src\util.c -o D:\a\PenguScript\PenguScript\build\obj_cyaml\util.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libcyaml.a D:\a\PenguScript\PenguScript\build\obj_cyaml\free.o D:\a\PenguScript\PenguScript\build\obj_cyaml\load.o D:\a\PenguScript\PenguScript\build\obj_cyaml\mem.o D:\a\PenguScript\PenguScript\build\obj_cyaml\save.o D:\a\PenguScript\PenguScript\build\obj_cyaml\utf8.o D:\a\PenguScript\PenguScript\build\obj_cyaml\util.o
[LIBCYAML] Created D:\a\PenguScript\PenguScript\build\lib\libcyaml.a
[LIBZIP] Building libzip-1.11.3 with CMake...
  [EXEC] cmake -S D:\a\PenguScript\PenguScript\extern\libzip-1.11.3 -B D:\a\PenguScript\PenguScript\build\libzip_cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=C:\mingw64\bin\gcc.EXE -G MinGW Makefiles -DCMAKE_MAKE_PROGRAM=C:\mingw64\bin\mingw32-make.EXE -DENABLE_BZIP2=OFF -DENABLE_LZMA=OFF -DENABLE_ZSTD=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TOOLS=OFF -DBUILD_REGRESS=OFF -DBUILD_DOC=OFF -DZLIB_INCLUDE_DIR=D:\a\PenguScript\PenguScript\build\include -DZLIB_LIBRARY=D:\a\PenguScript\PenguScript\build\lib\libz.a
  [EXEC] cmake --build D:\a\PenguScript\PenguScript\build\libzip_cmake --config Release -j 4 --target zip
[LIBZIP] Created D:\a\PenguScript\PenguScript\build\lib\libzip.a
[LIBEXPAT] Building expat-2.6.4 with CMake...
  [EXEC] cmake -S D:\a\PenguScript\PenguScript\extern\expat-2.6.4 -B D:\a\PenguScript\PenguScript\build\expat_cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=C:\mingw64\bin\gcc.EXE -G MinGW Makefiles -DCMAKE_MAKE_PROGRAM=C:\mingw64\bin\mingw32-make.EXE -DEXPAT_BUILD_TOOLS=OFF -DEXPAT_BUILD_EXAMPLES=OFF -DEXPAT_BUILD_TESTS=OFF -DEXPAT_SHARED_LIBS=OFF
  [EXEC] cmake --build D:\a\PenguScript\PenguScript\build\expat_cmake --config Release -j 4 --target expat
[LIBEXPAT] Created D:\a\PenguScript\PenguScript\build\lib\libexpat.a
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DSTATIC -ID:\a\PenguScript\PenguScript\extern\xlsxio-0.2.36\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\xlsxio-0.2.36\lib\xlsxio_read.c -o D:\a\PenguScript\PenguScript\build\obj_xlsxio_lib\xlsxio_read.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DSTATIC -ID:\a\PenguScript\PenguScript\extern\xlsxio-0.2.36\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\xlsxio-0.2.36\lib\xlsxio_read_sharedstrings.c -o D:\a\PenguScript\PenguScript\build\obj_xlsxio_lib\xlsxio_read_sharedstrings.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -DSTATIC -ID:\a\PenguScript\PenguScript\extern\xlsxio-0.2.36\include -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\extern\xlsxio-0.2.36\lib\xlsxio_write.c -o D:\a\PenguScript\PenguScript\build\obj_xlsxio_lib\xlsxio_write.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libxlsxio_read.a D:\a\PenguScript\PenguScript\build\obj_xlsxio_lib\xlsxio_read.o D:\a\PenguScript\PenguScript\build\obj_xlsxio_lib\xlsxio_read_sharedstrings.o
[XLSXIO] Created libxlsxio_read.a
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libxlsxio_write.a D:\a\PenguScript\PenguScript\build\obj_xlsxio_lib\xlsxio_write.o
[XLSXIO] Created libxlsxio_write.a
[TOMLC17] Compiling tomlc17...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\extern\tomlc17-R260821\src -Wno-array-bounds -Wno-stringop-overflow -c D:\a\PenguScript\PenguScript\extern\tomlc17-R260821\src\tomlc17.c -o D:\a\PenguScript\PenguScript\build\obj_tomlc17\tomlc17.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_tomlc17.c -o D:\a\PenguScript\PenguScript\build\obj_tomlc17\wrappers_tomlc17.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libtomlc17.a D:\a\PenguScript\PenguScript\build\obj_tomlc17\tomlc17.o D:\a\PenguScript\PenguScript\build\obj_tomlc17\wrappers_tomlc17.o
[TOMLC17] Created D:\a\PenguScript\PenguScript\build\lib\libtomlc17.a
[PENGU_STB] Compiling single-header wrappers...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_stb.c -o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_stb.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_xxhash.c -o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_xxhash.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_uuid.c -o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_uuid.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_minicoro.c -o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_minicoro.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\wrappers_raygui.c -o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_raygui.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\tinyfiledialogs.c -o D:\a\PenguScript\PenguScript\build\obj_stb\tinyfiledialogs.o
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -Wno-unused-function -Wno-return-type -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -ID:\a\PenguScript\PenguScript\std_c -ID:\a\PenguScript\PenguScript\build\include -c D:\a\PenguScript\PenguScript\std_c\tinyfd_moredialogs.c -o D:\a\PenguScript\PenguScript\build\obj_stb\tinyfd_moredialogs.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libpengu_stb.a D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_stb.o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_xxhash.o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_uuid.o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_minicoro.o D:\a\PenguScript\PenguScript\build\obj_stb\wrappers_raygui.o D:\a\PenguScript\PenguScript\build\obj_stb\tinyfiledialogs.o D:\a\PenguScript\PenguScript\build\obj_stb\tinyfd_moredialogs.o
[PENGU_STB] Created D:\a\PenguScript\PenguScript\build\lib\libpengu_stb.a
[RUNTIME] Compiling pengu_runtime.c...
  [EXEC] C:\mingw64\bin\gcc.EXE -O2 -ID:\a\PenguScript\PenguScript -ID:\a\PenguScript\PenguScript\build\include -DPCRE2_STATIC -DPCRE2_CODE_UNIT_WIDTH=8 -DLIBXML_STATIC -DCURL_STATICLIB -Wno-incompatible-pointer-types -Wno-implicit-function-declaration -c D:\a\PenguScript\PenguScript\pengu_parser\pengu_runtime.c -o D:\a\PenguScript\PenguScript\build\obj_runtime\pengu_runtime.o
  [EXEC] C:\mingw64\bin\ar.EXE rcs D:\a\PenguScript\PenguScript\build\lib\libpengu_runtime.a D:\a\PenguScript\PenguScript\build\obj_runtime\pengu_runtime.o
[RUNTIME] Created D:\a\PenguScript\PenguScript\build\lib\libpengu_runtime.a
=== Runtime build finished. Built: ZLIB, PCRE2, LIBXML2, MBEDTLS, CURL, MICROHTTPD, SQLITE3, WEBUI, RAYLIB, RAYMATH, LIBYAML, LIBCYAML, LIBZIP, LIBEXPAT, XLSXIO, TOMLC17, PENGU_STB, RUNTIME ===

[4/7] Assembling distribution assets in D:\a\PenguScript\PenguScript\pengucc_build...
  [STD] Copied standard library to D:\a\PenguScript\PenguScript\pengucc_build\std
  [LIB] Copied libcurl.a to runtime/
  [LIB] Copied libcyaml.a to runtime/
  [LIB] Copied libexpat.a to runtime/
  [LIB] Copied libmbedcrypto.a to runtime/
  [LIB] Copied libmicrohttpd.a to runtime/
  [LIB] Copied libpcre2-8.a to runtime/
  [LIB] Copied libpengu_raymath.a to runtime/
  [LIB] Copied libpengu_runtime.a to runtime/
  [LIB] Copied libpengu_stb.a to runtime/
  [LIB] Copied libraylib.a to runtime/
  [LIB] Copied libsqlite3.a to runtime/
  [LIB] Copied libtomlc17.a to runtime/
  [LIB] Copied libwebui.a to runtime/
  [LIB] Copied libxlsxio_read.a to runtime/
  [LIB] Copied libxlsxio_write.a to runtime/
  [LIB] Copied libxml2.a to runtime/
  [LIB] Copied libyaml.a to runtime/
  [LIB] Copied libz.a to runtime/
  [LIB] Copied libzip.a to runtime/
  [INC] Copied dependency headers to D:\a\PenguScript\PenguScript\pengucc_build\runtime\include

[5/7] Building and packaging VS Code Extension (.vsix)...
  [VSCODE] Packaging VS Code extension...
  [EXEC] npm.cmd --version
  [VSCODE] Installing npm dependencies...
  [EXEC] npm.cmd install
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/abort-controller@2.2.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-auth@1.11.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-client@1.11.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-process@1.0.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-rest-pipeline@1.25.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-tracing@1.4.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/core-util@1.14.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/identity@4.13.2',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@azure/logger@1.4.0',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@typespec/ts-http-runtime@0.3.8',
npm warn EBADENGINE   required: { node: '>=22.0.0' },
npm warn EBADENGINE   current: { node: 'v20.20.2', npm: '10.8.2' }
npm warn EBADENGINE }
npm warn deprecated whatwg-encoding@3.1.1: Use @exodus/bytes instead for a more spec-conformant and faster implementation
npm warn deprecated inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
npm warn deprecated glob@7.2.3: Old versions of glob are not supported, and contain widely publicized security vulnerabilities, which have been fixed in the current version. Please update. Support for old versions may be purchased (at exorbitant rates) by contacting i@izs.me
npm warn deprecated prebuild-install@7.1.3: No longer maintained. Please contact the author of the relevant native addon; alternatives are available.

added 192 packages, and audited 193 packages in 8s

50 packages are looking for funding
  run `npm fund` for details

5 vulnerabilities (3 moderate, 2 high)

To address issues that do not require attention, run:
  npm audit fix

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
  [VSCODE] Bundling extension with esbuild...
  [EXEC] npm.cmd run bundle

> pengus@0.10.0 bundle
> esbuild ./src/extension.ts --bundle --outfile=out/extension.js --external:vscode --format=cjs --platform=node


  out\extension.js  771.2kb

Done in 64ms
  [VSCODE] Generating .vsix package with vsce...
  [EXEC] npx.cmd -y @vscode/vsce package
Executing prepublish script 'npm run vscode:prepublish'...

> pengus@0.10.0 vscode:prepublish
> npm run bundle


> pengus@0.10.0 bundle
> esbuild ./src/extension.ts --bundle --outfile=out/extension.js --external:vscode --format=cjs --platform=node


  out\extension.js  771.2kb

Done in 54ms
Warning: This extension consists of 326 files, out of which 166 are JavaScript files. For performance reasons, you should bundle your extension: https://aka.ms/vscode-bundle-extension. You should also exclude unnecessary files by adding them to your .vscodeignore: https://aka.ms/vscode-vscodeignore.

Files included in the VSIX:
pengus-0.10.0.vsix
├─ [Content_Types].xml 
├─ extension.vsixmanifest 
└─ extension/
   ├─ LICENSE.txt 
   ├─ README.md [3.94 KB]
   ├─ language-configuration.json [0.85 KB]
   ├─ package.json [8.48 KB]
   ├─ icons/
   │  ├─ pengu_icon.png [3 MB]
   │  └─ pengu_icon_white.png [27.75 KB]
   ├─ node_modules/
   │  ├─ balanced-match/ (5 files) [6.78 KB]
   │  ├─ brace-expansion/ (5 files) [16.5 KB]
   │  ├─ minimatch/ (6 files) [41.37 KB]
   │  ├─ semver/ (53 files) [98.7 KB]
   │  ├─ vscode-jsonrpc/ (48 files) [203.49 KB]
   │  ├─ vscode-languageclient/ (121 files) [637.35 KB]
   │  ├─ vscode-languageserver-protocol/ (68 files) [356.78 KB]
   │  └─ vscode-languageserver-types/ (9 files) [367.87 KB]
   ├─ out/
   │  └─ extension.js [771.15 KB]
   ├─ snippets/
   │  └─ pengus.json [31.86 KB]
   └─ syntaxes/
      └─ pengus.tmLanguage.json [6.82 KB]

=> Run vsce ls --tree to see all included files.

Packaged: D:\a\PenguScript\PenguScript\vscode-extension\pengus-0.10.0.vsix (326 files, 3.57 MB)
  [VSCODE] Copied pengus-0.10.0.vsix -> D:\a\PenguScript\PenguScript\pengucc_build\pengus-0.10.0.vsix

[6/7] Packaging standalone CLI executable with PyInstaller...
  [EXEC] D:\a\PenguScript\PenguScript\.venv\Scripts\python.exe -m PyInstaller --clean --name pengu --onefile --console --distpath D:\a\PenguScript\PenguScript\pengucc_build --workpath D:\a\PenguScript\PenguScript\build\pyinstaller_work --specpath D:\a\PenguScript\PenguScript\build --noconfirm --add-data D:\a\PenguScript\PenguScript\std;std --add-data D:\a\PenguScript\PenguScript\pengu_runtime.h;. --add-data D:\a\PenguScript\PenguScript\VERSION;. --add-data D:\a\PenguScript\PenguScript\c_bind_stubs;c_bind_stubs --hidden-import pygls --hidden-import pygls.lsp --hidden-import pygls.lsp.server --hidden-import pygls.protocol --hidden-import pygls.capabilities --hidden-import lsprotocol --hidden-import lsprotocol.types --hidden-import lsprotocol.converters --hidden-import cattrs --hidden-import attrs --hidden-import pycparser --hidden-import pycparser.c_parser --hidden-import pycparser.c_lexer --hidden-import pycparser.c_ast --hidden-import pycparser.plyparser --hidden-import pycparser.ast_transforms --hidden-import lark --hidden-import lark.parsers --hidden-import lark.parsers.lalr_parser --hidden-import pengu_bind --hidden-import pengu_lsp --hidden-import pengu_lsp.server --hidden-import pengu_lsp.completions --hidden-import pengu_lsp.hover --hidden-import pengu_lsp.code_actions --hidden-import pengu_lsp.formatting --hidden-import pengu_parser --hidden-import pengu_parser.pengu_parser --hidden-import pengu_parser.pengu_checker --hidden-import pengu_parser.pengu_codegen --hidden-import pengu_parser.pengu_symbols --hidden-import pengu_parser.pengu_types --hidden-import pengu_parser.pengu_errors --hidden-import pengu_parser.pengu_infer --hidden-import pengu_parser.pengu_grammar --collect-submodules lsprotocol --collect-submodules pygls --collect-submodules cattrs --collect-submodules attrs D:\a\PenguScript\PenguScript\pengu_project.py
477 INFO: PyInstaller: 6.22.2, contrib hooks: 2026.7
477 INFO: Python: 3.14.7
503 INFO: Platform: Windows-2025Server-10.0.26100-SP0
503 INFO: Python environment: D:\a\PenguScript\PenguScript\.venv
503 INFO: wrote D:\a\PenguScript\PenguScript\build\pengu.spec
507 INFO: Removing temporary files and cleaning cache in C:\Users\runneradmin\AppData\Local\pyinstaller
2107 INFO: Module search paths (PYTHONPATH):
['D:\\a\\PenguScript\\PenguScript',
 'C:\\hostedtoolcache\\windows\\Python\\3.14.7\\x64\\python314.zip',
 'C:\\hostedtoolcache\\windows\\Python\\3.14.7\\x64\\DLLs',
 'C:\\hostedtoolcache\\windows\\Python\\3.14.7\\x64\\Lib',
 'C:\\hostedtoolcache\\windows\\Python\\3.14.7\\x64',
 'D:\\a\\PenguScript\\PenguScript\\.venv',
 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages',
 'D:\\a\\PenguScript\\PenguScript']
2407 INFO: Appending 'datas' from .spec
2409 INFO: checking Analysis
2409 INFO: Building Analysis because Analysis-00.toc is non existent
2409 INFO: Looking for Python shared library...
2409 INFO: Using Python shared library: C:\hostedtoolcache\windows\Python\3.14.7\x64\python314.dll
2410 INFO: Running Analysis Analysis-00.toc
2410 INFO: Target bytecode optimization level: 0
2410 INFO: Initializing module dependency graph...
2410 INFO: Initializing module graph hook caches...
2423 INFO: Analyzing modules for base_library.zip ...
4346 INFO: Processing standard module hook 'hook-encodings.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
4818 INFO: Processing standard module hook 'hook-math.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
13148 INFO: Processing standard module hook 'hook-difflib.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
13164 INFO: Processing standard module hook 'hook-heapq.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
13344 INFO: Processing standard module hook 'hook-pickle.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
15891 INFO: Caching module dependency graph...
15924 INFO: Analyzing D:\a\PenguScript\PenguScript\pengu_project.py
16117 INFO: Processing pre-safe-import-module hook 'hook-tomli.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
16118 INFO: SetuptoolsInfo: initializing cached setuptools info...
16597 INFO: Setuptools: 'tomli' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.tomli'!
16605 INFO: Processing standard module hook 'hook-setuptools.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
16670 INFO: Processing standard module hook 'hook-platform.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
16731 INFO: Processing standard module hook 'hook-sysconfig.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
16737 INFO: Processing standard module hook 'hook-_ctypes.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
16751 INFO: Processing pre-safe-import-module hook 'hook-distutils.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
16788 INFO: Processing pre-safe-import-module hook 'hook-jaraco.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
16788 INFO: Setuptools: 'jaraco' appears to be a full setuptools-vendored copy - creating alias to 'setuptools._vendor.jaraco'!
16801 INFO: Processing pre-safe-import-module hook 'hook-more_itertools.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
16801 INFO: Setuptools: 'more_itertools' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.more_itertools'!
17058 INFO: Processing standard module hook 'hook-_osx_support.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
17064 INFO: Processing pre-safe-import-module hook 'hook-typing_extensions.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
17435 INFO: Processing standard module hook 'hook-multiprocessing.util.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
17621 INFO: Processing standard module hook 'hook-xml.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
18557 INFO: Processing pre-safe-import-module hook 'hook-packaging.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
18951 INFO: Processing standard module hook 'hook-setuptools._vendor.jaraco.text.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
18953 INFO: Processing pre-safe-import-module hook 'hook-importlib_resources.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
18967 INFO: Processing pre-safe-import-module hook 'hook-backports.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
18967 INFO: Setuptools: 'backports' appears to be a full setuptools-vendored copy - creating alias to 'setuptools._vendor.backports'!
20369 INFO: Processing pre-safe-import-module hook 'hook-wheel.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
20369 INFO: Setuptools: 'wheel' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.wheel'!
20702 INFO: Processing standard module hook 'hook-lark.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\lark\\__pyinstaller'
22510 INFO: Processing standard module hook 'hook-pycparser.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
24448 INFO: Analyzing hidden import 'pycparser.plyparser'
24448 ERROR: Hidden import 'pycparser.plyparser' not found
24449 INFO: Analyzing hidden import 'pygls.cli'
24451 INFO: Analyzing hidden import 'pygls.client'
24460 INFO: Analyzing hidden import 'pygls.lsp._base_client'
24521 INFO: Analyzing hidden import 'pygls.lsp.client'
24522 INFO: Analyzing hidden import 'cattrs.preconf'
24526 INFO: Analyzing hidden import 'cattrs.preconf.bson'
24559 INFO: Analyzing hidden import 'cattrs.preconf.cbor2'
24563 INFO: Analyzing hidden import 'cattrs.preconf.json'
24568 INFO: Analyzing hidden import 'cattrs.preconf.msgpack'
24573 INFO: Analyzing hidden import 'cattrs.preconf.msgspec'
24585 INFO: Analyzing hidden import 'cattrs.preconf.orjson'
24591 INFO: Analyzing hidden import 'cattrs.preconf.pyyaml'
24595 INFO: Analyzing hidden import 'cattrs.preconf.tomlkit'
24601 INFO: Analyzing hidden import 'cattrs.preconf.tomllib'
24607 INFO: Analyzing hidden import 'cattrs.preconf.ujson'
24612 INFO: Processing module hooks (post-graph stage)...
24613 WARNING: Hidden import "pycparser.lextab" not found!
24613 WARNING: Hidden import "pycparser.yacctab" not found!
25167 INFO: Processing standard module hook 'hook-webbrowser.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks'
25733 INFO: Performing binary vs. data reclassification (80 entries)
25744 INFO: Looking for ctypes DLLs
25778 INFO: Analyzing run-time hooks ...
25781 INFO: Including run-time hook 'pyi_rth_inspect.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\rthooks'
25785 INFO: Including run-time hook 'pyi_rth_pkgutil.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\rthooks'
25787 INFO: Including run-time hook 'pyi_rth_multiprocessing.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\rthooks'
25790 INFO: Including run-time hook 'pyi_rth_setuptools.py' from 'D:\\a\\PenguScript\\PenguScript\\.venv\\Lib\\site-packages\\PyInstaller\\hooks\\rthooks'
25805 INFO: Creating base_library.zip...
25835 INFO: Looking for dynamic libraries
26808 INFO: Extra DLL search directories (AddDllDirectory): []
26808 INFO: Extra DLL search directories (PATH): []
28061 INFO: Warnings written to D:\a\PenguScript\PenguScript\build\pyinstaller_work\pengu\warn-pengu.txt
28111 INFO: Graph cross-reference written to D:\a\PenguScript\PenguScript\build\pyinstaller_work\pengu\xref-pengu.html
28138 INFO: checking PYZ
28138 INFO: Building PYZ because PYZ-00.toc is non existent
28138 INFO: Building PYZ (ZlibArchive) D:\a\PenguScript\PenguScript\build\pyinstaller_work\pengu\PYZ-00.pyz
28533 INFO: Building PYZ (ZlibArchive) D:\a\PenguScript\PenguScript\build\pyinstaller_work\pengu\PYZ-00.pyz completed successfully.
28568 INFO: checking PKG
28568 INFO: Building PKG because PKG-00.toc is non existent
28568 INFO: Building PKG (CArchive) pengu.pkg
29859 INFO: Building PKG (CArchive) pengu.pkg completed successfully.
29863 INFO: Bootloader D:\a\PenguScript\PenguScript\.venv\Lib\site-packages\PyInstaller\bootloader\Windows-64bit-intel\run.exe
29863 INFO: checking EXE
29863 INFO: Building EXE because EXE-00.toc is non existent
29863 INFO: Building EXE from EXE-00.toc
29864 INFO: Copying bootloader EXE to D:\a\PenguScript\PenguScript\pengucc_build\pengu.exe
29866 INFO: Copying icon to EXE
29872 INFO: Copying 0 resources to EXE
29872 INFO: Embedding manifest in EXE
29874 INFO: Appending PKG archive to EXE
29889 INFO: Fixing EXE headers
30008 INFO: Building EXE from EXE-00.toc completed successfully.
30011 INFO: Build complete! The results are available in: D:\a\PenguScript\PenguScript\pengucc_build
  [DOCS] Generated README_RELEASE.md and D:\a\PenguScript\PenguScript\pengucc_build\README.md

[7/7] Running release verification & smoke tests...
  [TEST 1] Verifying pengu.exe --help...
  [EXEC] D:\a\PenguScript\PenguScript\pengucc_build\pengu.exe --help
usage: pengu [-h] [-V]
             {init,add,build,run,test,check,update,bind,fmt,clean,lsp,doc} ...

PenguScript v0.10.0 Package & Build Manager

positional arguments:
  {init,add,build,run,test,check,update,bind,fmt,clean,lsp,doc}
                        Available subcommands
    init                Create a new PenguScript project template
    add                 Add an external dependency or binding to the project
    build               Compile the project according to configuration
    run                 Build and execute the project target, or run a
                        standalone .pengu script
    test                Compile and run the project's integrated unit tests
    check               Parse and type-check every module without generating
                        code (CI)
    update              Update dependencies: git pull + re-run build scripts
    bind                Generate a .d.pengu binding from a C header
    fmt                 Format .pengu files or directories (standard style)
    clean               Remove build directory and generated artifacts
    lsp                 Launch the PenguScript Language Server Protocol (LSP)
    doc                 Generate Markdown documentation from ## comments

options:
  -h, --help            show this help message and exit
  -V, --version         Print the PenguScript toolchain version and exit

Examples: pengu init my_game --type exe pengu add https://github.com/webui-
dev/webui pengu add ../local_binding -n my_binding pengu build --profile
release pengu build --cc clang --verbose pengu check # parse + type-check
without codegen (CI) pengu fmt src/ tests/ # format files/directories pengu
fmt --check src/ # verify formatting (exit 1 if changes) pengu run --profile
debug pengu run hello.pengu # run a standalone script (when main: enabled)
pengu update # git pull + rebuild every dependency pengu bind webui.h --prefix
webui_ --links webui-2-static ole32 stdc++ uuid pengu clean

  [TEST 2] Testing project initialization...
  [EXEC] D:\a\PenguScript\PenguScript\pengucc_build\pengu.exe init smoke_proj --type exe --links pengu_runtime
     Created exe project 'smoke_proj' at D:\a\PenguScript\PenguScript\scratch\smoke_release_test\smoke_proj
  [TEST 3] Testing standalone compilation and execution ('pengu run')...
  [EXEC] D:\a\PenguScript\PenguScript\pengucc_build\pengu.exe run

[ERROR] Command failed with exit code 1: D:\a\PenguScript\PenguScript\pengucc_build\pengu.exe run
Stderr: Traceback (most recent call last):
  File "pengu_project.py", line 2301, in <module>
  File "pengu_project.py", line 2199, in main
  File "pengu_project.py", line 1874, in run_project
  File "pengu_project.py", line 1257, in build_project
  File "pengu_project.py", line 1173, in compile
  File "pengu_project.py", line 892, in bundle
  File "pengu_parser\pengu_checker.py", line 196, in check
  File "pengu_parser\pengu_checker.py", line 1717, in _check_node
  File "pengu_parser\pengu_infer.py", line 2368, in infer
  File "pengu_parser\pengu_infer.py", line 511, in _reject_list_glued_operator
pengu_parser.pengu_errors.TypeMismatchError: [line 6, col 5] Ambiguous 'and' after a call with arguments
[PYI-3772:ERROR] Failed to execute script 'pengu_project' due to unhandled exception!

Stdout:    Compiling smoke_proj v0.1.0 (exe) [debug]

Error: Process completed with exit code 1.