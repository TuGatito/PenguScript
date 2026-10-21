"""The binding-level ``ldflag "..."`` directive.

``link "..."`` can only name a library.  A binding also needs a way to
contribute raw linker options that a library name cannot express -- the first
real user is raylib's Emscripten build, whose GLFW backend is the
``-sUSE_GLFW=3`` port selector rather than an archive.  The directive is
collected into ``Symbols.ldflags`` and propagated by the project builder.
"""
from __future__ import annotations


def test_ldflag_directive_is_collected(parse_and_check):
    errors, _, symbols = parse_and_check(
        'include "raylib.h"\n'
        'link "raylib"\n'
        'ldflag "-sUSE_GLFW=3"\n'
    )
    assert errors == []
    assert symbols.links == ["raylib"]
    assert symbols.ldflags == ["-sUSE_GLFW=3"]


def test_ldflag_inside_when_is_conditional(parse_and_check):
    errors, _, symbols = parse_and_check(
        "when wasm:\n"
        '    ldflag "-sUSE_GLFW=3"\n'
        "else:\n"
        '    ldflag "-framework"\n'
    )
    assert errors == []
    # The test host is not a wasm target, so only the else branch is active.
    assert symbols.ldflags == ["-framework"]
