import pytest
import subprocess
import sys
from pathlib import Path

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_infer import TypeInferrer
from pengu_parser.pengu_errors import InvalidRitualCallError
from pengu_parser.pengu_symbols import SymbolTable, Symbol
from pengu_parser.pengu_types import (
    AliasType, BaseType, INT_TYPE, FLOAT_TYPE, STRING_TYPE, BOOL_TYPE, AnyType, MapType
)
from pengu_project import PenguBuilder, OutputType, ProjectConfig
from pengu_assets import _emit_disk_c, _asset_const_name


def _build_and_run(source: str, tmp_path: Path, extra_files=None) -> int:
    """Helper to check, codegen, compile and run generated C code cross-platform using PenguBuilder."""
    main_file = tmp_path / "main.pengu"
    main_file.write_text(source, encoding="utf-8")
    if extra_files:
        for fname, code in extra_files:
            p = Path(fname) if Path(fname).is_absolute() else (tmp_path / fname)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(code, encoding="utf-8")

    cfg = ProjectConfig(
        entry="main.pengu",
        base_dir=str(tmp_path),
        output=OutputType.EXE,
        links=["pengu_runtime"]
    )
    builder = PenguBuilder(cfg)
    out_path, _ = builder.compile()
    run_res = subprocess.run([out_path], capture_output=True, text=True)
    return run_res.returncode


def test_1_1_binding_c_keyword_name(tmp_path):
    """Bug 1.1: Binding if with C keyword (e.g. switch) must escape name and compile valid C."""
    code = """
weave main into int:
    var o as maybe int is some 42
    if switch as int is o:
        return switch
    return 0
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 42


def test_1_2_destructure_array_copy(tmp_path):
    """Bug 1.2: Destructuring an array variable must produce valid C and work correctly."""
    code = """
weave main into int:
    var xs as array of int with size 3 is [10, 20, 30]
    let a, b, c is xs
    return a + b + c
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 60


def test_1_3_destructure_rune_keyword_fields(tmp_path):
    """Bug 1.3: Destructuring a rune with C keyword fields must escape accessors."""
    code = """
rune Config:
    default as int
    register as int

weave main into int:
    var c as Config is with default is 15, register is 25
    let d, r is c
    return d + r
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 40


def test_1_4_indent_rune_keyword_field(tmp_path):
    """Bug 1.4: indent_literal for rune with C keyword fields must resolve types and emit properly."""
    code = """
rune Config:
    default as int
    switch as int

weave main into int:
    var c as Config is:
        default: 12
        switch: 28
    return c.default + c.switch
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 40


def test_1_5_obj_output_multiple_c(tmp_path):
    """Bug 1.5: OutputType.OBJ with multiple C sources must compile objects and combine via -r -nostdlib."""
    c_dir = tmp_path / "c"
    c_dir.mkdir()
    (c_dir / "extra1.c").write_text("int f1() { return 1; }", encoding="utf-8")
    (c_dir / "extra2.c").write_text("int f2() { return 2; }", encoding="utf-8")

    cfg = ProjectConfig(
        name="test_obj",
        version="0.1.0",
        base_dir=str(tmp_path),
        output=OutputType.OBJ,
    )
    builder = PenguBuilder(cfg)
    bundle_path = str(tmp_path / "bundle.c")
    output_path = str(tmp_path / "out.o")

    cmds = builder.build_compile_commands(bundle_path, output_path)
    # Should compile bundle.c to bundle.o, each c_source to an object, and link them with -r -nostdlib
    assert len(cmds) == 4
    last_cmd = cmds[-1]
    last_cmd_str = " ".join(last_cmd)
    assert ("-r" in last_cmd and "-nostdlib" in last_cmd) or ("link" in last_cmd and "-lib" in last_cmd)
    assert output_path in last_cmd_str


def test_1_6_is_present_on_call(tmp_path):
    """Bug 1.6: 'is present' on a function call rvalue must materialize temporary and compile cleanly."""
    code = """
weave get_maybe with x as int into maybe int:
    if x > 0:
        return some x
    return maybe none

weave main into int:
    if (calling get_maybe with 5) is present:
        return 1
    return 0
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 1


def test_1_7_ritual_only_call_fails_on_instance_method():
    """Bug 1.7: Calling an instance method statically on a type must raise InvalidRitualCallError (E0034)."""
    code = """
rune Player:
    hp as int

enchanting Player:
    weave heal with self as ref to Player, amount as int into int:
        return self->hp + amount

weave main into int:
    calling Player.heal with 10
    return 0
"""
    parser = PenguParser()
    checker = PenguChecker()
    tree = parser.parse(code)
    with pytest.raises(InvalidRitualCallError) as exc_info:
        checker.check(tree)
    assert "E0034" in str(exc_info.value) or exc_info.value.code == "E0034"


def test_1_8_import_alias_member_call(tmp_path):
    """Bug 1.8: Calling a member on an aliased import must resolve with the real module prefix."""
    mod_dir = tmp_path / "mymod"
    mod_dir.mkdir()
    maths_code = """
weave square with x as int into int:
    return x * x
"""
    (mod_dir / "maths.pengu").write_text(maths_code, encoding="utf-8")

    main_code = """
import mymod.maths as m

weave main into int:
    return calling m.square with 7
"""
    ret = _build_and_run(main_code, tmp_path, extra_files=[(str(mod_dir / "maths.pengu"), maths_code)])
    assert ret == 49


def test_1_9_alias_eq_symmetry():
    """Bug 1.9: AliasType.__eq__ must be nominal and symmetric."""
    alias1 = AliasType("UserId", INT_TYPE)
    alias2 = AliasType("AccountId", INT_TYPE)
    alias1_clone = AliasType("UserId", INT_TYPE)

    assert (alias1 == INT_TYPE) == (INT_TYPE == alias1)
    assert (alias1 == INT_TYPE) is False
    assert alias1 == alias1_clone
    assert alias1 != alias2


def test_1_10_add_any_int_returns_numeric():
    """Bug 1.10: Arithmetic add with AnyType and int must not return STRING_TYPE."""
    symbols = SymbolTable()
    symbols.define(Symbol(name="x", type=AnyType()))
    inferrer = TypeInferrer(symbols)
    parser = PenguParser()
    tree = parser.parse_expr("x + 1")
    res_t = inferrer.infer(tree)
    assert res_t != STRING_TYPE
    assert res_t == INT_TYPE or isinstance(res_t, AnyType)


def test_1_11_borrowed_contextual():
    """Bug 1.11: 'borrowed' can be used as a parameter and rune field name."""
    parser = PenguParser()
    code1 = """
weave process with borrowed as int into int:
    return borrowed
"""
    tree1 = parser.parse(code1)
    assert tree1.data == "start"

    code2 = """
rune Resource:
    borrowed as int
"""
    tree2 = parser.parse(code2)
    assert tree2.data == "start"


def test_1_12_map_lit_expr_keys(tmp_path):
    """Bug 1.12: map_lit supports expression keys (e.g. integer keys)."""
    code = """
weave main into int:
    var m as map of int to int is {1: 10, 2: 20}
    return calling m.len
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 2


def test_1_13_disk_assets_custom_module(tmp_path):
    """Bug 1.13: _emit_disk_c with custom module must not hardcode ARCA_* or _arca_*."""
    c_code = _emit_disk_c("recursos", [("test.txt", tmp_path / "test.txt")], "assets")
    assert "ARCA_ASSET_DIR_ENV" not in c_code
    assert "RECURSOS_ASSET_DIR_ENV" in c_code
    assert "_arca_cache" not in c_code
    assert "_recursos_cache" in c_code
    assert "_arca_names" not in c_code
    assert "_recursos_names" in c_code


def test_3_1_public_exports():
    """Bug 3.1: pengu_parser __all__ exports complete type system."""
    import pengu_parser
    for expected in [
        "FrozenType", "TypeParam", "NullType", "NULL_TYPE", "ConceptType",
        "SealType", "AnyType", "ManyType", "estimate_size", "mangle_type",
        "implements_concept", "resolve_concept_method", "is_opaque_type", "ast_to_type"
    ]:
        assert hasattr(pengu_parser, expected), f"Missing export: {expected}"
        assert expected in pengu_parser.__all__, f"Missing from __all__: {expected}"


def test_3_10_asset_const_name_custom_module():
    """Bug 3.10: _asset_const_name incorporates custom module prefix to prevent collision."""
    c_arca = _asset_const_name("logo.png")
    c_custom = _asset_const_name("logo.png", module="recursos")
    assert c_arca.startswith("ASSET_LOGO_PNG")
    assert c_custom.startswith("ASSET_RECURSOS_LOGO_PNG")
    assert c_arca != c_custom


def test_multilevel_pointer_alias_compatibility():
    """Verify that multi-level pointers with aliases compare strictly but compatibly."""
    from pengu_parser.pengu_types import BaseType, AliasType, RefType, FrozenType, INT_TYPE
    opaque = BaseType("opaque")
    sqlite3_alias = AliasType("sqlite3", opaque)

    r_opaque = RefType(RefType(opaque))
    r_sqlite = RefType(RefType(sqlite3_alias))

    assert r_opaque.is_compatible(r_sqlite)
    assert r_sqlite.is_compatible(r_opaque)

    # Multi-level pointers with different const/frozen qualifications must be rejected
    r_frozen = RefType(RefType(FrozenType(INT_TYPE)))
    r_mut = RefType(RefType(INT_TYPE))
    assert r_frozen.is_compatible(r_mut) is False
    assert r_mut.is_compatible(r_frozen) is False


def test_assets_list_custom_module(tmp_path):
    """Bug 1.1: pengu assets --list propagates custom module to constant names."""
    import subprocess
    import sys
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "pengu.yaml").write_text("""
project:
  name: demo
  version: 0.1.0
  entry: src/main.pengu
assets:
  dir: assets
  module: recursos
  embed: true
""")
    res = subprocess.run(
        [sys.executable, "pengu_project.py", "assets", "--config", str(tmp_path / "pengu.yaml"), "--list"],
        capture_output=True, text=True, check=True
    )
    assert "ASSET_RECURSOS_LOGO_PNG_" in res.stdout


def test_add_toml_twice_idempotent(tmp_path):
    """Bug 1.2: _update_config_dependency updates existing TOML sections without duplicating."""
    import tomllib
    from pengu_project import _update_config_dependency
    (tmp_path / "pengu.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n')
    _update_config_dependency(str(tmp_path), "foo", "https://example.com/foo.git", branch="main")
    _update_config_dependency(str(tmp_path), "foo", "https://example.com/foo-updated.git", branch="v2")
    with open(tmp_path / "pengu.toml", "rb") as f:
        data = tomllib.load(f)
    assert "dependencies" in data
    assert "foo" in data["dependencies"]
    assert data["dependencies"]["foo"]["url"] == "https://example.com/foo-updated.git"
    assert data["dependencies"]["foo"]["branch"] == "v2"


def test_field_access_c_keyword_reference():
    """Bug 1.3 / 1.4: C keyword references in field_access emit -> and resolve types."""
    from tests.conftest import gen_bundle
    src = """
rune Player:
    hp as int

weave f with default as Player into int:
    return default.hp

weave g with switch as ref to Player into int:
    if switch != null:
        return switch->hp
    return 0
"""
    c_code = gen_bundle(src)
    assert "_default.hp" in c_code
    assert "_switch->hp" in c_code


def test_map_iter_continue(tmp_path):
    """Bug 2.2: Map iteration handles continue without skipping increments or desyncing."""
    code = """
import std.spark

weave main into int:
    var m as map of string to int is {"a": 1, "b": 2, "c": 3}
    var count as int is 0
    var last_idx as int is -1
    for idx, k in m:
        set last_idx is idx
        if k == "b":
            continue
        set count is count + 1
    if count == 2 and last_idx == 2:
        return 0
    return 1
"""
    ret = _build_and_run(code, tmp_path)
    assert ret == 0


def test_strip_comments_inline_unclosed_hashhash():
    """Bug 2.3: Unclosed inline ## comment does not swallow subsequent code."""
    src = """weave f into int: ## doc sin cerrar
    return 1

weave main into int:
    return calling f
"""
    p = PenguParser()
    tree = p.parse(src)
    assert tree.data == "start"


def test_watch_json_no_ansi():
    """Bug 1.1: pengu test --watch --json must not emit ANSI escape sequences to stdout."""
    import sys
    import io
    from unittest.mock import patch
    from pengu_project import _watch_and_test, ProjectConfig

    cfg = ProjectConfig(name="test", base_dir="/tmp", entry="main.pengu")
    captured_out = io.StringIO()
    captured_err = io.StringIO()

    iterations = 0
    def mock_sleep(d):
        nonlocal iterations
        iterations += 1
        if iterations > 1:
            raise KeyboardInterrupt()

    mtime_calls = [10.0, 20.0, 30.0]

    with patch("pengu_project.ProjectConfig.load", return_value=cfg), \
         patch("pengu_project.test_project", return_value=0), \
         patch("pengu_project._find_watch_files", return_value=["/tmp/a.pengu"]), \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getmtime", side_effect=mtime_calls), \
         patch("time.sleep", side_effect=mock_sleep), \
         patch("sys.stdout", captured_out), \
         patch("sys.stderr", captured_err):
        _watch_and_test(json_output=True)

    out = captured_out.getvalue()
    err = captured_err.getvalue()
    assert "\033[2J" not in out
    assert "\033[H" not in out
    assert "[watching]" in err


def test_generic_method_on_non_generic_rune():
    """Bug 1.2: A generic method with shard_params inside an enchanting block is skipped in static collection."""
    from tests.conftest import gen_bundle
    src = """
rune Vec2:
    x as f32
    y as f32

enchanting Vec2:
    weave scale shard T with factor as T into Vec2:
        return with x is 1.0, y is 2.0

weave main into int:
    return 0
"""
    c_code = gen_bundle(src)
    assert "T factor" not in c_code
    assert "TypeParam" not in c_code


def test_escape_with_target_push():
    """Bug 1.3: Variable pushed via with block 'calling .push with s' must be marked as escaped."""
    from tests.conftest import gen_bundle
    src = """
weave f into void:
    var lst as list of string is list of string
    var s as string is "a" + "b"
    with lst:
        calling .push with s
"""
    c_code = gen_bundle(src)
    assert "pengu_banish_string(&s)" not in c_code


def test_struct_init_alias_type():
    """Bug 2.1: struct_init with an AliasType expected_type emits (AliasType){...} in C."""
    from tests.conftest import gen_bundle
    src = """
rune Point:
    x as int
    y as int

alias Pt as Point

weave make into Pt:
    return with x is 1, y is 2
"""
    c_code = gen_bundle(src)
    assert "(Pt){.x = 1, .y = 2}" in c_code or "(Pt){ .x = 1, .y = 2 }" in c_code


def test_omen_c_name_insignia_lookup():
    """Bug 2.3: _lookup_type_fn resolves real c_name of omen from symbol table."""
    from pengu_parser.pengu_codegen import PenguCodegen
    from pengu_parser.pengu_symbols import SymbolTable, Symbol
    from pengu_parser.pengu_types import OmenType

    st = SymbolTable()
    omen_t = OmenType("Status", {"Ok": {}, "Err": {}}, c_name="ml_Status")
    st.define(Symbol("Status", omen_t, "omen", c_name="ml_Status"))

    cg = PenguCodegen(st)
    cg.omens["Status"] = {"Ok": {}, "Err": {}}
    res_t = cg._lookup_type_fn("Status")
    assert res_t.c_name == "ml_Status"


def test_estimate_size_recursive_alias():
    """Bug 3.2: Circular or self-referential AliasType does not trigger infinite recursion in estimate_size."""
    from pengu_parser.pengu_types import AliasType, estimate_size

    a = AliasType("A", None)
    b = AliasType("B", a)
    a.target = b
    sz = estimate_size(a)
    assert sz == 8



