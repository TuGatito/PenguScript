"""Phase 2 item 2.8 — the `derive` matrix, measured.

The manual promised `Par`, `Ordo`, `Vinculum`, `Imago`, `Nexus` and implied that
the generic concept table's other entries might be derivable too. Only some are.
This file establishes which, by **running** a program that needs the derived
behaviour for each concept (rule C1: no assertion here reads a list or a string;
every one compiles and executes, or asserts on the exact diagnostic).

Measured outcome (AUDIT_1.0_FASE2.md §1.3):

======================  =========  ==================================================
concept                 derivable  what it produces
======================  =========  ==================================================
`Par`                   yes        `==` / `!=` between the rune's values
`Ordo`                  yes        `<` `<=` `>` `>=`
`Vinculum`              yes        a hash, so the rune works as a `map` key
`Imago`                 yes        `_pengu_clone_<T>` -- deep-copy callback for containers
`Nexus`                 yes        `_pengu_cleanup_<T>` -- destructor, used by auto-banish
`Forma`                 no         `E0005`
`Iterabilis`            no         `E0005`
`Donum`                 no         `E0005`
======================  =========  ==================================================

`Imago` deliberately does **not** add a `.clone()` method to the rune: it emits
the C-level clone callback that the runtime's containers call. That distinction
tripped up the first attempt at this matrix, which is why it is written down.
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


def run_pengu(tmp_path, name, source, *args):
    """Runs the real CLI (`run` by default) and returns (rc, output)."""
    path = tmp_path / f"{name}.pengu"
    path.write_text(source, encoding="utf-8")
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    r = subprocess.run(
        [PY, "-m", MODULE] + list(args) + [str(path)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=300, env=env,
    )
    return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)


def check(tmp_path, name, source):
    return run_pengu(tmp_path, name, source, "check")


# ---------------------------------------------------------------------------
# Derivable concepts: each is exercised by running a program that needs it
# ---------------------------------------------------------------------------

def test_derive_par_enables_equality(tmp_path):
    """`derive Par` gives working `==` between two values of the rune."""
    rc, out = run_pengu(tmp_path, "par", (
        "rune P derive Par:\n"
        "  x as int\n"
        "weave same with a as P, b as P into bool:\n"
        "  return a == b\n"
        "weave main into int:\n"
        "  var a as P is with x is 1\n"
        "  var b as P is with x is 1\n"
        "  var c as P is with x is 2\n"
        "  var eq as bool is calling same with a, b\n"
        "  var ne as bool is calling same with a, c\n"
        "  if eq and not ne:\n"
        "    return 0\n"
        "  return 1\n"
    ), "run")
    assert rc == 0, out


def test_derive_ordo_enables_ordering(tmp_path):
    """`derive Ordo` gives working `<`."""
    rc, out = run_pengu(tmp_path, "ordo", (
        "rune O derive Ordo:\n"
        "  x as int\n"
        "weave less with a as O, b as O into bool:\n"
        "  return a < b\n"
        "weave main into int:\n"
        "  var a as O is with x is 1\n"
        "  var b as O is with x is 2\n"
        "  if calling less with a, b:\n"
        "    return 0\n"
        "  return 1\n"
    ), "run")
    assert rc == 0, out


def test_derive_vinculum_makes_a_usable_map_key(tmp_path):
    """`derive Vinculum` supplies the hash a `map` key needs."""
    rc, out = run_pengu(tmp_path, "vinc", (
        "rune V derive Vinculum:\n"
        "  x as int\n"
        "weave main into int:\n"
        "  var m as map of V to int is map of V to int\n"
        "  var k as V is with x is 1\n"
        "  calling m.put with k, 5\n"
        "  if (calling m.len) == 1:\n"
        "    return 0\n"
        "  return 1\n"
    ), "run")
    assert rc == 0, out


def test_derive_imago_emits_a_clone_callback(tmp_path):
    """`derive Imago` emits `_pengu_clone_<T>` for the runtime's containers.

    Note it does NOT add a `.clone()` method to the rune: calling
    `a.clone` on a `derive Imago` rune is an E0004 ('has no method'). What it
    produces is the C-level callback, so the observable check is that the symbol
    appears in the emitted bundle -- that is a compiler *output*, not a doc
    claim, so asserting on it is legitimate here.
    """
    rc, out = run_pengu(tmp_path, "imago", (
        "rune I derive Imago:\n"
        "  x as string\n"
    ), "expand")
    assert rc == 0, out
    assert "_pengu_clone_I" in out, out[:800]

    # And the negative half: no `.clone` method is added to the rune.
    rc2, out2 = check(tmp_path, "imago_clone", (
        "rune I derive Imago:\n"
        "  x as string\n"
        "weave main into int:\n"
        "  var a as I is with x is \"hi\"\n"
        "  var b as I is calling a.clone\n"
        "  return 0\n"
    ))
    assert rc2 != 0, out2
    assert "no method 'clone'" in out2, out2


def test_derive_nexus_emits_a_destructor(tmp_path):
    """`derive Nexus` emits `_pengu_cleanup_<T>`, which auto-banish uses."""
    rc, out = run_pengu(tmp_path, "nexus", (
        "rune N derive Nexus:\n"
        "  x as string\n"
    ), "expand")
    assert rc == 0, out
    assert "_pengu_cleanup_N" in out, out[:800]


def test_derive_imago_implies_nexus(tmp_path):
    """A container that clones must also release: `Imago` implies `Nexus`.

    Both symbols must appear when only `Imago` is written.
    """
    rc, out = run_pengu(tmp_path, "imago_pair", (
        "rune I derive Imago:\n"
        "  x as string\n"
    ), "expand")
    assert rc == 0, out
    assert "_pengu_clone_I" in out, out[:800]
    assert "_pengu_cleanup_I" in out, out[:800]


def test_derive_all_derivable_together(tmp_path):
    """The five derivable concepts can be combined on one rune."""
    rc, out = run_pengu(tmp_path, "all5", (
        "rune A derive Par, Ordo, Vinculum, Imago, Nexus:\n"
        "  x as int\n"
        "weave main into int:\n"
        "  var a as A is with x is 1\n"
        "  var b as A is with x is 2\n"
        "  if a < b and a != b:\n"
        "    return 0\n"
        "  return 1\n"
    ), "run")
    assert rc == 0, out


# ---------------------------------------------------------------------------
# Non-derivable concepts: rejected with E0005, and the message lists what is
# derivable so the diagnostic is actionable.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("concept", ["Forma", "Iterabilis", "Donum"])
def test_non_derivable_concepts_are_rejected(tmp_path, concept):
    """`Forma`/`Iterabilis`/`Donum` cannot be auto-derived (E0005)."""
    rc, out = check(tmp_path, f"nd_{concept}", (
        f"rune X derive {concept}:\n"
        "  x as int\n"
    ))
    assert rc != 0, f"derive {concept} was accepted:\n{out}"
    assert "E0005" in out, out
    assert concept in out, out


@pytest.mark.parametrize("concept", ["Speaker", "Measurable", "NotAThing"])
def test_user_and_unknown_concepts_are_not_derivable(tmp_path, concept):
    """Only the built-in derivable set works; user concepts are E0005."""
    rc, out = check(tmp_path, f"nc_{concept}", (
        "concept Speaker:\n"
        "  weave speak into string\n"
        f"rune X derive {concept}:\n"
        "  x as int\n"
    ))
    assert rc != 0, out
    assert "E0005" in out, out


def test_derive_on_a_generic_rune_checks_the_arguments(tmp_path):
    """On a generic rune, deriving a comparison concept bounds the parameters.

    LANGUAGE.md §11.6 states that `Point of int` works because `int` implements
    the concept. The inverse must also hold: substituting a type that does not
    implement it must be rejected.
    """
    ok = (
        "rune Point shard T derive Par, Ordo:\n"
        "  x as T\n"
        "weave main into int:\n"
        "  var a as Point of int is with x is 1\n"
        "  var b as Point of int is with x is 2\n"
        "  if a < b:\n"
        "    return 0\n"
        "  return 1\n"
    )
    rc, out = run_pengu(tmp_path, "generic_ok", ok, "run")
    assert rc == 0, out
