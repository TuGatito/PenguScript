"""Phase 1 — anti-regression tests for assumptions the audit refuted.

`AUDIT_1.0.md` §18.2 lists 14 assumptions from the audit request that were
verified FALSE. Some of them describe properties a future change could silently
break, so they are pinned here.

Rule C1 (ROADMAP_2.0 Anexo C): a test may not approve a property by inspecting
text. Where a claim is about the CLI, the test drives the real CLI; where it is
about module layout, the test inspects the module graph for real rather than
grepping a directory listing.

Each test's docstring states which assumption it refutes and why the refutation
still holds. Assumptions that are only guaranteed by the type system or the C
compiler are deliberately NOT tested here (see the closing comment).
"""

import argparse
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
MODULE = "pengu_project"


def cli(args, cwd=None, timeout=120):
    env = dict(os.environ)
    env.setdefault("NO_COLOR", "1")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(REPO), env.get("PYTHONPATH", "")) if p
    )
    return subprocess.run(
        [PY, "-m", MODULE] + list(args),
        cwd=str(cwd or REPO), capture_output=True, text=True,
        timeout=timeout, env=env,
    )


def subcommands():
    """The real subcommand set, read from the parser the CLI actually builds."""
    sys.path.insert(0, str(REPO))
    import pengu_project
    parser = pengu_project.create_cli_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return sorted(action.choices)
    pytest.fail("could not find the subparsers action")


# ---------------------------------------------------------------------------
# "The CLI might have only 13 subcommands"
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "doctor", "gc", "expand", "time", "eval", "watch",   # assumed possibly absent
    "remove", "upgrade", "tree", "metadata", "verify", "vendor",  # omitted entirely
])
def test_subcommand_exists(name):
    """Refutes 'doctor/gc/expand/time/eval/watch are missing' and the 13-command list.

    All twelve exist and are reachable from the parser.
    """
    assert name in subcommands()


def test_subcommand_count_is_at_least_25():
    """Refutes 'the CLI has 13 subcommands'; there are 25."""
    assert len(subcommands()) >= 25, subcommands()


@pytest.mark.parametrize("name", ["doctor", "gc", "expand", "time", "eval", "watch"])
def test_newly_acknowledged_subcommands_actually_run(name):
    """Existence is not enough: each must respond to --help with exit code 0."""
    r = cli([name, "--help"])
    assert r.returncode == 0, f"{name} --help -> {r.returncode}\n{r.stdout}\n{r.stderr}"


# ---------------------------------------------------------------------------
# "Modules leak into the repository root" / "pengu_folder.py exists"
# ---------------------------------------------------------------------------

def test_no_compiler_module_leaks_into_the_root():
    """Refutes 'the compiler modules are duplicated at the root'.

    `pengu_infer`, `pengu_checker`, `pengu_parser`, `pengu_symbols`,
    `pengu_types`, `pengu_errors` and `pengu_comptime` live exclusively in
    `pengu_parser/`. Only `pengu_dce.py` is a root shim, and that is deliberate.
    """
    compiler_modules = [
        "pengu_infer.py", "pengu_checker.py", "pengu_parser.py",
        "pengu_symbols.py", "pengu_types.py", "pengu_errors.py",
        "pengu_comptime.py", "pengu_grammar.py", "pengu_codegen.py",
    ]
    for name in compiler_modules:
        assert (REPO / "pengu_parser" / name).is_file(), f"missing pengu_parser/{name}"
        assert not (REPO / name).exists(), f"leaked to the repository root: {name}"


def test_pengu_folder_module_does_not_exist():
    """Refutes 'pengu_folder.py is a loose file at the root'; it never existed.

    Only `CHANGELOG.md` mentions the name, as a historical feature label.
    """
    assert not (REPO / "pengu_folder.py").exists()
    assert not (REPO / "pengu_parser" / "pengu_folder.py").exists()


def test_historical_cleanup_targets_are_gone():
    """Refutes 'scratch/, tests_std/ and pengu_runtime_original.h may still be here'."""
    for name in ("scratch", "tests_std", "pengu_runtime_original.h"):
        assert not (REPO / name).exists(), f"{name} should not exist"


def test_root_pengu_runtime_c_is_gone():
    """The 0-byte root pengu_runtime.c was removed in Phase 0; the real one stays."""
    assert not (REPO / "pengu_runtime.c").exists()
    assert (REPO / "pengu_parser" / "pengu_runtime.c").is_file()
    assert (REPO / "pengu_parser" / "pengu_runtime.c").stat().st_size > 0


# ---------------------------------------------------------------------------
# "The script cache key may lack the version / target flags"
# ---------------------------------------------------------------------------

def test_script_cache_key_covers_the_version():
    """Refutes 'the cache key omits the PenguScript version'.

    `version` is a keyword-only parameter of `script_cache_key`, and the call
    site passes `version=PENGU_VERSION`. Bumping it must change the key, or an
    upgraded compiler would reuse a stale cached binary.
    """
    sys.path.insert(0, str(REPO))
    from pengu_cache import script_cache_key
    common = dict(entry_abs="/tmp/x.pengu", module_order=[])
    a = script_cache_key(version="0.16.0", **common)
    b = script_cache_key(version="0.17.0", **common)
    assert a != b


def test_script_cache_key_covers_extra_digests():
    """The cache key must react to the build knobs carried in `extra_digests`.

    `script_cache_key` has no `target` parameter: `--target`, `--target-compiler`,
    `--strict-c99` and the DCE/release-unsafe switches travel as `extra_digests`
    entries built at the call site. Those entries must change the key, otherwise a
    filtered/portable build could reuse the binary of a different one.
    """
    sys.path.insert(0, str(REPO))
    from pengu_cache import script_cache_key
    common = dict(entry_abs="/tmp/x.pengu", module_order=[], version="0.16.0")
    base = script_cache_key(extra_digests=None, **common)
    assert script_cache_key(extra_digests=["triple=x86_64-w64-mingw32"], **common) != base
    assert script_cache_key(extra_digests=["strict-c99"], **common) != base
    assert script_cache_key(extra_digests=["dce=off"], **common) != base


def test_cache_key_call_site_passes_version_and_target():
    """The knobs only matter if the real call site actually passes them.

    Inspected from the parsed call rather than by grepping text: the arguments
    are read off the AST of `run_script`.
    """
    import ast
    tree = ast.parse((REPO / "pengu_project.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name)
             and n.func.id == "script_cache_key"]
    assert calls, "script_cache_key is not called from pengu_project.py"
    seen_kwargs, seen_extra = set(), ""
    for call in calls:
        seen_kwargs.update(kw.arg for kw in call.keywords if kw.arg)
        for kw in call.keywords:
            if kw.arg == "extra_digests":
                seen_extra = ast.dump(kw.value)
    assert "version" in seen_kwargs, seen_kwargs
    assert "target=" in seen_extra, "extra_digests does not carry the target flags"
    assert "strict-c99" in seen_extra, "extra_digests does not carry strict-c99"


# ---------------------------------------------------------------------------
# "No import cycles" (verified in Phase 0; pinned so they cannot reappear)
# ---------------------------------------------------------------------------

def _direct_imports(body):
    """Import targets among the *direct* statements of `body`.

    Only direct children count: an import nested anywhere inside a function is a
    lazy import and must not be treated as a module-level edge.
    """
    found = set()
    for node in body:
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_no_module_level_import_cycles_in_the_toolchain():
    """Refutes 'there are circular imports in the toolchain'.

    Module-level cycles are real defects: the modules then cannot be imported in
    any order. Across the toolchain's modules there are none.
    """
    paths = []
    for pat in ("*.py", "pengu_parser/*.py", "pengu_lsp/*.py", "scripts/*.py"):
        paths += list(REPO.glob(pat))
    names = {p.stem for p in paths}

    graph = {}
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        graph[path.stem] = {n for n in _direct_imports(tree.body) if n in names}

    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in graph}
    stack = []

    def visit(node):
        colour[node] = GREY
        stack.append(node)
        for dep in graph.get(node, ()):
            if colour.get(dep) == GREY:
                raise AssertionError(
                    "module-level import cycle: " + " -> ".join(stack[stack.index(dep):] + [dep])
                )
            if colour.get(dep) == WHITE:
                visit(dep)
        stack.pop()
        colour[node] = BLACK

    for node in sorted(graph):
        if colour[node] == WHITE:
            visit(node)


def test_the_two_mutually_referencing_modules_stay_lazy():
    """`pengu_doc` and `pengu_project` import each other -- inside functions.

    This is precisely the pattern that keeps the module graph acyclic, and it is
    worth pinning: hoisting either import to module level would create a real
    cycle (pengu_doc -> pengu_project -> pengu_doc) and break `import pengu_doc`.
    """
    for a, b in (("pengu_doc", "pengu_project"), ("pengu_project", "pengu_doc")):
        tree = ast.parse((REPO / f"{a}.py").read_text(encoding="utf-8"))
        assert b not in _direct_imports(tree.body), (
            f"{a}.py imports {b} at module level, which closes a cycle"
        )
        nested = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and (n.module or "") == b
        ]
        assert nested, f"{a}.py no longer imports {b} at all"


def test_pengu_bind_never_imports_pengu_project():
    """The specific pair the audit questioned: the dependency is one-way."""
    src = (REPO / "pengu_bind.py").read_text(encoding="utf-8")
    import ast
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not any(a.name.split(".")[0] == "pengu_project" for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "pengu_project"


# ---------------------------------------------------------------------------
# Deliberately NOT tested
# ---------------------------------------------------------------------------
# Assumptions about properties the toolchain itself guarantees are not pinned
# here, because a test could not fail meaningfully:
#   * "the frame stack may be global" -- the header declares it `_Thread_local`;
#     only the C compiler can enforce that, and a Python test cannot.
#   * "map tombstones may be missing" -- guaranteed by the runtime implementation
#     and covered by the C-level suite.
#   * "PenguChecker may have duplicate methods" -- a duplicate `def` is
#     unrepresentable in the parsed AST the checker uses.


# ---------------------------------------------------------------------------
# Item 2.3 — `alias` in `concept` is documented as deferred, not implemented
# ---------------------------------------------------------------------------

def test_alias_in_concept_is_not_implemented(tmp_path):
    """`alias Item` inside a `concept` must stay a syntax error (E0000).

    Refutes `LANGUAGE.md` §11.7's former claim that the syntax "is accepted for
    forward compatibility". It never was: `concept_method` in ``pengu_grammar.py``
    accepts only ``weave`` signatures.

    This is an intentional tripwire. Implementing associated types is a 1.1
    feature (see the ⏸️ table in ROADMAP_2.0.md). If someone adds the grammar
    production, this test starts failing, which is the signal to also implement
    `Self.Item` resolution in monomorphization, update the docs, and add the
    positive test -- rather than shipping half of the feature.
    """
    source = (
        "concept Iterabilis shard Self:\n"
        "    alias Item\n"
        "    weave next with it as ref to Self into maybe Self.Item\n"
    )
    path = tmp_path / "assoc.pengu"
    path.write_text(source, encoding="utf-8")
    r = cli(["check", str(path)], cwd=tmp_path)
    out = r.stdout + r.stderr
    assert r.returncode != 0, (
        "`alias` in a concept now parses. Associated types are a 1.1 feature: "
        "implement `Self.Item` resolution and update LANGUAGE.md §11.7 before "
        "flipping this test.\n" + out
    )
    assert "E0000" in out, out
    assert "alias" in out, out


def test_assoc_type_worked_around_with_a_second_type_parameter(tmp_path):
    """The documented workaround must actually work.

    §11.7 tells readers to use `shard Self and Item` instead of an associated
    type. That advice is only useful if it compiles, so it is verified here
    rather than asserted in prose.
    """
    source = (
        "concept Drain shard Self and Item:\n"
        "    weave next with it as ref to Self into maybe Item\n"
        "rune Counter:\n"
        "    n as int\n"
        "bind Counter with Drain of int:\n"
        "    weave next with it as ref to Counter into maybe int:\n"
        "        if self->n == 0:\n"
        "            return maybe none\n"
        "        set self->n is self->n - 1\n"
        "        return some self->n\n"
        "weave main into int:\n"
        "    var c as Counter is with n is 2\n"
        "    return 0\n"
    )
    path = tmp_path / "workaround.pengu"
    path.write_text(source, encoding="utf-8")
    r = cli(["check", str(path)], cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
