#!/usr/bin/env python3
"""Shared helpers for the PenguScript test-suite.

All tests import from here (``from tests.conftest import ...``) instead of
duplicating the parser / checker / codegen / gcc plumbing. Three levels are
supported:

* pure compiler checks (no C toolchain needed),
* bundle checks (inspect the generated C without compiling it),
* compile+run checks (Pengu source -> C -> gcc -> executable).

Archives under ``build/lib`` are optional: tests that need a specific C
library use :func:`have_lib` / the ``requires_*`` skip markers so the suite
stays green on a fresh checkout that has not run ``build_runtime.py`` yet.
"""
import functools
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest

REPO = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO / "build"
BUILD_LIB = BUILD_DIR / "lib"
BUILD_INCLUDE = BUILD_DIR / "include"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# --------------------------------------------------------------------------
# Environment probes
# --------------------------------------------------------------------------


def have_lib(name: str) -> bool:
    """True when build/lib/lib<name>.a exists (library was built)."""
    return (BUILD_LIB / f"lib{name}.a").is_file()


def have_tool(name: str) -> bool:
    """True when `name` is available on PATH."""
    return shutil.which(name) is not None


def have_std_module(name: str) -> bool:
    """True when std/<name>.pengu exists in the repository."""
    return (REPO / "std" / f"{name}.pengu").is_file()


HAVE_CC = have_tool("gcc") or have_tool("clang") or have_tool("cc")
HAVE_RUNTIME = have_lib("pengu_runtime")
HAVE_VALGRIND = have_tool("valgrind")

requires_cc = pytest.mark.skipif(not HAVE_CC, reason="no C compiler available")
requires_runtime = pytest.mark.skipif(
    not HAVE_RUNTIME, reason="libpengu_runtime.a not built (run build_runtime.py)"
)


def leakcheck_usable() -> bool:
    """True when a leak checker can actually run on this platform.

    ``tests/leakcheck.c`` is a *glibc/ELF* ``LD_PRELOAD`` shim: it needs
    ``<link.h>``/``dl_iterate_phdr``, ``__libc_malloc`` and ``LD_PRELOAD``
    itself.  macOS has none of those (and no supported valgrind), and Windows has
    neither the shim nor ``-ldl``/``-lpthread``; there the leak tests must skip
    instead of failing on a build error that says nothing about the compiler.

    ``valgrind`` is accepted as an alternative wherever it exists.
    ``PENGU_NO_LEAKCHECK=1`` forces the skip path (CI matrix, slow runners).
    """
    if os.environ.get("PENGU_NO_LEAKCHECK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    if HAVE_VALGRIND:
        return True
    return HAVE_CC and sys.platform.startswith("linux")


requires_leakcheck = pytest.mark.skipif(
    not leakcheck_usable(),
    reason="no leak checker available (tests/leakcheck.c is glibc/ELF-only; "
           "install valgrind or run on Linux)",
)

#: Hang guard for the "build one whole std program, in debug *and* release"
#: family (``tests/test_std_*``). Use it as ``@pytest.mark.timeout(...)``.
#:
#: These tests used a literal ``30``. That number was calibrated on a serial run,
#: where the heaviest of them takes ~13 s. Under ``pytest -n auto`` the same work
#: shares the machine with N-1 other C compilations, and
#: ``test_std_invoke_extended[release]`` was observed past 30 s -- a failure that
#: says nothing about the code under test and everything about how many compilers
#: were running.
#:
#: This is a **hang guard, not a performance assertion**: none of these tests
#: asserts on elapsed time, so the bound only has to sit comfortably above the
#: slowest honest run while still failing long before the CI job timeout.
STD_PROGRAM_BUILD_TIMEOUT = 120

#: True when the suite is running under PENGU_CFLAGS with a sanitizer
#: (`-fsanitize=...`), i.e. inside the `sanitizers` job of
#: `.github/workflows/nightly.yml`.
#:
#: Phase 8 item 8.2 measured which tests cannot hold their premise under
#: instrumentation: UBSan's own report replaces the crash handler's `[PENGU CRASH]`
#: dump, so tests that assert our signal path see rc=1 instead of the expected
#: signal, and `PENGU_CFLAGS` injects GNU flags into a command line that a test
#: asserts contains none for MSVC.  Those tests skip *here*, with the reason
#: visible, instead of leaving the sanitizer job red for a non-finding.
SANITIZERS_ACTIVE = "sanitize" in os.environ.get("PENGU_CFLAGS", "")

requires_no_sanitizer = pytest.mark.skipif(
    SANITIZERS_ACTIVE,
    reason="not meaningful under PENGU_CFLAGS sanitizers: UBSan reports before "
           "the project's crash handler runs (see AUDIT_1.0_FASE8.md item 8.2)",
)


def requires_no_sanitizer_reason(reason: str):
    """`requires_no_sanitizer`, with a reason specific to the test it decorates."""
    return pytest.mark.skipif(SANITIZERS_ACTIVE, reason=reason)


# --------------------------------------------------------------------------
# Platform facts the platform-dependent tests share
#
# Signal *numbers* and their `nm` spelling are the two things that differ most
# between the three CI runners (macOS SIGBUS is 10, Linux is 7; Mach-O prefixes
# C symbols with `_`).  Both are derived from the running interpreter instead of
# being written down as literals.
# --------------------------------------------------------------------------

#: True when a child killed by a fault is reported as a POSIX signalled process,
#: i.e. when the `128 + signo` contract exists at all.
#:
#: POSIX has it (`subprocess` reports a negative status, and the CLI remaps it).
#: Windows does not: an integer division by zero raises an SEH exception, and
#: `pengu_win_exception_handler` deliberately returns `EXCEPTION_EXECUTE_HANDLER`
#: so the process dies with the NTSTATUS (0xC0000094 = 3221225620), never 136.
POSIX_SIGNAL_EXIT_CODES = os.name != "nt"

requires_posix_signal_exit = pytest.mark.skipif(
    not POSIX_SIGNAL_EXIT_CODES,
    reason="POSIX-only contract: on Windows a faulting child exits with an "
           "NTSTATUS (0xC0000094), not 128 + signo",
)


def _fault_signal(name: str) -> Optional["tuple[str, int]"]:
    """`(name, 128 + signo)` for a fault signal, or None when it has no number.

    The exit status the crash handler produces is `128 + signo` on every POSIX
    system, but the *number* is platform-specific, and Windows does not define
    every name (`signal.SIGBUS` is absent there), so this must not be a literal.
    """
    signo = getattr(signal, name, None)
    if signo is None:
        return None
    return (name, 128 + int(signo))


#: Fault signals `pengu_install_crash_handler()` installs, with the exit status
#: the handler produces for each.  Built from the `signal` module, never from
#: literals: macOS `SIGBUS` is 10 (138), Linux `SIGBUS` is 7 (135).
FAULT_SIGNALS = [
    pair
    for pair in (_fault_signal(n) for n in ("SIGFPE", "SIGILL", "SIGBUS", "SIGSEGV"))
    if pair is not None
]

#: True when an integer division by zero actually raises `SIGFPE`.
#:
#: x86 traps; AArch64's `SDIV` returns 0 for a zero divisor, so the program runs
#: to completion and the crash handler is never reached (measured on the macOS
#: arm64 runner: the program printed `0` and exited 0).
DIVISION_BY_ZERO_TRAPS = platform.machine().lower() not in ("arm64", "aarch64")

#: True when AddressSanitizer's LeakSanitizer can actually run.
#:
#: macOS ships libclang_rt.asan without LeakSanitizer: `detect_leaks=1` aborts
#: the process with "detect_leaks is not supported on this platform" (exit -6),
#: so a leak gate there has to use valgrind or skip.
ASAN_DETECT_LEAKS_SUPPORTED = sys.platform != "darwin"


def nm_symbol_regex(name: str) -> str:
    """Regex matching `name` in `nm` output on ELF *and* Mach-O.

    Mach-O (macOS) prefixes C symbols with an underscore (`_pengu_abi_version`),
    and `_` is a word character, so a plain ``\\bname\\b`` can never match there:
    ``\\b`` does not exist between `_` and `p`.  The leading underscore is
    optional here, and the lookbehind keeps `not_name` from matching.
    """
    return rf"(?<![A-Za-z0-9_])_?{re.escape(name)}\b"


def nm_symbol_name(symbol: str) -> str:
    """Normalizes one `nm` symbol to the name the C source used.

    Mach-O prefixes every C symbol with `_` (`_pengu_abi_version`); ELF does not.
    Stripping exactly one underscore on Darwin maps both spellings onto the
    source name, including a symbol that legitimately begins with `_` (which
    Mach-O prints as `__name`).  Windows/COFF `nm` output is not affected.
    """
    if sys.platform == "darwin" and symbol.startswith("_"):
        return symbol[1:]
    return symbol


def _host_cc() -> str:
    """The compiler `compile_run` prefers (same order, so both agree)."""
    for cand in ("gcc", "clang", "cc"):
        if have_tool(cand):
            return cand
    return ""


@functools.lru_cache(maxsize=1)
def host_cc_is_clang() -> bool:
    """True when the suite's compiler is clang, whatever it is called.

    macOS ships `/usr/bin/gcc` as a shim for clang, so the *name* is not enough:
    the question is answered by asking the compiler.  Used to skip (with a
    reason) assertions that are GCC semantics, e.g. `-fwrapv` silencing UBSan's
    signed-overflow report.
    """
    cc = _host_cc()
    if not cc:
        return False
    try:
        res = subprocess.run([cc, "--version"], capture_output=True, text=True,
                             timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return "clang" in (res.stdout + res.stderr).lower()


def build_leakcheck(tmp_path: Path) -> Path:
    """Builds the ``LD_PRELOAD`` leak interposer, or skips the caller.

    Skipping (rather than asserting) keeps CI green on platforms where the
    interposer cannot exist, while a genuine build failure on Linux still
    surfaces as a skip with the compiler error attached.
    """
    if not leakcheck_usable():
        pytest.skip("leak checker unavailable: tests/leakcheck.c is glibc/ELF-only")
    if not HAVE_CC:
        pytest.skip("no C compiler to build the leak checker")
    cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
    so = Path(tmp_path) / "leakcheck.so"
    src = REPO / "tests" / "leakcheck.c"
    cmd = [cc, "-shared", "-fPIC", "-O1", "-o", str(so), str(src), "-ldl", "-lpthread"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip(f"leak checker does not build here: {res.stderr.strip()[:300]}")
    return so


def requires_lib(name: str):
    return pytest.mark.skipif(
        not have_lib(name), reason=f"lib{name}.a not built (run build_runtime.py)"
    )


def is_windows() -> bool:
    return os.name == "nt"


# --------------------------------------------------------------------------
# Level 1: parse / semantic check (no C toolchain)
# --------------------------------------------------------------------------


def check(source: str, filename: str = "t.pengu", base_dir: str = "."):
    """Parses + semantically checks `source`.

    Returns the checker instance. Raises on the first semantic error.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker(base_dir=base_dir)
    checker.check(tree, source=source, filename=filename)
    return checker


def check_ok(source: str, filename: str = "t.pengu", base_dir: str = "."):
    """Asserts `source` parses and type-checks cleanly; returns the checker."""
    return check(source, filename=filename, base_dir=base_dir)


def check_error(source: str, filename: str = "t.pengu", contains=None,
                base_dir: str = ".") -> str:
    """Asserts `source` FAILS to compile and returns the error text.

    ``contains`` may be a substring (or list of substrings) that must appear
    in the reported error (e.g. an error code like ``E0012``).
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    try:
        parser = PenguParser()
        tree = parser.parse(source)
        checker = PenguChecker(base_dir=base_dir)
        checker.check(tree, source=source, filename=filename)
    except Exception as exc:  # noqa: BLE001 - keep the message whatever it is
        text = str(exc)
        if getattr(exc, "code", None):
            text = f"{text} [{exc.code}]"
    else:
        raise AssertionError("expected a compile error but the source is clean")

    if contains is not None:
        wanted = [contains] if isinstance(contains, str) else contains
        for w in wanted:
            assert w in text, f"error {text!r} does not mention {w!r}"
    return text


# --------------------------------------------------------------------------
# Level 2: bundle to C text (no C toolchain)
# --------------------------------------------------------------------------


def gen_bundle(source: str, filename: str = "t.pengu", extra_files=None,
               strict_c99: bool = False, target_compiler: str = "") -> str:
    """Runs parse+check+codegen for one (or several) files and returns C text.

    ``extra_files`` is a list of ``(name, source)`` tuples for imports. The
    checker resolves std modules against the repository root.
    ``strict_c99`` forces portable C99 output (no GNU statement expressions);
    ``target_compiler`` selects the attribute/restrict dialect.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_codegen import PenguCodegen
    from pengu_parser.pengu_parser import PenguParser

    files = [(filename, source)] + list(extra_files or [])
    parser = PenguParser()
    checker = PenguChecker(base_dir=str(REPO))
    trees = {}
    for fname, code in files:
        tree = parser.parse(code)
        checker.check(tree, source=code, filename=fname)
        trees[fname] = tree
    # `gen_bundle` builds the codegen directly, so it must state the
    # bounds/overflow switch itself: otherwise it inherits whatever an earlier
    # test in the same process left in the `_RELEASE_UNSAFE` global, and a test
    # asserting on emitted `pengu_assert_bounds` depends on test order.
    from pengu_parser.pengu_codegen import set_release_unsafe as _gen_set_ru
    from pengu_parser.pengu_codegen import is_release_unsafe as _gen_is_ru

    _gen_previous_ru = _gen_is_ru()
    _gen_set_ru(False)
    try:
        cg = PenguCodegen(checker.symbols, [fname for fname, _ in files],
                          str(REPO), compile_env=checker.compile_env,
                          use_gnu_extensions=not strict_c99,
                          target_compiler=target_compiler)
        for fname, _ in files:
            cg.collect_declarations([(fname, trees[fname])])
        return cg.generate_bundle()
    finally:
        _gen_set_ru(_gen_previous_ru)


def check_c_syntax(c_code: str) -> None:
    """Verifies that generated C code passes syntax checking with gcc or clang (-fsyntax-only)."""
    if not HAVE_CC:
        return
    cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
        f.write(c_code)
        c_path = f.name
    try:
        cmd = [
            cc, "-fsyntax-only", "-std=c11", c_path,
            f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
            "-Wno-error=implicit-function-declaration",
            "-Wno-error=implicit-int",
            "-Wno-error=int-conversion"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"C syntax error: {res.stderr}\n\nGenerated C:\n{c_code}"
    finally:
        try:
            os.remove(c_path)
        except OSError:
            pass



# --------------------------------------------------------------------------
# Level 3: compile + run with a C compiler
# --------------------------------------------------------------------------


def bundle_project(source: str, tag: str = "proj") -> str:
    """Bundles a program through the real builder (std imports resolved).

    ``gen_bundle`` only checks the files it is given, so programs that use
    ``import std.…`` need the project builder. Returns the generated C text.
    """
    from pengu_project import PenguBuilder, ProjectConfig
    from pengu_parser.pengu_codegen import set_release_unsafe as _set_ru

    d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
    try:
        entry = d / f"{tag}.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
        return Path(bundle_path).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def runtime_tail_flags():
    """Platform tail that must come AFTER every archive/extra library.

    Single-pass linkers (GNU ld without --start-group, and especially macOS
    ld64) only resolve symbols from libraries that appear later on the command
    line, so provider libraries (-lm, -lcrypto/-lssl, frameworks) are appended
    last: sqlite3 needs `log`, libpengu_stb needs `sqrt`, libzip (OpenSSL
    backend) needs the EVP_* symbols, and std.uuid needs CoreFoundation.
    """
    if os.name == "nt":
        return []
    tail = []
    if sys.platform.startswith("linux"):
        # Older glibc put clock_gettime in librt; crypto/ssl only get pulled
        # when a library actually references them.
        tail += ["-lrt", "-lcrypto", "-lssl"]
    elif sys.platform.startswith("darwin"):
        tail += ["-framework", "CoreFoundation"]
    tail += ["-pthread", "-lm", "-ldl"]
    return tail


def raylib_link_flags():
    """``-lraylib`` plus the windowing/OpenGL providers its backend needs.

    ``libraylib.a`` is not self-contained: its GLFW backend calls into Xlib,
    Xrandr, Xinerama, Xcursor, Xi and Xext on X11 (and into the AppKit/IOKit/
    CoreVideo/OpenGL frameworks on Cocoa), and the GL entry points come from the
    system loader.  The CI runner installs exactly those dev packages
    (``.github/actions/setup-pengu``), so a raylib link line that omits them
    fails as soon as the archive exists -- with "undefined reference to
    `XCloseDisplay'" on Linux.  Windows passes the equivalents explicitly.

    Callers append this *before* :func:`runtime_tail_flags`, like every other
    extra library.
    """
    if os.name == "nt":
        return ["-lraylib", "-lopengl32", "-lgdi32", "-lwinmm"]
    if sys.platform.startswith("darwin"):
        return [
            "-lraylib",
            "-framework", "Cocoa",
            "-framework", "IOKit",
            "-framework", "CoreVideo",
            "-framework", "OpenGL",
            "-framework", "CoreAudio",
            "-framework", "AudioToolbox",
            "-framework", "AVFoundation",
            "-framework", "CoreMedia",
        ]
    return [
        "-lraylib",
        "-lGL", "-lX11", "-lXrandr", "-lXi", "-lXcursor", "-lXinerama", "-lXext",
    ]


def runtime_link_flags():
    """Core libraries the Pengu C runtime is built against (per platform).

    Does NOT include the platform tail (math/crypto/frameworks) — callers must
    append :func:`runtime_tail_flags` after their extra libraries so providers
    come last on the command line.
    """
    flags = []
    if os.name == "nt":
        flags = [
            "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl",
            "-lmbedcrypto", "-lmicrohttpd", "-lz",
            "-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt"
        ]
    else:
        # Search paths (-L) MUST come before -l flags
        for brew_lib in ("/opt/homebrew/lib", "/usr/local/lib"):
            if os.path.isdir(brew_lib):
                flags.append(f"-L{brew_lib}")
        try:
            from pengu_paths import pkg_config_libs
            for pkg in ("libxml-2.0", "libcurl", "libmicrohttpd", "mbedtls"):
                for tok in pkg_config_libs(pkg):
                    if tok.startswith("-L") and tok not in flags:
                        flags.append(tok)
        except Exception:
            pass

        flags.extend([
            "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl",
            "-lmbedcrypto", "-lmicrohttpd", "-lz"
        ])
        try:
            from pengu_paths import pkg_config_libs
            for pkg in ("libxml-2.0", "libcurl", "libmicrohttpd", "mbedtls"):
                for tok in pkg_config_libs(pkg):
                    if tok.startswith("-l") and tok not in flags:
                        flags.append(tok)
        except Exception:
            pass
    return flags


def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
                timeout: int = 180, profile: str = "debug",
                expect_exit: Optional[int] = 0,
                release_unsafe: bool = False,
                extra_cflags: Optional[list] = None) -> subprocess.CompletedProcess:
    """Writes ``source`` to a temp project, bundles, compiles and runs it.

    Returns the CompletedProcess of the executed binary. Decorating tests with
    ``@requires_runtime`` gives a nicer skip message than the internal asserts.

    Args:
        expect_exit: expected process exit code; pass ``None`` to accept any
            (useful for programs that are meant to abort, e.g. a bounds panic).
        release_unsafe: build with bounds/overflow checks disabled.
    """
    assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
    assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

    from pengu_project import PenguBuilder, ProjectConfig
    from pengu_parser.pengu_codegen import set_release_unsafe as _set_ru
    from pengu_parser.pengu_codegen import is_release_unsafe as _is_ru

    # `_RELEASE_UNSAFE` is a process global. Save it and put it back: a test that
    # leaves it set changes what *later* tests in the same process generate, which
    # is invisible while tests run in their historical order and breaks as soon as
    # they are distributed differently (pytest-xdist).
    _previous_release_unsafe = _is_ru()

    d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
    try:
        entry = d / f"{tag}.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile=profile, output="c")
        _set_ru(bool(release_unsafe))
        builder = PenguBuilder(cfg)
        builder.release_unsafe = bool(release_unsafe)
        bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

        cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
        exe = d / ("bin.exe" if is_windows() else "bin")
        cmd = [cc, str(bundle_path),
               f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
               f"-L{BUILD_LIB}"]
        if profile == "release":
            cmd.append("-O3")
            if not release_unsafe:
                cmd.append("-fwrapv")   # defined wrapping (roadmap 5.1)
        else:
            cmd.append("-g")
            if not release_unsafe:
                cmd.append("-ftrapv")   # trap signed overflow in debug
        if extra_cflags:
            cmd += list(extra_cflags)
        # Honour PENGU_CFLAGS / PENGU_LDFLAGS so the whole suite can be run under
        # sanitizers in CI (see the `sanitizers` job of nightly.yml).
        import shlex as _shlex

        _env_cflags = os.environ.get("PENGU_CFLAGS", "").strip()
        if _env_cflags:
            cmd += _shlex.split(_env_cflags)
        _env_ldflags = os.environ.get("PENGU_LDFLAGS", "").strip()
        if _env_ldflags:
            cmd += _shlex.split(_env_ldflags)
        # GCC 14 turns implicit declarations / int-conversion into errors by
        # default; generated C may trigger those warnings on newer toolchains,
        # so keep them as warnings across compilers.
        cmd += ["-Wno-error=implicit-function-declaration",
                "-Wno-error=implicit-int",
                "-Wno-error=int-conversion"]
        cmd += runtime_link_flags()
        if extra_libs:
            cmd += list(extra_libs)
        cmd += runtime_tail_flags()
        cmd += ["-o", str(exe)]

        res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                             text=True, timeout=timeout)
        assert res.returncode == 0, (
            f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
        )
        # PENGU_TEST_VALGRIND=1 prefixes the run with valgrind, so the sanitizer
        # workflow can leak-check the suite without a second harness.
        run_cmd: list = [str(exe)]
        if os.environ.get("PENGU_TEST_VALGRIND", "").strip().lower() in ("1", "true", "yes", "on"):
            valgrind = shutil.which("valgrind")
            if valgrind:
                run_cmd = [
                    valgrind, "--error-exitcode=99", "--leak-check=full",
                    "--errors-for-leak-kinds=definite", "--quiet",
                    str(exe),
                ]
            else:
                raise AssertionError("PENGU_TEST_VALGRIND=1 requires valgrind on PATH")
        run_res = subprocess.run(run_cmd, cwd=str(cwd or REPO),
                                 capture_output=True, text=True, timeout=timeout)
        if expect_exit is not None:
            assert run_res.returncode == expect_exit, (
                f"Execution failed ({run_res.returncode}, expected {expect_exit}):\n"
                f"{run_res.stderr}\n{run_res.stdout}"
            )
        return run_res
    finally:
        _set_ru(_previous_release_unsafe)
        shutil.rmtree(d, ignore_errors=True)

# --------------------------------------------------------------------------- #
# Generated-C helpers
# --------------------------------------------------------------------------- #

_BOUNDS_WRAPPER_RE = re.compile(
    r"\(__extension__\(\{\s*__auto_type\s+\w+\s*=\s*\((.*?)\);\s*"
    r"pengu_assert_bounds\(.*?\);\s*\w+;\s*\}\)\)",
    re.DOTALL,
)


def strip_bounds_checks(c_code: str) -> str:
    """Removes the always-on bounds-check wrappers from generated C.

    Since roadmap 5.2 every `at` access is emitted inside a GNU statement
    expression that calls ``pengu_assert_bounds``.  Emission-shape assertions
    care about the *access* shape, not the check, so normalise it away (and the
    extra parentheses it introduces).
    """
    prev = None
    while prev != c_code:
        prev = c_code
        c_code = _BOUNDS_WRAPPER_RE.sub(r"\1", c_code)
    return re.sub(r"\[\(([^()]*)\)\]", r"[\1]", c_code)


# --------------------------------------------------------------------------- #
# Level 4: reusable C-compilation fixtures (roadmap 8.18)
# --------------------------------------------------------------------------- #
#
# `check_c_syntax` above and the hand-rolled `subprocess.run([cc, ...])` blocks
# scattered over the portability, MSVC and cross-compile suites each re-derived
# the same knowledge: which compiler, which `-std`, which `-I`/`-L`, and which
# tail libraries.  Item 8.1 found the cost of that duplication — a suite that
# built argv by hand could assert "portable" while never asking a compiler.
# These fixtures are that knowledge in one place; the portability and attribute
# suites consume them instead of building argv themselves.


class CToolchain:
    """The C compiler this suite will use, plus the repo's include/link flags."""

    def __init__(self, cc: str, have_runtime: bool) -> None:
        self.cc = cc
        self.have_runtime = have_runtime

    def include_flags(self) -> list:
        return [f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}"]

    def link_flags(self) -> list:
        return [f"-L{BUILD_LIB}", *runtime_link_flags(), *runtime_tail_flags()]

    def std_flags(self, std: str, pedantic: bool) -> list:
        """``-std=`` plus the strictness flag this platform actually supports.

        ``-pedantic-errors`` turns a GNU extension into a hard error, which is
        the whole point of the portability gate; MSVC has no equivalent and
        MinGW's gcc keeps ``-pedantic`` (warnings) because its C library headers
        are not pedantic-clean.
        """
        if not std:
            return []
        if not pedantic:
            return [f"-std={std}"]
        return [f"-std={std}", "-pedantic"] if os.name == "nt" else [f"-std={std}", "-pedantic-errors"]


def default_cc() -> Optional[str]:
    """First C compiler on PATH, or None."""
    for name in ("gcc", "clang", "cc"):
        found = shutil.which(name)
        if found:
            return found
    return None


@pytest.fixture(scope="session")
def c_toolchain() -> CToolchain:
    """Session-wide C compiler description; skips when there is no compiler."""
    cc = default_cc()
    if cc is None:
        pytest.skip("no C compiler available")
    return CToolchain(cc=cc, have_runtime=HAVE_RUNTIME)


@pytest.fixture()
def compile_c(c_toolchain, tmp_path):
    """Returns ``compile(source, *, std, pedantic, syntax_only, extra) -> Path``.

    The returned callable compiles a C *text* (typically a generated bundle) and
    fails the test with the compiler's own stderr when it does not build.  With
    ``syntax_only=True`` it runs ``-fsyntax-only`` and returns the source path,
    which is what a portability gate wants when there is no runtime archive.
    """

    def _compile(c_code: str, *, name: str = "prog", std: str = "c11",
                 pedantic: bool = False, syntax_only: bool = False,
                 cc: Optional[str] = None, extra=(), timeout: int = 300) -> Path:
        src = tmp_path / f"{name}.c"
        src.write_text(c_code, encoding="utf-8")
        cmd = [cc or c_toolchain.cc, *c_toolchain.std_flags(std, pedantic),
               *c_toolchain.include_flags()]
        if syntax_only:
            cmd += ["-fsyntax-only", str(src)]
        else:
            exe = tmp_path / (name + (".exe" if os.name == "nt" else ""))
            cmd += [str(src), *c_toolchain.link_flags(), "-o", str(exe)]
        cmd += list(extra)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        assert res.returncode == 0, (
            f"C compilation failed (rc={res.returncode}):\n$ {' '.join(cmd)}\n"
            f"{res.stderr}\n{res.stdout}"
        )
        return src if syntax_only else exe

    return _compile


@pytest.fixture()
def run_c(compile_c):
    """Compiles a C text with :func:`compile_c` and executes it."""

    def _run(c_code: str, *, run_timeout: int = 120, **kwargs) -> subprocess.CompletedProcess:
        exe = compile_c(c_code, **kwargs)
        return subprocess.run([str(exe)], capture_output=True, text=True, timeout=run_timeout)

    return _run
