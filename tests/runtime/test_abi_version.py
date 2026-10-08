"""Phase 3 item 3.5 — the runtime ABI version is exported and verifiable.

`SECURITY.md` ("Runtime ABI pinning") claimed that a stale
`libpengu_runtime.a` fails at compile time instead of corrupting memory. Before
this item the claim was false: `pengu_codegen.py` only emitted
`_Static_assert(PENGU_ABI_VERSION == N)`, which compares the **codegen's**
expectation against the **header** and never looks at the archive. AUDIT_1.0.md
§5.6 measured the consequence —

    $ nm build/lib/libpengu_runtime.a | grep -i abi
    (empty)

— so a bundle and an ABI-mismatched archive linked silently and reinterpreted
struct fields at the wrong offsets.

What this item delivers: `pengu_abi_version()` is now a real, exported
object-file symbol that reports the archive's ABI version, and `SECURITY.md` /
`docs/ABI.md` state precisely what is and is not enforced.

What 3.5 deliberately did **not** do: make every generated bundle reference the
symbol. That was tried first and broke `pengu build` on every fresh project,
because the CLI only added `-lpengu_runtime` when `pengu.toml` asked for it and
a fresh `pengu init` project builds header-only. **Item 4.17 closed that**: the
CLI now links the runtime unconditionally (`pengu_project.py`) and the codegen
emits a `__attribute__((used))` pin, so an archive with no referenced symbol is
no longer dropped and a stale `.a` fails at link time. The tests below measure
that, and `test_stale_archive_fails_to_link` replaces the 3.5-era
`test_bundle_links_without_the_runtime_archive` constraint.

Scope of the guarantee (measured): it holds under **gcc** and **clang**, the
release compilers. Under **tcc** the output is stripped, so `nm` cannot verify
the pin; see `docs/ABI.md`.

Rule C1: every test **measures** (`nm`), **compiles+links+runs**, or both.
"""

import re
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


def _header_abi_version() -> int:
    """The `PENGU_ABI_VERSION` the header advertises, read from the source."""
    header = (REPO / "pengu_runtime.h").read_text(encoding="utf-8")
    match = re.search(r"^#define\s+PENGU_ABI_VERSION\s+(\d+)", header, re.MULTILINE)
    assert match, "PENGU_ABI_VERSION is not defined in pengu_runtime.h"
    return int(match.group(1))


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
    stops defining it and this test fails.
    """
    assert RUNTIME_A.is_file(), f"{RUNTIME_A} not built; run build_runtime.py"
    defined = _nm_defined_symbols(RUNTIME_A)
    assert ABI_SYMBOL in defined, (
        f"{ABI_SYMBOL} is not defined in {RUNTIME_A.name}; "
        f"symbols matching 'abi': {sorted(k for k in defined if 'abi' in k.lower()) or '(none)'}"
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
# 3. A normal program still links and runs
# ---------------------------------------------------------------------------

def test_minimal_pengu_program_links_and_runs():
    """The ordinary build path still works end to end."""
    res = compile_run("weave main into int:\n    return 0\n", tag="abi_ok")
    assert res.returncode == 0


def test_bundle_references_the_runtime_abi(tmp_path):
    """Every bundle references `pengu_abi_version`, so the archive is linked.

    Item 4.17 completes what 3.5 left open. The CLI now always adds
    `-lpengu_runtime` *and* `pengu_codegen.py` emits a `__attribute__((used))`
    pin, without which a static archive with no referenced symbols is simply
    dropped by the linker (measured: `nm` showed 0 runtime symbols even with
    `-lpengu_runtime` on the command line).

    C2: remove the `_pengu_abi_pin` emission and this measurement drops to 0
    symbols.
    """
    bundle_c = tmp_path / "bundle.c"
    bundle_c.write_text(
        gen_bundle("weave main into int:\n    return 0\n", filename="pinned.pengu"),
        encoding="utf-8",
    )
    exe = tmp_path / ("pinned.exe" if sys.platform == "win32" else "pinned")
    cmd = [
        _cc(), str(bundle_c),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
        f"-L{BUILD_LIB}",
        *runtime_link_flags(), *runtime_tail_flags(),
        "-o", str(exe),
    ]
    build = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stderr
    nm = shutil.which("nm")
    assert nm, "nm is required for this measurement"
    symbols = subprocess.run([nm, str(exe)], capture_output=True, text=True, timeout=120)
    assert re.search(rf"\b{ABI_SYMBOL}\b", symbols.stdout), (
        "the linked binary does not reference the runtime ABI symbol:\n"
        + symbols.stdout
    )
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0


def test_bundle_references_the_runtime_abi_release_profile(tmp_path):
    """The pin must survive -O2: `__attribute__((used))` is what keeps it."""
    bundle_c = tmp_path / "bundle.c"
    bundle_c.write_text(
        gen_bundle("weave main into int:\n    return 0\n", filename="pinned_o2.pengu"),
        encoding="utf-8",
    )
    exe = tmp_path / ("pinned_o2.exe" if sys.platform == "win32" else "pinned_o2")
    cmd = [
        _cc(), "-O2", str(bundle_c),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
        f"-L{BUILD_LIB}",
        *runtime_link_flags(), *runtime_tail_flags(),
        "-o", str(exe),
    ]
    build = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stderr
    nm = shutil.which("nm")
    symbols = subprocess.run([nm, str(exe)], capture_output=True, text=True, timeout=120)
    assert re.search(rf"\b{ABI_SYMBOL}\b", symbols.stdout), symbols.stdout


def test_stale_archive_fails_to_link(tmp_path):
    """An archive without the symbol must fail the link, naming it.

    This is the property `SECURITY.md` claims: a `libpengu_runtime.a` built
    against a different ABI cannot silently link.
    """
    bundle_c = tmp_path / "bundle.c"
    bundle_c.write_text(
        gen_bundle("weave main into int:\n    return 0\n", filename="stale.pengu"),
        encoding="utf-8",
    )
    stale_dir = tmp_path / "stale"
    stale_dir.mkdir()
    stub_c = stale_dir / "stub.c"
    stub_c.write_text("int pengu_stub_only(void) { return 0; }\n", encoding="utf-8")
    stub_o = stale_dir / "stub.o"
    subprocess.run([_cc(), "-c", str(stub_c), "-o", str(stub_o)], check=True, timeout=300)
    stale_a = stale_dir / "libpengu_runtime.a"
    subprocess.run(["ar", "rcs", str(stale_a), str(stub_o)], check=True, timeout=300)

    exe = tmp_path / ("stale.exe" if sys.platform == "win32" else "stale_bin")
    cmd = [
        _cc(), str(bundle_c),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
        f"-L{stale_dir}", f"-L{BUILD_LIB}",
        *runtime_link_flags(), *runtime_tail_flags(),
        "-o", str(exe),
    ]
    build = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    assert build.returncode != 0, "a stale archive linked silently"
    combined = build.stdout + build.stderr
    assert ABI_SYMBOL in combined, combined


# ---------------------------------------------------------------------------
# 4. The link-time hook itself: an archive without the symbol fails the link
# ---------------------------------------------------------------------------

def _build_stale_archive(tmp_path: Path) -> Path:
    """Builds a `libpengu_runtime.a` as it looked *before* item 3.5.

    The runtime source is compiled with the new symbol renamed away, which is
    exactly what an archive built from the pre-3.5 `pengu_runtime.c` looks like:
    every other symbol present, `pengu_abi_version` absent. Renaming via `-D`
    keeps this honest — it uses the real translation unit and real flags, and no
    source is edited.
    """
    from tests.runtime.test_runtime_c99 import _runtime_flags  # noqa: PLC0415 - lazy import

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


def _link_consumer(consumer_c: Path, tmp_path: Path, name: str, stale_dir=None):
    """Links a C consumer; `stale_dir` is searched before the real archive."""
    exe = tmp_path / name
    cmd = [_cc(), str(consumer_c),
           f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}"]
    if stale_dir is not None:
        cmd.append(f"-L{stale_dir}")
    cmd.append(f"-L{BUILD_LIB}")
    cmd += runtime_link_flags() + runtime_tail_flags() + ["-o", str(exe)]
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600)


def test_consumer_of_the_symbol_cannot_link_a_stale_archive(tmp_path):
    """The link-time hook works: an archive without the symbol fails the link.

    The bundle does not reference the symbol on its own (see the module
    docstring), so this uses an explicit consumer — the same shape any build that
    links the archive and wants the ABI gate can adopt.

    The control rules out "the command was just wrong": the identical consumer
    links and runs against the real archive, exiting with the ABI version.

    C2: remove the definition from `pengu_runtime.c` (and rebuild) and the
    *control* link fails too, so the negative result is no longer attributable to
    the staleness of the archive.
    """
    consumer = tmp_path / "consumer.c"
    consumer.write_text(
        '#include "pengu_runtime.h"\n'
        "int main(void) { return pengu_abi_version(); }\n",
        encoding="utf-8",
    )

    stale_a = _build_stale_archive(tmp_path)

    stale = _link_consumer(consumer, tmp_path, "consumer_stale", stale_dir=stale_a.parent)
    assert stale.returncode != 0, (
        "an archive without pengu_abi_version() linked successfully; the ABI "
        "version cannot be used to detect a stale archive"
    )
    diagnostics = stale.stderr + stale.stdout
    assert ABI_SYMBOL in diagnostics, (
        f"link failed, but not because of {ABI_SYMBOL}:\n{diagnostics}"
    )

    ok = _link_consumer(consumer, tmp_path, "consumer_ok")
    assert ok.returncode == 0, (
        f"the same consumer failed to link against the real archive — the "
        f"negative result above is not attributable to the missing symbol:\n{ok.stderr}"
    )
    exe = tmp_path / "consumer_ok"
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    expected_abi = _header_abi_version()
    assert run.returncode == expected_abi, (
        f"the control binary should exit with the ABI version ({expected_abi}), "
        f"got {run.returncode}"
    )
