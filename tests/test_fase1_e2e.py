"""End-to-End Regression Suite covering all FASE 1 and FASE 1.5 items (0.15.0 -> 0.16.0)."""

import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import (
    ParseError,
    SemanticError,
    MutabilityError,
    PenguError,
)
from tests.conftest import check_error, check_ok


def parse(code: str):
    return PenguParser().parse(code)


def check(code: str, filename: str = "main.pengu"):
    tree = parse(code)
    checker = PenguChecker()
    checker.check(tree, source=code, filename=filename)
    return tree, checker


# ─────────────────────────────────────────────────────────────────────────────
# 1.1 Strict LALR(1) + Mandatory Newline
# ─────────────────────────────────────────────────────────────────────────────
def test_1_1_mandatory_statement_delimiter():
    """Statements on the same line without delimiter are rejected by strict parser."""
    src = "weave main into int:\n    var x as int is 1 var y as int is 2\n    return x\n"
    with pytest.raises(ParseError) as exc_info:
        parse(src)
    assert getattr(exc_info.value, "code", None) == "E0000"

    valid_newlines = "weave main into int:\n    var x as int is 1\n    var y as int is 2\n    return x + y\n"
    t, c = check(valid_newlines)
    assert len(c.errors) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 1.2 DedentError, BOM Normalization & Mixed Indentation
# ─────────────────────────────────────────────────────────────────────────────
def test_1_2_dedent_and_bom():
    """Dedent errors map cleanly to ParseError (E0000) and BOM is stripped cleanly."""
    bom_src = "\ufeffweave main into int:\n    return 42\n"
    t, c = check(bom_src)
    assert len(c.errors) == 0

    bad_dedent = "weave main into int:\n    let x as int is 1\n  let y as int is 2\n    return x\n"
    with pytest.raises(ParseError) as exc_info:
        parse(bad_dedent)
    assert getattr(exc_info.value, "code", None) == "E0000"


# ─────────────────────────────────────────────────────────────────────────────
# 1.3 Soft Keywords
# ─────────────────────────────────────────────────────────────────────────────
def test_1_3_soft_keywords():
    """'inline', 'ritual', and 'borrowed' act as modifiers and identifiers without collision."""
    src = """weave inline helper into int:
    var borrowed x as int is 10
    return x

weave ritual make into int:
    return calling helper
"""
    t, c = check(src)
    assert len(c.errors) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 1.4 Concept Bounds Enforcement
# ─────────────────────────────────────────────────────────────────────────────
def test_1_4_concept_bounds_enforced():
    """Instantiating generic rune with type not satisfying concept bounds raises E0032."""
    src = """rune NonPar:
    x as int

rune Box shard T where T: Par:
    val as T

weave main into void:
    var np as NonPar with:
        set .x is 1
    var b as Box of NonPar with:
        set .val is np
"""
    err = check_error(src, contains="E0032")
    assert "E0032" in err


# ─────────────────────────────────────────────────────────────────────────────
# 1.5 Namespace-Aware Mangling
# ─────────────────────────────────────────────────────────────────────────────
def test_1_5_namespace_mangling(tmp_path):
    """Generic monomorphized functions include qualified module prefix in mangled name."""
    (tmp_path / "mod_a.pengu").write_text("weave wrap shard T with x as T into T:\n    return x\n", encoding="utf-8")
    (tmp_path / "main.pengu").write_text("import mod_a\nweave main into int:\n    return calling mod_a.wrap with 42\n", encoding="utf-8")
    from pengu_project import resolve_imports
    p = PenguParser()
    order = resolve_imports(str(tmp_path), "main.pengu", p)
    checker = PenguChecker(base_dir=str(tmp_path))
    trees = []
    for i, fp in enumerate(order):
        with open(fp, "r", encoding="utf-8") as f:
            code = f.read()
        t = p.parse(code)
        checker.check(t, source=code, filename=fp, reset_symbols=(i == 0), import_order=order)
        trees.append((fp, t))
    cg = PenguCodegen(checker.symbols, order, str(tmp_path))
    cg.collect_declarations(trees)
    code = cg.generate_bundle()
    assert "mod_a_wrap" in code


# ─────────────────────────────────────────────────────────────────────────────
# 1.6 FrozenType Propagation
# ─────────────────────────────────────────────────────────────────────────────
def test_1_6_frozen_propagation():
    """Index access on frozen array produces frozen element; mutating it is rejected."""
    src = """weave main into int:
    var arr as frozen array of int with size 3 is [1, 2, 3]
    set arr at 0 is 10
    return 0
"""
    with pytest.raises(MutabilityError) as exc_info:
        check(src)
    assert exc_info.value.code == "E0006"


# ─────────────────────────────────────────────────────────────────────────────
# 1.5.1 Judge Payload Bindings and Guards
# ─────────────────────────────────────────────────────────────────────────────
def test_1_5_1_judge_payloads_and_guards():
    """Judge supports payload binding and guards."""
    src = """omen Number:
    Val with n as int

weave describe with x as Number into string:
    return judge x:
        when Number.Val with n if n > 0 -> "positive"
        when Number.Val with n if n < 0 -> "negative"
        when Number.Val with n -> "zero"
        else -> "unknown"
"""
    t, c = check(src)
    assert len(c.errors) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 1.5.2 Attribute Syntax
# ─────────────────────────────────────────────────────────────────────────────
def test_1_5_2_attributes():
    """Attributes @inline, @cold, @deprecated, @packed, @align parse and validate."""
    src = """@deprecated("use modern_weave instead")
@cold
weave old_fn into int:
    return 0

@packed
@align(8)
rune PackedPoint:
    x as i32
    y as i32
"""
    t, c = check(src)
    assert len(c.errors) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 1.5.3 Local Const with Compile-time Evaluation
# ─────────────────────────────────────────────────────────────────────────────
def test_1_5_3_local_const():
    """Local const declarations inside weaves evaluate at compile-time."""
    src = """weave compute into int:
    const A is 10
    const B is A * 2 + 5
    return B
"""
    t, c = check(src)
    assert len(c.errors) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 1.5.4 Unicode Escapes and CRLF
# ─────────────────────────────────────────────────────────────────────────────
def test_1_5_4_unicode_and_crlf():
    """Unicode escapes in strings and chars, and CRLF line ending normalization."""
    src = "weave get_greet into string:\r\n    const GREET is \"Hello \\u{1F600}!\"\r\n    return GREET\r\n"
    t, c = check(src)
    assert len(c.errors) == 0
