#!/usr/bin/env python3
"""Consolidated language-FEATURE tests for the PenguScript compiler.

This file ports the assertions from the historical per-feature test files
(drawn from the previous, removed suite) into one pytest module,
grouped by feature:

* BytesOfFFI       <- test_feature_bytes_of.py
* SomeOrdChr       <- test_feature_some_ord_chr.py
* IndexedFor       <- test_feature_indexed_for.py (+ indexed-for e2e from test_features_e2e.py)
* MapLiterals      <- test_feature_map_literals.py (+ map e2e from test_features_e2e.py)
* ImportAlias      <- test_feature_import_alias.py (+ alias e2e from test_features_e2e.py)
* StaticVar        <- test_feature_static_var.py (+ static e2e from test_features_e2e.py)
* WhenCompileTime  <- test_feature_when.py (+ platform e2e from test_features_e2e.py)
* WhenMain         <- test_when_main.py ('main' compile-time variable + CLI script mode)
* StringOmens      <- test_feature_string_omens.py (+ omen e2e from test_features_e2e.py)
* EmbeddedTests    <- test_feature_tests.py (+ --test runner e2e from test_features_e2e.py)
* WeaveFunctionPointers <- test_feature_c_calls_weave.py
* PenguCoroutine   <- test_feature_pengu_coroutine.py
* ControlFlow      <- test_for_comp_bool.py (bool guards in for-comprehensions)
* EnchantingMethodCalls <- test_enchanting_call.py
* DeferBanish / EscapeAnalysis / Memory <- test_defer_banish.py,
    test_escape_analysis.py, test_11_memory.py

Pure parse / check / codegen tests need no C toolchain. Compile+run tests are
marked with ``@requires_runtime`` (and ``@requires_lib("pengu_stb")`` when the
program links the minicoro shim inside ``libpengu_stb.a``).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_comptime import CompileTimeEnv
from pengu_parser.pengu_errors import (  # noqa: F401
    InvalidMemoryOpError,
    PenguError,
    SemanticError,
    TypeMismatchError,
    UndefinedIdentifierError,
)
from pengu_parser.pengu_parser import PenguParser

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    check_ok,
    compile_run,
    gen_bundle,
    is_windows,
    requires_cc,
    requires_lib,
    requires_runtime,
    runtime_link_flags,
    runtime_tail_flags,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _check(source: str, filename: str = "t.pengu", env=None,
           base_dir=None) -> PenguChecker:
    """Parses + type-checks `source` (optionally under a compile-time env)."""
    parser = PenguParser()
    checker = PenguChecker(base_dir=base_dir or str(REPO), compile_env=env)
    checker.check(parser.parse(source), source=source, filename=filename)
    return checker


def _check_error(source: str, filename: str = "t.pengu", code=None,
                 contains=None, env=None, base_dir=None, exc=PenguError):
    """Asserts `source` fails semantic check; returns the raised error."""
    parser = PenguParser()
    checker = PenguChecker(base_dir=base_dir or str(REPO), compile_env=env)
    tree = parser.parse(source)
    with pytest.raises(exc) as caught:
        checker.check(tree, source=source, filename=filename)
    if code is not None:
        assert getattr(caught.value, "code", None) == code, f"{caught.value}"
    if contains is not None:
        text = f"{caught.value}"
        assert contains in text, text
    return caught.value


def _bundle(source: str, filename: str = "t.pengu", env=None, is_test: bool = False,
            extra_files=None, entry_main_mode: bool = False,
            entry_file=None) -> str:
    """Bundles source(s) to C text with a custom compile-time env / mode."""
    if env is None:
        env = CompileTimeEnv(os_name="windows", arch="x64", compiler="gcc")
    files = [(filename, source)] + list(extra_files or [])
    parser = PenguParser()
    checker = PenguChecker(base_dir=str(REPO), compile_env=env)
    trees = {}
    for fname, code in files:
        tree = parser.parse(code)
        checker.check(tree, source=code, filename=fname)
        trees[fname] = tree
    cg = PenguCodegen(checker.symbols, [f for f, _ in files], str(REPO),
                      compile_env=env)
    cg.entry_main_mode = entry_main_mode
    if entry_file is not None:
        cg.entry_file = entry_file
    for fname, _ in files:
        cg.collect_declarations([(fname, trees[fname])])
    return cg.generate_bundle(is_test=is_test)


def _compile_run(source: str, tag: str = "t", entry: str = "main.pengu",
                 extra_files=None, is_test: bool = False,
                 entry_as_main: bool = False, extra_libs=None,
                 timeout: int = 240) -> subprocess.CompletedProcess:
    """Bundles + gcc-compiles + runs a Pengu program.

    Like ``tests.conftest.compile_run`` but supports extra module files,
    integrated-test codegen mode (``is_test``) and the entry-as-main
    compile-time variable (``entry_as_main``).
    """
    from pengu_project import PenguBuilder, ProjectConfig

    assert shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=str(BUILD_DIR)))
    try:
        files = dict(extra_files or {})
        files[entry] = source
        for name, code in files.items():
            p = d / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(code, encoding="utf-8")
        entry_path = d / entry
        cfg = ProjectConfig(entry=str(entry_path), base_dir=str(REPO),
                            output="c")
        builder = PenguBuilder(cfg)
        builder.is_test_mode = is_test
        builder.entry_as_main = entry_as_main
        bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))

        cc = ("gcc" if shutil.which("gcc")
              else "clang" if shutil.which("clang") else "cc")
        exe = d / ("bin.exe" if os.name == "nt" else "bin")
        cmd = [cc, str(bundle_path),
               f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
               f"-L{BUILD_LIB}"]
        cmd += runtime_link_flags()
        if extra_libs:
            cmd += list(extra_libs)
        cmd += runtime_tail_flags()
        cmd += ["-o", str(exe)]

        res = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True,
                             timeout=timeout)
        assert res.returncode == 0, (
            f"Compilation failed ({res.returncode}):\n{res.stderr}\n{res.stdout}"
        )
        run_res = subprocess.run([str(exe)], cwd=str(REPO), capture_output=True,
                                 text=True, timeout=timeout)
        return run_res
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# 'bytes of' FFI keyword
# ---------------------------------------------------------------------------


class TestBytesOfFFI:
    """'bytes of' string -> read-only byte pointer FFI casts."""

    def test_string_variable_produces_byte_pointer_cast(self):
        code = """declare peek_bytes with p as ref to byte into int

weave main into int:
    var s as string is "hello"
    var view as ref to byte is bytes of s
    return calling peek_bytes with view
"""
        bundle = gen_bundle(code)
        assert "uint8_t* view = ((uint8_t*)(((s)).data));" in bundle

    def test_literal_string_also_works(self):
        code = """declare peek_bytes with p as ref to byte into int

weave main into int:
    var view as ref to byte is bytes of "abc"
    return 0
"""
        bundle = gen_bundle(code)
        assert "((uint8_t*)((" in bundle
        assert ").data));" in bundle

    def test_non_string_operand_rejected(self):
        code = """weave main into int:
    var n as int is 5
    var view as ref to byte is bytes of n
    return 0
"""
        _check_error(code, contains="bytes of")

    def test_weave_parameter_chain(self):
        # passing 'bytes of' straight into a call argument is valid
        code = """declare hash_bytes with data as ref to byte and len as int into i64

weave digest with msg as string into i64:
    var view as ref to byte is bytes of msg
    return calling hash_bytes with view and (msg length)
"""
        bundle = gen_bundle(code)
        assert "hash_bytes(view" in bundle

    def test_byte_array_is_writable_pointer(self):
        code = """declare store_bytes with p as ref to byte into int

weave main into int:
    var buf as array of byte with size 8 is array of byte with size 8
    var view as ref to byte is bytes of buf
    return calling store_bytes with view
"""
        bundle = gen_bundle(code)
        assert "uint8_t buf[8]" in bundle
        assert "uint8_t* view = (&((buf)[0]));" in bundle

    def test_non_byte_array_rejected(self):
        code = """weave main into int:
    var nums as array of int with size 4 is array of int with size 4
    var view as ref to byte is bytes of nums
    return 0
"""
        _check_error(code, contains="bytes of")

    def test_weave_name_decays_to_c_function_pointer(self):
        # Passing a weave where a 'ref to weave' alias is expected produces a
        # plain C function pointer at the call site.
        code = """alias Cb as ref to weave with v as int into void

declare register_cb with cb as Cb into void

weave handler with x as int into void:
    var y as int is x + 1

weave main into int:
    calling register_cb with handler
    return 0
"""
        bundle = gen_bundle(code)
        assert "register_cb(handler);" in bundle


# ---------------------------------------------------------------------------
# 'some expr', 'ord expr', 'chr expr' and insignia exemptions
# ---------------------------------------------------------------------------


class TestSomeOrdChr:
    """Unblocking extensions: 'some', 'ord', 'chr', insignia for primitives."""

    def test_some_types_as_maybe(self):
        code = """weave f into void:
  var m as maybe int is some 42
  var s as maybe string is some "hi"
  var e as maybe float is some 1.5
"""
        check_ok(code)

    def test_ord_returns_int_and_chr_string(self):
        code = """weave f into void:
  var code_val as int is ord "A"
  var ch as string is chr 66
"""
        check_ok(code)

    @pytest.mark.parametrize(
        "bad",
        [
            'weave f into void:\n  var x as int is ord "AB"\n',
            "weave f into void:\n  var x as string is chr 300\n",
            "weave f into void:\n  var x as int is ord 7\n",
            'weave f into void:\n  var x as string is chr "a"\n',
        ],
        ids=["ord-multi-char", "chr-out-of-range", "ord-non-string",
             "chr-non-int"],
    )
    def test_ord_chr_type_mismatches_rejected(self, bad):
        _check_error(bad, exc=TypeMismatchError)

    def test_some_emits_heap_allocation(self):
        code = """weave f into void:
  var m as maybe int is some 7
"""
        c = gen_bundle(code)
        assert "pengu_sigil_alloc" in c
        assert ".is_present = true" in c

    def test_runtime_ord_chr_emission(self):
        # A non-constant operand prevents const-folding, exercising the C paths.
        code = """weave f with v as int into void:
  var ch as string is chr v
"""
        c = gen_bundle(code)
        assert "pengu_string_from_char" in c

    def test_insignia_exemption_for_primitive_methods(self):
        code = """insignia pengu_

weave module_helper into void:
  calling print with "x"

enchanting string:
  weave my_probe into string:
    var sv as string is essence of self
    return sv
"""
        c = gen_bundle(code)
        # module-level weave gets the insignia prefix
        assert "void pengu_module_helper(void)" in c
        # primitive-type method keeps its plain (unprefixed) C name
        assert "PenguString string_my_probe(PenguString*" in c
        assert "pengu_string_my_probe(PenguString*" not in c

    @requires_runtime
    def test_compile_and_run(self):
        code = """weave main into void:
  var m as maybe int is some 42
  if m.is_present:
    if m.value == 42:
      var s as maybe string is some "hello"
      if s.is_present:
        if s.value == "hello":
          var c as string is chr 66
          var o as int is ord "A"
          var msg as string is "SOME_OK " + c + (o to string)
          calling print with msg
"""
        res = compile_run(code, tag="some")
        assert res.returncode == 0, res.stderr
        assert "SOME_OK B65" in res.stdout


# ---------------------------------------------------------------------------
# Indexed iteration: 'for i, v in collection'
# ---------------------------------------------------------------------------


class TestIndexedFor:
    """Indexed iteration 'for i, v in collection' (and discard forms)."""

    def test_indexed_for_checks(self):
        code = """weave sum with arr as array of int with size 3 into int:
  var acc as int is 0
  for i, v in arr:
    set acc is acc + i * v
  return acc
"""
        check_ok(code)

    def test_emits_indexed_loop(self):
        code = """weave test_for with arr as array of int with size 3 into void:
  var acc as int is 0
  for i, val in arr:
    set acc is acc + val
"""
        c = gen_bundle(code)
        assert "for (int32_t i = 0; i < 3; i++) {" in c
        assert "int32_t val = (arr)[i];" in c

    def test_single_name_still_works(self):
        code = """weave test_for with arr as array of int with size 3 into void:
  var acc as int is 0
  for v in arr:
    set acc is acc + v
"""
        c = gen_bundle(code)
        assert "for (int32_t v" not in c  # classic form keeps its temp counter
        assert "int32_t v = (arr)[" in c

    def test_discard_forms_parse_and_compile(self):
        code = """weave test_for with arr as array of int with size 3 into void:
  var n as int is 0
  for i, _ in arr:
    set n is n + i
  for _, v in arr:
    set n is n + v
"""
        c = gen_bundle(code)
        assert "for (int32_t i = 0; i < 3; i++) {" in c

    def test_discard_symbol_not_defined(self):
        # '_' must not be a usable symbol after an indexed-for loop
        bad = """weave test_for with arr as array of int with size 3 into void:
  for i, _ in arr:
    var x as int is _
"""
        _check_error(bad, exc=UndefinedIdentifierError)

    def test_duplicate_index_and_element_rejected(self):
        code = """weave test_for with arr as array of int with size 3 into void:
  for i, i in arr:
    set x is i
"""
        _check_error(code, exc=SemanticError, contains="index and element")

    def test_indexed_for_over_list(self):
        code = """weave test_for with nums as list of int into void:
  var acc as int is 0
  for i, v in nums:
    set acc is acc + i * v
"""
        c = gen_bundle(code)
        assert "for (int32_t i = 0; i < (nums).len; i++) {" in c
        assert "int32_t v = (*(int32_t*)pengu_list_at(&(nums), i));" in c

    @requires_runtime
    def test_runtime_indexed_for_sums(self):
        code = """weave sum_indexed with arr as array of int with size 3 into int:
  var acc as int is 0
  for i, val in arr:
    set acc is acc + i * val
  return acc

weave main into void:
  var data as array of int with size 3 is array of int with size 3
  set data at 0 is 10
  set data at 1 is 20
  set data at 2 is 30
  var r as int is calling sum_indexed with data
  var msg as string is "FAIL"
  if r == 80:
    set msg is "IDX_OK"
  calling print with msg
"""
        res = compile_run(code, tag="foridx")
        assert res.returncode == 0, res.stderr
        assert "IDX_OK" in res.stdout


# ---------------------------------------------------------------------------
# Map literals: '{ key: value, ... }'
# ---------------------------------------------------------------------------


class TestMapLiterals:
    """Map literals, heterogeneous checks and C emission."""

    def test_string_int_map_emits_map_new(self):
        code = """weave m into void:
  let scores is { "Alice": 100, "Bob": 90 }
"""
        c = gen_bundle(code)
        assert "PenguString" in c
        assert "pengu_map_new(sizeof(PenguString), sizeof(int32_t))" in c

    def test_identifier_keys_become_strings(self):
        # host (string) vs port (int) values are not homogenous -> error
        bad = """weave m into void:
  let cfg is { host: "localhost", port: 8080 }
"""
        _check_error(bad, exc=TypeMismatchError)

        good = """weave m into void:
  let cfg is { host: "localhost", port: "8080" }
"""
        check_ok(good)

    def test_empty_map_requires_annotation(self):
        bad = """weave m into void:
  let e is {}
"""
        _check_error(bad, exc=TypeMismatchError, contains="Empty map literal")

        good = """weave m into void:
  let e as map of string to int is {}
"""
        check_ok(good)

    def test_duplicate_key_rejected(self):
        code = """weave m into void:
  let e is { "x": 1, "x": 2 }
"""
        _check_error(code, exc=SemanticError, contains="Duplicate key")

    def test_heterogeneous_values_rejected(self):
        code = """weave m into void:
  let e is { "a": 1, "b": "two" }
"""
        _check_error(code, exc=TypeMismatchError)

    def test_emits_map_new_and_put(self):
        code = """weave m into void:
  let scores is { "Alice": 100, "Bob": 90 }
"""
        c = gen_bundle(code)
        assert "pengu_map_new(sizeof(PenguString), sizeof(int32_t))" in c
        assert "pengu_map_put(&" in c
        assert 'pengu_string_from_cstr("Alice")' in c

    def test_wrong_annotation_rejected(self):
        code = """weave m into void:
  let e as map of string to string is { "x": 1 }
"""
        _check_error(code, exc=TypeMismatchError)

    @requires_runtime
    def test_runtime_map_literal_get_put(self):
        code = """weave main into void:
  var m as map of string to int is { "Alice": 100, "Bob": 90 }
  var v as int is calling m.get with "Alice"
  calling m.put with "Carol" and 70
  var ok as bool is calling m.contains with "Carol"
  var msg as string is "FAIL"
  if v == 100:
    if ok:
      set msg is "MAP_OK"
  calling print with msg
"""
        res = compile_run(code, tag="maplit")
        assert res.returncode == 0, res.stderr
        assert "MAP_OK" in res.stdout


# ---------------------------------------------------------------------------
# Import aliasing: 'import path as name'
# ---------------------------------------------------------------------------


class TestImportAlias:
    """'import path as name' bindings and symbol-table effects."""

    def test_alias_creates_import_symbol(self):
        checker = _check("import std.spark as sp\n", filename="main.pengu")
        sym = checker.symbols.lookup("sp")
        assert sym is not None
        assert sym.kind == "import"
        assert checker.symbols.lookup("spark") is None

    def test_no_alias_keeps_last_component(self):
        checker = _check("import std.spark\n", filename="main.pengu")
        assert checker.symbols.lookup("spark") is not None

    def test_alias_cannot_be_discard(self):
        _check_error("import std.spark as _\n", filename="main.pengu",
                     exc=SemanticError, contains="cannot be '_'")

    def test_alias_collision_rejected(self):
        code = "const sp as int is 1\nimport std.spark as sp\n"
        _check_error(code, filename="main.pengu", exc=SemanticError,
                     contains="conflicts with an existing symbol")

    @requires_runtime
    def test_runtime_import_alias(self):
        code = """import std.spark as sp

weave main into void:
  calling sp.println with "ALIAS_OK"
"""
        res = compile_run(code, tag="alias")
        assert res.returncode == 0, res.stderr
        assert "ALIAS_OK" in res.stdout


# ---------------------------------------------------------------------------
# Function-static variables: 'static var ...'
# ---------------------------------------------------------------------------


class TestStaticVar:
    """Function-static 'static var' storage and init semantics."""

    def test_static_counter_emits_static(self):
        code = """weave counter into int:
  static var count as int is 0
  set count is count + 1
  return count
"""
        c = gen_bundle(code)
        assert "static int32_t count = 0;" in c

    def test_static_var_is_mutable_and_typed(self):
        code = """weave counter into int:
  static var count as int is 0
  set count is count + 1
  return count
"""
        check_ok(code)

    def test_static_var_not_allowed_at_top_level(self):
        # top-level statement list does not accept static var; parse failure
        with pytest.raises(Exception):
            PenguParser().parse("static var x as int is 1\n")

    def test_static_var_nested_in_block_rejected(self):
        code = """weave f into int:
  if true:
    static var x as int is 0
  return 1
"""
        _check_error(code, exc=SemanticError, contains="function body")

    def test_static_array_rejected(self):
        code = """weave f into int:
  static var arr as array of int with size 3 is array of int with size 3
  return 1
"""
        _check_error(code, exc=SemanticError)

    def test_static_string_lazy_init(self):
        code = """weave log_it with msg as string into void:
  static var first as string is "first"
  calling print with first
"""
        c = gen_bundle(code)
        assert "static PenguString first;" in c
        assert "_initialized" in c

    @requires_runtime
    def test_runtime_static_var_persists(self):
        code = """weave counter into int:
  static var count as int is 0
  set count is count + 1
  return count

weave main into void:
  var a as int is calling counter
  var b as int is calling counter
  var c as int is calling counter
  var msg as string is "FAIL"
  if a == 1:
    if b == 2:
      if c == 3:
        set msg is "STATIC_OK"
  calling print with msg
"""
        res = compile_run(code, tag="statvar")
        assert res.returncode == 0, res.stderr
        assert "STATIC_OK" in res.stdout


# ---------------------------------------------------------------------------
# Compile-time 'when' clauses (statement, expression, top-level)
# ---------------------------------------------------------------------------


class TestWhenCompileTime:
    """Compile-time branch selection through the 'when' construct."""

    WINDOWS_ENV = CompileTimeEnv(os_name="windows", arch="x64", compiler="gcc")

    def test_statement_when_selects_branch(self):
        code = """weave main into void:
  when os == "windows":
    var msg as string is "win"
  else:
    var msg as string is "unix"
  calling print with msg
"""
        c = _bundle(code, env=self.WINDOWS_ENV)
        assert 'pengu_string_from_cstr("win")' in c
        assert "unix" not in c

    def test_statement_when_on_other_platform(self):
        code = """weave main into void:
  when os == "windows":
    var msg as string is "win"
  else:
    var msg as string is "unix"
  calling print with msg
"""
        c = _bundle(code, env=CompileTimeEnv(os_name="linux"))
        assert 'pengu_string_from_cstr("unix")' in c
        assert '"win"' not in c

    def test_top_level_when_filters_declarations(self):
        code = """when os == "windows":
  const PLAT as string is "win"
else:
  const PLAT as string is "unix"

weave main into void:
  calling print with PLAT
"""
        c = _bundle(code, env=self.WINDOWS_ENV)
        assert 'pengu_string_from_cstr("win")' in c
        assert '"unix"' not in c

    def test_when_expression(self):
        code = """weave main into void:
  let os_name is when os == "windows" then "Win" else "Unix"
"""
        c = _bundle(code, env=self.WINDOWS_ENV)
        assert 'pengu_string_from_cstr("Win")' in c
        assert "Unix" not in c

    def test_defined_and_cli_like_flags(self):
        code = """when defined(WEB):
  const A as int is 1
else:
  const A as int is 2

weave main into int:
  return A
"""
        c_on = _bundle(code, env=CompileTimeEnv(defines={"WEB": True}))
        assert "#define A 1" in c_on
        c_off = _bundle(code, env=CompileTimeEnv(defines={}))
        assert "#define A 2" in c_off

    def test_non_constant_condition_rejected(self):
        code = """weave main into void:
  var n as int is 1
  when n == 1:
    var a as int is 1
"""
        _check_error(code, env=self.WINDOWS_ENV, exc=SemanticError,
                     contains="compile-time")

    def test_branch_vars_visible_after_when(self):
        # 'when' behaves like textual substitution: declarations in the active
        # branch stay in the enclosing scope.
        code = """weave main into void:
  when os == "windows":
    var msg as string is "win"
  calling print with msg
"""
        _bundle(code, env=self.WINDOWS_ENV)  # must not raise undefined 'msg'

    @requires_runtime
    def test_runtime_compile_time_selection(self):
        code = """when os == "windows":
  const PLAT as string is "win"
else:
  const PLAT as string is "unix"

weave main into void:
  var msg as string is "FAIL"
  when os == "windows":
    set msg is PLAT
  else:
    set msg is PLAT
  calling print with msg
"""
        res = compile_run(code, tag="whenct")
        assert res.returncode == 0, res.stderr
        # The host's own branch proves compile-time selection ran.
        if is_windows():
            assert "win" in res.stdout
        else:
            assert "unix" in res.stdout


# ---------------------------------------------------------------------------
# Compile-time 'main' variable / 'when main:' scripting (test_when_main.py)
# ---------------------------------------------------------------------------

_SCRIPT_SNIPPET = """\
weave greet with who as string into void:
    var kept as string is "greeting-kept"
    when main:
        var m2 as string is "inner-main"

when main:
    weave main into int:
        var m1 as string is "top-main"
        return 0
"""

_SCRIPTMOD = """\
# scriptmod.pengu: importable module that is also runnable standalone.
import std.spark

weave greet with who as string into void:
    calling spark.println with "greeting " + who
    when main:
        calling spark.println with "greet inner-main"

when main:
    weave main into int:
        calling spark.println with "scriptmod entry"
        calling greet with "World"
        return 0
"""

_RUNNER = """\
# runner.pengu: imports scriptmod as a module (its 'when main' blocks drop).
import std.spark
import scriptmod

weave main into int:
    calling spark.println with "runner entry"
    calling scriptmod.greet with "driver"
    return 0
"""


class TestWhenMain:
    """The compile-time 'main' variable and 'when main:' scripting mode."""

    def _main_bundle(self, code: str, main_mode: bool) -> str:
        env = CompileTimeEnv(os_name="windows", arch="x64", compiler="gcc",
                             is_main=main_mode)
        return _bundle(code, env=env, entry_main_mode=main_mode,
                       entry_file=os.path.abspath("t.pengu"))

    # ------------------------------------------------------------ codegen

    def test_main_off_drops_when_main_blocks(self):
        c = self._main_bundle(_SCRIPT_SNIPPET, main_mode=False)
        # Blocks guarded by 'when main' are not emitted at all.
        assert "top-main" not in c
        assert "inner-main" not in c
        assert "pengu_main" not in c
        # The unguarded helper is still emitted.
        assert "greeting-kept" in c

    def test_main_on_emits_when_main_blocks(self):
        c = self._main_bundle(_SCRIPT_SNIPPET, main_mode=True)
        assert "top-main" in c
        assert "inner-main" in c
        assert "pengu_main" in c
        assert "greeting-kept" in c

    def test_main_var_in_body_dropped_when_off(self):
        code = """weave run with who as string into void:
  var kept as string is "x"
  when main:
    var b as string is "body-main"
"""
        c = self._main_bundle(code, main_mode=False)
        assert "body-main" not in c
        assert '"x"' in c

    def test_main_expression_form(self):
        code = """weave f into int:
    return when main then 1 else 2
"""
        c_on = self._main_bundle(code, main_mode=True)
        assert "1" in c_on
        assert "? 2 :" not in c_on
        c_off = self._main_bundle(code, main_mode=False)
        assert "2" in c_off
        assert "1 :" not in c_off

    # ------------------------------------------------------------ error E0040

    @pytest.mark.parametrize(
        "code",
        [
            "weave f into void:\n  var main as int is 1\n",
            "weave f into void:\n  let main is 1\n",
            "const main as int is 1\n",
        ],
        ids=["var", "let", "const"],
    )
    def test_main_reserved_identifier_rejected(self, code):
        env = CompileTimeEnv()
        _check_error(code, env=env, code="E0040")

    # ------------------------------------------------- compiled executables

    @requires_runtime
    def test_script_standalone_entry_outputs(self):
        res = _compile_run(_SCRIPTMOD, tag="scriptmod", entry="scriptmod.pengu",
                           entry_as_main=True)
        assert res.returncode == 0, res.stderr
        assert "scriptmod entry" in res.stdout
        assert "greeting World" in res.stdout
        assert "greet inner-main" in res.stdout

    @requires_runtime
    def test_import_drops_main_blocks(self):
        res = _compile_run(_RUNNER, tag="runner_on", entry="runner.pengu",
                           extra_files={"scriptmod.pengu": _SCRIPTMOD},
                           entry_as_main=True)
        assert res.returncode == 0, res.stderr
        assert "runner entry" in res.stdout
        assert "greeting driver" in res.stdout
        # scriptmod was imported: its 'when main' blocks must not appear.
        assert "scriptmod entry" not in res.stdout
        assert "greet inner-main" not in res.stdout

    @requires_runtime
    def test_default_build_keeps_main_off(self):
        # Default project build: even the entry module has 'main' false.
        res = _compile_run(_RUNNER, tag="runner_off", entry="runner.pengu",
                           extra_files={"scriptmod.pengu": _SCRIPTMOD},
                           entry_as_main=False)
        assert res.returncode == 0, res.stderr
        assert "runner entry" in res.stdout
        assert "greeting driver" in res.stdout
        assert "scriptmod entry" not in res.stdout
        assert "greet inner-main" not in res.stdout

    # ------------------------------------------------------------ CLI script

    @requires_runtime
    def test_cli_run_script(self):
        d = Path(tempfile.mkdtemp(prefix="pengu_cli_", dir=str(BUILD_DIR)))
        try:
            script = d / "scriptmod.pengu"
            script.write_text(_SCRIPTMOD, encoding="utf-8")
            res = subprocess.run(
                [sys.executable, str(REPO / "pengu_project.py"), "run",
                 str(script)],
                cwd=str(d), capture_output=True, text=True, timeout=300,
            )
            assert res.returncode == 0, res.stderr
            assert "scriptmod entry" in res.stdout
            assert "greeting World" in res.stdout
            assert "greet inner-main" in res.stdout
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# String-valued omens: 'omen X with string:' / explicit string values
# ---------------------------------------------------------------------------


class TestStringOmens:
    """String-valued omens compile to #define string constants, not enums."""

    def test_auto_string_values(self):
        code = """omen Color with string:
  Red
  Green

weave main into void:
  var c as string is Color.Red
"""
        c = gen_bundle(code)
        assert '#define Color_Red pengu_string_from_cstr("Red")' in c
        assert '#define Color_Green pengu_string_from_cstr("Green")' in c
        assert "typedef enum Color" not in c

    def test_explicit_string_values(self):
        code = """omen Level:
  Low is "low"
  High is "high"
"""
        c = gen_bundle(code)
        assert '#define Level_Low pengu_string_from_cstr("low")' in c

    def test_int_omens_still_enums(self):
        code = """omen Nivel:
  Uno is 1
  Dos is 2
"""
        c = gen_bundle(code)
        assert "typedef enum Nivel {" in c
        assert "Nivel_Uno = 1," in c

    def test_variant_reference_has_string_type(self):
        code = """omen Color with string:
  Red

weave main into void:
  var c as string is Color.Red
  if c == "Red":
    calling print with c
"""
        check_ok(code)

    def test_cannot_mix_int_and_string_values(self):
        code = """omen Bad:
  A is 1
  B is "bee"
"""
        _check_error(code, exc=SemanticError,
                     contains="Cannot mix integer and string values")

    def test_payload_not_allowed_in_string_mode(self):
        code = """omen Bad with string:
  A with x as int
"""
        _check_error(code, exc=SemanticError)

    def test_duplicate_string_values_rejected(self):
        code = """omen Dup:
  A is "same"
  B is "same"
"""
        _check_error(code, exc=SemanticError, contains="Duplicate value")

    @requires_runtime
    def test_runtime_string_omen_value(self):
        code = """omen Color with string:
  Red
  Green

weave main into void:
  var c as string is Color.Red
  var msg as string is "FAIL"
  if c == "Red":
    set msg is "OMEN_OK"
  calling print with msg
"""
        res = compile_run(code, tag="stromen")
        assert res.returncode == 0, res.stderr
        assert "OMEN_OK" in res.stdout


# ---------------------------------------------------------------------------
# Integrated unit tests: 'test ...:' blocks and --test codegen mode
# ---------------------------------------------------------------------------


class TestEmbeddedTests:
    """Integrated 'test' blocks and their --test codegen mode."""

    def test_string_and_ident_test_names(self):
        code = """weave add with a as int and b as int into int:
  return a + b

test "addition works":
  let r is calling add with 2 and 3
  if r == 5:
    calling print with "ok"

test test_add:
  let r is calling add with 2 and 3
  if r == 5:
    calling print with "ok"
"""
        _bundle(code, is_test=True)

    def test_absent_in_normal_mode(self):
        code = """weave add with a as int and b as int into int:
  return a + b

test "x":
  calling print with "x"
"""
        c = _bundle(code, is_test=False)
        assert "pengu_test_" not in c
        assert "pengu_run_tests" not in c

    def test_runner_emitted_in_test_mode(self):
        code = """weave add with a as int and b as int into int:
  return a + b

test "add works":
  let r is calling add with 2 and 3
  if r == 5:
    calling print with "ok"

test second:
  let r is calling add with 0 and 0
  if r == 0:
    calling print with "ok"
"""
        c = _bundle(code, is_test=True)
        assert "static void pengu_test_0(void)" in c
        assert "static void pengu_test_1(void)" in c
        assert "int pengu_run_tests(void)" in c
        assert '"add works"' in c
        assert '"second"' in c

    def test_test_body_checked_as_void_function(self):
        code = """test "returns value in void test":
  return 5
"""
        _check_error(code, exc=SemanticError)

    def test_test_not_allowed_in_declaration_file(self):
        code = """declare pengu_print with s as string into void

test "bad":
  calling print with "x"
"""
        err = _check_error(code, filename="main.d.pengu", exc=SemanticError)
        assert "declaration files" in f"{err}".lower()

    @requires_runtime
    def test_runtime_test_mode_runner(self):
        code = """import std.ward as w

weave add with a as int and b as int into int:
  return a + b

weave main into void:
  calling print with "APP_OK"

test "add works":
  let r is calling add with 2 and 3
  calling w.assert_eq_int with r and 5

test second:
  let r is calling add with 0 and 0
  calling w.assert_eq_int with r and 0
"""
        res = _compile_run(code, tag="tests", is_test=True)
        assert res.returncode == 0, res.stderr
        assert "add works" in res.stdout
        assert "All 2 test(s) passed." in res.stdout
        assert "APP_OK" not in res.stdout


# ---------------------------------------------------------------------------
# C calling back into a PenguScript weave (function pointers)
# ---------------------------------------------------------------------------


class TestWeaveFunctionPointers:
    """A Pengu weave is passed as a C function pointer to a runtime helper."""

    @requires_runtime
    def test_runtime_invokes_pengu_weave(self):
        src = """import std.spark

declare pengu_call_callback_int with cb as ref to void and value as int into void

weave on_value with v as int into void:
    var msg as string is "callback got " + (v to string)
    calling spark.println with msg

weave main into int:
    calling pengu_call_callback_int with on_value and 7
    return 0
"""
        res = compile_run(src, tag="cb")
        assert res.returncode == 0, res.stderr
        assert "callback got 7" in res.stdout


# ---------------------------------------------------------------------------
# Pengu weave as a minicoro body (libpengu_stb shim)
# ---------------------------------------------------------------------------


class TestPenguCoroutine:
    """A Pengu weave runs as a minicoro coroutine via the libpengu_stb shim."""

    @requires_runtime
    @requires_lib("pengu_stb")
    def test_weave_as_minicoro_body(self):
        src = """import std.spark

declare pengu_mco_start with body as ref to void and user_data as ref to void and stack_size as usize into ref to void
declare pengu_mco_resume with co as ref to void into void
declare pengu_mco_yield with co as ref to void into void
declare pengu_mco_destroy with co as ref to void into void

weave run_body with co as ref to void into void:
    calling spark.println with "body start"
    calling pengu_mco_yield with co
    calling spark.println with "body end"

weave main into int:
    var no_ud as ref to void is null
    var co as ref to void is calling pengu_mco_start with run_body and no_ud and 16384
    if co == null:
        calling spark.println with "coro start failed"
        return 1
    calling pengu_mco_resume with co
    calling pengu_mco_resume with co
    calling pengu_mco_destroy with co
    calling spark.println with "coroutine smoke passed"
    return 0
"""
        res = compile_run(src, tag="mco", extra_libs=["-lpengu_stb"])
        assert res.returncode == 0, res.stderr
        assert "body start" in res.stdout
        assert "body end" in res.stdout
        assert "coroutine smoke passed" in res.stdout


# ---------------------------------------------------------------------------
# Control flow: bool guards in for-comprehensions
# ---------------------------------------------------------------------------


class TestControlFlow:
    """'when <bool>' guards inside for-comprehensions (test_for_comp_bool)."""

    def test_non_bool_when_in_for_comp_fails(self):
        code = """weave main into void:
  var arr as array of int is array of int with size 4
  var res is for x in arr when 10 then x
"""
        err = _check_error(code, exc=TypeMismatchError)
        assert getattr(err, "code", None) == "E0005"
        assert "when condition must be bool" in f"{err}"

    def test_bool_when_in_for_comp_passes(self):
        code = """weave main into void:
  var arr as array of int is array of int with size 4
  var res is for x in arr when x > 0 then x
"""
        check_ok(code)


# ---------------------------------------------------------------------------
# Enchanting method calls
# ---------------------------------------------------------------------------


class TestEnchantingMethodCalls:
    """Method calls on enchanted types generate C method calls."""

    def test_enchanting_method_call_value(self):
        """Calling a method on a value instance passes a pointer &var."""
        code = """
rune Persona:
  nombre as string
  edad as int

enchanting Persona:
  weave present into string:
    return self->nombre

weave main into void:
  var p as Persona is with nombre is "Juan" and edad is 25
  calling print with calling p.present
"""
        bundle = gen_bundle(code, filename="main.pengu")
        # Should generate Persona_present(&p)
        assert "Persona_present(&p)" in bundle
        # Should NOT contain p->present
        assert "p->present" not in bundle
        assert "p.present(" not in bundle

    def test_enchanting_method_call_ref(self):
        """Calling a method on a ref instance passes the ref directly."""
        code = """
rune Counter:
  val as int

enchanting Counter:
  weave inc with amount as int into void:
    set self->val is self->val + amount

weave test with c as ref to Counter into void:
  calling c.inc with 5
"""
        bundle = gen_bundle(code, filename="test.pengu")
        assert "Counter_inc(c, 5)" in bundle
        assert "c->inc" not in bundle


# ---------------------------------------------------------------------------
# Memory semantics: defer / banish / errdefer / size of / escape analysis
# ---------------------------------------------------------------------------


class TestDeferBanish:
    """'defer', 'errdefer', 'banish' and 'size of' memory operators."""

    def test_valid_defer_and_banish(self):
        code = """rune Player:
  id as int

weave cleanup with p as ref to Player into void:
  return

weave main into void:
  var p as ref to Player is sigil of with id is 1
  defer calling cleanup with p
  banish p
"""
        check_ok(code)

    def test_banish_non_ref_fails(self):
        code = """weave main into void:
  let x is 10
  banish x
"""
        err = _check_error(code, exc=InvalidMemoryOpError)
        assert getattr(err, "code", None) == "E0008"

    def test_size_of_valid_and_undefined(self):
        code_valid = """rune Vec2:
  x as float
  y as float

weave main into void:
  let s is size of Vec2
"""
        check_ok(code_valid)

        code_invalid = """weave main into void:
  let s is size of NonExistentType
"""
        err = _check_error(code_invalid, exc=UndefinedIdentifierError)
        assert getattr(err, "code", None) == "E0004"


class TestEscapeAnalysis:
    """Escaping values move to the heap; non-escaping stay on the stack."""

    def test_non_escaping_var_checks(self):
        code = """rune Vec2:
  x as int
  y as int

weave foo into void:
  var v as Vec2 is with x is 1 and y is 2
  set v.x is 10
"""
        check_ok(code)

    def test_escaping_var_checks(self):
        code = """rune Vec2:
  x as int
  y as int

weave bar into ref to Vec2:
  var v as Vec2 is with x is 1 and y is 2
  return sigil of v
"""
        check_ok(code)


class TestMemory:
    """defer/errdefer/banish semantics over a declared C allocator."""

    def test_memory_management(self):
        code = """declare alloc with bytes as int into ref to int

weave test_memory into void:
  let p as ref to int is calling alloc with size of int
  defer banish p
  errdefer banish p
  set essence of p is 10
  banish p
"""
        check_ok(code)
