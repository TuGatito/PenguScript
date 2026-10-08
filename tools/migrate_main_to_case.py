#!/usr/bin/env python3
"""Migrate a ``weave main into int:`` / ``into void:`` program into a
conformance case.

Why this exists
---------------
Most of the pre-existing corpus (``tests/compliance``, ``tests/std_programs``,
``tests/test_generics``, ...) is written as standalone ``weave main into int:``
programs. Two ``main``s cannot coexist in one binary, so none of them can join the
batch bundle (`tests/conformance/README.md`) without being rewritten. This tool
does that rewrite mechanically and, crucially, **derives the expectations by
running the original program** rather than by trusting the prose that describes it.

What it does, per program
-------------------------
1. Builds and runs the *original* ``main`` program, capturing stdout and the exit
   code. Those become ``.expected`` and ``.exit``.
2. Rewrites ``weave main into <type>:`` into ``test "<case id>":`` and drops the
   trailing ``return 0`` (a test body is void).
3. Writes ``<out>/<id>.pengu|.expected|.exit``.

Nothing is verified here: the migration is verified by *running* the new corpus.
If a conversion is wrong, ``pytest tests/test_conformance.py`` fails, because the
converted case no longer reproduces the output captured from the original.

Usage::

    # What would happen, writing nothing:
    python tools/migrate_main_to_case.py --compliance --dry-run

    # Do it:
    python tools/migrate_main_to_case.py --compliance --apply

    # One file:
    python tools/migrate_main_to_case.py --source tests/std_programs/atlas.pengu \\
        --id std_programs/atlas --out tests/conformance/std_programs --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.conftest import (  # noqa: E402
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    runtime_link_flags,
    runtime_tail_flags,
)

COMPLIANCE_DIR = REPO / "tests" / "compliance"
CONFORMANCE_DIR = REPO / "tests" / "conformance"
MANIFEST_PATH = CONFORMANCE_DIR / "_manifest.json"

#: The entry point of a corpus program. Both return types occur in
#: ``tests/std_programs``: programs that compute a value for the shell use
#: ``into int``, and the ones that only print use ``into void`` (and have no
#: trailing ``return``, so nothing else in the rewrite applies to them).
MAIN_HEADER_RE = re.compile(r"^weave main into (?:int|void):\s*$", re.MULTILINE)
#: The closing ``return 0`` (or bare ``return``) of the migrated entry point.
#:
#: Anchored to the END of the file, not "the first return that looks like it".
#: The entry point is the last block in every corpus program, so its closing
#: return is the file's last statement -- whereas the *first* ``return 0`` in a
#: file frequently belongs to a helper. Matching the first one silently gutted
#: ``tests/compliance/020-declare-extern-c.pengu``'s helper and left the void test
#: returning a value.
TRAILING_RETURN_RE = re.compile(r"\n[ \t]*return(?: 0)?[ \t]*\Z")


def _cc() -> Optional[str]:
    """TCC when staged, else gcc/clang/cc. See tools/../AGENT_TESTING.md."""
    try:
        from pengu_tcc import find_tcc

        staged = find_tcc()
        if staged:
            return staged
    except Exception:
        pass
    for name in ("gcc", "clang", "cc"):
        found = shutil.which(name)
        if found:
            return found
    return None


def capture_behaviour(source_text: str, tag: str = "migrate") -> Tuple[str, int]:
    """Builds and runs `source_text` as a normal program; returns (stdout, exit).

    ``exit`` is normalised to shell convention (128+signal) so a program that
    aborts can be recorded in a ``.exit`` file that means the same thing on every
    platform.
    """
    from pengu_project import PenguBuilder, ProjectConfig

    cc = _cc()
    if cc is None:
        raise RuntimeError("no C compiler available (set PENGU_TEST_CC or install gcc)")

    work = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
    try:
        entry = work / f"{tag}.pengu"
        entry.write_text(source_text, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), profile="debug", output="c")
        bundle_path, _ = PenguBuilder(cfg).compile()
        exe = Path(bundle_path)
        res = subprocess.run([str(exe)], capture_output=True, text=True,
                             cwd=str(REPO), timeout=300)
        rc = res.returncode + 256 if res.returncode < 0 else res.returncode
        return res.stdout, rc
    finally:
        shutil.rmtree(work, ignore_errors=True)


def convert(source_text: str, case_id: str, *, drop_trailing_return: bool = True) -> str:
    """Rewrites the entry point of a ``weave main into int:`` program into a test.

    Only the *last* ``return`` of the file is removed, and only when it closes the
    entry point: helper functions keep their returns (``tests/compliance/
    020-declare-extern-c.pengu`` has a helper returning -1/1 and must keep them).
    """
    match = MAIN_HEADER_RE.search(source_text)
    if match is None:
        raise ValueError("no `weave main into int:` / `into void:` header found")
    converted = source_text[:match.start()] + f'test "{case_id}":' + source_text[match.end():]

    if drop_trailing_return:
        # The entry point is the last block in every corpus program, so its
        # closing `return` is the final statement in the file. Anchor to the end:
        # the *first* `return 0` in a file often belongs to a helper, and removing
        # that one corrupts the helper and leaves the void test returning a value.
        stripped = converted.rstrip("\n")
        new, n = TRAILING_RETURN_RE.subn("", stripped, count=1)
        if n:
            converted = new + "\n"
    return converted


def _slug(case_id: str) -> str:
    return case_id.split("/")[-1]


def _safe_slug(stem: str) -> str:
    """A file stem that is also a valid Pengu module identifier.

    The batch runner imports every corpus module by its path, so the path has to
    *be* a module path. ``001-hello`` is not one: a leading digit cannot start an
    identifier and ``-`` is not an identifier character, so a corpus copied
    verbatim from ``tests/compliance`` fails to bundle with
    ``unexpected '001'``. ``s001_hello`` keeps the ordering and is legal.
    """
    slug = stem.replace("-", "_")
    slug = re.sub(r"[^0-9A-Za-z_]", "_", slug)
    if not slug or slug[0].isdigit():
        slug = "s" + slug
    return slug


def migrate_one(source_path: Path, case_id: str, out_dir: Path, *,
                apply: bool, meta: Optional[Dict[str, object]] = None,
                manifest: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Captures, converts and (when applying) writes one case. Returns a report."""
    original = source_path.read_text(encoding="utf-8")
    stdout, rc = capture_behaviour(original, tag=_slug(case_id).replace("-", "_"))
    converted = convert(original, case_id)

    stem = _slug(case_id)
    report: Dict[str, object] = {
        "id": case_id,
        "source": str(source_path.relative_to(REPO)),
        "exit": rc,
        "stdout_bytes": len(stdout.encode("utf-8")),
        "wrote": False,
    }
    if apply:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{stem}.pengu").write_text(converted, encoding="utf-8")
        (out_dir / f"{stem}.expected").write_text(stdout, encoding="utf-8")
        (out_dir / f"{stem}.exit").write_text(f"{rc}\n", encoding="utf-8")
        if manifest is not None:
            manifest[case_id] = meta or {}
        report["wrote"] = True
    return report


def _load_manifest() -> Dict[str, object]:
    if not MANIFEST_PATH.is_file():
        return {"_meta": {"comment": []}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _write_manifest(manifest: Dict[str, object]) -> None:
    """`_meta` first, then cases sorted -- the shape the runner documents."""
    meta = manifest.get("_meta")
    body = {k: v for k, v in sorted(manifest.items()) if k != "_meta"}
    ordered: Dict[str, object] = {}
    if meta is not None:
        ordered["_meta"] = meta
    ordered.update(body)
    MANIFEST_PATH.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def migrate_compliance(apply: bool) -> int:
    """Migrates every program in tests/compliance/corpus.json.

    The corpus manifest already records each program's LANGUAGE.md section, its
    title and what it pins, so the conformance manifest can carry the same
    information instead of losing it in the move.
    """
    corpus_path = COMPLIANCE_DIR / "corpus.json"
    if not corpus_path.is_file():
        print(f"error: {corpus_path.relative_to(REPO)} not found", file=sys.stderr)
        return 1
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    programs = corpus.get("programs", corpus) if isinstance(corpus, dict) else corpus

    out_dir = CONFORMANCE_DIR / "compliance"
    manifest = _load_manifest()
    reports: List[Dict[str, object]] = []
    for prog in programs:
        filename = prog["file"]
        stem = _safe_slug(Path(filename).stem)
        case_id = f"compliance/{stem}"
        meta = {
            "feature": "compliance",
            "platforms": ["linux", "macos", "windows"],
            "pins": prog.get("pins", ""),
            "section": prog.get("section", ""),
            "title": prog.get("title", ""),
            "migrated-from": f"tests/compliance/{filename}",
        }
        reports.append(migrate_one(
            COMPLIANCE_DIR / filename, case_id, out_dir,
            apply=apply, meta=meta, manifest=manifest,
        ))

    if apply:
        _write_manifest(manifest)

    non_zero = [r for r in reports if r["exit"] != 0]
    silent = [r for r in reports if r["stdout_bytes"] == 0]
    print(f"{'migrated' if apply else 'would migrate'}: {len(reports)} case(s) -> "
          f"{out_dir.relative_to(REPO)}")
    print(f"  expects a non-zero exit: {len(non_zero)}"
          + (f" {[r['id'] for r in non_zero]}" if non_zero else ""))
    print(f"  produces no stdout (assert-only): {len(silent)}")
    if apply:
        print("  next: python tools/gen_conformance_deps.py")
        print("        python tools/gen_test_policy_baseline.py")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--compliance", action="store_true",
                    help="migrate every program in tests/compliance/corpus.json. "
                         "ALREADY APPLIED: that corpus was migrated to "
                         "tests/conformance/compliance/ and the source removed, so "
                         "this mode only serves an equivalent corpus in the same "
                         "shape")
    ap.add_argument("--source", default=None, help="migrate a single .pengu file")
    ap.add_argument("--id", default=None, help="case id for --source")
    ap.add_argument("--out", default=None, help="output directory for --source")
    ap.add_argument("--profiles", default="debug",
                    help="comma-separated build profiles the case must pass in "
                         "(default: debug). Use debug,release to preserve a test "
                         "that asserted both")
    ap.add_argument("--skip-under-sanitizers", action="store_true",
                    help="declare a known sanitizer finding for this case")
    ap.add_argument("--platforms", default="linux,macos,windows",
                    help="comma-separated platforms the case is meaningful on")
    ap.add_argument("--apply", action="store_true", help="write the files")
    ap.add_argument("--dry-run", action="store_true",
                    help="capture and convert, but write nothing (the default)")
    args = ap.parse_args(argv[1:])

    apply = args.apply and not args.dry_run

    if args.compliance:
        return migrate_compliance(apply)

    if args.source:
        if not args.id or not args.out:
            print("error: --source needs --id and --out", file=sys.stderr)
            return 2
        manifest = _load_manifest()
        report = migrate_one(
            Path(args.source).resolve(), args.id, Path(args.out).resolve(),
            apply=apply,
            meta={
                "feature": args.id.split("/")[0],
                "platforms": [p.strip() for p in args.platforms.split(",") if p.strip()],
                "profiles": [p.strip() for p in args.profiles.split(",") if p.strip()],
                "migrated-from": str(Path(args.source).resolve().relative_to(REPO)),
                **({"skip_under_sanitizers": True} if args.skip_under_sanitizers else {}),
            },
            manifest=manifest,
        )
        if apply:
            _write_manifest(manifest)
        print(json.dumps(report, indent=2))
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
