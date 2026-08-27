#!/usr/bin/env python3
"""Test enchanting method calls in C code generator."""

import unittest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen


class TestEnchantingCall(unittest.TestCase):
    """Verifies that method calls on enchanted types generate correct C function calls."""

    def test_enchanting_method_call_value(self):
        """Calling method on value instance passes pointer &var."""
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
        parser = PenguParser()
        checker = PenguChecker()
        tree = parser.parse(code)
        checker.check(tree, source=code)

        codegen = PenguCodegen(checker.symbols, ["main.pengu"], ".")
        codegen.collect_declarations([("main.pengu", tree)])
        bundle = codegen.generate_bundle()

        # Should generate Persona_present(&p)
        self.assertIn("Persona_present(&p)", bundle)
        # Should NOT contain p->present
        self.assertNotIn("p->present", bundle)
        self.assertNotIn("p.present(", bundle)

    def test_enchanting_method_call_ref(self):
        """Calling method on ref instance passes ref directly."""
        code = """
rune Counter:
  val as int

enchanting Counter:
  weave inc with amount as int into void:
    set self->val is self->val + amount

weave test with c as ref to Counter into void:
  calling c.inc with 5
"""
        parser = PenguParser()
        checker = PenguChecker()
        tree = parser.parse(code)
        checker.check(tree, source=code)

        codegen = PenguCodegen(checker.symbols, ["test.pengu"], ".")
        codegen.collect_declarations([("test.pengu", tree)])
        bundle = codegen.generate_bundle()

        self.assertIn("Counter_inc(c, 5)", bundle)
        self.assertNotIn("c->inc", bundle)


if __name__ == "__main__":
    unittest.main()
