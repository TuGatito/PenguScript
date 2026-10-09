"""Roadmap Phase 2 / §2.1.h and Phase 8 / item 8.1 (blocker B10) — `--strict-c99`.

Why this file was rewritten
---------------------------
It used to approve "portable C99" by inspecting text: it read the generated
bundle and asserted the absence of two chosen substrings (``__extension__`` and
``__auto_type``). Absence of two substrings is not a property of the output.  Item 8.1
(B10) turns that into a compiler invocation, and the compiler immediately says
something the text could not: `--strict-c99` still emits **statement
expressions** for std-importing programs (roadmap 3.3, deferred), so
`-std=c99 -pedantic-errors` rejects the bundle — and, worse, for a second group
of programs it emits **undeclared identifiers**, which is invalid C even without
`-pedantic-errors`.

Measured classification of all 56 `tests/std_programs/test_*.pengu` programs
built with `--strict-c99` (command and counts in AUDIT_1.0_FASE8.md):

* 23 compile clean *and run* under `-std=c99 -pedantic-errors` -> asserted here, green;
* 1 compiles clean but miscompiles at runtime (finding F8-N4a) -> xfail;
* 14 are blocked only by statement expressions (B5 / roadmap 3.3) -> xfail;
* 18 hit the strict-mode codegen bug (finding F8-N4) -> xfail.

`xfail(strict=True)` everywhere, so when either blocker is fixed the affected
rows become `xpass` and this file fails until they are promoted to assertions.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO

#: Extra flags the project itself uses so that GCC 14+ does not turn the
#: runtime's implicit declarations into hard errors (see ``tests/conftest.py``).
_IMPLICIT_DECL_FLAGS = [
    "-Wno-error=implicit-function-declaration",
    "-Wno-error=implicit-int",
    "-Wno-error=int-conversion",
]

_STD_PROGRAMS = REPO / "tests" / "std_programs"

#: Measured with the real toolchain.  The three classes are not guesses: the
#: counts are the compiler's own `error:` counts for each bundle.
CLEAN = [  # 0 pedantic errors, 0 hard errors, runs clean
    "test_arithmancy.pengu", "test_arithmancy_extended.pengu",
    "test_chronicle.pengu", "test_chronicle_extended.pengu",
    "test_compass.pengu", "test_compass_extended.pengu",
    "test_filum.pengu", "test_filum_extended.pengu",
    "test_loom.pengu",
    "test_lot.pengu", "test_lot_extended.pengu",
    "test_oracle.pengu", "test_parchment.pengu", "test_parchment_extended.pengu",
    "test_regulus.pengu", "test_regulus_extended.pengu",
    "test_rites.pengu", "test_scrolls_extended.pengu",
    "test_spark.pengu", "test_spark_extended.pengu",
    "test_trial.pengu", "test_ward.pengu", "test_ward_extended.pengu",
]

#: Finding F8-N4a — the dangerous class: the strict bundle *compiles* cleanly
#: under `-std=c99 -pedantic-errors` and then **miscompiles at runtime**.  The
#: default build of `test_loom_extended` prints "loom extended: OK" and exits 0;
#: the `--strict-c99` build aborts with
#: `[PENGU] Index out of bounds: 1 (length 1) at std/loom.pengu:347`
#: (in `loom_zip_longest`).  Same source, same runtime, different codegen.
STRICT_MISCOMPILES = [
    "test_loom_extended.pengu",
]

#: Blocked by B5 / roadmap 3.3: the strict bundle still carries `({ ... })`
#: statement expressions (85-98 pedantic errors) but is otherwise valid C.
B5_STATEMENT_EXPRESSIONS = [
    "test_atlas.pengu", "test_atlas_extended.pengu", "test_atlas_generic_matrix.pengu",
    "test_atlas_ii.pengu", "test_atlas_is.pengu", "test_atlas_sb.pengu",
    "test_atlas_sf.pengu", "test_atlas_ss.pengu",
    "test_coven.pengu", "test_coven_extended.pengu",
    "test_ffi.pengu", "test_ffi_extended.pengu",
    "test_oracle_extended.pengu", "test_rites_extended.pengu",
]

#: Finding F8-N4: strict-mode codegen hoists a comprehension into C that
#: references loop variables it never declared (`'k' undeclared`), so the bundle
#: is invalid C.  13 hard errors for every program in this class, with or
#: without `-pedantic-errors`.
STRICT_CODEGEN_UNDECLARED = [
    "test_all.pengu", "test_archivum.pengu", "test_archivum_extended.pengu",
    "test_cipher.pengu", "test_cipher_extended.pengu",
    "test_invoke.pengu", "test_invoke_extended.pengu",
    "test_ledger.pengu", "test_ledger_extended.pengu",
    "test_precis.pengu", "test_precis_extended.pengu",
    "test_scrolls.pengu", "test_seal.pengu", "test_seal_extended.pengu",
    "test_tally.pengu", "test_tally_extended.pengu",
    "test_whisper.pengu", "test_whisper_extended.pengu",
]

_B5_REASON = ("B5 / roadmap 3.3: --strict-c99 still emits ({ ... }) statement "
              "expressions, so -std=c99 -pedantic-errors rejects the bundle")
_CODEGEN_REASON = ("F8-N4: --strict-c99 emits undeclared comprehension variables, "
                   "invalid C with or without -pedantic-errors")
_MISCOMPILE_REASON = ("F8-N4a: the strict bundle compiles clean and then crashes at "
                      "runtime (bounds check in std.loom's zip_longest), while the "
                      "default build of the same program exits 0")

#: F8-N4a was measured with Linux GCC.  MinGW's GCC and Apple's clang run the same
#: strict bundle cleanly, so there the marker would turn a pass into a failure.
_MISCOMPILE_MEASURED_HERE = os.name != "nt" and sys.platform != "darwin"

#: The B5 class is a *measurement* of the C compiler, not of PenguScript: the
#: Linux CI GCC rejects `({ ... })` statement expressions under
#: `-std=c99 -pedantic-errors`, but MinGW's GCC accepts them, so every row of
#: `test_strict_c99_std_program_blocked_by_b5` XPASSes there and
#: `xfail(strict=True)` turns the classification into a failure.  The class is
#: still enforced where it was measured (Linux and macOS).
_MEASURED_WITH_LINUX_GCC = pytest.mark.skipif(
    os.name == "nt",
    reason="the --strict-c99 classification was measured with Linux GCC; MinGW's "
           "GCC accepts statement expressions under -pedantic-errors",
)


def _write_project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "weave main into int:\n"
        "  var xs as list of int is [1, 2, 3]\n"
        "  var m as maybe int is some 7\n"
        "  var v as int is m or else 0\n"
        "  return v\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.yaml").write_text(
        "project:\n"
        "  name: strict_demo\n"
        "  entry: src/main.pengu\n"
        "build:\n"
        "  output: c\n",
        encoding="utf-8",
    )


def _run_build(tmp_path, *extra):
    cmd = [
        sys.executable, str(REPO / "pengu_project.py"), "build",
        "--config", str(tmp_path),
        "--output", str(tmp_path / "build" / "bundle.c"),
        *extra,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(tmp_path))


def _bundle(tmp_path, program: Path) -> str:
    """Bundles a std program with the real CLI and returns the generated C."""
    out = tmp_path / f"{program.stem}.c"
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build",
         "--entry", str(program), "--output", str(out), "--strict-c99"],
        capture_output=True, text=True, timeout=600, cwd=str(REPO),
    )
    assert res.returncode == 0, f"strict build failed:\n{res.stdout}\n{res.stderr}"
    return out.read_text(encoding="utf-8")


def test_cli_help_lists_phase2_flags():
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert "--strict-c99" in res.stdout
    assert "--target-compiler" in res.stdout


def test_cli_strict_c99_bundle_compiles_and_runs(tmp_path, compile_c):
    """The flag is real: the CLI's bundle compiles as C99 and the program runs.

    The fixture program returns ``v``, i.e. 7, which is the value `just 7 or else 0`
    has to produce. Asserting the *exit code* rather than "it started" keeps the
    semantics in the gate: strict mode must not change what the program computes.
    """
    _write_project(tmp_path)
    res = _run_build(tmp_path, "--strict-c99")
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"
    bundle = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    exe = compile_c(bundle, name="strict_demo", std="c99")
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 7, (
        f"strict program returned {run.returncode}, expected 7 from `m or else 0`\n{run.stderr}"
    )


def test_strict_mode_is_measurably_stricter_than_the_default(tmp_path, compile_c):
    """Non-vacuity: the same program's *default* bundle must be rejected.

    If the default output were accepted under `-pedantic-errors` too, the test
    above would prove nothing about `--strict-c99`.  "Rejected by the compiler"
    is the observable, not the absence of a substring.

    ``-D__extension__=`` is necessary for that observable to exist: GCC's
    ``__extension__`` silences ``-pedantic`` for the statement expression it
    guards, so the default bundle passes `-pedantic-errors` untouched (measured:
    0 errors with the keyword, 9 without).  Neutralising it asks the compiler
    whether the bundle relies on a GNU extension at all.
    """
    _write_project(tmp_path)
    assert _run_build(tmp_path).returncode == 0
    default_bundle = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    try:
        compile_c(default_bundle, name="default_bundle", std="c99", pedantic=True,
                  syntax_only=True, extra=["-D__extension__=", "-fmax-errors=1"])
    except AssertionError:
        return
    # The premise is compiler-specific: MinGW's GCC and Apple's clang do not turn
    # the neutralised `__extension__` into a hard `-pedantic` error, so the
    # observable this test needs does not exist there.  The check was measured
    # with Linux GCC and stays enforced wherever it holds.
    pytest.skip("this C compiler still accepts the statement expression with "
                "-D__extension__=; the non-vacuity check was measured with Linux GCC")


def test_every_std_program_is_classified():
    """A new std program must be classified, not silently skipped."""
    on_disk = {p.name for p in _STD_PROGRAMS.glob("test_*.pengu")}
    classified = (set(CLEAN) | set(B5_STATEMENT_EXPRESSIONS)
                  | set(STRICT_CODEGEN_UNDECLARED) | set(STRICT_MISCOMPILES))
    assert on_disk - classified == set(), (
        f"these std programs are not classified: {sorted(on_disk - classified)}"
    )
    assert classified - on_disk == set(), (
        f"the classification lists programs that do not exist: {sorted(classified - on_disk)}"
    )
    assert len(classified) == 56, f"expected the 56 test programs, got {len(classified)}"


@pytest.mark.parametrize("name", CLEAN)
def test_strict_c99_std_program_is_pedantically_clean(name, tmp_path, compile_c):
    """The 23 programs `--strict-c99` really does emit portable, correct C99 for.

    Compiled *and executed*: passing `-pedantic-errors` is necessary but not
    sufficient, and running is exactly what exposed F8-N4a below.
    """
    bundle = _bundle(tmp_path, _STD_PROGRAMS / name)
    exe = compile_c(bundle, name=Path(name).stem, std="c99", pedantic=True,
                    extra=_IMPLICIT_DECL_FLAGS)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, f"{name} failed at runtime: rc={run.returncode}\n{run.stderr}"


@pytest.mark.xfail(strict=True, condition=_MISCOMPILE_MEASURED_HERE,
                   reason=_MISCOMPILE_REASON)
@pytest.mark.parametrize("name", STRICT_MISCOMPILES)
def test_strict_c99_std_program_does_not_miscompile(name, tmp_path, compile_c):
    """Finding F8-N4a: strict mode compiles cleanly but changes behaviour.

    The bug was measured with Linux GCC; where the toolchain does not reproduce
    it, the same assertion is a plain expectation and the test must pass rather
    than XPASS into a failure.
    """
    bundle = _bundle(tmp_path, _STD_PROGRAMS / name)
    exe = compile_c(bundle, name=Path(name).stem, std="c99", pedantic=True,
                    extra=_IMPLICIT_DECL_FLAGS)
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, f"{name} failed at runtime: rc={run.returncode}\n{run.stderr}"


@_MEASURED_WITH_LINUX_GCC
@pytest.mark.xfail(strict=True, reason=_B5_REASON)
@pytest.mark.parametrize("name", B5_STATEMENT_EXPRESSIONS)
def test_strict_c99_std_program_blocked_by_b5(name, tmp_path, compile_c):
    """Blocked only by the deferred statement-expression work (roadmap 3.3)."""
    bundle = _bundle(tmp_path, _STD_PROGRAMS / name)
    compile_c(bundle, name=Path(name).stem, std="c99", pedantic=True,
              syntax_only=True, extra=_IMPLICIT_DECL_FLAGS + ["-fmax-errors=1"])


@pytest.mark.xfail(strict=True, reason=_CODEGEN_REASON)
@pytest.mark.parametrize("name", STRICT_CODEGEN_UNDECLARED)
def test_strict_c99_std_program_blocked_by_strict_codegen(name, tmp_path, compile_c):
    """Finding F8-N4: the strict bundle is not valid C at all."""
    bundle = _bundle(tmp_path, _STD_PROGRAMS / name)
    compile_c(bundle, name=Path(name).stem, std="c99",
              syntax_only=True, extra=_IMPLICIT_DECL_FLAGS + ["-fmax-errors=1"])
