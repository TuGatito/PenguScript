"""Roadmap Phase 5 / §5.2 + §5.6 — bounds checking policy and `unsafe:` blocks.

Policy: bounds checks are emitted in **every** profile.  Two escape hatches:
`unsafe:` (local, warns `W0007`) and `--release-unsafe` (global).
"""

import textwrap

import pytest

from pengu_project import ProjectConfig, PenguBuilder, build_project
from tests.conftest import compile_run, gen_bundle, requires_cc, requires_runtime

BODY = "  var xs as array of int with size 3 is [1, 2, 3]\n  var acc as int is 0\n"


def _bundle(src: str) -> str:
    return gen_bundle(textwrap.dedent(src))


def _checks(src: str) -> int:
    return _bundle(src).count("pengu_assert_bounds")


# --------------------------------------------------------------------------- #
# Codegen policy
# --------------------------------------------------------------------------- #


def test_bounds_check_is_emitted_in_release_by_default():
    src = (
        "weave f into int:\n" + BODY +
        "  for i in 0 to 3:\n"
        "    set acc is acc + (xs at i)\n"
        "  return acc\n"
    )
    # gen_bundle compiles in non-debug (release) mode.
    assert _checks(src) == 1, "release builds must still bounds-check"


def test_unsafe_block_suppresses_only_its_own_statements():
    src = (
        "weave f into int:\n" + BODY +
        "  unsafe:\n"
        "    set acc is acc + (xs at 0)\n"
        "  set acc is acc + (xs at 1)\n"
        "  return acc\n"
    )
    # Exactly one check: the access outside the unsafe block.
    assert _checks(src) == 1


def test_unsafe_block_with_loop_has_no_checks():
    src = (
        "weave f into int:\n" + BODY +
        "  unsafe:\n"
        "    for i in 0 to 3:\n"
        "      set acc is acc + (xs at i)\n"
        "  return acc\n"
    )
    assert _checks(src) == 0


def test_nested_unsafe_blocks_are_additive():
    src = (
        "weave f into int:\n" + BODY +
        "  unsafe:\n"
        "    unsafe:\n"
        "      set acc is acc + (xs at 0)\n"
        "  set acc is acc + (xs at 1)\n"
        "  return acc\n"
    )
    assert _checks(src) == 1


def test_release_unsafe_disables_every_check(tmp_path):
    src = (
        "weave f into int:\n" + BODY +
        "  for i in 0 to 3:\n"
        "    set acc is acc + (xs at i)\n"
        "  return acc\n"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(src, encoding="utf-8")
    (tmp_path / "pengu.toml").write_text(
        '[project]\nname = "r"\nentry = "src/main.pengu"\n\n[build]\nprofile = "release"\n',
        encoding="utf-8",
    )
    safe_out = tmp_path / "safe.c"
    unsafe_out = tmp_path / "unsafe.c"
    build_project(config_path=str(tmp_path), output=str(safe_out))
    build_project(config_path=str(tmp_path), output=str(unsafe_out), release_unsafe=True)
    assert safe_out.read_text(encoding="utf-8").count("pengu_assert_bounds") == 1
    assert unsafe_out.read_text(encoding="utf-8").count("pengu_assert_bounds") == 0


def test_bounds_flag_is_decoupled_from_profile(tmp_path):
    """-DPENGU_BOUNDS_CHECK=0 must come from --release-unsafe, not from release."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "weave main into int:\n  return 0\n", encoding="utf-8"
    )
    (tmp_path / "pengu.toml").write_text(
        '[project]\nname = "flag"\nentry = "src/main.pengu"\n\n[build]\nprofile = "release"\n',
        encoding="utf-8",
    )
    cfg = ProjectConfig.load(str(tmp_path))
    builder = PenguBuilder(cfg)
    bundle = tmp_path / "bundle.c"
    bundle.write_text("int main(void){return 0;}\n", encoding="utf-8")
    out = tmp_path / "app"
    def _flat(commands):
        # build_compile_commands returns a list of argv arrays.
        out_flags = []
        for cmd in commands:
            out_flags.extend(cmd if isinstance(cmd, (list, tuple)) else [cmd])
        return out_flags

    flags = _flat(builder.build_compile_commands(str(bundle), str(out)))
    assert "-DPENGU_BOUNDS_CHECK=0" not in flags, "release must keep runtime checks on"

    builder.release_unsafe = True
    flags = _flat(builder.build_compile_commands(str(bundle), str(out)))
    assert "-DPENGU_BOUNDS_CHECK=0" in flags
    assert "-DPENGU_OVERFLOW_CHECK=0" in flags


def test_config_hash_distinguishes_release_unsafe(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "weave main into int:\n  return 0\n", encoding="utf-8"
    )
    (tmp_path / "pengu.toml").write_text(
        '[project]\nname = "h"\nentry = "src/main.pengu"\n', encoding="utf-8"
    )
    safe = ProjectConfig.load(str(tmp_path))
    unsafe = ProjectConfig.load(str(tmp_path))
    unsafe.release_unsafe = True
    assert (PenguBuilder(safe).compute_config_hash()
            != PenguBuilder(unsafe).compute_config_hash())


# --------------------------------------------------------------------------- #
# Checker policy
# --------------------------------------------------------------------------- #


def _warnings_and_errors(source: str):
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    checker = PenguChecker(base_dir=".")
    checker.check(PenguParser().parse(source), source=source, filename="t.pengu")
    return [str(w) for w in checker.warnings], list(checker.errors)


def test_unsafe_block_emits_w0007():
    warnings, errors = _warnings_and_errors(
        "weave f into int:\n"
        "  var x as int is 0\n"
        "  unsafe:\n"
        "    set x is x + 1\n"
        "  return x\n"
    )
    assert not errors, errors
    assert any("W0007" in w for w in warnings), warnings


def test_unsafe_block_rejected_at_top_level():
    """`unsafe:` is a statement, so the grammar rejects it at the top level."""
    from pengu_parser.pengu_errors import ParseError
    from pengu_parser.pengu_parser import PenguParser

    with pytest.raises(ParseError):
        PenguParser().parse("unsafe:\n  var x as int is 1\n")


def test_unsafe_block_allows_banish_free_body():
    warnings, errors = _warnings_and_errors(
        "weave f into int:\n"
        "  var n as int is 3\n"
        "  unsafe:\n"
        "    var i as int is 0\n"
        "    while i < n:\n"
        "      set i is i + 1\n"
        "  return 0\n"
    )
    assert not errors, errors


# --------------------------------------------------------------------------- #
# Runtime behaviour (end to end)
# --------------------------------------------------------------------------- #


@requires_cc
@requires_runtime
def test_release_out_of_bounds_aborts():
    src = (
        "weave main into int:\n"
        "  var xs as array of int with size 3 is [1, 2, 3]\n"
        "  var i as int is 99\n"
        "  return xs at i\n"
    )
    res = compile_run(src, tag="bounds_release", expect_exit=None)
    assert res.returncode not in (0, 99), res.returncode
    assert "Index out of bounds" in (res.stderr or ""), res.stderr


@requires_cc
@requires_runtime
def test_unsafe_block_skips_the_check():
    src = (
        "weave f into int:\n"
        "  var xs as array of int with size 3 is [1, 2, 3]\n"
        "  var acc as int is 0\n"
        "  unsafe:\n"
        "    set acc is xs at 1\n"
        "  return acc\n\n"
        "weave main into int:\n"
        "  if (calling f) == 2:\n"
        "    return 0\n"
        "  return 1\n"
    )
    res = compile_run(src, tag="unsafe_ok")
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"
