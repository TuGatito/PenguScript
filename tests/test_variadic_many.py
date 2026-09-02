import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_types import ManyType, SliceType, INT_TYPE
from pengu_parser.pengu_errors import MultipleManyParamsError, ManyParamNotLastError


def test_variadic_grammar_and_checker_success():
    code = """
weave sum_all with base as int and values as many int into int:
    var total as int is base
    for v in values:
        set total is total + v
    return total

weave main into void:
    let r1 is calling sum_all with 10 and 20 and 30 and 40
    let r2 is calling sum_all with 100
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(base_dir=".")
    checker.check(tree)

    fn_sum = checker.symbols.functions["sum_all"]
    assert len(fn_sum.params) == 2
    assert fn_sum.params[0][0] == "base"
    assert fn_sum.params[0][1] == INT_TYPE
    assert fn_sum.params[1][0] == "values"
    assert isinstance(fn_sum.params[1][1], ManyType)
    assert fn_sum.params[1][1].element == INT_TYPE


def test_variadic_multiple_many_error():
    code = """
weave bad_func with a as many int and b as many int into void:
    return
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(base_dir=".")
    with pytest.raises(MultipleManyParamsError) as exc_info:
        checker.check(tree)
    assert exc_info.value.code == "E0023"


def test_variadic_not_last_error():
    code = """
weave bad_func with a as many int and b as int into void:
    return
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(base_dir=".")
    with pytest.raises(ManyParamNotLastError) as exc_info:
        checker.check(tree)
    assert exc_info.value.code == "E0024"


def test_variadic_codegen():
    code = """
weave process_nums with nums as many int into int:
    var total as int is 0
    for n in nums:
        set total is total + n
    return total

weave main into void:
    let res1 is calling process_nums with 1 and 2 and 3
    let res2 is calling process_nums
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(base_dir=".")
    checker.check(tree)
    codegen = PenguCodegen(checker.symbols, ["main.pengu"], ".")
    codegen.collect_declarations([("main.pengu", tree)])
    c_code = codegen.generate_bundle()

    assert "PenguSlice nums" in c_code
    assert "_tmp_arr" in c_code
    assert "process_nums(" in c_code


def test_variadic_enchanting_method():
    code = """
rune Calculator:
    base as int

enchanting Calculator:
    weave add_many with extra as many int into int:
        var total as int is self->base
        for val in extra:
            set total is total + val
        return total

weave main into void:
    var calc is with base is 100
    let total is calling calc.add_many with 1 and 2 and 3
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(base_dir=".")
    checker.check(tree)
    codegen = PenguCodegen(checker.symbols, ["main.pengu"], ".")
    codegen.collect_declarations([("main.pengu", tree)])
    c_code = codegen.generate_bundle()

    assert "Calculator_add_many" in c_code
    assert "PenguSlice extra" in c_code
