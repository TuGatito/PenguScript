"""Phase 3 item 3.5 — `pengu_abi_version()` is verified at LINK time.

`SECURITY.md` ("Runtime ABI pinning") promises that a stale
`libpengu_runtime.a` fails at compile time instead of corrupting memory. Before
this item the promise was false: `pengu_codegen.py` only emitted
`_Static_assert(PENGU_ABI_VERSION == N)`, which compares the **codegen's**
expectation against the **header** and never looks at the archive. AUDIT_1.0.md
§5.6 measured the consequence —

    $ nm build/lib/libpengu_runtime.a | grep -i abi
    (empty)

— so a bundle and an ABI-mismatched archive linked silently and reinterpreted
struct fields at the wrong offsets.

The fix exports the version as a real object-file symbol (defined only in
`pengu_runtime.c`, never inline in the header) and makes every generated bundle
take its address, so the resolver is forced to find it in the archive.

Rule C1: every test below **measures** (`nm`), **compiles+links+runs**, or both.
No test asserts on generated C text.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    compile_run,
    gen_bundle,
    have_tool,
    runtime_link_flags,
    runtime_tail_flags,
)

pytestmark = pytest.mark.skipif(
    not have_tool("gcc"), reason="gcc is required to compile/link the runtime"
)

RUNTIME_A = BUILD_LIB / "libpengu_runtime.a"
RUNTIME_C = REPO / "pengu_parser" / "pengu_runtime.c"
ABI_SYMBOL = "pengu_abi_version"


def _nm_defined_symbols(archive: Path) -> dict:
    """Returns {symbol_name: nm_type_letter} for *defined* symbols in `archive`.

    ``nm`` reports undefined references as ``U``; only ``T``/``t`` (text),
    ``D``/``d`` (data), ``R``/``r`` (rodata) and ``B``/``b`` (bss) count as
    definitions, so a mere declaration cannot satisfy the property.
    """
    nm = shutil.which("nm")
    assert nm, "nm is required for this measurement"
    res = subprocess.run([nm, str(archive)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"nm failed on {archive}:\n{res.stderr}"
    defined = {}
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-2] in {"T", "t", "D", "d", "R", "r", "B", "b", "W", "V"}:
            defined[parts[-1]] = parts[-2]
    return defined


def _cc() -> str:
    for cand in ("gcc", "clang", "cc"):
        if have_tool(cand):
            return cand
    return ""


# ---------------------------------------------------------------------------
# 1. The archive really defines the symbol (the AUDIT_1.0.md §5.6 measurement)
# ---------------------------------------------------------------------------

def test_archive_exports_abi_version_symbol():
    """`nm ... | grep pengu_abi_version` finds a *defined* symbol.

    C2: delete the definition from `pengu_runtime.c` and rebuild — the archive
    stops defining it and this test fails with an empty mapping.
    """
    assert RUNTIME_A.is_file(), (
        f"{RUNTIME_A} not built; run build_runtime.py"
    )
    defined = _nm_defined_symbols(RUNTIME_A)
    assert ABI_SYMBOL in defined, (
        f"{ABI_SYMBOL} is not defined in {RUNTIME_A.name}; "
        f"the link-time ABI pin cannot work. Defined symbols: "
        f"{sorted(k for k in defined if 'abi' in k.lower()) or '(none matching abi)'}"
    )
    assert defined[ABI_SYMBOL] in {"T", "t"}, (
        f"{ABI_SYMBOL} must be code (T/t), got {defined[ABI_SYMBOL]!r}"
    )


# ---------------------------------------------------------------------------
# 2. The exported symbol returns the header's version, measured by executing it
# ---------------------------------------------------------------------------

def test_exported_symbol_returns_the_header_version(tmp_path):
    """Compile a C harness that calls `pengu_abi_version()` and compares it.

    This proves the archive's symbol agrees with the `PENGU_ABI_VERSION` the
    header advertises — the property `_Static_assert` cannot check, because it
    never sees the archive.
    """
    src = tmp_path / "abi_probe.c"
    src.write_text(
        '#include "pengu_runtime.h"\n'
        "#include <stdio.h>\n"
        "int main(void) {\n"
        "  int linked = pengu_abi_version();\n"
        "  printf(\"linked=%d header=%d\\n\", linked, (int)PENGU_ABI_VERSION);\n"
        "  return linked == (int)PENGU_ABI_VERSION ? 0 : 1;\n"
        "}\n",
        encoding="utf-8",
    )
    exe = tmp_path / ("abi_probe.exe" if sys.platform == "win32" else "abi_probe")
    cmd = [
        _cc(), str(src),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
        f"-L{BUILD_LIB}",
    ] + runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]
    build = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, f"harness failed to link:\n{build.stderr}"

    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, (
        f"archive ABI version disagrees with the header: {run.stdout}{run.stderr}"
    )


# ---------------------------------------------------------------------------
# 3. A normal program still links and runs (the pin is not a new requirement)
# ---------------------------------------------------------------------------

def test_minimal_pengu_program_links_and_runs():
    """The pin must not break the ordinary build path."""
    res = compile_run(
        "weave main into int:\n"
        "    return 0\n",
        tag="abi_ok",
    )
    assert res.returncode == 0


# ---------------------------------------------------------------------------
# 4. THE property: a bundle cannot link against an archive without the symbol
# ---------------------------------------------------------------------------

def _build_stale_archive(tmp_path: Path) -> Path:
    """Builds a `libpengu_runtime.a` as it looked *before* item 3.5.

    The runtime source is compiled with the new symbol renamed away, which is
    exactly what an archive built from the pre-3.5 `pengu_runtime.c` looks like:
    every other symbol present, `pengu_abi_version` absent. Renaming via `-D`
    keeps this honest — it uses the real translation unit and real flags, and no
    source is edited.

    A copy of the *current* `pengu_runtime.h` is placed next to it so the bundle's
    header view is unchanged; only the archive is stale.
    """
    sys.path.insert(0, str(REPO / "tests"))
    from tests.test_runtime_c99 import _runtime_flags  # noqa: PLC0415 - lazy import

    obj = tmp_path / "pengu_runtime_stale.o"
    cmd = [
        _cc(), "-O2",
        "-Dpengu_abi_version=pengu_abi_version_pre_item_3_5",
        *_runtime_flags(),
        "-c", str(RUNTIME_C), "-o", str(obj),
    ]
    res = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert res.returncode == 0, f"could not build the stale runtime object:\n{res.stderr}"

    stale_dir = tmp_path / "stale_lib"
    stale_dir.mkdir()
    stale_a = stale_dir / "libpengu_runtime.a"
    ar = shutil.which("ar") or "ar"
    res = subprocess.run([ar, "rcs", str(stale_a), str(obj)],
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"ar failed:\n{res.stderr}"
    assert ABI_SYMBOL not in _nm_defined_symbols(stale_a), (
        "the simulated stale archive still defines the symbol; "
        "the test would not prove anything"
    )
    return stale_a


def _link_bundle(bundle_c: Path, tmp_path: Path, name: str,
                 stale_dir: Path | None = None):
    """Links `bundle_c` into an executable; returns the CompletedProcess."""
    exe = tmp_path / name
    cmd = [
        _cc(), str(bundle_c),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
    ]
    if stale_dir is not None:
        # Search the stale archive FIRST so it shadows the real one.
        cmd.append(f"-L{stale_dir}")
    cmd.append(f"-L{BUILD_LIB}")
    cmd += runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600)


def test_stale_archive_without_symbol_fails_to_link(tmp_path):
    """The whole point of 3.5: a stale archive must fail the link, not link.

    The same generated bundle is linked twice — once against the simulated
    pre-3.5 archive (must fail with an undefined reference) and once against the
    real one (must succeed). The control rules out "the command was just wrong",
    so the failure is attributable to the missing symbol alone.

    C2: remove the pin from `pengu_codegen.py` and the stale link *succeeds*,
    which fails this test.
    """
    bundle_c = tmp_path / "bundle.c"
    bundle_c.write_text(
        gen_bundle("weave main into int:\n    return 0\n", filename="abi_stale.pengu"),
        encoding="utf-8",
    )

    stale_a = _build_stale_archive(tmp_path)
    stale_dir = stale_a.parent

    stale = _link_bundle(bundle_c, tmp_path, "bin_stale", stale_dir=stale_dir)
    assert stale.returncode != 0, (
        "a bundle linked against an archive without pengu_abi_version(); the "
        "link-time ABI pin is not working (regression of item 3.5)"
    )
    diagnostics = stale.stderr + stale.stdout
    assert ABI_SYMBOL in diagnostics, (
        f"link failed, but not because of {ABI_SYMBOL}:\n{diagnostics}"
    )

    # Control: the identical bundle links cleanly against the shipped archive.
    ok = _link_bundle(bundle_c, tmp_path, "bin_ok")
    assert ok.returncode == 0, (
        f"the same bundle failed to link against the real archive — the "
        f"negative result above is not attributable to the missing symbol:\n{ok.stderr}"
    )
