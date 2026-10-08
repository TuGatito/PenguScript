"""Crash-resistance sweep: the front end must never leak an interpreter error.

Rule C1 (ROADMAP_2.0 Anexo C): this test measures **behaviour** -- it runs the
real compiler over real inputs and asserts that no input produces an interpreter
error. It does not assert on message prose, and it does not require the inputs to
be *valid*: a fragment may legitimately be rejected with E0000.

Why this file exists
--------------------
Blocker B6 was a `NameError` raised from inside a diagnostic
(`pengu_parser/pengu_infer.py:4055` referenced an undefined `node`), so a user
who accessed a private symbol of another module got an interpreter error instead
of `E0043`. `pyflakes` can only find that class of bug when the name is
*statically* undefined; the compiler can also fail at runtime through
`AttributeError`, `KeyError`, `IndexError`, `TypeError` or `RecursionError` on
inputs nobody tried. This sweep covers the whole documented language surface at
once, which is how it would have caught B6.

How the crash is detected (and why the first version could not detect it)
-----------------------------------------------------------------------
This sweep used to run `python -m pengu_project check <file>` per block and grep
the output for ``Traceback (most recent call last)``. **That could never fire.**
The front end catches the exception at two levels -- `check_sources_diagnostics`
has ``except Exception`` and `check_files` has another -- and renders it through
`_diagnostic_message`, which uses ``str(exc)``, never a traceback. Measured with a
`RuntimeError` injected into `TypeInferrer.infer`, the CLI prints

    /tmp/blk.pengu:0:0 SIMULATED-CRASH

with no traceback anywhere. The marker was therefore never present, and the sweep
stayed green no matter what the front end did. A crash-resistance test that cannot
fail is worse than no test: it advertises coverage nobody has.

What distinguishes a swallowed interpreter error from a real diagnostic is
**structure, not prose**: an interpreter error reaches `_diagnostic_message` with
no `code` attribute, so it is emitted with an empty code and position 0:0. Every
legitimate diagnostic carries one (`[E0005]`, `[W0001]`, ...). The sweep asserts
exactly that, which is both accurate and cheap -- no subprocess, so no ~0.36 s of
interpreter start-up and compiler import per block, which across ~290 blocks was
the largest single item in the suite.

The signature was calibrated before being asserted: running all 286 documented
blocks produced 0 uncoded diagnostics out of 327 (E0002 x144, E0004 x78, E0000
x61, and ten more codes), so the assertion does not merely restate "the compiler
is unhappy".

The inputs are the `pengu`-fenced blocks of the swept documents, parsed with a
line-based fence scanner rather than a single regex: `LANGUAGE.md` contains at
least one *indented* fence (````  ```pengu ````) that a naive regex misses, which
would silently drop blocks from the sweep.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
MODULE = "pengu_project"

#: Documents whose ```pengu blocks are swept. Declared once so the parametrisation
#: and the "has blocks" guard cannot disagree.
_SWEPT_DOCUMENTS = ("LANGUAGE.md", "LANGUAGE_Spanish.md", "CHEATSHEET.md")

#: Every diagnostic the CLI prints carries a code (`[E0005]`). An *uncoded* message
#: is what a swallowed internal exception looks like on the way out -- see the
#: module docstring -- so the CLI sample below asserts on this.
_DIAGNOSTIC_CODE_RE = re.compile(r"\[[EW]\d{4}\]")


def _blocks(path: Path):
    """Returns a list of (index, body) for every ```pengu block in `path`."""
    out, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\s*)```([A-Za-z_-]*)\s*$", line)
        if current is None:
            if m and m.group(2).lower().startswith("pengu"):
                current = []
        elif m:
            out.append((len(out), "\n".join(current)))
            current = None
        else:
            current.append(line)
    if current is not None:
        out.append((len(out), "\n".join(current)))
    return out


def _check_in_process(path: Path) -> None:
    """Front-end-checks `path` in this process; fails on an interpreter error.

    Same construction `pengu check <file>` uses -- a `PenguBuilder` rooted at the
    file's directory, then `check_sources_diagnostics` -- but the returned
    diagnostics are inspected instead of the CLI's prose output, because that is
    where a swallowed interpreter error is distinguishable: it comes out with an
    empty `code` and position 0:0, while every language diagnostic carries a code.
    See the module docstring for the calibration.
    """
    from dataclasses import replace

    from pengu_project import PenguBuilder, ProjectConfig

    absolute = path.resolve()
    config = replace(
        ProjectConfig.load(None),
        base_dir=str(absolute.parent),
        entry=absolute.name,
        name=path.stem,
    )
    builder = PenguBuilder(config)
    builder.verbose = False
    _ok, diagnostics = builder.check_sources_diagnostics()
    uncoded = [d for d in diagnostics if not str(d.get("code") or "").strip()]
    assert not uncoded, (
        "the front end reported a diagnostic with no code, which is how an "
        "interpreter error escapes (see the module docstring):\n"
        + "\n".join(f"  {d.get('file')}:{d.get('line')}: {d.get('message')}"
                    for d in uncoded[:5])
    )


def _run_check(tmp_path, name, source):
    """Runs `source` through the real CLI and returns (rc, combined output)."""
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
    return r.returncode, r.stdout + r.stderr


def _documented_blocks() -> list:
    """Every documented block of every swept document, as pytest parameters.

    One test per block. As one test per *document* this sweep took ~157 s across
    three tests that no amount of ``pytest-xdist`` could divide, so the suite could
    never finish faster than the slowest of them. The blocks are independent
    compilations, which makes them the easiest possible work to spread.
    """
    return [
        pytest.param(doc, index, body, id=f"{doc}-{index}")
        for doc in _SWEPT_DOCUMENTS
        for index, body in _blocks(REPO / doc)
    ]


_DOCUMENTED_BLOCKS = _documented_blocks()


@pytest.mark.parametrize("doc", _SWEPT_DOCUMENTS)
def test_the_document_has_blocks_to_sweep(doc):
    """A scanner that stopped finding blocks would make the sweep a green no-op."""
    assert _blocks(REPO / doc), f"{doc} has no ```pengu blocks; the scanner is broken"


def test_the_sweep_covers_every_block() -> None:
    """The parametrisation must see every block, or the sweep shrinks silently."""
    total = sum(len(_blocks(REPO / doc)) for doc in _SWEPT_DOCUMENTS)
    assert len(_DOCUMENTED_BLOCKS) == total
    assert total > 150, f"the fence scanner found only {total} documented blocks"


@pytest.mark.parametrize("doc,index,body", _DOCUMENTED_BLOCKS)
def test_no_interpreter_error_on_documented_blocks(doc, index, body, tmp_path):
    """Every documented block must be *handled*, valid or not.

    A fragment that does not parse is fine and expected -- it must produce a
    diagnostic, not an interpreter error. This is the generalised guard for B6: a
    missing return, an unknown call target, a private symbol, a malformed type and
    a bad container literal all funnel through the same front end.
    """
    path = tmp_path / f"{doc.replace('.', '_')}_{index}.pengu"
    path.write_text(body, encoding="utf-8")
    # No try/except: an interpreter error here is the failure this test exists for,
    # and letting it propagate preserves the traceback in the report.
    _check_in_process(path)


@pytest.mark.parametrize("doc", _SWEPT_DOCUMENTS)
def test_the_cli_reports_coded_diagnostics(doc, tmp_path):
    """One block per document through the *real CLI*.

    The mass sweep above no longer spawns a subprocess (it cannot detect the crash
    through one -- see the module docstring). The CLI wrapper is still worth
    covering, because it is where a swallowed exception becomes *user-visible
    output*: `check_files` converts it into a diagnostic with no code and position
    0:0, so a user sees a bare message. Asserting that a rejection always carries a
    code is what catches that, and it is asserted on the wrapper's own output.
    """
    first = _blocks(REPO / doc)[0][1]
    rc, out = _run_check(tmp_path, f"{doc.replace('.', '_')}_cli.pengu", first)
    if rc != 0:
        assert _DIAGNOSTIC_CODE_RE.search(out), (
            f"the CLI rejected {doc}'s first block without a diagnostic code, "
            f"which is how an internal compiler error reaches a user:\n{out[:1500]}"
        )


#: The forms that reach `_resolve_call_target` and the field-access path with a
#: module-qualified target -- the code where B6's undefined `node` lived. B6's
#: exact shape plus its neighbours, all cross-module.
_CROSS_MODULE_FORMS = [
    "return calling lib._priv\n",
    "return calling lib.pub with 1\n",
    "return calling lib.missing\n",
    "var v as lib._Hidden is with z is 1\n  return v.z\n",
    "var v as lib.Shown is with x is 1.0, y is 2.0\n  return (v.x to int)\n",
    "var v as lib.Shown is with nope is 1\n  return 0\n",
    "return lib._K\n",
    "return lib.K\n",
    "return lib._missing\n",
    "calling lib._priv\n  return 0\n",
]


def _write_cross_module_fixture(tmp_path: Path) -> None:
    (tmp_path / "lib.pengu").write_text(
        "weave _priv into int:\n  return 1\n"
        "weave pub with a as int into int:\n  return a\n"
        "rune _Hidden:\n  z as int\n"
        "rune Shown:\n  x as f32\n  y as f32\n"
        "const _K as int is 1\n"
        "const K as int is 2\n",
        encoding="utf-8",
    )
    (tmp_path / "dep.pengu").write_text(
        "import lib\n"
        "declare addp with a as lib.Shown, b as lib.Shown into lib.Shown\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize("prefix", ["import lib\n", "import lib\nimport dep\n"],
                         ids=["lib", "lib+dep"])
@pytest.mark.parametrize("index,form", list(enumerate(_CROSS_MODULE_FORMS)),
                         ids=[f"form{i}" for i in range(len(_CROSS_MODULE_FORMS))])
def test_cross_module_access_forms_never_crash(index, form, prefix, tmp_path):
    """B6's exact shape plus its neighbours, all cross-module.

    Parametrised per (form, prefix) rather than looping: the loop made 20
    independent compilations share one test, so a single worker paid for all of
    them and the first failure hid the other nineteen.
    """
    _write_cross_module_fixture(tmp_path)
    # Named from the parametrisation index, never from hash(): the filename must be
    # identical across runs (rule 8), and a stale hash would also rename the file
    # between runs and hide a real failure's provenance.
    path = tmp_path / f"form_{index}_{len(prefix)}.pengu"
    path.write_text(prefix + "weave main into int:\n  " + form, encoding="utf-8")
    _check_in_process(path)


@pytest.mark.parametrize("source", [
    "",                                    # empty file
    "\n\n\n",                              # only blank lines
    "weave\n",                             # truncated declaration
    "weave f into\n",                      # truncated return type
    "rune\n",                              # truncated rune
    "weave main into int:\n",              # header with no body
    "weave main into int:\n  return\n",    # bare return
    "weave main into int:\n  var\n",       # truncated var
    "weave main into int:\n  if\n",        # truncated if
    "import\n",                            # truncated import
    "weave main into int:\n  while\n",     # truncated while
    "weave main into int:\n  judge\n",     # truncated judge
    "weave main into int:\n  return calling\n",
    "weave main into int:\n  return donum\n",
    "weave main into int:\n  var x as\n",
    "weave main into int:\n  set\n",
    "weave main into int:\n  for\n",
    "weave main into int:\n  test\n",
    "@\n",
    "const\n",
    "alias\n",
    "concept\n",
    "enchanting\n",
    "bind\n",
    "omen\n",
    "echo\n",
    "seal\n",
    "insignia\n",
])
def test_truncated_inputs_never_crash(source, tmp_path):
    """Truncated declarations are the cheapest way to reach half-built AST nodes.

    An editor produces exactly these states on every keystroke, so the LSP path
    hits them constantly; an interpreter error here would be a language-server
    crash.
    """
    path = tmp_path / "trunc.pengu"
    path.write_text(source, encoding="utf-8")
    _check_in_process(path)
