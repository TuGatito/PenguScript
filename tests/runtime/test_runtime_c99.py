"""Phase 3 item 3.1 (B8) and 3.12 — the runtime translation unit is legal C99/C11.

Before Phase 3, `pengu_parser/pengu_runtime.c` did **not** compile as valid C: it
included third-party headers whose declarations the upstream library gates behind
private-access macros, and `build_runtime.py` compensated with

    -Wno-incompatible-pointer-types -Wno-implicit-function-declaration

which suppressed the implicit-function-declaration errors. They never appeared in
the build log, and `cl.exe` rejects both flags, so no MSVC build was possible.

Phase 1 removed every external binding from the tree, so the runtime now needs
nothing beyond libc/libm/pthreads and the only build-time define is
`PENGU_RUNTIME_SUBSYSTEM_ONLY` (plus the `PENGU_ENABLE_THREADS` gate).

Rule C1: these tests **compile** the translation unit with the real flags and
assert on the compiler's exit status and diagnostic count.
"""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RUNTIME_C = REPO / "pengu_parser" / "pengu_runtime.c"
INCLUDE = REPO / "build" / "include"

#: Object files go to the platform's temp directory: `/tmp` does not exist on
#: Windows, and MinGW resolves a hardcoded `/tmp/foo.o` to `C:\tmp\foo.o`, which
#: then fails to open — a red test that says nothing about the compiler.
OBJ_DIR = Path(tempfile.gettempdir())

pytestmark = pytest.mark.skipif(
    shutil.which("gcc") is None, reason="gcc is required to compile the runtime"
)


def _runtime_flags():
    """The real compile flags for the runtime, taken from build_runtime.py itself.

    Importing the build script and calling it is avoided on purpose: it would build
    third-party libraries. Instead the flags are reconstructed from the module the
    same way `build_pengu_runtime` does, so a change to that function's flag list
    cannot silently pass this test.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_runtime_probe", REPO / "build_runtime.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    flags = [
        "-O2",
        "-I" + str(mod.ROOT_DIR),
        "-I" + str(mod.INCLUDE_DIR),
    ]
    flags += list(mod.SECTION_FLAGS)
    return flags


def _compile_runtime(extra_flags=(), std="c11"):
    """Compiles the runtime and returns (rc, combined diagnostics)."""
    cmd = [
        "gcc", f"-std={std}", "-Wall", "-Wextra",
        *_runtime_flags(), *extra_flags,
        "-c", str(RUNTIME_C), "-o", str(OBJ_DIR / "_pengu_runtime_probe.o"),
    ]
    r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600)
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------------------
# Item 3.1 — the unit compiles clean with no suppression flags
# ---------------------------------------------------------------------------


def test_runtime_compiles_with_no_suppression_flags():
    """The core B8 property: valid C11, no -Wno-* needed."""
    rc, out = _compile_runtime()
    assert rc == 0, f"runtime.c failed to compile without suppression flags:\n{out}"


def test_runtime_compiles_with_zero_diagnostics():
    """Not merely "no errors": zero warnings too, under -Wall -Wextra."""
    rc, out = _compile_runtime()
    assert rc == 0, out
    diagnostics = [l for l in out.splitlines() if re.search(r"\b(error|warning):", l)]
    assert not diagnostics, "runtime.c produced diagnostics:\n" + "\n".join(diagnostics)


def _undefined_symbols(obj: Path) -> set:
    """`nm -u` names normalised to the C identifier, on every toolchain."""
    nm = shutil.which("nm")
    if not nm:
        pytest.skip("nm is required to inspect the object's symbols")
    res = subprocess.run([nm, "-u", str(obj)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    names = set()
    for line in res.stdout.splitlines():
        if not line.strip():
            continue
        name = line.split()[-1]
        if name.startswith("__imp_"):   # MinGW DLL import thunk
            name = name[len("__imp_"):]
        names.add(name.lstrip("_"))
    return names


def test_the_core_object_references_no_optional_library():
    """The member a plain program pulls must need nothing but libc.

    PE's `--gc-sections` keeps the unreferenced sections of an archive member,
    so a single-member runtime made `hello_world` demand `-lxml2`/`-lmicrohttpd`
    on Windows. Every optional subsystem now lives in its own member
    (`build_runtime.RUNTIME_OBJECTS`); this compiles the core exactly the way
    that build does and proves it has no optional-library reference.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_runtime_probe_core", REPO / "build_runtime.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    gates = [f"-D{gate}=0" for gate in mod.RUNTIME_GATES]
    obj = OBJ_DIR / "_pengu_runtime_core.o"
    cmd = ["gcc", "-std=c11", "-Wall", "-Wextra", *_runtime_flags(), *gates,
           "-DPENGU_RUNTIME_SUBSYSTEM_ONLY=0",
           "-c", str(RUNTIME_C), "-o", str(obj)]
    r = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr

    undefined = _undefined_symbols(obj)
    optional = sorted(s for s in undefined
                      if s.startswith(("MHD_", "curl_", "pcre2_", "mbedtls_", "xml", "sqlite3_",
                                       "webui", "raylib", "XXH", "yaml_", "toml")))
    assert not optional, (
        f"the core runtime object references an optional library: {optional}; "
        "its implementation belongs in a satellite binding, not the runtime"
    )
    assert "pengu_abi_version" not in undefined, "the core must define the ABI pin"


def test_runtime_has_no_implicit_function_declarations():
    """No call in the runtime may rely on an implicit declaration.

    Asserted by compiling with `-Werror=implicit-function-declaration`, which turns
    exactly that class into a hard error.
    """
    rc, out = _compile_runtime(extra_flags=["-Werror=implicit-function-declaration"])
    assert rc == 0, (
        f"implicit function declarations present:\n{out}"
    )


# ---------------------------------------------------------------------------
# Item 3.12 — the macro guards
# ---------------------------------------------------------------------------

def test_build_runtime_has_no_suppressions_for_the_runtime():
    """`build_pengu_runtime` passes no `-Wno-*`.

    Scoped to that one function on purpose: the other `-Wno-*` sites in
    `build_runtime.py` compile third-party libraries, which is out of scope for
    Phase 3. Asserting on the whole file would either be wrong or would force
    unrelated churn.
    """
    import ast

    src = (REPO / "build_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build_pengu_runtime")
    # Only *string literals* count: the function's explanatory comment mentions the
    # flags it no longer passes, and a substring check over the raw source would
    # trip on the comment rather than on real configuration.
    literals = [n.value for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    suppressed = [s for s in literals if s.startswith("-Wno-")]
    assert not suppressed, (
        "build_pengu_runtime still suppresses warnings; B8 is that the runtime is "
        f"valid C without them: {suppressed}"
    )


def test_the_subsystem_define_is_guarded():
    """Cross-check the guards against the flags, so they cannot drift apart.

    The build passes `-DPENGU_RUNTIME_SUBSYSTEM_ONLY`; the runtime must define it
    under an `#ifndef` guard or every compile emits `-Wmacro-redefined`.
    """
    import ast

    src = (REPO / "build_runtime.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "build_pengu_runtime")
    literals = [n.value for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    passed = {s[2:].split("=")[0] for s in literals
              if s.startswith("-D") and s[2:3].isupper()}
    text = RUNTIME_C.read_text(encoding="utf-8")
    unguarded = []
    for m in re.finditer(r"^#define\s+([A-Z_][A-Z0-9_]*)\s*$", text, re.M):
        macro = m.group(1)
        if macro not in passed:
            continue
        # Look back for the nearest #ifndef of this macro with no intervening
        # #endif, i.e. a real enclosing guard rather than a coincidence elsewhere.
        preceding = text[:m.start()].splitlines()
        guarded = False
        for line in reversed(preceding[-8:]):
            if line.strip() == "#endif":
                break
            if line.strip() == f"#ifndef {macro}":
                guarded = True
                break
        if not guarded:
            unguarded.append(macro)
    assert not unguarded, (
        f"these macros are passed by the build AND defined unguarded in the runtime, "
        f"which yields -Wmacro-redefined: {unguarded}"
    )
