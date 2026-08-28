import unittest
from pengu_parser import PenguParser, PenguChecker


class TestControl(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_control_flow(self):
        code = """rune Player:
  x as float
  y as float

enchanting Player:
  weave move with dist as int into void:
    set self->x is self->x + dist

rune File:
  name as string

declare open with path as string into maybe File
declare print with val as string into void

weave test_flow with opt_x as maybe int, key as string, arr as list of int into int:
  var x as int is 0
  let color is if x > 10 then "red" else "blue"

  if file as File is calling open with "data.txt" is present:
    calling print with file.name

  if opt_x is present:
    return 1

  unless opt_x is present:
    return 1

  let state as string is judge key:
    when "w" -> "up"
    when "s" -> "down"
    else -> "idle"

  while x < 10:
    set x is x + 1
    if x == 5: continue
    if x == 9: break

  for i from 0 to 10:
    calling print with "loop"

  for item in arr:
    calling print with "item"

  var player as Player is with x is 10 and y is 20
  with player:
    set.x is 100
    set.y is 200
    calling.move with 5

  return 0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_loops_modifying_arrays_and_collections_codegen(self):
        code = """weave loops_demo into void:
  var x as int is 0
  while x < 10:
    set x is x + 1
    if x == 5:
      continue
    if x == 9:
      break

  var arr as array of int with size 5 is [1, 2, 3, 4, 5]
  for i from 0 to 5:
    set arr at i is (arr at i) * 2

  let part as slice of int is arr at 1 to 4
  for i from 0 to part.len:
    set part at i is (part at i) + 10

  for num in arr:
    let doubled is num * 2

  var lst as list of int is list of int with capacity 10
  for i from 0 to 5:
    calling lst.push with i * 10
  for i from 0 to lst.len:
    set lst at i is (lst at i) + 100
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test_loop.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test_loop.pengu"], ".")
        codegen.collect_declarations([("test_loop.pengu", tree)])
        c_code = codegen.generate_function_definitions()

        self.assertIn("while ((x < 10)) {", c_code)
        self.assertIn("continue;", c_code)
        self.assertIn("break;", c_code)
        self.assertIn("for (int32_t i = 0; i < 5; i++) {", c_code)
        self.assertIn("arr[i] = (arr[i] * 2);", c_code)
        self.assertIn("for (int32_t i = 0; i < part.len; i++) {", c_code)
        self.assertIn("(((int32_t*)(part).data)[i]) = ((((int32_t*)(part).data)[i]) + 10);", c_code)
        self.assertIn("for (int32_t _idx_1 = 0; _idx_1 < 5; _idx_1++) {", c_code)
        self.assertIn("int32_t num = (arr)[_idx_1];", c_code)
        self.assertIn("for (int32_t i = 0; i < lst.len; i++) {", c_code)
        self.assertIn("(*(int32_t*)pengu_list_at(&(lst), i)) = ((*(int32_t*)pengu_list_at(&(lst), i)) + 100);", c_code)

    def test_judge_and_with_codegen(self):
        code = """rune Player:
  x as int
  y as int
  health as int

enchanting Player:
  weave heal with amount as int into void:
    set self->health is self->health + amount

weave reset_player with p as ref to Player into void:
  with p:
    set.x is 100
    set.y is 200
    calling.heal with 50

weave pattern_demo with key as int into string:
  let state as string is judge key:
    when 1 -> "Active"
    when 2 -> "Pending"
    when 3 -> "Finished"
    else -> "Unknown"
  return state
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test_judge_with.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test_judge_with.pengu"], ".")
        codegen.collect_declarations([("test_judge_with.pengu", tree)])
        c_code = codegen.generate_function_definitions()

        self.assertIn("p->x = 100;", c_code)
        self.assertIn("p->y = 200;", c_code)
        self.assertIn("Player_heal(p, 50);", c_code)
        self.assertIn("switch (_val) { case 1: _res = (pengu_string_from_cstr(\"Active\")); break; case 2: _res = (pengu_string_from_cstr(\"Pending\")); break; case 3: _res = (pengu_string_from_cstr(\"Finished\")); break; default: _res = (pengu_string_from_cstr(\"Unknown\")); break; }", c_code)


if __name__ == "__main__":
    unittest.main()


