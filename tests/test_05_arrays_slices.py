import unittest
from pengu_parser import PenguParser, PenguChecker


class TestArraysSlices(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_arrays_and_slices(self):
        code = """const MAX_ENTITIES as int is 100

rune Vec2:
  x as float
  y as float

weave test_collections into void:
  let arr is array of int with size 10
  let first is arr at 0
  set arr at 0 is 99

  let part as slice of int is arr at 1 to 3
  let n is part length

  let evens is for x in arr when x % 2 == 0 then x
  let doubled is for x in arr then x * 2

  var vertices as list of Vec2 is list of Vec2 with capacity MAX_ENTITIES
  var lookup as map of int to Vec2 is map of int to Vec2

  let name is "player1"
  let x is 10
  let msg is "player {name} at {x}"
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


    def test_arrays_and_slices_codegen(self):
        code = """const MAX_ENTITIES as int is 100

rune Vec2:
  x as float
  y as float

weave test_collections into void:
  let arr is array of int with size 10
  let first is arr at 0
  set arr at 0 is 99

  let part as slice of int is arr at 1 to 3
  let n is part length

  let evens is for x in arr when x % 2 == 0 then x
  let doubled is for x in arr then x * 2

  var vertices as list of Vec2 is list of Vec2 with capacity MAX_ENTITIES
  var lookup as map of int to Vec2 is map of int to Vec2

  let name is "player1"
  let x is 10
  let msg is "player {name} at {x}"
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test.pengu"], ".")
        codegen.collect_declarations([("test.pengu", tree)])
        c_code = codegen.generate_function_definitions()
        self.assertIn("int32_t arr[10] = {0};", c_code)
        self.assertIn("arr[0] = 99;", c_code)
        self.assertIn("PenguSlice part = pengu_slice_new", c_code)
        self.assertIn("const int32_t n = part.len;", c_code)
        self.assertIn("PenguList evens =", c_code)
        self.assertIn("PenguList doubled =", c_code)
        self.assertIn("PenguList vertices = pengu_list_new(sizeof(Vec2), 100);", c_code)
        self.assertIn("PenguMap lookup = pengu_map_new(sizeof(int32_t), sizeof(Vec2));", c_code)
        self.assertIn("player %s at %d", c_code)


if __name__ == "__main__":
    unittest.main()

