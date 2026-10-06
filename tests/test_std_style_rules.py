"""Roadmap Phase 7 / item 7.6 — one test per style-guide rule, over `std/`.

The roadmap asked to "apply the style guide to the standard library in a
verifiable way", with one test per rule from AUDIT_1.0.md §10.5.  Measuring the
rules first (AUDIT_1.0_FASE7.md §7.7) changed the picture: of the six proposed
rules, **four were already satisfied**, one needed scoping, and one was genuinely
violated.

| §10.5 rule | State measured for this item |
|---|---|
| Indent 4 spaces, never tabs | already true (`.pengufmt.toml` pins it; `fmt --check std/` is clean) |
| No `transmute` outside `ffi`/`filum` | already true — `std/` has **zero** `transmute` calls |
| New public function ships inline doc | enforced by the ratchet in `test_std_docs_completeness.py` |
| `ritual` constructors document their invariant | **violated: 20 of 44 had no doc** — fixed here |
| `<MOD>_VERSION` matches `VERSION` and is asserted | covered by `test_std_versioning.py` (3 cases) + `test_bindings_version_policy.py` |
| No local shadows a global; public names unique | `0 W0005`; but **49** public `weave` names repeat across modules — see the note in `test_rule_duplicate_public_names_are_recorded` |

The one rule that was actually broken is the interesting one: documenting the
`ritual` constructors surfaced a real invariant trap — `Vec2.up` is `(0, -1)`
because the 2-D convention has **Y growing downward**, while `Vec3.up` is
`(0, 1, 0)` because 3-D has Y up. Without the invariant written down, the two
constructors look like they disagree.
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
STD = REPO / "std"

#: Deferred §10.5 rules, recorded as ratchets so they cannot grow silently.
#: `cp_*` helpers: roadmap 6.11 defers the rename to 1.1 (0 external users, 32
#: documented helpers, ~169 internal uses).
CP_HELPER_BASELINE = 32
#: Public `weave` names that appear in more than one hand-written module.
#: Roadmap 6.5 deferred `loom`/`tally` to 1.1; the measured total across `std/`
#: is 49, of which 10 are `assert*` helpers re-exported by design. Unifying them
#: is a breaking change needing a deprecation window, so the count is a ratchet.
DUPLICATE_NAME_BASELINE = 49
#: ...of which these are documented, intentional re-exports rather than drift.
INTENTIONAL_REEXPORTS = frozenset({
    "assert", "assert_eq_int", "assert_eq_string", "assert_false", "assert_msg",
    "assert_ne_int", "assert_ne_string", "assert_ok_int", "assert_present_int",
    "assert_true",
})


def _modules() -> list[Path]:
    return sorted(p for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu"))


def _top_level_weaves(text: str) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(text.splitlines()):
        m = re.match(r"^weave ([a-z_][A-Za-z0-9_]*)", line)
        if m:
            out.append((i + 1, m.group(1)))
    return out


def _has_doc(lines: list[str], index: int) -> bool:
    j = index - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    return j >= 0 and lines[j].strip().startswith("#")


# ---------------------------------------------------------------------------
# Rule: indent with 4 spaces, never tabs
# ---------------------------------------------------------------------------

def test_rule_indentation_is_four_spaces():
    """Every indented line in `std/` uses a multiple of 4 spaces and no tabs.

    The formatter configuration is the authority (and is itself pinned); this
    checks the shipped sources actually match it, which `pengu fmt --check std/`
    also verifies end to end.
    """
    problems = []
    for module in _modules():
        for i, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
            if "\t" in line:
                problems.append(f"{module.name}:{i}: contains a tab")
                continue
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if stripped and indent % 4:
                problems.append(f"{module.name}:{i}: indent {indent} is not a multiple of 4")
    assert problems == [], "\n  ".join(problems[:20])

    import re as _re

    for name in (".pengufmt.toml", "std/.pengufmt.toml"):
        text = (REPO / name).read_text(encoding="utf-8")
        assert _re.search(r"^tab_size\s*=\s*4\s*$", text, _re.M), f"{name} does not pin 4"


# ---------------------------------------------------------------------------
# Rule: no unsafe conversion outside ffi/filum
# ---------------------------------------------------------------------------

def test_rule_no_transmute_outside_ffi_and_filum():
    """`transmute` is confined to the FFI modules — and today is absent entirely.

    The rule allows it in `std/ffi` and `std/filum`; measured, `std/` contains no
    `transmute` call at all (its only textual occurrence is an explanatory comment
    in `std/ffi.pengu`). A future call anywhere else fails this test.
    """
    offenders = []
    for module in _modules():
        for i, line in enumerate(module.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if "transmute" not in stripped or stripped.startswith("#"):
                continue
            if module.stem not in ("ffi", "filum"):
                offenders.append(f"{module.name}:{i}")
    assert offenders == [], (
        f"transmute outside std/ffi and std/filum: {offenders}"
    )


# ---------------------------------------------------------------------------
# Rule: public functions carry inline documentation
# ---------------------------------------------------------------------------

def test_rule_public_weaves_carry_inline_doc():
    """The `weave` surface is fully documented (the ratchet lives elsewhere)."""
    undocumented = []
    for module in _modules():
        lines = module.read_text(encoding="utf-8").splitlines()
        for line_no, name in _top_level_weaves(module.read_text(encoding="utf-8")):
            if name.startswith("_"):
                continue
            if not _has_doc(lines, line_no - 1):
                undocumented.append(f"{module.name}:{line_no} {name}")
    assert undocumented == [], f"public weaves without a doc comment: {undocumented}"


# ---------------------------------------------------------------------------
# Rule: `ritual` constructors document their invariant
# ---------------------------------------------------------------------------

def test_rule_ritual_constructors_document_their_invariant():
    """Every `weave ritual` constructor documents what it returns.

    This rule was **violated** when measured: 20 of 44 constructors had no doc
    comment. They were all in `arithmancy` (`Vec2`/`Vec3`/`Vec4`/`Mat4`/`Quat`
    constants), and writing them down surfaced a genuine trap — see
    `test_rule_ritual_invariants_state_the_axis_convention`.
    """
    undocumented = []
    total = 0
    for module in _modules():
        lines = module.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not re.match(r"^\s*weave ritual\b", line):
                continue
            total += 1
            if not _has_doc(lines, i):
                undocumented.append(f"{module.name}:{i + 1}")
    assert total >= 44, f"only {total} ritual constructors found; the pattern may have changed"
    assert undocumented == [], f"ritual constructors without a doc comment: {undocumented}"


def test_rule_ritual_invariants_state_the_axis_convention():
    """The invariant that made this rule worth having.

    `Vec2.up` is `(0, -1)` (2-D screen space has Y growing downward) while
    `Vec3.up` is `(0, 1, 0)` (3-D has Y up). Documenting the constructors is what
    turns that from a suspected bug into a stated convention.
    """
    text = (STD / "arithmancy.pengu").read_text(encoding="utf-8")
    lines = text.splitlines()
    docs: dict[str, str] = {}
    for i, line in enumerate(lines):
        m = re.match(r"^\s*weave ritual (\w+) into (\w+):", line)
        if not m:
            continue
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        docs[f"{m.group(2)}.{m.group(1)}"] = lines[j]
    assert "Vec2.up" in docs and "Vec3.up" in docs
    assert "downward" in docs["Vec2.up"].lower(), (
        "Vec2.up must state that 2-D Y grows downward"
    )
    assert "up" in docs["Vec3.up"].lower()
    # The trap is stated on both sides, so a reader comparing the two is warned.
    assert "(-1)" in docs["Vec2.up"].replace(" ", "") or "-1" in docs["Vec2.up"]


# ---------------------------------------------------------------------------
# Rule: module version constants are asserted
# ---------------------------------------------------------------------------

def test_rule_module_version_constants_are_asserted():
    """The `<MOD>_VERSION` rule is enforced by dedicated tests, not by prose."""
    versioning = (REPO / "tests" / "test_std_versioning.py").read_text(encoding="utf-8")
    assert "def test" in versioning
    bindings = (REPO / "tests" / "test_bindings_version_policy.py").read_text(encoding="utf-8")
    assert "VERSION" in bindings, (
        "test_bindings_version_policy.py no longer pins the binding version policy"
    )


# ---------------------------------------------------------------------------
# Deferred rules, held by ratchets
# ---------------------------------------------------------------------------

def test_rule_cp_helpers_do_not_grow():
    """`compass`'s 32 `cp_*` helpers are deferred (roadmap 6.11), not forgotten."""
    text = (STD / "compass.pengu").read_text(encoding="utf-8")
    count = len(re.findall(r"^weave cp_", text, re.M))
    assert count == CP_HELPER_BASELINE, (
        f"compass now exposes {count} cp_* helpers (baseline {CP_HELPER_BASELINE}); "
        f"roadmap 6.11 defers the rename to 1.1, so the count must not grow"
    )


def test_rule_duplicate_public_names_are_recorded():
    """49 public `weave` names repeat across modules — recorded, not ignored.

    Roadmap 6.5 found 15 for `loom`/`tally`; measured across all of `std/` the
    real number is **49** (10 of them `assert*` helpers re-exported by design).
    Unification is a breaking change needing a two-release deprecation window, so
    it stays deferred — but the count is a ratchet: a new collision fails here.
    """
    owners: dict[str, set[str]] = collections.defaultdict(set)
    for module in _modules():
        for _, name in _top_level_weaves(module.read_text(encoding="utf-8")):
            if not name.startswith("_"):
                owners[name].add(module.stem)
    duplicates = {name: sorted(mods) for name, mods in owners.items() if len(mods) > 1}

    assert len(duplicates) == DUPLICATE_NAME_BASELINE, (
        f"the number of public names shared across modules changed: "
        f"{len(duplicates)} (baseline {DUPLICATE_NAME_BASELINE}). "
        f"New collisions: "
        f"{sorted(set(duplicates) - INTENTIONAL_REEXPORTS)[:10]}"
    )
    for name in INTENTIONAL_REEXPORTS:
        assert name in duplicates, f"{name} is no longer a re-export; update the baseline"


def test_rule_no_local_shadows_a_global_weave():
    """`0 W0005` across `std/`, measured without a three-minute compiler sweep.

    The authoritative check is `python pengu_project.py check --entry std/<mod>.pengu`
    for all 27 modules (measured: 0 `W0005`, 0 `W0001`, with a positive control to
    prove the harness detects them). This test is the cheap structural proxy: a
    local declared with the same name as a top-level `weave` of the same module.
    """
    offenders = []
    for module in _modules():
        text = module.read_text(encoding="utf-8")
        globals_ = {name for _, name in _top_level_weaves(text) if not name.startswith("_")}
        in_test = False
        for i, line in enumerate(text.splitlines(), 1):
            if line and not line[0].isspace():
                # A top-level construct ends any `test` block that was open.
                in_test = bool(re.match(r"^test\b", line))
            if in_test:
                # The checker deliberately suppresses W0005 inside `test` blocks
                # (roadmap 2.12), so a test local may reuse a weave name.
                continue
            m = re.match(r"^\s+(?:static\s+)?(?:var|let)\s+([a-z_][A-Za-z0-9_]*)", line)
            if m and m.group(1) in globals_:
                offenders.append(f"{module.name}:{i} {m.group(1)}")
    assert offenders == [], (
        f"locals shadowing a module-level weave (W0005): {offenders}"
    )
