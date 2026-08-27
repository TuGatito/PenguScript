import unittest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_types import RuneType, INT_TYPE, FLOAT_TYPE, STRING_TYPE, TypeParam
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError


class TestGenerics(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def _check(self, code: str):
        tree = self.parser.parse(code)
        errors = self.checker.check(tree, source=code)
        self.assertEqual(len(errors), 0, f"Expected no semantic errors, got: {[str(e) for e in errors]}")
        return tree

    def _check_fails(self, code: str):
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError):
            self.checker.check(tree, source=code)

    def test_generic_rune_declaration_and_instantiation(self):
        code = """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair of int and float is with first is 42 and second is 3.14
  let f as int is p.first
  let s as float is p.second
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("struct Pair_int_float", c_code)
        self.assertIn("int32_t first;", c_code)
        self.assertIn("float second;", c_code)

    def test_generic_function_call_and_inference(self):
        code = """weave identity shard T with x as T into T:
  return x

weave main into void:
  let a as int is calling identity with 100
  let b as string is calling identity with "pengu"
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("identity_int", c_code)
        self.assertIn("identity_string", c_code)
        self.assertIn("identity_int(100)", c_code)
        self.assertIn("identity_string(pengu_string_from_cstr(\"pengu\"))", c_code)

    def test_generic_swap_multiple_type_params(self):
        code = """rune Pair shard T and U:
  first as T
  second as U

weave swap shard T and U with a as T, b as U into Pair of U and T:
  return with first is b and second is a

weave main into void:
  let p as Pair of float and int is calling swap with 10 and 2.5
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("swap_int_float", c_code)
        self.assertIn("Pair_float_int", c_code)

    def test_generic_enchanting_methods(self):
        code = """rune Box shard T:
  value as T

enchanting Box of T:
  weave get into T:
    return self->value

weave main into void:
  let b as Box of int is with value is 99
  let v as int is calling b.get
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("struct Box_int", c_code)
        self.assertIn("Box_int_get", c_code)

    def test_generic_nested_types(self):
        code = """rune Container shard T:
  item as T

rune Pair shard A and B:
  first as A
  second as B

weave main into void:
  let c as Container of int is with item is 7
  let p as Pair of (Container of int) and string is with first is c and second is "box"
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("struct Container_int", c_code)
        self.assertIn("struct Pair_Container_int_string", c_code)

    def test_generic_alias(self):
        code = """rune Pair shard T and U:
  first as T
  second as U

alias IntPair as Pair of int and int
alias GenericPair shard V as Pair of V and string

weave main into void:
  let ip as IntPair is with first is 1 and second is 2
  let gp as GenericPair of float is with first is 1.5 and second is "hello"
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("Pair_int_int", c_code)
        self.assertIn("Pair_float_string", c_code)

    def test_generic_omen(self):
        code = """omen Status shard T:
  Success with data as T
  Failure with code as int

weave main into void:
  let s as Status of string is with code is 404
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("Status_string", c_code)

    def test_error_arity_mismatch(self):
        code = """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair of int is with first is 1 and second is 2
"""
        self._check_fails(code)

    def test_error_uninstantiated_generic_type(self):
        code = """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair is with first is 1 and second is 2
"""
        self._check_fails(code)

    def test_error_duplicate_type_parameter(self):
        code = """rune Pair shard T and T:
  first as T
  second as T

weave main into void:
  return
"""
        self._check_fails(code)

    # -------------------------------------------------------------------------
    # Mejora 1: Deduplicación de instancias genéricas en el codegen
    # -------------------------------------------------------------------------
    def test_mejora1_deduplication_of_instances(self):
        mod1_code = """rune Pair shard T and U:
  first as T
  second as U

weave identity shard T with x as T into T:
  return x

weave use_mod1 into void:
  let p as Pair of int and float is with first is 1 and second is 2.0
  let y is calling identity with 10
"""
        mod2_code = """weave use_mod2 into void:
  let p as Pair of int and float is with first is 10 and second is 20.0
  let z is calling identity with 99
"""
        t1 = self.parser.parse(mod1_code)
        self.checker.check(t1, filename="mod1.pengu", source=mod1_code)
        t2 = self.parser.parse(mod2_code)
        self.checker.check(t2, filename="mod2.pengu", source=mod2_code, reset_symbols=False)

        codegen = PenguCodegen(self.checker.symbols, ["mod1.pengu", "mod2.pengu"], ".")
        codegen.collect_declarations([("mod1.pengu", t1), ("mod2.pengu", t2)])
        c_code = codegen.generate_bundle()

        # Ensure struct Pair_int_float and identity_int are declared exactly once
        self.assertEqual(c_code.count("struct Pair_int_float {"), 1)
        self.assertEqual(c_code.count("int32_t identity_int(int32_t x) {"), 1)

    # -------------------------------------------------------------------------
    # Mejora 2: Manejo de parámetros por defecto en funciones genéricas
    # -------------------------------------------------------------------------
    def test_mejora2_generic_default_valid_constant(self):
        code = """weave compute shard T with x as T, factor as int is 2 into int:
  return factor

weave main into void:
  let res is calling compute with "text"
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("compute_string", c_code)

    def test_mejora2_generic_default_invalid_dependent_on_t_rejected(self):
        code = """weave bad_fn shard T with x as T is 0 into T:
  return x

weave main into void:
  return
"""
        self._check_fails(code)

    # -------------------------------------------------------------------------
    # Mejora 3: Compatibilidad con include y defines de C
    # -------------------------------------------------------------------------
    def test_mejora3_c_defines_compatibility(self):
        code = """include "<stdio.h>"

rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair of int and BUFFER_SIZE is with first is 1 and second is 1024
"""
        tree = self._check(code)
        codegen = PenguCodegen(self.checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()
        self.assertIn("Pair_int_BUFFER_SIZE", c_code)

    # -------------------------------------------------------------------------
    # Mejora 4: Mensajes de error claros (E0021 y E0022)
    # -------------------------------------------------------------------------
    def test_mejora4_error_code_e0021_missing_type_args(self):
        code = """rune Pair shard T and U:
  first as T
  second as U

weave main into void:
  let p as Pair is with first is 1 and second is 2
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as cm:
            self.checker.check(tree, source=code)
        all_codes = [e.code for e in getattr(cm.exception, 'all_errors', [])] + [cm.exception.code]
        self.assertIn("E0021", all_codes, f"Expected E0021 in {all_codes}")

    def test_mejora4_error_code_e0022_type_param_outside_generic(self):
        code = """weave main into void:
  let x as T is 10
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SemanticError) as cm:
            self.checker.check(tree, source=code)
        all_codes = [e.code for e in getattr(cm.exception, 'all_errors', [])] + [cm.exception.code]
        self.assertIn("E0022", all_codes, f"Expected E0022 in {all_codes}")

    # -------------------------------------------------------------------------
    # Mejora 5: Consistencia en nombres manglados
    # -------------------------------------------------------------------------
    def test_mejora5_mangle_type_consistency(self):
        from pengu_parser.pengu_types import mangle_type, ListType, MapType, ResultType
        t1 = RuneType(name="Pair", type_args=[INT_TYPE, FLOAT_TYPE])
        self.assertEqual(mangle_type(t1), "Pair_int_float")

        t2 = ListType(element=INT_TYPE)
        self.assertEqual(mangle_type(t2), "list_int")

        t3 = MapType(key=STRING_TYPE, value=INT_TYPE)
        self.assertEqual(mangle_type(t3), "map_string_int")

        t4 = ResultType(ok_type=INT_TYPE, err_type=STRING_TYPE)
        self.assertEqual(mangle_type(t4), "result_int_string")


if __name__ == "__main__":
    unittest.main()
