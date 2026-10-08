#!/usr/bin/env python3
"""Regenerate ``tests/_test_policy_baseline.json``.

The baseline is a frozen snapshot of the test suite's *shape*, enforced by
``tests/test_test_policy.py``. It exists so that the rules in ``AGENT_TESTING.md``
are machine-checked rather than aspirational, and so that moving the suite towards
its target (``tests/*.py`` <= 15) is a sequence of deliberate, reviewable edits.

It is a **ratchet**, the same idiom as ``fail_under`` in ``.coveragerc``:

* adding a root test file fails the policy test -- new cases belong in
  ``tests/conformance/``;
* deleting one *also* fails until this file is regenerated, so shrinking the set
  cannot happen by accident.

Usage::

    python tools/gen_test_policy_baseline.py          # rewrite the baseline
    python tools/gen_test_policy_baseline.py --check  # fail if it is out of date
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
TESTS = REPO / "tests"
BASELINE_PATH = TESTS / "_test_policy_baseline.json"

#: Files that may inspect *generated C* rather than executed behaviour.
#:
#: The mission's rule 1: an end-to-end test never reads the generated C. A test
#: that asserts on codegen output pins the implementation, so a legitimate
#: refactor turns it red for no behavioural reason. These ten predate the rule;
#: the set may only shrink, and each one is a migration candidate for
#: ``tests/conformance/`` (behaviour) or ``tests/test_snapshots_c.py`` (a
#: structural snapshot, only when the runtime genuinely cannot detect the
#: regression).
READS_GENERATED_C_RE = r"bundle_c|generated_c"

#: Files that may call ``time.sleep``. Rule 7 says a test may not sleep: a sleep
#: is a guess about timing and a flake on a loaded machine. The three below use it
#: to force a distinct mtime before a cache assertion (an ordering device, not a
#: wait for a side effect), which is the one defensible form; they may only
#: shrink, and the ratchet is what stops a fourth from appearing.
SLEEP_RE = r"\btime\.sleep\("

#: This file declares the patterns it searches for and must not police itself.
POLICY_FILE = "test_test_policy.py"

#: Files allowed to spawn processes *and* carry the ``smoke`` marker. The smoke
#: tier promises "no C compilation", so a smoke file must not shell out.
SUBPROCESS_RE = r"subprocess|Popen|check_output"


def _root_test_files() -> List[str]:
    return sorted(p.name for p in TESTS.glob("test_*.py"))


def _files_matching(pattern: str) -> List[str]:
    """Files whose text matches ``pattern``, excluding this rule's own enforcer.

    ``tests/test_test_policy.py`` contains the patterns it searches for, so it
    always matches itself. Excluding it is not a loophole: the rules are about
    *new* files, and a self-match would only put the enforcer on its own
    allowlist, which is exactly the kind of quiet wrongness these checks exist to
    prevent.
    """
    rx = re.compile(pattern)
    # Recursive: the rule is about every test file, and the suite lives in area
    # packages under tests/. Only the *root count* is deliberately non-recursive.
    return sorted(
        p.name for p in TESTS.rglob("test_*.py")
        if p.name != POLICY_FILE
        and rx.search(p.read_text(encoding="utf-8", errors="replace"))
    )


def _tree(path: Path) -> Optional[ast.Module]:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"), str(path))
    except SyntaxError:
        return None


def _is_smoke_mark(node: ast.AST) -> bool:
    """True when ``node`` is the expression ``pytest.mark.smoke``."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "smoke"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    )


def _is_smoke_marked(tree: ast.Module) -> bool:
    """True for ``@pytest.mark.smoke`` or a module-level ``pytestmark``.

    Parsed rather than grepped on purpose. A file that merely *emits* the marker
    -- ``tests/test_conformance.py`` builds ``pytest.mark.smoke`` params in a
    helper -- is not itself smoke-marked, and a grep cannot tell the difference.
    """
    for node in ast.walk(tree):
        if any(_is_smoke_mark(d) for d in getattr(node, "decorator_list", None) or []):
            return True
    for stmt in tree.body:
        value = None
        if isinstance(stmt, ast.Assign):
            names = [t for t in stmt.targets if isinstance(t, ast.Name)]
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names = [stmt.target]
            value = stmt.value
        else:
            continue
        if not any(n.id == "pytestmark" for n in names) or value is None:
            continue
        if any(_is_smoke_mark(sub) for sub in ast.walk(value)):
            return True
    return False


def _spawns_a_process(tree: ast.Module) -> bool:
    """True when the module imports ``subprocess`` or calls ``os.system``/``os.popen``.

    Import- and call-based, not text-based: the words "subprocess" and "Popen"
    appear in the smoke files' own comments (and in this generator's patterns),
    and a text search happily reports a file as spawning a process because it
    says it does not.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == "subprocess" for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] == "subprocess":
                return True
        elif isinstance(node, ast.Call):
            fn = node.func
            if (isinstance(fn, ast.Attribute) and fn.attr in ("system", "popen")
                    and isinstance(fn.value, ast.Name) and fn.value.id == "os"):
                return True
    return False


def _smoke_files_with_subprocess() -> List[str]:
    """Smoke-marked files that spawn a process -- must stay empty."""
    out = []
    for path in sorted(TESTS.glob("test_*.py")):
        tree = _tree(path)
        if tree is None:
            continue
        if _is_smoke_marked(tree) and _spawns_a_process(tree):
            out.append(path.name)
    return out


def build_baseline() -> Dict[str, Any]:
    """The frozen snapshot. Deterministic, so a no-op run is a no-op diff."""
    return {
        "_meta": [
            "Frozen snapshot of the test suite's shape, enforced by "
            "tests/test_test_policy.py.",
            "Regenerate with: python tools/gen_test_policy_baseline.py",
            "",
            "root_test_files           -- adding one FAILS: put the case in "
            "tests/conformance/ instead.",
            "                             deleting one also fails until this file "
            "is shrunk: that is the ratchet.",
            "may_read_generated_c      -- may only shrink. Rule 1: an end-to-end "
            "test judges behaviour, not emitted C.",
            "may_sleep                 -- may only shrink. Rule 7: no test may "
            "sleep (mtime ordering is the one exception).",
            "smoke_files_with_subprocess -- must stay empty. The smoke tier "
            "promises no C compilation.",
        ],
        "root_test_files": _root_test_files(),
        "may_read_generated_c": _files_matching(READS_GENERATED_C_RE),
        "may_sleep": _files_matching(SLEEP_RE),
        "smoke_files_with_subprocess": _smoke_files_with_subprocess(),
    }


def render(baseline: Dict[str, Any]) -> str:
    return json.dumps(baseline, indent=2, ensure_ascii=False) + "\n"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the baseline is out of date")
    args = ap.parse_args(argv[1:])

    text = render(build_baseline())
    if args.check:
        current = BASELINE_PATH.read_text(encoding="utf-8") if BASELINE_PATH.is_file() else ""
        if current != text:
            print(f"{BASELINE_PATH.relative_to(REPO)} is out of date; run: "
                  f"python tools/gen_test_policy_baseline.py", file=sys.stderr)
            return 1
        print(f"{BASELINE_PATH.relative_to(REPO)} is up to date "
              f"({len(build_baseline()['root_test_files'])} root test files)")
        return 0

    BASELINE_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {BASELINE_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
