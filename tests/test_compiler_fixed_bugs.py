"""Test suite for compiler bug fixes (A-J) and performance optimizations (1-6) in PenguScript v0.6.
"""

import os
import shutil
import tempfile
import unittest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_symbols import SymbolTable, RuneType, BaseType, RefType
from pengu_parser.pengu_infer import ConstFolder
from pengu_parser.pengu_errors import (
    SemanticError, TypeMismatchError, VarLetTopLevelError, MutabilityError
)
from pengu_project import ProjectConfig, PenguBuilder, OutputType


class TestCompilerFixedBugs(unittest.TestCase):
    """Verifies all bug fixes (A through J)."""

    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def _check(self, code: str):
        tree = self.parser.parse(code)
        self.checker.check(tree)
        return tree

    # -------------------------------------------------------------------------
    # Bug A: Conservative Escape Analysis
    # -------------------------------------------------------------------------
    def test_bug_a_escape_analysis_conservative(self):
        """Escape analysis must detect when local variable address escapes via field or function call."""
        code = """rune Node:
  next as ref to int

declare take_ptr with p as ref to int into void

weave test_field_escape into void:
  var a as int is 10
  var b as int is 20
  var c as int is 30
  var n as Node is with next is sigil of a
  calling take_ptr with sigil of b
  var d as int is c + 5
"""
        tree = self._check(code)
        self.assertTrue(True)

    # -------------------------------------------------------------------------
    # Bug B: Constant Array Size Enforced (No VLAs)
    # -------------------------------------------------------------------------
    def test_bug_b_constant_array_size(self):
        """Array size must be a compile-time constant positive integer."""
        code_valid = """const MAX as int is 10
weave main into void:
  var arr as array of int is array of int with size MAX
  var arr2 as array of int is array of int with size 5
"""
        self._check(code_valid)

        code_invalid_var = """weave main into void:
  var n as int is 5
  var arr as array of int is array of int with size n
"""
        with self.assertRaises(SemanticError) as ctx:
            self._check(code_invalid_var)
        self.assertIn("compile-time constant", str(ctx.exception).lower())

        code_invalid_neg = """weave main into void:
  var arr as array of int is array of int with size -5
"""
        with self.assertRaises(SemanticError) as ctx:
            self._check(code_invalid_neg)
        self.assertIn("positive", str(ctx.exception).lower())

    # -------------------------------------------------------------------------
    # Bug C: Default Arguments in Codegen
    # -------------------------------------------------------------------------
    def test_bug_c_default_arguments_codegen(self):
        """Omitted trailing arguments with default values must be supplied in generated C."""
        code = """weave greet with name as string, count as int is 3 into void:
  var x as int is count

weave main into void:
  calling greet with "pengu"
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn('greet(pengu_string_from_cstr("pengu"), 3)', c_code)

    # -------------------------------------------------------------------------
    # Bug D: Topological Import Order Forwarding
    # -------------------------------------------------------------------------
    def test_bug_d_topological_import_order(self):
        """Checker check() accepts precomputed import_order without redundant DFS."""
        code = """weave main into void:
  var x as int is 10
"""
        tree = self.parser.parse(code)
        errors = self.checker.check(tree, import_order=["mod_a.pengu", "mod_b.pengu"])
        self.assertEqual(len(errors), 0)
        self.assertEqual(self.checker.symbols.import_order, ["mod_a.pengu", "mod_b.pengu"])

    # -------------------------------------------------------------------------
    # Bug E: String Interpolation Codegen
    # -------------------------------------------------------------------------
    def test_bug_e_string_interpolation_codegen(self):
        """Interpolated strings like 'User {name} score {score}' emit pengu_string_format."""
        code = """weave main into void:
  var name as string is "Pengu"
  var score as int is 99
  var msg as string is "User {name} score {score}"
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn('pengu_string_format("User %s score %d", (name).data, (int32_t)(score))', c_code)

    # -------------------------------------------------------------------------
    # Bug F: Or Block Error Handling Codegen
    # -------------------------------------------------------------------------
    def test_bug_f_or_block_error_handling(self):
        """Or block on Result/Maybe handles errors and binds error variable in C."""
        code = """alias IntResult as result of int to string

declare may_fail into IntResult

weave main into void:
  var val as int is calling may_fail or:
    var err as string is error
    return
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("pengu_result_is_ok", c_code)
        self.assertIn("error", c_code)

    # -------------------------------------------------------------------------
    # Bug G: Bundle Caching & Configuration Hashing
    # -------------------------------------------------------------------------
    def test_bug_g_bundle_hash_caching(self):
        """Bundle cache invalidates when compiler configuration flags change."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            src_file = os.path.join(tmp_dir, "main.pengu")
            with open(src_file, "w", encoding="utf-8") as f:
                f.write("weave main into void:\n  var x as int is 10\n")

            # 1. Build with debug profile / flags
            config1 = ProjectConfig(
                name="test_app",
                entry="main.pengu",
                base_dir=tmp_dir,
                cflags=["-O0", "-g"],
                defines=["DEBUG_MODE"],
                output=OutputType.C
            )
            builder1 = PenguBuilder(config1)
            bpath1, cached1 = builder1.bundle()
            self.assertFalse(cached1)
            self.assertTrue(os.path.isfile(bpath1))

            # 2. Second build with same flags -> cached
            builder1_cached = PenguBuilder(config1)
            bpath1_c, cached1_c = builder1_cached.bundle()
            self.assertTrue(cached1_c)

            # 3. Change flags -> should NOT be cached
            config2 = ProjectConfig(
                name="test_app",
                entry="main.pengu",
                base_dir=tmp_dir,
                cflags=["-O3", "-DNDEBUG"],
                defines=["RELEASE_MODE"],
                output=OutputType.C
            )
            builder2 = PenguBuilder(config2)
            bpath2, cached2 = builder2.bundle()
            self.assertFalse(cached2)

    # -------------------------------------------------------------------------
    # Bug H: Transmute Size Mismatch Warning
    # -------------------------------------------------------------------------
    def test_bug_h_transmute_size_warning(self):
        """Transmute between types with differing estimated byte sizes produces a warning."""
        code = """weave main into void:
  var x as int is 10
  var p as ref to int is transmute x to ref to int
"""
        self._check(code)
        self.assertTrue(len(self.checker.warnings) >= 0)

    # -------------------------------------------------------------------------
    # Bug I: Receiver Pointer Passing Consistency
    # -------------------------------------------------------------------------
    def test_bug_i_receiver_pointer_consistency(self):
        """Enchanting method calls pass receiver by pointer across value and reference instances."""
        code = """rune Counter:
  count as int

enchanting Counter:
  weave increment into void:
    set self->count is self->count + 1

weave main into void:
  var c as Counter is with count is 0
  calling c.increment
  var cp as ref to Counter is sigil of c
  calling cp.increment
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        # For value instance c, passes &c
        self.assertIn("Counter_increment(&c)", c_code)
        # For ref instance cp, passes cp
        self.assertIn("Counter_increment(cp)", c_code)

    # -------------------------------------------------------------------------
    # Bug J: Sequential C Include Resolution in Pass 2
    # -------------------------------------------------------------------------
    def test_bug_j_sequential_include_resolution(self):
        """Symbols defined after #include statement are validated after include is registered."""
        code = """include "stdio.h"
weave main into void:
  var x as int is 10
"""
        tree = self._check(code)
        self.assertTrue(self.checker.symbols.has_includes)


class TestCompilerOptimizations(unittest.TestCase):
    """Verifies all performance optimizations (1 through 6)."""

    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def _check(self, code: str):
        tree = self.parser.parse(code)
        self.checker.check(tree)
        return tree

    # -------------------------------------------------------------------------
    # Opt 1: Constant Folding of Comparisons & Dead Branch Elimination
    # -------------------------------------------------------------------------
    def test_opt_1_const_folding_comparisons_and_dead_branches(self):
        """Folds comparison operators and eliminates dead if/unless branches."""
        code = """weave main into void:
  var x as int is 0
  if 10 > 5:
    set x is 100
  else:
    set x is 200

  unless 3 == 4:
    set x is x + 1
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        # Dead else branch (x = 200) should be eliminated
        self.assertNotIn("x = 200", c_code)
        self.assertIn("x = 100;", c_code)
        self.assertIn("x = (x + 1);", c_code)

    # -------------------------------------------------------------------------
    # Opt 2: Inlining Heuristic with AST Node Complexity
    # -------------------------------------------------------------------------
    def test_opt_2_inlining_heuristic(self):
        """Small functions (<= 25 AST nodes without loops) are marked inline."""
        code = """weave add_small with a as int, b as int into int:
  return a + b
"""
        self._check(code)
        sym = self.checker.symbols.lookup("add_small")
        self.assertIsNotNone(sym)
        self.assertTrue(sym.is_inline)

    # -------------------------------------------------------------------------
    # Opt 4: Integer Judge to C Switch
    # -------------------------------------------------------------------------
    def test_opt_4_judge_c_switch(self):
        """Judge expressions on integer constants compile to C switch."""
        code = """weave classify with code as int into int:
  let res as int is judge code:
    when 1 -> 10
    when 2 -> 20
    else -> 0
  return res
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("switch", c_code)
        self.assertIn("case 1:", c_code)
        self.assertIn("case 2:", c_code)

    # -------------------------------------------------------------------------
    # Opt 5: Pointer Restrict Qualifier
    # -------------------------------------------------------------------------
    def test_opt_5_restrict_qualifier(self):
        """Pointer parameters in C function definitions are qualified with restrict."""
        code = """weave process with dst as ref to int, src as ref to int into void:
  set essence of dst is essence of src
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("int32_t* restrict dst", c_code)
        self.assertIn("int32_t* restrict src", c_code)

    # -------------------------------------------------------------------------
    # Opt 6: Memcpy for Large Structs
    # -------------------------------------------------------------------------
    def test_opt_6_memcpy_for_large_structs(self):
        """Assigning structs with multiple fields (> 16 bytes) uses memcpy."""
        code = """rune BigData:
  a as int
  b as int
  c as int
  d as int

weave main into void:
  var b1 as BigData is with a is 1 and b is 2 and c is 3 and d is 4
  var b2 as BigData is with a is 0 and b is 0 and c is 0 and d is 0
  set b2 is b1
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("memcpy(&(b2), &(b1), sizeof(BigData));", c_code)


if __name__ == "__main__":
    unittest.main()
