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
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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

requires_cc = pytest.mark.skipif(not HAVE_CC, reason="no C compiler available")
requires_runtime = pytest.mark.skipif(
    not HAVE_RUNTIME, reason="libpengu_runtime.a not built (run build_runtime.py)"
)


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

    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker(base_dir=base_dir)
    try:
        checker.check(tree, source=source, filename=filename)
    except Exception as exc:  # noqa: BLE001 - keep the message whatever it is
        text = str(exc)
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


def gen_bundle(source: str, filename: str = "t.pengu", extra_files=None) -> str:
    """Runs parse+check+codegen for one (or several) files and returns C text.

    ``extra_files`` is a list of ``(name, source)`` tuples for imports. The
    checker resolves std modules against the repository root.
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
    cg = PenguCodegen(checker.symbols, [fname for fname, _ in files],
                      str(REPO), compile_env=checker.compile_env)
    for fname, _ in files:
        cg.collect_declarations([(fname, trees[fname])])
    return cg.generate_bundle()


# --------------------------------------------------------------------------
# Level 3: compile + run with a C compiler
# --------------------------------------------------------------------------


def runtime_link_flags():
    """Core libraries the Pengu C runtime is built against (per platform)."""
    flags = ["-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl",
             "-lmbedcrypto", "-lmicrohttpd", "-lz"]
    if os.name == "nt":
        flags += ["-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt"]
    else:
        flags += ["-pthread", "-lm", "-ldl"]
    return flags


def compile_run(source: str, tag: str = "t", extra_libs=None, cwd=None,
                timeout: int = 180) -> subprocess.CompletedProcess:
    """Writes ``source`` to a temp project, bundles, compiles and runs it.

    Returns the CompletedProcess of the executed binary. Decorating tests with
    ``@requires_runtime`` gives a nicer skip message than the internal asserts.
    """
    assert HAVE_CC, "no C compiler (gcc/clang/cc) found on PATH"
    assert HAVE_RUNTIME, "libpengu_runtime.a not built (run build_runtime.py)"

    from pengu_project import PenguBuilder, ProjectConfig

    d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
    try:
        entry = d / f"{tag}.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

        cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
        exe = d / ("bin.exe" if is_windows() else "bin")
        cmd = [cc, str(bundle_path),
               f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
               f"-L{BUILD_LIB}"]
        cmd += runtime_link_flags()
        if extra_libs:
            cmd += list(extra_libs)
        cmd += ["-o", str(exe)]

        res = subprocess.run(cmd, cwd=str(cwd or REPO), capture_output=True,
                             text=True, timeout=timeout)
        assert res.returncode == 0, (
            f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
        )
        run_res = subprocess.run([str(exe)], cwd=str(cwd or REPO),
                                 capture_output=True, text=True, timeout=timeout)
        assert run_res.returncode == 0, (
            f"Execution failed ({run_res.returncode}):\n"
            f"{run_res.stderr}\n{run_res.stdout}"
        )
        return run_res
    finally:
        shutil.rmtree(d, ignore_errors=True)
