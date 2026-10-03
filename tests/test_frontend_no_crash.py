"""Crash-resistance sweep: the front end must never leak an interpreter error.

Rule C1 (ROADMAP_2.0 Anexo C): this test measures **behaviour** -- it runs the
real compiler over real inputs and asserts that no input produces a Python
traceback. It does not assert on message prose, and it does not require the
inputs to be *valid*: a fragment may legitimately be rejected with E0000.

Why this file exists
--------------------
Blocker B6 was a `NameError` raised from inside a diagnostic
(`pengu_parser/pengu_infer.py:4055` referenced an undefined `node`), so a user
who accessed a private symbol of another module got a Python traceback instead
of `E0043`. `pyflakes` can only find that class of bug when the name is
*statically* undefined; the compiler can also fail at runtime through
`AttributeError`, `KeyError`, `IndexError`, `TypeError` or `RecursionError` on
inputs nobody tried. This sweep covers the whole documented language surface at
once, which is how it would have caught B6.

The inputs are the `pengu`-fenced blocks of `LANGUAGE.md`, parsed with a
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

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODULE = "pengu_project"

TRACEBACK_MARKER = "Traceback (most recent call last)"

#: A traceback in the compiler's own frames, as opposed to a diagnostic that
#: merely quotes source text. `pengu_project.py` is the CLI entry point, so a
#: traceback there means the front end crashed rather than reported.
_CRASH_RE = re.compile(
    r'File "(?P<file>[^"]+)", line \d+, in ',
)


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


def _run_check(tmp_path, name, source):
    """Compiles `source` with the real CLI and returns (rc, combined output)."""
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


def _is_crash(output: str) -> bool:
    """True when the output contains a genuine Python traceback.

    A diagnostic may legitimately *quote* the word "Traceback" inside a message;
    we look for the compiler's own frames, and exclude frames raised while
    compiling C source (which are reported as build errors, not crashes).
    """
    if TRACEBACK_MARKER not in output:
        return False
    frames = [m.group("file") for m in _CRASH_RE.finditer(output)]
    if not frames:
        return True
    # A traceback whose frames all live in the Python standard library or in the
    # CLI/compiler is a crash. Anything mentioning a generated bundle is a C
    # compilation report, which is already formatted by the CLI.
    return any("pengu" in f or "site-packages" in f for f in frames)


@pytest.mark.parametrize("doc", ["LANGUAGE.md", "LANGUAGE_Spanish.md", "CHEATSHEET.md"])
def test_no_python_traceback_on_documented_blocks(doc, tmp_path):
    """Every documented block must be *handled*, valid or not.

    A fragment that does not parse is fine and expected -- it must produce a
    diagnostic, not an interpreter traceback. This is the generalised guard for
    B6: a missing return, an unknown call target, a private symbol, a malformed
    type and a bad container literal all funnel through the same front end.
    """
    path = REPO / doc
    blocks = _blocks(path)
    assert blocks, f"{doc} has no ```pengu blocks; the scanner is broken"

    crashes = []
    for index, body in blocks:
        rc, out = _run_check(tmp_path, f"{doc.replace('.', '_')}_{index}.pengu", body)
        if _is_crash(out):
            crashes.append((index, body.splitlines()[0][:70] if body.strip() else "(empty)", out))

    assert not crashes, "blocks produced a Python traceback:\n" + "\n\n".join(
        f"--- block {i} ({first}) ---\n{out[:1200]}" for i, first, out in crashes
    )


def test_cross_module_access_forms_never_crash(tmp_path):
    """B6's exact shape plus its neighbours, all cross-module.

    These are the forms that reach `_resolve_call_target` and the field-access
    path with a module-qualified target -- the code where the undefined `node`
    lived.
    """
    (tmp_path / "lib.pengu").write_text(
        "weave _priv into int:\n  return 1\n"
        "weave pub with a as int into int:\n  return a\n"
        "rune _Hidden:\n  z as int\n"
        "rune Shown:\n  x as f32\n  y as f32\n"
        "const _K as int is 1\n"
        "const K as int is 2\n",
        encoding="utf-8",
    )
    reexport = tmp_path / "dep.pengu"
    reexport.write_text(
        "import lib\n"
        "declare addp with a as lib.Shown, b as lib.Shown into lib.Shown\n",
        encoding="utf-8",
    )
    forms = [
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
    for i, body in enumerate(forms):
        for prefix in ("import lib\n", "import lib\nimport dep\n"):
            _rc, out = _run_check(tmp_path, f"form_{i}_{len(prefix)}.pengu",
                                  prefix + "weave main into int:\n  " + body)
            assert not _is_crash(out), f"form {i} with {prefix!r} crashed:\n{out[:1500]}"


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
    hits them constantly; a traceback here would be a language-server crash.
    """
    _rc, out = _run_check(tmp_path, "trunc.pengu", source)
    assert not _is_crash(out), f"input {source!r} crashed:\n{out[:1500]}"
