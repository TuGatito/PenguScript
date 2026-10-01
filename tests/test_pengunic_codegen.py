#!/usr/bin/env python3
"""Codegen contracts required by the Pengunic standard-library rewrite.

Three behaviours were documented (or assumed) but not implemented, and they block
idiomatic generic stdlib code:

1. **Implicit return** (guide §4.11): a weave whose last statement is a value
   expression returns it.  Before, `weave f into int: x * 2` emitted `(x * 2);`
   with no `return`, so the function returned garbage.
2. **Generic `if v as T is <maybe>`**: inside a monomorphized generic
   enchanting the unwrapping cast was emitted with the *erased* type
   (`int32_t v = *(void* *)m.value`), producing C that does not compile.
3. **`bool to string` is a borrowed view**: `pengu_string_from_bool` returns a
   `.rodata` view, so releasing an interpolation temporary built from it called
   `free()` on static memory ("free(): invalid pointer").

Each test pins one of them; they are cheap (`gen_bundle` inspects the generated C)
except the last, which has to execute the binary to catch the invalid free.
"""

from tests.conftest import compile_run, gen_bundle, requires_cc, requires_runtime


def test_implicit_return_in_plain_weave():
    c = gen_bundle("weave double with x as int into int:\n    x * 2\n")
    assert "return (x * 2);" in c
    # ...and no dangling bare expression remains.
    assert "\n  (x * 2);\n" not in c


def test_implicit_return_in_concrete_enchanting_method():
    c = gen_bundle(
        "enchanting list of int:\n"
        "    weave total into int:\n"
        "        var acc as int is 0\n"
        "        for x in essence of self:\n"
        "            set acc is acc + x\n"
        "        acc\n"
    )
    assert "return acc;" in c


def test_implicit_return_in_monomorphized_generic_method():
    """The generic instance must return too (the emitter is shared)."""
    c = gen_bundle(
        "enchanting list of shard T where T: Num:\n"
        "    weave total into T:\n"
        "        var acc as T is donum T\n"
        "        for x in essence of self:\n"
        "            set acc is acc + x\n"
        "        acc\n"
        "\n"
        "weave main into int:\n"
        "    var xs as list of int is [1, 2, 3]\n"
        "    calling xs.total\n"
        "    return 0\n"
    )
    assert "list_int_total" in c
    assert "return acc;" in c


def test_no_implicit_return_for_void_weaves():
    c = gen_bundle("weave nothing into void:\n    var x as int is 1\n")
    assert "return x;" not in c


def test_generic_maybe_binding_uses_the_concrete_cast():
    """`if v as T is essence of self` must cast to T, never to void*."""
    c = gen_bundle(
        "enchanting maybe shard T:\n"
        "    weave is_some into bool:\n"
        "        if v as T is essence of self:\n"
        "            return true\n"
        "        return false\n"
        "\n"
        "weave main into int:\n"
        "    var m as maybe int is some 7\n"
        "    if calling m.is_some:\n"
        "        return 0\n"
        "    return 1\n"
    )
    assert "maybe_int_is_some" in c
    assert "(*(int32_t *)" in c
    assert "(*(void* *)" not in c


@requires_cc
@requires_runtime
def test_bool_interpolation_does_not_free_static_memory():
    """`{(cond to string)}` must not banish the runtime's '.rodata' view.

    `m is present` lowers to the runtime's ``bool``-returning
    ``pengu_maybe_is_present``; ``pengu_string_from_bool`` then hands back a
    static ``"true"/"false"`` view.  Releasing the interpolation temporary used to
    call ``free()`` on that literal.
    """
    res = compile_run(
        "import std.spark\n"
        "\n"
        "weave main into int:\n"
        "    var m as maybe int is some 7\n"
        "    calling spark.println with \"present: {((m is present) to string)}\"\n"
        "    return 0\n",
        tag="bool_interp",
    )
    assert "present: true" in res.stdout



def test_result_constructor_intrinsics_emit_boxed_results():
    """`calling ok_of/err_of with v` builds a heap-boxed PenguResult."""
    c = gen_bundle(
        "weave g into result of int to string:\n"
        "    return calling ok_of with 41\n"
        "\n"
        "weave b into result of int to string:\n"
        "    return calling oracle.err_of with \"boom\"\n"
    )
    assert "PenguResult" in c
    assert "pengu_sigil_alloc" in c
    # The constructor is never constant-folded into a bare 'return 41;'.
    assert "return 41;" not in c


def test_result_constructor_without_context_is_rejected():
    from tests.conftest import check_error

    check_error(
        "weave f into int:\n    var r is calling ok_of with 1\n    return 0\n",
        contains="E0014",
    )


def test_ok_err_are_still_valid_identifiers():
    """The constructors must not reserve 'ok'/'err' (60 test files use them)."""
    c = gen_bundle(
        "weave f into bool:\n"
        "    var ok as bool is true\n"
        "    var err as int is 0\n"
        "    if ok:\n"
        "        return err == 0\n"
        "    return false\n"
    )
    assert "ok" in c and "err" in c


@requires_cc
@requires_runtime
def test_result_construction_and_try_propagation():
    """ok_of/err_of build the native result, .error carries the failure, `try` propagates."""
    res = compile_run(
        "import std.spark\n"
        "\n"
        "weave good into result of int to string:\n"
        "    return calling ok_of with 41\n"
        "\n"
        "weave bad into result of int to string:\n"
        "    return calling oracle.err_of with \"boom\"\n"
        "\n"
        "weave plus_one into result of int to string:\n"
        "    let v is try calling good\n"
        "    return calling ok_of with (v + 1)\n"
        "\n"
        "weave main into int:\n"
        "    var a as result of int to string is calling good\n"
        "    var b as result of int to string is calling bad\n"
        "    var c as result of int to string is calling plus_one\n"
        "    calling spark.println with \"a={((a.value) to string)}\"\n"
        "    calling spark.println with \"b={b.error}\"\n"
        "    calling spark.println with \"c={((c.value) to string)}\"\n"
        "    return 0\n",
        tag="result_ctor",
    )
    assert "a=41" in res.stdout
    assert "b=boom" in res.stdout
    assert "c=42" in res.stdout


@requires_cc
@requires_runtime
def test_generic_method_with_own_shard_param_can_be_called_twice():
    """Regression: the second call used to fail with E0005.

    The first call cached its *specialized* signature in `symbols.methods`; the
    next call returned that cache entry instead of re-inferring the method's own
    type parameter (U in `maybe T .map shard U`), leaving nothing to bind.
    """
    res = compile_run(
        "import std.spark\n"
        "\n"
        "enchanting maybe shard T:\n"
        "    weave map shard U with f as weave with x as T into U into maybe U:\n"
        "        if v as T is essence of self:\n"
        "            return some (calling f with v)\n"
        "        return maybe none\n"
        "\n"
        "    weave unwrap_or with fallback as T into T:\n"
        "        if v as T is essence of self:\n"
        "            return v\n"
        "        return fallback\n"
        "\n"
        "weave double_it with x as int into int:\n"
        "    return x * 2\n"
        "\n"
        "weave triple_it with x as int into int:\n"
        "    return x * 3\n"
        "\n"
        "weave main into int:\n"
        "    var a as maybe int is some 1\n"
        "    var b as maybe int is some 2\n"
        "    var q1 as maybe int is calling a.map with double_it\n"
        "    var q2 as maybe int is calling b.map with triple_it\n"
        "    var v1 as int is calling q1.unwrap_or with 0\n"
        "    var v2 as int is calling q2.unwrap_or with 0\n"
        "    calling spark.println with \"{v1} {v2}\"\n"
        "    return 0\n",
        tag="generic_method_twice",
    )
    assert "2 6" in res.stdout


def test_generic_container_value_access_casts_to_the_element_type():
    """`.value`/`.error` on a *generic* maybe/result must cast to T.

    The concrete path cast correctly, but inside `enchanting maybe shard T` the
    field access fell back to the erased container field, emitting
    `return ((*self)).value;` — a `void*` returned as `int32_t`.
    """
    c = gen_bundle(
        "enchanting maybe shard T:\n"
        "    weave get_or with fallback as T into T:\n"
        "        if (essence of self).is_present:\n"
        "            return (essence of self).value\n"
        "        return fallback\n"
        "\n"
        "enchanting result of shard T to shard E:\n"
        "    weave value_or with fallback as T into T:\n"
        "        if (essence of self).is_ok:\n"
        "            return (essence of self).value\n"
        "        return fallback\n"
        "\n"
        "weave main into int:\n"
        "    var m as maybe int is some 3\n"
        "    var v as int is calling m.get_or with 0\n"
        "    var r as result of int to string is calling ok_of with 9\n"
        "    var w as int is calling r.value_or with 0\n"
        "    return v + w\n"
    )
    assert "maybe_int_get_or" in c
    assert "return ((*self)).value;" not in c
    assert "(*(int32_t *)((*self)).value)" in c
    assert "(*(int32_t *)((*self)).ok_val)" in c


@requires_cc
@requires_runtime
def test_local_shadows_module_function_of_the_same_name():
    """A local named like a module-level weave must be read as the local.

    `var words as list of string is calling s.split_words` shadows the module
    level `words` weave; reading `words.len` used to decay the *function* to a
    pointer and index it, which does not compile.
    """
    res = compile_run(
        "import std.spark\n"
        "\n"
        "weave words with s as string into list of string:\n"
        "    return [s]\n"
        "\n"
        "enchanting string:\n"
        "    weave split_words into list of string:\n"
        "        return calling words with essence of self\n"
        "\n"
        "weave main into int:\n"
        "    var s as string is \"hi\"\n"
        "    var words as list of string is calling s.split_words\n"
        "    let n is words.len\n"
        "    calling spark.println with \"shadowed len={n}\"\n"
        "    return 0\n",
        tag="local_shadow",
    )
    assert "shadowed len=1" in res.stdout
