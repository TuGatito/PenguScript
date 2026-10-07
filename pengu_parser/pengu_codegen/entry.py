"""The program entry point.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations


class EntryMixin:
    """The program entry point."""

    def generate_entry_point(self) -> str:
        """Generates standard C main function wrapper for executable output."""
        if not self.has_main:
            return ""

        main_call = getattr(self, "main_c_name", "pengu_main")
        if self._main_is_void():
            call_lines = [f"  {main_call}();"]
            return_lines = ["  return 0;"]
        else:
            call_lines = [f"  int pengu_status = (int){main_call}();"]
            return_lines = ["  return pengu_status;"]

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Entry Point Wrapper",
            " * ------------------------------------------------------------------------- */",
            "int main(int argc, char** argv) {",
            "  /* Expose the program arguments to 'rites.get_args()' etc. */",
            "  pengu_init(argc, argv);",
            "  /* Phase 3 item 3.8: install the crash handler exactly once, at process",
            "     start. It used to be installed lazily from pengu_frame_push, which",
            "     meant a racy check on every single frame push in the program. */",
            "  pengu_install_crash_handler();",
        ]
        lines += call_lines
        lines += [
            "  fflush(stdout);",
            "  fflush(stderr);",
        ]
        lines += return_lines
        lines += ["}", ""]

        return "\n".join(lines)
