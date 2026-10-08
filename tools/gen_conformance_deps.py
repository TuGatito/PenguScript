#!/usr/bin/env python3
"""Generate ``tests/conformance/_deps.json`` — which files can affect which case.

``pengu selftest --affected`` uses this to decide which conformance cases a change
can possibly break. It is deliberately **conservative**: over-selecting costs a few
seconds, under-selecting ships a regression that CI never ran.

Keys are repository-relative POSIX paths
----------------------------------------
The mission sketch for this file used dotted module names (``std.scrolls``,
``pengu_parser.pengu_codegen``). Paths are used instead, because a path is exactly
what ``git diff --name-only`` prints: no name<->path conversion step, no silent
mismatch when a module is renamed, and every changed file is directly comparable.
The generator is the only thing that ever writes this file, so the format cannot
drift out of sync with it.

Prefix entries
--------------
A dependency ending in ``/`` is a **directory prefix**, meaning "any file under
here". Every case depends on the ``pengu_parser/`` package, the builder and the C
runtime header, because every case is compiled by them. Recording that as a prefix
rather than as a list of files is what keeps the graph from going stale: adding
``pengu_parser/pengu_codegen/new_thing.py`` is covered the moment it exists, instead
of requiring someone to remember to regenerate a file list.

Measured dependency (what this does *not* do)
---------------------------------------------
A prefix over-approximates: any change under ``pengu_parser/`` selects the whole
corpus, and that is the honest answer, not a bug -- a grammar change can affect
every program. Sharper selection needs *measured* dependencies: run the corpus
under ``coverage --cov-context=test`` and record, per case, which lines actually
executed. That turns "can affect" into "did affect". It is the intended follow-up;
see tests/_inventory.md §12.

Usage::

    python tools/gen_conformance_deps.py            # write _deps.json
    python tools/gen_conformance_deps.py --check    # fail if it is out of date
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

REPO = Path(__file__).resolve().parent.parent
CONFORMANCE = REPO / "tests" / "conformance"
DEPS_PATH = CONFORMANCE / "_deps.json"

#: Files/prefixes every case depends on, whatever it contains.
#:
#: ``pengu_parser/`` is the front end (grammar, parser, checker, codegen);
#: ``pengu_project.py`` is the builder that assembles the bundle;
#: ``pengu_runtime.h`` is included by every bundle. All three are prefixes/files,
#: and all three are deliberately over-approximate.
CORE_DEPS: List[str] = [
    "build_runtime.py",
    "pengu_parser/",
    "pengu_project.py",
    "pengu_runtime.h",
]

#: The runner itself: a change to it can change any case's semantics.
RUNNER_DEPS: List[str] = [
    "tests/conformance/_manifest.json",
    "tests/test_conformance.py",
    "tools/gen_conformance_deps.py",
]

_IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)\s*$", re.M)


def _case_id(path: Path) -> str:
    return path.relative_to(CONFORMANCE).with_suffix("").as_posix()


def _load_patterns() -> Set[str]:
    """Every dependency pattern declared by the tree layout, as a set."""
    return set(CORE_DEPS) | set(RUNNER_DEPS)


def _resolve_import(token: str, case: Path) -> List[str]:
    """Maps a Pengu ``import`` token to repository-relative dependency paths.

    ``std.spark`` -> ``std/spark.pengu``. A non-``std`` token may name a sibling
    module of the case (``import helpers``) or a corpus-root module
    (``import _smoke.shared``); both are tried, and an import that resolves to
    neither yields no dependency but is reported by the caller.
    """
    dotted = token.split(".")
    if dotted[0] == "std":
        rel = Path("std") / Path(*dotted[1:])
        return [str((rel.with_suffix(".pengu")).as_posix())] if dotted[1:] else []

    candidates = []
    # Relative to this case's own directory, then relative to the corpus root.
    for base in (case.parent, CONFORMANCE):
        for suffix in (".pengu", "/main.pengu", "/mod.pengu"):
            p = base / (Path(*dotted).as_posix() + suffix)
            if p.is_file():
                candidates.append(str(p.relative_to(REPO).as_posix()))
                break
        if candidates:
            break
    return candidates


def _imports_of(path: Path) -> List[str]:
    return _IMPORT_RE.findall(path.read_text(encoding="utf-8"))


def build_graph(verbose: bool = False) -> Dict[str, List[str]]:
    """Dependency sets for every case, plus a ``_meta`` block. Deterministic."""
    cases = sorted(
        p for p in CONFORMANCE.rglob("*.pengu")
    )
    # A case is a .pengu with a sibling .expected; everything else is a support
    # module that cases may import.
    case_files = [p for p in cases if p.with_suffix(".expected").is_file()]
    support = {_case_id(p): p for p in cases if p not in case_files}

    graph: Dict[str, List[str]] = {}
    unresolved: List[str] = []

    for case in case_files:
        deps: Set[str] = _load_patterns()
        # Support modules of the corpus are compiled into the same bundle, so a
        # change to any of them can affect this case.
        for support_id, support_path in support.items():
            deps.add(str(support_path.relative_to(REPO).as_posix()))
        for token in _imports_of(case):
            resolved = _resolve_import(token, case)
            if not resolved:
                unresolved.append(f"{_case_id(case)}: import {token}")
            deps.update(resolved)
        # The case's own file: changing it must select exactly it.
        deps.add(str(case.relative_to(REPO).as_posix()))
        graph[_case_id(case)] = sorted(deps)

    if unresolved and verbose:
        for line in unresolved:
            print(f"  [deps] unresolved import -> {line}", file=sys.stderr)

    graph["_meta"] = [
        f"generated-by: tools/gen_conformance_deps.py",
        f"cases: {len(graph)}",
    ]
    return graph


def render(graph: Dict[str, List[str]]) -> str:
    """Stable JSON: sorted keys, sorted lists, so a no-op run is a no-op diff."""
    meta = graph.get("_meta")
    body = {k: sorted(v) for k, v in sorted(graph.items()) if k != "_meta"}
    ordered: Dict[str, object] = {}
    if meta is not None:
        ordered["_meta"] = meta
    ordered.update(body)
    return json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if _deps.json is missing or out of date")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv[1:])

    graph = build_graph(verbose=args.verbose)
    if len(graph) <= 1:
        print("error: no conformance cases found under tests/conformance/",
              file=sys.stderr)
        return 1

    text = render(graph)
    if args.check:
        current = DEPS_PATH.read_text(encoding="utf-8") if DEPS_PATH.is_file() else ""
        if current != text:
            print(f"{DEPS_PATH.relative_to(REPO)} is out of date; "
                  f"run: python tools/gen_conformance_deps.py", file=sys.stderr)
            return 1
        print(f"{DEPS_PATH.relative_to(REPO)} is up to date "
              f"({len(graph) - 1} case(s))")
        return 0

    DEPS_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {DEPS_PATH.relative_to(REPO)} ({len(graph) - 1} case(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
