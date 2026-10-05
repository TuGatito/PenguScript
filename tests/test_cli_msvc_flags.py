"""Phase 4 item 4.11: the `cl.exe` command line contains no GNU flags.

`build_compile_commands` builds one GNU-shaped flag list and handed it to every
compiler. With ``--cc cl`` the command line mixed ``/W3``/``/std:c11`` with
``-o``, ``-I``, ``-L``, ``-lfoo``, ``-pthread`` and ``-Wl,--start-group``, none
of which `cl` accepts (``D9002: ignoring unknown option``) — and the library
names never reached the linker, so the build failed on unresolved externals.

`cl` is not installed in CI, so these tests inspect the command that *would* be
run. That is the observable artefact here: the flag list is the deliverable, and
building it needs no compiler.
"""

import os
import sys

import pytest

from pengu_project import OutputType, PenguBuilder, ProjectConfig

# GNU spellings that must never appear on an MSVC command line. `-c` is not
# listed: MSVC spells it `/c`, and the check below catches the bare form.
GNU_FLAGS = ("-o", "-I", "-L", "-l", "-Wl,", "-pthread", "-shared", "-fPIC",
             "-D", "-O", "-g", "-W", "-std=", "-f")


def _commands(output_type, cc="cl", target_compiler="msvc", links=("pengu_runtime",)):
    cfg = ProjectConfig(name="p", output=output_type, output_name="app",
                        base_dir="/tmp/pengu_msvc_flags", cc=cc,
                        target_compiler=target_compiler, links=list(links))
    builder = PenguBuilder(cfg)
    return builder.build_compile_commands("/tmp/pengu_msvc_flags/bundle.c",
                                          "/tmp/pengu_msvc_flags/app")


@pytest.mark.parametrize("output_type", [
    OutputType.EXE, OutputType.OBJ, OutputType.STATIC, OutputType.SHARED,
])
def test_msvc_command_has_no_gnu_flags(output_type):
    for cmd in _commands(output_type):
        offenders = [tok for tok in cmd if tok.startswith(GNU_FLAGS)]
        assert not offenders, f"GNU flags on an MSVC command: {offenders}\n{' '.join(cmd)}"


def test_msvc_executable_uses_fe_and_link_section():
    cmd = _commands(OutputType.EXE)[0]
    assert cmd[0] == "cl"
    assert "/Fe:/tmp/pengu_msvc_flags/app" in cmd
    assert "-o" not in cmd
    assert "/link" in cmd, "libraries must reach the linker"
    libs = cmd[cmd.index("/link") + 1:]
    assert libs and all(lib.endswith(".lib") for lib in libs), libs
    assert "pengu_runtime.lib" in libs
    assert not any("--start-group" in tok for tok in cmd)


def test_msvc_shared_and_object_use_their_switches():
    shared = _commands(OutputType.SHARED)[0]
    assert "/LD" in shared and "/Fe:/tmp/pengu_msvc_flags/app" in shared

    obj = _commands(OutputType.OBJ)[0]
    assert "/c" in obj
    assert any(tok.startswith("/Fo:") for tok in obj), obj
    assert "/link" not in obj


def test_msvc_include_and_define_spellings():
    cmd = _commands(OutputType.EXE)[0]
    assert any(tok.startswith("/I") for tok in cmd)
    assert any(tok.startswith("/D") for tok in cmd)
    assert not any(tok.startswith("-I") or tok.startswith("-D") for tok in cmd)


def test_gnu_command_line_is_unchanged():
    """The MSVC branch must not touch gcc/clang builds."""
    cmd = _commands(OutputType.EXE, cc="gcc", target_compiler="gcc")[0]
    assert cmd[0] == "gcc"
    assert "-o" in cmd and "/Fe:" not in cmd and "/link" not in cmd
    assert any(tok.startswith("-l") for tok in cmd)


def test_msvc_link_flag_translation_unit():
    from pengu_project import _msvc_link_flags

    assert _msvc_link_flags([]) == []
    assert _msvc_link_flags(["-Wl,--start-group", "-lfoo", "-Wl,--end-group"]) == \
        ["/link", "foo.lib"]
    assert _msvc_link_flags(["-L/some/lib", "-lpengu_runtime"]) == \
        ["/link", "/LIBPATH:/some/lib", "pengu_runtime.lib"]
    assert _msvc_link_flags(["-lm", "-ldl", "-lrt", "-pthread"]) == []
    assert _msvc_link_flags(["already.lib"]) == ["/link", "already.lib"]
