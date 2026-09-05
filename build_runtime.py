#!/usr/bin/env python3
"""build_runtime.py - Automated compilation of PenguScript runtime and external dependencies.

Compiles into build/lib/ (Windows builds every library statically):
  - zlib 1.3.2 -> libz.a                 - PCRE2 10.47 -> libpcre2-8.a
  - libxml2 2.9.0 -> libxml2.a           - mbedtls 4.2.0 -> libmbedcrypto.a
  - curl 8.21.0 -> libcurl.a             - libmicrohttpd 1.0.1 -> libmicrohttpd.a
  - SQLite 3.53.4 -> libsqlite3.a        - raylib 6.0 -> libraylib.a
  - WebUI 2.5.0 -> libwebui.a            - libuv 1.52.1 -> libuv.a
  - libyaml 0.2.5 -> libyaml.a           - libcyaml 1.4.2 -> libcyaml.a
  - libzip 1.11.3 -> libzip.a            - libexpat 2.6.4 -> libexpat.a
  - xlsxio 0.2.36 -> libxlsxio_{read,write}.a
  - tomlc17 R260821 -> libtomlc17.a      - std_c wrappers -> libpengu_stb.a
  - pengu_runtime.c -> libpengu_runtime.a

Cross-platform notes (Linux/macOS):
  - The Windows-tuned static builds of libxml2/curl/libmicrohttpd are skipped
    on POSIX hosts; the C runtime then links the system libraries (install the
    matching -dev packages / brew formulae; see .github/workflows/ci.yml).
  - libxml2's headers are pulled through pkg-config when compiling
    pengu_runtime.c; every other library is still built statically from
    source where feasible, and best-effort builds never abort the run.

Headers are copied into build/include/.
"""

import os
import sys
import platform as _platform_mod
import shutil
import subprocess
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
EXTERN_DIR = ROOT_DIR / "extern"
BUILD_DIR = ROOT_DIR / "build"
INCLUDE_DIR = BUILD_DIR / "include"
LIB_DIR = BUILD_DIR / "lib"
PARSER_DIR = ROOT_DIR / "pengu_parser"

IS_WINDOWS = sys.platform.startswith("win")
IS_DARWIN = sys.platform.startswith("darwin")
IS_POSIX = not IS_WINDOWS


def platform_machine():
    """Returns the CPU architecture of the host (normalized)."""
    m = _platform_mod.machine().lower()
    if m in ("amd64", "x86_64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "arm64"
    return m


def _cmake_generator():
    """Returns the CMake generator + make program best suited to this host."""
    if IS_WINDOWS:
        mk = shutil.which("mingw32-make") or "mingw32-make"
        return ["-G", "MinGW Makefiles", "-DCMAKE_MAKE_PROGRAM=" + mk]
    # POSIX hosts use the platform make (or Ninja when available).
    ninja = shutil.which("ninja")
    if ninja:
        return ["-G", "Ninja"]
    return ["-G", "Unix Makefiles"]


def _pkg_config_cflags(package):
    """Returns pkg-config include flags for `package` ([] when unavailable)."""
    if IS_WINDOWS:
        return []
    pkgconfig = shutil.which("pkg-config")
    if not pkgconfig:
        return []
    try:
        res = subprocess.run([pkgconfig, "--cflags", package],
                             capture_output=True, text=True)
        if res.returncode != 0:
            return []
        return [tok for tok in res.stdout.split() if tok]
    except Exception:
        return []


def get_toolchain():
    """Detects available C compiler and archiver."""
    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    ar = shutil.which("ar") or shutil.which("llvm-ar")
    if not cc:
        raise RuntimeError("No C compiler (gcc/clang/cc) found in PATH.")
    if not ar:
        raise RuntimeError("No static archiver (ar/llvm-ar) found in PATH.")
    return cc, ar

def run_cmd(cmd, cwd=None, env=None):
    """Runs a shell command and raises an error on failure."""
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"  [EXEC] {cmd_str}")
    res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Command failed with exit code {res.returncode}:")
        print(res.stderr)
        raise RuntimeError(f"Command failed: {cmd_str}\n{res.stderr}")
    return res

def build_zlib(cc, ar, rebuild=False):
    """Compiles zlib-1.3.2 into build/lib/libz.a and copies headers."""
    target_lib = LIB_DIR / "libz.a"
    zlib_dir = EXTERN_DIR / "zlib-1.3.2"
    if not zlib_dir.exists():
        raise FileNotFoundError(f"zlib source directory not found: {zlib_dir}")

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zlib_dir / "zlib.h", INCLUDE_DIR / "zlib.h")
    shutil.copy2(zlib_dir / "zconf.h", INCLUDE_DIR / "zconf.h")

    if target_lib.exists() and not rebuild:
        print(f"[ZLIB] {target_lib.name} is up to date.")
        return target_lib

    print("[ZLIB] Compiling zlib-1.3.2...")
    sources = [
        "adler32.c", "compress.c", "crc32.c", "deflate.c", "gzclose.c",
        "gzlib.c", "gzread.c", "gzwrite.c", "infback.c", "inffast.c",
        "inflate.c", "inftrees.c", "trees.c", "uncompr.c", "zutil.c"
    ]
    obj_files = []
    obj_dir = BUILD_DIR / "obj_zlib"
    obj_dir.mkdir(parents=True, exist_ok=True)

    for src in sources:
        src_path = zlib_dir / src
        obj_path = obj_dir / f"{src_path.stem}.o"
        cmd = [cc, "-O2", "-I" + str(zlib_dir), "-c", str(src_path), "-o", str(obj_path)]
        run_cmd(cmd)
        obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[ZLIB] Created {target_lib}")
    return target_lib

def build_pcre2(cc, ar, rebuild=False):
    """Compiles PCRE2 10.47 (8-bit) into build/lib/libpcre2-8.a and copies headers."""
    target_lib = LIB_DIR / "libpcre2-8.a"
    pcre2_dir = EXTERN_DIR / "pcre2-10.47"
    src_dir = pcre2_dir / "src"
    if not pcre2_dir.exists():
        raise FileNotFoundError(f"pcre2 source directory not found: {pcre2_dir}")

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    if not (src_dir / "config.h").exists():
        shutil.copy2(src_dir / "config.h.generic", src_dir / "config.h")
    if not (src_dir / "pcre2.h").exists():
        shutil.copy2(src_dir / "pcre2.h.generic", src_dir / "pcre2.h")
    if not (src_dir / "pcre2_chartables.c").exists():
        shutil.copy2(src_dir / "pcre2_chartables.c.dist", src_dir / "pcre2_chartables.c")

    shutil.copy2(src_dir / "pcre2.h", INCLUDE_DIR / "pcre2.h")

    if target_lib.exists() and not rebuild:
        print(f"[PCRE2] {target_lib.name} is up to date.")
        return target_lib

    print("[PCRE2] Compiling pcre2-10.47 (8-bit)...")
    sources = [
        "pcre2_auto_possess.c", "pcre2_chkdint.c", "pcre2_compile.c", "pcre2_compile_cgroup.c",
        "pcre2_compile_class.c", "pcre2_config.c", "pcre2_context.c", "pcre2_convert.c",
        "pcre2_dfa_match.c", "pcre2_error.c", "pcre2_extuni.c", "pcre2_find_bracket.c",
        "pcre2_match.c", "pcre2_match_data.c", "pcre2_match_next.c", "pcre2_newline.c",
        "pcre2_ord2utf.c", "pcre2_pattern_info.c", "pcre2_script_run.c", "pcre2_serialize.c",
        "pcre2_string_utils.c", "pcre2_study.c", "pcre2_substitute.c", "pcre2_substring.c",
        "pcre2_tables.c", "pcre2_ucd.c", "pcre2_valid_utf.c", "pcre2_xclass.c",
        "pcre2_chartables.c"
    ]
    obj_files = []
    obj_dir = BUILD_DIR / "obj_pcre2"
    obj_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-O2", "-DHAVE_CONFIG_H", "-DPCRE2_CODE_UNIT_WIDTH=8",
        "-DPCRE2_STATIC", "-DSUPPORT_UNICODE", "-I" + str(src_dir)
    ]

    for src in sources:
        src_path = src_dir / src
        obj_path = obj_dir / f"{src_path.stem}.o"
        cmd = [cc] + flags + ["-c", str(src_path), "-o", str(obj_path)]
        run_cmd(cmd)
        obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[PCRE2] Created {target_lib}")
    return target_lib

def build_libxml2(cc, ar, rebuild=False):
    """Compiles libxml2-2.9.0 into build/lib/libxml2.a and copies headers."""
    target_lib = LIB_DIR / "libxml2.a"
    xml_dir = EXTERN_DIR / "libxml2-2.9.0"
    if not xml_dir.exists():
        raise FileNotFoundError(f"libxml2 source directory not found: {xml_dir}")

    config_path = xml_dir / "config.h"
    if not config_path.exists() or rebuild:
        if (xml_dir / "win32" / "VC10" / "config.h").exists():
            content = (xml_dir / "win32" / "VC10" / "config.h").read_text(encoding="utf-8")
            content = content.replace("#define ICONV_CONST const", "#define ICONV_CONST")
            config_path.write_text(content, encoding="utf-8")
        elif (xml_dir / "config.h.in").exists():
            shutil.copy2(xml_dir / "config.h.in", config_path)

    if IS_POSIX:
        # libxml2's build system is autotools-only for this vintage; a static
        # build would need a platform-generated config.h. On POSIX hosts we
        # link the system libxml2 (dev package; headers under the standard
        # pkg-config include dir). The bundled 2.9.0 headers are NOT staged
        # here so the native system headers stay in charge.
        print("[LIBXML2] Skipped on this platform (uses system libxml2).")
        return None

    xml_include_dst = INCLUDE_DIR / "libxml"
    xml_include_dst.mkdir(parents=True, exist_ok=True)
    for h in (xml_dir / "include" / "libxml").glob("*.h"):
        shutil.copy2(h, xml_include_dst / h.name)

    if target_lib.exists() and not rebuild:
        print(f"[LIBXML2] {target_lib.name} is up to date.")
        return target_lib

    print("[LIBXML2] Compiling libxml2-2.9.0...")
    sources = [
        "SAX.c", "SAX2.c", "DOCBparser.c", "HTMLparser.c", "HTMLtree.c", "buf.c", "c14n.c", "catalog.c",
        "chvalid.c", "debugXML.c", "dict.c", "encoding.c", "entities.c", "error.c", "globals.c",
        "hash.c", "legacy.c", "list.c", "nanoftp.c", "nanohttp.c", "parser.c",
        "parserInternals.c", "pattern.c", "relaxng.c", "schematron.c", "threads.c",
        "tree.c", "uri.c", "valid.c", "xinclude.c", "xlink.c", "xmlIO.c",
        "xmlmemory.c", "xmlmodule.c", "xmlreader.c", "xmlregexp.c", "xmlsave.c",
        "xmlschemas.c", "xmlschemastypes.c", "xmlstring.c", "xmlunicode.c",
        "xmlwriter.c", "xpath.c", "xpointer.c", "xzlib.c"
    ]
    obj_files = []
    obj_dir = BUILD_DIR / "obj_libxml2"
    obj_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-O2", "-DLIBXML_STATIC", "-DWITHOUT_TRIO", "-D_REENTRANT",
        "-Wno-incompatible-pointer-types",
        "-Wno-implicit-function-declaration",
        "-Wno-int-conversion",
        "-I" + str(xml_dir),
        "-I" + str(xml_dir / "include"),
        "-I" + str(INCLUDE_DIR)
    ]

    for src in sources:
        src_path = xml_dir / src
        obj_path = obj_dir / f"{src_path.stem}.o"
        cmd = [cc] + flags + ["-c", str(src_path), "-o", str(obj_path)]
        run_cmd(cmd)
        obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[LIBXML2] Created {target_lib}")
    return target_lib

def build_mbedtls(cc, ar, rebuild=False):
    """Compiles mbedtls 4.2.0 crypto into build/lib/libmbedcrypto.a and copies headers."""
    target_lib = LIB_DIR / "libmbedcrypto.a"
    mbedtls_dir = EXTERN_DIR / "mbedtls-4.2.0"
    if not mbedtls_dir.exists():
        raise FileNotFoundError(f"mbedtls source directory not found: {mbedtls_dir}")

    # Copy headers
    mbed_inc_dst = INCLUDE_DIR / "mbedtls"
    mbed_inc_dst.mkdir(parents=True, exist_ok=True)
    for h in (mbedtls_dir / "include" / "mbedtls").glob("*.h"):
        shutil.copy2(h, mbed_inc_dst / h.name)

    # Copy tf-psa-crypto headers
    tf_inc = mbedtls_dir / "tf-psa-crypto" / "include"
    if tf_inc.exists():
        for item in tf_inc.iterdir():
            if item.is_dir():
                dst = INCLUDE_DIR / item.name
                dst.mkdir(parents=True, exist_ok=True)
                for h in item.rglob("*.h"):
                    rel = h.relative_to(item)
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(h, target)

    builtin_inc = mbedtls_dir / "tf-psa-crypto" / "drivers" / "builtin" / "include" / "mbedtls"
    if builtin_inc.exists():
        for h in builtin_inc.rglob("*.h"):
            rel = h.relative_to(builtin_inc)
            target = mbed_inc_dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(h, target)

    if target_lib.exists() and not rebuild:
        print(f"[MBEDTLS] {target_lib.name} is up to date.")
        return target_lib

    print("[MBEDTLS] Compiling mbedtls-4.2.0 crypto...")
    crypto_src_dir = mbedtls_dir / "tf-psa-crypto" / "drivers" / "builtin" / "src"
    platform_dir = mbedtls_dir / "tf-psa-crypto" / "platform"

    sources = [
        crypto_src_dir / "md5.c",
        crypto_src_dir / "sha1.c",
        crypto_src_dir / "sha256.c",
        crypto_src_dir / "sha512.c",
        platform_dir / "platform_util.c",
        platform_dir / "platform.c"
    ]
    obj_files = []
    obj_dir = BUILD_DIR / "obj_mbedtls"
    obj_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-O2",
        "-DMBEDTLS_MD5_C",
        "-DMBEDTLS_SHA1_C",
        "-DMBEDTLS_SHA256_C",
        "-DMBEDTLS_SHA512_C",
        "-I" + str(mbedtls_dir / "include"),
        "-I" + str(mbedtls_dir / "tf-psa-crypto" / "include"),
        "-I" + str(mbedtls_dir / "tf-psa-crypto" / "drivers" / "builtin" / "include"),
        "-I" + str(mbedtls_dir / "tf-psa-crypto" / "core"),
        "-I" + str(mbedtls_dir / "tf-psa-crypto" / "platform")
    ]

    for src_path in sources:
        if src_path.exists():
            obj_path = obj_dir / f"{src_path.stem}.o"
            cmd = [cc] + flags + ["-c", str(src_path), "-o", str(obj_path)]
            run_cmd(cmd)
            obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[MBEDTLS] Created {target_lib}")
    return target_lib

def build_curl(cc, ar, rebuild=False):
    """Compiles curl 8.21.0 into build/lib/libcurl.a and copies headers."""
    target_lib = LIB_DIR / "libcurl.a"
    curl_dir = EXTERN_DIR / "curl-8.21.0"
    lib_dir = curl_dir / "lib"
    if not curl_dir.exists():
        raise FileNotFoundError(f"curl source directory not found: {curl_dir}")

    if IS_POSIX:
        # The static curl build is Windows-tuned (config-win32.h,
        # system_win32.c, schannel TLS). On POSIX hosts the system libcurl
        # (dev package) is used instead and its headers are NOT staged here so
        # the native system headers stay in charge.
        print("[CURL] Skipped on this platform (uses system libcurl).")
        return None

    # Copy headers
    curl_inc_dst = INCLUDE_DIR / "curl"
    curl_inc_dst.mkdir(parents=True, exist_ok=True)
    for h in (curl_dir / "include" / "curl").glob("*.h"):
        shutil.copy2(h, curl_inc_dst / h.name)

    # Prepare curl_config.h
    cfg_h = lib_dir / "curl_config.h"
    if not cfg_h.exists() or rebuild:
        if (lib_dir / "config-win32.h").exists():
            shutil.copy2(lib_dir / "config-win32.h", cfg_h)

    if target_lib.exists() and not rebuild:
        print(f"[CURL] {target_lib.name} is up to date.")
        return target_lib

    print("[CURL] Compiling curl-8.21.0...")
    sources = [
        "altsvc.c", "asyn-base.c", "asyn-thrdd.c", "bufq.c", "bufref.c", "cf-dns.c",
        "cf-h1-proxy.c", "cf-haproxy.c", "cf-https-connect.c", "cf-ip-happy.c", "cf-recvbuf.c", "cf-setup.c",
        "cf-socket.c", "cfilters.c", "conncache.c", "connect.c", "content_encoding.c",
        "cookie.c", "creds.c", "cshutdn.c", "curl_addrinfo.c", "curl_endian.c",
        "curl_fnmatch.c", "curl_fopen.c", "curl_get_line.c", "curl_gethostname.c",
        "curl_memrchr.c", "curl_range.c", "curl_sasl.c", "curl_sha512_256.c", "curl_share.c", "curl_threads.c",
        "curl_trc.c", "cw-out.c", "cw-pause.c", "dnscache.c", "doh.c", "dynhds.c",
        "easy.c", "easygetopt.c", "easyoptions.c", "escape.c", "fake_addrinfo.c",
        "file.c", "fileinfo.c", "formdata.c", "getenv.c", "getinfo.c", "hash.c",
        "headers.c", "hmac.c", "hostip.c", "hostip4.c", "hostip6.c", "hsts.c",
        "http.c", "http1.c", "http_aws_sigv4.c", "http_chunks.c", "http_digest.c",
        "http_proxy.c", "httpsrr.c", "idn.c", "if2ip.c", "llist.c", "md5.c", "memdebug.c", "mime.c",
        "mprintf.c", "multi.c", "multi_ev.c", "multi_ntfy.c", "netrc.c", "parsedate.c",
        "peer.c", "progress.c", "protocol.c", "proxy.c", "rand.c", "ratelimit.c", "request.c", "select.c",
        "sendf.c", "setopt.c", "sha256.c", "slist.c", "socketpair.c", "socks.c",
        "splay.c", "strcase.c", "strequal.c", "strerror.c", "system_win32.c",
        "thrdpool.c", "thrdqueue.c", "transfer.c", "uint-bset.c", "uint-hash.c",
        "uint-spbset.c", "uint-table.c", "url.c", "urlapi.c", "version.c", "ws.c"
    ]
    obj_files = []
    obj_dir = BUILD_DIR / "obj_curl"
    obj_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-O2", "-DBUILDING_LIBCURL", "-DCURL_STATICLIB", "-DHTTP_ONLY",
        "-DUSE_WIN32_LARGE_FILES", "-DHAVE_CONFIG_H",
        "-Wno-incompatible-pointer-types",
        "-Wno-implicit-function-declaration",
        "-I" + str(curl_dir / "include"),
        "-I" + str(lib_dir),
        "-I" + str(curl_dir)
    ]

    for src in sources:
        src_path = lib_dir / src
        if src_path.exists():
            obj_path = obj_dir / f"{src_path.stem}.o"
            cmd = [cc] + flags + ["-c", str(src_path), "-o", str(obj_path)]
            run_cmd(cmd)
            obj_files.append(str(obj_path))

    # Also compile curlx, vauth, vtls, and vquic utility sources
    for subdir in ["curlx", "vauth", "vtls", "vquic"]:
        sub_path = lib_dir / subdir
        if sub_path.exists():
            for src_path in sub_path.glob("*.c"):
                # Skip third party TLS/QUIC wrappers not built
                if subdir == "vtls" and src_path.stem in ["openssl", "rustls", "gtls", "wolfssl", "mbedtls", "apple"]:
                    continue
                if subdir == "vquic" and src_path.stem in ["cf-ngtcp2", "cf-ngtcp2-cmn", "cf-ngtcp2-proxy", "cf-quiche"]:
                    continue
                obj_path = obj_dir / f"{subdir}_{src_path.stem}.o"
                cmd = [cc] + flags + ["-c", str(src_path), "-o", str(obj_path)]
                run_cmd(cmd)
                obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[CURL] Created {target_lib}")
    return target_lib

def build_microhttpd(cc, ar, rebuild=False):
    """Compiles libmicrohttpd 1.0.1 into build/lib/libmicrohttpd.a and copies headers."""
    target_lib = LIB_DIR / "libmicrohttpd.a"
    mhd_dir = EXTERN_DIR / "libmicrohttpd-1.0.1"
    src_dir = mhd_dir / "src" / "microhttpd"
    if not mhd_dir.exists():
        raise FileNotFoundError(f"libmicrohttpd source directory not found: {mhd_dir}")

    if IS_POSIX:
        # The bundled 1.0.1 header mixes POSIX and <winsock2.h> includes and
        # cannot compile on POSIX hosts; use the system libmicrohttpd (dev
        # package) and its native headers there.
        print("[MICROHTTPD] Skipped on this platform (uses system libmicrohttpd).")
        return None

    # Prepare MHD_config.h
    cfg_h = mhd_dir / "MHD_config.h"
    if not cfg_h.exists() or rebuild:
        w32_cfg = mhd_dir / "w32" / "common" / "MHD_config.h"
        if w32_cfg.exists():
            content = w32_cfg.read_text(encoding="utf-8")
            content = content.replace("#define _MHD_static_inline static __forceinline", "#define _MHD_static_inline static inline")
            cfg_h.write_text(content, encoding="utf-8")
            (mhd_dir / "src" / "include" / "MHD_config.h").write_text(content, encoding="utf-8")

    # Copy headers
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mhd_dir / "src" / "include" / "microhttpd.h", INCLUDE_DIR / "microhttpd.h")

    if target_lib.exists() and not rebuild:
        print(f"[MICROHTTPD] {target_lib.name} is up to date.")
        return target_lib

    print("[MICROHTTPD] Compiling libmicrohttpd-1.0.1...")
    sources = [
        "basicauth.c", "connection.c", "daemon.c", "digestauth.c", "gen_auth.c",
        "internal.c", "memorypool.c", "mhd_compat.c", "mhd_itc.c", "mhd_mono_clock.c",
        "mhd_panic.c", "mhd_send.c", "mhd_sockets.c", "mhd_str.c", "mhd_threads.c",
        "postprocessor.c", "reason_phrase.c", "response.c", "sha256.c",
        "sysfdsetsize.c", "tsearch.c"
    ]
    obj_files = []
    obj_dir = BUILD_DIR / "obj_microhttpd"
    obj_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-O2", "-DMHD_W32LIB", "-D_REENTRANT",
        "-Wno-incompatible-pointer-types",
        "-Wno-implicit-function-declaration",
        "-I" + str(mhd_dir / "src" / "include"),
        "-I" + str(src_dir),
        "-I" + str(mhd_dir)
    ]

    for src in sources:
        src_path = src_dir / src
        if src_path.exists():
            obj_path = obj_dir / f"{src_path.stem}.o"
            cmd = [cc] + flags + ["-c", str(src_path), "-o", str(obj_path)]
            run_cmd(cmd)
            obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[MICROHTTPD] Created {target_lib}")
    return target_lib

def build_sqlite3(cc, ar, rebuild=False):
    """Compiles SQLite3 (amalgamation) into build/lib/libsqlite3.a and copies headers."""
    target_lib = LIB_DIR / "libsqlite3.a"
    src_dir = EXTERN_DIR / "sqlite-autoconf-3530400"
    if not src_dir.exists():
        raise FileNotFoundError(f"sqlite3 source directory not found: {src_dir}")
    if not (src_dir / "sqlite3.c").exists():
        raise FileNotFoundError(f"sqlite3 amalgamation not found in {src_dir}")

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_dir / "sqlite3.h", INCLUDE_DIR / "sqlite3.h")
    if (src_dir / "sqlite3ext.h").exists():
        shutil.copy2(src_dir / "sqlite3ext.h", INCLUDE_DIR / "sqlite3ext.h")

    if target_lib.exists() and not rebuild:
        print(f"[SQLITE3] {target_lib.name} is up to date.")
        return target_lib

    target_lib.unlink(missing_ok=True)
    print("[SQLITE3] Compiling SQLite3 amalgamation...")
    obj_dir = BUILD_DIR / "obj_sqlite3"
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj_path = obj_dir / "sqlite3.o"
    flags = [
        "-O2",
        "-DSQLITE_THREADSAFE=0",
        "-DSQLITE_OMIT_LOAD_EXTENSION",
        "-DSQLITE_ENABLE_FTS5",
        "-Wno-unused-but-set-variable",
        "-I" + str(src_dir)
    ]
    cmd = [cc] + flags + ["-c", str(src_dir / "sqlite3.c"), "-o", str(obj_path)]
    run_cmd(cmd)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib), str(obj_path)])
    print(f"[SQLITE3] Created {target_lib}")
    return target_lib


def _first_existing(*paths):
    for p in paths:
        if p and p.exists():
            return p
    return None


def _cmake_static_lib(label, src_dir, lib_name, build_sub, extra_cmake, target=None, rebuild=False):
    """Generic tolerant CMake static build following repo conventions."""
    target_lib = LIB_DIR / lib_name
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    if target_lib.exists() and not rebuild:
        print(f"[{label}] {target_lib.name} is up to date.")
        return target_lib
    target_lib.unlink(missing_ok=True)
    print(f"[{label}] Building {src_dir.name} with CMake...")
    bd = BUILD_DIR / build_sub
    bd.mkdir(parents=True, exist_ok=True)
    cc = shutil.which("gcc") or "gcc"
    cfg = ["cmake", "-S", str(src_dir), "-B", str(bd),
           "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_C_COMPILER=" + cc]
    cfg += _cmake_generator()
    cfg += list(extra_cmake)
    try:
        run_cmd(cfg)
        tgt = ["--target", target] if target else []
        run_cmd(["cmake", "--build", str(bd), "--config", "Release", "-j", "4"] + tgt)
        found = [x for x in bd.rglob(lib_name)] or [x for x in bd.rglob("*.a") if x.name == lib_name]
        if not found:
            raise FileNotFoundError(f"{lib_name} not produced")
        shutil.copy2(found[0], target_lib)
        print(f"[{label}] Created {target_lib}")
        return target_lib
    except Exception as e:
        print(f"[{label}] build not feasible on this toolchain, skipping: {str(e)[-240:]}", file=sys.stderr)
        return None


def _stage_libzip_headers(src: Path) -> None:
    """Copies zip.h and the CMake-generated zipconf.h into build/include.

    zipconf.h is produced by libzip's CMake configure step, so on a fresh
    checkout it only exists after the build directory has been generated.
    """
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    zip_h = src / "lib" / "zip.h"
    if zip_h.exists():
        shutil.copy2(zip_h, INCLUDE_DIR / "zip.h")
    zcand = list((BUILD_DIR / "libzip_cmake").rglob("zipconf.h"))
    if not zcand:
        # Archive may already be built while the cmake dir was cleaned; a plain
        # configure regenerates zipconf.h without recompiling anything.
        try:
            cmake_cfg = ["cmake", "-S", str(src), "-B", str(BUILD_DIR / "libzip_cmake"),
                         "-DCMAKE_BUILD_TYPE=Release", "-DENABLE_BZIP2=OFF",
                         "-DENABLE_LZMA=OFF", "-DENABLE_ZSTD=OFF", "-DBUILD_SHARED_LIBS=OFF",
                         "-DBUILD_TOOLS=OFF", "-DBUILD_REGRESS=OFF", "-DBUILD_DOC=OFF",
                         "-DZLIB_INCLUDE_DIR=" + str(INCLUDE_DIR),
                         "-DZLIB_LIBRARY=" + str(LIB_DIR / "libz.a")]
            cmake_cfg += _cmake_generator()
            subprocess.run(cmake_cfg, capture_output=True, text=True)
            zcand = list((BUILD_DIR / "libzip_cmake").rglob("zipconf.h"))
        except Exception:
            zcand = []
    if zcand:
        shutil.copy2(zcand[0], INCLUDE_DIR / "zipconf.h")


def build_libzip(cc, ar, rebuild=False):
    src = EXTERN_DIR / "libzip-1.11.3"
    if not src.exists():
        raise FileNotFoundError(f"libzip source not found: {src}")
    if (LIB_DIR / "libzip.a").exists() and not rebuild:
        _stage_libzip_headers(src)
        print("[LIBZIP] libzip.a is up to date.")
        return LIB_DIR / "libzip.a"
    flags = ["-DENABLE_BZIP2=OFF", "-DENABLE_LZMA=OFF", "-DENABLE_ZSTD=OFF",
             "-DBUILD_SHARED_LIBS=OFF", "-DBUILD_TOOLS=OFF", "-DBUILD_REGRESS=OFF",
             "-DBUILD_DOC=OFF",
             "-DZLIB_INCLUDE_DIR=" + str(INCLUDE_DIR),
             "-DZLIB_LIBRARY=" + str(LIB_DIR / "libz.a")]
    res = _cmake_static_lib("LIBZIP", src, "libzip.a", "libzip_cmake", flags, target="zip", rebuild=rebuild)
    _stage_libzip_headers(src)
    return res


def build_libexpat(cc, ar, rebuild=False):
    src = EXTERN_DIR / "expat-2.6.4"
    if not src.exists():
        raise FileNotFoundError(f"expat source not found: {src}")
    if (LIB_DIR / "libexpat.a").exists() and not rebuild:
        for h in ("expat.h", "expat_external.h"):
            hp = src / "lib" / h
            if hp.exists():
                shutil.copy2(hp, INCLUDE_DIR / h)
        print("[LIBEXPAT] libexpat.a is up to date.")
        return LIB_DIR / "libexpat.a"
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    flags = ["-DEXPAT_BUILD_TOOLS=OFF", "-DEXPAT_BUILD_EXAMPLES=OFF", "-DEXPAT_BUILD_TESTS=OFF",
             "-DEXPAT_SHARED_LIBS=OFF"]
    res = _cmake_static_lib("LIBEXPAT", src, "libexpat.a", "expat_cmake", flags, target="expat", rebuild=rebuild)
    for h in ("expat.h", "expat_external.h"):
        hp = src / "lib" / h
        if hp.exists():
            shutil.copy2(hp, INCLUDE_DIR / h)
    return res


def build_xlsxio(cc, ar, rebuild=False):
    """Compiles xlsxio read/write static libs from its sources (needs libzip)."""
    src = EXTERN_DIR / "xlsxio-0.2.36"
    if not src.exists():
        raise FileNotFoundError(f"xlsxio source not found: {src}")
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    for h in ("xlsxio_read.h", "xlsxio_write.h", "xlsxio_version.h"):
        hp = src / "include" / h
        if hp.exists():
            shutil.copy2(hp, INCLUDE_DIR / h)
    done = all((LIB_DIR / n).exists() for n in ("libxlsxio_read.a", "libxlsxio_write.a"))
    if done and not rebuild:
        print("[XLSXIO] libxlsxio_*.a are up to date.")
        return LIB_DIR / "libxlsxio_read.a"
    libdir = src / "lib"
    objdir = BUILD_DIR / "obj_xlsxio_lib"
    objdir.mkdir(parents=True, exist_ok=True)
    inc = ["-I" + str(src / "include"), "-I" + str(INCLUDE_DIR)]
    objs = []
    for fn in ("xlsxio_read.c", "xlsxio_read_sharedstrings.c", "xlsxio_write.c"):
        o = objdir / (Path(fn).stem + ".o")
        cmd = [cc, "-O2", "-DSTATIC"] + inc + ["-c", str(libdir / fn), "-o", str(o)]
        run_cmd(cmd)
        objs.append((fn, str(o)))
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    read_objs = [o for fn, o in objs if fn.startswith("xlsxio_read")]
    write_objs = [o for fn, o in objs if fn.startswith("xlsxio_write")]
    for name, ol in [("libxlsxio_read.a", read_objs), ("libxlsxio_write.a", write_objs)]:
        (LIB_DIR / name).unlink(missing_ok=True)
        run_cmd([ar, "rcs", str(LIB_DIR / name)] + ol)
        print(f"[XLSXIO] Created {name}")
    return LIB_DIR / "libxlsxio_read.a"


def build_libyaml(cc, ar, rebuild=False):
    """Compiles libyaml 0.2.5 directly (broken upstream CMake; no autotools)."""
    target_lib = LIB_DIR / "libyaml.a"
    src_dir = EXTERN_DIR / "yaml-0.2.5"
    if not src_dir.exists():
        raise FileNotFoundError(f"libyaml source not found: {src_dir}")
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    if (src_dir / "include" / "yaml.h").exists():
        shutil.copy2(src_dir / "include" / "yaml.h", INCLUDE_DIR / "yaml.h")
    if target_lib.exists() and not rebuild:
        print(f"[LIBYAML] {target_lib.name} is up to date.")
        return target_lib
    target_lib.unlink(missing_ok=True)
    cfg = INCLUDE_DIR / "config.h"
    cfg.write_text(
        "#define HAVE_STDINT_H 1\n#define HAVE_STRING_H 1\n#define HAVE_STRINGS_H 1\n"
        "#define HAVE_STDLIB_H 1\n#define HAVE_MEMORY_H 1\n"
        '#define YAML_VERSION_STRING "0.2.5"\n#define YAML_VERSION_MAJOR 0\n'
        "#define YAML_VERSION_MINOR 2\n#define YAML_VERSION_PATCH 5\n",
        encoding="utf-8")
    print("[LIBYAML] Compiling libyaml sources...")
    obj_dir = BUILD_DIR / "obj_yaml"
    obj_dir.mkdir(parents=True, exist_ok=True)
    incs = [str(src_dir / "include"), str(src_dir / "src"), str(INCLUDE_DIR)]
    objs = []
    for fn in ("api.c","dumper.c","emitter.c","loader.c","parser.c","reader.c","scanner.c","writer.c"):
        o = obj_dir / (fn[:-2] + ".o")
        run_cmd([cc, "-O2", "-DHAVE_CONFIG_H"] + [f"-I{x}" for x in incs] + ["-c", str(src_dir / "src" / fn), "-o", str(o)])
        objs.append(str(o))
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + objs)
    print(f"[LIBYAML] Created {target_lib}")
    return target_lib


def build_libcyaml(cc, ar, rebuild=False):
    """Compiles libcyaml 1.4.2 directly against libyaml."""
    target_lib = LIB_DIR / "libcyaml.a"
    src_dir = EXTERN_DIR / "libcyaml-1.4.2"
    if not src_dir.exists():
        raise FileNotFoundError(f"libcyaml source not found: {src_dir}")
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    cy_inc = INCLUDE_DIR / "cyaml"
    cy_inc.mkdir(parents=True, exist_ok=True)
    if (src_dir / "include" / "cyaml" / "cyaml.h").exists():
        shutil.copy2(src_dir / "include" / "cyaml" / "cyaml.h", cy_inc / "cyaml.h")
    if target_lib.exists() and not rebuild:
        print(f"[LIBCYAML] {target_lib.name} is up to date.")
        return target_lib
    target_lib.unlink(missing_ok=True)
    print("[LIBCYAML] Compiling libcyaml sources...")
    obj_dir = BUILD_DIR / "obj_cyaml"
    obj_dir.mkdir(parents=True, exist_ok=True)
    incs = [str(src_dir / "include"), str(src_dir / "src"), str(INCLUDE_DIR)]
    objs = []
    for p in sorted((src_dir / "src").glob("*.c")):
        o = obj_dir / (p.stem + ".o")
        cmd = [cc, "-O2", "-DVERSION_MAJOR=1", "-DVERSION_MINOR=4", "-DVERSION_PATCH=2",
               "-DVERSION_DEVEL=0"] + [f"-I{x}" for x in incs] + ["-c", str(p), "-o", str(o)]
        run_cmd(cmd)
        objs.append(str(o))
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + objs)
    print(f"[LIBCYAML] Created {target_lib}")
    return target_lib


def build_libuv(cc, ar, rebuild=False):
    """Builds libuv 1.52.1 with CMake into build/lib/libuv.a and copies headers."""
    target_lib = LIB_DIR / "libuv.a"
    src_dir = EXTERN_DIR / "libuv-1.52.1"
    if not src_dir.exists():
        raise FileNotFoundError(f"libuv source directory not found: {src_dir}")
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    if (src_dir / "include" / "uv.h").exists():
        shutil.copy2(src_dir / "include" / "uv.h", INCLUDE_DIR / "uv.h")
        uv_inc = INCLUDE_DIR / "uv"
        uv_inc.mkdir(parents=True, exist_ok=True)
        for h in (src_dir / "include" / "uv").glob("*.h"):
            shutil.copy2(h, uv_inc / h.name)
    if target_lib.exists() and not rebuild:
        print(f"[LIBUV] {target_lib.name} is up to date.")
        return target_lib

    # MinGW/GCC 15 const-correctness fix: uv__convert_utf16_to_utf8 expects
    # `char**` but libuv passes `&(cpu_info->model)` (a `const char **`).
    # extern/ is re-downloaded on every CI run, so this patch is applied here
    # (idempotently) instead of being hand-edited in the working tree.
    util_c = src_dir / "src" / "win" / "util.c"
    if util_c.exists() and IS_WINDOWS:
        text = util_c.read_text(encoding="utf-8", errors="replace")
        already = "char **" in text or "char**" in text
        if "&(cpu_info->model));" in text and not already:
            patched = text.replace("&(cpu_info->model));", "(char **)&(cpu_info->model));")
            if patched != text:
                util_c.write_text(patched, encoding="utf-8")
                print("[LIBUV] Applied MinGW const-correctness patch to src/win/util.c")

    print("[LIBUV] Building libuv with CMake...")
    bd = BUILD_DIR / "libuv_cmake"
    bd.mkdir(parents=True, exist_ok=True)
    cmake_cfg = ["cmake", "-S", str(src_dir), "-B", str(bd),
                 "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_TESTING=OFF",
                 f"-DCMAKE_C_COMPILER={cc}"]
    cmake_cfg += _cmake_generator()
    try:
        run_cmd(cmake_cfg)
        run_cmd(["cmake", "--build", str(bd), "--config", "Release", "-j", "4"])
        lib_src = bd / "libuv.a"
        if not lib_src.exists():
            cand = list(bd.rglob("libuv.a"))
            if not cand:
                raise FileNotFoundError("libuv.a not produced by cmake build")
            lib_src = cand[0]
        LIB_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lib_src, target_lib)
        print(f"[LIBUV] Created {target_lib}")
        return target_lib
    except Exception as e:
        print(f"[LIBUV] build not feasible on this toolchain, skipping: {str(e)[-220:]}",
              file=sys.stderr)
        return None


def build_tomlc17(cc, ar, rebuild=False):
    """Compiles the tomlc17 TOML parser into build/lib/libtomlc17.a.

    Also compiles std_c/wrappers_tomlc17.c (the PenguScript-friendly shim
    pengu_toml_valid / pengu_toml_valid_file) into the same archive and
    stages its companion header std_c/pengu_tomlc17.h to build/include/, so
    `include "pengu_tomlc17.h"` resolves and -ltomlc17 alone provides the
    shim symbols.
    """
    target_lib = LIB_DIR / "libtomlc17.a"
    src_dir = EXTERN_DIR / "tomlc17-R260821" / "src"
    if not src_dir.exists():
        raise FileNotFoundError(f"tomlc17 source directory not found: {src_dir}")
    shim_dir = ROOT_DIR / "std_c"
    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    if (src_dir / "tomlc17.h").exists():
        shutil.copy2(src_dir / "tomlc17.h", INCLUDE_DIR / "tomlc17.h")
    shim_c = shim_dir / "wrappers_tomlc17.c"
    shim_h = shim_dir / "pengu_tomlc17.h"
    if shim_h.exists():
        shutil.copy2(shim_h, INCLUDE_DIR / "pengu_tomlc17.h")
    if target_lib.exists() and not rebuild:
        print(f"[TOMLC17] {target_lib.name} is up to date.")
        return target_lib
    print("[TOMLC17] Compiling tomlc17...")
    obj_dir = BUILD_DIR / "obj_tomlc17"
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj_path = obj_dir / "tomlc17.o"
    flags = ["-O2", "-I" + str(src_dir), "-Wno-array-bounds", "-Wno-stringop-overflow"]
    run_cmd([cc] + flags + ["-c", str(src_dir / "tomlc17.c"), "-o", str(obj_path)])
    objs = [str(obj_path)]
    if shim_c.exists():
        shim_obj = obj_dir / "wrappers_tomlc17.o"
        run_cmd([cc, "-O2", "-I" + str(INCLUDE_DIR),
                 "-c", str(shim_c), "-o", str(shim_obj)])
        objs.append(str(shim_obj))
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + objs)
    print(f"[TOMLC17] Created {target_lib}")
    return target_lib


def _webui_platform_asset():
    """Selects the official prebuilt WebUI asset for the host platform."""
    if sys.platform.startswith("win"):
        return "webui-windows-gcc-x64.zip"
    if sys.platform.startswith("darwin"):
        return "webui-macos-clang-x64.zip"
    return "webui-linux-gcc-x64.zip"


def build_webui(cc, ar, rebuild=False):
    """Installs the official prebuilt WebUI static library (libwebui.a).

    WebUI upstream ships mingw/msvc/clang static builds as release assets; the
    in-repo C sources do not compile cleanly on mingw (they assume the MSVC
    UNICODE API set), so the release archive is fetched instead - the same
    artifact their own bindings (std/webui.d.pengu) target.

    Headers are copied to build/include/ so `include "webui.h"` resolves.
    """
    import urllib.request
    import zipfile

    if IS_POSIX and sys.platform.startswith("darwin") and platform_machine() != "x86_64":
        print("[WEBUI] Skipped: no prebuilt Apple Silicon WebUI asset (x64-only).")
        return None

    target_lib = LIB_DIR / "libwebui.a"
    tag = "2.5.0-beta.3"
    asset = _webui_platform_asset()
    stem = os.path.splitext(asset)[0]
    cache_dir = EXTERN_DIR / stem  # extracted folder name inside the zip
    inc_file = None

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    if not cache_dir.exists():
        url = f"https://github.com/webui-dev/webui/releases/download/{tag}/{asset}"
        print(f"[WEBUI] Downloading prebuilt release {asset} ...")
        req = urllib.request.Request(url, headers={"User-Agent": "PenguScript-Release-Packager/0.6.0"})
        tmp_zip = EXTERN_DIR / asset
        with urllib.request.urlopen(req, timeout=300) as resp, open(tmp_zip, "wb") as out:
            out.write(resp.read())
        with zipfile.ZipFile(tmp_zip) as zf:
            zf.extractall(EXTERN_DIR)
        tmp_zip.unlink(missing_ok=True)

    if not cache_dir.exists():
        raise FileNotFoundError(f"webui prebuilt dir not found at {cache_dir}")

    lib_src = cache_dir / "libwebui-2-static.a"
    if not lib_src.is_file():
        found = list(cache_dir.rglob("libwebui-2-static.a"))
        if not found:
            raise FileNotFoundError("libwebui-2-static.a not found in webui prebuilt package")
        lib_src = found[0]
    shutil.copy2(lib_src, target_lib)

    inc_candidates = list(cache_dir.rglob("webui.h")) + [EXTERN_DIR / "webui-2.5.0-beta.3" / "include" / "webui.h"]
    for cand in inc_candidates:
        if cand and cand.exists():
            inc_file = cand
            break
    if inc_file is None:
        raise FileNotFoundError("webui.h not found for copying to build/include")
    shutil.copy2(inc_file, INCLUDE_DIR / "webui.h")
    print(f"[WEBUI] Installed {target_lib}")
    return target_lib



def build_raylib(cc, ar, rebuild=False):
    """Compiles Raylib (PLATFORM_DESKTOP) into build/lib/libraylib.a and copies headers."""
    target_lib = LIB_DIR / "libraylib.a"
    src_dir = EXTERN_DIR / "raylib-6.0"
    if not src_dir.exists():
        raise FileNotFoundError(f"raylib source directory not found: {src_dir}")

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    raylib_inc = INCLUDE_DIR / "raylib"
    raylib_inc.mkdir(parents=True, exist_ok=True)
    # raylib.h must be found as "raylib.h"; the internal headers it pulls live
    # in the same directory (rlgl.h etc.), so expose the whole src/ header set
    # flat under include/raylib and also link raylib.h at the include root.
    src_headers = list((src_dir / "src").glob("*.h"))
    for h in src_headers:
        shutil.copy2(h, raylib_inc / h.name)
        if h.name in ("raylib.h",):
            shutil.copy2(h, INCLUDE_DIR / h.name)

    if target_lib.exists() and not rebuild:
        print(f"[RAYLIB] {target_lib.name} is up to date.")
        return target_lib

    target_lib.unlink(missing_ok=True)
    print("[RAYLIB] Compiling Raylib (desktop, OpenGL 3.3)...")
    src_root = src_dir / "src"
    obj_dir = BUILD_DIR / "obj_raylib"
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj_files = []

    flags = [
        "-O2",
        "-DPLATFORM_DESKTOP",
        "-DGRAPHICS_API_OPENGL_33",
        "-D_CRT_SECURE_NO_WARNINGS",
        "-fno-strict-aliasing",
        f"-I{src_root}",
        f"-I{src_root / 'external' / 'glfw' / 'include'}",
        f"-I{src_root / 'external' / 'glad' / 'include'}",
        f"-I{src_root / 'external' / 'miniaudio' / 'include'}" if (src_root / 'external' / 'miniaudio' / 'include').exists() else f"-I{src_root / 'external'}",
        "-Wno-implicit-function-declaration",
    ]
    if sys.platform.startswith("win"):
        flags.append("-D_GLFW_WIN32")
    elif sys.platform.startswith("linux"):
        flags.append("-D_GLFW_X11")

    sources = [
        "rcore.c", "rshapes.c", "rtextures.c", "rtext.c", "rmodels.c",
        "rutils.c", "raudio.c", "rcamera.c", "rgestures.c", "rlgl.c",
        "raymath.c",
    ]
    for src in sources:
        src_path = src_root / src
        if src_path.exists():
            obj_path = obj_dir / f"{src_path.stem}.o"
            run_cmd([cc] + flags + ["-c", str(src_path), "-o", str(obj_path)])
            obj_files.append(str(obj_path))

    # raylib ships an amalgamated GLFW driver (src/rglfw.c) that pulls every
    # needed glfw source for the current platform/backends, so build that
    # instead of manually assembling glfw's per-backend .c files.
    rglfw = src_root / "rglfw.c"
    if rglfw.exists():
        obj_path = obj_dir / "rglfw.o"
        run_cmd([cc] + flags + ["-c", str(rglfw), "-o", str(obj_path)])
        obj_files.append(str(obj_path))

    glad_candidates = [
        src_root / "external" / "glad" / "src",
        src_root / "external" / "glad",
    ]
    for glad_src_dir in glad_candidates:
        if glad_src_dir.exists():
            for src_path in glad_src_dir.glob("*.c"):
                obj_path = obj_dir / f"glad_{src_path.stem}.o"
                run_cmd([cc] + flags + ["-c", str(src_path), "-o", str(obj_path)])
                obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[RAYLIB] Created {target_lib}")
    return target_lib


SINGLE_HEADER_NAMES = [
    "imago.h", "scriptor.h", "typis.h", "pactum.h", "datastructura.h",
    "perlinum.h", "nanosvg.h", "nanosvgrast.h",
    # Extra vendored single-header / dialog libraries with curated bindings:
    "xxhash.h", "uuid.h", "minicoro.h", "miniaudio.h", "raygui.h",
    "rlights.h", "tinyfiledialogs.h", "tinyfd_moredialogs.h",
]


# (source file under std_c/, object name, extra C flags or None)
# Each implementation unit is compiled to its OWN object file so the archive
# stays independently linkable: a program that only uses xxhash must not be
# forced to resolve raygui's raylib references (or uuid's BCrypt references).
_PENGU_STB_SOURCES = [
    ("wrappers_stb.c", "wrappers_stb.o", None),
    ("wrappers_xxhash.c", "wrappers_xxhash.o", None),
    ("wrappers_uuid.c", "wrappers_uuid.o", None),
    ("wrappers_minicoro.c", "wrappers_minicoro.o", None),
    ("wrappers_raygui.c", "wrappers_raygui.o", None),
    # Real .c implementations (tinyfiledialogs + tinyfd_moredialogs). Note:
    # tinyfd_moredialogs.c only defines symbols on non-Windows platforms, so
    # its object is empty on Windows but required for cross-platform parity.
    ("tinyfiledialogs.c", "tinyfiledialogs.o", None),
    ("tinyfd_moredialogs.c", "tinyfd_moredialogs.o", None),
]


def build_pengu_stb(cc, ar, rebuild=False):
    """Compiles the std_c implementation wrappers into build/lib/libpengu_stb.a.

    The archive carries the implementation units of the Latin-renamed STB
    single-header libraries (imago/scriptor/typis/pactum/datastructura/
    perlinum), nanosvg/nanosvgrast, and the extra curated libraries with
    std/*.d.pengu bindings: xxhash (std/xxhash), uuid (std/uuid), minicoro
    (std/minicoro), raygui (usable with std/raylib), and the tinyfiledialogs
    dialog implementations (std/fenestra). miniaudio and rlights are NOT
    compiled here on purpose: miniaudio's implementation needs an audio
    backend and rlights needs raylib + OpenGL at runtime (see the header
    comments of std/miniaudio.d.pengu and std/rlights.d.pengu).

    Headers are staged in build/include/ so `include "xxhash.h"` etc. resolve
    for project builds.
    """
    target_lib = LIB_DIR / "libpengu_stb.a"
    std_c_dir = ROOT_DIR / "std_c"
    sources = [std_c_dir / name for name, _, _ in _PENGU_STB_SOURCES]
    if not all(s.exists() for s in sources):
        missing = [str(s) for s in sources if not s.exists()]
        raise FileNotFoundError(f"single-header wrapper source missing: {missing}")

    INCLUDE_DIR.mkdir(parents=True, exist_ok=True)
    for name in SINGLE_HEADER_NAMES:
        h = std_c_dir / name
        if h.exists():
            shutil.copy2(h, INCLUDE_DIR / name)

    newest_src = max(s.stat().st_mtime for s in sources)
    if target_lib.exists() and not rebuild:
        if target_lib.stat().st_mtime >= newest_src:
            print(f"[PENGU_STB] {target_lib.name} is up to date.")
            return target_lib

    target_lib.unlink(missing_ok=True)
    print("[PENGU_STB] Compiling single-header wrappers...")
    obj_dir = BUILD_DIR / "obj_stb"
    obj_dir.mkdir(parents=True, exist_ok=True)
    base_flags = [
        "-O2",
        "-Wno-unused-function",
        "-Wno-return-type",
        "-Wno-implicit-function-declaration",
        "-Wno-incompatible-pointer-types",
        "-I" + str(std_c_dir),
        "-I" + str(INCLUDE_DIR),
    ]
    obj_files = []
    for src_name, obj_name, extra_flags in _PENGU_STB_SOURCES:
        src_path = std_c_dir / src_name
        obj_path = obj_dir / obj_name
        flags = list(base_flags) + (list(extra_flags) if extra_flags else [])
        run_cmd([cc] + flags + ["-c", str(src_path), "-o", str(obj_path)])
        obj_files.append(str(obj_path))

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib)] + obj_files)
    print(f"[PENGU_STB] Created {target_lib}")
    return target_lib


def build_pengu_runtime(cc, ar, rebuild=False):
    """Compiles pengu_runtime.c into build/lib/libpengu_runtime.a."""
    target_lib = LIB_DIR / "libpengu_runtime.a"
    runtime_c = PARSER_DIR / "pengu_runtime.c"
    runtime_h = ROOT_DIR / "pengu_runtime.h"

    # Also copy pengu_runtime.h to build/include/
    shutil.copy2(runtime_h, INCLUDE_DIR / "pengu_runtime.h")

    if not runtime_c.exists():
        print("[RUNTIME] pengu_runtime.c not found yet, skipping pengu_runtime compilation.")
        return None

    if target_lib.exists() and not rebuild:
        if target_lib.stat().st_mtime >= runtime_c.stat().st_mtime:
            print(f"[RUNTIME] {target_lib.name} is up to date.")
            return target_lib

    print("[RUNTIME] Compiling pengu_runtime.c...")
    obj_dir = BUILD_DIR / "obj_runtime"
    obj_dir.mkdir(parents=True, exist_ok=True)
    obj_path = obj_dir / "pengu_runtime.o"

    flags = [
        "-O2",
        "-I" + str(ROOT_DIR),
        "-I" + str(INCLUDE_DIR),
        "-DPCRE2_STATIC",
        "-DPCRE2_CODE_UNIT_WIDTH=8",
        "-DLIBXML_STATIC",
        "-DCURL_STATICLIB",
        "-Wno-incompatible-pointer-types",
        "-Wno-implicit-function-declaration"
    ]
    # POSIX hosts use the system libxml2/libcurl/libmicrohttpd (build_runtime
    # skips their Windows-tuned static builds there), so their headers come
    # POSIX hosts use the system libxml2/libcurl/libmicrohttpd (build_runtime
    # skips their Windows-tuned static builds there), so their headers come
    # from the system include paths; libxml2 needs its pkg-config include dir,
    # and libmicrohttpd/mbedtls may live in a Homebrew prefix (Apple Silicon).
    if IS_POSIX:
        for pkg in ("libxml-2.0", "libcurl", "libmicrohttpd", "mbedtls"):
            for tok in _pkg_config_cflags(pkg):
                if tok not in flags:
                    flags.append(tok)
        # Plain clang does not search the Homebrew prefix by default.
        for brew_inc in ("/opt/homebrew/include", "/usr/local/include"):
            if os.path.isdir(brew_inc) and f"-I{brew_inc}" not in flags:
                flags.append(f"-I{brew_inc}")
    cmd = [cc] + flags + ["-c", str(runtime_c), "-o", str(obj_path)]
    run_cmd(cmd)

    LIB_DIR.mkdir(parents=True, exist_ok=True)
    run_cmd([ar, "rcs", str(target_lib), str(obj_path)])
    print(f"[RUNTIME] Created {target_lib}")
    return target_lib

def main():
    parser = argparse.ArgumentParser(description="Build PenguScript static runtime and dependencies.")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of all libraries.")
    args = parser.parse_args()

    # Automatically ensure external dependencies are downloaded and extracted
    from extern_manifest import download_and_extract_externs
    download_and_extract_externs(EXTERN_DIR)

    cc, ar = get_toolchain()
    print(f"=== Building PenguScript Runtime (CC: {cc}, AR: {ar}) ===")

    built = []

    # On POSIX only these genuinely optional, windowing/desktop-dependent
    # builds may fail without aborting the whole run. Everything else (the C
    # runtime, std wrappers and the core static libraries) is required: a
    # failure there raises loudly so CI reports the real error instead of
    # silently producing a runtime-less build.
    POSIX_BEST_EFFORT = {"WEBUI", "RAYLIB"}

    def _build(label, fn, *a, **kw):
        """Runs one builder; optional POSIX-only builds degrade to a warning."""
        try:
            result = fn(*a, **kw)
            if result is not None:
                built.append(label)
        except Exception as e:  # noqa: BLE001 - optional platform builds must not abort
            if IS_POSIX and label in POSIX_BEST_EFFORT:
                print(f"[{label}] skipped (best-effort on this platform): {str(e)[-200:]}", file=sys.stderr)
            else:
                raise

    _build("ZLIB", build_zlib, cc, ar, rebuild=args.rebuild)
    _build("PCRE2", build_pcre2, cc, ar, rebuild=args.rebuild)
    _build("LIBXML2", build_libxml2, cc, ar, rebuild=args.rebuild)
    _build("MBEDTLS", build_mbedtls, cc, ar, rebuild=args.rebuild)
    _build("CURL", build_curl, cc, ar, rebuild=args.rebuild)
    _build("MICROHTTPD", build_microhttpd, cc, ar, rebuild=args.rebuild)
    _build("SQLITE3", build_sqlite3, cc, ar, rebuild=args.rebuild)
    _build("WEBUI", build_webui, cc, ar, rebuild=args.rebuild)
    _build("RAYLIB", build_raylib, cc, ar, rebuild=args.rebuild)
    _build("LIBUV", build_libuv, cc, ar, rebuild=args.rebuild)
    _build("LIBYAML", build_libyaml, cc, ar, rebuild=args.rebuild)
    _build("LIBCYAML", build_libcyaml, cc, ar, rebuild=args.rebuild)
    _build("LIBZIP", build_libzip, cc, ar, rebuild=args.rebuild)
    _build("LIBEXPAT", build_libexpat, cc, ar, rebuild=args.rebuild)
    _build("XLSXIO", build_xlsxio, cc, ar, rebuild=args.rebuild)
    _build("TOMLC17", build_tomlc17, cc, ar, rebuild=args.rebuild)
    _build("PENGU_STB", build_pengu_stb, cc, ar, rebuild=args.rebuild)
    _build("RUNTIME", build_pengu_runtime, cc, ar, rebuild=args.rebuild)

    print(f"=== Runtime build finished. Built: {', '.join(built) or '(none)'} ===")

if __name__ == "__main__":
    main()
