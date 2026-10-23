"""Dead-code elimination: whole-project guarantees.

DCE is a whole-project pass, so these tests go through the driver
(``pengu expand`` / ``pengu build``) rather than the single-module ``emit_c``
fixture: a single-module bundle has no ``std`` closure to prune.

The cases pinned here are the ones that used to be wrong (or silently costly):

* an installed ``std/`` (``PENGU_STD_DIR``, FHS, wheel) must prune exactly like
  the checkout's;
* a weave named only by a **default argument** must survive (the caller emits
  the call even though the callee body never mentions it);
* a **test block** must keep its helpers in ``--test`` mode only; a normal
  build does not emit the test section, so its references must not inflate the
  production bundle.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


def _defined(c_source: str, name: str) -> bool:
    """True when ``name`` is *defined* (a `{` body), not merely declared."""
    return re.search(rf"^[\w \*]+\b{re.escape(name)}\([^;{{]*\)\s*\{{",
                     c_source, re.M) is not None


def _declared(c_source: str, name: str) -> bool:
    """True when ``name`` has a prototype (a `;` declaration)."""
    return re.search(rf"\b{re.escape(name)}\([^;{{]*\)\s*;", c_source) is not None


@pytest.fixture
def expand(pengu_cli, tmp_path):
    """Expands a script (plus optional sibling modules) to C."""
    def _run(source: str, files: dict[str, str] | None = None,
             tag: str = "t", env: dict[str, str] | None = None,
             script_rel: str | None = None) -> str:
        for rel, text in (files or {}).items():
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        script = tmp_path / (script_rel or f"{tag}.pengu")
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(source, encoding="utf-8")
        res = pengu_cli("expand", str(script), env=env)
        assert res.returncode == 0, (
            f"expand failed:\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
        )
        return res.stdout
    return _run


def test_spark_println_is_minimal(expand):
    """The headline case: importing spark for println emits println only."""
    c = expand("""
import std.spark

weave main into int:
    calling spark.println with "hello"
    return 0
""")
    assert _defined(c, "spark_println")
    assert _defined(c, "spark_pengu_println")
    # Nearby output helpers are dead and must be gone.  The `\b…\(` match in
    # `_defined` keeps `spark_pengu_print` from matching `spark_pengu_println`.
    assert not _defined(c, "spark_print")
    assert not _defined(c, "spark_pengu_print")
    assert not _defined(c, "spark_pengu_eprint")
    assert "Dead-code elimination" in c


def test_default_argument_keeps_callee(expand):
    """A weave used only by a default argument must not be pruned."""
    c = expand(
        "import u\n\nweave main into int:\n    return calling u.measure with \"hello\"\n",
        script_rel="src/main.pengu",
        files={
            "src/u.pengu": (
                "import std.scrolls\n\n"
                "weave measure with s as string is \"abc\", "
                "n as int is calling scrolls.len with \"xy\" into int:\n"
                "    return n + 1\n"
            ),
        },
    )
    # The default is translated at the call site; pruning `pengu_len` used to
    # leave an implicit declaration and a failed C build.
    assert _defined(c, "pengu_len"), (
        "DCE pruned a weave referenced only by a default argument:\n"
        + "\n".join(l for l in c.splitlines() if "pengu_len" in l)
    )
    assert _declared(c, "pengu_len")


def test_default_argument_is_not_treated_as_a_body_reference(expand):
    """The fix must not degenerate into "keep every scrolls weave"."""
    c = expand(
        "import u\n\nweave main into int:\n    return calling u.measure with \"hello\"\n",
        script_rel="src/main.pengu",
        files={
            "src/u.pengu": (
                "import std.scrolls\n\n"
                "weave measure with s as string is \"abc\", "
                "n as int is calling scrolls.len with \"xy\" into int:\n"
                "    return n + 1\n"
            ),
        },
    )
    assert _defined(c, "pengu_len")
    assert not _defined(c, "pengu_upper")
    assert not _defined(c, "pengu_trim")


def test_test_blocks_do_not_inflate_a_normal_build(pengu_cli, tmp_path):
    """Test-only std references stay out of the production bundle."""
    (tmp_path / "pengu.toml").write_text(
        'name = "dce_proj"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "c"\n',
        encoding="utf-8",
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.pengu").write_text(
        "import std.scrolls\n\n"
        "test \"upper works\":\n"
        "    let s as string is \"abc\"\n"
        "    let u as string is calling scrolls.upper with s\n"
        "    if u == \"ABC\":\n"
        "        calling scrolls.trim with s\n\n"
        "weave main into int:\n"
        "    return 0\n",
        encoding="utf-8",
    )

    normal = pengu_cli("build")
    assert normal.returncode == 0, normal.stderr
    normal_c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert not _defined(normal_c, "pengu_upper"), (
        "a normal build kept a weave referenced only by a test block"
    )
    assert not _defined(normal_c, "pengu_trim")

    tested = pengu_cli("build", "--test")
    assert tested.returncode == 0, tested.stderr
    test_c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert _defined(test_c, "pengu_upper"), (
        "--test dropped a weave referenced by a test block"
    )


def test_installed_std_root_is_prunable(monkeypatch, tmp_path):
    """An FHS/PENGU_STD_DIR std/ is std, not user code (B1)."""
    std = tmp_path / "share" / "pengu" / "std"
    std.mkdir(parents=True)
    spark = std / "spark.pengu"
    spark.write_text("# fake\n", encoding="utf-8")
    monkeypatch.setenv("PENGU_STD_DIR", str(std))

    from pengu_parser.pengu_dce import is_prunable_module, resolved_std_roots

    roots = resolved_std_roots()
    assert str(std) in roots
    assert is_prunable_module(str(spark)) is True
    assert is_prunable_module(str(tmp_path / "src" / "main.pengu")) is False


def test_test_mode_keeps_every_instance(pengu_cli, tmp_path):
    """--test keeps instances (test bodies can call generic specializations).

    The exact alternative is to translate and scan the test section too; until
    then, keeping instances in test builds is the safe, documented behaviour.
    A test bundle is not distributed, so the size cost is acceptable.
    """
    (tmp_path / "pengu.toml").write_text(
        'name = "dce_test_inst"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "c"\n',
        encoding="utf-8",
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.pengu").write_text(
        "import std.oracle\n\n"
        "test \"some works\":\n"
        "    var m as maybe int is some 42\n"
        "    if m is present:\n"
        "        let v as int is m.value\n"
        "        if v == 42:\n"
        "            return\n\n"
        "weave main into int:\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = pengu_cli("build", "--test")
    assert res.returncode == 0, res.stderr
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert _defined(c, "some_of_int"), (
        "--test dropped the instance that the test body calls"
    )


# ---------------------------------------------------------------------------
# Phase 1 — exact reachability over the emitted C
# ---------------------------------------------------------------------------

def test_unused_json_import_does_not_emit_instances(expand):
    """An unused generic-heavy import must not drag its monomorphizations in."""
    c = expand("""
import std.json

weave main into int:
    return 0
""")
    # `json` creates instances for its own helpers; none of them is reachable.
    assert not _defined(c, "some_of_int"), (
        "an unused import emitted the generic instance `some_of_int`:\n"
        + "\n".join(l for l in c.splitlines() if "some_of_int" in l)
    )
    assert not _defined(c, "JsonValue_get")
    assert not _defined(c, "json_parse")
    assert "Dead-code elimination" in c


def test_cipher_one_function_does_not_pull_the_closure(expand):
    """Using one cipher function must not emit the other 500+ specializations."""
    c = expand("""
import std.cipher

weave main into int:
    var s as string is calling cipher.encode_base64 with "hi"
    banish s
    return 0
""")
    assert _defined(c, "cipher_encode_base64")
    assert not _defined(c, "some_of_int")
    assert not _defined(c, "JsonValue_get")
    # A function from a sibling std module that only the dead closure used.
    assert not _defined(c, "atlas_get_or")
    assert not _defined(c, "tally_sum_int")


def test_function_pointer_keeps_callee(expand):
    """A weave used as a value (not called) is a real reference."""
    c = expand("""
import std.scrolls

weave main into int:
    var f as weave with string into int is scrolls.len
    return calling f with "abc"
""")
    assert _defined(c, "pengu_len")


def test_lambda_body_keeps_callee(expand):
    """A dependency named only inside a lambda body must survive."""
    c = expand("""
import std.tally
import std.scrolls

weave main into int:
    var xs as list of int is list of int
    calling xs.push with 1
    calling xs.push with 2
    var out as list of int is calling tally.scan_left with xs, (lambda acc as int, x as int into acc + (calling scrolls.len with "ab"))
    banish out
    banish xs
    return 0
""")
    assert _defined(c, "pengu_len")
    assert _defined(c, "tally_scan_left_int")


def test_interpolation_keeps_callee(expand):
    """A call inside `"{…}"` is still a call at the call site."""
    c = expand("""
import std.scrolls

weave main into int:
    let s as string is "abc"
    let out as string is "len={calling scrolls.len with s}"
    banish out
    return 0
""")
    assert _defined(c, "pengu_len")


def test_common_local_names_do_not_keep_std_weaves(expand):
    """B8: a local called `len`/`contains` must not keep `pengu_len`/`pengu_contains`."""
    c = expand("""
import std.scrolls

weave main into int:
    var len as int is 5
    var contains as bool is true
    var values as int is 7
    if contains:
        return len + values
    return 0
""")
    assert not _defined(c, "pengu_len"), (
        "a local variable named `len` kept the std weave `pengu_len`"
    )
    assert not _defined(c, "pengu_contains")
    assert not _defined(c, "pengu_pengu_string_contains")


def test_std_export_is_a_root(expand):
    """`@export` survives even when only C is supposed to call it."""
    c = expand("""
import std.atlas

weave main into int:
    return 0
""")
    assert _defined(c, "atlas__atlas_cmp_i32")
    assert _defined(c, "atlas__atlas_cmp_string")


def test_no_dce_keeps_instances(expand):
    """`PENGU_NO_DCE=1` remains the escape hatch (A/B and bug reports)."""
    c = expand("""
import std.oracle

weave main into int:
    return 0
""", env={"PENGU_NO_DCE": "1"})
    assert "Dead-code elimination: disabled" in c
    assert _defined(c, "some_of_int")


@pytest.fixture
def ccheck(tmp_path, has_cc, pengu_root):
    """Compiles a generated bundle under `-Werror=implicit-function-declaration`."""
    import shutil
    import subprocess

    gcc = shutil.which("gcc") or shutil.which("clang")
    if not gcc:
        pytest.skip("no C compiler available")

    def _run(c_source: str, tag: str = "bundle") -> None:
        path = tmp_path / f"{tag}.c"
        path.write_text(c_source, encoding="utf-8")
        res = subprocess.run(
            [gcc, "-fsyntax-only", "-std=c11",
             "-Werror=implicit-function-declaration", "-Wno-unused-function",
             "-I", str(pengu_root / "std_c"),
             "-I", str(pengu_root / "build" / "include"),
             "-I", str(pengu_root), str(path)],
            capture_output=True, text=True, timeout=300,
        )
        assert res.returncode == 0, (
            f"generated C does not compile:\n{res.stdout}\n{res.stderr}"
        )
    return _run


@pytest.mark.parametrize("source,tag", [
    ('import std.spark\n\nweave main into int:\n    calling spark.println with "hello"\n    return 0\n',
     "spark"),
    ('import std.json\n\nweave main into int:\n    return 0\n', "json_unused"),
    ('import std.cipher\n\nweave main into int:\n    var s as string is calling cipher.encode_base64 with "hi"\n    banish s\n    return 0\n',
     "cipher_one"),
    ('import std.scrolls\n\nweave main into int:\n    var f as weave with string into int is scrolls.len\n    return calling f with "abc"\n',
     "fnptr"),
])
def test_generated_c_has_no_implicit_declarations(expand, ccheck, source, tag):
    """Every reachability miss would surface here as an implicit declaration."""
    c = expand(source)
    ccheck(c, tag=tag)


# ---------------------------------------------------------------------------
# Phase 4a — derived helpers
# ---------------------------------------------------------------------------

def test_derived_helpers_of_unused_runes_are_dropped(expand):
    c = expand("""
rune Used derive Par:
    x as int

rune Unused derive Par:
    x as int

weave main into int:
    var a as Used is with x is 1
    var b as Used is with x is 1
    if a == b:
        return 0
    return 1
""")
    assert _defined(c, "Used_eq")
    assert not _defined(c, "Unused_eq"), (
        "a derived helper for an unused rune is still in the bundle"
    )
    assert "derived helper block" in c


def test_derived_helpers_close_over_field_types(expand):
    c = expand("""
rune Inner derive Par:
    v as int

rune Outer derive Par:
    inner as Inner

weave main into int:
    var a as Outer is with inner is with v is 1
    var b as Outer is with inner is with v is 1
    if a == b:
        return 0
    return 1
""")
    assert _defined(c, "Outer_eq")
    assert _defined(c, "Inner_eq"), (
        "Outer_eq calls Inner_eq; the closure must keep Inner's helper"
    )


def test_only_the_used_concept_block_is_kept(expand):
    c = expand("""
rune Data derive Par, Ordo, Vinculum, Imago, Nexus:
    v as int

weave main into int:
    var a as Data is with v is 1
    var b as Data is with v is 1
    if a == b:
        return 0
    return 1
""")
    assert _defined(c, "Data_eq")
    # The other concept blocks are independent and unused.
    assert not _defined(c, "Data_cmp")
    assert not _defined(c, "Data_Vinculum")
    assert not _defined(c, "_pengu_clone_Data")
    assert not _defined(c, "Data_nexus")
    assert "pruned 4 of 5 derived helper block(s)" in c


def test_test_mode_keeps_all_derived_helpers(pengu_cli, tmp_path):
    (tmp_path / "pengu.toml").write_text(
        'name = "dce_derived_test"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "c"\n',
        encoding="utf-8",
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.pengu").write_text(
        "rune Data derive Par, Ordo, Vinculum, Imago, Nexus:\n"
        "    v as int\n\n"
        "test \"eq\":\n"
        "    var a as Data is with v is 1\n"
        "    var b as Data is with v is 1\n"
        "    if a == b:\n"
        "        return\n\n"
        "weave main into int:\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = pengu_cli("build", "--test")
    assert res.returncode == 0, res.stderr
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert _defined(c, "Data_cmp")
    assert _defined(c, "Data_Vinculum")
    assert _defined(c, "_pengu_clone_Data")
    assert _defined(c, "Data_nexus")
    assert "derived helper block" not in c


# ---------------------------------------------------------------------------
# Phase 4b — opt-in type/constant pruning
# ---------------------------------------------------------------------------

def test_prune_types_is_opt_in(expand):
    source = """
rune Used:
    v as int

rune Unused:
    w as int

weave main into int:
    var u as Used is with v is 3
    return u.v
"""
    kept = expand(source, tag="types_default")
    assert "struct Unused" in kept

    pruned = expand(source, tag="types_pruned", env={"PENGU_PRUNE_TYPES": "1"})
    assert "struct Used" in pruned
    assert "struct Unused" not in pruned
    assert "--prune-types" in pruned


def test_prune_types_keeps_types_named_by_signatures(expand):
    c = expand(
        """
rune Secret:
    value as int

rune Hidden:
    value as int

weave peek with p as ref to Secret into int:
    return 0

weave main into int:
    return 0
""",
        tag="types_signature",
        env={"PENGU_PRUNE_TYPES": "1"},
    )
    assert "struct Secret" in c
    assert "struct Hidden" not in c


def test_prune_types_keeps_types_used_only_by_constants(expand):
    c = expand(
        """
rune Palette:
    r as int

rune Other:
    z as int

const P as Palette is with r is 5

weave main into int:
    return P.r
""",
        tag="types_const",
        env={"PENGU_PRUNE_TYPES": "1"},
    )
    assert "struct Palette" in c
    assert "struct Other" not in c
    assert "static const Palette P" in c


def test_prune_types_drops_unused_constants(expand):
    c = expand(
        """
const USED as array of int with size 3 is [1, 2, 3]
const GONE_ARR as array of int with size 2 is [8, 9]

weave main into int:
    return USED at 0
""",
        tag="consts",
        env={"PENGU_PRUNE_TYPES": "1"},
    )
    assert "USED[3]" in c
    assert "GONE_ARR" not in c


def test_prune_types_drops_unused_enum_but_keeps_used(expand):
    c = expand(
        """
omen Color:
    Red
    Blue

omen Other:
    A
    B

weave main into int:
    var c as Color is Color.Red
    return 0
""",
        tag="omen",
        env={"PENGU_PRUNE_TYPES": "1"},
    )
    assert "Color_Red" in c
    assert "Other_A" not in c


def test_prune_types_does_not_run_with_no_dce(expand):
    c = expand(
        """
rune Used:
    v as int

rune Unused:
    w as int

weave main into int:
    var u as Used is with v is 3
    return u.v
""",
        tag="types_nodce",
        env={"PENGU_PRUNE_TYPES": "1", "PENGU_NO_DCE": "1"},
    )
    assert "struct Unused" in c
    assert "--prune-types" not in c


@pytest.mark.parametrize("source,tag", [
    ("""
rune Used:
    v as int

rune Unused:
    w as int

weave main into int:
    var u as Used is with v is 3
    return u.v
""", "prune_rune"),
    ("""
omen Shape:
    Circle with r as float
    Empty

omen Other:
    Thing with v as int

weave area with s as Shape into float:
    return judge s:
        when Circle with r -> r * 3.0
        else -> 0.0

weave main into int:
    var s as Shape is with Circle is with r is 2.0
    return (calling area with s) to int
""", "prune_omen"),
    ("""
rune P:
    x as int

rune Q:
    y as int

weave pair into (P, P):
    var a as P is with x is 1
    var b as P is with x is 2
    return a, b

weave main into int:
    let (a, b) is calling pair
    return a.x + b.x
""", "prune_tuple"),
    ("""
rune Inner:
    x as int

alias Alias as Inner
seal UnusedSeal as int

weave read_inner with a as Alias into int:
    return a.x

weave main into int:
    var i as Inner is with x is 4
    return calling read_inner with i
""", "prune_alias"),
])
def test_prune_types_bundles_compile(expand, ccheck, source, tag):
    c = expand(source, tag=tag, env={"PENGU_PRUNE_TYPES": "1"})
    ccheck(c, tag=tag)


def test_prune_types_does_not_run_in_test_mode(pengu_cli, tmp_path):
    """--test keeps types/constants: test bodies are outside the liveness scan."""
    (tmp_path / "pengu.toml").write_text(
        'name = "dce_types_test"\nversion = "0.1.0"\nentry = "src/main.pengu"\noutput = "c"\n',
        encoding="utf-8",
    )
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.pengu").write_text(
        "rune Used:\n"
        "    v as int\n\n"
        "rune Unused:\n"
        "    w as int\n\n"
        "const GONE as int is 9\n\n"
        "test \"used\":\n"
        "    var u as Used is with v is 1\n"
        "    if u.v == 1:\n"
        "        return\n\n"
        "weave main into int:\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = pengu_cli("build", "--test", "--prune-types")
    assert res.returncode == 0, res.stderr
    c = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert "struct Unused" in c
    assert "GONE" in c
    assert "--prune-types" not in c


def test_prune_types_keeps_type_named_by_size_of(expand):
    c = expand(
        """
rune Sized:
    v as int

rune Dropped:
    z as int

weave main into int:
    let n as usize is size of Sized
    return 0
""",
        tag="types_sizeof",
        env={"PENGU_PRUNE_TYPES": "1"},
    )
    assert "struct Sized" in c
    assert "struct Dropped" not in c
