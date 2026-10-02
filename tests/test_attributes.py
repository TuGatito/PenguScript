import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import UnknownAttributeError, SemanticError
from tests.conftest import gen_bundle


def test_attribute_inline_codegen():
    source = """
@inline
weave add with a as int, b as int into int:
    a + b

weave main:
    let x is calling add with 1, 2
"""
    c_code = gen_bundle(source)
    assert "always_inline" in c_code
    assert "static inline __attribute__((always_inline))" in c_code


def test_attribute_cold_codegen():
    source = """
@cold
weave log_error with code as int:
    var x is code

weave main:
    calling log_error with 404
"""
    c_code = gen_bundle(source)
    assert "__attribute__((cold))" in c_code


def test_attribute_deprecated_codegen_and_warning():
    source = """
@deprecated("use modern_calc instead")
weave legacy_calc with x as int into int:
    x * 2

weave modern_calc with x as int into int:
    x * 2

weave main:
    let res is calling legacy_calc with 5
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    checker.check(tree, source=source, filename="main.pengu")
    
    assert any("[W0006] Symbol 'legacy_calc' is deprecated: use modern_calc instead" in w for w in checker.warnings)
    
    c_code = gen_bundle(source)
    assert 'deprecated("use modern_calc instead")' in c_code


def test_attribute_deprecated_without_message():
    source = """
@deprecated
weave old_helper into int:
    42

weave main:
    let v is calling old_helper
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    checker.check(tree, source=source, filename="main.pengu")
    
    assert any("[W0006] Symbol 'old_helper' is deprecated" in w for w in checker.warnings)


def test_attribute_packed_rune_codegen():
    source = """
@packed
rune NetworkPacket:
    tag as int
    length as int

weave main:
    var p as NetworkPacket is with tag is 1, length is 2
"""
    c_code = gen_bundle(source)
    assert "struct __attribute__((packed)) NetworkPacket" in c_code


def test_attribute_align_rune_and_field_codegen():
    source = """
@align(16)
rune AlignedBuffer:
    @align(8)
    head as int
    tail as int

weave main:
    var b as AlignedBuffer is with head is 0, tail is 0
"""
    c_code = gen_bundle(source)
    assert "aligned(16)" in c_code
    assert "aligned(8)" in c_code


def test_unknown_attribute_fails():
    source = """
@nonexistent_attr
weave foo:
    var x is 1

weave main:
    calling foo
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    with pytest.raises(UnknownAttributeError) as exc_info:
        checker.check(tree, source=source, filename="main.pengu")
    assert exc_info.value.code == "E0056"
    assert "Unknown attribute '@nonexistent_attr'" in str(exc_info.value)


def test_packed_on_weave_fails():
    source = """
@packed
weave invalid_weave:
    var x is 1

weave main:
    calling invalid_weave
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    with pytest.raises(UnknownAttributeError) as exc_info:
        checker.check(tree, source=source, filename="main.pengu")
    assert exc_info.value.code == "E0056"
    assert "not supported on weave" in str(exc_info.value)


def test_inline_with_args_fails():
    source = """
@inline(42)
weave bad_inline:
    var x is 1

weave main:
    calling bad_inline
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    with pytest.raises(UnknownAttributeError) as exc_info:
        checker.check(tree, source=source, filename="main.pengu")
    assert exc_info.value.code == "E0056"
    assert "@inline" in str(exc_info.value)


def test_align_without_int_fails():
    source = """
@align("sixteen")
rune BadAlign:
    x as int

weave main:
    var b as BadAlign is with x is 0
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    with pytest.raises(UnknownAttributeError) as exc_info:
        checker.check(tree, source=source, filename="main.pengu")
    assert exc_info.value.code == "E0056"
    assert "@align" in str(exc_info.value)


def test_deprecated_field_warning():
    source = """
rune Config:
    @deprecated("use timeout_ms")
    timeout as int
    timeout_ms as int

weave main:
    var cfg as Config is with timeout is 10, timeout_ms is 20
    let t is cfg.timeout
"""
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    checker.check(tree, source=source, filename="main.pengu")
    assert any("[W0006] Symbol 'timeout' is deprecated: use timeout_ms" in w for w in checker.warnings)
