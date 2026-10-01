#!/usr/bin/env python3
"""Cross-platform toolchain smoke test (used by CI on Windows/Linux/macOS).

The full pytest suite is the real gate, but it is slow and a few of its areas
skip on platforms where a helper cannot exist (leak interposer, TCC).  This
script exercises the *end-to-end* paths that must work on every OS and would
otherwise only fail deep inside the suite:

* ``pengu doctor`` reports a usable C compiler (and TCC when staged),
* ``pengu run script.pengu`` compiles, caches and executes a script,
* the second run is a cache hit, and the cached binary is executable on this
  platform (Windows needs ``app.exe``; an extension-less image never runs),
* a default run never creates ``build/`` in the working directory,
* ``pengu expand`` emits the DCE marker.

Exit code 0 on success, 1 on the first failed expectation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "pengu_project.py"

# The toolchain modules live at the checkout root, not in this directory.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from pengu_cache import script_binary_name  # noqa: E402

HELLO = '''import std.spark

weave main into int:
    calling spark.println with "smoke ok"
    return 0
'''

_failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'ok' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")
    if not ok:
        _failures.append(name)
    return ok


def run(args: list[str], cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI)] + args, cwd=str(cwd),
                          capture_output=True, text=True, env=env, timeout=600)


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="pengu_smoke_"))
    cache = work / "cache"
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache)
    env.pop("PENGU_CACHE", None)
    env.pop("PENGU_NO_TCC", None)
    env.pop("PENGU_NO_DCE", None)
    env.pop("PENGU_NO_LEAKCHECK", None)

    print(f"PenguScript smoke test ({sys.platform})")
    try:
        # --- doctor ---------------------------------------------------------
        doc = run(["doctor", "--json"], work, env)
        ok_json = doc.returncode in (0, 1) and doc.stdout.strip().startswith("{")
        check("doctor --json is machine readable", ok_json, doc.stdout[-200:] if not ok_json else "")
        info = json.loads(doc.stdout.strip().splitlines()[-1]) if ok_json else {}
        check("doctor finds a C compiler with a version",
              bool(info.get("cc")) and bool(info.get("cc_version")),
              f"{info.get('cc')} / {info.get('cc_version')}")
        blockers = [p for p in info.get("problems", []) if "tcc" not in p.lower()]
        check("doctor reports no blocking problems", not blockers, "; ".join(blockers))
        print(f"       tcc: {info.get('tcc') or 'not available (gcc fallback)'}")

        # --- run + cache ----------------------------------------------------
        script = work / "smoke.pengu"
        script.write_text(HELLO, encoding="utf-8")

        first = run(["run", str(script)], work, env)
        check("first run compiles and executes", first.returncode == 0 and "smoke ok" in first.stdout,
              (first.stderr or first.stdout)[-300:])

        cached = sorted((cache / "scripts").glob(f"*/{script_binary_name()}")) if (cache / "scripts").is_dir() else []
        check(f"cached binary is named {script_binary_name()}",
              bool(cached), f"found {[p.name for p in (cache / 'scripts').glob('*/*')]}")
        check("cached binary is directly executable",
              bool(cached) and subprocess.run([str(cached[0])], capture_output=True,
                                              text=True).returncode == 0)

        second = run(["run", str(script)], work, env)
        check("second run is a cache hit",
              second.returncode == 0 and "cached" in (second.stdout + second.stderr).lower(),
              (second.stdout + second.stderr)[-200:])

        check("a default run does not create build/", not (work / "build").exists())

        # --- expand / DCE ---------------------------------------------------
        expanded = run(["expand", str(script)], work, env)
        check("expand emits the DCE marker",
              expanded.returncode == 0 and "Dead-code elimination" in expanded.stdout,
              expanded.stderr[-200:])
        return 1 if _failures else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    rc = main()
    if _failures:
        print(f"FAILED ({len(_failures)}): {', '.join(_failures)}")
    else:
        print("smoke test passed")
    sys.exit(rc)
