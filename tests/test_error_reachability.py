"""Roadmap 2.0 Phase 8 / item 8.9 -- every diagnostic code is *reachable*.

``docs/error_catalog.json`` is the source of truth: it lists the codes the
compiler can report, split into ``errors``, ``warnings`` and the project/lockfile
``project`` layer.  A catalogue nobody exercises rots: a code can become dead
documentation (nothing emits it any more) or a definition can drift away from
the check that is supposed to raise it.  This module closes that hole by
compiling one **minimal** Pengu program per code and asserting that the compiler
reports *that* code -- not a lookalike, not a different diagnostic.

Structured surface (Annex C rule C1)
------------------------------------
No assertion here inspects generated C, the source text, or the rendered
diagnostic prose:

* **Errors** are read through the ``PenguError.code`` attribute -- the field the
  CLI/LSP serialise into ``pengu check --json`` diagnostics and the LSP carries
  over the wire.  ``tests.conftest.check_error`` exists and is used by the rest
  of the suite, but it asserts on ``str(exc)``, which is exactly the text
  matching C1 forbids as the *primary* evidence; this module reads ``.code``
  directly instead (and also keeps the structured ``.line``).
* **Warnings** are stored by the checker as plain strings in
  ``PenguChecker.warnings`` (``"[Wxxxx] message [on line L col C]"``).  The
  documented machine-readable part is the bracketed code, so it is parsed with
  ``_WARNING_CODE_RE`` and asserted on the parsed value; the message body is
  never inspected.  The CLI's ``check --json`` returns the same code, but
  spawning a subprocess per snippet would be ~70x slower for no extra fidelity.

Each program is compiled through the real front end (``PenguParser`` ->
``PenguChecker``) and, when checking is clean, through the backend
(``PenguCodegen``) so that a diagnostic emitted only during emission (a backend
invariant guard) is still visible to the reachability claim.

Exemptions
----------
Codes that cannot be reached by compiling *any* source program live in
``UNREACHABLE`` with a written reason.  ``test_exempted_code_is_unreachable``
is marked ``xfail(strict=True)``: it fails today (so it is expected to fail) and
turns into a hard failure the moment the code becomes reachable -- either
because someone adds a program to ``REACHABLE`` or because the compiler starts
emitting it for a program in the compiled corpus.  That forces the exemption to
be deleted instead of silently outliving its reason.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from tests.conftest import REPO

CATALOG_PATH = REPO / "docs" / "error_catalog.json"

# ---------------------------------------------------------------------------
# The table: one minimal program per diagnostic code.
#
# ``code -> (source, why)``.  ``why`` names the condition from the catalogue the
# program is meant to exercise, so a reviewer can check the pair without
# re-deriving it from the compiler.  Sources are written with explicit "\n" so
# the indentation the PenguParser sees is unambiguous.
# ---------------------------------------------------------------------------
REACHABLE: Dict[str, Tuple[str, str]] = {
    "E0000": (
        "weave main into int:\n"
        "    var x as int is (\n"
        "    return 0\n",
        "Lark syntax error (unterminated initializer).  The other two E0000 "
        "conditions are codegen invariant guards; the code is reachable as the "
        "'source does not parse' bucket.",
    ),
    "E0001": (
        "weave main with a as int into int:\n"
        "    const X as int is a + 100\n"
        "    return 0\n",
        "'const' inside a weave whose initializer is not compile-time evaluable.",
    ),
    "E0002": (
        "var global_x as int is 10\n"
        "weave main into int:\n"
        "    return 0\n",
        "'var' declared at top level.",
    ),
    "E0003": (
        "rune Player:\n"
        "    x as int\n"
        "\n"
        "enchanting Player:\n"
        "    weave move into void:\n"
        "        set self.x is 20\n",
        "'self' (always a reference inside 'enchanting') accessed with '.', not '->'.",
    ),
    "E0004": (
        "weave main into int:\n"
        "    let x is undefined_thing\n"
        "    return 0\n",
        "Identifier absent from the symbol table.",
    ),
    "E0005": (
        "weave main into int:\n"
        "    var f as float is 3.0\n"
        "    set f %= 2.0\n"
        "    return 0\n",
        "Compound '%=' applied to a non-integer target.",
    ),
    "E0006": (
        "weave main into void:\n"
        "    let x as int is 10\n"
        "    set x is 20\n",
        "Assignment to an immutable 'let' binding.",
    ),
    "E0007": (
        "weave main into void:\n"
        "    break\n",
        "'break' outside any loop.",
    ),
    "E0008": (
        "weave main into void:\n"
        "    banish 42\n",
        "'banish' applied to a literal instead of an lvalue.",
    ),
    "E0009": (
        "weave main into void:\n"
        "    set .x is 10\n",
        "Leading-dot field assignment outside a 'with' block.",
    ),
    "E0010": (
        "weave main into void:\n"
        "    let v is with x is 1, y is 2\n",
        "Bare 'with' struct-init whose fields match no rune, so no type can be inferred.",
    ),
    "E0011": (
        "const FOO is 1\n"
        "const FOO is 2\n"
        "\n"
        "weave main into int:\n"
        "    return 0\n",
        "Constant redefined with a conflicting value.",
    ),
    "E0012": (
        "alias Texture as opaque\n"
        "\n"
        "weave main into void:\n"
        "    let t as Texture is with id is 1\n",
        "Opaque type instantiated with a 'with' block.",
    ),
    "E0013": (
        "rune Player:\n"
        "    hp as int\n"
        "\n"
        "weave main into void:\n"
        "    var p as Player with:\n"
        "        set .hp is 100\n"
        "    set p.unknown_field is 50\n",
        "Field access on a rune that has no such field.",
    ),
    "E0014": (
        "weave main into void:\n"
        "    let x is maybe none\n",
        "'maybe none' without an explicit type context.",
    ),
    "E0015": (
        "weave main into int:\n"
        "    var m as array of array of f32 with size 2 is []\n"
        "    return 0\n",
        "Inner array dimension not inferable from an empty literal.",
    ),
    "E0016": (
        "weave main into int:\n"
        "    let k is KEY_W\n"
        "    return k\n",
        "C define used without a prior 'include'.",
    ),
    "E0017": (
        "weave main into int:\n"
        "    let x is 42\n"
        "    let a, b is x\n"
        "    return 0\n",
        "Destructuring a value whose type does not support destructuring.",
    ),
    "E0018": (
        "weave main into void:\n"
        "    var l as list of int is list of int with capacity 10\n"
        "    calling l.push with \"hi\"\n",
        "List push of a value that does not match the element type.",
    ),
    "E0019": (
        "weave f into void:\n"
        "    var s as string is \"{out},\"\n",
        "Undefined variable referenced inside string interpolation.",
    ),
    "E0020": (
        "weave get_number into int:\n"
        "    return\n",
        "Bare 'return' in a weave declared to return 'int'.",
    ),
    "E0021": (
        "rune Pair shard T, U:\n"
        "    first as T\n"
        "    second as U\n"
        "\n"
        "weave main into void:\n"
        "    let p as Pair is with first is 1, second is 2\n",
        "Generic type used without its 'of' type arguments.",
    ),
    "E0022": (
        "weave f with x as Undefined into void:\n"
        "    return\n",
        "Unknown name in type position used as a bare type parameter outside 'shard'.",
    ),
    "E0023": (
        "weave bad_func with a as many int, b as many int into void:\n"
        "    return\n",
        "Two 'many' parameters in one function.",
    ),
    "E0024": (
        "weave bad_func with a as many int, b as int into void:\n"
        "    return\n",
        "'many' parameter followed by a normal parameter.",
    ),
    "E0025": (
        "weave f into int:\n"
        "    return 1\n",
        "Weave implementation body inside a '.d.pengu' declaration file "
        "(see _FILENAMES).",
    ),
    "E0026": (
        "insignia webui_\n"
        "declare new_window into int\n"
        "insignia raylib_\n"
        "declare init_window into int\n",
        "Second 'insignia' directive in the same file.",
    ),
    "E0027": (
        "omen Mitad:\n"
        "    Uno\n"
        "    Dos\n"
        "    Tres is 5\n"
        "    Cuatro is 1\n",
        "Two omen variants share an explicit value.",
    ),
    "E0028": (
        "omen ResultPayload:\n"
        "    Ok with val as int\n"
        "    Err is 404 with msg as string\n",
        "Explicit value assigned to an algebraic (payload) omen variant.",
    ),
    "E0029": (
        "omen Floats:\n"
        "    A is 3.14\n"
        "    B\n",
        "Omen variant value that is not a compile-time integer constant.",
    ),
    "E0030": (
        "concept Printer:\n"
        "    weave ritual describe into string\n"
        "\n"
        "rune Dot:\n"
        "    x as int\n"
        "\n"
        "bind Dot with Printer:\n"
        "    weave describe into string:\n"
        "        return \"dot\"\n",
        "Bind-block method signature does not match the concept declaration.",
    ),
    "E0031": (
        "concept Greeter:\n"
        "    weave greet into void\n"
        "    weave goodbye into void\n"
        "\n"
        "rune Person:\n"
        "    name as string\n"
        "\n"
        "bind Person with Greeter:\n"
        "    weave greet into void:\n"
        "        return\n",
        "Bind block omits a method the concept requires.",
    ),
    "E0032": (
        "weave g shard T where T: Num with v as T into void:\n"
        "    return\n"
        "\n"
        "weave main into int:\n"
        "    calling g with \"x\"\n"
        "    return 0\n",
        "Generic argument does not satisfy the 'where T: Num' bound.",
    ),
    "E0033": (
        "rune Point:\n"
        "    x as int\n"
        "\n"
        "enchanting Point:\n"
        "    weave ritual create into Point:\n"
        "        set self->x is 10\n"
        "        return with x is 10\n",
        "'self' used inside a 'ritual' (static) method.",
    ),
    "E0034": (
        "rune Point:\n"
        "    x as int\n"
        "\n"
        "enchanting Point:\n"
        "    weave ritual create into Point:\n"
        "        return with x is 0\n"
        "\n"
        "weave main into int:\n"
        "    var p as Point is with x is 5\n"
        "    var p2 as Point is calling p.create\n"
        "    return 0\n",
        "Ritual (static) method called on an instance.",
    ),
    "E0035": (
        "rune int:\n"
        "    x as int\n",
        "User type name collides with a C reserved word / standard identifier.",
    ),
    "E0036": (
        "const sp as int is 1\n"
        "import std.spark as sp\n",
        "Import alias collides with an existing symbol.",
    ),
    "E0037": (
        "weave f with arr as array of int with size 3 into void:\n"
        "    for i, i in arr:\n"
        "        return\n",
        "Loop index and element bindings share the same name.",
    ),
    "E0038": (
        "weave m into void:\n"
        "    let e is { \"x\": 1, \"x\": 2 }\n",
        "Duplicate key in a map literal.",
    ),
    "E0039": (
        "weave main into int:\n"
        "    let x is defined(int)\n"
        "    return 0\n",
        "'defined(...)' used outside a compile-time 'when' condition.",
    ),
    "E0040": (
        "const main as int is 1\n",
        "Top-level declaration of 'main', the reserved compile-time variable.",
    ),
    "E0041": (
        "weave run into void:\n"
        "    var x as array of int with size 5 is [1, 2, 3]\n",
        "Array literal length does not match the declared fixed size.",
    ),
    "E0042": (
        "weave main into void:\n"
        "    let r as range of int is 10 to 1\n",
        "Compile-time descending range written with 'to'.",
    ),
    "E0043": (
        "rune Account:\n"
        "    _secret as i32\n"
        "    public_id as i32\n"
        "\n"
        "weave main into int:\n"
        "    var acc as Account is with _secret is 123, public_id is 1\n"
        "    let s is acc._secret\n"
        "    return 0\n",
        "Access to a field whose leading underscore marks it private.",
    ),
    "E0044": (
        "omen Status:\n"
        "    Ok\n"
        "    Err\n"
        "    Pending\n"
        "\n"
        "weave main into int:\n"
        "    var s as Status is Status_Ok\n"
        "    let code is judge s:\n"
        "        when Status_Ok -> 0\n"
        "        when Status_Err -> 1\n"
        "    return code\n",
        "Non-exhaustive 'judge' with no 'else ->' branch.",
    ),
    "E0045": (
        "declare open_file with path as string into maybe string\n"
        "weave main into int:\n"
        "    let f is try calling open_file with \"x\"\n"
        "    return 0\n",
        "'try' over 'maybe T' inside a weave returning 'int'.",
    ),
    "E0046": (
        "omen A:\n"
        "    ONE\n"
        "\n"
        "omen B:\n"
        "    ONE\n",
        "Same variant name declared by two different omens.",
    ),
    "E0049": (
        "weave bad shard T with a as T, b as T into T:\n"
        "    return a + b\n",
        "Operator used on a type parameter without the required concept bound.",
    ),
    "E0050": (
        "rune BadDirect:\n"
        "    b as BadDirect\n",
        "Recursive type containing itself by value (infinite size).",
    ),
    "E0051": (
        "weave f into slice of int:\n"
        "    var arr as array of int with size 4 is [1, 2, 3, 4]\n"
        "    return arr at 0 to 2\n",
        "Returning a slice of a stack array (the slice would dangle).",
    ),
    "E0052": (
        "concept Showable:\n"
        "    weave show with self as self into string\n"
        "\n"
        "bind int with Showable:\n"
        "    weave show with self as self into string:\n"
        "        return \"int\"\n"
        "\n"
        "bind int with Showable:\n"
        "    weave show with self as self into string:\n"
        "        return \"int again\"\n",
        "Same (type, concept) pair bound twice.",
    ),
    "E0053": (
        "weave main into void:\n"
        "    var x is 1\n"
        "    var x is 2\n",
        "Redefinition of a name in the same scope.",
    ),
    "E0054": (
        "rune PointA:\n"
        "    x as float\n"
        "    y as float\n"
        "\n"
        "rune PointB:\n"
        "    x as float\n"
        "    y as float\n"
        "\n"
        "weave main into int:\n"
        "    var p is with x is 1.0, y is 2.0\n"
        "    return 0\n",
        "Struct-init fields match more than one rune.",
    ),
    "E0055": (
        "weave f into int:\n"
        "    static var arr as array of int with size 3 is array of int with size 3\n"
        "    return 1\n",
        "Function-static variable declared with an array type.",
    ),
    "E0056": (
        "@nonexistent_attr\n"
        "weave foo:\n"
        "    var x is 1\n"
        "\n"
        "weave main:\n"
        "    calling foo\n",
        "Unsupported attribute applied to a declaration.",
    ),
    "E0057": (
        "weave get_emoji into char:\n"
        "    return '\U0001F600'\n",
        "Char literal whose codepoint exceeds the ASCII range.",
    ),
    "E0058": (
        "weave main into void:\n"
        "    let e is error\n",
        "'error' used outside an 'or:' error-handling block.",
    ),
    "E0063": (
        "weave f into void:\n"
        "    if true:\n"
        "        static var x as int is 1\n"
        "    return\n",
        "'static var' nested inside a conditional instead of the function body.",
    ),
    "E0064": (
        "test \"\":\n"
        "    return\n",
        "'test' block with an empty (unusable) name.",
    ),
    "E0065": (
        "rune BadRune:\n"
        "    FILE as i32\n"
        "    _FILE as i32\n"
        "\n"
        "weave main into int:\n"
        "    return 0\n",
        "Two fields that escape to the same C identifier.",
    ),
    "W0001": (
        "weave main into void:\n"
        "    let f as float is 10 to float\n"
        "    let i is f to int\n"
        "    let t is transmute f to int\n",
        "'transmute' is unsafe; use 'to' for safe conversions.",
    ),
    "W0002": (
        "echo Value:\n"
        "    as_int as int\n"
        "    as_float as float\n"
        "\n"
        "weave main into void:\n"
        "    var v as Value is with as_int is 42\n"
        "    let x is v.as_int\n",
        "Field read through an untagged 'echo' union.",
    ),
    "W0004": (
        "weave main into void:\n"
        "    unless true:\n"
        "        calling print with \"unreachable\"\n",
        "Dead 'unless' branch.",
    ),
    "W0005": (
        "weave helper into int:\n"
        "    return 100\n"
        "\n"
        "weave main into int:\n"
        "    var helper as int is 42\n"
        "    return helper\n",
        "Local variable shadows a global function of the same name.",
    ),
    "W0006": (
        "@deprecated\n"
        "weave old_helper into int:\n"
        "    42\n"
        "\n"
        "weave main:\n"
        "    let v is calling old_helper\n",
        "Use of a symbol marked '@deprecated'.",
    ),
    "W0007": (
        "weave f into int:\n"
        "    var x as int is 0\n"
        "    unsafe:\n"
        "        set x is x + 1\n"
        "    return x\n",
        "'unsafe:' block disables bounds/overflow checks.",
    ),
    "W0013": (
        "weave main into int:\n"
        "    var xs as list of int is [1, 2, 3, 4]\n"
        "    var s as slice of int is (xs at 1..3)\n"
        "    return 0\n",
        "Deprecated '..' range syntax.",
    ),
}

#: Codes no source program can reach, with the reason the exemption is valid.
#: ``test_exempted_code_is_unreachable`` is a strict xfail over this table.
UNREACHABLE: Dict[str, str] = {
    "W0000": (
        "Infrastructure fallback, not a language diagnostic: the CLI's "
        "_warning_diag maps any warning string that does not match "
        "'[Wxxxx] message' to W0000.  Every current emitter in pengu_checker.py, "
        "pengu_infer.py and pengu_parser.py tags its warning with a code, so no "
        "source program produces an unlabelled warning."
    ),
    "W0003": (
        "Reserved code kept so existing numbers never move: WARNING_CATALOG "
        "documents it as '(reserved)' with no condition, and "
        "tools/gen_error_catalog.py::extract_warnings finds no emitter for it."
    ),
    "E0061": (
        "Project/lockfile layer, not a source diagnostic: pengu.lock missing or "
        "stale under --locked/--frozen (pengu_project.py emits a plain "
        "'[E0061]' string).  Exercised by tests/test_lockfile.py and "
        "tests/test_phase6_bugfixes.py, not by a .pengu program."
    ),
    "E0062": (
        "Project layer: conflicting dependency version requirements during "
        "resolution, raised by the dependency code rather than by checking a "
        "source file.  Exercised by tests/test_lockfile.py."
    ),
}

#: Codes whose trigger depends on the *filename*, not only on the source text.
#: Kept out of ``REACHABLE`` so that table stays exactly ``code -> (source, why)``.
_FILENAMES: Dict[str, str] = {
    "E0025": "t.d.pengu",  # declaration-file rules key off the '.d.pengu' suffix
}

#: The checker stores warnings as strings; the bracketed code is their
#: documented machine-readable part (see ``_warning_diag`` in pengu_project.py).
_WARNING_CODE_RE = re.compile(r"^\[(W\d{4})\]")
_WARNING_POS_RE = re.compile(r" on line (\d+)(?: col (\d+))?$")


def _diagnostics(source: str, filename: str = "t.pengu") -> List[Dict[str, object]]:
    """Compiles ``source`` and returns its structured diagnostics.

    Each entry is ``{"code", "severity", "line"}``.  Error codes come from the
    ``PenguError.code`` attribute; warning codes from the ``[Wxxxx]`` prefix of
    the checker's warning strings (the message body is never read).  The backend
    runs only when checking was clean, so a codegen-only invariant guard is still
    observable without turning a normal check error into a codegen crash.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_codegen import PenguCodegen
    from pengu_parser.pengu_parser import PenguParser

    out: List[Dict[str, object]] = []
    parser = PenguParser()
    checker = PenguChecker(base_dir=str(REPO))
    try:
        tree = parser.parse(source)
    except Exception as exc:  # noqa: BLE001 - a parse failure *is* the diagnostic
        return [{
            "code": getattr(exc, "code", None) or "E0000",
            "severity": "error",
            "line": int(getattr(exc, "line", None) or 0),
        }]

    try:
        checker.check(tree, source=source, filename=filename)
    except Exception as exc:  # noqa: BLE001 - the exception carries the code
        out.append({
            "code": getattr(exc, "code", None) or "",
            "severity": "error",
            "line": int(getattr(exc, "line", None) or 0),
        })

    for text in getattr(checker, "warnings", None) or []:
        match = _WARNING_CODE_RE.match(str(text))
        pos = _WARNING_POS_RE.search(str(text))
        out.append({
            "code": match.group(1) if match else "W0000",
            "severity": "warning",
            "line": int(pos.group(1)) if pos else 0,
        })

    if not any(d["severity"] == "error" for d in out):
        try:
            codegen = PenguCodegen(checker.symbols, [filename], str(REPO),
                                   compile_env=checker.compile_env)
            codegen.collect_declarations([(filename, tree)])
            codegen.generate_bundle()
        except Exception as exc:  # noqa: BLE001 - backend invariant guard
            out.append({
                "code": getattr(exc, "code", None) or "",
                "severity": "error",
                "line": int(getattr(exc, "line", None) or 0),
            })
    return out


def _reachable_params():
    """``pytest.param`` list so a failing case is reported by its code."""
    return [
        pytest.param(code, source, why, id=code)
        for code, (source, why) in sorted(REACHABLE.items())
    ]


def _catalog() -> Dict[str, dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _corpus_codes() -> frozenset:
    """Every code the REACHABLE programs produce, compiled once.

    Used by the strict-xfail test below as a behavioural probe: if the compiler
    starts emitting an exempted code for any of these programs, the exemption
    stops being valid and the test flips from xfail to a hard failure.
    """
    codes = set()
    for code, (source, _why) in REACHABLE.items():
        for diag in _diagnostics(source, filename=_FILENAMES.get(code, "t.pengu")):
            codes.add(diag["code"])
    return frozenset(codes)


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,source,why", _reachable_params())
def test_code_is_reachable(code: str, source: str, why: str):
    """Compiling this program reports exactly ``code``.

    ``why`` documents which catalogue condition the program exercises.  The
    assertion uses the structured code field only (rule C1): for an error the
    *first and only* error diagnostic must be ``code``; for a warning the
    program must check and emit cleanly and the warning set must be ``{code}``.
    """
    diagnostics = _diagnostics(source, filename=_FILENAMES.get(code, "t.pengu"))
    errors = [d for d in diagnostics if d["severity"] == "error"]
    warnings = [d for d in diagnostics if d["severity"] == "warning"]

    if code.startswith("W"):
        assert errors == [], (
            f"{code} ({why}): the minimal program was expected to check cleanly, "
            f"but it reported errors: {errors}.  A codegen/parser crash here is a "
            f"C4 violation (no user input may produce a traceback)."
        )
        assert {d["code"] for d in warnings} == {code}, (
            f"{code} ({why}): expected only [{code}], got {warnings}"
        )
    else:
        assert errors, (
            f"{code} ({why}): the minimal program reported no error at all; "
            f"diagnostics: {diagnostics}"
        )
        assert errors[0]["code"] == code, (
            f"{code} ({why}): expected [{code}] to be the first error, "
            f"got {errors[0]['code']!r} ({errors[0]['line']})"
        )
        assert errors[0]["line"] >= 1, (
            f"{code} ({why}): the structured diagnostic carries no source line: "
            f"{errors[0]}"
        )


def test_table_accounts_for_every_catalogued_code():
    """The table covers every code, so a new one cannot be added silently.

    A code must be either exercised by a program in ``REACHABLE`` or carry a
    written, reviewable exemption in ``UNREACHABLE``; the two tables may not
    overlap or contain anything the catalogue does not document.
    """
    catalog = _catalog()
    assert {"errors", "warnings", "project"} <= set(catalog), (
        "docs/error_catalog.json lost a documented section"
    )
    documented = set(catalog["errors"]) | set(catalog["warnings"]) | set(catalog["project"])
    assert documented, "the catalogue is empty -- the source of truth moved?"

    covered = set(REACHABLE) | set(UNREACHABLE)
    assert not (documented - covered), (
        "these catalogued codes are neither exercised nor exempted: "
        f"{sorted(documented - covered)}"
    )
    assert not (covered - documented), (
        f"these table entries are not in the catalogue: {sorted(covered - documented)}"
    )
    assert not (set(REACHABLE) & set(UNREACHABLE)), (
        "a code cannot be both reachable and exempted: "
        f"{sorted(set(REACHABLE) & set(UNREACHABLE))}"
    )


def test_every_reachable_entry_is_documented():
    """A program without a stated reason is not reviewable."""
    for code, (source, why) in REACHABLE.items():
        assert source.strip(), f"{code} has an empty program"
        assert why.strip(), f"{code} has no explanation"


def test_every_exemption_states_a_reason():
    """An exemption without a concrete reason is a hole in the proof."""
    for code, reason in UNREACHABLE.items():
        assert len(reason.strip()) >= 40, (
            f"{code} is exempted with a reason too short to review: {reason!r}"
        )


def test_reachable_table_is_not_trivially_small():
    """Guard the extraction: an empty/misread table would make this file vacuous."""
    catalog = _catalog()
    assert len(REACHABLE) >= len(catalog["errors"]), (
        f"only {len(REACHABLE)} programs for {len(catalog['errors'])} error codes"
    )


@pytest.mark.parametrize("code", sorted(UNREACHABLE), ids=sorted(UNREACHABLE))
@pytest.mark.xfail(strict=True, reason="documented as unreachable from a source program")
def test_exempted_code_is_unreachable(code: str):
    """Expected to fail while the exemption is valid.

    The code is reachable as soon as either a program for it lands in
    ``REACHABLE`` or the compiler starts emitting it for a program in the
    compiled corpus.  ``strict=True`` turns that future pass into a failure, so
    the exemption in ``UNREACHABLE`` must be removed rather than silently
    outlive its reason (the assert message repeats the reason).
    """
    observed = _corpus_codes()
    assert code in REACHABLE or code in observed, (
        f"{code} is exempted as unreachable but was observed while compiling the "
        f"corpus: move it to REACHABLE and delete the UNREACHABLE entry "
        f"({UNREACHABLE[code]})"
    )
