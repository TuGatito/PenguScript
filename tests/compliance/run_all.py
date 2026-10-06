#!/usr/bin/env python3
"""Compliance-corpus runner (Roadmap 2.0, item 8.4).

Every program under ``tests/compliance/`` is a small canonical program that pins
one section of ``LANGUAGE.md``.  This runner drives each one through the *real*
toolchain, never by inspecting source or generated text:

1. ``python pengu_project.py check --entry <file>``   (must exit 0)
2. ``python pengu_project.py build --entry <file>``   (must exit 0)
3. execute the produced binary and compare its exit code with the ``expects_rc``
   recorded in ``corpus.json``.

Each program is built in its own throw-away directory so the repository tree is
never written to and runs cannot see each other's artifacts.

Usage::

    python tests/compliance/run_all.py              # run everything
    python tests/compliance/run_all.py --list       # list the corpus
    python tests/compliance/run_all.py --only 016   # run one program (prefix match)
    python tests/compliance/run_all.py --json       # machine-readable summary
    python tests/compliance/run_all.py -v           # stream each program's output

Exit status is 0 only when every program checks, builds, and exits with its
expected code.
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

COMPLIANCE_DIR = Path(__file__).resolve().parent
REPO = COMPLIANCE_DIR.parent.parent
CORPUS_PATH = COMPLIANCE_DIR / "corpus.json"
LANGUAGE_MD = REPO / "LANGUAGE.md"
CLI = REPO / "pengu_project.py"

PROGRAM_GLOB = "[0-9][0-9][0-9]-*.pengu"
DEFAULT_EXPECTS_RC = 0
DEFAULT_TIMEOUT = 300

# `## 12. Optionals & errors` / `### 7.4 \`judge\` — pattern matching` / `#### 9.1.1 ...`
_HEADING_RE = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")
# `# LANGUAGE.md §7.4 — judge — pattern matching`
_PROGRAM_HEADER_RE = re.compile(r"^#\s*LANGUAGE\.md\s*§(\S+)\s*—\s*(.+?)\s*$")
# `    Finished [debug] target(s) in 0.64s -> /tmp/xxx/build/app`
_ARTIFACT_RE = re.compile(r"->\s*(\S+)\s*$")


# --------------------------------------------------------------------------
# Corpus + LANGUAGE.md integrity
# --------------------------------------------------------------------------


def load_corpus(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Loads ``corpus.json`` and returns its list of program entries."""
    raw = json.loads((path or CORPUS_PATH).read_text(encoding="utf-8"))
    programs = raw["programs"] if isinstance(raw, dict) else raw
    return [dict(entry) for entry in programs]


def language_sections(md_path: Optional[Path] = None) -> Dict[str, str]:
    """Maps every numbered LANGUAGE.md heading to its title.

    >>> language_sections()["7.4"]
    '`judge` — pattern matching'
    """
    text = (md_path or LANGUAGE_MD).read_text(encoding="utf-8")
    sections: Dict[str, str] = {}
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            section = match.group(2)
            title = re.sub(r"\s+#+\s*$", "", match.group(3)).strip()
            sections.setdefault(section, title)
    return sections


def program_file_header(path: Path) -> Dict[str, str]:
    """Reads the ``# LANGUAGE.md §<section> — <title>`` header of a program."""
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    match = _PROGRAM_HEADER_RE.match(first_line)
    if not match:
        raise ValueError(f"{path.name}: first line is not a corpus header: {first_line!r}")
    return {"section": match.group(1), "title": match.group(2).strip()}


def corpus_dir_programs() -> List[Path]:
    return sorted(COMPLIANCE_DIR.glob(PROGRAM_GLOB))


def verify_corpus(programs: Optional[List[Dict[str, Any]]] = None,
                  md_path: Optional[Path] = None) -> List[str]:
    """Returns a list of human-readable problems (empty when the corpus is sound).

    Checks: every listed file exists, the directory holds exactly the listed
    programs, each program's header agrees with its corpus entry, every declared
    section exists in LANGUAGE.md with the same title, and sections are
    distinct-ish (no section is reused more than once).
    """
    programs = programs if programs is not None else load_corpus()
    sections = language_sections(md_path)
    problems: List[str] = []

    listed = [entry["file"] for entry in programs]
    on_disk = [path.name for path in corpus_dir_programs()]
    for name in listed:
        if not (COMPLIANCE_DIR / name).is_file():
            problems.append(f"{name}: listed in corpus.json but missing on disk")
    for name in on_disk:
        if name not in listed:
            problems.append(f"{name}: present on disk but missing from corpus.json")

    seen: Dict[str, List[str]] = {}
    for entry in programs:
        name = entry["file"]
        section = str(entry.get("section", ""))
        title = entry.get("title", "")
        path = COMPLIANCE_DIR / name
        if not path.is_file():
            continue
        header = program_file_header(path)
        if header["section"] != section:
            problems.append(
                f"{name}: header section {header['section']!r} != corpus section {section!r}")
        if header["title"] != title:
            problems.append(
                f"{name}: header title {header['title']!r} != corpus title {title!r}")
        if section not in sections:
            problems.append(f"{name}: section {section!r} does not exist in LANGUAGE.md")
        elif sections[section] != title:
            problems.append(
                f"{name}: title {title!r} != LANGUAGE.md {sections[section]!r} "
                f"for section {section}")
        if not isinstance(entry.get("expects_rc"), int):
            problems.append(f"{name}: 'expects_rc' must be an integer")
        seen.setdefault(section, []).append(name)

    for section, files in seen.items():
        if len(files) > 1:
            problems.append(f"section {section!r} is claimed by more than one program: {files}")
    return problems


# --------------------------------------------------------------------------
# Running one program
# --------------------------------------------------------------------------


@dataclass
class RunResult:
    """Outcome of one corpus program through check -> build -> execute."""

    file: str
    section: str
    title: str
    expects_rc: int
    stage: str = "check"           # check | build | run | done
    ok: bool = False
    rc: Optional[int] = None        # observed exit code of the produced binary
    artifact: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    commands: List[List[str]] = field(default_factory=list)

    def detail(self) -> str:
        parts = [f"stage={self.stage}"]
        if self.rc is not None:
            parts.append(f"rc={self.rc} expected={self.expects_rc}")
        return " ".join(parts)


def _python() -> str:
    return os.environ.get("PENGU_COMPLIANCE_PYTHON", sys.executable)


def _artifact_from_stdout(stdout: str, workdir: Path) -> Path:
    """Reads the artifact path the CLI prints (`Finished ... -> <path>`)."""
    for line in reversed(stdout.splitlines()):
        match = _ARTIFACT_RE.search(line)
        if match:
            return Path(match.group(1))
    exe = "app.exe" if os.name == "nt" else "app"
    return workdir / "build" / exe


def run_program(entry: Path, expects_rc: int = DEFAULT_EXPECTS_RC,
                timeout: int = DEFAULT_TIMEOUT,
                workdir: Optional[Path] = None) -> RunResult:
    """Checks, builds and executes one corpus program.

    ``entry`` is the ``.pengu`` file.  The build happens in a private temporary
    directory (or ``workdir`` when given) so nothing in the repository changes.
    """
    entry = Path(entry).resolve()
    header = program_file_header(entry)
    result = RunResult(file=entry.name, section=header["section"],
                       title=header["title"], expects_rc=expects_rc)

    own_dir = workdir is None
    cwd = Path(workdir) if workdir is not None else Path(
        tempfile.mkdtemp(prefix="pengu_compliance_"))
    try:
        for stage, argv in (
            ("check", [_python(), str(CLI), "check", "--entry", str(entry)]),
            ("build", [_python(), str(CLI), "build", "--entry", str(entry)]),
        ):
            result.stage = stage
            result.commands.append(argv)
            proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                                  timeout=timeout)
            if stage == "check":
                result.stdout, result.stderr = proc.stdout, proc.stderr
            else:
                result.stdout, result.stderr = proc.stdout, proc.stderr
            if proc.returncode != 0:
                result.ok = False
                result.rc = None
                return result
            if stage == "build":
                result.artifact = str(_artifact_from_stdout(proc.stdout, cwd))

        result.stage = "run"
        exe = Path(result.artifact)
        if not exe.is_file():
            result.stdout += f"\n[runner] build reported an artifact that does not exist: {exe}"
            result.ok = False
            return result
        result.commands.append([str(exe)])
        run = subprocess.run([str(exe)], cwd=str(cwd), capture_output=True, text=True,
                             timeout=timeout)
        result.stage = "done"
        result.rc = run.returncode
        result.stdout += run.stdout
        result.stderr += run.stderr
        result.ok = run.returncode == expects_rc
        return result
    finally:
        if own_dir:
            shutil.rmtree(cwd, ignore_errors=True)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _select(programs: List[Dict[str, Any]], only: Optional[str]) -> List[Dict[str, Any]]:
    if not only:
        return programs
    return [entry for entry in programs if only in entry["file"]]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile and execute every compliance-corpus program.")
    parser.add_argument("--only", metavar="SUBSTRING",
                        help="run only programs whose filename contains SUBSTRING")
    parser.add_argument("--list", action="store_true", dest="list_only",
                        help="list the corpus and exit")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable JSON report")
    parser.add_argument("--check-corpus", action="store_true",
                        help="validate corpus.json against the files and LANGUAGE.md, then exit")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="stream each program's stdout/stderr")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"per-command timeout in seconds (default {DEFAULT_TIMEOUT})")
    args = parser.parse_args(argv)

    if args.check_corpus:
        problems = verify_corpus()
        for problem in problems:
            print(f"corpus: {problem}")
        print("corpus ok" if not problems else f"corpus FAILED ({len(problems)} problems)")
        return 1 if problems else 0

    programs = load_corpus()

    if args.list_only:
        for entry in programs:
            print(f"{entry['file']}\t§{entry['section']}\t{entry['title']}\t"
                  f"rc={entry.get('expects_rc', DEFAULT_EXPECTS_RC)}")
        return 0

    selected = _select(programs, args.only)
    if not selected:
        print(f"no corpus programs match {args.only!r}", file=sys.stderr)
        return 2

    results: List[RunResult] = []
    for entry in selected:
        result = run_program(COMPLIANCE_DIR / entry["file"],
                             expects_rc=int(entry.get("expects_rc", DEFAULT_EXPECTS_RC)),
                             timeout=args.timeout)
        results.append(result)
        if args.json:
            continue
        status = "ok  " if result.ok else "FAIL"
        print(f"[{status}] {result.file:<44} §{result.section:<6} {result.detail()}")
        if not result.ok or args.verbose:
            blob = (result.stdout + result.stderr).strip()
            if blob:
                for line in blob.splitlines():
                    print(f"        | {line}")

    failed = [result for result in results if not result.ok]

    if args.json:
        print(json.dumps({
            "total": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "results": [
                {
                    "file": result.file,
                    "section": result.section,
                    "title": result.title,
                    "ok": result.ok,
                    "stage": result.stage,
                    "rc": result.rc,
                    "expects_rc": result.expects_rc,
                    "artifact": result.artifact,
                }
                for result in results
            ],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\ncompliance corpus: {len(results) - len(failed)}/{len(results)} passed")
        if failed:
            print("failed programs:")
            for result in failed:
                print(f"  - {result.file} ({result.detail()})")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
