#!/usr/bin/env python3
"""tests/test_ffi_libs.py - C-FFI / external-library integration tests.

Consolidates the C-level integration coverage that previously lived in the
previous, removed suite:

  test_runtime_h.py          C runtime header API contract
  test_runtime_libs.py       runtime + PCRE2 / libxml2 / curl / libuv deps
  test_std_c_libs.py         single-header / std_c wrappers (xxhash, uuid,
                             minicoro, imago, ...)
  test_integrated_libs.py    sqlite3 binding smoke, webui + raylib link-only
  test_extern_g5.py          xlsxio roundtrip, std.xlsx writer, tomlum TOML
                             validity, std.yaml version
  test_archivum_tree.py      std.archivum copy_tree / list_files_recursive
  test_feature_pengu_coroutine.py  Pengu weave as a minicoro coroutine body

Every runnable test degrades gracefully: it is guarded with the matching
``requires_lib`` / ``requires_runtime`` skip marker (plus a member-level guard
where a specific object inside an archive is required) so the suite stays green
on a machine where build_runtime.py has not produced the corresponding
archive. GUI libraries (webui / raylib / tinyfiledialogs) are only exercised
at compile/link level - nothing here opens a window or an interactive dialog.
"""

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    compile_run,
    have_lib,
    have_tool,
    requires_cc,
    requires_lib,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)

CC = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")

# ---------------------------------------------------------------------------
# Archives / link lines
# ---------------------------------------------------------------------------

# Core libs the Pengu runtime is linked against (see conftest.runtime_link_flags).
# xlsxio / tomlc17 / yaml / sqlite3 / pengu_stb are pulled in per-test.
IS_NT = os.name == "nt"

# Windows-only system libraries (bcrypt/comdlg32/ole32/... do not exist on
# POSIX hosts; those code paths are #ifdef'd out of the vendored headers).
XLSX_LIBS = ["-lxlsxio_write", "-lxlsxio_read", "-lzip", "-lz", "-lexpat"]
if IS_NT:
    XLSX_LIBS += ["-lbcrypt"]
WEBUI_LIBS = ["-lwebui", "-lole32", "-luuid", "-lstdc++", "-lws2_32"] if IS_NT else []
RAYLIB_LIBS = ["-lraylib", "-lopengl32", "-lgdi32", "-lwinmm"] if IS_NT else []
TINYFD_LIBS = ["-lcomdlg32", "-lole32", "-lgdi32", "-luser32"] if IS_NT else []

XLSX_OK = all(have_lib(n) for n in ("xlsxio_read", "xlsxio_write", "zip", "z", "expat"))

STB_LIB = BUILD_LIB / "libpengu_stb.a"


def _ar_members(lib_path: Path):
    """Object member names inside an archive (or [] when unavailable)."""
    if not Path(lib_path).is_file():
        return []
    try:
        res = subprocess.run(["ar", "t", str(lib_path)], capture_output=True, text=True)
    except OSError:
        return []
    return res.stdout.split() if res.returncode == 0 else []


STB_MEMBERS = _ar_members(STB_LIB)
TOMLC17_MEMBERS = _ar_members(BUILD_LIB / "libtomlc17.a")


def requires_stb_member(member: str):
    """Skip marker: libpengu_stb.a exists but lacks the member object."""
    return pytest.mark.skipif(
        member not in STB_MEMBERS,
        reason=f"{STB_LIB.name} lacks {member} (run build_runtime.py)",
    )


def requires_tomlc17_shim():
    """Skip marker: tomlc17 shim object missing from libtomlc17.a."""
    return pytest.mark.skipif(
        "wrappers_tomlc17.o" not in TOMLC17_MEMBERS,
        reason="wrappers_tomlc17.o not in libtomlc17.a (run build_runtime.py)",
    )


# ---------------------------------------------------------------------------
# Semantic-check helper (parser + checker, std imports resolved against REPO)
# ---------------------------------------------------------------------------


def _semantic_check(relpath: str):
    """Parses + checks one std module; raises AssertionError on any error."""
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    path = REPO / "std" / relpath
    code = path.read_text(encoding="utf-8")
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(base_dir=str(REPO))
    checker.check(tree, source=code, filename=str(path))
    assert not checker.errors, [str(e) for e in checker.errors]


def _expect_stdout(res: subprocess.CompletedProcess, *markers: str):
    for marker in markers:
        assert marker in res.stdout, f"missing {marker!r} in output:\n{res.stdout}"


# ---------------------------------------------------------------------------
# Compile+run helpers
# ---------------------------------------------------------------------------


def _compile_run_pengu(source: str, tag: str, extra_libs=None, cwd=None,
                       static: bool = False) -> subprocess.CompletedProcess:
    """Pengu -> C -> gcc -> run (asserts compile rc == 0 and run rc == 0).

    Like conftest.compile_run but lets callers add ``-DSTATIC`` (the xlsxio
    stack needs it on Windows) via ``static=True``.
    """
    from pengu_project import PenguBuilder, ProjectConfig

    d = Path(tempfile.mkdtemp(prefix=f"pengu_ffi_{tag}_", dir=BUILD_DIR))
    try:
        entry = d / f"{tag}.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

        exe = d / "bin.exe"
        cmd = [CC, str(bundle_path),
               f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}", f"-L{BUILD_LIB}"]
        if static:
            cmd.insert(1, "-DSTATIC")
        cmd += ["-Wno-error=implicit-function-declaration",
                "-Wno-error=implicit-int",
                "-Wno-error=int-conversion"]
        cmd += runtime_link_flags()
        if extra_libs:
            cmd += list(extra_libs)
        cmd += runtime_tail_flags()
        cmd += ["-o", str(exe)]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        assert res.returncode == 0, (
            f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
        )
        rr = subprocess.run([str(exe)], cwd=str(cwd or REPO),
                            capture_output=True, text=True, timeout=120)
        assert rr.returncode == 0, (
            f"Execution failed ({rr.returncode}):\n{rr.stderr}\n{rr.stdout}"
        )
        return rr
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _run_c_probe(c_source: str, tag: str, extra_libs, *,
                 extra_flags=(), link_pengu_stb: bool = True,
                 run: bool = True) -> subprocess.CompletedProcess:
    """Compiles a standalone C probe with gcc and optionally runs it.

    ``link_pengu_stb=True`` reproduces the old single-header archive probes
    (uuid / minicoro / tinyfiledialogs). GUI libraries set it to False and use
    ``run=False`` for a pure link check.
    """
    d = Path(tempfile.mkdtemp(prefix=f"pengu_ffi_c_{tag}_", dir=BUILD_DIR))
    try:
        cfile = d / f"{tag}.c"
        cfile.write_text(c_source, encoding="utf-8")
        exe = d / f"{tag}.exe"
        cmd = [CC, *extra_flags, str(cfile),
               f"-I{BUILD_INCLUDE}", f"-I{REPO / 'std_c'}", f"-L{BUILD_LIB}"]
        cmd += ["-Wno-error=implicit-function-declaration",
                "-Wno-error=implicit-int",
                "-Wno-error=int-conversion"]
        if link_pengu_stb:
            cmd += ["-lpengu_stb"]
        cmd += list(extra_libs) + runtime_tail_flags() + ["-o", str(exe)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        assert res.returncode == 0, f"C compilation failed:\n{res.stderr}\n{res.stdout}"
        if not run:
            return res
        rr = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
        assert rr.returncode == 0, (
            f"C probe failed (rc={rr.returncode}):\n{rr.stdout}\n{rr.stderr}"
        )
        return rr
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 1. C runtime header API contract  (was tests/test_runtime_h.py)
# ---------------------------------------------------------------------------


class TestRuntimeHeader:
    """pengu_runtime.h must keep the documented C surface."""

    HEADER = REPO / "pengu_runtime.h"

    def test_core_types_and_string_primitives_present(self):
        content = TestRuntimeHeader.HEADER.read_text(encoding="utf-8")
        for token in (
            "PenguList", "PenguMap", "PenguSlice", "PenguMaybe",
            "PenguResult", "PenguString", "pengu_banish",
            # Core string primitives retained in C (compiler lowering + byte access)
            "pengu_string_substring", "pengu_string_char_at",
            "pengu_string_concat", "pengu_string_equal", "pengu_string_from_cstr",
        ):
            assert token in content, f"pengu_runtime.h no longer defines {token}"

    def test_list_and_map_helpers_present(self):
        content = TestRuntimeHeader.HEADER.read_text(encoding="utf-8")
        for token in (
            "pengu_list_push_int", "pengu_list_push_string", "pengu_list_pop_int",
            "pengu_list_contains_int", "pengu_list_index_of_int",
            "pengu_map_put_string_int", "pengu_map_get_string_int",
            "pengu_map_contains_string_int", "pengu_map_remove_string_int",
        ):
            assert token in content, f"pengu_runtime.h no longer defines {token}"

    def test_migrated_utilities_removed_from_header(self):
        # String utilities moved to std/scrolls.pengu ...
        content = TestRuntimeHeader.HEADER.read_text(encoding="utf-8")
        for token in ("static inline int scrolls_len", "pengu_string_upper"):
            assert token not in content, f"{token} should live in std, not the C header"
        # ... and path handling moved to std/compass.pengu.
        for token in ("pengu_c_path_is_sep", "pengu_c_path_normalize",
                      "pengu_c_path_join", "pengu_c_path_relative_to"):
            assert token not in content, f"{token} should live in std, not the C header"


# ---------------------------------------------------------------------------
# 2. Semantic sweep over every std/*.d.pengu declaration file
# ---------------------------------------------------------------------------

STD_D_PENGU = sorted((REPO / "std").glob("*.d.pengu"))


class TestStdDeclarationsCheck:
    """Every std/*.d.pengu declaration file must parse + type-check cleanly."""

    @pytest.mark.parametrize("decl_file", STD_D_PENGU,
                             ids=[p.name for p in STD_D_PENGU])
    def test_declaration_file_checks(self, decl_file):
        _semantic_check(decl_file.name)

    def test_curated_wrapper_modules_check(self):
        # Wrapper modules (not pure .d.pengu) that pull the C bindings in.
        for rel in ("xlsx.pengu", "celeris.pengu"):
            _semantic_check(rel)


# ---------------------------------------------------------------------------
# 3. Runtime + real external deps (PCRE2 / libxml2 / libuv concurrency)
#    (was tests/test_runtime_libs.py)
# ---------------------------------------------------------------------------


class TestRuntimeDeps:
    """Compile+run against the runtime's real external libraries."""

    @requires_runtime
    def test_real_regex_and_xml_execution(self):
        """Regulus (PCRE2) regex matching + Parchment (libxml2) XML parsing."""
        src = r"""
import std.spark
import std.oracle
import std.regulus
import std.parchment

weave main into void:
    calling spark.println with "=== Testing Real Regulus & Parchment ==="

    # 1. Regulus Regex with PCRE2
    var re_m as maybe Regex is calling regulus.compile with "[a-zA-Z0-9_]+@[a-zA-Z0-9_]+\\.[a-zA-Z0-9_]+", ""
    if re_m.is_present:
        calling spark.println with "regex compiled ok"
        var re as Regex is re_m.value
        var m as maybe Match is calling re.search with "Contact us at support@penguscript.org for info"
        if m.is_present:
            var matched as Match is m.value
            calling spark.println with "matched: " + matched.matched

    # 2. Parchment XML with libxml2
    var xml_data as string is "<pengu version=\"1.0\"><wizard name=\"Merlin\"><spell>Fireball</spell></wizard></pengu>"
    var doc_m as maybe Document is calling parchment.parse_xml with xml_data
    if doc_m.is_present:
        calling spark.println with "xml parsed ok"
        var doc as Document is doc_m.value
        var root_node as Node is doc.root
        calling spark.println with "root tag: " + root_node.tag

        var wiz as maybe Node is calling parchment.find with sigil of root_node, "wizard"
        if wiz.is_present:
            var wnode as Node is wiz.value
            var attr_val as maybe string is calling parchment.attr with sigil of wnode, "name"
            if attr_val.is_present:
                calling spark.println with "wizard name: " + attr_val.value

    calling spark.println with "=== Real Libs OK ==="
"""
        res = compile_run(src, tag="real_libs")
        _expect_stdout(res,
                       "=== Testing Real Regulus & Parchment ===",
                       "regex compiled ok", "matched: support@penguscript.org",
                       "xml parsed ok", "root tag: pengu", "wizard name: Merlin",
                       "=== Real Libs OK ===")

    @requires_runtime
    def test_real_concurrency_execution(self):
        """Filum concurrency primitives: AtomicInt, Mutex, WaitGroup, sleep."""
        src = r"""
import std.spark
import std.oracle
import std.filum

weave main into void:
    calling spark.println with "=== Testing Real Filum Concurrency ==="

    # 1. AtomicInt
    var counter as AtomicInt is calling filum.atomic_int with 10
    var cur_val as int is calling counter.load
    calling spark.println with "atomic load: " + cur_val

    var added as int is calling counter.add with 5
    var new_val as int is calling counter.load
    calling spark.println with "atomic new: " + new_val

    # 2. Mutex
    var mtx as Mutex is calling filum.mutex
    calling mtx.lock
    calling spark.println with "mutex locked"
    calling mtx.unlock
    calling spark.println with "mutex unlocked"

    # 3. WaitGroup
    var wg as WaitGroup is calling filum.wait_group
    calling wg.add with 1
    calling spark.println with "wg added 1"
    calling wg.done
    calling spark.println with "wg done"
    calling wg.wait
    calling spark.println with "wg wait ok"

    # 4. Sleep
    calling filum.sleep with 10
    calling spark.println with "sleep ok"

    calling spark.println with "=== Filum OK ==="
"""
        res = compile_run(src, tag="real_filum")
        _expect_stdout(res,
                       "=== Testing Real Filum Concurrency ===",
                       "atomic load: 10", "atomic new: 15",
                       "mutex locked", "mutex unlocked",
                       "wg added 1", "wg done", "wg wait ok",
                       "sleep ok", "=== Filum OK ===")

    @requires_runtime
    def test_filum_resource_cleanup(self):
        """Every filum primitive can be disposed through its new free API."""
        src = r"""
import std.spark
import std.filum

weave main into void:
    calling spark.println with "=== Filum Cleanup ==="

    var mtx as Mutex is calling filum.mutex
    calling mtx.lock
    calling mtx.unlock
    calling mtx.free

    var wg as WaitGroup is calling filum.wait_group
    calling wg.free

    var o as Once is calling filum.once
    calling o.free

    var cv as Cond is calling filum.cond
    calling cv.free

    var atom as AtomicInt is calling filum.atomic_int with 7
    calling atom.free

    # functional wrappers (ref-taking) resolve to the same C cleanup
    var mtx2 as Mutex is calling filum.mutex
    calling filum.free_mutex with sigil of mtx2
    var wg2 as WaitGroup is calling filum.wait_group
    calling filum.free_wait_group with sigil of wg2
    var o2 as Once is calling filum.once
    calling filum.free_once with sigil of o2
    var cv2 as Cond is calling filum.cond
    calling filum.free_cond with sigil of cv2
    var atom2 as AtomicInt is calling filum.atomic_int with 1
    calling filum.free_atomic_int with sigil of atom2

    calling spark.println with "=== Filum Cleanup OK ==="
"""
        res = compile_run(src, tag="filum_free")
        _expect_stdout(res,
                       "=== Filum Cleanup ===",
                       "=== Filum Cleanup OK ===")

    @requires_runtime
    def test_regulus_parchment_resource_cleanup(self):
        """Regex / XML/HTML native resources are released via the new frees."""
        src = r"""
import std.spark
import std.oracle
import std.regulus
import std.parchment

weave main into void:
    calling spark.println with "=== Native Cleanup ==="

    # Regulus: compile, search, then release the PCRE2 code and match buffer.
    var re_m as maybe Regex is calling regulus.compile with "o+", ""
    if re_m.is_present:
        calling spark.println with "regex compiled ok"
        var re as Regex is re_m.value
        var m as maybe Match is calling re.search with "foo"
        if m.is_present:
            var matched as Match is m.value
            calling spark.println with "matched: " + matched.matched
            calling regulus.match_free with sigil of matched
        calling re.free

    # Parchment: parse XML, walk one node, then release the document.
    var xml_data as string is "<pengu version=\"1.0\"><wizard name=\"Merlin\"><spell>Fireball</spell></wizard></pengu>"
    var doc_m as maybe Document is calling parchment.parse_xml with xml_data
    if doc_m.is_present:
        calling spark.println with "xml parsed ok"
        var doc as Document is doc_m.value
        var root_node as Node is doc.root
        var wiz as maybe Node is calling parchment.find with sigil of root_node, "wizard"
        if wiz.is_present:
            var wnode as Node is wiz.value
            calling parchment.free_node with sigil of wnode
        calling parchment.free_document with sigil of doc

    calling spark.println with "=== Native Cleanup OK ==="
"""
        res = compile_run(src, tag="native_free")
        _expect_stdout(res,
                       "=== Native Cleanup ===",
                       "regex compiled ok", "matched: oo",
                       "xml parsed ok",
                       "=== Native Cleanup OK ===")


# ---------------------------------------------------------------------------
# 4. libpengu_stb single-header archive (xxhash / uuid / minicoro / stb_image
#    / tinyfiledialogs)  (was tests/test_std_c_libs.py + std_c coverage of
#    test_integrated_libs.py)
# ---------------------------------------------------------------------------


class TestStbSingleHeaderLibs:
    """Modules bundled into build/lib/libpengu_stb.a."""

    @requires_lib("pengu_stb")
    def test_all_stb_modules_import_and_compile_in_one_bundle(self):
        src = r"""import std.spark
import std.xxhash
import std.uuid
import std.minicoro
import std.miniaudio
import std.rlights
import std.celeris

weave main into int:
    var h as u64 is calling celeris.hash64 with "PenguScript", 11
    if h == 0x610DF71A00097754:
        calling spark.println with "all new modules import ok"
    else:
        return 1
    return 0
"""
        res = compile_run(src, tag="allimports", extra_libs=["-lpengu_stb"])
        _expect_stdout(res, "all new modules import ok")

    @requires_lib("pengu_stb")
    def test_xxhash_one_shot_and_streaming(self):
        src = r"""import std.spark
import std.xxhash

weave main into int:
    var e32 as u32 is calling xxhash.XXH32 with "", 0, 0
    if e32 == 0x02CC5D05:
        calling spark.println with "xxh32 vector ok"
    else:
        return 1
    var e64 as u64 is calling xxhash.XXH64 with "", 0, 0
    if e64 == 0xEF46DB3751D8E999:
        calling spark.println with "xxh64 vector ok"
    else:
        return 1
    var e3 as u64 is calling xxhash.XXH3_64bits with "", 0
    if e3 == 0x2D06800538D394C2:
        calling spark.println with "xxh3 vector ok"
    else:
        return 1
    var one as u64 is calling xxhash.XXH64 with "PenguScript", 11, 7
    var st as ref to XXH64_state_t is calling xxhash.XXH64_createState
    var r0 as int is calling xxhash.XXH64_reset with st, 7
    var r1 as int is calling xxhash.XXH64_update with st, "Pengu", 5
    var r2 as int is calling xxhash.XXH64_update with st, "Script", 6
    var dig as u64 is calling xxhash.XXH64_digest with st
    var r3 as int is calling xxhash.XXH64_freeState with st
    if r0 == 0:
        if r1 == 0:
            if r2 == 0:
                if r3 == 0:
                    if dig == one:
                        calling spark.println with "xxh64 streaming ok"
                    else:
                        return 1
    calling spark.println with "xxhash pengu smoke passed"
    return 0
"""
        res = compile_run(src, tag="xxhash", extra_libs=["-lpengu_stb"])
        _expect_stdout(res, "xxh32 vector ok", "xxh64 vector ok", "xxh3 vector ok",
                       "xxh64 streaming ok", "xxhash pengu smoke passed")

    @requires_lib("pengu_stb")
    def test_celeris_wrapper_hashes(self):
        src = r"""import std.spark
import std.celeris

weave main into int:
    var h64 as u64 is calling celeris.hash64 with "PenguScript", 11
    if h64 == 0x610DF71A00097754:
        calling spark.println with "celeris h64 ok"
    else:
        return 1
    var h3 as u64 is calling celeris.hash3_64 with "PenguScript", 11
    if h3 == 0xC5617D8EE18E0403:
        calling spark.println with "celeris h3 ok"
    else:
        return 1
    var hs as u64 is calling celeris.hash64_seeded with "PenguScript", 11, 7
    if hs == 0xD104A1CEC9DDA702:
        calling spark.println with "celeris h64 seeded ok"
    else:
        return 1
    calling spark.println with "celeris wrapper passed"
    return 0
"""
        res = compile_run(src, tag="celeris", extra_libs=["-lpengu_stb"])
        _expect_stdout(res, "celeris h64 ok", "celeris h3 ok",
                       "celeris h64 seeded ok", "celeris wrapper passed")

    @requires_lib("pengu_stb")
    def test_imago_binding_links(self):
        # std.imago (stb_image) smoke: failure_reason returns a C string, and
        # the binding declares it 'ref to frozen char' (C's 'const char*'), so
        # the local is read-only too.
        src = r"""import std.spark
import std.imago

weave main into int:
    var why as ref to frozen char is calling imago.failure_reason
    calling spark.println with "imago binding smoke passed"
    return 0
"""
        res = compile_run(src, tag="imago", extra_libs=["-lpengu_stb"])
        _expect_stdout(res, "imago binding smoke passed")

    @requires_lib("pengu_stb")
    @requires_stb_member("wrappers_uuid.o")
    @requires_cc
    def test_uuid4_generate_prints_and_parses(self):
        # uuid structs cannot be expressed in pure Pengu; C-level probe.
        c = r'''#include <stdio.h>
#include <string.h>
#include "uuid.h"
int main(void) {
    uuid u;
    memset(&u, 0, sizeof(u));
    uuid0_generate(&u);
    if (uuid_type(&u) != 0) return 1;
    uuid4_generate(&u);
    if (uuid_type(&u) != 4) return 2;
    char buf[37];
    if (uuid_to_string(&u, buf) != buf) return 3;
    buf[36] = '\0';
    printf("uuid4=%s\n", buf);
    if (strlen(buf) != 36) return 4;
    if (buf[14] != '4') return 5;
    uuid back;
    memset(&back, 0, sizeof(back));
    if (!uuid_from_string(buf, &back)) return 6;
    if (uuid_type(&back) != 4) return 7;
    printf("uuid generation ok\n");
    return 0;
}
'''
        # BCrypt (Windows RNG) only exists on Windows; POSIX uuid4 uses the
        # OS RNG directly.
        res = _run_c_probe(c, "uuid", ["-lbcrypt"] if IS_NT else [])
        _expect_stdout(res, "uuid4=", "uuid generation ok")

    @requires_lib("pengu_stb")
    @requires_stb_member("wrappers_minicoro.o")
    @requires_cc
    def test_minicoro_create_resume_yield_roundtrip(self):
        c = r'''#include <stdio.h>
#define MINICORO_IMPL
#include "minicoro.h"
static int g_stage = 0;
static void coro_entry(mco_coro* co) {
    (void)co;
    g_stage = 1;
    mco_yield(co);
    g_stage = 2;
}
int main(void) {
    mco_desc desc = mco_desc_init(coro_entry, 0);
    mco_coro* co = NULL;
    mco_result r = mco_create(&co, &desc);
    if (r != MCO_SUCCESS) return 1;
    if (mco_status(co) != MCO_SUSPENDED) return 2;
    if (mco_resume(co) != MCO_SUCCESS) return 3;
    if (g_stage != 1) return 4;
    if (mco_resume(co) != MCO_SUCCESS) return 5;
    if (g_stage != 2) return 6;
    if (mco_status(co) != MCO_DEAD) return 7;
    if (mco_destroy(co) != MCO_SUCCESS) return 8;
    printf("minicoro roundtrip ok\n");
    return 0;
}
'''
        res = _run_c_probe(c, "minicoro", [])
        _expect_stdout(res, "minicoro roundtrip ok")

    @pytest.mark.skipif(not IS_NT, reason="tinyfiledialogs links desktop GUI libs (Windows-only in CI)")
    @requires_lib("pengu_stb")
    @requires_stb_member("tinyfiledialogs.o")
    @requires_cc
    def test_tinyfd_version_prints(self):
        # Link + run that only prints the version string; never opens a dialog.
        c = r'''#include <stdio.h>
#include <string.h>
#include "tinyfiledialogs.h"
int main(void) {
    printf("tinyfd_version=%s\n", tinyfd_version);
    if (strlen(tinyfd_version) == 0) return 1;
    printf("tinyfiledialogs version ok\n");
    return 0;
}
'''
        res = _run_c_probe(c, "tinyfd", TINYFD_LIBS)
        _expect_stdout(res, "tinyfd_version=", "tinyfiledialogs version ok")


# ---------------------------------------------------------------------------
# 5. Pengu coroutine: a weave driven by the minicoro shim (libpengu_stb)
#    (was tests/test_feature_pengu_coroutine.py)
# ---------------------------------------------------------------------------


class TestPenguCoroutine:
    """A PenguScript weave used as a minicoro coroutine body."""

    @requires_lib("pengu_stb")
    @requires_stb_member("wrappers_minicoro.o")
    def test_weave_as_minicoro_body(self):
        src = r"""import std.spark

declare pengu_mco_start with body as ref to void, user_data as ref to void, stack_size as usize into ref to void
declare pengu_mco_resume with co as ref to void into void
declare pengu_mco_yield with co as ref to void into void
declare pengu_mco_destroy with co as ref to void into void

weave run_body with co as ref to void into void:
    calling spark.println with "body start"
    calling pengu_mco_yield with co
    calling spark.println with "body end"

weave main into int:
    var no_ud as ref to void is null
    var co as ref to void is calling pengu_mco_start with run_body, no_ud, 16384
    if co == null:
        calling spark.println with "coro start failed"
        return 1
    calling pengu_mco_resume with co
    calling pengu_mco_resume with co
    calling pengu_mco_destroy with co
    calling spark.println with "coroutine smoke passed"
    return 0
"""
        res = compile_run(src, tag="coro", extra_libs=["-lpengu_stb"])
        _expect_stdout(res, "body start", "body end", "coroutine smoke passed")


# ---------------------------------------------------------------------------
# 6. sqlite3 binding  (was tests/test_integrated_libs.py)
# ---------------------------------------------------------------------------


class TestSqlite3Binding:
    """std.sqlite3: in-memory open/close through the C API."""

    @requires_lib("sqlite3")
    def test_sqlite3_open_close_smoke(self):
        src = r"""import std.spark
import std.sqlite3

weave main into int:
    var db as ref to sqlite3 is null
    var rc as int is calling sqlite3.open with ":memory:", (sigil of db)
    if rc == 0:
        calling spark.println with "sqlite open ok"
        calling sqlite3.close with db
        calling spark.println with "sqlite smoke passed"
    else:
        calling spark.println with "sqlite open failed"
    return 0
"""
        res = compile_run(src, tag="sqlite3", extra_libs=["-lsqlite3"])
        _expect_stdout(res, "sqlite open ok", "sqlite smoke passed")


# ---------------------------------------------------------------------------
# 7. GUI libraries: link-only checks (never open a window)
#    (was tests/test_integrated_libs.py)
# ---------------------------------------------------------------------------


class TestWebuiLinkOnly:
    """libwebui.a links against its documented platform libraries (Windows)."""

    @pytest.mark.skipif(not IS_NT, reason="WebUI link line is Windows-specific")
    @requires_lib("webui")
    @requires_cc
    def test_webui_archive_links(self):
        c = ("#include <stdio.h>\ntypedef unsigned long long size_t;\n"
             "extern size_t webui_new_window(void);\n"
             "int main(void){ size_t w = webui_new_window(); (void)w; "
             'printf("webui link ok\\n"); return 0; }\n')
        _run_c_probe(c, "webui", WEBUI_LIBS, link_pengu_stb=False, run=False)


class TestRaylibLinkOnly:
    """libraylib.a links; a real desktop session is out of scope here."""

    @pytest.mark.skipif(not IS_NT, reason="raylib link line is Windows-specific")
    @requires_lib("raylib")
    @requires_cc
    def test_raylib_archive_links(self):
        c = ('#include <stdio.h>\nextern _Bool IsWindowReady(void);\n'
             'int main(void){ (void)IsWindowReady(); '
             'printf("raylib link ok\\n"); return 0; }\n')
        _run_c_probe(c, "raylib", RAYLIB_LIBS, link_pengu_stb=False, run=False)


# ---------------------------------------------------------------------------
# 8. xlsxio stack: C roundtrip + std.xlsx Pengu writer  (was tests/test_extern_g5.py)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not XLSX_OK,
                    reason="xlsxio stack not built (run build_runtime.py)")
class TestXlsxio:
    """libxlsxio_write / libxlsxio_read (+ libzip / libexpat / libz)."""

    @requires_cc
    def test_write_read_roundtrip(self):
        d = Path(tempfile.mkdtemp(prefix="pengu_xlsxio_", dir=BUILD_DIR))
        try:
            xlsx = (d / "probe.xlsx").as_posix()
            c = (
                '#include <stdio.h>\n#include "xlsxio_write.h"\n'
                '#include "xlsxio_read.h"\n'
                'int main(void){\n  printf("xlsxio %s\\n", '
                'xlsxiowrite_get_version_string());\n'
                f'  const char* path = "{xlsx}";\n'
                '  xlsxiowriter w = xlsxiowrite_open(path, "Sheet1");\n'
                '  if(!w){ printf("write-open failed\\n"); return 1; }\n'
                '  xlsxiowrite_next_row(w); '
                'xlsxiowrite_add_cell_string(w, "hello");\n'
                '  xlsxiowrite_close(w);\n'
                '  xlsxioreader r = xlsxioread_open(path);\n'
                '  if(!r){ printf("read-open failed\\n"); return 1; }\n'
                '  xlsxioread_close(r);\n'
                '  printf("xlsxio link+io passed\\n"); return 0;\n}\n'
            )
            res = _run_c_probe(c, "xlsxio", XLSX_LIBS,
                               extra_flags=("-DSTATIC",), link_pengu_stb=False)
            _expect_stdout(res, "xlsxio ", "xlsxio link+io passed")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_pengu_wrapper_writes_xlsx(self):
        # std.xlsx.write_sheet -> xlsxio write stack; verify the produced file
        # is a real spreadsheet (zip entries + sheet name + cell strings).
        out_dir = Path(tempfile.mkdtemp(prefix="pengu_xlsx_out_", dir=BUILD_DIR))
        try:
            xlsx = (out_dir / "pengu_written.xlsx").as_posix()
            src = r"""import std.spark
import std.xlsx
import std.xlsxio

weave main into int:
    var header as list of string is list of string
    calling header.push with "Name"
    calling header.push with "City"
    var r1 as list of string is list of string
    calling r1.push with "Ada"
    calling r1.push with "London"
    var r2 as list of string is list of string
    calling r2.push with "Grace"
    calling r2.push with "New York"
    var rows as list of list of string is list of list of string
    calling rows.push with r1
    calling rows.push with r2
    var ok as bool is calling xlsx.write_sheet with "P", "Sheet1", header, rows
    if ok:
        calling spark.println with "xlsx write_sheet ok"
    else:
        calling spark.println with "xlsx write_sheet failed"
        return 1
    calling spark.println with "xlsx pengu smoke passed"
    return 0
""".replace('"P"', f'"{xlsx}"')
            res = _compile_run_pengu(src, "xlsxwrite", XLSX_LIBS, static=True)
            _expect_stdout(res, "xlsx write_sheet ok", "xlsx pengu smoke passed")

            assert (out_dir / "pengu_written.xlsx").is_file(), \
                "pengu-written .xlsx missing"
            with zipfile.ZipFile(out_dir / "pengu_written.xlsx") as zf:
                names = zf.namelist()
                sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace")
                shared = (zf.read("xl/sharedStrings.xml").decode("utf-8", "replace")
                          if "xl/sharedStrings.xml" in names else "")
                wb = zf.read("xl/workbook.xml").decode("utf-8", "replace")
            assert "Ada" in sheet + shared
            assert "London" in sheet + shared
            assert "Sheet1" in wb
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 9. tomlum (tomlc17 shim): TOML validity  (was tests/test_extern_g5.py)
# ---------------------------------------------------------------------------


@requires_lib("tomlc17")
@requires_tomlc17_shim()
class TestTomlumBinding:
    """std.tomlum pengu_toml_valid / pengu_toml_valid_file over tomlc17."""

    def test_toml_valid_and_invalid_text(self):
        src = r"""import std.spark
import std.tomlum

weave main into int:
    var text as string is "title = \"PenguScript\"\nversion = 1"
    var ok1 as int is calling tomlum.pengu_toml_valid with (bytes of text)
    var bad as string is "title = "
    var ok2 as int is calling tomlum.pengu_toml_valid with (bytes of bad)
    if ok1 == 1:
        calling spark.println with "toml valid ok"
    else:
        calling spark.println with "toml valid failed"
        return 1
    if ok2 == 0:
        calling spark.println with "toml invalid detected ok"
    else:
        calling spark.println with "toml invalid NOT detected"
        return 1
    calling spark.println with "toml pengu smoke passed"
    return 0
"""
        res = compile_run(src, tag="tomlum", extra_libs=["-ltomlc17"])
        _expect_stdout(res, "toml valid ok", "toml invalid detected ok",
                       "toml pengu smoke passed")

    def test_toml_valid_and_invalid_file(self):
        d = Path(tempfile.mkdtemp(prefix="pengu_tomlfile_", dir=BUILD_DIR))
        try:
            good = (d / "good.toml").as_posix()
            bad = (d / "bad.toml").as_posix()
            (d / "good.toml").write_text(
                'title = "PenguScript"\nversion = 1\n', encoding="utf-8")
            (d / "bad.toml").write_text("title = \n", encoding="utf-8")
            src = r"""import std.spark
import std.tomlum

weave main into int:
    var ok1 as int is calling tomlum.pengu_toml_valid_file with "GOOD_PATH"
    var ok2 as int is calling tomlum.pengu_toml_valid_file with "BAD_PATH"
    if ok1 == 1:
        calling spark.println with "toml file valid ok"
    else:
        calling spark.println with "toml file valid failed"
        return 1
    if ok2 == 0:
        calling spark.println with "toml file invalid ok"
    else:
        calling spark.println with "toml file invalid NOT detected"
        return 1
    calling spark.println with "toml file pengu smoke passed"
    return 0
""".replace("GOOD_PATH", good).replace("BAD_PATH", bad)
            res = compile_run(src, tag="tomlfile", extra_libs=["-ltomlc17"], cwd=d)
            _expect_stdout(res, "toml file valid ok", "toml file invalid ok",
                           "toml file pengu smoke passed")
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 10. std.yaml binding  (was tests/test_extern_g5.py)
# ---------------------------------------------------------------------------


class TestYamlBinding:
    """std.yaml get_version fills out-ints (0.2.5 for the bundled libyaml)."""

    @requires_lib("yaml")
    def test_yaml_get_version_out_ints(self):
        src = r"""import std.spark
import std.yaml

weave main into int:
    var ma as int is -1
    var mi as int is -1
    var pa as int is -1
    calling yaml.get_version with (sigil of ma), (sigil of mi), (sigil of pa)
    if ma == 0:
        if mi == 2:
            if pa == 5:
                calling spark.println with "yaml 0.2.5 ok"
                return 0
    calling spark.println with "yaml version mismatch"
    return 1
"""
        res = compile_run(src, tag="yaml", extra_libs=["-lyaml"])
        _expect_stdout(res, "yaml 0.2.5 ok")


# ---------------------------------------------------------------------------
# 11. std.archivum recursive tree helpers  (was tests/test_archivum_tree.py)
# ---------------------------------------------------------------------------


class TestArchivumTree:
    """copy_tree / list_files_recursive - pure Pengu, gated on the runtime."""

    REL_SRC = "build/pengu_ffi_arch_src"
    REL_DST = "build/pengu_ffi_arch_dst"

    @requires_runtime
    def test_copy_tree_and_list_files_recursive(self):
        src_dir = REPO / "build" / "pengu_ffi_arch_src"
        dst_dir = REPO / "build" / "pengu_ffi_arch_dst"
        for d in (src_dir, dst_dir):
            shutil.rmtree(d, ignore_errors=True)
        try:
            demo = r"""import std.spark
import std.archivum

weave main into int:
    var ok_root as bool is calling archivum.create_dir with "{src}", true
    if ok_root == false:
        calling spark.println with "mkdir failed"
        return 1
    var ok_a as bool is calling archivum.write_file with "{src}/a.txt", "alpha"
    if ok_a == false:
        return 1
    var ok_sub as bool is calling archivum.create_dir with "{src}/sub", true
    if ok_sub == false:
        return 1
    var ok_b as bool is calling archivum.write_file with "{src}/sub/b.txt", "beta"
    if ok_b == false:
        return 1
    var copied as bool is calling archivum.copy_tree with "{src}", "{dst}"
    if copied == false:
        calling spark.println with "copy failed"
        return 1
    var files as list of string is calling archivum.list_files_recursive with "{dst}"
    if files.len == 2:
        calling spark.println with "list ok"
    var a_ok as bool is calling archivum.is_file with "{dst}/a.txt"
    var b_ok as bool is calling archivum.is_file with "{dst}/sub/b.txt"
    if a_ok:
        if b_ok:
            calling spark.println with "copy_tree ok"
    return 0
""".format(src=TestArchivumTree.REL_SRC, dst=TestArchivumTree.REL_DST)
            res = compile_run(demo, tag="archivum")
            _expect_stdout(res, "list ok", "copy_tree ok")
            assert (dst_dir / "a.txt").is_file()
            assert (dst_dir / "sub" / "b.txt").is_file()
        finally:
            for d in (src_dir, dst_dir):
                shutil.rmtree(d, ignore_errors=True)
