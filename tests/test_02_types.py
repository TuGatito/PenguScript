import unittest
from pengu_parser import PenguParser, PenguChecker


class TestTypes(unittest.TestCase):
    def setUp(self):
        self.parser = PenguParser()
        self.checker = PenguChecker()

    def test_base_and_ref_types(self):
        code = """alias MyInt as int
alias MyI32 as i32
alias MyI64 as i64
alias MyFloat as float
alias MyF32 as f32
alias MyF64 as f64
alias MyBool as bool
alias MyString as string
alias VoidPtr as ref to void
alias IntPtr as ref to int
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_collection_types(self):
        code = """alias IntArray as array of int
alias IntSlice as slice of int
alias VecList as list of int
alias LookupMap as map of int to string
alias MaybeUser as maybe int
alias Texture as opaque
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)

    def test_function_pointer_types(self):
        code = """alias AddFunc as ref to weave with int, int into int
alias WebUIHandler as ref to weave with e as ref to void into void
alias VoidCallback as ref to weave into void
"""
        tree = self.parser.parse(code)
        self.assertIsNotNone(tree)
        self.checker.check(tree)


if __name__ == "__main__":
    unittest.main()
