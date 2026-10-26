"""Regression: a local parameter shadows an imported module of the same name.

Before this fix, a file that imported a module as `span` made an unrelated
parameter named `span` resolve as the module, and `span.a` was emitted as the
undefined C identifier `span_a`.
"""
from __future__ import annotations


def test_local_parameter_shadows_imported_module_alias(emit_c):
    c = emit_c("""
import std.sourcemap as span

rune S:
    a as int

weave read_it with span as S into int:
    return span.a

weave main into int:
    var s as S is with a is 7
    return calling read_it with s
""", filename="shadow.pengu")
    assert "span.a" in c
    assert "span_a" not in c
