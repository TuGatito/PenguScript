"""Phase 2 — E0047: a `(type, method)` pair is provided exactly once.

`enchanting int: weave clamp` emits the C symbol `int_clamp` with external
linkage.  Two modules providing it would collide at link time, and a call site
would have no way to choose, so the checker rejects the second declaration.

The cross-module case is checked with the *shared* symbol table the real build
uses: `pengu_project.py` checks the topological module order with one
``PenguChecker`` (``reset_symbols=False`` after the first module), which is why
the ownership map lives on the ``SymbolTable`` and not on the checker.
"""
from __future__ import annotations

import pytest

from tests.compiler.conftest import COMPILER_ROOT, FIXTURES

pytestmark = pytest.mark.smoke


def _check_two_modules(tmp_path, first: str, second: str):
    """Checks two source files with one checker, exactly like a real build."""
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_errors import PenguError
    from pengu_parser.pengu_parser import PenguParser

    parser = PenguParser()
    checker = PenguChecker(base_dir=str(tmp_path))
    path_a = tmp_path / "moda.pengu"
    path_b = tmp_path / "modb.pengu"
    errors = []
    for i, (path, source) in enumerate(((path_a, first), (path_b, second))):
        tree = parser.parse(source)
        try:
            checker.check(tree, source=source, filename=str(path),
                          reset_symbols=(i == 0))
        except PenguError as exc:
            errors.extend(getattr(exc, "all_errors", None) or [exc])
    return errors, checker.symbols


def test_duplicate_in_one_block_rejected(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    weave clamp into int:
        return self
    weave clamp into int:
        return self
""")
    assert any(e.code == "E0047" for e in errors), [e.code for e in errors]


def test_duplicate_across_blocks_rejected(parse_and_check):
    errors, _, _ = parse_and_check("""
enchanting int:
    weave clamp into int:
        return self

enchanting int:
    weave clamp into int:
        return self
""")
    assert any(e.code == "E0047" for e in errors), [e.code for e in errors]


def test_duplicate_across_modules_rejected(tmp_path):
    errors, symbols = _check_two_modules(tmp_path, """
enchanting int:
    weave clamp with lo as int, hi as int into int:
        return self
""", """
enchanting int:
    weave clamp with lo as int, hi as int into int:
        return self
""")
    assert [e.code for e in errors] == ["E0047"], [str(e) for e in errors]
    # The message names the module that already owns the pair.
    assert "moda" in str(errors[0]), str(errors[0])
    assert symbols.primitive_method_owners[("int", "clamp")][0].endswith("moda.pengu")


def test_same_method_on_different_primitives_is_fine(tmp_path):
    errors, _ = _check_two_modules(tmp_path, """
enchanting int:
    weave clamp into int:
        return self
""", """
enchanting i64:
    weave clamp into i64:
        return self
""")
    assert errors == [], [str(e) for e in errors]


def test_different_methods_on_the_same_primitive_is_fine(tmp_path):
    errors, _ = _check_two_modules(tmp_path, """
enchanting int:
    weave clamp into int:
        return self
""", """
enchanting int:
    weave double into int:
        return self + self
""")
    assert errors == [], [str(e) for e in errors]


def test_alias_spellings_collide_too(tmp_path):
    """`int32_t` and `int` are the same C type, so this is still a collision."""
    errors, _ = _check_two_modules(tmp_path, """
enchanting int:
    weave clamp into int:
        return self
""", """
enchanting int32_t:
    weave clamp into int:
        return self
""")
    assert [e.code for e in errors] == ["E0047"], [str(e) for e in errors]


def test_fixture_conflict_is_the_documented_failure(parse_and_check):
    source = (FIXTURES / "coherence_conflict.pengu").read_text(encoding="utf-8")
    errors, _, _ = parse_and_check(source, filename=str(FIXTURES / "coherence_conflict.pengu"))
    assert any(e.code == "E0047" for e in errors), [e.code for e in errors]
    assert COMPILER_ROOT.is_dir()
