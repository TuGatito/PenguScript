#!/usr/bin/env python3
"""Download-and-execute verification of a published release artifact.

Roadmap 2.0 / Phase 9, items 9.7 and 9.12.  A release is only "published" after
this script has proved, on the artifact itself, that:

1. the bundled ``VERSION`` matches the tag it was published under,
2. ``pengu -V`` reports that version,
3. ``pengu new exe`` + ``pengu build`` produces a binary (exit 0),
4. ``pengu run hello.pengu`` prints ``Hello, world!``.

The artifact can be exercised in either layout:

* ``--layout portable``: run it where it was unpacked (``<dir>/pengu`` +
  ``<dir>/runtime``), the layout ``make_release.py`` publishes by default;
* ``--layout fhs``: install it into a real prefix (``<prefix>/bin/pengu``,
  ``<prefix>/lib/pengu``, ``<prefix>/include/pengu``, ``<prefix>/share/pengu``)
  and run it from there **without** ``PENGU_PREFIX``, so the layout has to be
  discovered from the executable's own path (``pengu_paths.fhs_prefixes``).

For the FHS run the script also proves *why* it worked: ``libpengu_runtime.a`` is
not embedded in the frozen binary, so the archive can only come from
``<prefix>/lib/pengu``.  Hiding it must make the build fail with the documented
error; if it still succeeds, the layout was not actually being used and the run
is a false positive.

Usage::

    python scripts/verify_release_artifact.py --artifact pengu-linux-x64.tar.gz \\
        --layout portable --expected-version 1.0.0
    python scripts/verify_release_artifact.py --artifact pengu-linux-x64.tar.gz \\
        --layout fhs --expected-version 1.0.0
    # local run against a source checkout (no packaging needed):
    python scripts/verify_release_artifact.py --pengu "python pengu_project.py" \\
        --expected-version 0.16.0
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from pengu_archive import safe_extract_tar, safe_extract_zip  # noqa: E402

HELLO_SOURCE = """import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
"""

_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)")


class VerificationError(RuntimeError):
    """One of the artifact checks failed."""


def _run(cmd: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(
        [str(c) for c in cmd], cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
    )


def unpack(artifact: Path, dest: Path) -> Path:
    """Extract ``artifact`` (``.zip`` or ``.tar.gz``) into ``dest`` safely."""
    dest.mkdir(parents=True, exist_ok=True)
    name = artifact.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(artifact) as zf:
            safe_extract_zip(zf, str(dest))
    elif name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(artifact) as tar:
            safe_extract_tar(tar, str(dest))
    else:
        raise VerificationError(f"unsupported artifact type: {artifact.name}")
    return dest


def _find_binary(root: Path) -> Path:
    """Locate ``pengu``/``pengu.exe`` in an unpacked artifact."""
    names = {"pengu", "pengu.exe"}
    for candidate in sorted(root.rglob("*")):
        if candidate.is_file() and candidate.name in names:
            return candidate
    raise VerificationError(f"no pengu executable found under {root}")


def install_fhs(unpacked: Path, prefix: Path) -> Path:
    """Install an unpacked artifact into an FHS prefix; return ``bin/pengu``.

    Accepts either an already-FHS artifact (``bin``/``lib``/``include``/``share``)
    or the portable one ``make_release.py`` publishes (``pengu`` + ``runtime`` +
    ``std`` + ``VERSION``), which is the case for the GitHub release assets.
    """
    (prefix / "bin").mkdir(parents=True, exist_ok=True)
    (prefix / "lib" / "pengu").mkdir(parents=True, exist_ok=True)
    (prefix / "include" / "pengu").mkdir(parents=True, exist_ok=True)
    (prefix / "share" / "pengu").mkdir(parents=True, exist_ok=True)

    binary = _find_binary(unpacked)
    shutil.copy2(binary, prefix / "bin" / binary.name)

    def _copy_tree(src: Path, dst: Path) -> None:
        if not src.is_dir():
            return
        dst.mkdir(parents=True, exist_ok=True)
        for entry in src.iterdir():
            target = dst / entry.name
            if entry.is_dir():
                shutil.copytree(entry, target, dirs_exist_ok=True)
            else:
                shutil.copy2(entry, target)

    # Portable layout: `make_release.py` writes <dist>/runtime/{*.a, *.lib,
    # pengu_runtime.h, include/} -- note the archives sit *directly* in runtime/,
    # which is why `pengu_paths.runtime_lib_dirs()` probes `runtime` as well as
    # `runtime/lib`.
    runtime = unpacked / "runtime"
    for pattern in ("*.a", "*.lib"):
        for archive in sorted(runtime.glob(pattern)):
            shutil.copy2(archive, prefix / "lib" / "pengu" / archive.name)
    _copy_tree(runtime / "lib", prefix / "lib" / "pengu")
    _copy_tree(runtime / "include", prefix / "include" / "pengu")
    for header in ("pengu_runtime.h",):
        cand = runtime / header
        if cand.is_file():
            shutil.copy2(cand, prefix / "include" / "pengu" / header)
    _copy_tree(unpacked / "std", prefix / "share" / "pengu" / "std")
    for name in ("VERSION",):
        cand = unpacked / name
        if cand.is_file():
            shutil.copy2(cand, prefix / "share" / "pengu" / name)
    # Already-FHS layout.
    _copy_tree(unpacked / "lib" / "pengu", prefix / "lib" / "pengu")
    _copy_tree(unpacked / "include" / "pengu", prefix / "include" / "pengu")
    _copy_tree(unpacked / "share" / "pengu", prefix / "share" / "pengu")

    return prefix / "bin" / binary.name


def artifact_version(unpacked: Path, layout: str) -> Optional[str]:
    """The ``VERSION`` file shipped inside the artifact."""
    candidates = [unpacked / "VERSION", unpacked / "share" / "pengu" / "VERSION"]
    for candidate in candidates:
        if candidate.is_file():
            match = _VERSION_RE.search(candidate.read_text(encoding="utf-8"))
            if match:
                return match.group(1)
    return None


def check_version_report(pengu: Sequence[str], expected: Optional[str]) -> str:
    """``pengu -V`` must report a version, and it must be the expected one."""
    result = _run([*pengu, "-V"])
    if result.returncode != 0:
        raise VerificationError(f"pengu -V failed (rc={result.returncode}): {result.stderr}")
    reported = (result.stdout + result.stderr).strip()
    match = _VERSION_RE.search(reported)
    if not match:
        raise VerificationError(f"pengu -V printed no version: {reported!r}")
    version = match.group(1)
    if expected and version != expected:
        raise VerificationError(f"pengu -V reports {version}, expected {expected}")
    print(f"  [OK] pengu -V -> {version}")
    return version


def check_empty_project(pengu: Sequence[str], workdir: Path) -> Path:
    """`pengu new exe` + `pengu build` on a minimal project must succeed."""
    project = workdir / "verify_project"
    if project.exists():
        shutil.rmtree(project)
    created = _run([*pengu, "new", "exe", project.name], cwd=workdir)
    if created.returncode != 0:
        raise VerificationError(
            f"pengu new failed (rc={created.returncode}): {created.stdout}{created.stderr}"
        )
    source = project / "src" / "main.pengu"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(HELLO_SOURCE, encoding="utf-8")
    built = _run([*pengu, "build"], cwd=project)
    if built.returncode != 0:
        raise VerificationError(
            f"pengu build failed (rc={built.returncode}):\n{built.stdout}\n{built.stderr}"
        )
    print("  [OK] pengu build of a minimal project (rc=0)")
    return project


def check_run_hello(pengu: Sequence[str], workdir: Path) -> None:
    """`pengu run hello.pengu` must print exactly the expected greeting."""
    script = workdir / "hello.pengu"
    script.write_text(HELLO_SOURCE, encoding="utf-8")
    ran = _run([*pengu, "run", str(script)], cwd=workdir)
    output = ran.stdout + ran.stderr
    if ran.returncode != 0:
        raise VerificationError(f"pengu run failed (rc={ran.returncode}):\n{output}")
    if "Hello, world!" not in output:
        raise VerificationError(f"pengu run did not print 'Hello, world!':\n{output}")
    print("  [OK] pengu run hello.pengu -> Hello, world!")


def check_layout_is_actually_used(pengu: Sequence[str], workdir: Path, prefix: Path) -> None:
    """Negative control: without ``<prefix>/lib/pengu`` the build must fail.

    ``libpengu_runtime.a`` is not inside the frozen binary, so a build that
    succeeds with the archive hidden never used the FHS prefix.
    """
    lib_dir = prefix / "lib" / "pengu"
    if not lib_dir.is_dir():
        raise VerificationError(f"the FHS prefix has no {lib_dir}")
    hidden = prefix / "lib" / "pengu.hidden"
    lib_dir.rename(hidden)
    try:
        project = workdir / "verify_negative"
        if project.exists():
            shutil.rmtree(project)
        _run([*pengu, "new", "exe", project.name], cwd=workdir)
        source = project / "src" / "main.pengu"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(HELLO_SOURCE, encoding="utf-8")
        result = _run([*pengu, "build"], cwd=project)
        combined = result.stdout + result.stderr
        if result.returncode == 0:
            raise VerificationError(
                "the build succeeded with <prefix>/lib/pengu hidden: the FHS layout "
                "is not what made it work, so the positive run proves nothing"
            )
        if "libpengu_runtime.a" not in combined:
            raise VerificationError(
                "the build failed without naming libpengu_runtime.a; cannot attribute "
                f"the failure to the layout:\n{combined}"
            )
        print("  [OK] hiding <prefix>/lib/pengu breaks the build (layout really used)")
    finally:
        hidden.rename(lib_dir)


def check_macos_signature(binary: Path) -> None:
    """macOS, item 9.9: a *valid ad-hoc* signature, and no notarization claim.

    ``codesign --verify --strict`` must pass: without it Gatekeeper refuses the
    binary even after the quarantine attribute is removed.  ``spctl --assess`` is
    printed for the record and its failure is expected: notarization needs an
    Apple developer account (`notarytool`), which this project does not have, so
    the release documents the limitation instead of claiming `spctl` passes.
    """
    if sys.platform != "darwin":
        return
    verify = _run(["codesign", "--verify", "--strict", "--verbose=2", str(binary)])
    if verify.returncode != 0:
        raise VerificationError(
            "the macOS artifact has no valid signature (codesign --verify failed):\n"
            f"{verify.stdout}{verify.stderr}"
        )
    print("  [OK] codesign --verify --strict")

    assess = _run(["spctl", "--assess", "--type", "execute", "-vv", str(binary)])
    if assess.returncode == 0:
        print("  [OK] spctl --assess accepts the artifact (notarized)")
    else:
        print(
            "  [NOTARIZATION] spctl --assess rejected the artifact (expected: not "
            "notarized). Documented in docs/RELEASE.md §macOS; users must run "
            "'xattr -d com.apple.quarantine pengu' or build from source."
        )
        for line in (assess.stdout + assess.stderr).strip().splitlines():
            print(f"    spctl: {line}")


def verify(
    pengu: Sequence[str],
    workdir: Path,
    layout: str,
    expected_version: Optional[str],
    prefix: Optional[Path] = None,
    expect_version_file: bool = True,
    prove_layout: bool = False,
    check_signature: bool = False,
    binary: Optional[Path] = None,
) -> None:
    """Run every check; raise :class:`VerificationError` on the first failure."""
    # Every caller gets a usable scratch directory: the checks run with
    # cwd=<workdir>, and a missing one used to surface as a bare
    # FileNotFoundError from subprocess instead of a check failing.
    workdir.mkdir(parents=True, exist_ok=True)
    if expect_version_file:
        shipped = artifact_version(Path(prefix or workdir), layout)
        if shipped is None:
            raise VerificationError("the artifact ships no readable VERSION file")
        if expected_version and shipped != expected_version:
            raise VerificationError(
                f"the artifact's VERSION is {shipped}, expected {expected_version}"
            )
        print(f"  [OK] artifact VERSION -> {shipped}")
        # Without an explicit tag, the artifact's own VERSION is the expectation:
        # `pengu -V` must agree with the file that shipped next to it.
        expected_version = expected_version or shipped

    reported = check_version_report(pengu, expected_version)
    check_empty_project(pengu, workdir)
    check_run_hello(pengu, workdir)
    if prove_layout and prefix is not None:
        check_layout_is_actually_used(pengu, workdir, prefix)
    if check_signature:
        target = binary or Path(pengu[0])
        check_macos_signature(target)
    print(f"  [OK] {layout} layout verified (pengu {reported})")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--artifact", type=Path, help="release artifact to download/verify")
    source.add_argument("--pengu", help="already-available pengu command (local runs)")
    parser.add_argument("--layout", choices=["portable", "fhs"], default="portable")
    parser.add_argument("--expected-version", default=None,
                        help="version the tag promises (e.g. 1.0.0)")
    parser.add_argument("--workdir", type=Path, default=None,
                        help="scratch directory (default: a temp dir)")
    parser.add_argument("--keep", action="store_true", help="do not delete the workdir")
    parser.add_argument("--no-prove-layout", action="store_true",
                        help="skip the FHS negative control")
    parser.add_argument("--check-signature", action="store_true",
                        help="on macOS, require a valid ad-hoc signature and record "
                             "the spctl result (notarization is not performed)")
    args = parser.parse_args(argv)

    workdir = args.workdir or Path(tempfile.mkdtemp(prefix="pengu-release-verify-"))
    workdir.mkdir(parents=True, exist_ok=True)
    print(f"=== Verifying release artifact ({args.layout} layout) in {workdir} ===")

    try:
        if args.artifact:
            artifact = args.artifact.resolve()
            if not artifact.is_file():
                raise VerificationError(f"artifact not found: {artifact}")
            unpacked = unpack(artifact, workdir / "unpacked")
            if args.layout == "fhs":
                prefix_dir = workdir / "prefix"
                binary = install_fhs(unpacked, prefix_dir)
                # A real installation: no PENGU_PREFIX, discovery must come from
                # <prefix>/bin/pengu itself.
                os.environ.pop("PENGU_PREFIX", None)
                pengu = [str(binary)]
                verify(pengu, workdir / "scratch", "fhs", args.expected_version,
                       prefix=prefix_dir, expect_version_file=True,
                       prove_layout=not args.no_prove_layout,
                       check_signature=args.check_signature, binary=binary)
            else:
                binary = _find_binary(unpacked)
                pengu = [str(binary)]
                verify(pengu, workdir / "scratch", "portable", args.expected_version,
                       prefix=unpacked, expect_version_file=True,
                       check_signature=args.check_signature, binary=binary)
        else:
            # Relative path tokens are resolved against the invocation directory:
            # the checks run with cwd=<scratch>, where they would not exist.
            invocation_cwd = Path.cwd()
            resolved = []
            for token in shlex.split(args.pengu):
                candidate = os.path.join(str(invocation_cwd), token)
                looks_like_path = "/" in token or "\\" in token
                if not os.path.isabs(token) and (looks_like_path or os.path.exists(candidate)):
                    # abspath, not resolve(): resolving a venv interpreter
                    # symlink escapes the virtualenv.
                    token = os.path.abspath(candidate)
                resolved.append(token)
            pengu = resolved
            verify(pengu, workdir, "portable", args.expected_version,
                   prefix=None, expect_version_file=False,
                   check_signature=False)
    except VerificationError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        if not args.keep:
            print(f"       scratch kept for diagnosis: {workdir}", file=sys.stderr)
        return 1

    print("\n[OK] every release-artifact check passed")
    if not args.keep:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
