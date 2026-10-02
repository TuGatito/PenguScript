"""Tests for FASE 1.5.4: Unicode escapes (\\u{...}, \\uNNNN) and CRLF normalization."""

import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import InvalidCharLiteralError, PenguError
from pengu_parser.pengu_codegen import PenguCodegen


def parse(source: str):
    return PenguParser().parse(source)


def check(source: str):
    tree = parse(source)
    return PenguChecker().check(tree, source=source)


def check_error(source: str, contains: str = "E0057"):
    with pytest.raises(PenguError) as exc_info:
        check(source)
    err = exc_info.value
    err_str = f"{err} [{getattr(err, 'code', '')}]"
    assert contains in err_str, f"Expected '{contains}' in error message, got:\n{err_str}"
    return err_str


def test_unicode_escape_in_interpolated_string():
    """Lexer distinguishes \\u{...} from interpolation blocks {...}."""
    src = '''weave greet with name as string into string:
    return "hello \\u{1F600} {name}!"
'''
    tree = parse(src)
    assert tree is not None
    check(src)


def test_char_literal_valid_escapes():
    """\\u0041 and \\u{41} are valid ASCII char literals ('A')."""
    src1 = """weave get_a into char:
    return '\\u0041'
"""
    check(src1)

    src2 = """weave get_a into char:
    return '\\u{41}'
"""
    check(src2)


def test_char_literal_codepoint_exceeding_ascii_rejected():
    """Char literals with codepoint > 0x7F raise E0057 (InvalidCharLiteralError)."""
    src_emoji = """weave get_emoji into char:
    return '\\u{1F600}'
"""
    err = check_error(src_emoji, contains="E0057")
    assert "exceeds ASCII range" in err

    src_omega = """weave get_omega into char:
    return '\\u03A9'
"""
    err2 = check_error(src_omega, contains="E0057")
    assert "exceeds ASCII range" in err2

    src_direct_unicode = """weave get_crab into char:
    return '🦀'
"""
    err3 = check_error(src_direct_unicode, contains="E0057")
    assert "exceeds ASCII range" in err3


def test_crlf_normalization():
    """Windows CRLF (\\r\\n) is normalized to LF (\\n) preserving line numbers."""
    posix_src = "weave main into int:\n    let x as int is 42\n    return x\n"
    crlf_src = "weave main into int:\r\n    let x as int is 42\r\n    return x\r\n"

    p = PenguParser()
    posix_tree = p.parse(posix_src)
    crlf_tree = p.parse(crlf_src)

    assert str(posix_tree) == str(crlf_tree)

    posix_checker = PenguChecker()
    posix_checker.check(posix_tree, source=posix_src)

    crlf_checker = PenguChecker()
    crlf_checker.check(crlf_tree, source=crlf_src)

    assert crlf_checker.source_code == posix_checker.source_code


def test_unicode_codegen():
    """Verify C codegen for strings with \\u{...} and \\uNNNN."""
    src = '''weave message into string:
    return "Hello \\u{1F600} \\u0041"
'''
    tree = parse(src)
    checker = PenguChecker()
    checker.check(tree, source=src)
    gen = PenguCodegen(checker.symbols)
    gen.collect_declarations([("main.pengu", tree)])
    c_code = gen.generate_function_definitions()
    assert "Hello" in c_code
    # \\u{1F600} is decoded to UTF-8 emoji 😀 and \\u0041 to A
    assert "😀" in c_code
    assert "A" in c_code
