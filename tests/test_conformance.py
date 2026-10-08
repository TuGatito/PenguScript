#!/usr/bin/env python3
"""Batch conformance runner.

A conformance **case** is a ``.pengu`` file under ``tests/conformance/`` that has
a sibling ``.expected`` file::

    tests/conformance/_smoke/hello.pengu      the case (exactly one `test` block)
    tests/conformance/_smoke/hello.expected   the stdout it must produce
    tests/conformance/_smoke/hello.exit       the exit code it must produce (default 0)

A ``.pengu`` file with **no** sibling ``.expected`` is a support module: it is
compiled into the bundle (so cases can share helpers) but is not itself a case.

The contract, and why it is shaped this way
-------------------------------------------
Every case is compiled into **one** binary. Compiling ~350 separate programs is
what makes the old suite take 34 minutes (``tests/_inventory.md`` §10); building
one binary and then spawning it per case is the only shape that reaches the
per-test budget.

A process yields exactly one stdout and one exit code, so judging N cases
separately would be impossible from a single run. That is why the generated
harness grew ``--list`` and ``--only-index N`` (``pengu_codegen/tests_gen.py``):
the binary is compiled once and then *re-executed* once per case. Re-spawning an
already-linked image costs ~5 ms, against seconds to recompile -- measured, see
``_inventory.md`` §9.2. It is also the only portable option: ``fork()`` does not
exist on Windows.

Case ids
--------
The id of a case is its path relative to ``tests/conformance/`` without the
``.pengu`` suffix, and the case's ``test`` block **must be named exactly that**::

    test "_smoke/hello":

The runner reads the compiled binary's own test list and maps name -> index, so a
name that does not match its path is a loud failure and never a silent mix-up
between two cases. Names are selected by index, not by name, because a corpus of
5000 cases repeats names like "basic" constantly.

Environment
-----------
``PENGU_TEST_FILTER``   regex; only case ids matching it are executed. The bundle
                        still contains every case, so filtering never recompiles.
``PENGU_TEST_CC``       compiler to link the bundle with. Defaults to TCC when
                        one is staged (``pengu_tcc.find_tcc()``), else gcc/clang/cc.
``PENGU_TEST_JSON_FILE``write one JSON object per case to this path (JSONL).
``PENGU_TEST_TIMEOUT``  per-case timeout in seconds (default 300).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.conftest import (  # noqa: E402
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    HAVE_CC,
    HAVE_RUNTIME,
    SANITIZERS_ACTIVE,
    runtime_link_flags,
    runtime_tail_flags,
)

CONFORMANCE_DIR = Path(__file__).resolve().parent / "conformance"
MANIFEST_PATH = CONFORMANCE_DIR / "_manifest.json"
ENTRY_NAME = "_conformance_entry.pengu"

#: The single manifest key that holds documentation instead of a case.
#:
#: Deliberately ONE reserved name rather than "any key starting with `_`": the
#: corpus's own smoke directory is `_smoke/`, so a prefix rule would have
#: silently swallowed every `_smoke/*` entry and made their `platforms`
#: declarations inert -- the entries would look present in the file and be
#: absent at runtime. `test_manifest_has_no_stale_entries` now catches both a
#: stale case entry and a case that collides with this reserved name.
RESERVED_MANIFEST_KEYS = frozenset({"_meta"})

PENGU_SUFFIX = ".pengu"
EXPECTED_SUFFIX = ".expected"
EXIT_SUFFIX = ".exit"
DEFAULT_EXIT = 0
DEFAULT_TIMEOUT = 300


# --------------------------------------------------------------------------
# Platform + manifest
# --------------------------------------------------------------------------


def current_platform() -> str:
    """``linux`` / ``macos`` / ``windows``, the vocabulary used by the manifest."""
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return "linux"


def _load_manifest() -> Dict[str, Dict[str, Any]]:
    """Reads ``_manifest.json``; ``_meta`` is documentation, every other key a case."""
    if not MANIFEST_PATH.is_file():
        return {}
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AssertionError(f"{MANIFEST_PATH.name} must be a JSON object")
    return {k: v for k, v in raw.items() if k not in RESERVED_MANIFEST_KEYS}


MANIFEST = _load_manifest()


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One conformance case and the files that describe it."""

    case_id: str
    source: Path
    expected: Path
    exit_file: Path
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def expected_stdout(self) -> str:
        return _normalise(self.expected.read_text(encoding="utf-8"))

    @property
    def expected_exit(self) -> int:
        if not self.exit_file.is_file():
            return DEFAULT_EXIT
        text = self.exit_file.read_text(encoding="utf-8").strip()
        return DEFAULT_EXIT if not text else int(text)

    @property
    def profiles(self) -> List[str]:
        """Build profiles this case must pass in. Defaults to debug alone.

        A case may legitimately need more than one: the ``test_std_*`` programs were
        asserted in *both* debug (``-ftrapv``, bounds checks) and release (``-O3
        -fwrapv``), because optimisation is what exposes a different class of
        undefined behaviour. Migrating such a program to a single-profile case
        would quietly drop that coverage, so the profile is declared per case
        rather than assumed.
        """
        profiles = self.meta.get("profiles") or ["debug"]
        return [str(p) for p in profiles]

    @property
    def skip_reason(self) -> Optional[str]:
        """Non-None when the manifest says this case cannot run here.

        Two reasons are modelled, both declared rather than coded into the test:
        the platform it is meaningful on, and a known sanitizer finding. The second
        exists because the sanitizer workflow runs `pytest tests` -- the whole
        suite, corpus included -- so a program whose bug is only visible under ASan
        must be able to say so, exactly as the per-program test it replaced did.
        """
        platforms = self.meta.get("platforms")
        if platforms and current_platform() not in platforms:
            return (f"case is {platforms}-only, running on {current_platform()} "
                    f"(declared in {MANIFEST_PATH.name})")
        if self.meta.get("skip_under_sanitizers") and SANITIZERS_ACTIVE:
            return ("known sanitizer finding, declared in "
                    f"{MANIFEST_PATH.name} (skip_under_sanitizers)")
        return None


def discover_cases() -> List[Case]:
    """Every case under ``tests/conformance``, sorted by id (stable order)."""
    found: List[Case] = []
    for source in sorted(CONFORMANCE_DIR.rglob(f"*{PENGU_SUFFIX}")):
        expected = source.with_suffix(EXPECTED_SUFFIX)
        if not expected.is_file():
            continue  # support module, not a case
        case_id = source.relative_to(CONFORMANCE_DIR).with_suffix("").as_posix()
        found.append(
            Case(
                case_id=case_id,
                source=source,
                expected=expected,
                exit_file=source.with_suffix(EXIT_SUFFIX),
                meta=MANIFEST.get(case_id, {}),
            )
        )
    return found


def _selected_cases() -> List[Case]:
    """The cases this run will execute (filter applied, platform skips kept)."""
    cases = discover_cases()
    pattern = os.environ.get("PENGU_TEST_FILTER", "").strip()
    if pattern:
        rx = re.compile(pattern)
        cases = [c for c in cases if rx.search(c.case_id)]
    return cases


# --------------------------------------------------------------------------
# Grouping: one bundle per collision-free set of cases
# --------------------------------------------------------------------------
#
# A bundle is ONE compilation unit, and PenguScript resolves the symbols of its
# modules in a single namespace. Two cases that both declare a top-level `Point`
# therefore cannot share a bundle at all -- the build fails with
# "Omen variant name 'Point' of omen 'Shape' collides with the top-level symbol
# 'Point'", which names neither the cases nor the fix.
#
# Measured on the first 56-case corpus: 7 colliding names, and the failure mode is
# all-or-nothing -- one collision makes EVERY case unrunnable.
#
# The alternative would be to force every case author to prefix every top-level
# name for the lifetime of the corpus. Grouping costs a handful of extra compiles
# and keeps cases readable, which matters much more at 5000 cases than the
# difference between 1 and N compiles.

#: Top-level declarations that introduce a name visible to the whole bundle.
_DECL_RE = re.compile(
    r"^(weave|omen|rune|concept|alias|seal|const|var|let|static|echo|declare"
    r"|enchanting|bind)\s+([A-Za-z_][A-Za-z0-9_]*)"
)
#: The first identifier of an indented line, i.e. an omen variant:
#: `omen Shape:` / `    Point` / `    Circle with r as int`.
_VARIANT_RE = re.compile(r"^[ \t]+([A-Za-z_][A-Za-z0-9_]*)")


def case_symbols(path: Path) -> set:
    """Top-level (and omen-variant) names a case adds to the shared namespace.

    Omen variants count because they are promoted to bundle-level symbols: the
    collision that first broke the corpus was between a *variant* named `Point`
    and an unrelated case's `rune Point`.
    """
    symbols = set()
    in_omen = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _DECL_RE.match(line)
        if match:
            symbols.add(match.group(2))
            in_omen = match.group(1) == "omen"
            continue
        if line[:1] in (" ", "\t"):
            if in_omen:
                variant = _VARIANT_RE.match(line)
                if variant:
                    symbols.add(variant.group(1))
        else:
            in_omen = False
    return symbols


#: `import a.b` / `import a.b as c` inside a module.
_IMPORT_LINE_RE = re.compile(
    r"^\s*import\s+([A-Za-z_][A-Za-z0-9_.]*)\s*(?:as\s+\w+)?\s*$", re.M
)

_IMPORT_CLOSURE_CACHE: Dict[str, frozenset] = {}


def _resolve_module(token: str, case: Path) -> Optional[Path]:
    """Maps an import token to the file it names, or None when it does not exist."""
    dotted = token.split(".")
    if dotted[0] == "std":
        candidate = REPO / "std" / Path(*dotted[1:]).with_suffix(".pengu")
        return candidate if candidate.is_file() else None
    for base in (case.parent, CONFORMANCE_DIR):
        candidate = base / Path(*dotted).with_suffix(".pengu")
        if candidate.is_file():
            return candidate
    return None


def imported_symbols(path: Path) -> set:
    """Every symbol the modules ``path`` imports bring into the bundle, transitively.

    This is the half of the constraint that is easy to miss, and missing it cost a
    real debugging session. Two cases declaring the same name is the obvious half.
    The subtle half: `std/scrolls.pengu` declares a non-generic `count`, so a case
    that declares its own generic `count` cannot share a bundle with a case that
    imports `std.scrolls` -- even though neither case names the other. The failure
    surfaces as ``Could not infer type parameter(s) T for generic function 'count'``
    pointing at a line in a file that is not involved, and it depends on import
    order, which is why grouping by declared names alone looked correct and was not.
    """
    key = str(path)
    cached = _IMPORT_CLOSURE_CACHE.get(key)
    if cached is not None:
        return set(cached)

    symbols: set = set()
    seen: set = set()
    queue = [path]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            text = current.read_text(encoding="utf-8")
        except OSError:
            continue
        if current != path:
            symbols |= case_symbols(current)
        for token in _IMPORT_LINE_RE.findall(text):
            resolved = _resolve_module(token, current)
            if resolved is not None and resolved not in seen:
                queue.append(resolved)

    _IMPORT_CLOSURE_CACHE[key] = frozenset(symbols)
    return symbols


def case_scope(case: Case) -> set:
    """Everything a case contributes to the bundle's namespace: its own + imports'."""
    return case_symbols(case.source) | imported_symbols(case.source)


def _conflicts(a: Case, b: Case) -> bool:
    """True when the two cases cannot share a bundle.

    A conflict is a name one case *declares* that the other's scope also provides.
    Two cases that merely both import `std.spark` do not conflict: that name comes
    from one shared module, not from two competing definitions, and treating it as
    a conflict would put every case in its own group.
    """
    own_a, own_b = case_symbols(a.source), case_symbols(b.source)
    if own_a & own_b:
        return True
    return bool(own_a & case_scope(b)) or bool(own_b & case_scope(a))


def group_cases(cases: List[Case]) -> List[List[Case]]:
    """Split cases into groups that cannot collide. Deterministic (greedy, sorted).

    Greedy first-fit over cases sorted by id: each case joins the earliest group it
    does not conflict with, else opens a new group. Deterministic, so the grouping
    -- and therefore the number of compiles -- does not move between runs.
    """
    groups: List[List[Case]] = []
    for case in sorted(cases, key=lambda c: c.case_id):
        for group in groups:
            if not any(_conflicts(case, member) for member in group):
                group.append(case)
                break
        else:
            groups.append([case])
    return groups


def symbol_collisions(cases: List[Case]) -> Dict[str, List[str]]:
    """Symbols declared by more than one case, with the case ids that declare them."""
    owners: Dict[str, List[str]] = {}
    for case in cases:
        for symbol in case_symbols(case.source):
            owners.setdefault(symbol, []).append(case.case_id)
    return {s: sorted(ids) for s, ids in sorted(owners.items()) if len(ids) > 1}


def scope_conflicts(cases: List[Case]) -> Dict[str, List[str]]:
    """Symbols a case declares that another case's *import closure* also provides.

    The cross-case half of :func:`imported_symbols`: this is the set that made a
    naive name-only grouping look right while the bundle still refused to build.
    """
    conflicts: Dict[str, List[str]] = {}
    for case in cases:
        overlap = case_symbols(case.source) & {
            s for other in cases if other.case_id != case.case_id
            for s in imported_symbols(other.source)
        }
        for symbol in sorted(overlap):
            conflicts.setdefault(symbol, []).append(case.case_id)
    return {s: sorted(ids) for s, ids in sorted(conflicts.items())}



def all_pengu_files() -> List[Path]:
    """Every ``.pengu`` under the corpus, cases *and* support modules."""
    return sorted(CONFORMANCE_DIR.rglob(f"*{PENGU_SUFFIX}"))


def _normalise(text: str) -> str:
    """CRLF/CR -> LF, so a case written on Windows compares equal on Linux."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# --------------------------------------------------------------------------
# Building the one bundle
# --------------------------------------------------------------------------


def _pick_cc() -> Optional[str]:
    """TCC when available (10x faster here), else gcc/clang/cc.

    Note ``shutil.which("tcc")`` is not enough: the repository stages a TCC under
    ``build/tcc-dist`` that is deliberately *not* on PATH, so the lookup goes
    through ``pengu_tcc.find_tcc()`` first.
    """
    wanted = os.environ.get("PENGU_TEST_CC", "tcc").strip() or "tcc"
    if wanted not in ("tcc", ""):
        explicit = shutil.which(wanted) if os.sep not in wanted else wanted
        return explicit or None
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


@dataclass
class Bundle:
    """The compiled corpus binary plus the mapping needed to judge one case."""

    exe: Path
    cc: str
    workdir: Path
    index_by_id: Dict[str, int]
    test_names: List[str]

    def index_of(self, case_id: str) -> Optional[int]:
        return self.index_by_id.get(case_id)


def _write_aggregator(dest: Path, modules: List[str]) -> None:
    """Writes the entry module that imports every corpus module.

    Importing is what pulls a module's ``test`` blocks into the bundle: the
    codegen skips the tests of *imported* modules only when they live under a
    ``std/`` path, which is exactly what keeps this from re-running the standard
    library's own suite.
    """
    lines = [
        "# Generated by tests/test_conformance.py -- do not edit.",
        "#",
        "# Imports every module of the conformance corpus so that a single binary",
        "# carries all of their `test` blocks. Order does not decide anything: the",
        "# runner maps names to indices by asking the binary itself (--list).",
        "",
    ]
    lines.extend(f"import {module}" for module in modules)
    lines.append("")
    dest.write_text("\n".join(lines), encoding="utf-8")


def _list_tests(exe: Path, cwd: Path) -> List[str]:
    """Asks the compiled binary for its test names, in index order."""
    res = subprocess.run([str(exe), "--list"], capture_output=True, text=True,
                         cwd=str(cwd), timeout=300)
    assert res.returncode == 0, (
        f"`{exe.name} --list` failed (rc={res.returncode}):\n{res.stderr}"
    )
    names: List[str] = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "index" in obj and "name" in obj:
            assert obj["index"] == len(names), (
                f"--list returned index {obj['index']} where {len(names)} was "
                f"expected; the protocol is ordered and dense"
            )
            names.append(str(obj["name"]))
    return names


#: Cross-worker cache of built group binaries.
#:
#: Under pytest-xdist every worker that touches a case builds its own bundle for
#: that case's group, so the same compile is paid once per worker. Measured on the
#: 85-case corpus: 10 bundle builds cost 83.7 s while the 85 case spawns cost
#: 0.5 s, and `test_conformance.py` reported 528 s of aggregate work. The cache
#: makes the compile once per (group, profile, inputs) per machine.
_GROUPS_CACHE_DIR = BUILD_DIR / "_conformance_cache"


def _compiler_sources() -> List[Path]:
    """Every source that can change the C a bundle produces.

    The project's own bundle fingerprint covers the *program* and its config, not
    the compiler, so editing `pengu_parser/` used to leave a stale artifact in place
    (tests/_inventory.md §15.5). A cache keyed on inputs alone would repeat exactly
    that mistake, so the compiler and the runtime header are part of the key.
    """
    files = [REPO / "pengu_project.py", REPO / "pengu_paths.py", REPO / "pengu_runtime.h"]
    for pattern in ("pengu_parser/*.py", "pengu_parser/pengu_codegen/*.py"):
        files.extend(sorted(REPO.glob(pattern)))
    return [f for f in files if f.is_file()]


def _groups_cache_key(cases: List["Case"], profile: str, cc: str) -> str:
    """A digest of everything that can change the built binary."""
    digest = hashlib.sha256()
    digest.update(b"conformance-bundle-cache-v1\n")
    digest.update(f"{profile}\n{cc}\n".encode("utf-8"))
    # The instrumentation flags change the binary, so they change the key: a
    # sanitized run must never be served the plain build (or the reverse).
    digest.update(os.environ.get("PENGU_CFLAGS", "").encode("utf-8") + b"\0")
    digest.update(os.environ.get("PENGU_LDFLAGS", "").encode("utf-8") + b"\0")
    for case in sorted(cases, key=lambda c: c.case_id):
        digest.update(case.case_id.encode("utf-8") + b"\0")
        digest.update(case.source.read_bytes() + b"\0")
    for path in _compiler_sources():
        digest.update(str(path.relative_to(REPO)).encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()[:32]


def _serve_cached_bundle(cached: Path, cc: str) -> Optional["Bundle"]:
    """A Bundle from the cache, or None when this group has not been built here.

    The binary is *copied* into a private workdir rather than run from the cache:
    `run_case` uses the workdir as the process's cwd, and cases that write files
    (the ledger/archivum exercises do) must not write into the shared cache.
    """
    exe_name = "conformance.exe" if os.name == "nt" else "conformance"
    cached_exe = cached / exe_name
    cached_names = cached / "names.json"
    if not (cached_exe.is_file() and cached_names.is_file()):
        return None
    try:
        names = json.loads(cached_names.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    workdir = Path(tempfile.mkdtemp(prefix="pengu_conformance_", dir=BUILD_DIR))
    exe = workdir / exe_name
    shutil.copy2(cached_exe, exe)
    os.chmod(exe, 0o755)
    return Bundle(
        exe=exe,
        cc=cc,
        workdir=workdir,
        index_by_id={name: i for i, name in enumerate(names)},
        test_names=list(names),
    )


def _store_cached_bundle(cached: Path, exe: Path, names: List[str], cc: str) -> None:
    """Publishes a built binary for the other workers, atomically.

    Two workers can build the same group at the same time; `os.replace` means the
    last one wins instead of leaving a half-written executable behind for the next
    worker to run. A cache that cannot be written (a read-only build dir) is not an
    error: it is an optimisation, and failing a run over it would be worse.
    """
    try:
        cached.mkdir(parents=True, exist_ok=True)
        staged = cached / f".staged-{os.getpid()}-{exe.name}"
        shutil.copy2(exe, staged)
        os.chmod(staged, 0o755)
        os.replace(staged, cached / exe.name)
        # The names file lands second, so a worker never finds a binary without it.
        names_staged = cached / f".staged-names-{os.getpid()}.json"
        names_staged.write_text(json.dumps(names), encoding="utf-8")
        os.replace(names_staged, cached / "names.json")
    except OSError:
        pass


def build_bundle(cases: List[Case], profile: str = "debug") -> Bundle:
    """Copies the corpus aside, compiles ONE group into a binary, returns it.

    The corpus is copied rather than built in place so the repository is never
    written to by a test (the aggregator has to sit next to the modules it
    imports, and a module path is resolved relative to the project base dir).

    ``cases`` is a collision-free group (see :func:`group_cases`): the aggregator
    imports exactly those cases, while the whole tree is copied so their own
    imports still resolve.
    """
    cc = _pick_cc()
    assert cc, "no C compiler: set PENGU_TEST_CC or install gcc"

    if os.environ.get("PENGU_CFLAGS", "").strip() or os.environ.get("PENGU_LDFLAGS", "").strip():
        # TCC *silently ignores* flags it does not implement, `-fsanitize=address`
        # among them, so an instrumented run through it would link a plain binary
        # and stay green -- measured: the cached bundle had no libasan. When flags
        # are supplied, ask for the compiler that honours them.
        real = _fallback_cc(cc)
        if real:
            cc = real

    cached = _GROUPS_CACHE_DIR / _groups_cache_key(cases, profile, cc)
    served = _serve_cached_bundle(cached, cc)
    if served is not None:
        return served

    workdir = Path(tempfile.mkdtemp(prefix="pengu_conformance_", dir=BUILD_DIR))
    try:
        # Named `corpus`, not `conformance`: the linked binary is written next to it
        # as `conformance`, and a compiler cannot write an executable over a directory.
        corpus = workdir / "corpus"
        corpus.mkdir(parents=True, exist_ok=True)

        for src in all_pengu_files():
            rel = src.relative_to(CONFORMANCE_DIR)
            dest = corpus / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)

        modules = [
            c.source.relative_to(CONFORMANCE_DIR).with_suffix("").as_posix().replace("/", ".")
            for c in cases
        ]
        entry = corpus / ENTRY_NAME
        _write_aggregator(entry, modules)

        from pengu_project import PenguBuilder, ProjectConfig

        cfg = ProjectConfig(entry=str(entry), base_dir=str(corpus), profile=profile, output="c")
        builder = PenguBuilder(cfg)
        builder.is_test_mode = True
        bundle_path, _ = builder.bundle(output_file=str(workdir / "bundle.c"))

        exe = workdir / ("conformance.exe" if os.name == "nt" else "conformance")

        def _compile(compiler: str):
            cmd = [
                compiler, str(bundle_path),
                f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}", f"-L{BUILD_LIB}",
                "-Wno-error=implicit-function-declaration",
                "-Wno-error=implicit-int",
                "-Wno-error=int-conversion",
                "-Wno-div-by-zero",
                "-Wno-unused-variable",
                # Honour PENGU_CFLAGS / PENGU_LDFLAGS exactly as
                # tests/conftest.compile_run does. Without this the sanitizer
                # workflow's `pytest tests` step ran the *whole corpus* without
                # instrumentation: the job was green and covered nothing, which is
                # the worst kind of green.
                *shlex.split(os.environ.get("PENGU_CFLAGS", "").strip()),
                *shlex.split(os.environ.get("PENGU_LDFLAGS", "").strip()),
                *runtime_link_flags(),
                *runtime_tail_flags(),
                "-o", str(exe),
            ]
            return subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        # TCC is the default because it is ~10x faster, but generated C uses GNU
        # extensions it does not implement -- `__auto_type` (from the always-on
        # bounds-check wrappers) is a hard error, not a warning flag away. Falling
        # back keeps the runner usable on any toolchain instead of demanding one
        # particular compiler.
        attempts = [(cc, _compile(cc))]
        if attempts[0][1].returncode != 0:
            fallback = _fallback_cc(cc)
            if fallback:
                attempts.append((fallback, _compile(fallback)))

        succeeded = next(((c, r) for c, r in attempts if r.returncode == 0), None)
        if succeeded is not None:
            cc, _ = succeeded
        else:
            # Report EVERY attempt, because the first one is usually a red
            # herring: TCC stops at `__auto_type` whatever the real problem is,
            # so leading with its error sends the reader after the wrong bug.
            detail = "\n\n".join(
                f"--- {compiler} (rc={r.returncode}) ---\n{r.stderr[-2500:]}"
                for compiler, r in attempts
            )
            raise AssertionError(
                f"the conformance bundle failed to build with "
                f"{' or '.join(c for c, _ in attempts)}:\n{detail}"
            )

        names = _list_tests(exe, corpus)
        _store_cached_bundle(cached, exe, names, cc)
        return Bundle(
            exe=exe,
            cc=cc,
            workdir=workdir,
            index_by_id={name: i for i, name in enumerate(names)},
            test_names=names,
        )
    except BaseException:
        # The build may fail after the workdir exists (a group that will not
        # compile). Without this the temp tree leaks, and during the
        # investigation that littered build/ with 159 directories -- the kind
        # of thing that fills a CI runner's disk instead of failing a test.
        shutil.rmtree(workdir, ignore_errors=True)
        raise


def _fallback_cc(cc: str) -> Optional[str]:
    """A stricter compiler to retry with when TCC cannot compile the bundle."""
    if "tcc" not in os.path.basename(cc).lower():
        return None
    for name in ("gcc", "clang", "cc"):
        found = shutil.which(name)
        if found and found != cc:
            return found
    return None


# --------------------------------------------------------------------------
# Running one case
# --------------------------------------------------------------------------


@dataclass
class Result:
    case_id: str
    status: str
    duration_ms: float
    expected_stdout: str = ""
    expected_exit: int = DEFAULT_EXIT
    got_stdout: str = ""
    got_exit: int = 0
    stderr: str = ""
    message: str = ""

    def as_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "name": self.case_id,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 3),
        }
        if self.status != "pass":
            out.update({
                "expected": self.expected_stdout,
                "expected_exit": self.expected_exit,
                "got": self.got_stdout,
                "got_exit": self.got_exit,
                "stdout": self.got_stdout,
                "stderr": self.stderr,
            })
            if self.message:
                out["message"] = self.message
        return out


def _shell_exit(returncode: int) -> int:
    """Signal deaths as shells report them (128+signal), so ``.exit`` is portable.

    Python reports a signal death as a negative ``returncode``; a shell reports
    ``128+n``. Windows has no negative codes, so normalising here keeps one
    ``.exit`` file meaningful on all three platforms.
    """
    return returncode + 256 if returncode < 0 else returncode


def run_case(bundle: Bundle, case: Case) -> Result:
    """Spawns the bundle once, for one case, and judges its stdout and exit code."""
    index = bundle.index_of(case.case_id)
    if index is None:
        return Result(
            case_id=case.case_id,
            status="error",
            duration_ms=0.0,
            message=(
                f"the compiled bundle has no test named {case.case_id!r}. A case's "
                f"`test` block must be named exactly its id (the path relative to "
                f"tests/conformance/, without .pengu). Bundle has "
                f"{len(bundle.test_names)} test(s)."
            ),
        )

    expected_stdout = case.expected_stdout
    expected_exit = case.expected_exit
    timeout = float(os.environ.get("PENGU_TEST_TIMEOUT", DEFAULT_TIMEOUT))

    started = time.perf_counter()
    try:
        res = subprocess.run(
            [str(bundle.exe), "--only-index", str(index)],
            capture_output=True, text=True, cwd=str(bundle.workdir), timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return Result(
            case_id=case.case_id, status="fail",
            duration_ms=(time.perf_counter() - started) * 1000.0,
            expected_stdout=expected_stdout, expected_exit=expected_exit,
            message=f"timed out after {timeout:.0f}s",
        )
    duration_ms = (time.perf_counter() - started) * 1000.0

    got_stdout = _normalise(res.stdout)
    got_exit = _shell_exit(res.returncode)

    problems = []
    if got_exit != expected_exit:
        problems.append(f"exit code: expected {expected_exit}, got {got_exit}")
    if got_stdout != expected_stdout:
        problems.append(
            f"stdout differs:\n"
            f"--- expected ---\n{expected_stdout!r}\n"
            f"--- got ---\n{got_stdout!r}"
        )

    return Result(
        case_id=case.case_id,
        status="fail" if problems else "pass",
        duration_ms=duration_ms,
        expected_stdout=expected_stdout,
        expected_exit=expected_exit,
        got_stdout=got_stdout,
        got_exit=got_exit,
        stderr=_normalise(res.stderr),
        message="\n".join(problems),
    )


# --------------------------------------------------------------------------
# pytest wiring
# --------------------------------------------------------------------------


CASES: List[Case] = _selected_cases()

#: Collision-free groups, computed once at import so the parametrisation and the
#: fixture agree on exactly which cases share a binary.
GROUPS: List[List[Case]] = group_cases(CASES) if CASES else []
GROUP_OF: Dict[str, int] = {
    case.case_id: index for index, group in enumerate(GROUPS) for case in group
}


class _BundleCache:
    """Builds (at most) one binary per group, on first use, and tears them down.

    Lazy on purpose: `--test <one case>` must not pay for the whole corpus, and a
    full run pays for one compile per collision-free group rather than one per
    case.
    """

    def __init__(self, groups: List[List[Case]]) -> None:
        self._groups = groups
        self._built: Dict[tuple, Bundle] = {}
        self._failed: Dict[tuple, str] = {}

    def for_case(self, case_id: str, profile: str = "debug") -> Bundle:
        """The bundle for this case's group, built in `profile` on first use.

        A group that does not build is remembered as failed and **not retried**.
        That is not an optimisation, it is what keeps one bad case from costing the
        group size: while failures were not cached, every case in a broken group
        re-attempted the compile, so a group of 25 turned one compiler error into
        25 slow failures (measured: a 115-case corpus with two broken groups took
        13m36s instead of ~1m). The first failure carries the compiler output; the
        rest point at it instead of recompiling.
        """
        index = GROUP_OF[case_id]
        key = (index, profile)
        if key in self._failed:
            raise AssertionError(
                f"group {index} ({profile}) already failed to build in this run, "
                f"not retrying. Members: "
                f"{', '.join(c.case_id for c in self._groups[index])[:400]}\n"
                f"First failure:\n{self._failed[key]}"
            )
        if key not in self._built:
            try:
                self._built[key] = build_bundle(self._groups[index], profile=profile)
            except BaseException as exc:
                self._failed[key] = f"{type(exc).__name__}: {exc}"
                raise
        return self._built[key]

    def close(self) -> None:
        for bundle in self._built.values():
            shutil.rmtree(bundle.workdir, ignore_errors=True)
        self._built.clear()


@pytest.fixture(scope="session")
def bundles() -> "_BundleCache":
    """The compiled binaries, one per collision-free group, built on demand."""
    if not HAVE_CC:
        pytest.skip("no C compiler available")
    if not HAVE_RUNTIME:
        pytest.skip("libpengu_runtime.a not built (run build_runtime.py)")
    if not CASES:
        pytest.skip("no conformance cases selected")
    cache = _BundleCache(GROUPS)
    try:
        yield cache
    finally:
        cache.close()


def _pytest_id(case: Case) -> str:
    return case.case_id


def _case_param(case: Case):
    """A parametrised case, marked ``smoke`` when it is part of the fast subset.

    ``_smoke/`` is the corpus's cheap tier by convention: the cases small enough
    that a pre-commit hook can afford them. Marking them here keeps the set
    data-driven -- moving a case in or out of the smoke tier is a file move, not
    an edit to the runner.
    """
    # One xdist group per collision-free group, so that under `--dist loadgroup`
    # every case of a group lands on ONE worker. The bundle is built by whichever
    # worker first needs it; without the grouping each worker that touches the
    # group rebuilds it, which measured as 1207s of aggregate work for a corpus
    # whose bundles cost 84s in total. The doc-block sweeps are a different file
    # and keep spreading across all workers, which a blanket `--dist loadfile`
    # would have prevented (measured twice: 311s and 313s against 219s).
    marks = [pytest.mark.xdist_group(f"conformance-group-{GROUP_OF[case.case_id]}")]
    if case.case_id.startswith("_smoke/"):
        marks.append(pytest.mark.smoke)
    return pytest.param(case.case_id, id=case.case_id, marks=marks)


CASE_PARAMS = [_case_param(c) for c in CASES]


@pytest.mark.conformance
@pytest.mark.parametrize("case_id", CASE_PARAMS)
def test_conformance_case(case_id: str, bundles: "_BundleCache") -> None:
    """One corpus case: its stdout and exit code must match the recorded files.

    Run once per profile the case declares (debug by default). A case that needs
    release as well says so in the manifest, and both runs must reproduce the same
    recorded behaviour -- which is the point: optimisation is what exposes a
    different class of undefined behaviour.
    """
    case = next(c for c in CASES if c.case_id == case_id)
    if case.skip_reason:
        pytest.skip(case.skip_reason)

    json_file = os.environ.get("PENGU_TEST_JSON_FILE", "").strip()
    failures = []
    for profile in case.profiles:
        result = run_case(bundles.for_case(case_id, profile), case)
        if json_file:
            payload = result.as_json()
            payload["profile"] = profile
            with open(json_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if result.status != "pass":
            failures.append((profile, result))

    if failures:
        raise AssertionError("\n\n".join(
            f"{case_id} ({case.source.relative_to(REPO)}) [{profile}]:\n"
            f"{result.message}\n"
            f"--- stderr ---\n{result.stderr[-2000:]}"
            for profile, result in failures
        ))


def test_manifest_has_no_stale_entries() -> None:
    """A manifest entry for a case that no longer exists is a lie about coverage."""
    known = {c.case_id for c in discover_cases()}
    stale = sorted(set(MANIFEST) - known)
    assert not stale, (
        f"{MANIFEST_PATH.name} describes cases that do not exist: {stale}. "
        f"Delete the entry, or the case, so the two cannot disagree."
    )
    collisions = sorted(RESERVED_MANIFEST_KEYS & known)
    assert not collisions, (
        f"a conformance case is called {collisions}, which is a reserved manifest "
        f"key. Rename the case: {RESERVED_MANIFEST_KEYS} holds documentation."
    )


def test_every_case_is_discoverable() -> None:
    """The `_`-prefixed smoke corpus must actually be found by discovery."""
    ids = {c.case_id for c in discover_cases()}
    assert ids, (
        "no conformance cases found under tests/conformance/. A case is a .pengu "
        "file with a sibling .expected file."
    )


def test_case_ids_are_unique() -> None:
    ids = [c.case_id for c in discover_cases()]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert not duplicates, f"duplicate case ids: {duplicates}"


# --------------------------------------------------------------------------
# The dependency graph behind `pengu selftest --affected`
# --------------------------------------------------------------------------


def _load_deps_graph() -> Dict[str, Any]:
    path = CONFORMANCE_DIR / "_deps.json"
    assert path.is_file(), (
        "tests/conformance/_deps.json is missing; run: "
        "python tools/gen_conformance_deps.py"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _load_deps_module():
    """Imports ``tools/gen_conformance_deps.py`` (not a package)."""
    import importlib.util

    path = REPO / "tools" / "gen_conformance_deps.py"
    spec = importlib.util.spec_from_file_location("gen_conformance_deps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deps_graph_is_up_to_date() -> None:
    """A stale graph silently mis-scopes `--affected`, so it is gated here."""
    mod = _load_deps_module()
    expected = mod.render(mod.build_graph())
    actual = (CONFORMANCE_DIR / "_deps.json").read_text(encoding="utf-8")
    assert actual == expected, (
        "tests/conformance/_deps.json is out of date; run: "
        "python tools/gen_conformance_deps.py"
    )


def test_deps_graph_covers_every_case() -> None:
    graph = _load_deps_graph()
    mapped = {k for k in graph if k != "_meta"}
    known = {c.case_id for c in discover_cases()}
    assert mapped == known, (
        f"the dependency graph and the corpus disagree: "
        f"only in graph={sorted(mapped - known)}, only on disk={sorted(known - mapped)}"
    )


def test_a_compiler_change_selects_the_smoke_tier() -> None:
    """A change under ``pengu_parser/`` must select the ``_smoke/`` cases.

    Regression guard for a real bug: the selector skipped every ``_``-prefixed
    case id as if it were the metadata key, so the cases most likely to be
    affected were exactly the ones quietly excluded. It reported "no case
    affected" for a change to the compiler. The corpus's smoke tier is
    ``_smoke/``, so the ``_`` prefix is a normal part of a case id.
    """
    from pengu_project import _selftest_affected_cases

    selected = _selftest_affected_cases(["pengu_parser/pengu_grammar.py"])
    assert selected, "a compiler change must select the corpus, not nothing"
    assert any(c.startswith("_smoke/") for c in selected), selected


def test_a_std_change_selects_only_the_cases_that_import_it() -> None:
    from pengu_project import _selftest_affected_cases

    graph = _load_deps_graph()
    referenced = {
        dep for deps in graph.values() if isinstance(deps, list) for dep in deps
    }

    # A std module some case imports must select at least that case...
    imported = sorted(d for d in referenced if d.startswith("std/"))
    assert imported, "the corpus is expected to import at least one std module"
    selected = _selftest_affected_cases([imported[0]])
    assert selected, f"{imported[0]} is referenced by the graph but selected nothing"

    # ...and a std module no case imports must select nothing. Derived from the
    # tree rather than hardcoded: the corpus is expected to grow, and a literal
    # module name here would silently stop testing anything the moment a migrated
    # case started importing it (which is exactly what happened to std/scrolls).
    on_disk = {f"std/{p.name}" for p in (REPO / "std").glob("*.pengu")}
    unimported = sorted(on_disk - referenced)
    assert unimported, "every std module is imported by some case; nothing to assert"
    assert _selftest_affected_cases([unimported[0]]) == []


def test_an_unrelated_change_selects_nothing() -> None:
    from pengu_project import _selftest_affected_cases

    assert _selftest_affected_cases(["docs/PENGU_BUILD.md", "README.md"]) == []


# --------------------------------------------------------------------------
# The shared-namespace constraint (why the corpus is bundled in groups)
# --------------------------------------------------------------------------


def _tmp_case(tmp_path: Path, case_id: str, body: str) -> "Case":
    source = tmp_path / (case_id.replace("/", "_") + ".pengu")
    source.write_text(body, encoding="utf-8")
    expected = source.with_suffix(".expected")
    expected.write_text("", encoding="utf-8")
    return Case(case_id=case_id, source=source, expected=expected,
                exit_file=source.with_suffix(".exit"))


def test_cases_that_share_a_symbol_are_not_bundled_together(tmp_path) -> None:
    """Two cases declaring the same top-level name must land in different groups.

    A bundle is ONE compilation unit and PenguScript resolves its modules in a
    single symbol namespace, so two cases declaring `Point` cannot coexist. The
    build fails with "Omen variant name 'Point' of omen 'Shape' collides with the
    top-level symbol 'Point'" -- naming neither the cases nor the fix.

    This is a characterisation test of the constraint, not of a feature: if the
    compiler ever namespaces modules properly, grouping can go away and this test
    should be deleted along with :func:`group_cases`.
    """
    a = _tmp_case(tmp_path, "x/a", 'test "x/a":\n    var p as int is 1\nomen Shape:\n    Point\n')
    b = _tmp_case(tmp_path, "x/b", 'test "x/b":\n    var q as int is 2\nrune Point:\n    x as int\n')
    plain = _tmp_case(tmp_path, "x/plain", 'test "x/plain":\n    var r as int is 3\n')

    assert symbol_collisions([a, b, plain]) == {"Point": ["x/a", "x/b"]}

    groups = group_cases([a, b, plain])
    placement = {c.case_id: i for i, g in enumerate(groups) for c in g}
    assert placement["x/a"] != placement["x/b"], (
        "cases that share a symbol must not share a bundle"
    )
    assert placement["x/plain"] in (placement["x/a"], placement["x/b"]), (
        "a case with no colliding symbol should join an existing group"
    )


def test_real_corpus_groups_are_collision_free() -> None:
    """No group may contain two cases that share a symbol.

    If this fails, bundling will fail on the machine that runs it -- which is a
    confusing place to find out.
    """
    for index, group in enumerate(GROUPS):
        collisions = symbol_collisions(group)
        assert not collisions, (
            f"group {index} has cases sharing symbols: {collisions}. "
            f"group_cases() should have separated them."
        )


def test_a_case_can_declare_a_known_sanitizer_finding(monkeypatch) -> None:
    """`skip_under_sanitizers` in the manifest must actually skip.

    The sanitizer workflow runs `pytest tests` -- the whole suite, corpus included --
    so a program whose bug is only visible under ASan has to be able to say so in
    the manifest instead of the runner hard-coding a filename. No case needs it
    today; the field is asserted here so it is a tested capability rather than
    scaffolding that decays.
    """
    import tests.test_conformance as runner

    case = next(c for c in CASES if not c.meta.get("skip_under_sanitizers"))
    assert case.skip_reason is None

    monkeypatch.setitem(case.meta, "skip_under_sanitizers", True)
    monkeypatch.setattr(runner, "SANITIZERS_ACTIVE", True)
    reason = case.skip_reason
    assert reason and "sanitizer" in reason

    monkeypatch.setattr(runner, "SANITIZERS_ACTIVE", False)
    assert case.skip_reason is None, "the skip must not apply outside sanitizer runs"


def test_a_broken_group_is_only_built_once(monkeypatch) -> None:
    """One bad case must not cost the group size.

    While build failures were not cached, every case in a broken group retried the
    compile. Measured on a 115-case corpus with two broken groups: 13m36s, against
    ~1m once the failure is remembered. The first failure keeps the compiler
    output; the rest say which group already failed instead of recompiling it.
    """
    calls = []

    def boom(cases, profile="debug"):
        calls.append(profile)
        raise AssertionError("synthetic build failure")

    monkeypatch.setattr("tests.test_conformance.build_bundle", boom)
    cache = _BundleCache(GROUPS)
    case_id = next(c.case_id for c in CASES if c.profiles[0] == "debug")
    for _ in range(3):
        with pytest.raises(AssertionError, match="synthetic build failure"):
            cache.for_case(case_id)
    assert len(calls) == 1, f"the broken group was built {len(calls)} times, not once"
    with pytest.raises(AssertionError, match="already failed to build"):
        cache.for_case(case_id)


def test_grouping_is_deterministic() -> None:
    """The number of compiles must not move between runs."""
    again = group_cases(CASES)
    assert [[c.case_id for c in g] for g in again] == [
        [c.case_id for c in g] for g in GROUPS
    ]


def test_the_smoke_tier_is_a_single_bundle() -> None:
    """`--smoke` must stay one compile, or it stops being fast.

    The smoke cases avoid top-level declarations precisely so this holds; a new
    smoke case that declares one would split the tier and slow the job down.
    """
    smoke = [c for c in CASES if c.case_id.startswith("_smoke/")]
    if not smoke:
        pytest.skip("no smoke cases selected")
    assert len(group_cases(smoke)) == 1, (
        "the smoke tier now needs more than one bundle; a `_smoke/` case must not "
        "declare top-level symbols"
    )
