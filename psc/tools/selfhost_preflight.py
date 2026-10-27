#!/usr/bin/env python3
"""F5 self-compile preflight.

Dev-only tool. Emits C for a PenguScript entry with PSC, compiles it with a C
compiler in syntax-only mode, classifies the errors by root cause, and reports
the remaining error budget. It is the objective metric for F5a.

Examples:

    python psc/tools/selfhost_preflight.py --psc psc/build/psc
    python psc/tools/selfhost_preflight.py --psc psc/build/psc --budget 0 \
        --cc gcc --json
    python psc/tools/selfhost_preflight.py --psc psc/build/psc --smoke --keep

Exit codes: 0 within budget (and smoke ok, when requested), 1 over budget or
smoke failed, 2 setup/usage error.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "psc" / "src" / "main.pengu"
DEFAULT_PSC = ROOT / "psc" / "build" / "psc"

# Compiler candidates used when --cc is not given (gcc, clang, tcc in PATH or
# the in-tree TCC builds used by stage0).
TCC_CANDIDATES = (
    ROOT / "build" / "tcc-dist" / "tcc-dist" / "bin" / "tcc",
    ROOT / "build" / "tcc-dev" / "tinycc-src" / "tcc",
)

GCC_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
                    r"(?P<sev>error|warning|fatal error|note):\s*(?P<msg>.*)$")
# TCC uses "file:line: error: msg"; some variants omit the column.
TCC_RE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):\s*"
                    r"(?P<sev>error|warning):\s*(?P<msg>.*)$")

CLASSIFIERS = (
    ("G1", "módulo/tipo duplicado", (
        "redeclar", "redefin", "already defined", "previous definition",
        "redeclaration", "redefinition",
    )),
    ("G2", "declarador de puntero a función", (
        "expected identifier or", "no tiene un miembro", "has no member",
        "declarator", "function pointer",
    )),
    ("G6", "método/llamada", (
        "too many arguments", "argumento", "argument", "no es una función",
        "is not a function", "Num_", "incompatible-pointer-types",
    )),
    ("G5", "value-if / when / to string", (
        "returning", "return", "implicit declaration", "conversión",
        "conversion", "PenguString", "incompatible types when returning",
    )),
    ("G7", "strings/listas/index/omens", (
        "invalid operands to binary", "subíndice", "subscript", "member 'tag'",
        "miembro ‘tag’", "incompatible", "void *", "void*",
    )),
    ("G3", "defer/local fuera de scope", (
        "no se declaró", "undeclared", "was not declared", "unknown type name",
        "unknown type",
    )),
    ("G4", "constante cualificada", (
        "sdiag", "types.", "sym.", "CODE_", "NIF_", "SYM_",
    )),
)


@dataclass
class Issue:
    file: str
    line: int
    col: int
    severity: str
    message: str
    category: str = "G8"
    label: str = "otros"
    source_line: str = ""


@dataclass
class Report:
    source: str
    psc: str
    cc: str
    bundle: str = ""
    bundle_bytes: int = 0
    bundle_lines: int = 0
    emit_seconds: float = 0.0
    cc_seconds: float = 0.0
    ok_emit: bool = False
    emit_stderr: str = ""
    issues: list[Issue] = field(default_factory=list)
    raw_stderr: str = ""
    smoke_ok: bool | None = None
    smoke_stderr: str = ""

    @property
    def errors(self) -> int:
        return len(self.issues)


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, **kwargs)


def find_cc(name: str) -> str | None:
    if name in ("", "auto"):
        for cand in ("gcc", "clang"):
            found = shutil.which(cand)
            if found:
                return found
        for cand in TCC_CANDIDATES:
            if cand.is_file():
                return str(cand)
        found = shutil.which("tcc")
        return found
    if os.path.sep in name:
        return name if Path(name).is_file() else None
    found = shutil.which(name)
    if found:
        return found
    for cand in TCC_CANDIDATES:
        if cand.name == name and cand.is_file():
            return str(cand)
    return None


def include_flags() -> list[str]:
    return [
        "-I", str(ROOT),
        "-I", str(ROOT / "build" / "include"),
        "-I", str(ROOT / "std_c"),
    ]


def runtime_archive() -> str | None:
    for cand in (
        ROOT / "build" / "lib" / "libpengu_runtime.a",
        ROOT / "psc" / "build" / "libpengu_runtime.a",
    ):
        if cand.is_file():
            return str(cand)
    return None


def classify(issue: Issue) -> None:
    msg = issue.message.lower()
    # Qualified constants are checked before the generic "undeclared" bucket.
    if any(k.lower() in msg for k in ("sdiag.", "types.", "sym.", "code_",
                                      "nif_", "sym_")):
        issue.category, issue.label = "G4", "constante cualificada"
        return
    for cat, label, needles in CLASSIFIERS:
        if any(n.lower() in msg for n in needles):
            issue.category, issue.label = cat, label
            return
    issue.category, issue.label = "G8", "otros"


def parse_issues(stderr: str) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[tuple[str, int, str]] = set()
    for raw in stderr.splitlines():
        m = GCC_RE.match(raw) or TCC_RE.match(raw)
        if not m:
            continue
        sev = m.group("sev")
        if sev not in ("error", "fatal error"):
            continue
        f = m.group("file")
        line = int(m.group("line"))
        col = int(m.group("col") or 0)
        msg = m.group("msg").strip()
        key = (f, line, msg)
        if key in seen:
            continue
        seen.add(key)
        issue = Issue(file=f, line=line, col=col, severity=sev, message=msg)
        classify(issue)
        issues.append(issue)
    return issues


def attach_source(issues: list[Issue], max_files: int = 200) -> None:
    cache: dict[str, list[str] | None] = {}
    for issue in issues:
        if not issue.file or not os.path.isabs(issue.file):
            continue
        if issue.file not in cache:
            try:
                cache[issue.file] = Path(issue.file).read_text(
                    encoding="utf-8", errors="replace").splitlines()
            except OSError:
                cache[issue.file] = None
        lines = cache[issue.file]
        if lines and 1 <= issue.line <= len(lines):
            issue.source_line = lines[issue.line - 1].strip()
        if len(cache) > max_files:
            break


def normalize_path(text: str) -> str:
    return text.replace(str(ROOT) + os.sep, "").replace(str(ROOT), ".")


def print_report(rep: Report, top: int, as_json: bool) -> None:
    if as_json:
        print(json.dumps({
            "source": normalize_path(rep.source),
            "psc": normalize_path(rep.psc),
            "cc": rep.cc,
            "ok_emit": rep.ok_emit,
            "emit_stderr": rep.emit_stderr,
            "bundle": normalize_path(rep.bundle),
            "bundle_bytes": rep.bundle_bytes,
            "bundle_lines": rep.bundle_lines,
            "emit_seconds": round(rep.emit_seconds, 3),
            "cc_seconds": round(rep.cc_seconds, 3),
            "errors": rep.errors,
            "categories": dict(Counter(i.category for i in rep.issues)),
            "issues": [
                {
                    "file": normalize_path(i.file),
                    "line": i.line,
                    "col": i.col,
                    "category": i.category,
                    "label": i.label,
                    "message": i.message,
                    "source_line": i.source_line,
                }
                for i in rep.issues[:top]
            ],
            "smoke_ok": rep.smoke_ok,
            "smoke_stderr": rep.smoke_stderr,
        }, ensure_ascii=False, indent=2))
        return

    print(f"source:  {normalize_path(rep.source)}")
    print(f"psc:     {normalize_path(rep.psc)}")
    print(f"cc:      {rep.cc}")
    print(f"bundle:  {rep.bundle_lines} lines, {rep.bundle_bytes / (1024 * 1024):.2f} MB, "
          f"{rep.emit_seconds:.2f} s")
    print(f"errors:  {rep.errors} (unique files: "
          f"{len({i.file for i in rep.issues if i.file and not i.file.startswith('/tmp')})})")
    if rep.errors:
        counts = Counter((i.category, i.label) for i in rep.issues)
        for (cat, label), count in counts.most_common():
            print(f"  {cat} {label:<42} {count:5d}")
        print()
        shown = 0
        seen: set[tuple[str, str]] = set()
        for issue in rep.issues:
            key = (issue.category, issue.message)
            if key in seen:
                continue
            seen.add(key)
            shown += 1
            print(f"  [{issue.category}] {normalize_path(issue.file)}:{issue.line}: "
                  f"{issue.message}")
            if issue.source_line:
                print(f"      {issue.source_line}")
            if shown >= top:
                break
    status = "READY" if rep.errors == 0 else "BLOCKED"
    if rep.smoke_ok is False:
        status = "BLOCKED (smoke)"
    print(f"status:  {status}")
    if rep.smoke_ok is not None:
        print(f"smoke:   {'ok' if rep.smoke_ok else 'failed'}")
        if not rep.smoke_ok and rep.smoke_stderr:
            print(rep.smoke_stderr[:2000])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--psc", default=str(DEFAULT_PSC))
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--cc", default="auto")
    ap.add_argument("--budget", type=int, default=0)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="compile+link the bundle and run 'version'")
    ap.add_argument("--keep", action="store_true",
                    help="keep the temporary bundle and binary")
    ap.add_argument("--absolute", action="store_true",
                    help="pass the absolute source path (default: relative to ROOT)")
    args = ap.parse_args(argv)

    psc = Path(args.psc)
    source = Path(args.source)
    if not psc.is_file():
        print(f"preflight: PSC binary not found: {psc}", file=sys.stderr)
        return 2
    if not source.is_file():
        print(f"preflight: source not found: {source}", file=sys.stderr)
        return 2

    cc = find_cc(args.cc)
    if cc is None:
        print(f"preflight: C compiler not found: {args.cc}", file=sys.stderr)
        return 2

    tmpdir = Path(tempfile.mkdtemp(prefix="psc_preflight_"))
    bundle = tmpdir / "bundle.c"
    rep = Report(source=str(source), psc=str(psc), cc=cc)

    # The source spelling is part of the bug under test (G1). By default use
    # the same relative spelling a developer uses from the repo root; the
    # absolute variant is available for comparison.
    if args.absolute:
        source_arg = str(source)
    else:
        try:
            source_arg = str(source.resolve().relative_to(ROOT))
        except ValueError:
            source_arg = str(source)

    t0 = time.time()
    emit = _run([str(psc), "emit-c", source_arg, f"--out={bundle}"],
                cwd=str(ROOT))
    rep.emit_seconds = time.time() - t0
    rep.ok_emit = emit.returncode == 0 and bundle.is_file()
    rep.emit_stderr = (emit.stderr or "") + (emit.stdout or "")
    if not rep.ok_emit:
        print(rep.emit_stderr[:4000], file=sys.stderr)
        return 1
    rep.bundle = str(bundle)
    data = bundle.read_bytes()
    rep.bundle_bytes = len(data)
    rep.bundle_lines = data.count(b"\n") + 1

    cc_base = [cc, "-std=c11", "-w"]
    if Path(cc).name.lower().startswith("tcc"):
        # TCC has no -fsyntax-only; -c still checks syntax and is fast enough.
        syntax_cmd = cc_base + ["-c", str(bundle), "-o", str(tmpdir / "probe.o")]
    else:
        syntax_cmd = cc_base + ["-fsyntax-only", str(bundle)]
    t1 = time.time()
    syntax = _run(syntax_cmd + include_flags(), cwd=str(ROOT))
    rep.cc_seconds = time.time() - t1
    rep.raw_stderr = syntax.stderr or ""
    rep.issues = parse_issues(rep.raw_stderr)
    attach_source(rep.issues)

    if args.smoke:
        exe = tmpdir / "psc_smoke"
        runtime = runtime_archive()
        if runtime is None:
            rep.smoke_ok = False
            rep.smoke_stderr = "libpengu_runtime.a not found"
        else:
            link = _run([
                cc, "-std=c11", "-w", *include_flags(), str(bundle),
                runtime, "-lm", "-lpthread", "-o", str(exe),
            ], cwd=str(ROOT))
            if link.returncode != 0:
                rep.smoke_ok = False
                rep.smoke_stderr = link.stderr or link.stdout
            else:
                run = _run([str(exe), "version"], cwd=str(ROOT))
                rep.smoke_ok = run.returncode == 0
                if run.returncode != 0:
                    rep.smoke_stderr = run.stderr or run.stdout
                else:
                    rep.smoke_stderr = run.stdout.strip()

    print_report(rep, args.top, args.json)

    if args.keep:
        print(f"kept: {tmpdir}", file=sys.stderr)
    else:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if rep.errors > args.budget:
        return 1
    if args.smoke and rep.smoke_ok is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
