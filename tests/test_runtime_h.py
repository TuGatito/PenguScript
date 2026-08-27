import unittest
import os


class TestRuntimeH(unittest.TestCase):
    def test_runtime_header_exists_and_contains_definitions(self):
        header_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pengu_runtime.h")
        self.assertTrue(os.path.isfile(header_path), f"Expected {header_path} to exist")

        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Core types
        self.assertIn("PenguList", content)
        self.assertIn("PenguMap", content)
        self.assertIn("PenguSlice", content)
        self.assertIn("PenguMaybe", content)
        self.assertIn("PenguResult", content)
        self.assertIn("PenguString", content)
        self.assertIn("pengu_banish", content)

        # String helpers
        self.assertIn("pengu_string_upper", content)
        self.assertIn("pengu_string_lower", content)
        self.assertIn("pengu_string_trim", content)
        self.assertIn("pengu_string_trim_start", content)
        self.assertIn("pengu_string_trim_end", content)
        self.assertIn("pengu_string_contains", content)
        self.assertIn("pengu_string_starts_with", content)
        self.assertIn("pengu_string_ends_with", content)
        self.assertIn("pengu_string_index_of", content)
        self.assertIn("pengu_string_last_index_of", content)
        self.assertIn("pengu_string_substring", content)
        self.assertIn("pengu_string_replace", content)
        self.assertIn("pengu_string_split", content)
        self.assertIn("pengu_string_repeat", content)
        self.assertIn("pengu_string_reverse", content)
        self.assertIn("pengu_string_char_at", content)
        self.assertIn("pengu_string_is_alpha", content)
        self.assertIn("pengu_string_is_digit", content)
        self.assertIn("pengu_string_is_alnum", content)

        # List helpers
        self.assertIn("pengu_list_push_int", content)
        self.assertIn("pengu_list_push_string", content)
        self.assertIn("pengu_list_pop_int", content)
        self.assertIn("pengu_list_contains_int", content)
        self.assertIn("pengu_list_index_of_int", content)

        # Map helpers
        self.assertIn("pengu_map_put_string_int", content)
        self.assertIn("pengu_map_get_string_int", content)
        self.assertIn("pengu_map_contains_string_int", content)
        self.assertIn("pengu_map_remove_string_int", content)


if __name__ == "__main__":
    unittest.main()
