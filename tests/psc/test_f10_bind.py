from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"
ENTRY = ROOT / "psc" / "tools" / "pengu_bind_entry.py"
STAGE0 = ROOT / "pengu_project.py"


def helper(tmp: Path) -> Path:
    p = tmp / "pengu-bind"
    p.write_text(
        "#!/bin/sh\nexec " + sys.executable + " " + str(ENTRY) + ' "$@"\n',
        encoding="utf-8",
    )
    p.chmod(0o755)
    return p


def env(tmp: Path, bind: Path) -> dict[str, str]:
    e = os.environ.copy()
    e["PENGU_BIND"] = str(bind)
    e["PENGU_STD_DIR"] = str(ROOT / "std")
    e["PENGU_LIB_DIR"] = str(ROOT / "build" / "lib")
    e["PENGU_INCLUDE_DIR"] = str(ROOT / "build" / "include")
    return e


def test_f10_bind_parity_and_stdout(tmp_path: Path) -> None:
    h = helper(tmp_path)
    e = env(tmp_path, h)
    for header in ("stdio.h", "stdlib.h", "string.h"):
        a = tmp_path / f"{header}.stage0.d.pengu"
        b = tmp_path / f"{header}.psc.d.pengu"
        subprocess.run([sys.executable, str(STAGE0), "bind", str(ROOT / "c_bind_stubs" / header),
                        "--output", str(a)], cwd=ROOT, check=True, capture_output=True)
        r = subprocess.run([str(PSC), "bind", str(ROOT / "c_bind_stubs" / header),
                            f"--output={b}"], cwd=ROOT, env=e, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert a.read_bytes() == b.read_bytes()
    r = subprocess.run([str(PSC), "bind", str(ROOT / "c_bind_stubs" / "stdio.h"), "--output=-"],
                       cwd=ROOT, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("## PenguScript declaration binding")


def test_f10_bind_locator_sibling(tmp_path: Path) -> None:
    h = helper(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shutil.copy2(PSC, bin_dir / "psc")
    shutil.copy2(h, bin_dir / "pengu-bind")
    r = subprocess.run([str(bin_dir / "psc"), "bind", "--print-helper"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert Path(r.stdout.strip()) == bin_dir / "pengu-bind"


def test_f10_bind_missing_helper_and_bad_flag(tmp_path: Path) -> None:
    e = env(tmp_path, tmp_path / "nope")
    r = subprocess.run([str(PSC), "bind", str(ROOT / "c_bind_stubs" / "stdio.h")],
                       cwd=ROOT, env=e, capture_output=True, text=True)
    assert r.returncode == 1
    assert "cannot find 'pengu-bind'" in r.stderr
    r = subprocess.run([str(PSC), "bind", "--definitely-unknown"], cwd=ROOT, env=e,
                       capture_output=True, text=True)
    assert r.returncode == 2


def test_f10_release_layout_and_checksums(tmp_path: Path) -> None:
    fake = tmp_path / "pengu-bind"
    fake.write_text("#!/bin/sh\necho 'pengu-bind 0.10.0'\n", encoding="utf-8")
    fake.chmod(0o755)
    dist = tmp_path / "dist"
    cmd = [sys.executable, str(ROOT / "psc" / "tools" / "release.py"),
           "--dist-dir", str(dist), "--layout", "both", "--skip-bind", "--skip-smoke",
           "--bind-helper", str(fake)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    sums = (dist / "SHA256SUMS").read_text(encoding="utf-8")
    assert "portable.tar.gz" in sums and "fhs.tar.gz" in sums
    portable = next(dist.glob("*-portable"))
    assert (portable / "bin" / "psc").is_file()
    assert (portable / "bin" / "pengu-bind").is_file()
    assert (portable / "std" / "spark.pengu").is_file()
    assert (portable / "lib" / "libpengu_runtime.a").is_file()
    fhs = next(dist.glob("*-fhs"))
    assert (fhs / "share" / "pengu" / "std" / "spark.pengu").is_file()
    assert (fhs / "include" / "pengu" / "pengu_runtime.h").is_file()
