#!/usr/bin/env python3
"""Per-archive attribution of the ``hello_world`` binary size.

Builds ``hello_world`` once through the real toolchain (``pengu_project.py``),
then answers two different questions with real measurements instead of
guesses:

1. **Map attribution** — how many bytes of the final, stripped executable each
   input archive actually contributes. Read straight out of GNU ld's
   ``-Map`` output (``Linker script and memory map``), so it is exact and
   costs one extra link, not N.

2. **Delta when excluded** — how much smaller the binary becomes when one
   archive is dropped from the link line entirely. This is the number people
   usually mean by "how much does libxml2 cost me?", and it is *not* the same
   as the map figure: dropping an archive can also drop everything that only
   existed to satisfy it. The link is re-run with
   ``-Wl,--unresolved-symbols=ignore-all`` so that a link which would normally
   fail still produces an ELF we can measure. The resulting binary is broken
   on purpose; only its section sizes are read.

Why not ``-Wl,--exclude-libs,<archive>``: that option only hides symbols from
the *dynamic* symbol table of a shared object. It does not stop the linker from
pulling a static member in, so it measures ~0 for every archive. The two
methods above measure what they claim to measure.

``--legacy`` measures the *pre-2.0* link shape instead: every archive on the
command line and no section GC. That is what makes the attribution table in
``BENCHMARKS.md`` reproducible on today's checkout -- without it the "before"
numbers would only be reproducible by checking out the parent commit.

Requires a checkout with ``build/lib/*.a`` already compiled
(``python build_runtime.py``) and a working ``gcc`` + ``strip``.

Usage::

    python benches/binary_size_breakdown.py            # human-readable table
    python benches/binary_size_breakdown.py --json      # machine-readable
    python benches/binary_size_breakdown.py --legacy    # pre-2.0 link shape
    python benches/binary_size_breakdown.py --out benches/results/x.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

#: ``-l`` names emitted by the toolchain's platform tail. They are not
#: third-party archives: they are libc/libm/libdl/pthread specifics and the
#: dynamic OpenSSL/CoreFoundation providers. Dropping one to attribute size
#: would not build anything reproducible, so they stay out of the table.
TAIL_LIBS = {"rt", "crypto", "ssl", "pthread", "m", "dl", "c", "gcc", "stdc++"}

#: ``-l`` names that are part of the PenguScript runtime itself, never attributed.
CORE_LIBS = {"pengu_runtime", "pengu_raymath", "pengu_stb"}

#: The archives every build linked before conditional linking existed. ``-lz``
#: is already on the modern line, the other five are not.
LEGACY_ARCHIVES = ["pcre2-8", "xml2", "curl", "mbedcrypto", "microhttpd"]

#: The two ways section GC is spelled. ``--legacy`` has to remove both.
_GC_TOKENS = ("-Wl,--gc-sections", "-Wl,-dead_strip")
_SECTION_TOKENS = ("-ffunction-sections", "-fdata-sections")

_LINK_LINE = re.compile(r"\[pengu\] running C compiler: (.*)$", re.MULTILINE)
#: The map's memory-map body writes an input section two ways, depending on
#: whether the section name fits its column:
#:
#:   `` .text       0x0000000000001170    0x26 /path/Scrt1.o``
#:   `` .text.pcre2_compile_8``
#:   ``                0x0000000000001170    0x26 /path/libpcre2-8.a(pcre2_compile.o)``
#:
#: Long section names take the two-line form, which is *every* section of a
#: ``-ffunction-sections`` build. Matching only the one-line form silently
#: attributes those bytes to nobody.
_MAP_LINE = re.compile(r"^\s+(\S+)\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)\s+(\S+)\s*$")
_MAP_CONT = re.compile(r"^\s+0x[0-9a-fA-F]+\s+0x([0-9a-fA-F]+)\s+(\S+)\s*$")

#: Sections the map lists but ``strip`` removes, or that are not part of the
#: loaded image. Counting them would attribute ~255 KiB of debug info (the
#: archives are built with ``-g``) to whichever object happens to carry it.
_NON_ALLOCATED = (".debug", ".zdebug", ".symtab", ".strtab", ".comment", ".note")


def _env() -> Dict[str, str]:
    """Environment for every child process.

    ``LC_ALL=C`` is mandatory: binutils translates the ``-Map`` headings, so a
    Spanish or German locale silently breaks the parser.
    """
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    return env


def _strip_size(path: Path) -> int:
    """Returns the size in bytes after stripping *path*."""
    strip = shutil.which("strip")
    if strip:
        subprocess.run([strip, str(path)], check=False, capture_output=True, env=_env())
    return path.stat().st_size


def _make_project(scratch: Path, source: str) -> Path:
    """Creates a throw-away project holding *source* and returns its directory."""
    subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "init", "hello",
         "--type", "exe", "--links", "pengu_runtime", "-q"],
        cwd=str(scratch), check=True, env=_env(),
    )
    proj = scratch / "hello"
    (proj / "src" / "main.pengu").write_text(source, encoding="utf-8")
    return proj


def _build_and_capture_link(proj: Path, map_path: Optional[Path] = None,
                            ldflags: str = "") -> Tuple[Path, List[str]]:
    """Runs ``pengu build --profile release --verbose`` and returns (binary, argv).

    The verbose log is the only honest way to learn what the toolchain linked:
    re-deriving the command here would drift from ``pengu_project.py``.
    """
    env = _env()
    map_flag = f"-Wl,-Map={map_path}" if map_path else ""
    if map_flag or ldflags:
        env["PENGU_LDFLAGS"] = " ".join(x for x in (map_flag, ldflags) if x)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "build",
         "--profile", "release", "--verbose"],
        cwd=str(proj), check=False, capture_output=True, text=True, env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"build failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    match = _LINK_LINE.search(proc.stderr + proc.stdout)
    if not match:
        raise RuntimeError("could not find the link command in --verbose output")
    argv = shlex.split(match.group(1))
    binary = proj / "build" / "hello"
    if not binary.is_file():
        raise RuntimeError(f"build produced no {binary}")
    return binary, argv


def _link_libs(argv: List[str]) -> List[str]:
    """The third-party ``-l`` names of a link command, in order, deduplicated."""
    names: List[str] = []
    for tok in argv:
        if not tok.startswith("-l") or len(tok) <= 2:
            continue
        name = tok[2:]
        if name in TAIL_LIBS or name in CORE_LIBS or name in names:
            continue
        names.append(name)
    return names


def _static_archive(name: str) -> Optional[str]:
    """Path of ``build/lib/lib<name>.a`` when the checkout ships one."""
    cand = ROOT / "build" / "lib" / f"lib{name}.a"
    return str(cand.relative_to(ROOT)) if cand.is_file() else None


def legacy_link_command(argv: List[str]) -> List[str]:
    """Rewrites a captured link command into its pre-2.0 shape.

    Section GC and the section-splitting flags come off, and the five archives
    the runtime used to drag in unconditionally go back on. The result is what
    ``pengu build --profile release`` produced before 2.0, which is the only way
    the "before" attribution in BENCHMARKS.md stays reproducible on a tree whose
    archives are now split.
    """
    cmd = [tok for tok in argv if tok not in _GC_TOKENS + _SECTION_TOKENS]
    extras = [f"-l{name}" for name in LEGACY_ARCHIVES if f"-l{name}" not in cmd]
    if "-lpengu_runtime" in cmd:
        idx = cmd.index("-lpengu_runtime") + 1
        cmd[idx:idx] = extras
    else:
        cmd.extend(extras)
    return cmd


def _parse_map(map_path: Path) -> List[Tuple[str, int]]:
    """Sums the *kept* section bytes of a GNU ld map by input archive.

    Only the body after the ``Linker script and memory map`` heading counts:
    everything before it is the ``Discarded input sections`` list, which is
    exactly the code ``--gc-sections`` removed and must not be counted. Debug
    and symbol sections are skipped too, because ``strip`` deletes them from
    the artifact the table talks about (see ``_NON_ALLOCATED``).
    """
    text = map_path.read_text(encoding="utf-8", errors="replace")
    start = text.find("Linker script and memory map")
    if start < 0:
        raise RuntimeError(f"{map_path} has no memory map section")

    totals: Dict[str, int] = {}

    def account(section: str, size: int, src: str) -> None:
        if section.startswith(_NON_ALLOCATED):
            return
        if not (src.startswith("/") or "(" in src):
            return
        if "(" in src:
            archive = src.split("(", 1)[0]
            key = Path(archive).name if archive.startswith("/") else archive
        else:
            key = Path(src).name
        totals[key] = totals.get(key, 0) + size

    pending = ""
    for line in text[start:].splitlines():
        m = _MAP_LINE.match(line)
        if m:
            account(m.group(1), int(m.group(2), 16), m.group(3))
            pending = ""
            continue
        m = _MAP_CONT.match(line)
        if m:
            account(pending, int(m.group(1), 16), m.group(2))
            pending = ""
            continue
        stripped = line.strip()
        # A lone section name introduces the address line that follows it.
        pending = stripped if stripped.startswith(".") and " " not in stripped else ""
    return sorted(totals.items(), key=lambda kv: -kv[1])


def _relink(argv: List[str], drop: Optional[str], out: Path,
            map_path: Optional[Path] = None) -> Optional[int]:
    """Re-links *argv* without archive *drop* and returns the stripped size.

    ``--unresolved-symbols=ignore-all`` is what makes the measurement possible:
    a program that genuinely needs libxml2 cannot link without it, and refusing
    to produce a binary would mean never being able to attribute the cost.
    """
    cmd: List[str] = []
    skip_next = False
    for i, tok in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if tok == "-o":
            cmd += ["-o", str(out)]
            skip_next = True
            continue
        if drop and tok == f"-l{drop}":
            continue
        # A second -Map would only confuse the parser; the caller passes none.
        if tok.startswith("-Wl,-Map="):
            continue
        if tok.startswith("-Wl,--start-group") or tok.startswith("-Wl,--end-group"):
            cmd.append(tok)
            continue
        cmd.append(tok)
    cmd.append("-Wl,--unresolved-symbols=ignore-all")
    if map_path is not None:
        cmd.append(f"-Wl,-Map={map_path}")
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True, env=_env())
    if proc.returncode != 0 or not out.is_file():
        print(f"  ! relink without -l{drop} failed: {proc.stderr.strip()[-300:]}",
              file=sys.stderr)
        return None
    return _strip_size(out)


def measure(source: Optional[str] = None, legacy: bool = False) -> Dict[str, object]:
    """Measures one ``hello_world`` link and returns its attribution report.

    The link command is captured from the toolchain, optionally rewritten into
    its pre-2.0 shape (``legacy=True``) and then re-run here one extra time per
    linked archive. The baseline is produced by the same relink path as the
    deltas, so the two numbers are always comparable.
    """
    if source is None:
        source = (ROOT / "benches" / "hello_world.pengu").read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="pengu_size_") as tmp:
        scratch = Path(tmp)
        proj = _make_project(scratch, source)
        _binary, captured = _build_and_capture_link(proj)
        argv = legacy_link_command(captured) if legacy else captured

        map_path = scratch / "link.map"
        baseline = _relink(argv, None, scratch / "baseline", map_path=map_path)
        if baseline is None:
            raise RuntimeError("the baseline link failed; run build_runtime.py first")

        archives: List[Dict[str, object]] = []
        if map_path.is_file():
            for archive, size in _parse_map(map_path):
                archives.append({"archive": archive, "bytes": size,
                                 "kiB": round(size / 1024, 1)})

        libs = _link_libs(argv)
        deltas: List[Dict[str, object]] = []
        for name in libs:
            size = _relink(argv, name, scratch / f"nolib_{name}")
            if size is None:
                continue
            deltas.append({
                "lib": name,
                "static_archive": _static_archive(name),
                "excluded_bytes": size,
                "excluded_kiB": round(size / 1024, 1),
                "delta_bytes": baseline - size,
                "delta_kiB": round((baseline - size) / 1024, 1),
            })

    return {
        "link_shape": "legacy (pre-2.0: all archives, no section GC)" if legacy
                      else "2.0 (conditional archives, section GC)",
        "baseline_bytes": baseline,
        "baseline_kiB": round(baseline / 1024, 1),
        "linked_libs": libs,
        "link_command": " ".join(argv),
        "map_attribution": archives,
        "exclusion_delta": deltas,
    }


def _print_table(report: Dict[str, object]) -> None:
    print(f"hello_world, release, stripped: "
          f"{report['baseline_bytes']} B ({report['baseline_kiB']} KiB)")
    print(f"link shape: {report['link_shape']}")
    print(f"third-party archives linked: {', '.join(report['linked_libs']) or '(none)'}")
    print()
    print(f"{'Archive':<28} {'In binary (KiB)':>16} {'Delta if dropped (KiB)':>24}")
    print("-" * 70)
    contrib = {row["archive"]: row["kiB"] for row in report["map_attribution"]}
    for row in report["exclusion_delta"]:
        name = row["static_archive"] or row["lib"]
        inbin = next((v for k, v in contrib.items()
                      if k.startswith(f"lib{row['lib']}.")), None)
        shown = f"{inbin:.1f}" if inbin is not None else "\u2014"
        print(f"{name:<28} {shown:>16} {row['delta_kiB']:>24.1f}")
    print()
    print("Archive contributions (from the link map, kept sections only):")
    for row in report["map_attribution"][:15]:
        print(f"  {row['kiB']:>9.1f} KiB  {row['archive']}")


def _sanitize(value):
    """Replaces machine-specific paths so the committed report is portable.

    The link commands are the interesting part of the report and they are full
    of absolute paths: the checkout's root and the throw-away project directory.
    Both are replaced with placeholders, because a benchmark artifact that only
    makes sense on one machine's `/tmp` is not evidence.
    """
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, str):
        value = value.replace(str(ROOT), "<repo>")
        return re.sub(r"/tmp/pengu_size_\w+", "<scratch>", value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true",
                        help="print the report as JSON instead of a table")
    parser.add_argument("--legacy", action="store_true",
                        help="measure the pre-2.0 link shape as well as the current one")
    parser.add_argument("--out", default="benches/results/binary_size_breakdown.json",
                        help="where to write the JSON report")
    parser.add_argument("--stdout-only", action="store_true",
                        help="do not write the JSON report to disk")
    args = parser.parse_args()

    report: Dict[str, object] = {
        "measured_on": date.today().isoformat(),
        "current": measure(),
    }
    if args.legacy:
        report["legacy"] = measure(legacy=True)
    report = _sanitize(report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_table(report["current"])
        if "legacy" in report:
            print()
            print("=" * 70)
            _print_table(report["legacy"])

    if not args.stdout_only:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
