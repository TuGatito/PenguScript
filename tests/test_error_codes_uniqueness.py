"""Phase 0 / item 0.6 — error codes are unique and unambiguous.

The audit found codes shared between unrelated diagnostics (E0047 used for both
"banish an auto-owned variable" and "duplicate concept binding"; E0035 used for
both "reserved C keyword" and "redefinition in the same scope"; E0011 for both
"conflicting constant" and "ambiguous struct init").  These tests pin the
disambiguation so a future change cannot silently re-merge them.
"""

import re
from pathlib import Path

from pengu_parser import pengu_errors as E

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
    """E0047 stays for AutoOwnedBanishError; the binding collision is E0052."""
    codes = _class_default_codes()
    assert codes.get("AutoOwnedBanishError") == "E0047"
    assert codes.get("DuplicateConceptBindingError") == "E0052"


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
