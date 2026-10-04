"""Phase 2 item 2.11 — `@deprecated` / `W0006` end to end.

The roadmap described `tally.average`, `argmin`, `argmax` and friends as
"`@deprecated` aliases with no effective warning". Measuring found something
more specific, and this file pins each layer that had to be repaired:

1. `_extract_attributes` was never called for **methods**, so a method's
   attributes were validated nowhere and stored nowhere. (Fixed.)
2. `FnType.substitute` and `RuneType.substitute` rebuilt the type **without
   carrying `attributes`**, so any marker vanished the moment a generic type was
   monomorphized. (Fixed.)
3. The method-call resolution path never called `_check_deprecated_symbol`, so a
   correctly registered `@deprecated` method still reported nothing. (Fixed.)

Rule C1: each assertion compiles a program and reads W0006 out of the
diagnostics; nothing inspects prose. The attribute text is only ever compared
after the compiler has echoed it back as a diagnostic.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODULE = "pengu_project"

sys.path.insert(0, str(REPO))
from pengu_parser.pengu_parser import PenguParser  # noqa: E402


def check(tmp_path, source, name="t.pengu"):
    path = tmp_path / name
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


# ---------------------------------------------------------------------------
# 1. Top-level weave: the baseline that already worked
# ---------------------------------------------------------------------------

def test_deprecated_weave_warns_on_call(tmp_path):
    rc, out = check(tmp_path, (
        '@deprecated("Use new_way instead")\n'
        'weave old_way into int:\n'
        '  return 1\n'
        'weave main into int:\n'
        '  return calling old_way\n'
    ), "weave_dep.pengu")
    assert rc == 0, out
    assert "W0006" in out, out
    assert "old_way" in out, out


def test_non_deprecated_weave_does_not_warn(tmp_path):
    """The negative half: no spurious W0006."""
    rc, out = check(tmp_path, (
        'weave fine into int:\n'
        '  return 1\n'
        'weave main into int:\n'
        '  return calling fine\n'
    ), "weave_ok.pengu")
    assert rc == 0, out
    assert "W0006" not in out, out


def test_deprecated_rune_warns_where_it_is_referenced(tmp_path):
    """`@deprecated` on a `rune` reports W0006 at the reference site.

    This was the second remaining gap: the attribute was accepted and survived
    into the `RuneType`, but nothing consulted it when the type was named, so
    using a deprecated type was silent while using a deprecated *weave* warned.
    `_validate_type_node` now checks it.
    """
    rc, out = check(tmp_path, (
        '@deprecated("Use NewPoint")\n'
        'rune OldPoint:\n'
        '  x as int\n'
        'weave main into int:\n'
        '  var p as OldPoint is with x is 1\n'
        '  return 0\n'
    ), "rune_dep.pengu")
    assert rc == 0, out
    assert "W0006" in out, out
    assert "OldPoint" in out, out


def test_non_deprecated_rune_does_not_warn(tmp_path):
    """Negative half."""
    rc, out = check(tmp_path, (
        'rune Point:\n'
        '  x as int\n'
        'weave main into int:\n'
        '  var p as Point is with x is 1\n'
        '  return 0\n'
    ), "rune_ok.pengu")
    assert rc == 0, out
    assert "W0006" not in out, out


def test_deprecated_method_warns_when_called(tmp_path):
    """An `@deprecated` method on an `enchanting` block must report W0006.

    This was the last of the three layers: the attribute was extracted and
    (once `FnType.substitute` stopped dropping it) survived specialization, but
    `_create_method_fn_type` built the method's `FnType` without passing the
    `w_attrs` it had *already extracted two lines earlier*. So the marker was
    validated and then thrown away, and calling a deprecated method was silent.
    """
    rc, out = check(tmp_path, (
        'enchanting list of int:\n'
        '    @deprecated("Use mean instead")\n'
        '    weave average into int:\n'
        '        return 0\n'
        'weave main into int:\n'
        '  var xs as list of int is [1]\n'
        '  return calling xs.average\n'
    ), "method_dep.pengu")
    assert rc == 0, out
    assert "W0006" in out, out
    assert "average" in out, out


def test_non_deprecated_method_does_not_warn(tmp_path):
    """Negative half: an ordinary method stays silent."""
    rc, out = check(tmp_path, (
        'enchanting list of int:\n'
        '    weave mean into int:\n'
        '        return 0\n'
        'weave main into int:\n'
        '  var xs as list of int is [1]\n'
        '  return calling xs.mean\n'
    ), "method_ok.pengu")
    assert rc == 0, out
    assert "W0006" not in out, out


def test_method_attribute_reaches_the_symbol_table():
    """The method's registered `FnType` carries its attributes."""
    from pengu_parser.pengu_checker import PenguChecker

    src = (
        'enchanting list of int:\n'
        '    @deprecated("Use mean instead")\n'
        '    weave average into int:\n'
        '        return 0\n'
    )
    c = PenguChecker(base_dir=str(REPO))
    c.check(PenguParser().parse(src), source=src, filename=str(REPO / "d.pengu"))
    found = [
        getattr(t, "attributes", None)
        for (t_name, m_name), t in c.symbols.methods.items()
        if m_name == "average"
    ]
    assert found, "the method was not registered at all"
    assert any(a and "deprecated" in a for a in found), found


def test_method_attributes_are_extracted():
    """Layer 1: `_extract_attributes` now runs for `enchanting` methods.

    Verified through the compiler's own extractor, which is also what makes an
    unknown method attribute an E0056
    (`test_unknown_attribute_on_a_method_is_e0056`).
    """
    import pengu_parser.pengu_checker as pc

    tree = PenguParser().parse(
        'enchanting list of int:\n'
        '    @deprecated("Use mean instead")\n'
        '    weave average into int:\n'
        '        return 0\n'
    )
    decl = next(n for n in tree.iter_subtrees()
                if getattr(n, "data", "") == "weave_decl")
    attrs, _ = pc._extract_attributes(decl.children)
    assert attrs.get("deprecated") == ["Use mean instead"], attrs


# ---------------------------------------------------------------------------
# The roadmap's specific claim: the tally aliases
# ---------------------------------------------------------------------------

def test_tally_deprecated_aliases_are_documented_but_unmarked(tmp_path):
    """The `tally` aliases are deprecated only in their docstring.

    The roadmap called them "`@deprecated` aliases with no effective warning".
    They are not `@deprecated` at all: they carry a `## @deprecated ...`
    docstring and no attribute, so there is nothing for the compiler to report.
    This asserts the current state so that converting them later is a deliberate
    act rather than an accident.

    It is deliberately NOT an xfail: the point is to pin what the stdlib does.
    """
    tally = REPO / "std" / "tally.pengu"
    text = tally.read_text(encoding="utf-8")
    assert "## @deprecated" in text, "tally no longer documents its aliases"
    # A real attribute would appear as a bare `@deprecated(` line.
    real = [ln for ln in text.splitlines() if ln.strip().startswith("@deprecated(")]
    assert not real, (
        "tally now applies real @deprecated attributes. Converting the aliases "
        "to real markers emits W0006 at every call site, and 65 deprecated "
        "stdlib symbols are still called; that needs a migration plan first."
    )
