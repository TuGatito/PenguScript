import unittest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import (
    PenguError, ErrorReporter, SemanticError, ConstInsideWeaveError, VarLetTopLevelError,
    SelfDotAccessError, UndefinedIdentifierError, TypeMismatchError, MutabilityError,
    InvalidControlFlowError, InvalidMemoryOpError, InvalidWithTargetError
)


class TestRustErrors(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()

    def _check_and_catch(self, code: str, filename: str = "test.pengu") -> PenguError:
        tree = self.parser.parse(code)
        checker = PenguChecker(source=code, filename=filename)
        with self.assertRaises(PenguError) as ctx:
            checker.check(tree)
        return ctx.exception

    def test_e0001_const_inside_weave(self):
        code = """weave main into void:
  const X is 10"""
        err = self._check_and_catch(code, "main.pengu")
        self.assertEqual(err.code, "E0001")
        rendered = err.render(code)
        self.assertIn("error[E0001]", rendered)
        self.assertIn("--> main.pengu:2:", rendered)
        self.assertIn("^", rendered)
        self.assertIn("= help:", rendered)
        self.assertIn("= note:", rendered)

    def test_e0002_var_let_top_level(self):
        code = "let v is 10"
        err = self._check_and_catch(code, "test.pengu")
        self.assertEqual(err.code, "E0002")
        rendered = err.render(code)
        self.assertIn("error[E0002]", rendered)
        self.assertIn("--> test.pengu:1:", rendered)
        self.assertIn("^", rendered)
        self.assertIn("= help:", rendered)
        self.assertIn("= note:", rendered)

    def test_e0003_self_dot_access(self):
        code = """rune Player:
  x as int

enchanting Player:
  weave move into void:
    set self.x is 20"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0003")
        rendered = err.render(code)
        self.assertIn("error[E0003]", rendered)
        self.assertIn("self->", rendered)
        self.assertIn("= help:", rendered)

    def test_e0004_undefined_identifier(self):
        code = """weave main into void:
  let x is unknown_var + 1"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0004")
        rendered = err.render(code)
        self.assertIn("error[E0004]", rendered)
        self.assertIn("unknown_var", rendered)
        self.assertIn("= help:", rendered)

    def test_e0005_type_mismatch(self):
        code = """weave main into void:
  let x as int is "hello" """
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0005")
        rendered = err.render(code)
        self.assertIn("error[E0005]", rendered)
        self.assertIn("-->", rendered)
        self.assertIn("= help:", rendered)

    def test_e0006_mutability_error(self):
        code = """weave main into void:
  let x is 10
  set x is 20"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0006")
        rendered = err.render(code)
        self.assertIn("error[E0006]", rendered)
        self.assertIn("immutable", rendered)
        self.assertIn("= help:", rendered)

    def test_e0007_break_outside_loop(self):
        code = """weave main into void:
  break"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0007")
        rendered = err.render(code)
        self.assertIn("error[E0007]", rendered)
        self.assertIn("= help:", rendered)

    def test_e0008_invalid_memory_op(self):
        code = """weave main into void:
  let p is sigil of 123"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0008")
        rendered = err.render(code)
        self.assertIn("error[E0008]", rendered)
        self.assertIn("= help:", rendered)

    def test_e0009_invalid_with_target(self):
        code = """weave main into void:
  set .x is 10"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0009")
        rendered = err.render(code)
        self.assertIn("error[E0009]", rendered)
        self.assertIn("with", rendered)

    def test_e0010_cannot_infer_rune(self):
        code = """weave main into void:
  let v is with x is 1 and y is 2"""
        err = self._check_and_catch(code, "test.pengu")
        self.assertEqual(err.code, "E0010")
        rendered = err.render(code)
        self.assertIn("error[E0010]", rendered)
        self.assertIn("no rune matches", rendered)
        self.assertIn("--> test.pengu:2:", rendered)
        self.assertIn("^", rendered)
        self.assertIn("= help:", rendered)
        self.assertIn("= note:", rendered)

    def test_e0011_ambiguous_struct_init(self):
        code = """rune Vec2A:
  x as int
  y as int

rune Vec2B:
  x as int
  y as int

weave main into void:
  let v is with x is 1 and y is 2"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0011")
        rendered = err.render(code)
        self.assertIn("error[E0011]", rendered)
        self.assertIn("Ambiguous", rendered)
        self.assertIn("= help:", rendered)

    def test_e0012_opaque_instantiation(self):
        code = """alias Texture as opaque

weave main into void:
  let t as Texture is with id is 1"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0012")
        rendered = err.render(code)
        self.assertIn("error[E0012]", rendered)
        self.assertIn("Cannot instantiate opaque type", rendered)
        self.assertIn("= help:", rendered)

    def test_e0013_field_not_exist(self):
        code = """rune Point:
  x as int

weave main into void:
  let p as Point is with x is 10
  let z is p.z"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0013")
        rendered = err.render(code)
        self.assertIn("error[E0013]", rendered)
        self.assertIn("has no field 'z'", rendered)

    def test_e0014_maybe_none_without_type(self):
        code = """weave main into void:
  let x is maybe none"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0014")
        rendered = err.render(code)
        self.assertIn("error[E0014]", rendered)
        self.assertIn("= help:", rendered)

    def test_e0015_error_outside_or_block(self):
        code = """weave main into void:
  let e is error"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0015")
        rendered = err.render(code)
        self.assertIn("error[E0015]", rendered)
        self.assertIn("or:", rendered)

    def test_e0016_c_define_without_include(self):
        code = """weave main into void:
  let key is KEY_W"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0016")
        rendered = err.render(code)
        self.assertIn("error[E0016]", rendered)
        self.assertIn("include", rendered)

    def test_e0017_destructuring_mismatch(self):
        code = """rune Vec2:
  x as int
  y as int

weave main into void:
  let v as Vec2 is with x is 1 and y is 2
  let a, b, c is v"""
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0017")
        rendered = err.render(code)
        self.assertIn("error[E0017]", rendered)
        self.assertIn("Destructuring mismatch", rendered)

    def test_e0018_list_push_type_mismatch(self):
        code = """weave main into void:
  var items as list of int is list of int with capacity 10
  calling items.push with "invalid string" """
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0018")
        rendered = err.render(code)
        self.assertIn("error[E0018]", rendered)
        self.assertIn("push expects int", rendered)

    def test_e0019_string_interp_undefined(self):
        code = """weave main into void:
  let msg is "hello {missing_var}" """
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0019")
        rendered = err.render(code)
        self.assertIn("error[E0019]", rendered)
        self.assertIn("missing_var", rendered)

    def test_e0020_implicit_return_type_mismatch(self):
        code = """weave compute into int:
  let x is 10
  "not an int" """
        err = self._check_and_catch(code)
        self.assertEqual(err.code, "E0020")
        rendered = err.render(code)
        self.assertIn("error[E0020]", rendered)
        self.assertIn("Implicit return type", rendered)


if __name__ == "__main__":
    unittest.main()
