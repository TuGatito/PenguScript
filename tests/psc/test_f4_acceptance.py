"""F4 acceptance: PSC emite C compilable y ejecutable.

La suite es deliberadamente incremental: cada caso compila el bundle con el
compilador del sistema y ejecuta el binario. Los casos que necesitan la
biblioteca runtime se saltan si no se ha construido.

Para el corpus completo (costoso) usar `PSC_F4_FULL=1` en una fase posterior.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"
FIXTURES = Path(__file__).parent / "fixtures" / "f4"
RUNTIME = ROOT / "build" / "lib" / "libpengu_runtime.a"


def _run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def _emit(tmp_path: Path, name: str) -> Path:
    if not PSC.is_file():
        pytest.skip("psc binary not built")
    out = tmp_path / f"{name}.c"
    res = _run([str(PSC), "emit-c", str(FIXTURES / f"{name}.pengu"),
                f"--out={out}"], cwd=str(ROOT))
    assert res.returncode == 0, res.stderr + res.stdout
    assert out.is_file()
    return out


def _compile(bundle: Path, exe: Path) -> None:
    cc = shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        pytest.skip("no C compiler")
    if not RUNTIME.is_file():
        pytest.skip("libpengu_runtime.a not built")
    res = _run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
                str(bundle), str(RUNTIME), "-lm", "-o", str(exe)])
    assert res.returncode == 0, res.stderr


@pytest.mark.parametrize(
    "name,expected",
    [("hello", 5), ("types", 3), ("control", 10), ("interp", 7), ("arena", 0)],
)
def test_emit_compile_run(tmp_path: Path, name: str, expected: int) -> None:
    bundle = _emit(tmp_path, name)
    exe = tmp_path / name
    _compile(bundle, exe)
    res = _run([str(exe)])
    assert res.returncode == expected, res.stderr
    assert "error:" not in res.stderr.lower()


def test_std_hello(tmp_path: Path) -> None:
    bundle = _emit(tmp_path, "std_hello")
    exe = tmp_path / "std_hello"
    _compile(bundle, exe)
    res = _run([str(exe)])
    assert res.returncode == 0, res.stderr
    assert res.stdout == "hello from PSC\n"


def test_emit_is_deterministic(tmp_path: Path) -> None:
    a = _emit(tmp_path, "types")
    b = _emit(tmp_path, "types")
    assert a.read_text() == b.read_text()


def test_c_has_abi_pin(tmp_path: Path) -> None:
    text = _emit(tmp_path, "hello").read_text()
    assert "_Static_assert(PENGU_ABI_VERSION == 2" in text
    assert "_pengu_abi_pin" in text


def _emit_extra(tmp_path: Path, name: str, *flags: str) -> Path:
    if not PSC.is_file():
        pytest.skip("psc binary not built")
    out = tmp_path / f"{name}.c"
    res = _run([str(PSC), "emit-c", str(FIXTURES / f"{name}.pengu"),
                *flags, f"--out={out}"], cwd=str(ROOT))
    assert res.returncode == 0, res.stderr + res.stdout
    return out


def test_lambda(tmp_path: Path) -> None:
    exe = tmp_path / "lambda"
    _compile(_emit_extra(tmp_path, "lambda"), exe)
    assert _run([str(exe)]).returncode == 4


def test_generic_inference(tmp_path: Path) -> None:
    exe = tmp_path / "generic"
    _compile(_emit_extra(tmp_path, "generic"), exe)
    assert _run([str(exe)]).returncode == 7


def test_judge(tmp_path: Path) -> None:
    exe = tmp_path / "judge"
    _compile(_emit_extra(tmp_path, "judge"), exe)
    assert _run([str(exe)]).returncode == 7


def test_test_mode(tmp_path: Path) -> None:
    exe = tmp_path / "testmode"
    _compile(_emit_extra(tmp_path, "testmode", "--test"), exe)
    res = _run([str(exe)])
    assert res.returncode == 0
    assert "All 1 test(s) passed." in res.stdout


def test_dce_scope_user_prunes_unused(tmp_path: Path) -> None:
    text = _emit_extra(tmp_path, "dce", "--dce-scope=user").read_text()
    assert "int32_t unused(" not in text


def test_strict_c99(tmp_path: Path) -> None:
    bundle = _emit_extra(tmp_path, "types", "--strict-c99")
    text = bundle.read_text()
    assert "pengu_abi_static_assert" in text
    cc = shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler")
    exe = tmp_path / "strict"
    res = _run([cc, "-std=c99", "-pedantic", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
                str(bundle), str(RUNTIME), "-lm", "-o", str(exe)])
    assert res.returncode == 0, res.stderr


def test_clang_matrix_if_available(tmp_path: Path) -> None:
    cc = shutil.which("clang")
    if cc is None:
        pytest.skip("clang not installed")
    bundle = _emit_extra(tmp_path, "types", "--strict-c99")
    exe = tmp_path / "types_clang"
    res = _run([cc, "-std=c99", "-pedantic", "-Wall", "-Wextra", "-Werror",
                "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
                str(bundle), str(RUNTIME), "-lm", "-o", str(exe)])
    assert res.returncode == 0, res.stderr
    assert _run([str(exe)]).returncode == 3


def test_asan_clean_if_available(tmp_path: Path) -> None:
    cc = shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler")
    bundle = _emit_extra(tmp_path, "hello")
    exe = tmp_path / "hello_asan"
    res = _run([cc, "-std=c11", "-w", "-fsanitize=address,undefined", "-g",
                "-I", str(ROOT), "-I", str(ROOT / "build" / "include"),
                str(bundle), str(RUNTIME), "-lm", "-o", str(exe)])
    assert res.returncode == 0, res.stderr
    run = _run([str(exe)], env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"})
    assert run.returncode == 5, run.stderr
    assert "ERROR: AddressSanitizer" not in run.stderr


def test_golden_hello(tmp_path: Path) -> None:
    golden = ROOT / "psc" / "tests" / "golden" / "codegen" / "hello.c"
    def norm(x: str) -> str:
        return "\n".join(line for line in x.splitlines() if not line.lstrip().startswith("#line"))
    got = norm(_emit_extra(tmp_path, "hello").read_text())
    want = norm(golden.read_text())
    assert got == want, "\n".join(__import__("difflib").unified_diff(want.splitlines(), got.splitlines(), lineterm=""))
