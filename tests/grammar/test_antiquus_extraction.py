"""Contract tests for the `antiquus` C-body extractor.

The extractor is the one delicate part of the feature: it runs *before* the
textual preprocessing passes (_strip_comments, _merge_chain_continuations,
_expand_short_struct_inits) and must hand the LALR parser an inert placeholder
without disturbing any other line of the file.
"""
from lark import Token

from pengu_parser.pengu_parser import PenguParser


def _find_body(tree):
    """Returns the C body carried by the first ANTIQUUS_BODY token, or None."""
    for st in tree.iter_subtrees():
        for c in st.children:
            if isinstance(c, Token) and c.type == "ANTIQUUS_BODY":
                return str(c)
    return None


def test_simple_body():
    src = '''antiquus f with a as int into int:
    """
    return a + 1;
    """

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert _find_body(tree) == "return a + 1;"


def test_hash_include_survives():
    src = '''antiquus f into int:
    """
    #include <stdio.h>
    return 0;
    """

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert "#include <stdio.h>" in _find_body(tree)


def test_arrow_at_line_start_survives():
    src = '''antiquus f into int:
    """
    if (x)
    ->field;
    return 0;
    """

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert "->field;" in _find_body(tree)


def test_with_inside_c_survives():
    src = '''antiquus f into int:
    """
    if (foo(with 1, 2)) return 0;
    return 1;
    """

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert "foo(with 1, 2)" in _find_body(tree)


def test_raw_triple():
    src = '''antiquus f into int:
    r"""
    printf("hello\\n");
    return 0;
    """

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert 'printf("hello\\n");' in _find_body(tree)


def test_single_line_body():
    src = '''antiquus f into int:
    """return 42;"""

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert _find_body(tree) == "return 42;"


def test_dedent_multiline():
    src = '''antiquus f into int:
    """
        if (a) {
            return 1;
        }
        return 0;
    """

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert _find_body(tree) == "if (a) {\n    return 1;\n}\nreturn 0;"


def test_line_numbers_after_body_are_preserved():
    """The extractor must not shift the position of later declarations."""
    src = '''weave before into int:
    return 0

antiquus f into int:
    """
    line one;
    line two;
    line three;
    """

weave after into int:
    return 1
'''
    tree = PenguParser().parse(src)
    names = {}
    for st in tree.iter_subtrees():
        if st.data == "weave_decl":
            name = next(str(c) for c in st.children if isinstance(c, Token) and c.type == "NAME")
            names[name] = st.meta.line
    assert names["before"] == 1
    # 'weave after' starts on source line 11; without line-count preservation
    # the three-line body would pull it up to line 8.
    assert names["after"] == 11


def test_antiquus_inside_string_is_not_extracted():
    src = '''const text as string is "antiquus f into int:"

weave main into int:
    return 0
'''
    tree = PenguParser().parse(src)
    assert _find_body(tree) is None


def test_nested_when_body():
    src = '''when os == "linux":
    antiquus getpid_c into int:
        """
        return (int)getpid();
        """
else:
    antiquus getpid_c into int:
        """
        return -1;
        """

weave main into int:
    return 0
'''
    parser = PenguParser()
    bodies = []
    tree = parser.parse(src)
    for st in tree.iter_subtrees():
        for c in st.children:
            if isinstance(c, Token) and c.type == "ANTIQUUS_BODY":
                bodies.append(str(c))
    # Subtree iteration is not source order; compare as a set.
    assert sorted(bodies) == sorted(["return (int)getpid();", "return -1;"])
