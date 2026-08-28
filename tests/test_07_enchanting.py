import unittest
from pengu_parser import PenguParser, PenguChecker
from pengu_parser.pengu_checker import SelfDotAccessError


class TestEnchanting(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_enchanting_with_arrow(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    Vec2 is with x is self->x + other.x and y is self->y + other.y

  weave length into float:
    (self->x * self->x + self->y * self->y) to float

  weave move with dx as float, dy as float into void:
    set self->x is self->x + dx
    set self->y is self->y + dy

weave main into void:
  let a as Vec2 is with x is 10 and y is 20
  let b as Vec2 is with x is 5 and y is 5
  let c is calling a.add with b
  var d as Vec2 is a
  calling d.move with 10, 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_self_dot_access_fails(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave move with dx as float into void:
    set self.x is self.x + dx
"""
        tree = self.parser.parse(code)
        with self.assertRaises(SelfDotAccessError):
            self.checker.check(tree)

    def test_enchanting_codegen(self):
        code = """rune Vec2:
  x as float
  y as float

enchanting Vec2:
  weave add with other as Vec2 into Vec2:
    return with x is self->x + other.x and y is self->y + other.y

  weave length into float:
    return (self->x * self->x + self->y * self->y) to float

  weave move with dx as float and dy as float into void:
    set self->x is self->x + dx
    set self->y is self->y + dy

weave main into void:
  var a as Vec2 is with x is 10.0 and y is 20.0
  var b as Vec2 is with x is 5.0 and y is 5.0
  let c as Vec2 is calling a.add with b
  calling a.move with 10.0 and 0.0
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test_enchanting.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test_enchanting.pengu"], ".")
        codegen.collect_declarations([("test_enchanting.pengu", tree)])
        prototypes_c = codegen.generate_function_prototypes()
        fn_c = codegen.generate_function_definitions()

        self.assertIn("Vec2 Vec2_add(Vec2* self, Vec2 other);", prototypes_c)
        self.assertIn("float Vec2_length(Vec2* self);", prototypes_c)
        self.assertIn("void Vec2_move(Vec2* self, float dx, float dy);", prototypes_c)

        self.assertIn("Vec2 Vec2_add(Vec2* restrict self, Vec2 other) {", fn_c)
        self.assertIn("return (Vec2){.x = (self->x + other.x), .y = (self->y + other.y)};", fn_c)
        self.assertIn("void Vec2_move(Vec2* restrict self, float dx, float dy) {", fn_c)
        self.assertIn("const Vec2 c = Vec2_add(&a, b);", fn_c)
        self.assertIn("Vec2_move(&a, 10.0f, 0.0f);", fn_c)


if __name__ == "__main__":
    unittest.main()

