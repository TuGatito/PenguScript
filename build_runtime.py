#!/usr/bin/env python3
"""build_runtime.py - Automated compilation of PenguScript runtime and external dependencies.

Compiles:
  - zlib 1.3.2 -> build/lib/libz.a
  - PCRE2 10.47 -> build/lib/libpcre2-8.a
  - libxml2 2.9.0 -> build/lib/libxml2.a
  - mbedtls 4.2.0 (crypto) -> build/lib/libmbedcrypto.a
  - curl 8.21.0 -> build/lib/libcurl.a
  - libmicrohttpd 1.0.1 -> build/lib/libmicrohttpd.a
  - pengu_runtime.c -> build/lib/libpengu_runtime.a

Headers are copied into build/include/.
"""

import os
import sys
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

    build_zlib(cc, ar, rebuild=args.rebuild)
    build_pcre2(cc, ar, rebuild=args.rebuild)
    build_libxml2(cc, ar, rebuild=args.rebuild)
    build_mbedtls(cc, ar, rebuild=args.rebuild)
    build_curl(cc, ar, rebuild=args.rebuild)
    build_microhttpd(cc, ar, rebuild=args.rebuild)
    build_pengu_runtime(cc, ar, rebuild=args.rebuild)

    print("=== Runtime and Dependencies Built Successfully! ===")

if __name__ == "__main__":
    main()
