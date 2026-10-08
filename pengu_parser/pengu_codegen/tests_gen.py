"""The integrated unit-test section (`--test` mode).

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    List,
    VOID_TYPE,
)

class TestsMixin:
    """The integrated unit-test section (`--test` mode)."""

    def generate_test_section(self) -> str:
        """Generates test functions and a pengu_run_tests() runner for --test mode."""
        if not self.tests:
            return ""

        def _c_escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

        blocks: List[str] = [
            "/* -------------------------------------------------------------------------",
            " * Integrated Unit Tests (--test mode)",
            " * ------------------------------------------------------------------------- */",
        ]
        # Forward declarations of every test function.
        fwd = [f"static void pengu_test_{i}(void);" for i in range(len(self.tests))]
        blocks.append("\n".join(fwd))

        for i, t in enumerate(self.tests):
            self._apply_main_flag(t.get("filepath"))
            self.current_source_file = t.get("filepath")
            test_file = self._display_path(t.get("filepath")) or ""
            test_line = t.get("line") or 0
            lines = [f"static void pengu_test_{i}(void) {{"]
            self.indent_level += 1
            lines.append(f'{self.indent()}pengu_frame_push("pengu_test_{i}", "{test_file}", {test_line});')
            self.current_function = f"pengu_test_{i}"
            self.current_return_type = VOID_TYPE
            self.current_enchanted_type = None
            self.current_subst_map = {}
            self.local_vars = {}
            self.defer_stack.append([])
            self.errdefer_stack.append([])
            self._resolve_weave_refs_in_stmts(t["body_stmts"])
            body_code = self._translate_block(t["body_stmts"])
            lines.append(body_code)
            active_defers = self.defer_stack.pop() if self.defer_stack else []
            if self.errdefer_stack:
                self.errdefer_stack.pop()
            if not self._stmts_end_with_jump(t["body_stmts"]):
                if active_defers:
                    lines.append(f"{self.indent()}/* Deferred cleanup */")
                    for d in reversed(active_defers):
                        lines.append(self._format_defer_cleanup(d, self.indent()))
            lines.append(f"{self.indent()}pengu_frame_pop();")
            self.indent_level -= 1
            lines.append("}")
            blocks.append("\n".join(lines))

        names_c = ", ".join(f'"{_c_escape(t["name"])}"' for t in self.tests)
        fns_c = ", ".join(f"pengu_test_{i}" for i in range(len(self.tests)))
        n_tests = len(self.tests)
        # Emitted before the registry/selector: the selector calls
        # ``pengu_json_escape_print`` for ``--list``, so the helper has to be
        # defined first (C has no implicit static promotion).
        helpers = (
            "static int pengu_test_json_mode(void) {\n"
            '    const char *v = getenv("PENGU_TEST_JSON");\n'
            "    return v && *v;\n"
            "}\n\n"
            "static void pengu_json_escape_print(const char *s) {\n"
            "    if (!s) return;\n"
            "    for (; *s; s++) {\n"
            '        if (*s == \'"\') printf("\\\\\\\"");\n'
            '        else if (*s == \'\\\\\') printf("\\\\\\\\");\n'
            '        else if (*s == \'\\n\') printf("\\\\n");\n'
            '        else if (*s == \'\\r\') printf("\\\\r");\n'
            '        else if (*s == \'\\t\') printf("\\\\t");\n'
            "        else putchar(*s);\n"
            "    }\n"
            "}\n"
        )
        # The registry lives at file scope rather than inside ``pengu_run_tests``
        # so the single-test selector below can share it.
        #
        # Why a selector exists at all: a batch runner compiles ONE binary
        # holding every case and then spawns that binary once per case.  A
        # process yields exactly one stdout and one exit code, so per-case
        # judgement is only possible when each case gets its own process -- and
        # re-spawning an already-linked binary costs milliseconds where
        # recompiling costs seconds.  See tests/_inventory.md §9.2.
        registry = (
            f"static const char* pengu_test_names[{n_tests}] = {{ {names_c} }};\n"
            f"static void (*const pengu_test_fns[{n_tests}])(void) = {{ {fns_c} }};\n"
        )
        selector = (
            "/*\n"
            " * Single-test selection, for batch runners.\n"
            " *\n"
            " *   --list          one {\"index\":N,\"name\":\"...\"} JSON object per test\n"
            " *   --only-index N  run test N and exit (0 ok, 1 index out of range)\n"
            " *   --only NAME     run the first test called NAME\n"
            " *\n"
            " * Returns -1 when no selection flag was given, and main then falls\n"
            " * through to the ordinary full-suite run; otherwise the return value IS\n"
            " * this process's exit status.  --only-index is the form a runner should\n"
            " * use: test names repeat across a corpus, indices do not.\n"
            " *\n"
            " * The exit code is whatever the test body produced: 0 on success, and\n"
            " * the runtime's crash path (128+signal) when the body aborts.  That is\n"
            " * what lets one failing case be judged without hiding the others.\n"
            " */\n"
            "static int pengu_run_test_selection(int argc, char **argv) {\n"
            "  int i, a, want_list = 0;\n"
            "  const char *only_name = NULL;\n"
            "  long only_index = -1;\n"
            "  for (a = 1; a < argc; a++) {\n"
            '    if (strcmp(argv[a], "--list") == 0) {\n'
            "      want_list = 1;\n"
            '    } else if (strcmp(argv[a], "--only-index") == 0 && a + 1 < argc) {\n'
            "      only_index = strtol(argv[++a], NULL, 10);\n"
            '    } else if (strcmp(argv[a], "--only") == 0 && a + 1 < argc) {\n'
            "      only_name = argv[++a];\n"
            "    }\n"
            "  }\n"
            "  if (want_list) {\n"
            f"    for (i = 0; i < {n_tests}; i++) {{\n"
            '      printf("{\\"index\\":%d,\\"name\\":\\"", i);\n'
            "      pengu_json_escape_print(pengu_test_names[i]);\n"
            '      printf("\\"}\\n");\n'
            "    }\n"
            "    return 0;\n"
            "  }\n"
            "  if (only_index >= 0) {\n"
            f"    if (only_index >= {n_tests}) {{\n"
            '      fprintf(stderr, "pengu: test index %ld out of range (0..%d)\\n",\n'
            f"              only_index, {n_tests} - 1);\n"
            "      return 1;\n"
            "    }\n"
            "    pengu_test_fns[only_index]();\n"
            "    return 0;\n"
            "  }\n"
            "  if (only_name) {\n"
            f"    for (i = 0; i < {n_tests}; i++) {{\n"
            "      if (strcmp(pengu_test_names[i], only_name) == 0) {\n"
            "        pengu_test_fns[i]();\n"
            "        return 0;\n"
            "      }\n"
            "    }\n"
            "    fprintf(stderr, \"pengu: no test named '%s'\\n\", only_name);\n"
            "    return 1;\n"
            "  }\n"
            "  return -1;\n"
            "}\n"
        )
        runner = (
            "int pengu_run_tests(void) {\n"
            "  int i;\n"
            "  if (pengu_test_json_mode()) {\n"
            f'    printf("{{\\"event\\":\\"start\\",\\"total\\":{n_tests}}}\\n");\n'
            "    fflush(stdout);\n"
            f"    for (i = 0; i < {n_tests}; i++) {{\n"
            '      printf("{\\"event\\":\\"test_start\\",\\"name\\":\\"");\n'
            "      pengu_json_escape_print(pengu_test_names[i]);\n"
            '      printf("\\"}\\n");\n'
            "      fflush(stdout);\n"
            "      pengu_test_fns[i]();\n"
            '      printf("{\\"event\\":\\"test_pass\\",\\"name\\":\\"");\n'
            "      pengu_json_escape_print(pengu_test_names[i]);\n"
            '      printf("\\"}\\n");\n'
            "      fflush(stdout);\n"
            "    }\n"
            f'    printf("{{\\"event\\":\\"end\\",\\"total\\":{n_tests},\\"passed\\":{n_tests},\\"failed\\":0}}\\n");\n'
            "    fflush(stdout);\n"
            "    return 0;\n"
            "  }\n"
            f'  printf("Running {n_tests} test(s)...\\n");\n'
            "  fflush(stdout);\n"
            f"  for (i = 0; i < {n_tests}; i++) {{\n"
            '    printf("  [RUN] %s\\n", pengu_test_names[i]);\n'
            "    fflush(stdout);\n"
            "    pengu_test_fns[i]();\n"
            '    printf("  [PASS] %s\\n", pengu_test_names[i]);\n'
            "    fflush(stdout);\n"
            "  }\n"
            f'  printf("All {n_tests} test(s) passed.\\n");\n'
            "  fflush(stdout);\n"
            "  return 0;\n"
            "}\n"
        )
        blocks.append(helpers)
        blocks.append(registry)
        blocks.append(selector)
        blocks.append(runner)
        return "\n\n".join(blocks) + "\n"
    def generate_test_entry_point(self) -> str:
        """Generates a C main that runs the integrated unit tests."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Test Entry Point (--test mode)",
            " * ------------------------------------------------------------------------- */",
            "int main(int argc, char** argv) {",
            "  pengu_init(argc, argv);",
            "  /* Item 4.18: the --test entry point installs the crash handler too.",
            "     Phase 3 item 3.8 moved the install here for the normal main; the",
            "     test main was missed, so a fault in a test killed the process by",
            "     signal (Python rc=-8 -> shell 248) and the [PENGU CRASH] dump with",
            "     the failing frame never appeared. */",
            "  pengu_install_crash_handler();",
            "  int pengu_failed = 0;",
        ]
        if self.tests:
            # A batch runner spawns this binary once per case with
            # ``--only-index N``; without that flag the selector returns -1 and
            # the ordinary full-suite run happens exactly as before.
            lines.append("  int pengu_selected = pengu_run_test_selection(argc, argv);")
            lines.append("  if (pengu_selected >= 0) {")
            lines.append("    fflush(stdout);")
            lines.append("    fflush(stderr);")
            lines.append("    return pengu_selected;")
            lines.append("  }")
            lines.append("  pengu_failed = pengu_run_tests();")
        else:
            lines.append('  printf("No tests to run.\\n");')
            lines.append("  fflush(stdout);")
        lines.extend([
            "  fflush(stdout);",
            "  fflush(stderr);",
            "  return pengu_failed;",
            "}",
            "",
        ])
        return "\n".join(lines)
