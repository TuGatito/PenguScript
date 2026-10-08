"""Roadmap Phase 8 / item 8.1 (blocker B10) — the MSVC dialect is *compiled*.

`tests/codegen/test_attributes_msvc_text.py` pins the text the dialect mapper produces.
That is a legitimate unit test of the mapper, but it is not evidence that MSVC
accepts the output, and treating it as such is exactly what blocker B10 is:
the gate went green over output that does not compile.

Measured while converting this gate (finding F8-N3): the msvc dialect emitted
the GNU **trailing** attribute position for a field —

    int32_t head __declspec(align(8));

which `cl.exe` and clang's MS mode both reject ("expected ';' at end of
declaration list"). The text assertion ``"__declspec(align(16))" in c`` was
satisfied either way, so no test noticed.

This file compiles the bundle with a compiler that actually parses MSVC syntax:

* ``clang -fdeclspec -fms-extensions`` wherever clang exists — it understands
  ``__declspec``, ``#pragma pack`` and ``__forceinline``, and it is the only
  MSVC-syntax oracle available on the Linux/macOS runners;
* ``cl.exe /Zs`` (syntax check only, so no runtime library is needed) on a
  Windows runner that has Visual Studio.

The third test is a **negative control**: it re-inserts the pre-fix emission and
requires the same invocation to fail. Without it this file could be a gate that
cannot fail, which is the one thing item 8.1 forbids.
"""

import re
import shutil
import subprocess

import pytest

from tests.conftest import BUILD_DIR, BUILD_INCLUDE, REPO, gen_bundle

#: Exercises every attribute the msvc dialect has to translate: inline, cold,
#: deprecated, packed and align on both a struct and a *field* (the field is what
#: regressed), plus an aligned array field (different emission path).
_SRC = """\
@inline
weave add with a as int, b as int into int:
  a + b

@cold
weave log_error with code as int:
  var x is code

@deprecated("use modern instead")
weave old into int:
  42

@packed
rune Packet:
  tag as int
  length as int

@align(16)
rune Aligned:
  @align(8)
  head as int
  @align(8)
  tail as array of int with size 4

weave main into int:
  var p as Packet is with tag is 1, length is 2
  var a as Aligned is with head is 1, tail is [0, 0, 0, 0]
  return calling add with p.tag, a.head
"""

#: The correct (MSVC) emission: the declspec precedes the declared name. The
#: substitution in the negative control below rewrites it back to the pre-fix
#: trailing form, so this pattern is also what proves the fix is in the bundle.
_PREFIX_DECLSPEC_FIELD = re.compile(
    r"__declspec\(align\((\d+)\)\) (int32_t \w+(?:\[\d+\])?);",
)

#: The pre-fix emission that cl.exe/clang-MS reject ("expected ';' at end of
#: declaration list").
_TRAILING_DECLSPEC_FIELD = re.compile(
    r"int32_t \w+(?:\[\d+\])? __declspec\(align\(\d+\)\);",
)


def _msvc_bundle() -> str:
    return gen_bundle(_SRC, target_compiler="msvc")


def _clang_ms_available() -> bool:
    return shutil.which("clang") is not None


@pytest.mark.skipif(not _clang_ms_available(), reason="clang is required for the MSVC-syntax oracle")
def test_msvc_dialect_compiles_with_clang_ms_extensions(compile_c):
    """The msvc bundle passes a compiler that parses MSVC syntax."""
    compile_c(_msvc_bundle(), name="msvc_dialect", std="c11", syntax_only=True,
              cc=shutil.which("clang"),
              extra=["-fdeclspec", "-fms-extensions", "-Werror=implicit-function-declaration"])


@pytest.mark.skipif(not _clang_ms_available(), reason="clang is required for the MSVC-syntax oracle")
def test_msvc_field_align_is_emitted_before_the_declarator(compile_c):
    """F8-N3: ``__declspec`` precedes the name, both for scalars and arrays.

    Asserted by compiling, not by matching: the negative control below proves the
    compiler is what decides this.
    """
    bundle = _msvc_bundle()
    compile_c(bundle, name="msvc_field_align", std="c11", syntax_only=True,
              cc=shutil.which("clang"), extra=["-fdeclspec", "-fms-extensions"])
    assert _PREFIX_DECLSPEC_FIELD.search(bundle) is not None, (
        "no aligned field found: this test would pass vacuously"
    )
    assert _TRAILING_DECLSPEC_FIELD.search(bundle) is None, (
        "a trailing __declspec survived; the pre-fix form is not valid MSVC"
    )


@pytest.mark.skipif(not _clang_ms_available(), reason="clang is required for the MSVC-syntax oracle")
def test_the_msvc_gate_rejects_the_pre_fix_emission(compile_c):
    """Negative control: reverting the fix must make this file fail.

    This is the C2 evidence for the fix, automated: it mutates the generated C
    back to the trailing-attribute form and requires clang's MS mode to reject
    it. If the gate ever stops having teeth, this test fails.
    """
    bundle = _msvc_bundle()
    mutant, count = _PREFIX_DECLSPEC_FIELD.subn(r"\2 __declspec(align(\1));", bundle)
    assert count >= 2, "the negative control no longer rewrites both aligned fields"
    assert _TRAILING_DECLSPEC_FIELD.search(mutant) is not None

    with pytest.raises(AssertionError, match="C compilation failed"):
        compile_c(mutant, name="msvc_mutant", std="c11", syntax_only=True,
                  cc=shutil.which("clang"),
                  extra=["-fdeclspec", "-fms-extensions"])


@pytest.mark.skipif(shutil.which("cl") is None, reason="MSVC (cl.exe) not available on this runner")
def test_msvc_dialect_compiles_with_cl_exe(tmp_path):
    """End-to-end with the real ``cl.exe`` (syntax check only: ``/Zs``).

    ``/Zs`` parses and type-checks without linking, so this needs no MSVC-built
    runtime archive — which is also why it can run on a plain windows-latest
    runner. It is skipped everywhere else; see item 8.11 for why the project does
    not *claim* MSVC support on the strength of a job that may never run.
    """
    src = tmp_path / "msvc_dialect.c"
    src.write_text(_msvc_bundle(), encoding="utf-8")
    cmd = ["cl", "/nologo", "/Zs", "/std:c11", str(src),
           f"/I{REPO}", f"/I{BUILD_DIR}", f"/I{BUILD_INCLUDE}"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, f"cl.exe rejected the msvc bundle:\n{res.stdout}\n{res.stderr}"
