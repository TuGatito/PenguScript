#!/usr/bin/env python3
"""benches/run_bench.py — reproducible PenguScript vs C/Rust/Zig benchmarks.

Roadmap 6.1.  Measures, for each program in ``benches/``:

* **build** time (PenguScript only: the toolchain's own cost),
* **run** time (best of N, after one warm-up),
* **artifact size** (stripped when ``strip`` is available).

Baselines are compiled only when the toolchain is present, so the harness never
fails on a machine without Zig or Rust — it reports what it could measure and
says what it skipped.

Usage::

    python benches/run_bench.py                # best of 3, human table
    python benches/run_bench.py --repeat 5
    python benches/run_bench.py --csv out.csv  # machine-readable
    python benches/run_bench.py --only fib_40  # a single program

The output is deliberately honest: a missing toolchain is reported as
``skipped``, never as a win.
"""

from __future__ import annotations

import argparse
import csv
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))

# name -> (pengu source, c source, rust source, zig source)
CASES = {
    "hello_world": ("hello_world.pengu", "c/hello_world.c", "rust/hello_world.rs", "zig/hello_world.zig"),
    "fib_40": ("fib_40.pengu", "c/fib_40.c", "rust/fib_40.rs", "zig/fib_40.zig"),
    "string_ops": ("string_ops.pengu", "c/string_ops.c", "rust/string_ops.rs", "zig/string_ops.zig"),
    "list_ops": ("list_ops.pengu", "c/list_ops.c", None, None),
}


def _which(*names: str) -> Optional[str]:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def _exe(directory: Path, name: str) -> Path:
    return directory / (name + (".exe" if os.name == "nt" else ""))


def _strip(path: Path) -> None:
    strip = _which("strip")
    if strip and os.name != "nt":
        subprocess.run([strip, str(path)], capture_output=True)


def _timed_run(exe: Path, repeat: int, cwd: Optional[Path] = None) -> Optional[float]:
    """Best-of-N wall time in seconds; None when the program could not run."""
    try:
        subprocess.run([str(exe)], capture_output=True, timeout=600, cwd=str(cwd or REPO))
    except Exception:
        return None
    best: Optional[float] = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        try:
            res = subprocess.run([str(exe)], capture_output=True, timeout=600, cwd=str(cwd or REPO))
        except Exception:
            return None
        elapsed = time.perf_counter() - t0
        if res.returncode < 0:      # killed by a signal
            return None
        best = elapsed if best is None else min(best, elapsed)
    return best


def bench_pengu(source: Path, workdir: Path, repeat: int) -> Dict[str, object]:
    from pengu_project import ProjectConfig, build_project

    project = workdir / "pengu"
    (project / "src").mkdir(parents=True, exist_ok=True)
    (project / "src" / "main.pengu").write_text(source.read_text(encoding="utf-8"),
                                                encoding="utf-8")
    from pengu_paths import runtime_lib_dirs, runtime_include_dirs

    lib_dirs = [str(p) for p in runtime_lib_dirs()]
    inc_dirs = [str(p) for p in runtime_include_dirs()]
    manifest = (
        f'[project]\nname = "{source.stem}"\nentry = "src/main.pengu"\n\n'
        f"[build]\nprofile = \"release\"\n"
        f"lib_dirs = {lib_dirs!r}\ninclude_dirs = {inc_dirs!r}\n"
        f'links = ["pengu_runtime"]\n'
    ).replace("'", '"')
    (project / "pengu.toml").write_text(manifest, encoding="utf-8")

    t0 = time.perf_counter()
    build_project(config_path=str(project), profile="release")
    build_time = time.perf_counter() - t0

    exe = project / "build" / source.stem
    if os.name == "nt":
        exe = exe.with_suffix(".exe")
    if not exe.is_file():
        return {"status": "build-failed"}
    _strip(exe)
    return {
        "status": "ok",
        "build_s": build_time,
        "run_s": _timed_run(exe, repeat),
        "size": exe.stat().st_size,
    }


def bench_c(source: Path, workdir: Path, repeat: int, cc: str) -> Dict[str, object]:
    out = _exe(workdir, "c_" + source.stem)
    res = subprocess.run([cc, "-O3", "-o", str(out), str(source)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "build-failed", "detail": res.stderr.splitlines()[:2]}
    _strip(out)
    return {"status": "ok", "run_s": _timed_run(out, repeat), "size": out.stat().st_size}


def bench_rust(source: Path, workdir: Path, repeat: int, rustc: str) -> Dict[str, object]:
    out = _exe(workdir, "rs_" + source.stem)
    res = subprocess.run([rustc, "-O", "-o", str(out), str(source)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "build-failed", "detail": res.stderr.splitlines()[:2]}
    _strip(out)
    return {"status": "ok", "run_s": _timed_run(out, repeat), "size": out.stat().st_size}


def bench_zig(source: Path, workdir: Path, repeat: int, zig: str) -> Dict[str, object]:
    out = _exe(workdir, "zig_" + source.stem)
    res = subprocess.run([zig, "build-exe", "-OReleaseFast", "-femit-bin=" + str(out),
                          str(source)], capture_output=True, text=True, cwd=str(workdir))
    if res.returncode != 0 or not out.is_file():
        return {"status": "build-failed", "detail": res.stderr.splitlines()[:2]}
    _strip(out)
    return {"status": "ok", "run_s": _timed_run(out, repeat), "size": out.stat().st_size}


def _fmt(value: Optional[float], unit: str = "s", nd: int = 3) -> str:
    if value is None:
        return "n/a"
    if unit == "s" and value < 1:
        return f"{value * 1000:.0f} ms"
    return f"{value:.{nd}f} {unit}"


def _fmt_size(value: Optional[int]) -> str:
    if value is None:
        return "n/a"
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value / (1024 * 1024):.2f} MiB"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeat", type=int, default=3, help="runs per measurement (best kept)")
    ap.add_argument("--csv", default=None, help="write raw results to this CSV")
    ap.add_argument("--only", default=None, help="run a single case by name")
    args = ap.parse_args()

    cc = _which("gcc", "clang", "cc")
    rustc = _which("rustc")
    zig = _which("zig")

    missing = [n for n, t in (("C", cc), ("Rust", rustc), ("Zig", zig)) if not t]
    if missing:
        print(f"# baselines skipped (toolchain not found): {', '.join(missing)}", file=sys.stderr)

    cases = {k: v for k, v in CASES.items() if not args.only or k == args.only}
    rows: List[Dict[str, object]] = []

    for name, (pengu_src, c_src, rs_src, zig_src) in cases.items():
        with tempfile.TemporaryDirectory(prefix=f"pengu_bench_{name}_") as tmp:
            work = Path(tmp)
            row: Dict[str, object] = {"case": name}
            print(f"\n== {name} ==")

            pr = bench_pengu(HERE / pengu_src, work, args.repeat)
            row.update({f"pengu_{k}": v for k, v in pr.items()})
            print(f"  pengu  build {_fmt(pr.get('build_s')):>9}   "
                  f"run {_fmt(pr.get('run_s')):>9}   size {_fmt_size(pr.get('size'))}")

            if cc and c_src:
                cr = bench_c(HERE / c_src, work, args.repeat, cc)
                row.update({f"c_{k}": v for k, v in cr.items()})
                ratio = ""
                if pr.get("run_s") and cr.get("run_s"):
                    ratio = f"   ({pr['run_s'] / cr['run_s']:.2f}x C)"
                print(f"  c -O3        {'':>9}   run {_fmt(cr.get('run_s')):>9}   "
                      f"size {_fmt_size(cr.get('size'))}{ratio}")

            if rustc and rs_src:
                rr = bench_rust(HERE / rs_src, work, args.repeat, rustc)
                row.update({f"rust_{k}": v for k, v in rr.items()})
                print(f"  rust -O      {'':>9}   run {_fmt(rr.get('run_s')):>9}   "
                      f"size {_fmt_size(rr.get('size'))}")

            if zig and zig_src:
                zr = bench_zig(HERE / zig_src, work, args.repeat, zig)
                row.update({f"zig_{k}": v for k, v in zr.items()})
                print(f"  zig RelFast  {'':>9}   run {_fmt(zr.get('run_s')):>9}   "
                      f"size {_fmt_size(zr.get('size'))}")

            rows.append(row)

    print("\n# environment")
    print(f"#   platform : {platform.platform()}")
    print(f"#   machine  : {platform.machine()} / {platform.processor() or 'unknown'}")
    print(f"#   python   : {platform.python_version()}")
    if cc:
        ver = subprocess.run([cc, "--version"], capture_output=True, text=True).stdout.splitlines()
        print(f"#   cc       : {ver[0] if ver else cc}")

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted({k for r in rows for k in r})
        with open(out, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n# wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
