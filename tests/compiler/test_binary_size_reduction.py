"""Size-reduction invariants that are cheap enough to run on every CI job.

The dead-code pass and the build manager each own a table that maps a runtime
``PENGU_ENABLE_*`` gate to the ``std`` module that switches it on
(``pengu_codegen/bundle.py`` and ``pengu_project.py``).  They cannot import each
other, so the only thing that keeps them in agreement is this test.

The rest of the file pins the *inputs* of the pass (the standard-library roots),
not a byte budget: budget tests live next to the benchmark that produces the
measurement, so a compiler change cannot make a budget fail for an unrelated
reason.
"""
from __future__ import annotations

import os
from pathlib import Path

from pengu_parser.pengu_codegen.bundle import FEATURE_GATE_MODULES


def test_feature_gate_tables_agree():
    import pengu_project

    assert FEATURE_GATE_MODULES == pengu_project._FEATURE_GATE_MODULES, (
        "bundle.py and pengu_project.py disagree on which std module enables "
        "which PENGU_ENABLE_* gate; a bundle would emit a gate the linker "
        "does not enable (or vice versa)"
    )


def test_every_gate_has_a_module():
    for gate, module in FEATURE_GATE_MODULES.items():
        assert gate.startswith("PENGU_ENABLE_"), gate
        assert module and not module.endswith(".pengu"), module


def test_standard_library_roots_include_the_checkout(pengu_root):
    from pengu_parser.pengu_dce import resolved_std_roots

    roots = [os.path.normcase(os.path.abspath(p))
             for p in resolved_std_roots()]
    checkout_std = os.path.normcase(os.path.abspath(str(pengu_root / "std")))
    assert checkout_std in roots, (
        "resolved_std_roots() must always know the checkout's std/, or the "
        "DCE pass silently stops pruning in a source build"
    )


def test_installed_std_root_is_discovered(monkeypatch, tmp_path):
    from pengu_parser.pengu_dce import resolved_std_roots

    custom = tmp_path / "prefix" / "share" / "pengu" / "std"
    custom.mkdir(parents=True)
    monkeypatch.setenv("PENGU_STD_DIR", str(custom))
    roots = [os.path.normcase(os.path.abspath(p)) for p in resolved_std_roots()]
    assert os.path.normcase(os.path.abspath(str(custom))) in roots


# ---------------------------------------------------------------------------
# Size budgets (Phase 1)
#
# These are not byte-perfect golden values: they are ceilings that catch a
# regression back to "emit every instance of the transitive closure".  The
# realistic values after the exact-reachability pass are far below them; the
# margin absorbs a different `#line` path length and future small additions.
# Phase 4 (type/derived pruning) will lower them further, not raise them.
# ---------------------------------------------------------------------------

import pytest


def _expand_bytes(pengu_cli, tmp_path, source: str, tag: str,
                  extra: tuple[str, ...] = ()) -> tuple[int, str]:
    script = tmp_path / f"{tag}.pengu"
    script.write_text(source, encoding="utf-8")
    out = tmp_path / f"{tag}.c"
    res = pengu_cli("expand", str(script), "-o", str(out), *extra)
    assert res.returncode == 0, res.stderr
    return out.stat().st_size, out.read_text(encoding="utf-8")


@pytest.mark.slow
def test_hello_bundle_stays_small(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.spark

weave main into int:
    calling spark.println with "hello"
    return 0
""", "hello")
    assert size < 5_000, f"hello is {size} bytes"
    assert "spark_println" in c


@pytest.mark.slow
def test_unused_json_import_stays_small(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.json

weave main into int:
    return 0
""", "json_unused")
    assert size < 12_000, f"unused std.json is {size} bytes"
    assert "some_of_int" not in c


@pytest.mark.slow
def test_cipher_one_function_stays_small(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.cipher

weave main into int:
    var s as string is calling cipher.encode_base64 with "hi"
    banish s
    return 0
""", "cipher_one")
    assert size < 16_000, f"cipher one-function bundle is {size} bytes"
    assert "cipher_encode_base64" in c
    assert "some_of_int" not in c


@pytest.mark.slow
def test_stdlib_ops_stays_small(pengu_cli, tmp_path):
    bench = Path(__file__).resolve().parents[2] / "benches" / "stdlib_ops.pengu"
    out = tmp_path / "stdlib_ops.c"
    res = pengu_cli("expand", str(bench), "-o", str(out))
    assert res.returncode == 0, res.stderr
    size = out.stat().st_size
    assert size < 15_000, f"benches/stdlib_ops is {size} bytes"


@pytest.mark.slow
def test_unused_petitio_import_stays_small(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.petitio

weave main into int:
    return 0
""", "petitio_unused")
    assert size < 22_000, f"unused std.petitio is {size} bytes"
    assert "some_of_int" not in c


@pytest.mark.slow
def test_prune_types_unused_json_budget(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.json

weave main into int:
    return 0
""", "json_pruned", extra=("--prune-types",))
    assert size < 4_000, f"pruned unused std.json is {size} bytes"
    assert "--prune-types" in c


@pytest.mark.slow
def test_prune_types_cipher_budget(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.cipher

weave main into int:
    var s as string is calling cipher.encode_base64 with "hi"
    banish s
    return 0
""", "cipher_pruned", extra=("--prune-types",))
    assert size < 8_000, f"pruned cipher one-function bundle is {size} bytes"
    assert "cipher_encode_base64" in c


@pytest.mark.slow
def test_prune_types_petitio_budget(pengu_cli, tmp_path):
    size, c = _expand_bytes(pengu_cli, tmp_path, """
import std.petitio

weave main into int:
    return 0
""", "petitio_pruned", extra=("--prune-types",))
    assert size < 6_000, f"pruned unused std.petitio is {size} bytes"
