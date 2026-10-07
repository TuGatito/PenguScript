#!/usr/bin/env python3
"""
make_release.py - Automated Release & Packaging Script for PenguScript

This script automates:
1. Virtual environment (.venv) verification and dependency installation (PyInstaller, Lark, PyYAML, etc.).
2. Clean static compilation of the C runtime and dependencies (build_runtime.py --rebuild).
3. Assembling the release distribution directory (pengucc_build/).
   - std/ : All standard library PenguScript modules.
   - runtime/ : pengu_runtime.h, static libraries (*.a / *.lib), and dependency headers.
4. Packaging the PenguScript CLI & LSP server with PyInstaller into a standalone executable (pengu / pengu.exe).
5. Automated smoke test: verifying CLI help, project initialization, and end-to-end compilation with the standalone binary.

Usage:
    python make_release.py [--rebuild] [--skip-tests] [--dist-dir DIR]
    python make_release.py --archive pengu-linux-x64.tar.gz --dist-dir pengucc_build

Reproducibility (Roadmap 2.0 / Phase 9, item 9.8)
-------------------------------------------------
Two runs of the same commit must produce the same bytes.  This script therefore

1. pins ``SOURCE_DATE_EPOCH`` (from the environment, or from the commit time of
   ``HEAD``, which is stable for a given commit),
2. exports ``PYTHONHASHSEED=0`` and ``TZ=UTC`` for the PyInstaller run,
3. writes the distribution archive itself with sorted entries, a constant
   timestamp and normalized ownership/permissions -- the workflows used to call
   ``tar -czf``/``Compress-Archive``, which embed the current mtime and gzip
   timestamps and were therefore never reproducible.

``--archive`` is what the release workflow calls; ``--archive-only`` skips the
build so a single artifact can be re-created for comparison.
"""

import os
import re
import sys
import shutil
import subprocess
import argparse
import gzip
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
STD_DIR = ROOT_DIR / "std"
DEFAULT_DIST_DIR = ROOT_DIR / "pengucc_build"

IS_WINDOWS = sys.platform.startswith("win")

#: Fallback epoch used when neither the environment nor git can supply one.
#: It is the commit time of the repository bootstrap, not "now": a build must
#: never depend on the wall clock.
FALLBACK_SOURCE_DATE_EPOCH = 1700000000


def log_step(step_num: int, total_steps: int, msg: str):
    print(f"\n[{step_num}/{total_steps}] {msg}")
    sys.stdout.flush()


def resolve_source_date_epoch() -> int:
    """The timestamp every produced artifact is pinned to.

    Order: ``$SOURCE_DATE_EPOCH`` (the reproducible-builds convention), then the
    commit time of ``HEAD`` (stable for a given commit, so two builds of the same
    commit agree), then a constant.  Never the current time.
    """
    env = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if env.isdigit():
        return int(env)
    try:
        res = subprocess.run(["git", "log", "-1", "--format=%ct"], cwd=str(ROOT_DIR),
                             capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip().isdigit():
            return int(res.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return FALLBACK_SOURCE_DATE_EPOCH


def deterministic_build_env() -> dict:
    """Environment for PyInstaller and every child process of a release build."""
    epoch = resolve_source_date_epoch()
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = str(epoch)
    env.setdefault("TZ", "UTC")
    env["PYTHONHASHSEED"] = "0"
    # PyInstaller's own caches are keyed on mtime; a stale cache is the most
    # common source of "the same commit built twice" differing.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ.update({k: env[k] for k in ("SOURCE_DATE_EPOCH", "TZ", "PYTHONHASHSEED")})
    return env


def _normalized_mode(path: Path) -> int:
    """0o755 for anything executable, 0o644 otherwise (platform independent)."""
    if path.is_dir():
        return 0o755
    if os.name == "posix" and os.access(path, os.X_OK):
        return 0o755
    if os.name != "posix" and path.suffix.lower() in (".exe", ".dll", ".so"):
        return 0o755
    return 0o644


def _iter_tree(root: Path) -> Iterable[Path]:
    """Every file under ``root``, in a deterministic (sorted) order."""
    return sorted((p for p in root.rglob("*") if p.is_file()),
                  key=lambda p: p.relative_to(root).as_posix())


def _write_tar_gz(root: Path, out_path: Path, epoch: int) -> None:
    """Deterministic ``.tar.gz``: sorted names, constant mtime, no owner data."""
    with open(out_path, "wb") as raw:
        # mtime=0 in the gzip header: `tar -z` used to embed the build time,
        # which alone made two identical trees hash differently.
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0,
                           compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                for path in _iter_tree(root):
                    rel = path.relative_to(root).as_posix()
                    info = tar.gettarinfo(str(path), arcname=rel)
                    info.mtime = epoch
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = _normalized_mode(path)
                    with open(path, "rb") as handle:
                        tar.addfile(info, handle)


def _write_zip(root: Path, out_path: Path, epoch: int) -> None:
    """Deterministic ``.zip``: sorted names, constant date, normalized modes."""
    import time

    stamp = time.gmtime(max(epoch, 315532800))  # ZIP cannot represent < 1980
    date_time = (stamp.tm_year, stamp.tm_mon, stamp.tm_mday,
                 stamp.tm_hour, stamp.tm_min, stamp.tm_sec)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as zf:
        for path in _iter_tree(root):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = _normalized_mode(path) << 16
            info.create_system = 3  # Unix, so external_attr is meaningful
            zf.writestr(info, path.read_bytes())


def make_archive(dist_dir: Path, out_path: Path, epoch: Optional[int] = None) -> Path:
    """Write the release archive for ``dist_dir`` deterministically.

    Supports the two artifact kinds the release publishes: ``.tar.gz`` (Unix)
    and ``.zip`` (Windows).
    """
    dist_dir = dist_dir.resolve()
    if not dist_dir.is_dir():
        print(f"[ERROR] distribution directory not found: {dist_dir}")
        sys.exit(1)
    epoch = resolve_source_date_epoch() if epoch is None else epoch
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    name = out_path.name.lower()
    if name.endswith(".zip"):
        _write_zip(dist_dir, out_path, epoch)
    elif name.endswith((".tar.gz", ".tgz")):
        _write_tar_gz(dist_dir, out_path, epoch)
    else:
        print(f"[ERROR] unsupported archive type: {out_path.name}")
        sys.exit(1)
    print(f"  [ARCHIVE] {out_path} ({out_path.stat().st_size} bytes, SOURCE_DATE_EPOCH={epoch})")
    return out_path


def artifact_hashes(dist_dir: Path) -> List[Tuple[str, str]]:
    """``[(relative path, sha256)]`` for the files of a distribution directory."""
    import hashlib

    out = []
    for path in _iter_tree(dist_dir):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append((path.relative_to(dist_dir).as_posix(), digest))
    return out


def run_cmd(cmd, cwd=None, check=True, env=None, capture=False):
    """Executes a command and streams output or fails gracefully."""
    print(f"  [EXEC] {' '.join(str(c) for c in cmd)}")
    sys.stdout.flush()
    if capture:
        res = subprocess.run(cmd, cwd=cwd or str(ROOT_DIR), capture_output=True, text=True, env=env)
        if check and res.returncode != 0:
            print(f"\n[ERROR] Command failed with exit code {res.returncode}: {' '.join(str(c) for c in cmd)}\nStderr: {res.stderr}\nStdout: {res.stdout}")
            sys.exit(res.returncode)
        return res
    else:
        res = subprocess.run(cmd, cwd=cwd or str(ROOT_DIR), check=False, text=True, env=env)
        if check and res.returncode != 0:
            print(f"\n[ERROR] Command failed with exit code {res.returncode}: {' '.join(str(c) for c in cmd)}")
            sys.exit(res.returncode)
        return res


def get_venv_python() -> Path:
    """Finds or creates a virtual environment and returns its python executable."""
    venv_dir = ROOT_DIR / ".venv"
    if not venv_dir.exists():
        print("  [VENV] Creating .venv virtual environment...")
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])

    if IS_WINDOWS:
        py_exe = venv_dir / "Scripts" / "python.exe"
    else:
        py_exe = venv_dir / "bin" / "python"

    if not py_exe.exists():
        # Fallback to current sys.executable
        return Path(sys.executable)
    return py_exe


def ensure_dependencies(py_exe: Path):
    """Ensures all necessary Python dependencies are installed in the venv."""
    packages = [
        "pyinstaller>=6.0",
        "lark>=1.1.0",
        "pyyaml>=6.0",
        "pygls>=2.0.0",
        "lsprotocol>=2023.0.0",
        "pycparser>=2.21",
        "pytest>=7.0.0",
        "cmake",
    ]
    if sys.version_info < (3, 11):
        packages.append("tomli>=2.0.0")

    print("  [PIP] Checking / installing required packages...")
    cmd = [str(py_exe), "-m", "pip", "install", "--upgrade"] + packages
    run_cmd(cmd)


def ensure_external_libraries():
    """Downloads and unpacks external C libraries defined in extern_manifest.py.

    Phase 9 / item 9.1: the release path forces a (re-)download so every archive
    is hashed against its pinned digest before extraction, instead of trusting a
    directory that may predate the pin.  ``PENGU_EXTERN_FAST=1`` skips the forced
    re-download for local iteration; it is never set in CI.
    """
    from extern_manifest import download_and_extract_externs
    force = os.environ.get("PENGU_EXTERN_FAST", "").strip() != "1"
    download_and_extract_externs(ROOT_DIR / "extern", force=force)


def build_runtime(py_exe: Path, rebuild: bool = True):
    """Compiles all static external libraries and libpengu_runtime.a."""
    ensure_external_libraries()

    build_script = ROOT_DIR / "build_runtime.py"
    if not build_script.exists():
        print(f"[ERROR] build_runtime.py not found in {ROOT_DIR}")
        sys.exit(1)

    cmd = [str(py_exe), str(build_script)]
    if rebuild:
        cmd.append("--rebuild")

    run_cmd(cmd)


def assemble_distribution(dist_dir: Path, layout: str = "portable"):
    """Assembles std/ and runtime/ into dist_dir using the requested layout."""
    dist_dir.mkdir(parents=True, exist_ok=True)
    if layout == "fhs":
        _assemble_fhs(dist_dir)
    else:
        _assemble_portable(dist_dir)


def _assemble_portable(dist_dir: Path):
    """Current self-contained layout: <dist>/{std,runtime/{lib,include}}."""
    # Clean previous FHS-layout artifacts if switching layouts
    for sub in ("bin", "lib", "share"):
        p = dist_dir / sub
        if p.exists():
            shutil.rmtree(p)
    for f in ("install.sh", "uninstall.sh"):
        p = dist_dir / f
        if p.exists():
            p.unlink()

    # 1. Copy std/
    dst_std = dist_dir / "std"
    if dst_std.exists():
        shutil.rmtree(dst_std)
    shutil.copytree(STD_DIR, dst_std)
    print(f"  [STD] Copied standard library to {dst_std}")

    # VERSION -> <dist>/VERSION
    version_file = ROOT_DIR / "VERSION"
    if version_file.is_file():
        shutil.copy2(version_file, dist_dir / "VERSION")

    # 2. Setup runtime/
    dst_runtime = dist_dir / "runtime"
    dst_runtime.mkdir(parents=True, exist_ok=True)

    runtime_h = ROOT_DIR / "pengu_runtime.h"
    if runtime_h.exists():
        shutil.copy2(runtime_h, dst_runtime / "pengu_runtime.h")

    src_lib = BUILD_DIR / "lib"
    if src_lib.exists():
        for lib_file in src_lib.glob("*.*"):
            if lib_file.suffix in (".a", ".lib"):
                shutil.copy2(lib_file, dst_runtime / lib_file.name)
                print(f"  [LIB] Copied {lib_file.name} to runtime/")

    src_inc = BUILD_DIR / "include"
    dst_inc = dst_runtime / "include"
    if src_inc.exists():
        if dst_inc.exists():
            shutil.rmtree(dst_inc)
        shutil.copytree(src_inc, dst_inc)
        print(f"  [INC] Copied dependency headers to {dst_inc}")


def _assemble_fhs(dist_dir: Path):
    """FHS-compliant layout for Linux/macOS.

    Produces:
        <dist>/bin/pengu
        <dist>/lib/pengu/*.a
        <dist>/include/pengu/*.h
        <dist>/share/pengu/std/
        <dist>/share/pengu/VERSION
    """
    # Clean previous portable-layout artifacts if switching layouts
    for sub in ("bin", "lib", "include", "share", "runtime", "std"):
        p = dist_dir / sub
        if p.exists():
            shutil.rmtree(p)
    for f in ("pengu", "pengu.exe", "VERSION"):
        p = dist_dir / f
        if p.is_file():
            p.unlink()

    # std/ -> share/pengu/std/
    dst_std = dist_dir / "share" / "pengu" / "std"
    dst_std.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(STD_DIR, dst_std)
    print(f"  [STD] Copied standard library to {dst_std}")

    # VERSION -> share/pengu/VERSION
    version_file = ROOT_DIR / "VERSION"
    if version_file.is_file():
        shutil.copy2(version_file, dist_dir / "share" / "pengu" / "VERSION")

    # Static libs -> lib/pengu/
    src_lib = BUILD_DIR / "lib"
    dst_lib = dist_dir / "lib" / "pengu"
    dst_lib.mkdir(parents=True, exist_ok=True)
    if src_lib.is_dir():
        for f in src_lib.glob("*.*"):
            if f.suffix in (".a", ".lib"):
                shutil.copy2(f, dst_lib / f.name)
                print(f"  [LIB] Copied {f.name} to lib/pengu/")

    # Headers -> include/pengu/
    src_inc = BUILD_DIR / "include"
    dst_inc = dist_dir / "include" / "pengu"
    dst_inc.mkdir(parents=True, exist_ok=True)
    if src_inc.is_dir():
        for entry in src_inc.iterdir():
            target = dst_inc / entry.name
            if entry.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(entry, target)
            else:
                shutil.copy2(entry, target)
        print(f"  [INC] Copied dependency headers to {dst_inc}")

    # pengu_runtime.h -> include/pengu/pengu_runtime.h
    runtime_h = ROOT_DIR / "pengu_runtime.h"
    if runtime_h.is_file():
        shutil.copy2(runtime_h, dst_inc / "pengu_runtime.h")


def get_version() -> str:
    """Reads project version from VERSION file."""
    version_file = ROOT_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.1.0"


def ensure_tcc_for_release() -> Optional[Path]:
    """Builds or downloads TinyCC into ``build/tcc-dist`` (best effort).

    Returns the path of the ``tcc`` binary to bundle, or None when TCC is not
    available (the release then ships without it and uses gcc/clang).
    """
    dist = BUILD_DIR / "tcc-dist"
    try:
        from pengu_tcc import ensure_tcc
    except Exception:
        return None
    print("[release] staging TinyCC into", dist)
    path = ensure_tcc(str(dist), verbose=True)
    if path:
        print("[release] tcc bundled:", path)
        return Path(path)
    print("[release] WARNING: TinyCC unavailable — the release will use the system compiler")
    return None


def find_tcc_include(tcc_bin: Path) -> Optional[Path]:
    """Directory holding TCC's own headers (``stdarg.h``, ``stddef.h`` …).

    Covers the layouts the release pipeline produces:

    * ``<prefix>/bin/tcc`` + ``<prefix>/lib/tcc/include`` (``make install``),
    * ``<dir>/tcc.exe`` + ``<dir>/include`` (Windows prebuilt archive),
    * ``<dir>/tcc.exe`` with the archive unpacked to a *sibling* subtree
      (``<dir>/tcc_20221020/include``) — what the CI staging step leaves behind
      when it copies only the executable next to the archive root.

    Without this search the Windows release shipped ``tcc.exe`` with no headers
    and TCC could not compile anything (the bundle silently fell back to gcc).
    """
    direct = (tcc_bin.parent / "include",
              tcc_bin.parent.parent / "lib" / "tcc" / "include")
    for cand in direct:
        if (cand / "stdarg.h").is_file() or (cand / "stddef.h").is_file():
            return cand
    base = tcc_bin.parent
    for root, dirs, files in os.walk(base):
        depth = len(Path(root).relative_to(base).parts)
        if depth >= 4:
            dirs[:] = []
            continue
        # Never descend into a TCC source checkout (huge, and not the headers).
        dirs[:] = [d for d in dirs if "tinycc-src" not in d]
        if Path(root).name == "include" and ("stdarg.h" in files or "stddef.h" in files):
            return Path(root)
    return None


def tcc_add_binary_args(tcc_bin: Path, data_sep: str) -> List[str]:
    """PyInstaller ``--add-binary`` arguments that bundle a TCC installation.

    The destination **keeps the source file name**: on Windows the binary is
    ``tcc.exe`` and ``pengu_tcc.find_tcc()`` probes ``<bundle>/tcc/tcc.exe``.
    Hard-coding ``tcc/tcc`` shipped the file under a name the frozen toolchain
    never looks for, silently disabling TCC in Windows releases.

    The include tree (``stdarg.h``, ``stddef.h``, ``tccdefs.h`` …) travels with
    it so the bundled compiler can actually build the generated bundle.
    """
    args = [f"{tcc_bin}{data_sep}tcc/{tcc_bin.name}"]
    include = find_tcc_include(tcc_bin)
    if include is not None:
        args.append(f"{include}{data_sep}tcc/include")
    return args


def package_with_pyinstaller(py_exe: Path, dist_dir: Path, bin_subdir: str = ""):
    """Packages pengu_project.py into a standalone pengu / pengu.exe binary.

    ``bin_subdir`` (e.g. ``"bin"``) selects the FHS-layout output directory;
    the default places the binary at the root of ``dist_dir``.
    """
    output_dir = dist_dir / bin_subdir if bin_subdir else dist_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    entry_point = ROOT_DIR / "pengu_project.py"
    data_sep = ";" if IS_WINDOWS else ":"

    add_data = [
        f"{str(STD_DIR)}{data_sep}std",
        f"{str(ROOT_DIR / 'pengu_runtime.h')}{data_sep}.",
        f"{str(ROOT_DIR / 'VERSION')}{data_sep}.",
        # Stub C headers used by 'pengu bind' when preprocessing C headers.
        f"{str(ROOT_DIR / 'c_bind_stubs')}{data_sep}c_bind_stubs",
    ]

    # TinyCC is bundled so 'pengu run' has a fast compiler without any system
    # dependency (it is optional: without it the toolchain falls back to gcc).
    add_binary = []
    tcc_bin = ensure_tcc_for_release()
    if tcc_bin:
        add_binary.extend(tcc_add_binary_args(tcc_bin, data_sep))

    # Hidden imports that PyInstaller may not auto-detect
    hidden_imports = [
        "pengu_paths",
        "pygls",
        "pygls.lsp",
        "pygls.lsp.server",
        "pygls.protocol",
        "pygls.capabilities",
        "lsprotocol",
        "lsprotocol.types",
        "lsprotocol.converters",
        "cattrs",
        "attrs",
        "pycparser",
        "pycparser.c_parser",
        "pycparser.c_lexer",
        "pycparser.c_ast",
        "pycparser.plyparser",
        "pycparser.ast_transforms",
        "lark",
        "lark.parsers",
        "lark.parsers.lalr_parser",
        "pengu_bind",
        "pengu_lsp",
        "pengu_lsp.server",
        "pengu_lsp.completions",
        "pengu_lsp.hover",
        "pengu_lsp.code_actions",
        "pengu_lsp.formatting",
        "pengu_parser",
        "pengu_parser.pengu_parser",
        "pengu_parser.pengu_checker",
        "pengu_parser.pengu_codegen",
        "pengu_parser.pengu_symbols",
        "pengu_parser.pengu_types",
        "pengu_parser.pengu_errors",
        "pengu_parser.pengu_infer",
        "pengu_parser.pengu_grammar",
    ]

    # Collect all submodules for packages with many internal modules
    collect_submodules = [
        "lsprotocol",
        "pygls",
        "cattrs",
        "attrs",
    ]

    cmd = [
        str(py_exe), "-m", "PyInstaller",
        "--clean",
        "--name", "pengu",
        "--onefile",
        "--console",
        "--distpath", str(output_dir),
        "--workpath", str(BUILD_DIR / "pyinstaller_work"),
        "--specpath", str(BUILD_DIR),
        "--noconfirm",
    ]

    for item in add_data:
        cmd.extend(["--add-data", item])

    for item in add_binary:
        cmd.extend(["--add-binary", item])

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    for pkg in collect_submodules:
        cmd.extend(["--collect-submodules", pkg])

    cmd.append(str(entry_point))
    # SOURCE_DATE_EPOCH/PYTHONHASHSEED travel to PyInstaller, which embeds
    # timestamps in the CArchive and would otherwise stamp "now" into the binary.
    run_cmd(cmd, env=deterministic_build_env())


def verify_executable(dist_dir: Path, bin_subdir: str = ""):
    """Runs smoke tests against the generated standalone binary."""
    exe_name = "pengu.exe" if IS_WINDOWS else "pengu"
    exe_path = (dist_dir / bin_subdir / exe_name) if bin_subdir else (dist_dir / exe_name)

    if not exe_path.exists():
        print(f"[ERROR] Expected binary not found: {exe_path}")
        sys.exit(1)

    print(f"  [TEST 1] Verifying {exe_name} --help...")
    res = run_cmd([str(exe_path), "--help"], capture=True)
    print(res.stdout)
    assert "PenguScript" in res.stdout or "usage:" in res.stdout or "commands:" in res.stdout.lower()

    test_scratch = ROOT_DIR / "scratch" / "smoke_release_test"
    if test_scratch.exists():
        shutil.rmtree(test_scratch)
    test_scratch.mkdir(parents=True, exist_ok=True)

    print("  [TEST 2] Testing project initialization...")
    run_cmd([str(exe_path), "init", "smoke_proj", "--type", "exe", "--links", "pengu_runtime"], cwd=str(test_scratch))

    proj_dir = test_scratch / "smoke_proj"
    assert proj_dir.exists(), "smoke_proj was not created"

    # init creates a Cargo-style project whose configured entry point lives at
    # src/main.pengu, so the smoke-test source must overwrite that file (a
    # stray 'main.pengu' at the project root is ignored by 'pengu run').
    src_main = proj_dir / "src" / "main.pengu"
    root_main = proj_dir / "main.pengu"
    if root_main.exists():
        root_main.unlink()
    src_main.parent.mkdir(parents=True, exist_ok=True)
    src_main.write_text(
        """import std.spark
import std.ward

weave main into void:
    calling spark.println with "Hello from Standalone PenguScript Release!"
    calling ward.assert_eq_int with 40 + 2, 42
    calling spark.println with "Release smoke test passed!"
""",
        encoding="utf-8",
    )

    print("  [TEST 3] Testing standalone compilation and execution ('pengu run')...")
    run_res = run_cmd([str(exe_path), "run"], cwd=str(proj_dir), capture=True)
    print(run_res.stdout)
    assert "Release smoke test passed!" in run_res.stdout

    print("  [TEST 3b] Testing embedded assets ('arca')...")
    assets_smoke = proj_dir / "assets" / "smoke.txt"
    assets_smoke.write_text("Arca smoke asset OK!", encoding="utf-8")
    from pengu_assets import _asset_const_name
    cname = _asset_const_name("smoke.txt")
    src_main.write_text(
        f"""import arca
import std.spark
import std.ward

weave main into void:
    calling ward.assert_true with calling arca.has with "smoke.txt"
    calling ward.assert_true with calling arca.has with arca.{cname}
    var txt as string is calling arca.string with arca.{cname}
    calling spark.println with txt
    calling ward.assert_true with txt == "Arca smoke asset OK!"
    banish txt
    calling spark.println with "Embedded assets smoke test passed!"
""",
        encoding="utf-8",
    )
    run_res_assets = run_cmd([str(exe_path), "run"], cwd=str(proj_dir), capture=True)
    print(run_res_assets.stdout)
    assert "Embedded assets smoke test passed!" in run_res_assets.stdout

    print("  [TEST 4] Testing 'pengu doctor' inside the release bundle...")
    doctor = run_cmd([str(exe_path), "doctor"], cwd=str(test_scratch), capture=True)
    print(doctor.stdout)
    assert "PenguScript doctor" in doctor.stdout
    tcc_line = [ln for ln in doctor.stdout.splitlines() if "tcc" in ln.lower()]
    if tcc_line and "not available" not in tcc_line[0]:
        print("  [TEST 5] Verifying the bundled TCC and the script cache...")
        script = test_scratch / "release_cache.pengu"
        script.write_text(
            'import std.spark\n\nweave main into int:\n'
            '    calling spark.println with "release cache ok"\n'
            '    return 0\n',
            encoding="utf-8",
        )
        first = run_cmd([str(exe_path), "run", str(script)], cwd=str(test_scratch), capture=True)
        assert "release cache ok" in first.stdout
        second = run_cmd([str(exe_path), "run", str(script)], cwd=str(test_scratch), capture=True)
        assert "release cache ok" in second.stdout
        assert "cached" in second.stdout.lower(), "the second run should be a cache hit"
        assert not (test_scratch / "build").exists(), "a cached run must not create build/"
    else:
        print("  [TEST 5] Skipped (no TCC inside the bundle; gcc/clang fallback is in use)")

    print("  [SUCCESS] All smoke tests passed!")


def sync_extension_version() -> None:
    """Writes the VERSION value into the VS Code extension manifest.

    The extension's ``package.json`` carries its own ``version`` field, which
    used to drift from ``VERSION``; the packaged ``.vsix`` name already comes from
    ``VERSION``, so both are kept in sync here before bundling.
    """
    manifest = ROOT_DIR / "vscode-extension" / "package.json"
    if not manifest.exists():
        return
    text = manifest.read_text(encoding="utf-8")
    updated = re.sub(r'("version"\s*:\s*")[^"]*(")', rf"\g<1>{get_version()}\g<2>", text, count=1)
    if updated != text:
        manifest.write_text(updated, encoding="utf-8")
        print(f"  [VSCODE] Synced extension version -> {get_version()}")


def build_vscode_extension(dist_dir: Path):
    """Builds and packages the VS Code extension into a .vsix artifact."""
    ext_dir = ROOT_DIR / "vscode-extension"
    if not ext_dir.exists():
        print(f"  [WARN] vscode-extension directory not found at {ext_dir}")
        return

    print("  [VSCODE] Packaging VS Code extension...")
    sync_extension_version()
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"

    try:
        # Check npm
        run_cmd([npm_cmd, "--version"], capture=True)
    except Exception:
        print("  [WARN] npm not found in system PATH. Skipping automated .vsix packaging.")
        return

    # 1. npm install and compile
    print("  [VSCODE] Installing npm dependencies...")
    run_cmd([npm_cmd, "install"], cwd=str(ext_dir))

    print("  [VSCODE] Bundling extension with esbuild...")
    run_cmd([npm_cmd, "run", "bundle"], cwd=str(ext_dir))

    # 2. Package .vsix
    print("  [VSCODE] Generating .vsix package with vsce...")
    run_cmd([npx_cmd, "-y", "@vscode/vsce", "package"], cwd=str(ext_dir))

    # 3. Copy .vsix to dist_dir
    vsix_files = list(ext_dir.glob("*.vsix"))
    for vf in vsix_files:
        dest_vsix = dist_dir / vf.name
        shutil.copy2(vf, dest_vsix)
        print(f"  [VSCODE] Copied {vf.name} -> {dest_vsix}")


def generate_install_script(dist_dir: Path) -> None:
    """Writes an install.sh / uninstall.sh pair for the FHS layout."""
    version = get_version()

    install_sh = dist_dir / "install.sh"
    install_sh.write_text(
        f"""#!/bin/sh
# PenguScript {version} installer (FHS layout).
#
# Usage:
#   ./install.sh                            # install to ~/.local  (user)
#   PREFIX=/usr/local sudo ./install.sh     # system-wide
#   DESTDIR=/tmp/stage PREFIX=/usr ./install.sh   # package-manager staging
#
set -eu

PREFIX="${{PREFIX:-$HOME/.local}}"
DESTDIR="${{DESTDIR:-}}"

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${{DESTDIR}}${{PREFIX}}"

echo "Installing PenguScript {version} into $DEST"

install -d "$DEST/bin" "$DEST/lib/pengu" "$DEST/include/pengu" "$DEST/share/pengu"

# Binary
if [ -f "$SRC/bin/pengu" ]; then
    install -m 755 "$SRC/bin/pengu" "$DEST/bin/pengu"
fi

# Static libraries
if [ -d "$SRC/lib/pengu" ]; then
    for f in "$SRC"/lib/pengu/*; do
        [ -e "$f" ] || continue
        install -m 644 "$f" "$DEST/lib/pengu/$(basename "$f")"
    done
fi

# C headers
if [ -d "$SRC/include/pengu" ]; then
    cp -R "$SRC/include/pengu/." "$DEST/include/pengu/"
fi

# Standard library + VERSION
if [ -d "$SRC/share/pengu" ]; then
    cp -R "$SRC/share/pengu/." "$DEST/share/pengu/"
fi

echo
echo "Done."
case ":$PATH:" in
    *":$PREFIX/bin:"*) ;;
    *) echo "Add $PREFIX/bin to your PATH:"
       echo "    export PATH=\\"$PREFIX/bin:\\$PATH\\"" ;;
esac
echo "Then run: pengu --help"
""",
        encoding="utf-8",
    )
    install_sh.chmod(0o755)
    print(f"  [INSTALL] Wrote {install_sh}")

    uninstall_sh = dist_dir / "uninstall.sh"
    uninstall_sh.write_text(
        """#!/bin/sh
# PenguScript uninstaller (FHS layout).
set -eu

PREFIX="${PREFIX:-$HOME/.local}"
DEST="${DESTDIR:-}${PREFIX}"

rm -f  "$DEST/bin/pengu"
rm -rf "$DEST/lib/pengu"
rm -rf "$DEST/include/pengu"
rm -rf "$DEST/share/pengu"

echo "PenguScript removed from $DEST"
""",
        encoding="utf-8",
    )
    uninstall_sh.chmod(0o755)
    print(f"  [INSTALL] Wrote {uninstall_sh}")


def generate_release_readme(dist_dir: Path, layout: str = "portable"):
    """Writes the distribution guide to ``docs/README_RELEASE.md`` and ``<dist>/README.md``."""
    version = get_version()
    vsix_name = f"pengus-{version}.vsix"

    if layout == "fhs":
        body_tree = f"""\\
{dist_dir.name}/
├── bin/pengu                        # Standalone CLI + LSP server
├── lib/pengu/*.a                    # Runtime static libraries
├── include/pengu/*.h                # Runtime + dependency headers
├── share/pengu/std/                 # Standard library modules
├── share/pengu/VERSION
├── {vsix_name}     # VS Code extension
├── install.sh                       # FHS installer (PREFIX/DESTDIR aware)
└── uninstall.sh"""
        quickstart = """\\
### 1. Install

```bash
./install.sh                         # ~/.local
PREFIX=/usr/local sudo ./install.sh  # system-wide
DESTDIR=/tmp/stage PREFIX=/usr ./install.sh   # package-manager staging
```
"""
    else:
        body_tree = f"""\\
{dist_dir.name}/
├── pengu{' .exe' if IS_WINDOWS else ''}
├── {vsix_name}
├── std/
└── runtime/
    ├── pengu_runtime.h
    ├── libpengu_runtime.a
    └── include/"""
        quickstart = f"""\\
### 1. Add to PATH
Add this directory (the one holding the `pengu` binary) to your system `PATH`
environment variable. It is the `{dist_dir.name}/` directory of the unpacked
archive; the path is relative on purpose so the generated guide does not embed
the build machine's absolute layout (Phase 9, finding F9-N8).
"""

    readme_content = f"""# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

## Directory Structure

```
{body_tree}
```

---

## Quick Start

{quickstart}

### 2. Install the VS Code Extension
1. Open Visual Studio Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Click the `...` menu (Views and More Actions) in the top-right corner.
4. Select **Install from VSIX...** and choose `{dist_dir.name}/{vsix_name}` (relative to the unpacked archive).

### 3. Create a new project
```bash
pengu init my_app --type exe --links pengu_runtime
cd my_app
```

### 4. Build and Run
```bash
# Build optimized binary
pengu build --profile release

# Build and execute directly
pengu run
```

### 5. Available Commands
- `pengu init <name>` : Initializes a new project template with `pengu.toml`.
- `pengu build`        : Bundles and compiles to executable / static lib / DLL.
- `pengu run`          : Builds and runs the binary immediately.
- `pengu assets`       : Inspects (`--list`) or regenerates (`--force`) embedded project assets.
- `pengu clean`        : Cleans intermediate build artifacts.
- `pengu lsp`          : Starts the Language Server Protocol (LSP) for VS Code / Neovim.
"""
    # The generated release guide lives under docs/ (a tracked, regenerated copy)
    # and is also written into the distribution as its own README.md. It is no
    # longer written to the repository root (Phase 0 of the 1.0 roadmap (`ROADMAP_1.1.md`)).
    docs_readme = ROOT_DIR / "docs" / "README_RELEASE.md"
    docs_readme.parent.mkdir(parents=True, exist_ok=True)
    docs_readme.write_text(readme_content, encoding="utf-8")
    (dist_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print(f"  [DOCS] Generated docs/README_RELEASE.md and {dist_dir / 'README.md'}")


def main():
    parser = argparse.ArgumentParser(description="Automated Release Packager for PenguScript")
    parser.add_argument("--rebuild", action="store_true", default=True, help="Force clean rebuild of C runtime")
    parser.add_argument("--skip-tests", action="store_true", help="Skip post-packaging smoke tests")
    parser.add_argument("--dist-dir", type=str, default=str(DEFAULT_DIST_DIR), help="Target release directory")
    parser.add_argument(
        "--layout",
        choices=["portable", "fhs"],
        default="portable",
        help="Distribution layout: 'portable' (default, self-contained bundle) "
             "or 'fhs' (Linux/macOS FHS: bin/ lib/pengu include/pengu share/pengu + install.sh)",
    )
    parser.add_argument(
        "--archive",
        metavar="PATH",
        default=None,
        help="Distribution archive to write (.tar.gz or .zip), deterministically "
             "(Roadmap 2.0 / item 9.8). This is what the release workflow calls.",
    )
    parser.add_argument(
        "--archive-only",
        action="store_true",
        help="Only write --archive for --dist-dir and exit (no build, no packaging).",
    )
    parser.add_argument(
        "--print-hashes",
        action="store_true",
        help="Print the SHA-256 of every file in --dist-dir (for reproducibility checks).",
    )
    args = parser.parse_args()

    if args.archive_only:
        if not args.archive:
            print("[ERROR] --archive-only requires --archive PATH")
            sys.exit(2)
        make_archive(Path(args.dist_dir), Path(args.archive))
        if args.print_hashes:
            for rel, digest in artifact_hashes(Path(args.dist_dir).resolve()):
                print(f"  {digest}  {rel}")
        return

    if args.layout == "fhs" and IS_WINDOWS:
        print("[ERROR] --layout fhs is only supported on Linux/macOS.")
        sys.exit(1)

    dist_dir = Path(args.dist_dir).resolve()
    bin_subdir = "bin" if args.layout == "fhs" else ""

    total_steps = 6 if args.skip_tests else 7

    print("================================================================")
    print("  PenguScript Automated Release & PyInstaller Packaging Script")
    print("================================================================")
    print(f"  SOURCE_DATE_EPOCH={resolve_source_date_epoch()} (reproducible packaging)")

    # Step 1: Virtual Environment
    log_step(1, total_steps, "Verifying virtual environment (.venv)...")
    py_exe = get_venv_python()
    print(f"  [PYTHON] Using {py_exe}")

    # Step 2: Dependencies
    log_step(2, total_steps, "Installing / verifying build dependencies (PyInstaller, Lark, PyYAML)...")
    ensure_dependencies(py_exe)

    # Step 3: Runtime Static Compilation
    log_step(3, total_steps, "Compiling static runtime libraries (build_runtime.py)...")
    build_runtime(py_exe, rebuild=args.rebuild)

    # Step 4: Assemble distribution folder
    log_step(4, total_steps, f"Assembling distribution assets ({args.layout} layout) in {dist_dir}...")
    assemble_distribution(dist_dir, layout=args.layout)

    # Step 5: Package VS Code extension
    log_step(5, total_steps, "Building and packaging VS Code Extension (.vsix)...")
    build_vscode_extension(dist_dir)

    # Step 6: Package binary with PyInstaller
    log_step(6, total_steps, "Packaging standalone CLI executable with PyInstaller...")
    package_with_pyinstaller(py_exe, dist_dir, bin_subdir=bin_subdir)

    if args.layout == "fhs":
        generate_install_script(dist_dir)

    generate_release_readme(dist_dir, layout=args.layout)

    # Step 7: Smoke Tests
    if not args.skip_tests:
        log_step(7, total_steps, "Running release verification & smoke tests...")
        verify_executable(dist_dir, bin_subdir=bin_subdir)

    exe_name = "pengu.exe" if IS_WINDOWS else "pengu"
    vsix_name = f"pengus-{get_version()}.vsix"
    exe_rel = (Path(bin_subdir) / exe_name) if bin_subdir else Path(exe_name)
    print("\n================================================================")
    print(f"  SUCCESS! PenguScript release packaged at: {dist_dir}")
    print(f"  Executable: {dist_dir / exe_rel}")
    print(f"  VS Code Extension: {dist_dir / vsix_name}")
    print("================================================================\n")


if __name__ == "__main__":
    main()
