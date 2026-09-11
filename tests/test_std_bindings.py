"""Regressions found while auditing std/ for production use.

Covers: single-element array literals, UTF-8 BOM tolerance and cross-module
binding imports (raylib/raygui, nanosvg/nanosvgrast).
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import BUILD_DIR, REPO, compile_run, gen_bundle, requires_runtime


def bundle_project(source: str, tag: str = "proj") -> str:
    """Bundles a program through the real builder (imports resolved).

    ``gen_bundle`` only checks the files it is given, so std imports need the
    project builder to be loaded.
    """
    from pengu_project import PenguBuilder, ProjectConfig

    d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=str(BUILD_DIR)))
    try:
        entry = d / f"{tag}.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
        return Path(bundle_path).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(d, ignore_errors=True)



class TestSingleElementArrayLiteral:
    """`[0]` is an initializer list, not the scalar 0 (ConstFolder collapsed it)."""

    def test_single_element_is_braced(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var p as array of byte with size 4 is [0]\n"
            "    return 0\n"
        )
        assert "uint8_t p[4] = { 0 };" in code

    def test_single_non_zero_element_is_braced(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var a as array of int with size 3 is [7]\n"
            "    return 0\n"
        )
        assert "int32_t a[3] = { 7 };" in code

    def test_multi_element_unchanged(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var a as array of int with size 3 is [1, 2]\n"
            "    return 0\n"
        )
        assert "int32_t a[3] = { 1, 2 };" in code

    @requires_runtime
    def test_single_element_array_runs(self):
        res = compile_run(
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var p as array of byte with size 4 is [0]\n"
            "    var a as array of int with size 3 is [7]\n"
            "    calling spark.println with ((a at 0) to string)\n"
            "    return 0\n",
            tag="array_single",
        )
        assert "7" in res.stdout


class TestBareLiteralStatements:
    """`x[0]` is not Pengu indexing: it used to compile as a stray '[0]'."""

    def test_c_style_indexing_is_rejected(self):
        with pytest.raises(PenguError) as info:
            PenguChecker(base_dir=".").check(
                PenguParser().parse(
                    "weave main into int:\n"
                    "    var arr as array of int with size 3 is [10, 20, 30]\n"
                    "    var p as ref to void is sigil of arr[0]\n"
                    "    return 0\n"
                ),
                source="weave main into int:\n",
                filename="t.pengu",
            )
        assert getattr(info.value, "code", "") == "E0005"
        assert "is not a statement" in str(info.value)
        assert "'x at i'" in (info.value.help or "")

    def test_bare_array_literal_is_rejected(self):
        with pytest.raises(PenguError) as info:
            PenguChecker(base_dir=".").check(
                PenguParser().parse("weave main into int:\n    [1, 2]\n    return 0\n"),
                source="weave main into int:\n",
                filename="t.pengu",
            )
        assert "An array literal is not a statement" in str(info.value)

    def test_proper_indexing_is_fine(self):
        code = gen_bundle(
            "weave main into int:\n"
            "    var arr as array of int with size 3 is [10, 20, 30]\n"
            "    var p as ref to void is sigil of (arr at 0)\n"
            "    return 0\n"
        )
        assert "int32_t arr[3] = { 10, 20, 30 };" in code


class TestBomTolerance:
    """Editors on Windows write a UTF-8 BOM; it must not break parsing."""

    def test_bom_is_ignored(self):
        tree = PenguParser().parse("\ufeffweave main into int:\n    return 0\n")
        assert tree is not None

    def test_bom_in_expression(self):
        tree = PenguParser().parse_expr("\ufeff1 + 2")
        assert tree is not None

    def test_bomless_source_still_parses(self):
        tree = PenguParser().parse("weave main into int:\n    return 0\n")
        assert tree is not None


class TestCrossModuleBindings:
    """Bindings that include another header must import its binding."""

    def test_raylib_and_raygui_compile_together(self):
        # raygui.h includes raylib.h: its binding re-declares the KEY_* defines
        # as consts, which must not collide with raylib's KeyboardKey omen.
        code = bundle_project(
            "import std.raylib\n"
            "import std.raygui\n\n"
            "weave main into int:\n"
            "    return 0\n",
            tag="raylib_raygui",
        )
        assert "raylib.h" in code and "raygui.h" in code

    def test_raygui_uses_raylib_types(self):
        # 'Rectangle' comes from std.raylib; without the import raygui's
        # signature would expect a placeholder 'Rectangle_any'.
        code = bundle_project(
            "import std.raylib\n"
            "import std.raygui\n\n"
            "weave main into int:\n"
            "    var b as Rectangle is with x is 1.0, y is 2.0, width is 3.0, height is 4.0\n"
            "    var r as int is calling raygui.Button with b, \"ok\"\n"
            "    return 0\n",
            tag="raygui_types",
        )
        assert "GuiButton" in code

    def test_nanosvgrast_uses_nanosvg_types(self):
        code = bundle_project(
            "import std.nanosvg\n"
            "import std.nanosvgrast\n\n"
            "weave main into int:\n"
            "    var r as ref to NSVGrasterizer is calling nanosvgrast.CreateRasterizer\n"
            "    return 0\n",
            tag="nanosvg_types",
        )
        assert "nsvgCreateRasterizer" in code

    def test_conflicting_constant_values_are_still_reported(self):
        # whisper's LOG_INFO is 2, raylib's TraceLogLevel_LOG_INFO is 3: a real
        # collision, unlike raygui's identical KEY_* defines.
        with pytest.raises(PenguError) as info:
            bundle_project(
                "import std.raylib\n"
                "import std.whisper\n\n"
                "weave main into int:\n"
                "    return 0\n",
                tag="conflict",
            )
        exc = info.value
        assert getattr(exc, "code", "") == "E0046"
        assert "collides with the top-level constant" in str(exc)
