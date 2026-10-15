"""``std.scrolls`` — edge cases and the internal-leak regression.

Two programs, batched as the stdlib conftest requires:

* the edge program pins the documented behaviour for empty strings, out-of-range
  slicing, empty delimiters, padding and parsing;
* the leak program drives the methods that used to allocate an unreleased
  temporary per call (``trim``/``trim_start``/``trim_end``, the case
  transforms, ``is_palindrome``, ``compare``, ``replace``, ``split*``).  It
  releases every returned value, so under ASan it fails with a leak report if
  the module ever allocates an intermediate again.

Run under a sanitizer to make the leak half real::

    PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer" \\
    PENGU_LDFLAGS="-fsanitize=address,undefined" \\
    ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 \\
    python -m pytest tests/stdlib/audit/test_scrolls_edges.py -v -p no:cacheprovider
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.scrolls

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave chk_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"
    banish got

weave eat with s as string into void:
    banish s
"""


def test_scrolls_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    var empty as string is ""
    var ab_c as string is "abc"
    var a_comma as string is "a,"
    var spaces as string is "   "
    var ws_mix as string is "\\t x \\n"
    var cat_cat as string is "cat, cat"
    var mixed as string is "MiXeD"
    var hw as string is "hello world"
    var hw_odd as string is "hELLO wORLD"
    var camel as string is "helloWorld"
    var snake as string is "hello_world"
    var acronym as string is "HTTPServer"
    var four_two as string is "42"
    var neg_four_two as string is "-42"
    var ab as string is "ab"
    var num_good as string is " 42 "
    var num_bad as string is "4x2"
    var flt_good as string is " -3.5 "
    var num_simple as string is "3.5"
    var num_twodots as string is "3.5.1"

    # split: empty receiver yields one empty part; a trailing delimiter yields a
    # final empty part; an empty delimiter yields the receiver itself.
    var one as list of string is calling empty.split with ","
    calling eq_i with one.len, 1, "split of empty"
    banish one
    var trailing as list of string is calling a_comma.split with ","
    calling eq_i with trailing.len, 2, "split keeps the trailing empty part"
    banish trailing
    var whole as list of string is calling ab_c.split with ""
    calling eq_i with whole.len, 1, "empty delim yields the receiver"
    calling eq_s with (whole at 0), "abc", "empty delim content"
    banish whole

    # substring / char_at bounds
    calling eat with (calling ab_c.get_substring with 5, 100)
    calling chk_s with (calling ab_c.get_substring with 5, 100), "", "substring past end"
    calling chk_s with (calling ab_c.get_substring with 0, -3), "", "substring negative end"
    calling chk_s with (calling ab_c.get_substring with -2, 2), "ab", "substring clamps start"
    calling chk_s with (calling ab_c.get_char_at with 9), "", "char_at past end"
    calling chk_s with (calling ab_c.get_char_at with -1), "", "char_at negative"

    # trim / trim_start / trim_end on all-whitespace and empty input
    calling chk_s with (calling spaces.get_trim), "", "trim all whitespace"
    calling chk_s with (calling spaces.get_trim_start), "", "trim_start all whitespace"
    calling chk_s with (calling spaces.get_trim_end), "", "trim_end all whitespace"
    calling chk_s with (calling empty.get_trim), "", "trim empty"
    calling chk_s with (calling ws_mix.get_trim), "x", "trim tabs and newlines"

    # starts_with / ends_with on the empty needle always match
    calling eq_b with (calling ab_c.starts_with with ""), true, "empty prefix"
    calling eq_b with (calling ab_c.ends_with with ""), true, "empty suffix"

    # join over an empty list is the empty string
    var none as list of string is list of string
    var joined as string is calling scrolls.join with none, ","
    calling eq_s with joined, "", "join of empty list"
    banish joined
    banish none

    # padding and zfill keep the sign first
    calling chk_s with (calling four_two.get_zfill with 5), "00042", "zfill positive"
    calling chk_s with (calling neg_four_two.get_zfill with 5), "-0042", "zfill negative"
    calling chk_s with (calling ab.get_center with 5, "-"), "-ab--", "center odd padding"
    calling chk_s with (calling ab.get_ljust with 4, "."), "ab..", "ljust"
    calling chk_s with (calling ab.get_rjust with 4, "."), "..ab", "rjust"

    # classification edges
    calling eq_b with (calling empty.is_space), false, "is_space empty is false"
    calling eq_b with (calling empty.is_blank), true, "is_blank empty is true"
    calling eq_b with (calling empty.is_alpha), false, "is_alpha empty is false"
    calling eq_b with (calling ab_c.is_alpha), true, "is_alpha true"
    var ab1 as string is "ab1"
    calling eq_b with (calling ab1.is_alpha), false, "is_alpha digits are false"
    calling eq_b with (calling ab1.is_alnum), true, "is_alnum"
    calling eq_b with (calling ab.is_palindrome), false, "is_palindrome"
    var aba as string is "aba"
    calling eq_b with (calling aba.is_palindrome), true, "is_palindrome true"
    calling eq_b with (calling empty.is_palindrome), true, "empty palindrome"

    # compare returns exactly -1 / 0 / 1
    var letter_a as string is "a"
    var letter_b as string is "b"
    var ab_long as string is "ab"
    calling eq_i with (calling letter_a.compare with letter_b), 0 - 1, "compare lt"
    calling eq_i with (calling letter_b.compare with letter_a), 1, "compare gt"
    calling eq_i with (calling letter_a.compare with letter_a), 0, "compare eq"
    calling eq_i with (calling letter_a.compare with ab_long), 0 - 1, "compare prefix lt"

    # replace only touches the first occurrence; empty needle inserts at the front
    calling eat with (calling cat_cat.get_replace with "cat", "dog")
    calling chk_s with (calling cat_cat.get_replace with "cat", "dog"), "dog, cat", "replace first"
    calling eat with (calling cat_cat.get_replace_all with "cat", "dog")
    calling chk_s with (calling cat_cat.get_replace_all with "cat", "dog"), "dog, dog", "replace_all"
    calling eat with (calling ab_c.get_replace with "", "X")
    calling chk_s with (calling ab_c.get_replace with "", "X"), "Xabc", "replace empty needle"

    # case conversion
    calling eat with (calling mixed.get_lower)
    calling chk_s with (calling mixed.get_lower), "mixed", "lower"
    calling eat with (calling mixed.get_upper)
    calling chk_s with (calling mixed.get_upper), "MIXED", "upper"
    calling eat with (calling mixed.get_swap_case)
    calling chk_s with (calling mixed.get_swap_case), "mIxEd", "swap_case"
    calling eat with (calling hw.get_capitalize)
    calling chk_s with (calling hw.get_capitalize), "Hello world", "capitalize"
    calling eat with (calling hw_odd.get_title)
    calling chk_s with (calling hw_odd.get_title), "Hello World", "title"

    # identifier casing
    calling eat with (calling camel.get_to_snake_case)
    calling chk_s with (calling camel.get_to_snake_case), "hello_world", "snake_case"
    calling eat with (calling camel.get_to_kebab_case)
    calling chk_s with (calling camel.get_to_kebab_case), "hello-world", "kebab_case"
    calling eat with (calling snake.get_pascal_case)
    calling chk_s with (calling snake.get_pascal_case), "HelloWorld", "pascal_case"
    calling eat with (calling acronym.get_pascal_case)
    calling chk_s with (calling acronym.get_pascal_case), "HttpServer", "pascal_case acronym"

    # numeric parsing
    var mi as maybe int is calling num_good.parse_int
    calling eq_b with mi.is_present, true, "parse_int present"
    banish mi
    var bad as maybe int is calling num_bad.parse_int
    calling eq_b with bad.is_present, false, "parse_int rejects garbage"
    banish bad
    var mf as maybe float is calling flt_good.parse_float
    calling eq_b with mf.is_present, true, "parse_float present"
    if f as float is mf:
        calling eq_b with (f == 0.0 - 3.5), true, "parse_float value"
    banish mf
    calling eq_b with (calling num_simple.is_numeric), true, "is_numeric true"
    calling eq_b with (calling num_twodots.is_numeric), false, "is_numeric two dots"
    calling eq_b with (calling empty.is_numeric), false, "is_numeric empty"

    calling spark.println with "DONE"
    return 0
""")


def test_scrolls_no_internal_leak(compile_and_run):
    """Every method here used to leak an unreleased temporary.

    The loop repeats the calls so a residual leak is large enough for
    LeakSanitizer to report it despite its conservative stack scan.
    """
    out = compile_and_run(_PRE + """
weave churn with src as string into void:
    calling eat with (calling src.get_trim)
    calling eat with (calling src.get_trim_start)
    calling eat with (calling src.get_trim_end)
    calling eat with (calling src.get_strip)
    calling eat with (calling src.get_lower)
    calling eat with (calling src.get_upper)
    calling eat with (calling src.get_swap_case)
    calling eat with (calling src.get_capitalize)
    calling eat with (calling src.get_title)
    calling eat with (calling src.get_to_snake_case)
    calling eat with (calling src.get_to_kebab_case)
    calling eat with (calling src.get_pascal_case)
    calling eat with (calling src.get_reverse)
    calling eat with (calling src.get_substring with 1, 4)
    calling eat with (calling src.get_char_at with 2)
    calling eat with (calling src.get_replace with "l", "L")
    calling eat with (calling src.get_replace_all with "l", "L")
    calling eat with (calling src.get_removeprefix with "  ")
    calling eat with (calling src.get_removesuffix with "  ")
    calling eat with (calling src.get_ljust with 20, ".")
    calling eat with (calling src.get_rjust with 20, ".")
    calling eat with (calling src.get_center with 20, ".")
    calling eat with (calling src.get_zfill with 20)
    calling eat with (calling src.get_truncate with 4, "...")
    calling eat with (calling src.get_ellipsis with 4)
    calling eat with (calling src.get_repeat with 2)
    calling eat with (calling src.get_repeat_join with 2, "-")
    var is_pal as bool is calling src.is_palindrome
    var alpha as bool is calling src.is_alpha
    var digit as bool is calling src.is_digit
    var alnum as bool is calling src.is_alnum
    var lower as bool is calling src.is_lower
    var upper as bool is calling src.is_upper
    var space as bool is calling src.is_space
    var blank as bool is calling src.is_blank
    var num as bool is calling src.is_numeric
    var cmp as int is calling src.compare with "zzz"

    var parts as list of string is calling src.split with ","
    banish parts
    var ws as list of string is calling src.split_whitespace
    banish ws
    var lines as list of string is calling src.lines
    banish lines
    var words as list of string is calling src.words
    banish words
    var chars as list of string is calling src.chars
    banish chars
    var codes as list of int is calling src.bytes
    banish codes
    var pf as maybe float is calling src.parse_float
    banish pf

weave main into int:
    var src as string is "  Hello, World!  "
    var i as int is 0
    while i < 200:
        calling churn with src
        set i is i + 1
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
