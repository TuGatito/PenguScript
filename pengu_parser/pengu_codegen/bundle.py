"""The final orchestrator that assembles `bundle.c`.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Dict,
    List,
    Optional,
    PENGU_VERSION,
    Set,
    Tree,
    _dce_collect_refs,
    _dce_summarize,
    os,
    prune_weaves,
)

#: ``PENGU_ENABLE_*`` runtime gate -> the ``std`` module that switches it on.
#: Mirrors ``pengu_project.py``'s ``_FEATURE_GATE_MODULES`` (which also decides
#: which native ``-l`` archives get linked). The two tables are duplicated
#: rather than shared because the code generator must not import the build
#: manager; ``tests/compiler/test_binary_size_reduction.py`` asserts they agree.
FEATURE_GATE_MODULES: "Dict[str, str]" = {
    "PENGU_ENABLE_REGEX": "regulus",
    "PENGU_ENABLE_XML": "parchment",
    "PENGU_ENABLE_NET": "precis",
    "PENGU_ENABLE_CRYPTO": "seal",
    "PENGU_ENABLE_THREADS": "filum",
}

#: Runtime C symbol prefix -> the gate that must stay on for it. Consulted
#: against the generated body so a hand-written ``declare pengu_c_regulus_*``
#: keeps compiling even without ``import std.regulus``.
FEATURE_GATE_PREFIXES: "Dict[str, str]" = {
    "pengu_c_regulus_": "PENGU_ENABLE_REGEX",
    "pengu_c_parchment_": "PENGU_ENABLE_XML",
    "pengu_c_precis_": "PENGU_ENABLE_NET",
    "pengu_c_seal_": "PENGU_ENABLE_CRYPTO",
    "pengu_c_filum_": "PENGU_ENABLE_THREADS",
}


def _std_module_stem(path: str) -> Optional[str]:
    """``/repo/std/regulus.pengu`` -> ``"regulus"``; anything else -> None."""
    norm = str(path).replace("\\", "/")
    idx = norm.rfind("/std/")
    if idx < 0:
        return None
    return os.path.splitext(norm[idx + len("/std/"):])[0]


class BundleMixin:
    """The final orchestrator that assembles `bundle.c`."""

    def generate_bundle(
        self,
        custom_includes: Optional[List[str]] = None,
        is_library: bool = False,
        output_path: Optional[str] = None,
        is_test: bool = False
    ) -> str:
        """Generates single monolithic bundle.c combining all modules and runtime header.

        Layout:
        1. Auto-generated header comment.
        2. #include "pengu_runtime.h"
        3. Project custom #include <header.h> directives.
        4. Forward declarations of all types.
        5. Type definitions (runes, echos, omens, aliases, consts).
        6. Function prototypes for all modules.
        7. Function implementations in topological dependency order.
        8. Test section + test entry point (--test mode) or normal entry wrapper.

        Args:
            custom_includes: Additional C headers from pengu.yaml.
            is_library: True if generating static or shared library artifact.
            output_path: Optional destination file path to write bundle.c.
            is_test: True to emit the integrated unit-test runner instead of the
                normal application entry point.

        Returns:
            Generated C code string.
        """
        # Dead-code elimination: drop std/lib weaves nothing reachable refers to.
        # Runs before any section is generated so prototypes and definitions stay
        # consistent (see pengu_dce.py for the safety rules).
        if self.dce_enabled and self.weaves:
            import time as _time
            _t_dce = _time.time()
            before = len(self.weaves)
            # 'test' blocks are collected separately from the weaves, so their
            # references are roots too (otherwise --test mode would link against
            # pruned std helpers).
            extra_roots: Set[str] = set()
            for test in self.tests:
                extra_roots |= _dce_collect_refs(test.get("body_stmts") or [])
            kept, dropped = prune_weaves(self.weaves, extra_refs=extra_roots,
                                         base_dir=self.base_dir)
            if dropped:
                self.weaves = kept
                self.dce_stats = {
                    "before": before,
                    "after": len(kept),
                    "dropped": len(dropped),
                    "names": sorted({str(w.get("name", "?")) for w in dropped}),
                    "seconds": _time.time() - _t_dce,
                    "message": _dce_summarize(dropped, before, len(kept)),
                }

        all_includes = list(self.includes)
        if custom_includes:
            for inc in custom_includes:
                if inc not in all_includes:
                    all_includes.append(inc)

        # `#line` directives are spelled relative to the bundle so the paths stay
        # short and portable; everything else keeps its absolute path.
        if self.compile_env is not None:
            self.debug_mode = bool(getattr(self.compile_env, "is_debug", False))
            if not hasattr(self, "_unsafe_depth"):
                self._unsafe_depth = 0
        self.line_base_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else None
        self.bundle_display_path = os.path.basename(output_path) if output_path else None

        sections = [
            f"/* Auto-generated by PenguScript v{PENGU_VERSION} */",
            '#include "pengu_runtime.h"',
            # The bundle and a prebuilt libpengu_runtime.a must agree on the ABI;
            # a mismatch silently reinterprets struct fields, so fail at compile
            # time instead of corrupting memory at runtime.  `_Static_assert` is
            # C11, so it is guarded out for strict C99 builds.
            "#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L",
            f'_Static_assert(PENGU_ABI_VERSION == {self.expected_abi_version}, '
            f'"pengu_runtime.h ABI mismatch: bundle expects v{self.expected_abi_version}");',
            "#endif",
            # Item 4.17: reference `pengu_abi_version` from every bundle so the
            # runtime archive cannot be dropped by the linker and a stale
            # `libpengu_runtime.a` fails at link time. Without a reference the
            # archive is never pulled in, so "always linking it" would be a
            # no-op. `__attribute__((used))` keeps the pin alive under -O2/-O3;
            # tcc strips its output, so `nm` cannot verify the pin there (see
            # docs/ABI.md).
            "extern int pengu_abi_version(void);",
            "#if defined(__GNUC__) || defined(__clang__)",
            "__attribute__((used))",
            "#endif",
            "static int (*const _pengu_abi_pin)(void) = pengu_abi_version;",
        ]

        # Self-describing marker so a bundle.c found in the wild says whether DCE
        # ran and how much it dropped (handy when A/B comparing --no-dce builds).
        if self.dce_stats.get("dropped"):
            sections.append(
                f"/* Dead-code elimination: pruned {self.dce_stats['dropped']} of "
                f"{self.dce_stats['before']} std/lib weave(s), "
                f"{self.dce_stats['before']} -> {self.dce_stats['after']} */"
            )
        elif not self.dce_enabled:
            sections.append("/* Dead-code elimination: disabled (PENGU_NO_DCE) */")

        for inc in all_includes:
            if inc.startswith("<") or inc.startswith('"'):
                sections.append(f"#include {inc}")
            else:
                sections.append(f'#include "{inc}"')

        sections.append("")
        sections.append("/* Compiled modules in topological order:")
        for mod in self.import_order:
            sections.append(f" * - {os.path.basename(mod)}")
        sections.append(" */")
        sections.append("")


        # Generate every section before assembling so the lazily-registered
        # element helpers (list of maybe/result/array) are all known: they are
        # emitted as forward declarations before the function definitions and as
        # definitions after them.  Relative generation order is unchanged, and
        # the test section is generated here too because its bodies can also
        # require element helpers.
        forward_decls = self.generate_forward_declarations()
        type_defs = self.generate_type_definitions()
        derived_impls = self.generate_derived_implementations()
        constants = self.generate_constants()
        prototypes = self.generate_function_prototypes()
        lambdas_code = self.generate_lambdas()
        function_defs = self.generate_function_definitions()
        test_section = self.generate_test_section() if is_test else ""
        entry_code = ""
        if not is_library:
            entry_code = (self.generate_test_entry_point() if is_test
                          else self.generate_entry_point())
        sections.append(forward_decls)
        sections.append(type_defs)
        sections.append(derived_impls)
        sections.append(constants)
        sections.append(prototypes)
        sections.append(self._generated_c_reset())
        sections.append(lambdas_code)
        sections.append(function_defs)
        sections.append(self._generated_c_reset())

        if test_section:
            sections.append(test_section)
        if entry_code:
            sections.append(entry_code)

        bundle_code = self._inject_feature_gates("\n".join(sections))

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(bundle_code)

        return bundle_code

    def _std_feature_gates(self, bundle_code: str) -> "Dict[str, int]":
        """Value of every ``PENGU_ENABLE_*`` gate for this program.

        A gate is 1 when the matching ``std`` module was imported *or* when the
        generated body mentions one of the subsystem's C symbols. The second
        condition matters: a program can ``declare pengu_c_regulus_compile``
        and call it without ever importing ``std.regulus``, and compiling that
        against a header with the declarations gated out would be a regression.
        """
        imported: Set[str] = set()
        for module in (self.import_order or []):
            stem = _std_module_stem(module)
            if stem:
                imported.add(stem)

        gates = {gate: 0 for gate in FEATURE_GATE_MODULES}
        for gate, module in FEATURE_GATE_MODULES.items():
            if module in imported:
                gates[gate] = 1
        for prefix, gate in FEATURE_GATE_PREFIXES.items():
            if prefix in bundle_code:
                gates[gate] = 1
        return gates

    def _inject_feature_gates(self, bundle_code: str) -> str:
        """Emits the ``#define PENGU_ENABLE_*`` preamble above the runtime include.

        The runtime header defaults every gate to 1 so a plain C consumer sees
        the whole API; the bundle narrows that to what the program actually
        uses. ``pengu_project.py`` links the matching native archives from the
        same information (see BENCHMARKS.md §Binary size).
        """
        marker = '#include "pengu_runtime.h"'
        if marker not in bundle_code:
            return bundle_code
        gates = self._std_feature_gates(bundle_code)
        lines = ["/* --- PenguScript 2.0 subsystem feature gates (size reduction) --- */"]
        for gate in FEATURE_GATE_MODULES:
            lines.append(f"#define {gate} {gates[gate]}")
        lines.append("/* ----------------------------------------------------------------- */")
        return bundle_code.replace(marker, "\n".join(lines) + "\n" + marker, 1)

    def _resolve_weave_refs_in_stmts(self, stmts: List[Tree]) -> None:
        """Pre-pass: injects c_name into var_ref nodes when pointing to a weave."""
        for stmt in stmts:
            if not isinstance(stmt, Tree):
                continue
            for node in stmt.iter_subtrees():
                if node.data == "var_ref":
                    name = str(node.children[0])
                    sym = self.symbols.lookup(name) if self.symbols else None
                    if sym is not None and getattr(sym, "kind", "") in ("weave", "declare", "function"):
                        c_name = getattr(sym, "c_name", None)
                        if not c_name or c_name == name:
                            if self.current_source_file:
                                for w in self.weaves:
                                    if w.get("name") == name and w.get("filepath") == self.current_source_file:
                                        c_name = w.get("c_name")
                                        break
                            if not c_name and name in self.fn_info:
                                c_name = self.fn_info[name].get("c_name")
                        if c_name:
                            node._pengu_resolved_c_name = c_name
                    elif name in self.fn_info:
                        c_name = self.fn_info[name].get("c_name")
                        if c_name:
                            node._pengu_resolved_c_name = c_name
    def get_temp_name(self, prefix: str = "_tmp") -> str:
        """Generates unique local variable identifier.

        Args:
            prefix: Name prefix.

        Returns:
            Unique identifier string.
        """
        self.temp_counter += 1
        return f"{prefix}_{self.temp_counter}"
    def indent(self) -> str:
        """Returns current indentation spaces string."""
        return "  " * self.indent_level
