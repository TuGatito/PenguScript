"""Roadmap Phase 5 / §5.1 — integer overflow policy.

Policy: signed overflow is **never** left as undefined behaviour unless the user
opts out.

* debug   -> ``-ftrapv`` (SIGABRT on signed overflow)
* release -> ``-fwrapv`` (defined two's-complement wrapping, no UB)
* ``--release-unsafe`` -> neither flag (C-native UB, explicitly requested)

The `-fsanitize=signed-integer-overflow` test below is the acceptance check from
the roadmap: release builds must produce zero UB reports.
"""

import os
import subprocess
import textwrap

import pytest

from pengu_project import ProjectConfig, PenguBuilder
from tests.conftest import (
    compile_run,
    have_tool,
    requires_cc,
    requires_runtime,
)

OVERFLOW_SRC = textwrap.dedent("""\
    weave bump with x as int, y as int into int:
      return x + y

    weave main into int:
      var b as int is calling bump with 2147483647, 1
      if b == -2147483648:
        return 0
      return 1
""")


def _flags(profile: str, release_unsafe: bool, tmp_path):
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "main.pengu").write_text("weave main into int:\n  return 0\n", encoding="utf-8")
    (tmp_path / "pengu.toml").write_text(
        f'[project]\nname = "o"\nentry = "src/main.pengu"\n\n[build]\nprofile = "{profile}"\n',
        encoding="utf-8",
    )
    cfg = ProjectConfig.load(str(tmp_path), profile=profile)
    cfg.release_unsafe = release_unsafe
    builder = PenguBuilder(cfg)
    bundle = tmp_path / "b.c"
    bundle.write_text("int main(void){return 0;}\n", encoding="utf-8")
    cmds = builder.build_compile_commands(str(bundle), str(tmp_path / "app"))
    flat = []
    for cmd in cmds:
        flat.extend(cmd if isinstance(cmd, (list, tuple)) else [cmd])
    return flat


def test_debug_uses_trapv(tmp_path):
    assert "-ftrapv" in _flags("debug", False, tmp_path)


def test_release_uses_fwrapv(tmp_path):
    flags = _flags("release", False, tmp_path)
    assert "-fwrapv" in flags
    assert "-ftrapv" not in flags


def test_release_unsafe_uses_no_overflow_flag(tmp_path):
    flags = _flags("release", True, tmp_path)
    assert "-ftrapv" not in flags and "-fwrapv" not in flags
    assert "-DPENGU_OVERFLOW_CHECK=0" in flags


def test_debug_and_release_do_not_pass_both(tmp_path):
    for profile in ("debug", "release"):
        flags = _flags(profile, False, tmp_path)
        assert not ("-ftrapv" in flags and "-fwrapv" in flags)


@requires_cc
@requires_runtime
def test_release_wraps_defined():
    res = compile_run(OVERFLOW_SRC, tag="ovf_release", profile="release")
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


@requires_cc
@requires_runtime
def test_debug_traps_overflow():
    res = compile_run(OVERFLOW_SRC, tag="ovf_debug", profile="debug", expect_exit=None)
    assert res.returncode != 0, "debug overflow must trap"


@pytest.mark.skipif(not have_tool("gcc"), reason="gcc not available")
@requires_cc
@requires_runtime
def test_release_wrapping_is_ubsan_clean():
    """Roadmap acceptance check: release arithmetic has no signed-overflow UB."""
    res = compile_run(
        OVERFLOW_SRC, tag="ovf_ubsan", profile="release", expect_exit=None,
        extra_cflags=["-fsanitize=signed-integer-overflow", "-fno-sanitize-recover=all"],
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"
    assert "runtime error" not in (res.stderr or ""), res.stderr
