import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from lark import Tree, Token

from tests.conftest import gen_bundle
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_symbols import SymbolTable, Symbol
from pengu_parser.pengu_infer import TypeInferrer
from pengu_parser.pengu_types import ast_to_type, ArrayType, AnyType, INT_TYPE
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError
from pengu_project import ProjectConfig, PenguBuilder
import build_runtime


def test_or_block_operand_not_tree_does_not_crash():
    """P0 #1: _check_or_block does not crash with NameError when operand child is not a Tree."""
    checker = PenguChecker()
    dummy_node = Tree("or_block", [Token("IDENT", "val"), Tree("block", [])])
    # Should not raise NameError (left_t uninitialized)
    checker._check_or_block(dummy_node)


def test_banish_essence_of_pointer_frees_pointee():
    """P0 #2: banish essence of p frees the pointed address &(*p), not the dereferenced value."""
    src = """weave main into void:
    var p as ref to int is null
    banish essence of p
"""
    c = gen_bundle(src)
    assert "pengu_banish((void*)(&((*p))))" in c or "pengu_banish((void*)(&(*p)))" in c


def test_chained_set_index_through_ref_to_array():
    """P0 #3: set target indexing through ref to array unwraps RefType for chained access."""
    src = """weave test_fn with r as ref to array of array of int with size 2 with size 2 into void:
    set r at 0 at 1 is 42
"""
    c = gen_bundle(src)
    assert "r[0][1] = 42;" in c or "(*r)[0][1] = 42;" in c


def test_for_comp_over_anytype_reports_e0005():
    """P1 #5: for_comp over AnyType or non-iterable reports SemanticError E0005."""
    # 1. Non-iterable type through compiler pipeline
    src = """weave test_fn into void:
    var non_iter as int is 42
    var l is for x in non_iter then x
"""
    with pytest.raises(SemanticError) as exc_info:
        gen_bundle(src)
    assert "E0005" in str(exc_info.value.code) or "cannot iterate" in str(exc_info.value).lower()

    # 2. Inferrer check with explicit AnyType
    st = SymbolTable()
    st.define(Symbol("any_val", AnyType(), "var"))
    inferrer = TypeInferrer(st)
    node = Tree("for_comp", [
        Token("NAME", "x"),
        Tree("var_ref", [Token("NAME", "any_val")]),
        Tree("var_ref", [Token("NAME", "x")])
    ])
    with pytest.raises(SemanticError) as exc_any:
        inferrer.infer(node)
    assert exc_any.value.code == "E0005"


def test_some_of_anytype_reports_e0005():
    """P1 #10: some of AnyType or void value raises TypeMismatchError E0005."""
    st = SymbolTable()
    st.define(Symbol("unknown_var", AnyType(), "var"))
    inferrer = TypeInferrer(st)
    node = Tree("some_expr", [Tree("var_ref", [Token("NAME", "unknown_var")])])
    with pytest.raises(TypeMismatchError) as exc_info:
        inferrer.infer(node)
    assert exc_info.value.code == "E0005"
    assert "cannot wrap a void or unknown value" in str(exc_info.value)


def test_lambda_with_unknown_body_raises_semantic_error():
    """P0 #4: Lambda with unknown identifier in body propagates SemanticError instead of AnyType."""
    src = """weave test_fn into void:
    var fn is lambda x as int into unknown_var + 1
"""
    with pytest.raises(SemanticError) as exc_info:
        gen_bundle(src)
    assert "undefined identifier" in str(exc_info.value).lower() or "unknown_var" in str(exc_info.value)


def test_ast_to_type_multi_dim_order():
    """P1 #7: ast_to_type preserves array dimensions in AST nesting order."""
    src = """weave test_fn with a as array of array of int with size 2 with size 3 into void:
    return
"""
    tree = PenguParser().parse(src)
    param_type = None
    for n in tree.iter_subtrees():
        if n.data == "param":
            param_type = ast_to_type(n.children[1])
            break

    assert isinstance(param_type, ArrayType)
    assert param_type.size == 2
    assert isinstance(param_type.element, ArrayType)
    assert param_type.element.size == 3


def test_unclosed_doc_block():
    """P2 #12: Unclosed bare ## doc comment blanks lines through EOF and parses cleanly."""
    src = """weave f into int:
    return 1

##
Unclosed doc block line 1
Unclosed doc block line 2
"""
    tree = PenguParser().parse(src)
    assert tree.data == "start"


def test_config_hash_includes_src_dir_c_dir():
    """P2 #13: compute_config_hash factors in src_dir, c_dir, and output_name."""
    cfg1 = ProjectConfig(src_dir="src1", c_dir="c1", output_name="out1")
    cfg2 = ProjectConfig(src_dir="src2", c_dir="c1", output_name="out1")
    cfg3 = ProjectConfig(src_dir="src1", c_dir="c2", output_name="out1")
    cfg4 = ProjectConfig(src_dir="src1", c_dir="c1", output_name="out2")

    h1 = PenguBuilder(cfg1).compute_config_hash()
    h2 = PenguBuilder(cfg2).compute_config_hash()
    h3 = PenguBuilder(cfg3).compute_config_hash()
    h4 = PenguBuilder(cfg4).compute_config_hash()

    assert h1 != h2
    assert h1 != h3
    assert h1 != h4


def test_raylib_build_flags_macos():
    """P2 #14: build_raylib appends -D_GLFW_COCOA when targeting macOS (darwin)."""
    cmds = []
    with patch("sys.platform", "darwin"), \
         patch("build_runtime.run_cmd", side_effect=lambda c: cmds.append(c)), \
         patch("build_runtime.shutil.copy2"), \
         patch.object(Path, "unlink"), \
         patch.object(Path, "mkdir"):
        build_runtime.build_raylib("gcc", "ar", rebuild=True)

    assert any("-D_GLFW_COCOA" in c for c in cmds)
