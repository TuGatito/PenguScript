"""Phase 2 item 2.10 — the documented primitive-type table must match the codegen.

`LANGUAGE.md` §4.1 lists 42 accepted primitive spellings grouped by the canonical
C type each one emits. That mapping lives in `CTypeMapper.to_c_type`, so the docs
and the code can drift. This test closes that gap.

Rule C1 (ROADMAP_2.0 Anexo C): the ground truth is not a hand-copied list. The
test **reads the real mapping out of the codegen source with `ast`** and compares
the documented grouping against it. It then compiles one program per spelling and
asserts that the emitted C really contains the documented canonical type -- so a
doc that lies about the mapping fails even if the ast extraction were wrong.

This is the item that caught `isize`: the old table called it
"`ssize_t`-ish", while it actually emits `intptr_t`.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"
# `CTypeMapper` lives in the `pengu_codegen` package, in the module that owns
# the C type mapping.
CODEGEN = REPO / "pengu_parser" / "pengu_codegen" / "ctype.py"

_BLOCK_RE = re.compile(r"```text prim-c-map\n(?P<body>.*?)```", re.DOTALL)


#: Both language references carry the block; they must agree with the codegen
#: AND with each other (Phase 2 bilingualism rule).
DOCS = ["LANGUAGE.md", "LANGUAGE_Spanish.md"]


def _documented_mapping(doc: str = "LANGUAGE.md") -> dict:
    """{canonical C type: [spelling, ...]} from `doc`'s `prim-c-map` block."""
    text = (REPO / doc).read_text(encoding="utf-8")
    match = _BLOCK_RE.search(text)
    assert match, (
        f"{doc} has no ```text prim-c-map block; item 2.10 requires the "
        "primitive table to be machine-readable in both language references"
    )
    documented = {}
    for line in match.group("body").strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        ctype, _, spellings = line.partition(":")
        documented[ctype.strip()] = [s.strip() for s in spellings.split(",") if s.strip()]
    return documented


def _arms_from_codegen() -> dict:
    """{spelling: canonical C type} read straight out of `to_c_type`.

    Extracted per *arm* rather than collapsed per C type: the code generator is a
    chain of ``if name in (...)`` tests, and how it groups spellings across arms
    is an implementation detail. What must match the docs is the resulting
    spelling -> C type mapping.
    """
    source = CODEGEN.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "to_c_type":
            arms = {}
            for sub in ast.walk(node):
                if not isinstance(sub, ast.If):
                    continue
                test = sub.test
                if not (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
                        and test.left.id == "name"):
                    continue
                names = set()
                for comp in test.comparators:
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                        names.add(comp.value)
                    elif isinstance(comp, (ast.Tuple, ast.Set, ast.List)):
                        for elt in comp.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.add(elt.value)
                if not names:
                    continue
                ret = sub.body[0] if sub.body else None
                ctype = None
                if isinstance(ret, ast.Return) and isinstance(ret.value, ast.JoinedStr):
                    for part in ret.value.values:
                        if isinstance(part, ast.Constant) and isinstance(part.value, str):
                            frag = part.value.strip()
                            if frag and frag != "{prefix}":
                                ctype = frag
                if ctype:
                    for n in names:
                        arms[n] = ctype
            return arms
    pytest.fail("CTypeMapper.to_c_type not found in pengu_codegen.py")


def check(tmp_path, name, source):
    """Runs `pengu check` on `source`; returns (rc, output)."""
    path = tmp_path / f"{name}.pengu"
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, "check", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)


def _emitted_c_type(tmp_path, spelling):
    """Compiles `weave f with a as <spelling> into void` and returns the C type."""
    path = tmp_path / "p.pengu"
    path.write_text(
        f"weave f with a as {spelling} into void:\n  return\n", encoding="utf-8"
    )
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE, "expand", str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    assert r.returncode == 0, out
    m = re.search(r"void f\(([^)]*)\)", out)
    assert m, f"no C signature emitted for {spelling!r}:\n{out[:600]}"
    params = m.group(1).replace("const ", "").strip()
    if params in ("", "void"):
        return "void"
    # `void f(int32_t a)` -> "int32_t"; drop the parameter name.
    return params.split()[0]


# ---------------------------------------------------------------------------
# Documented = emitted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("doc", DOCS)
def test_documented_primitive_map_is_complete(tmp_path, doc):
    """Every spelling the codegen knows about appears in the documented table."""
    documented = _documented_mapping(doc)
    doc_map = {s: c for c, spells in documented.items() for s in spells}
    arms = _arms_from_codegen()
    # `void`, `bool`, `char`, `string` and `opaque` are single-spelling
    # primitives covered by the table's prose rows; the machine block covers the
    # many-spelling numeric family, which is the part that is easy to get wrong.
    PROSE_ONLY = {"void", "bool", "char", "PenguString", "void*", "const char*"}
    for spelling, ctype in sorted(arms.items()):
        if ctype in PROSE_ONLY:
            continue
        assert spelling in doc_map, (
            f"codegen maps {spelling!r} to {ctype}, but LANGUAGE.md's prim-c-map "
            "block does not mention it"
        )
        assert doc_map[spelling] == ctype, (
            f"{spelling!r} is documented as {doc_map[spelling]!r} but the "
            f"codegen maps it to {ctype!r}"
        )


@pytest.mark.parametrize("doc", DOCS)
def test_documented_map_has_no_entries_the_codegen_lacks(tmp_path, doc):
    """The docs must not invent a spelling the codegen does not handle."""
    documented = _documented_mapping(doc)
    arms = _arms_from_codegen()
    for spelling in (s for spells in documented.values() for s in spells):
        assert spelling in arms, (
            f"LANGUAGE.md documents {spelling!r} but CTypeMapper.to_c_type has "
            "no arm for it"
        )


@pytest.mark.parametrize("doc", DOCS)
def test_both_language_references_document_the_same_mapping(doc):
    """The English and Spanish tables must list the same ctype -> spellings map.

    This is the check that was missing when the Spanish §4.1 table was rewritten
    separately and silently lost the machine-readable block.
    """
    assert _documented_mapping(doc) == _documented_mapping("LANGUAGE.md"), (
        f"{doc} documents a different primitive mapping than LANGUAGE.md"
    )


@pytest.mark.parametrize("spelling", [
    "int", "i32", "int32", "int32_t",
    "i64", "int64", "int64_t", "long",
    "short", "i16", "byte", "u8", "uint8_t",
    "u32", "uint", "u64", "ulong",
    "usize", "size_t", "isize", "ssize_t",
    "f32", "f64", "double", "float", "char", "bool", "string", "void", "opaque",
])
def test_documented_spelling_emits_the_documented_ctype(tmp_path, spelling):
    """Each spelling is compiled and its emitted C type compared to the docs.

    This is the half that makes the table trustworthy: it does not trust the
    extraction above, it asks the compiler.
    """
    documented = _documented_mapping()
    expected = next((c for c, spells in documented.items() if spelling in spells), None)
    if expected is None:
        pytest.skip(f"{spelling} is documented in prose, not in the machine block")
    emitted = _emitted_c_type(tmp_path, spelling)
    assert emitted == expected, (
        f"{spelling!r} is documented as emitting {expected!r} but the compiler "
        f"emitted {emitted!r}"
    )


def test_isize_is_intptr_not_ssize_t(tmp_path):
    """The specific error the old table had.

    `LANGUAGE.md` §4.1 said `usize`/`isize` were "`size_t`/`ssize_t`-ish". `isize`
    actually emits `intptr_t`, so a reader relying on the table would get the
    wrong C type at a boundary.
    """
    assert _emitted_c_type(tmp_path, "isize") == "intptr_t"
    assert _emitted_c_type(tmp_path, "usize") == "size_t"


def test_float_is_32_bit_not_double(tmp_path):
    """The second error the old table had.

    §4.1 claimed `float`/`f64`/`double` were all 64-bit and mapped to `double`.
    `float` and `f32` actually emit C `float` (32-bit); `f64`/`double` emit
    `double`. A reader believing the old row would write `float` expecting double
    precision and silently get single.
    """
    assert _emitted_c_type(tmp_path, "float") == "float"
    assert _emitted_c_type(tmp_path, "f32") == "float"
    assert _emitted_c_type(tmp_path, "f64") == "double"
    assert _emitted_c_type(tmp_path, "double") == "double"


def test_ssize_t_is_not_a_pengu_type(tmp_path):
    """`ssize_t` must not be usable, and the codegen must not pretend otherwise.

    `to_c_type` had an arm for `ssize_t` that the grammar could never reach
    (item 2.10 removed it). This test pins both halves: the name is still a
    type-parameter error, and `isize` is the supported spelling.
    """
    rc, out = check(tmp_path, "ssize", "weave f with a as ssize_t into void:\n  return\n")
    assert rc != 0, (
        "`ssize_t` now parses; add it to LANGUAGE.md's prim-c-map block (it maps "
        "to intptr_t, same as isize) and update this test.\n" + out
    )
    # And `isize`, the supported spelling, does work.
    assert _emitted_c_type(tmp_path, "isize") == "intptr_t"


def test_int_family_is_abi_identical(tmp_path):
    """Every spelling in one row must emit the SAME C type.

    That is what makes the rows meaningful: they are interchangeable, not merely
    similar.
    """
    for ctype, spellings in _documented_mapping().items():
        emitted = {s: _emitted_c_type(tmp_path, s) for s in spellings}
        distinct = set(emitted.values())
        assert distinct == {ctype}, (
            f"documented row {ctype!r} contains spellings emitting {emitted}"
        )
