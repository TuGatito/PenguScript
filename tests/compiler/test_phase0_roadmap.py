"""Regression tests for the Phase 0 (roadmap 1.0.0) items closed after the
initial round of fixes.

Covered here:

* 0.11 — the range counter follows the inferred bound type (int32_t for 'int'
  bounds, int64_t for a 64-bit bound), which the previous "always int64_t"
  implementation got wrong.
* 0.12 — a 'test' block may shadow a same-file global (the scope isolation
  change had turned that into a false E0035 redefinition, which broke every
  std module using 'test' blocks, e.g. std/tally.pengu).
* 0.16 — `pengu bind` erases GNU attributes together with their (multi-comma)
  argument list.
* 0.17 — the implicit 'error' binding of an 'or:' block is scoped.
* 0.20 — a project's custom `lib_dir` is honoured by import resolution and the
  LSP.
"""

import pytest

from tests.conftest import (
    check_error,
    check_ok,
    gen_bundle,
    have_tool,
)


# ---------------------------------------------------------------------------
# 0.11 — range counter type follows the bounds
# ---------------------------------------------------------------------------


def test_int_range_uses_int32_counter():
    c = gen_bundle("weave main into int:\n  for i from 0 to 5:\n    return i\n  return 0\n")
    assert "for (int32_t i = 0; i < 5; i++)" in c


def test_i64_range_uses_int64_counter():
    c = gen_bundle(
        "weave main into int:\n"
        "  for i from 0 to 5000000000 step 1000000000:\n"
        "    return i\n"
        "  return 0\n"
    )
    assert "for (int64_t i = 0;" in c


# ---------------------------------------------------------------------------
# 0.12 — test blocks may shadow a same-file global
# ---------------------------------------------------------------------------


def test_test_block_can_shadow_global_weave():
    check_ok(
        'weave last into int:\n'
        '  return 0\n'
        'test "shadow":\n'
        '  var last as int is 5\n'
        '  calling print with last\n'
    )


def test_test_block_shadowing_via_tally_module():
    """The exact shape that broke std/tally.pengu: consecutive test blocks each
    declaring a local named after a global weave."""
    check_ok(
        'weave chunk into int:\n'
        '  return 0\n'
        'test "a":\n'
        '  var out as int is 0\n'
        '  var last as int is out\n'
        '  calling print with last\n'
        'test "b":\n'
        '  var out as int is 0\n'
        '  var last as int is out\n'
        '  calling print with last\n'
    )


# ---------------------------------------------------------------------------
# 0.16 — GNU attributes are erased with their argument list
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not have_tool("gcc"), reason="gcc is required for the C preprocessor")
def test_bind_erases_packed_and_aligned_attributes(tmp_path):
    from pengu_bind import preprocess_and_parse

    header = tmp_path / "attrs.h"
    header.write_text(
        "struct __attribute__((packed)) PackedA { int x; };\n"
        "struct __attribute__((aligned(8), packed)) PackedB { int y; };\n"
        "int add(int a, int b) __attribute__((warn_unused_result));\n",
        encoding="utf-8",
    )
    ast, text, _ = preprocess_and_parse(str(header))
    assert ast is not None
    assert "PackedA" in text and "PackedB" in text
    # The attribute (and its argument list) must be gone, not left as '((packed))'.
    assert "((packed))" not in text
    assert "__attribute__" not in text


# ---------------------------------------------------------------------------
# 0.17 — the 'or:' error binding is scoped
# ---------------------------------------------------------------------------


def test_or_block_error_binding_is_scoped():
    source = (
        'weave may into maybe int:\n'
        '  return some 1\n'
        'weave f into void:\n'
        '  var x as int is 0\n'
        '  set x += calling may or:\n'
        '    calling print with "e"\n'
        '  calling print with error\n'
    )
    check_error(source, contains="only available inside")


# ---------------------------------------------------------------------------
# 0.20 — custom 'lib_dir' is honoured
# ---------------------------------------------------------------------------


def _make_libdir_project(tmp_path):
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "external" / "mylib" / "pengu").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: libdirproj\n  entry: src/main.pengu\n"
        "build:\n  lib_dir: external\n",
        encoding="utf-8",
    )
    (tmp_path / "external" / "mylib" / "pengu" / "mylib.pengu").write_text(
        'weave greet into string:\n    return "hi"\n', encoding="utf-8"
    )
    (tmp_path / "src" / "main.pengu").write_text(
        'import mylib\n\nweave main into int:\n    return 0\n', encoding="utf-8"
    )


def test_custom_lib_dir_resolves_imports(tmp_path):
    from pengu_parser.pengu_symbols import find_module_path, resolve_imports

    _make_libdir_project(tmp_path)
    root = str(tmp_path)
    assert find_module_path(root, "mylib") is None  # not under ./lib
    resolved = find_module_path(root, "mylib", lib_dir="external")
    assert resolved is not None and resolved.endswith("mylib.pengu")

    order = resolve_imports(root, "src/main.pengu", lib_dir="external")
    assert any(p.endswith("mylib.pengu") for p in order)


def test_checker_honours_custom_lib_dir(tmp_path):
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    _make_libdir_project(tmp_path)
    root = str(tmp_path)
    code = (tmp_path / "src" / "main.pengu").read_text(encoding="utf-8")
    checker = PenguChecker(base_dir=root, lib_dir="external")
    errors = checker.check(PenguParser().parse(code), source=code,
                           filename=str(tmp_path / "src" / "main.pengu"))
    assert not errors


def test_lsp_reads_project_lib_dir(tmp_path):
    from pengu_lsp.server import _lib_dir_for_project

    _make_libdir_project(tmp_path)
    assert _lib_dir_for_project(str(tmp_path)) == "external"
    # No manifest: falls back to the default.
    empty = tmp_path / "empty"
    empty.mkdir()
    assert _lib_dir_for_project(str(empty)) == "lib"
