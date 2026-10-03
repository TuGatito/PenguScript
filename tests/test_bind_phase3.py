"""Roadmap Phase 3 / §3.3 — `pengu bind` corrections.

- 3.3.1 anonymous enums become constants instead of being dropped
- 3.3.2 float / char / integer-constant-expression macros are bound
- 3.3.3 GNU `packed` / `aligned(N)` attributes become `@packed` / `@align(N)`
- 3.3.4 Doxygen tags produce a structured `##` docstring
- 3.3.7 implementation-reserved macro names are skipped
- 3.3.8 real headers (zlib, sqlite3, xxhash) still bind and check clean
"""

import pytest

from pengu_bind import _scan_struct_attributes, generate_bind_file
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import REPO, have_tool


def _bind(tmp_path, header_text, name="demo.h", **kw):
    hdr = tmp_path / name
    hdr.write_text(header_text, encoding="utf-8")
    out = tmp_path / (name.rsplit(".", 1)[0] + ".d.pengu")
    kw.setdefault("output", str(out))
    generate_bind_file(str(hdr), **kw)
    return out.read_text(encoding="utf-8")


def _check_ok(text, filename="demo.d.pengu"):
    checker = PenguChecker(base_dir=str(REPO))
    checker.check(PenguParser().parse(text), source=text, filename=filename)
    errs = [e for e in getattr(checker, "errors", []) if getattr(e, "severity", "error") == "error"]
    assert not errs, f"binding did not check clean: {[getattr(e, 'code', '') for e in errs]}"


def test_anonymous_enum_becomes_constants(tmp_path):
    text = _bind(tmp_path, "enum { ALPHA = 1, BETA = 2, GAMMA = (1 << 4) };\n")
    assert "const ALPHA as i64 is 1" in text
    assert "const BETA as i64 is 2" in text
    assert "const GAMMA as i64 is 16" in text
    _check_ok(text)


def test_float_char_and_expression_macros(tmp_path):
    text = _bind(tmp_path, (
        "#define PI 3.14159\n"
        "#define HALF 1.5f\n"
        "#define LETTER 'A'\n"
        "#define SHIFT (1 << 4)\n"
        "#define KBYTES (2 * 1024)\n"
        "#define NAME \"pengu\"\n"
        "#define CTRY (KBYTES | 1)\n"
    ))
    assert "const PI as f64 is 3.14159" in text
    assert "const HALF as f64 is 1.5" in text
    assert "const LETTER as char is 'A'" in text
    assert "const SHIFT as i64 is 16" in text
    assert "const KBYTES as i64 is 2048" in text
    assert 'const NAME as string is "pengu"' in text
    _check_ok(text)


def test_function_like_and_multiline_macros_skipped(tmp_path):
    text = _bind(tmp_path, (
        "#define MAX(a, b) ((a) > (b) ? (a) : (b))\n"
        "#define MULTI do { \\\n"
        "  x(); \\\n"
        "} while (0)\n"
        "#define PLAIN 7\n"
    ))
    assert "const PLAIN as i64 is 7" in text
    assert "MAX" not in text
    assert "MULTI" not in text


def test_reserved_macro_names_are_ignored(tmp_path):
    text = _bind(tmp_path, (
        "#define _MSC_VER 1930\n"
        "#define __INTERNAL 1\n"
        "#define _WIN32 1\n"
        "#define PUBLIC_ONE 1\n"
    ))
    assert "const PUBLIC_ONE as i64 is 1" in text
    assert "_MSC_VER" not in text
    assert "__INTERNAL" not in text
    assert "_WIN32" not in text


def test_doxygen_tags_produce_structured_docstring(tmp_path):
    text = _bind(tmp_path, (
        "/* Adds two numbers.\n"
        " * @param a first operand\n"
        " * @param b second operand\n"
        " * @return the sum\n"
        " * @deprecated use add2 instead\n"
        " */\n"
        "int add(int a, int b);\n"
    ))
    assert "## Adds two numbers." in text
    assert "## @param a first operand" in text
    assert "## @return the sum" in text
    assert "## @deprecated use add2 instead" in text
    _check_ok(text)


def test_plain_comment_stays_single_hash(tmp_path):
    text = _bind(tmp_path, "/* Just a plain description. */\nint f(void);\n")
    assert "# Just a plain description." in text
    assert "## Just a plain description." not in text


def test_struct_attributes_scanner():
    src = (
        "struct __attribute__((packed)) A { char c; int i; };\n"
        "struct B { char c; int i; } __attribute__((aligned(16)));\n"
        "typedef struct __attribute__((packed, aligned(8))) { char c; double d; } C;\n"
        "struct D { int x; };\n"
    )
    attrs = _scan_struct_attributes(src)
    assert attrs["A"] == {"packed": True}
    assert attrs["B"] == {"align": 16}
    assert attrs["C"] == {"packed": True, "align": 8}
    assert "D" not in attrs


def test_packed_and_align_become_attributes(tmp_path):
    text = _bind(tmp_path, (
        "struct __attribute__((packed)) PackedA { char tag; int value; };\n"
        "struct AlignedB { char c; int x; } __attribute__((aligned(16)));\n"
        "struct Plain { int x; int y; };\n"
    ))
    assert "@packed\nrune PackedA:" in text
    assert "@align(16)\nrune AlignedB:" in text
    # Plain structs must not get attributes.
    assert "@packed\nrune Plain:" not in text
    assert "@align\nrune Plain:" not in text
    _check_ok(text)


@pytest.mark.skipif(not have_tool("gcc"), reason="pengu bind needs gcc -E")
@pytest.mark.parametrize("rel,defines", [
    ("extern/zlib-1.3.2/zlib.h", ["Z_SOLO"]),
    ("build/include/sqlite3.h", None),
    ("std_c/xxhash.h", None),
    ("build/include/nanosvg.h", None),
])
def test_real_headers_still_bind_and_check(tmp_path, rel, defines):
    src = REPO / rel
    if not src.is_file():
        pytest.skip(f"{rel} not found")
    out = tmp_path / (src.name.replace(".h", ".d.pengu"))
    generate_bind_file(str(src), output=str(out), defines=defines)
    text = out.read_text(encoding="utf-8")
    assert "declare " in text or "rune " in text
    _check_ok(text, filename=str(out))
