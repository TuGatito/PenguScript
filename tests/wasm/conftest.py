"""Shared plumbing for the WebAssembly test-suite (``tests/wasm/``).

Everything here is about the ``wasm32-unknown-emscripten`` target. Two levels:

* The **pure-Python** checks (triple parsing, artifact naming, dialect mapping,
  the runtime-archive lookup) need nothing at all — no emcc, no Node, no wasm
  runtime archive. They are the ones marked ``smoke``.
* The **end-to-end** checks compile with ``emcc`` and execute with ``node``.
  They skip unless the Emscripten SDK is active *and*
  ``build/wasm/lib/libpengu_runtime.a`` exists (``python build_runtime.py
  --target emscripten``).

Why the target is exercised through the CLI instead of by calling the builder
directly: ``pengu run --target wasm`` is what a user types, and it owns the
``-s`` settings, the archive search path, the output naming and the choice of
``node`` as the runner. A test that reproduced those by hand would pass even if
the CLI were broken.

``tests/wasm/filum_handles_leakcheck.c`` is compiled here too. It is a
deterministic replacement for LeakSanitizer on this workload: LSAN cannot see
leaked filum handles that contain a ``pthread_mutex_t``/``pthread_cond_t``,
because glibc registers those objects in internal lists and LSAN then treats the
whole block as still reachable. The C file's header comment has the measurements.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

#: ``tests/wasm/conftest.py`` -> ``tests/wasm`` -> ``tests`` -> the checkout.
WASM_ROOT = Path(__file__).resolve().parents[2]

if str(WASM_ROOT) not in sys.path:
    sys.path.insert(0, str(WASM_ROOT))

#: The host runtime (native tests) and the wasm runtime built by
#: ``build_runtime.py --target emscripten``.
BUILD_LIB = WASM_ROOT / "build" / "lib"
BUILD_INCLUDE = WASM_ROOT / "build" / "include"
WASM_LIB = WASM_ROOT / "build" / "wasm" / "lib"
WASM_INCLUDE = WASM_ROOT / "build" / "wasm" / "include"

#: The two fixtures this suite exercises end to end.
STRESS_PENGU = Path(__file__).parent / "filum_stress.pengu"
LEAKCHECK_C = Path(__file__).parent / "filum_handles_leakcheck.c"


def _which(name: str) -> str | None:
    return shutil.which(name)


@pytest.fixture(scope="session")
def wasm_root() -> Path:
    """The repository root."""
    return WASM_ROOT


@pytest.fixture(scope="session")
def emcc() -> str:
    """Path to ``emcc``, or skip the test."""
    path = _which("emcc")
    if not path:
        pytest.skip("emcc not on PATH (activate the Emscripten SDK)")
    return path


@pytest.fixture(scope="session")
def node() -> str:
    """Path to ``node``, or skip the test."""
    path = _which("node")
    if not path:
        pytest.skip("node not on PATH")
    return path


@pytest.fixture(scope="session")
def emar_path(emcc) -> str:
    """Path to ``emar``, derived from the active emcc (or PATH).

    ``ar`` cannot write an archive of wasm members, so this is a hard
    requirement of the static-library path.
    """
    sibling = Path(emcc).parent / "emar"
    if sibling.is_file():
        return str(sibling)
    path = _which("emar")
    if not path:
        pytest.skip("emar not on PATH (activate the Emscripten SDK)")
    return path


@pytest.fixture(scope="session")
def wasm_runtime() -> Path:
    """``build/wasm/lib/libpengu_runtime.a``, or skip the test."""
    archive = WASM_LIB / "libpengu_runtime.a"
    if not archive.is_file():
        pytest.skip("wasm runtime not built (run: python build_runtime.py --target emscripten)")
    return archive


@pytest.fixture(scope="session")
def host_runtime() -> Path:
    """``build/lib/libpengu_runtime.a``, or skip the test."""
    archive = BUILD_LIB / "libpengu_runtime.a"
    if not archive.is_file():
        pytest.skip("host runtime not built (run: python build_runtime.py)")
    return archive


def _cli_env() -> dict:
    return {**os.environ, "PYTHONPATH": str(WASM_ROOT)}


@pytest.fixture
def run_wasm_script(tmp_path, emcc, node, wasm_runtime):
    """Compiles a Pengu source for wasm and runs it with node.

    Depends on ``emcc``, ``node`` and ``wasm_runtime`` so that a missing
    toolchain *skips* rather than silently producing a test that asserts on the
    CLI's own "emcc not found" error.

    Returns the ``CompletedProcess``; ``stdout`` still carries the CLI's progress
    lines, so callers asserting on program output should look for their marker
    rather than compare the whole stream.
    """
    def _run(source: str, tag: str = "prog", timeout: int = 600,
             env: dict | None = None):
        script = tmp_path / f"{tag}.pengu"
        script.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(WASM_ROOT / "pengu_project.py"), "run",
             "--target", "wasm32-unknown-emscripten",
             "--no-cache", "--ephemeral", str(script)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(tmp_path), env={**_cli_env(), **(env or {})},
        )
        return result

    return _run


@pytest.fixture
def run_host_script(tmp_path, host_runtime):
    """Compiles a Pengu source for the host and runs it. Same contract."""
    def _run(source: str, tag: str = "prog", timeout: int = 600,
             env: dict | None = None):
        script = tmp_path / f"{tag}.pengu"
        script.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(WASM_ROOT / "pengu_project.py"), "run",
             "--no-cache", "--ephemeral", str(script)],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(tmp_path), env={**_cli_env(), **(env or {})},
        )
        return result

    return _run


def _wrap_flags() -> list:
    """Linker flags that route malloc/free through the leak-check shims.

    ``--wrap`` is supported by GNU ld, lld and wasm-ld alike, so the same
    harness runs on both targets.
    """
    return ["-Wl,--wrap=malloc", "-Wl,--wrap=calloc",
            "-Wl,--wrap=realloc", "-Wl,--wrap=free"]


@pytest.fixture
def leakcheck_binary(tmp_path, host_runtime):
    """Builds ``filum_handles_leakcheck.c`` against the *host* runtime."""
    cc = _which("clang") or _which("gcc")
    if not cc:
        pytest.skip("no C compiler for the leak check")

    def _build(name: str = "leakcheck") -> Path:
        out = tmp_path / name
        cmd = [cc, "-O1", "-I", str(WASM_ROOT), "-I", str(BUILD_INCLUDE),
               str(LEAKCHECK_C), "-o", str(out),
               "-L", str(BUILD_LIB), *_wrap_flags(),
               "-Wl,--start-group", "-lpengu_runtime", "-Wl,--end-group",
               "-pthread", "-lm", "-ldl"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        assert res.returncode == 0, f"leak-check build failed:\n{res.stderr}"
        return out

    return _build


@pytest.fixture
def leakcheck_wasm_js(tmp_path, emcc, wasm_runtime):
    """Builds ``filum_handles_leakcheck.c`` against the *wasm* runtime."""
    def _build(name: str = "leakcheck") -> Path:
        out = tmp_path / f"{name}.js"
        cmd = [emcc, "-O1", "-I", str(WASM_ROOT), "-I", str(WASM_INCLUDE),
               "-pthread", str(LEAKCHECK_C), "-o", str(out),
               "-L", str(WASM_LIB), *_wrap_flags(),
               "-Wl,--start-group", "-lpengu_runtime", "-Wl,--end-group",
               "-s", "ALLOW_MEMORY_GROWTH=1", "-s", "ENVIRONMENT=node",
               "-s", "PTHREAD_POOL_SIZE=4"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        assert res.returncode == 0, f"wasm leak-check build failed:\n{res.stderr}"
        return out

    return _build
