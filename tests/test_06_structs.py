import unittest
from pengu_parser import PenguParser, PenguChecker


class TestStructs(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_struct_definitions_and_access(self):
        code = """rune Vec2:
  x as float
  y as float

echo Value:
  i as int
  f as float

alias MyInt as int
alias Texture as opaque

omen Result:
  Ok with value as int
  Err with msg as string

weave struct_test into void:
  var v as Vec2 is with x is 10 and y is 20
  let vx is v.x
  set v.x is 100.0

  var vp as ref to Vec2 is sigil of v
  set vp->x is 100.0
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_structs_echos_omens_aliases_codegen(self):
        code = """rune Vec2:
  x as float
  y as float

echo Value:
  as_int as int
  as_float as float

alias Score as int
alias Texture as opaque

omen NetworkState:
  Disconnected
  Connecting with retry_count as int
  Connected with session_id as string
  Failed with error_code as int and reason as string

weave struct_test into void:
  var v as Vec2 is with x is 10.0 and y is 20.0
  let vx is v.x
  set v.x is 100.0

  var val as Value is with as_int is 42
  var sc as Score is 100
  var state as NetworkState is with Connected is with session_id is "sess_123"

  var vp as ref to Vec2 is sigil of v
  set vp->x is 200.0
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test_structs.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test_structs.pengu"], ".")
        codegen.collect_declarations([("test_structs.pengu", tree)])
        types_c = codegen.generate_type_definitions()
        fn_c = codegen.generate_function_definitions()

        self.assertIn("struct Vec2 {", types_c)
        self.assertIn("union Value {", types_c)
        self.assertIn("typedef int32_t Score;", types_c)
        self.assertIn("typedef struct Texture Texture;", types_c)
        self.assertIn("typedef enum NetworkState_Tag {", types_c)
        self.assertIn("struct NetworkState {", types_c)

        self.assertIn("Vec2 v = (Vec2){.x = 10.0f, .y = 20.0f};", fn_c)
        self.assertIn("Value val = (Value){.as_int = 42};", fn_c)
        self.assertIn("Score sc = 100;", fn_c)
        self.assertIn("NetworkState state = (NetworkState){ .tag = NetworkState_Connected, .data.Connected = {.session_id = pengu_string_from_cstr(\"sess_123\")} };", fn_c)
        self.assertIn("vp->x = 200.0f;", fn_c)

    def test_simple_enum_omen_codegen(self):
        code = """omen Level:
  ONE
  TWO
  THREE

weave enum_test into string:
  var l1 as Level is Level_ONE
  var l2 as Level is Level.TWO
  var l3 as Level is THREE
  let res is judge l2:
    when Level_ONE -> "1"
    when Level.TWO -> "2"
    when THREE -> "3"
    else -> "other"
  return res
"""
        from pengu_parser.pengu_codegen import PenguCodegen
        tree = self.parser.parse(code)
        self.checker.check(tree, source=code, filename="test_enum.pengu")
        codegen = PenguCodegen(self.checker.symbols, ["test_enum.pengu"], ".")
        codegen.collect_declarations([("test_enum.pengu", tree)])
        fwd_c = codegen.generate_forward_declarations()
        types_c = codegen.generate_type_definitions()
        fn_c = codegen.generate_function_definitions()

        self.assertIn("typedef enum Level Level;", fwd_c)
        self.assertNotIn("struct Level;", fwd_c)

        self.assertIn("typedef enum Level {", types_c)
        self.assertIn("  Level_ONE,", types_c)
        self.assertIn("  Level_TWO,", types_c)
        self.assertIn("  Level_THREE,", types_c)
        self.assertIn("} Level;", types_c)
        self.assertNotIn("struct Level {", types_c)

        self.assertIn("Level l1 = Level_ONE;", fn_c)
        self.assertIn("Level l2 = Level_TWO;", fn_c)
        self.assertIn("Level l3 = Level_THREE;", fn_c)
        self.assertIn("switch (_val) { case Level_ONE: _res = (pengu_string_from_cstr(\"1\")); break; case Level_TWO: _res = (pengu_string_from_cstr(\"2\")); break; case Level_THREE: _res = (pengu_string_from_cstr(\"3\")); break; default: _res = (pengu_string_from_cstr(\"other\")); break; }", fn_c)


if __name__ == "__main__":
    unittest.main()


