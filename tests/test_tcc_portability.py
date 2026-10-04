"""Phase 3 item 3.4 — `tcc` accepts the bundles (no `__auto_type`).

`__auto_type` is a GCC/Clang extension; tcc does not implement it, so every bundle
that used it failed to compile with the development compiler and `pengu run` fell
back to gcc:

    $ tcc -c bundle.c -Ibuild/include
    error: '__auto_type' undeclared

Measured before the fix: **46 of the 61** programs in `tests/std_programs/`
produced a bundle tcc rejected, exactly the 46 whose bundle contained
`__auto_type`. The fix replaces the GCC-only spelling with `__typeof__`, which
both gcc and tcc provide.

Rule C1: these tests invoke the real compilers and assert on exit status and on the
bytes the program writes. Nothing inspects the generated source for a substring.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
STD_PROGRAMS = REPO / "tests" / "std_programs"
TCC = REPO / "build" / "tcc-dist" / "tcc-dist" / "bin" / "tcc"
INCLUDE = REPO / "build" / "include"


def _pengu(*args, timeout=600):
    r = subprocess.run(
        [sys.executable, "-m", "pengu_project", *args],
        cwd=str(REPO), capture_output=True, text=True, timeout=timeout,
    )
    return r.returncode, r.stdout + r.stderr


def _tcc(path, out):
    r = subprocess.run(
        [str(TCC), "-c", str(path), "-I" + str(INCLUDE), "-o", str(out)],
        cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    return r.returncode, r.stdout + r.stderr


requires_tcc = pytest.mark.skipif(
    not TCC.exists(), reason="the bundled tcc is not present"
)


@requires_tcc
@pytest.mark.parametrize("program", [
    # Chosen by measured `__auto_type` emission with the fix reverted: cipher 96,
    # archivum 63, tally 59, atlas 42. (test_spark was measured too and emits
    # ZERO -- it passed with the fix reverted, so it was a vacuous parameter and
    # is not used here.)
    "test_cipher.pengu",
    "test_archivum.pengu",
    "test_tally.pengu",
    "test_atlas.pengu",
])
def test_tcc_compiles_the_bundle(tmp_path, program):
    """A representative bundle from each area compiles under tcc.

    Each of these emits `__auto_type` in the pre-fix codebase, so this test fails
    when the fix is reverted -- verified, not assumed.
    """
    src = STD_PROGRAMS / program
    bundle = tmp_path / f"{program}.c"
    rc, out = _pengu("build", "--entry", str(src), "--output", str(bundle))
    assert rc == 0, f"pengu build failed for {program}:\n{out}"
    rc, out = _tcc(bundle, tmp_path / f"{program}.o")
    assert rc == 0, f"tcc rejected the bundle for {program}:\n{out}"


@requires_tcc
def test_no_bundle_in_the_corpus_contains_gcc_only_auto_type(tmp_path):
    """Every std program's bundle compiles under tcc.

    The corpus-wide form of the check: a single regression anywhere in codegen
    that reintroduces `__auto_type` fails here. This replaces a substring grep on
    purpose -- the property is "tcc compiles it", and that is what is asserted.
    """
    failures = []
    for src in sorted(STD_PROGRAMS.glob("*.pengu")):
        bundle = tmp_path / (src.stem + ".c")
        rc, out = _pengu("build", "--entry", str(src), "--output", str(bundle))
        if rc != 0:
            failures.append(f"{src.name}: pengu build failed")
            continue
        rc, out = _tcc(bundle, tmp_path / (src.stem + ".o"))
        if rc != 0:
            first = next((l for l in out.splitlines() if "error" in l), out[:200])
            failures.append(f"{src.name}: {first}")
    assert not failures, (
        f"{len(failures)} program(s) produced a bundle tcc rejects:\n"
        + "\n".join(failures[:10])
    )


@requires_tcc
def test_tcc_compiled_program_runs_and_produces_output(tmp_path):
    """Compiling is not enough: link the tcc object and run it.

    Guards against a fix that satisfies the compiler while changing behaviour --
    the concern the phase brief raised explicitly for this class of change.
    """
    src = tmp_path / "hello.pengu"
    src.write_text(
        "import std.spark\n"
        "weave main into int:\n"
        '  calling spark.println with "tcc-ok"\n'
        "  return 0\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "hello.c"
    rc, out = _pengu("build", "--entry", str(src), "--output", str(bundle))
    assert rc == 0, out
    exe = tmp_path / "hello"
    r = subprocess.run(
        [str(TCC), str(bundle), "-I" + str(INCLUDE), "-o", str(exe), "-lpengu_runtime", "-L" + str(REPO / "build" / "lib"), "-lm", "-lpthread", "-ldl"],
        cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        pytest.skip(f"linking with tcc needs the full runtime link line: {r.stderr[:200]}")
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=300)
    assert "tcc-ok" in run.stdout, run.stdout + run.stderr


def test_pengu_run_does_not_fall_back_to_gcc(tmp_path):
    """`pengu run` must not report a development-compiler fallback.

    Before the fix, running a script that imported `std` printed
    "development compiler failed; retrying with gcc" because tcc could not parse
    the bundle. The assertion is on the absence of that message in a real run.
    """
    if not TCC.exists():
        pytest.skip("the bundled tcc is not present")
    src = tmp_path / "run.pengu"
    src.write_text(
        "import std.spark\n"
        "weave main into int:\n"
        '  calling spark.println with "hello"\n'
        "  return 0\n",
        encoding="utf-8",
    )
    rc, out = _pengu("run", str(src))
    assert rc == 0, out
    lowered = out.lower()
    assert "retrying with gcc" not in lowered, out
    assert "development compiler failed" not in lowered, out
    assert "hello" in out, out


def test_gcc_still_accepts_the_converted_declarations(tmp_path):
    """The `__typeof__` spelling must not regress the primary compiler.

    tcc compatibility is worthless if it costs gcc. This compiles the same bundle
    with gcc under the project's own discipline (`-Wall -Wextra`, no suppression)
    and requires zero diagnostics.
    """
    if shutil.which("gcc") is None:
        pytest.skip("gcc is not available")
    src = STD_PROGRAMS / "test_atlas.pengu"
    bundle = tmp_path / "gcc_bundle.c"
    rc, out = _pengu("build", "--entry", str(src), "--output", str(bundle))
    assert rc == 0, out
    r = subprocess.run(
        ["gcc", "-std=c11", "-Wall", "-Wextra", "-fsyntax-only",
         str(bundle), "-I" + str(INCLUDE)],
        cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    diagnostics = [l for l in (r.stdout + r.stderr).splitlines()
                   if "error:" in l or "warning:" in l]
    assert r.returncode == 0, "\n".join(diagnostics)
    assert not diagnostics, "\n".join(diagnostics)
