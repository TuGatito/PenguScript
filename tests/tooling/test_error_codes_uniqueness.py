"""Phase 0 / item 0.6 + Phase 7 / item 7.2 — error codes are unique and unambiguous.

The audit found codes shared between unrelated diagnostics (E0047 was used for
both the since-removed "banish an auto-owned variable" and "duplicate concept
binding"; E0035 for both "reserved C keyword" and "redefinition in the same
scope"; E0011 for both "conflicting constant" and "ambiguous struct init").
These tests pin the disambiguation so a future change cannot silently re-merge
them.  E0047/E0048 were retired with the implicit ownership model in 1.0 and are
reserved, never reused.

Phase 7 item 7.2 extends the file past ``kwargs.setdefault``: AUDIT_1.0.md §15.2
lists this module as a gate that went green over broken code because it ignored
the ~24 codes emitted as a bare ``SemanticError`` with an explicit ``code=``
keyword.  The second half of this file walks the AST of every emitter instead.
"""

import re
import sys
from pathlib import Path

import pytest

from pengu_parser import pengu_errors as E

REPO_ROOT = Path(__file__).resolve().parents[2]
ERRORS_SRC = Path(E.__file__).read_text(encoding="utf-8")
CHECKER_SRC = (Path(E.__file__).parent / "pengu_checker.py").read_text(encoding="utf-8")
INFER_SRC = (Path(E.__file__).parent / "pengu_infer.py").read_text(encoding="utf-8")


def _class_default_codes() -> dict:
    """Maps every error class to the code its ``__init__`` defaults to."""
    mapping: dict = {}
    cls = None
    for line in ERRORS_SRC.splitlines():
        m = re.match(r"class (\w+)\((\w+)\):", line)
        if m:
            cls = m.group(1)
            mapping.setdefault(cls, None)
        m2 = re.search(r'kwargs\.setdefault\("code", "(E\d+)"\)', line)
        if m2 and cls and mapping.get(cls) is None:
            mapping[cls] = m2.group(1)
    return {k: v for k, v in mapping.items() if v}


def test_error_class_default_codes_are_unique():
    """No two error classes may default to the same diagnostic code.

    The single documented exception is E0000, the generic "the source is not
    valid" bucket shared by the base ``SemanticError`` (its constructor's
    default) and ``ParseError`` (which is itself a SemanticError).
    """
    mapping = _class_default_codes()
    assert mapping, "no error classes with a default code were found"

    by_code: dict = {}
    for cls, code in mapping.items():
        by_code.setdefault(code, []).append(cls)

    # Base SemanticError carries E0000 as a constructor default, not via
    # setdefault, so it is not in `mapping`; add it explicitly for the check.
    by_code.setdefault("E0000", []).append("SemanticError")

    duplicates = {code: sorted(names) for code, names in by_code.items() if len(set(names)) > 1}
    assert duplicates == {"E0000": ["ParseError", "SemanticError"]}, (
        f"error codes are not unique per class: {duplicates}"
    )


def test_duplicate_concept_binding_has_its_own_code():
    """The binding collision is E0052, and the retired E0047 was not reused."""
    codes = _class_default_codes()
    assert codes.get("DuplicateConceptBindingError") == "E0052"
    # E0047/E0048 belonged to the removed implicit-ownership diagnostics.
    # Retiring a code means *reserving* it: nothing may claim it again.
    assert "E0047" not in set(codes.values())
    assert "E0048" not in set(codes.values())


def test_redefinition_is_not_the_c_keyword_code():
    """Redefinition/destructuring-dup is E0053; reserved C names stay E0035."""
    assert "f\"Redefinition of '{v_name}' in the same scope\"" in CHECKER_SRC
    assert "code=\"E0053\"" in CHECKER_SRC
    # The reserved-C-keyword diagnostics keep E0035.
    assert "is a reserved C keyword" in CHECKER_SRC
    assert "code=\"E0035\"" in CHECKER_SRC


def test_ambiguous_struct_init_is_not_the_constant_code():
    """Ambiguous struct init is E0054; conflicting constants stay E0011."""
    assert "Ambiguous struct init" in INFER_SRC
    assert "code=\"E0054\"" in INFER_SRC
    assert "Constant '{cname}' is redefined with conflicting values" in CHECKER_SRC
    assert "code=\"E0011\"" in CHECKER_SRC


def test_static_array_type_has_its_own_code():
    """The 'static var cannot be an array' diagnostic moved off E0035 to E0055."""
    assert "cannot have an array type" in CHECKER_SRC
    assert "code=\"E0055\"" in CHECKER_SRC


def test_slice_stack_return_has_its_own_code():
    """Roadmap 0.5 uses the dedicated E0051 for a slice of a stack array."""
    assert "code=\"E0051\"" in CHECKER_SRC


# ---------------------------------------------------------------------------
# Roadmap Phase 7 / item 7.2 — the raw emissions, not just the class defaults
#
# The tests above only read ``kwargs.setdefault("code", …)`` in
# ``pengu_errors.py``, so they were blind to the ~24 codes that are emitted as a
# bare ``SemanticError`` with an explicit ``code=`` keyword.  AUDIT_1.0.md §15.2
# lists this file by name as one of the four gates that went green over broken
# code.  The tests below close that hole with an AST walk over every emitter, so
# they see the same thing the compiler does.
# ---------------------------------------------------------------------------

#: Ratchet: how many distinct message *shapes* each code may carry.
#:
#: A new shape under an existing code is a new condition sharing a code — the
#: exact bug class item 7.2 exists to kill (``E0035`` used to carry 7 shapes
#: across 4 unrelated conditions).  Bumping a number here is the deliberate act
#: that says "yes, this code really covers one more condition"; forgetting to
#: bump it fails the build instead of silently widening a code's meaning.
#: Shapes are normalised, so interpolated values appear as ``{}`` and renaming a
#: local does not require touching this table.
CONDITION_SHAPES = {
    "E0000": 3, "E0001": 1, "E0002": 3, "E0003": 6, "E0004": 15, "E0005": 137, "E0006": 11,
    "E0007": 1, "E0008": 15, "E0009": 2, "E0010": 1, "E0011": 1, "E0012": 1, "E0013": 10,
    "E0014": 10, "E0015": 4, "E0016": 1, "E0017": 4, "E0018": 1, "E0019": 3, "E0020": 7,
    "E0021": 1, "E0022": 1, "E0023": 2, "E0024": 2, "E0025": 2, "E0026": 1, "E0027": 1,
    "E0028": 1, "E0029": 3, "E0030": 3, "E0031": 1, "E0032": 4, "E0033": 1, "E0034": 2,
    "E0035": 4, "E0036": 2, "E0037": 1, "E0038": 1, "E0039": 3, "E0040": 1, "E0041": 9,
    "E0042": 3, "E0043": 2, "E0044": 1, "E0045": 4, "E0046": 5,
    "E0049": 8, "E0050": 1, "E0051": 1, "E0052": 2, "E0053": 2, "E0054": 1, "E0055": 1,
    "E0056": 5, "E0057": 2, "E0058": 1, "E0063": 1, "E0064": 1, "E0065": 1,
}

#: The conditions ``E0035`` is allowed to cover.  Every one of them is "a user
#: name collides with a C reserved word or standard identifier"; anything else
#: belongs on its own code.
_E0035_FAMILY = (
    "Constant name '{}' is a reserved C keyword or standard identifier",
    "Function name '{}' is a reserved C keyword",
    "Function name '{}' is a reserved standard C function or identifier",
    "Type name '{}' is a reserved C keyword or standard identifier",
)


def _emissions() -> dict:
    """``{code: sorted message shapes}`` for every raw ``code=`` emission."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools import gen_error_catalog as G

    return {code: sorted(entry["conditions"])
            for code, entry in G.extract_error_emissions().items()}


def test_raw_emissions_are_visible_to_this_module():
    """Guards the extractor itself: an empty walk would make the rest vacuous."""
    emissions = _emissions()
    assert len(emissions) >= 59, f"only {len(emissions)} codes extracted"
    assert "E0035" in emissions and "E0058" in emissions


def test_every_emitted_code_has_exactly_one_condition_family():
    """A code may not silently grow a new, unrelated condition.

    This is the ratchet that closes the bug class AUDIT §15.2 described: it sees
    the raw emissions, so widening a code's meaning is a build failure until
    ``CONDITION_SHAPES`` is updated on purpose.
    """
    emissions = _emissions()
    actual = {code: len(shapes) for code, shapes in emissions.items()}

    grew = {code: (CONDITION_SHAPES.get(code, 0), n)
            for code, n in actual.items() if n > CONDITION_SHAPES.get(code, 0)}
    assert grew == {}, (
        "these codes gained a new condition shape without a deliberate ratchet "
        f"bump in CONDITION_SHAPES (was, now): {grew}"
    )

    unknown = sorted(set(actual) - set(CONDITION_SHAPES))
    assert unknown == [], (
        f"new diagnostic codes are not in CONDITION_SHAPES: {unknown}"
    )


def test_ratchet_is_not_padded():
    """A stale, too-large number would hide a removed condition."""
    emissions = _emissions()
    inflated = {code: (CONDITION_SHAPES[code], len(emissions.get(code, [])))
                for code in CONDITION_SHAPES
                if len(emissions.get(code, [])) < CONDITION_SHAPES[code]}
    assert inflated == {}, (
        f"CONDITION_SHAPES overstates these codes (table, actual): {inflated}"
    )


def test_no_message_shape_is_emitted_under_two_codes():
    """``message -> code`` must be a function.

    Two different codes for the same text is the "which one do I look up?" bug:
    the historical ``E0035``/``E0053`` and ``E0011``/``E0054`` overlaps were
    exactly this.
    """
    by_message: dict = {}
    for code, shapes in _emissions().items():
        for shape in shapes:
            by_message.setdefault(shape, []).append(code)
    ambiguous = {msg: sorted(codes) for msg, codes in by_message.items() if len(codes) > 1}
    assert ambiguous == {}, (
        f"these messages are emitted under more than one code: {ambiguous}"
    )


def test_e0035_covers_only_the_c_reserved_name_family():
    """Item 7.2: E0035 stops carrying unrelated conditions.

    Measured before the split, E0035 carried 7 shapes across 4 conditions: the
    C reserved-name collision, ``static var`` placement, an invalid ``test``
    name, and a field-name collision in C emission.  The last three moved to
    E0063/E0064/E0065.
    """
    assert _emissions()["E0035"] == sorted(_E0035_FAMILY), (
        "E0035 is carrying a condition outside the 'collides with C' family"
    )


@pytest.mark.parametrize("code,needle", [
    ("E0063", "'static var' is only allowed directly inside a function body"),
    ("E0064", "Test name must be a non-empty string or identifier"),
    ("E0065", "collides with field"),
])
def test_displaced_conditions_have_their_own_code(code, needle):
    """The three conditions moved off E0035 are emitted on new codes."""
    shapes = _emissions()[code]
    assert any(needle in shape for shape in shapes), (
        f"{code} does not carry the expected condition: {shapes}"
    )
    assert len(shapes) == 1, f"{code} should carry exactly one condition: {shapes}"


def test_the_split_is_real_not_cosmetic():
    """Compiling the three cases reports the new codes, not E0035.

    Pins the behaviour, not just the source text: the extractor above would pass
    even if the checker kept emitting the old code through another path.
    """
    from tests.conftest import check_error

    check_error('weave f into void:\n    if true:\n        static var x as int is 1\n    return\n',
                contains="E0063")
    check_error('test "":\n    return\n', contains="E0064")
    check_error('rune BadRune:\n    FILE as i32\n    _FILE as i32\n\nweave main into int:\n    return 0\n',
                contains="E0065")
    # ...and the C-reserved-name family keeps E0035.
    check_error("rune int:\n    x as int\n", contains="E0035")
