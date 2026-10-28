#!/usr/bin/env python3
"""Package PSC + pengu-bind into portable/FHS artifacts (F10).

Build-time helper only: the produced tree never needs Python.  Uses TOML for
release metadata and a plain-text SHA256SUMS file (no YAML/JSON).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import gzip
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSC = ROOT / "psc" / "build" / "psc"
BUILD_INCLUDE = ROOT / "build" / "include"
BUILD_LIB = ROOT / "build" / "lib"
STD = ROOT / "std"
STUBS = ROOT / "c_bind_stubs"
ENTRY = ROOT / "tools" / "pengu-bind-src" / "pengu_bind_entry.py"
BIND_HELPER = ROOT / "build" / ("pengu-bind.exe" if os.name == "nt" else "pengu-bind")
EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1700000000"))


def target_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        machine = "x86_64"
    elif machine in ("arm64", "aarch64"):
        machine = "arm64"
    return f"{system}-{machine}"


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def version() -> str:
    out = subprocess.run([str(PSC), "version"], capture_output=True, text=True, check=True).stdout
    m = re.search(r"psc\s+([0-9]+\.[0-9]+\.[0-9]+)", out)
    return m.group(1) if m else "0.0.0"


def bind_version() -> str:
    text = ENTRY.read_text(encoding="utf-8")
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "0.0.0"


def copy_tree(src: Path, dst: Path, exclude: tuple[str, ...] = ("__pycache__", ".pyc")) -> None:
    for item in sorted(src.rglob("*")):
        if any(part in exclude for part in item.parts):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def build_helper(out: Path) -> Path:
    if out.is_file():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    work = ROOT / "build" / "pyinstaller-bind"
    spec = ROOT / "build"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--clean", "--onefile",
        "--name", "pengu-bind", "--distpath", str(out.parent),
        "--workpath", str(work), "--specpath", str(spec),
        "--paths", str(ROOT), "--add-data", f"{STUBS}:c_bind_stubs",
        "--hidden-import", "pengu_bind", "--hidden-import", "pycparser",
        "--collect-submodules", "pycparser", str(ENTRY),
    ]
    subprocess.run(cmd, check=True)
    return out


TARGET = target_name()


def assemble(root: Path, layout: str) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    if layout == "portable":
        bindir = root / "bin"
        libdir = root / "lib"
        incdir = root / "include"
        stddir = root / "std"
        stubdir = root / "c_bind_stubs"
        docdir = root / "share" / "doc" / "pengu"
    else:
        bindir = root / "bin"
        libdir = root / "lib" / "pengu"
        incdir = root / "include" / "pengu"
        stddir = root / "share" / "pengu" / "std"
        stubdir = root / "share" / "pengu" / "c_bind_stubs"
        docdir = root / "share" / "doc" / "pengu"
    for d in (bindir, libdir, incdir, stddir, stubdir, docdir):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PSC, bindir / "psc")
    (bindir / "psc").chmod(0o755)
    bind_name = "pengu-bind.exe" if TARGET.startswith("windows") else "pengu-bind"
    shutil.copy2(BIND_HELPER, bindir / bind_name)
    (bindir / bind_name).chmod(0o755)
    for lib in sorted(BUILD_LIB.glob("*.a")):
        shutil.copy2(lib, libdir / lib.name)
    copy_tree(BUILD_INCLUDE, incdir)
    copy_tree(STD, stddir)
    copy_tree(STUBS, stubdir)
    for name in ("README.md", "CHANGELOG.md", "LICENSE", "LICENSE.md"):
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, docdir / name)
    (root / "VERSION").write_text(version() + "\n", encoding="utf-8")
    (root / "release.toml").write_text(
        "[release]\n"
        f'version = "{version()}"\n'
        f'bind_version = "{bind_version()}"\n'
        f'layout = "{layout}"\n'
        f'target = "{TARGET}"\n',
        encoding="utf-8",
    )
    log(f"assembled {layout}: {root}")


def normalize_tar(path: Path, root: Path) -> None:
    def reset(ti: tarfile.TarInfo) -> tarfile.TarInfo:
        ti.uid = 0
        ti.gid = 0
        ti.uname = "root"
        ti.gname = "root"
        ti.mtime = EPOCH
        return ti
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=EPOCH) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
                for item in sorted(root.rglob("*")):
                    tf.add(item, arcname=str(item.relative_to(root.parent)), filter=reset)


def make_artifacts(dist: Path, version_s: str, target: str, layouts: list[str]) -> list[Path]:
    made: list[Path] = []
    for layout in layouts:
        root = dist / f"pengu-{version_s}-{target}-{layout}"
        assemble(root, layout)
        if target.startswith("windows"):
            arc = dist / f"pengu-{version_s}-{target}-{layout}.zip"
            with zipfile.ZipFile(arc, "w", zipfile.ZIP_DEFLATED) as zf:
                for item in sorted(root.rglob("*")):
                    if item.is_file():
                        zi = zipfile.ZipInfo(str(item.relative_to(root.parent)), (1980, 1, 1, 0, 0, 0))
                        zi.external_attr = (item.stat().st_mode & 0o777) << 16
                        zi.compress_type = zipfile.ZIP_DEFLATED
                        zf.writestr(zi, item.read_bytes())
        else:
            arc = dist / f"pengu-{version_s}-{target}-{layout}.tar.gz"
            normalize_tar(arc, root)
        made.append(arc)
    return made


def smoke(root: Path, target: str) -> None:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(ROOT / "build" / "release-home"),
        "PENGU_HOME": str(root),
        "SOURCE_DATE_EPOCH": str(EPOCH),
    }
    psc = root / "bin" / ("psc.exe" if target.startswith("windows") else "psc")
    log("smoke: " + subprocess.run([str(psc), "version"], env=env, capture_output=True, text=True, check=True).stdout.strip())
    helper = root / "bin" / ("pengu-bind.exe" if target.startswith("windows") else "pengu-bind")
    subprocess.run([str(helper), "--version"], env=env, check=True)
    subprocess.run([str(psc), "bind", "--helper-version"], env=env, check=True, capture_output=True)
    with tempfile.TemporaryDirectory(prefix="psc-release-smoke-") as td:
        proj = Path(td) / "app"
        subprocess.run([str(psc), "init", "app"], cwd=td, env=env, check=True, capture_output=True)
        r = subprocess.run([str(psc), "build"], cwd=proj, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"release smoke build failed:\n{r.stderr}\n{r.stdout}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Package PSC + pengu-bind (F10)")
    ap.add_argument("--dist-dir", default=str(ROOT / "dist"))
    ap.add_argument("--version", default="")
    ap.add_argument("--target", default=target_name())
    ap.add_argument("--layout", choices=["portable", "fhs", "both"], default="both")
    ap.add_argument("--skip-bind", action="store_true")
    ap.add_argument("--bind-helper", default="", help="Use this pengu-bind instead of building one")
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()
    if not PSC.is_file():
        raise SystemExit(f"missing {PSC}; build PSC first")
    global BIND_HELPER
    if args.bind_helper:
        BIND_HELPER = Path(args.bind_helper).resolve()
    if not args.skip_bind:
        build_helper(BIND_HELPER)
    if not BIND_HELPER.is_file():
        raise SystemExit(f"missing {BIND_HELPER}; build the helper first")
    global TARGET
    TARGET = args.target
    layouts = ["portable", "fhs"] if args.layout == "both" else [args.layout]
    v = args.version or version()
    dist = Path(args.dist_dir)
    dist.mkdir(parents=True, exist_ok=True)
    arcs = make_artifacts(dist, v, args.target, layouts)
    sums = dist / "SHA256SUMS"
    with sums.open("w", encoding="utf-8", newline="\n") as f:
        for arc in arcs:
            f.write(f"{sha256(arc)}  {arc.name}\n")
    if not args.skip_smoke:
        for layout in layouts:
            smoke(dist / f"pengu-{v}-{args.target}-{layout}", args.target)
    log(f"release ready: {dist} ({len(arcs)} artifact(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
