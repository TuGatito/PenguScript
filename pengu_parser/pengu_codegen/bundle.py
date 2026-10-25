"""The final orchestrator that assembles `bundle.c`.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

import re
from collections import deque

from ._base import (
    Any,
    Dict,
    List,
    Optional,
    PENGU_VERSION,
    RuneType,
    Set,
    Tree,
    _dce_collect_refs,
    _dce_identifiers_in_text,
    _dce_resolved_std_roots,
    _dce_summarize,
    is_prunable_module,
    os,
    prune_weaves,
)

#: Identifier-shaped token in generated C.  Reachability discovery scans the C
#: it has just produced: the text contains the exact `c_name` of every function
#: value, call, callback table and `@mutates` alias, so no AST-name heuristic
#: is involved.
_C_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

#: ``PENGU_ENABLE_*`` runtime gate -> the ``std`` module that switches it on.
#: Mirrors ``pengu_project.py``'s ``_FEATURE_GATE_MODULES`` (which also decides
#: which native ``-l`` archives get linked). The two tables are duplicated
#: rather than shared because the code generator must not import the build
#: manager; ``tests/compiler/test_binary_size_reduction.py`` asserts they agree.
#:
#: The core runtime has exactly one gated subsystem left (threads). Bindings to
#: external libraries no longer ship here: they live in satellite repositories.
FEATURE_GATE_MODULES: "Dict[str, str]" = {
    "PENGU_ENABLE_THREADS": "filum",
}

#: Runtime C symbol prefix -> the gate that must stay on for it. Consulted
#: against the generated body so a hand-written ``declare pengu_c_filum_*``
#: keeps compiling even without ``import std.filum``.
FEATURE_GATE_PREFIXES: "Dict[str, str]" = {
    "pengu_c_filum_": "PENGU_ENABLE_THREADS",
}


def _std_module_stem(path: str) -> Optional[str]:
    """``/repo/std/spark.pengu`` -> ``"spark"``; anything else -> None."""
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
        is_test: bool = False,
        c_glue_text: str = "",
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
            c_glue_text: Project C glue sources, scanned as DCE roots when
                ``--dce-scope=user`` is active.

        Returns:
            Generated C code string.
        """
        # A bundle is generated once per builder, but keeping the pass
        # idempotent makes `generate_bundle()` safe to call twice (tests and
        # the LSP do).  The catalog is captured before any pruning, so a second
        # call can rediscover from the full set instead of from the previous
        # call's filtered list.
        import time as _time
        _t_dce_all = _time.time()
        if self._dce_all_weaves:
            known = {id(w) for w in self._dce_all_weaves}
            for w in self.weaves:
                if id(w) not in known:
                    self._dce_all_weaves.append(w)
                    known.add(id(w))
            self.weaves = list(self._dce_all_weaves)
        else:
            self._dce_all_weaves = list(self.weaves)
        self._definition_cache = {}
        self._dce_materialized = set()
        self._live_type_names = None

        # Phase 3 is opt-in and never applies to tests or library outputs: test
        # bodies must be able to call any helper, and a library's public API is
        # its product.  `--no-dce` also wins.
        scope_user = bool(self.dce_scope_user and self.dce_enabled
                          and not is_test and not is_library)
        self._dce_scope_user_active = scope_user
        # Native include/link pruning is opt-in and never applies to tests or
        # library outputs (their headers/libraries are the public boundary).
        native_active = bool(self.prune_native_enabled and self.dce_enabled
                             and not is_test and not is_library)
        self._native_active = native_active

        # Compact label for the self-describing marker below (`std` = checked
        # now, `off` = PENGU_NO_DCE, `test` = instances kept for test bodies,
        # `user` = ordinary project modules are prunable too).
        dce_mode = "test" if is_test else ("user" if scope_user else "std")

        # Dead-code elimination, pass 1: conservative, name-based.  This is the
        # fallback for --test (test bodies can call instances that the exact
        # pass would not see) and the starting point for the exact pass below.
        if self.dce_enabled and self.weaves:
            _t_dce = _time.time()
            before = len(self.weaves)
            # Resolve the standard-library roots once.  The same list is what
            # `is_prunable_module` uses, so a packaged std/ (FHS, PENGU_STD_DIR,
            # wheel) is pruned exactly like the checkout's.
            std_roots = _dce_resolved_std_roots()
            self._dce_std_roots = std_roots
            # 'test' blocks are collected separately from the weaves, so in
            # --test mode their references are roots too (otherwise the test
            # runner would link against pruned std helpers).  A normal build
            # does not emit the test section, so those references must NOT keep
            # production code alive: they used to inflate every `pengu run`.
            extra_roots: Set[str] = set()
            if is_test:
                for test in self.tests:
                    extra_roots |= _dce_collect_refs(test.get("body_stmts") or [])
            if scope_user and c_glue_text:
                # A C glue file can call a project weave the bundle never names
                # in PenguScript.  Scan every identifier (conservative) and keep
                # the matching names/c_names.
                extra_roots |= _dce_identifiers_in_text(c_glue_text)
            kept, dropped = prune_weaves(self.weaves, extra_refs=extra_roots,
                                         base_dir=self.base_dir, std_roots=std_roots,
                                         include_user=scope_user)
            self.weaves = kept
            if dropped:
                self.dce_stats = {
                    "before": before,
                    "after": len(kept),
                    "dropped": len(dropped),
                    "names": sorted({str(w.get("name", "?")) for w in dropped}),
                    "seconds": _time.time() - _t_dce,
                    "message": _dce_summarize(dropped, before, len(kept)),
                }
            else:
                self.dce_stats = {}
        else:
            self.dce_stats = {}

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

        # Generate the sections that do not depend on the weave list first.  The
        # discovery pass below translates bodies (so it needs `line_base_dir`
        # set) and scans lambdas/derived helpers, so those two sections are
        # generated here as well.  Nothing here mutates the weave list.
        self._prune_placeholder_types()
        self._prune_duplicate_type_aliases()
        derived_impls = self.generate_derived_implementations()
        constants = self.generate_constants()
        lambdas_code = self.generate_lambdas()

        # Dead-code elimination, pass 2: exact reachability over the C the
        # generator will actually emit.  Runs in normal builds only; --test
        # keeps every instance because test bodies are not part of this scan.
        if self.dce_enabled and dce_mode in ("std", "user") and self._dce_all_weaves:
            self.weaves = list(self._dce_all_weaves)
            extra_texts = (lambdas_code, derived_impls, constants)
            if scope_user and c_glue_text:
                extra_texts = extra_texts + (c_glue_text,)
            self._discover_reachable_weaves(extra_texts)
            if self.dce_stats:
                # Report both layers: the metric is "time spent pruning", not
                # just the exact pass.
                self.dce_stats["seconds"] = _time.time() - _t_dce_all

            # Phase 4a: derived helpers are `static inline`, so their only
            # possible callers are this bundle's own C.  Drop the blocks no
            # live body/lambda/constant (or another live block) names.
            roots = list(self._definition_cache.values()) + [lambdas_code, constants]
            derived_impls = self.prune_derived_implementations(roots)

        # Prototypes are independent of the type sections (they are just
        # signatures), and the type-liveness pass below needs their text: a
        # type can be named by a kept signature and nowhere else.
        prototypes = self.generate_function_prototypes()

        # Phase 4b, opt-in: drop types/constants no emitted C names.  Off by
        # default because a `c/` glue file can name a Pengu type or constant
        # the bundle never spells.  A library's public API includes its types,
        # so a shared/static/obj build keeps them all.
        prune_types = (self.prune_types_enabled and self.dce_enabled
                       and not is_test and not is_library)
        if prune_types:
            live_texts = (list(self._definition_cache.values())
                          + [prototypes, lambdas_code, derived_impls])
            live_consts = self.compute_live_consts(live_texts)
            constants = self.prune_constants(live_consts)
            extra_types = []
            for const_name in live_consts:
                const_type = (self.consts.get(const_name) or (None, None))[0]
                if const_type is not None:
                    extra_types.append(const_type)
            live_types = self.compute_live_types(
                live_texts + [constants], extra_types=extra_types)
            all_type_names = set()
            for table in (self.runes, self.echos, self.omens,
                          self.aliases, self.seals):
                all_type_names |= set(table)
            all_type_names -= self.declaration_types
            dropped_types = all_type_names - live_types
            if dropped_types:
                self.dce_stats = dict(self.dce_stats or {})
                self.dce_stats["types_before"] = len(all_type_names)
                self.dce_stats["types_after"] = len(all_type_names & live_types)
                self.dce_stats["types_dropped"] = len(dropped_types)

        # Type and forward sections come after discovery: translating a body
        # can materialize a specialization whose tuple return registers a new
        # product struct.  Generating the type section first would omit it.
        self._prune_placeholder_types()
        self._prune_duplicate_type_aliases()
        forward_decls = self.generate_forward_declarations()
        type_defs = self.generate_type_definitions()
        function_defs = self.generate_function_definitions()
        test_section = self.generate_test_section() if is_test else ""
        entry_code = ""
        if not is_library:
            entry_code = (self.generate_test_entry_point() if is_test
                          else self.generate_entry_point())

        if native_active:
            native_texts = (list(self._definition_cache.values())
                            + [prototypes, lambdas_code, derived_impls,
                               c_glue_text])
            module_includes = self._filter_native_includes(
                list(self.includes), custom_includes, native_texts)
            custom_list = [inc for inc in all_includes if inc not in self.includes]
            all_includes = module_includes + custom_list

        sections = [
            f"/* Auto-generated by PenguScript v{PENGU_VERSION} */",
            '#include "pengu_runtime.h"',
            # Derived helpers (`Par`, `Imago`, `Nexus`, tuple comparisons, ...)
            # are emitted for every deriving type, but a program only calls the
            # ones its own code reaches. GCC does not warn about an unused
            # `static inline`, Clang does, and `-Werror` turns that into a build
            # failure for perfectly valid programs. `unused` is the portable
            # spelling for "this definition is intentional and may be
            # unreferenced".
            "#if defined(__GNUC__) || defined(__clang__)",
            "#define PENGU_MAYBE_UNUSED __attribute__((unused))",
            "#else",
            "#define PENGU_MAYBE_UNUSED",
            "#endif",
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
            scope_note = " (scope=user)" if self._dce_scope_user_active else ""
            sections.append(
                f"/* Dead-code elimination: pruned {self.dce_stats['dropped']} of "
                f"{self.dce_stats['before']} module weave(s), "
                f"{self.dce_stats['before']} -> {self.dce_stats['after']}{scope_note} */"
            )
        elif not self.dce_enabled:
            sections.append("/* Dead-code elimination: disabled (PENGU_NO_DCE) */")
        if self.dce_stats.get("derived_dropped"):
            sections.append(
                f"/* Dead-code elimination: pruned {self.dce_stats['derived_dropped']} of "
                f"{self.dce_stats['derived_before']} derived helper block(s) */"
            )
        if self.dce_stats.get("types_dropped") or self.dce_stats.get("consts_dropped"):
            sections.append(
                f"/* Dead-code elimination (--prune-types): pruned "
                f"{self.dce_stats.get('types_dropped', 0)} type(s), "
                f"{self.dce_stats.get('consts_dropped', 0)} constant(s) */"
            )

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

    def _is_dce_root(self, w: Dict[str, Any]) -> bool:
        """True for a weave that survives regardless of who calls it.

        Roots are the entry point, every ``@export`` FFI symbol, and every
        weave that does not belong to a prunable ``std/``/``lib/`` module.
        User module weaves are roots until ``--dce-scope=user`` exists; a
        library build must keep its public API, so this stays conservative.
        """
        if (w.get("attributes") or {}).get("export"):
            # An FFI entry point is a root wherever it lives, including a
            # (rare) exported specialization.
            return True
        if w.get("is_generic") or w.get("subst_map"):
            # Monomorphized instances are not roots: the worklist discovers
            # them from the C symbol a live body actually names.  (They used to
            # be roots because their synthetic `filepath="."` is not under
            # std/, which pulled every instance of the transitive closure in.)
            return False
        if w.get("name") == "main" or w.get("c_name") == "pengu_main":
            return True
        filepath = str(w.get("filepath", ""))
        if getattr(self, "_dce_scope_user_active", False):
            # `--dce-scope=user`: ordinary project weaves are prunable; only
            # the C binding boundary stays a root.  C glue references are fed
            # through the extra-text scan.
            return filepath.endswith(".d.pengu")
        return not is_prunable_module(
            filepath, self.base_dir, self._dce_std_roots)

    def _materialize_instance(self, name: str,
                              catalog: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Collects an instance the code generator created on demand.

        The checker pre-registers almost every monomorphization, but a call
        whose explicit type arguments are resolved only at codegen time can add
        a new entry while a body is translated.  When the emitted C names one
        of those, the record is collected here instead of being pruned as
        "unknown".
        """
        existing = catalog.get(name)
        if existing is not None:
            return existing
        if name in self._dce_materialized:
            return None
        symbols = self.symbols
        if symbols is None:
            return None
        self._dce_materialized.add(name)

        fn = (getattr(symbols, "monomorphized_functions", {}) or {}).get(name)
        if fn is not None:
            fn_ast, subst_map = fn
            self._collect_monomorphized_weave(name, fn_ast, subst_map, None,
                                              filepath=".")
        else:
            entry = (getattr(symbols, "monomorphized_methods", {}) or {}).get(name)
            if entry is None:
                return None
            if len(entry) == 3:
                m_ast, subst_map, rec_type = entry
            else:
                m_ast, subst_map = entry
                rec_tname = name.rsplit("_", 1)[0]
                rec_type = symbols.lookup_type(rec_tname) or RuneType(name=rec_tname)
            self._collect_monomorphized_weave(name, m_ast, subst_map, rec_type,
                                              filepath=".")

        for w in reversed(self.weaves):
            if w.get("c_name") == name:
                catalog[name] = w
                return w
        return None

    def _scan_c_text(self, text: str, catalog: Dict[str, Dict[str, Any]],
                     queue: deque, queued: Set[str]) -> None:
        """Queues every catalog weave mentioned by generated C text.

        Scanning the emitted C (instead of the Pengu AST) is what makes the
        pass exact: the text contains the final ``c_name`` of calls, function
        values, ``@mutates`` variants and concept methods.  It also removes the
        old false positives where a local variable named ``len`` kept
        ``pengu_len`` alive: the C text spells the symbol ``pengu_len``, never
        ``len``.

        The scan is intentionally conservative in one direction only: an
        identifier that looks like a call but does not resolve to a C symbol
        keeps the weaves with that Pengu short name.  That fallback is rare
        (unresolved/generated calls) and cannot cause a missing definition.
        """
        if not text:
            return
        for match in _C_IDENT_RE.finditer(text):
            ident = match.group(0)
            dep = catalog.get(ident)
            if dep is None:
                dep = self._materialize_instance(ident, catalog)
            if dep is None:
                tail = text[match.end():]
                if tail[:1] == "(":
                    for cand in self._dce_by_name.get(ident, ()):
                        if cand["c_name"] not in queued:
                            queue.append(cand)
                            queued.add(cand["c_name"])
                continue
            if dep["c_name"] not in queued:
                queue.append(dep)
                queued.add(dep["c_name"])

    def _discover_reachable_weaves(self, extra_texts=()) -> None:
        """Filters ``self.weaves`` to the weaves the emitted C actually reaches.

        Worklist over C symbols: translate a root, scan the text it produced,
        translate every new catalog name, repeat.  The bodies are cached in
        ``self._definition_cache`` so the final emission is byte-for-byte what
        the scanner inspected (and no body is translated twice).

        ``extra_texts`` are sections that are also emitted as C but are not
        weave bodies (lambdas, derived helpers); a dependency named only there
        must survive too.
        """
        all_weaves = list(self._dce_all_weaves or self.weaves)
        catalog: Dict[str, Dict[str, Any]] = {}
        self._dce_by_name: Dict[str, List[Dict[str, Any]]] = {}
        for w in all_weaves:
            if w.get("is_generic"):
                continue
            catalog[w["c_name"]] = w
            self._dce_by_name.setdefault(str(w.get("name", "")), []).append(w)
        # Records materialized by an earlier build in the same generator are
        # part of the catalog too (they live after the original snapshot).
        for w in self.weaves[len(all_weaves):]:
            if w.get("is_generic"):
                continue
            catalog.setdefault(w["c_name"], w)
            self._dce_by_name.setdefault(str(w.get("name", "")), []).append(w)

        queue: deque = deque()
        queued: Set[str] = set()
        for w in all_weaves:
            if w.get("is_generic"):
                continue
            if self._is_dce_root(w) and w["c_name"] not in queued:
                queue.append(w)
                queued.add(w["c_name"])

        for text in extra_texts:
            self._scan_c_text(text, catalog, queue, queued)

        live: Set[str] = set()
        while queue:
            w = queue.popleft()
            name = w["c_name"]
            if name in live:
                continue
            live.add(name)
            text = self._definition_cache.get(name)
            if text is None:
                text = self._generate_one_definition(w)
                self._definition_cache[name] = text
            self._scan_c_text(text, catalog, queue, queued)

        before = len(self.weaves)
        dropped = [w for w in self.weaves if w["c_name"] not in live]
        self.weaves = [w for w in self.weaves if w["c_name"] in live]
        if dropped:
            self.dce_stats = {
                "before": before,
                "after": len(self.weaves),
                "dropped": len(dropped),
                "names": sorted({str(w.get("name", "?")) for w in dropped}),
                "message": _dce_summarize(dropped, before, len(self.weaves)),
            }
        else:
            self.dce_stats = {}

    def _std_feature_gates(self, bundle_code: str) -> "Dict[str, int]":
        """Value of every ``PENGU_ENABLE_*`` gate for this program.

        A gate is 1 when the matching ``std`` module was imported *or* when the
        generated body mentions one of the subsystem's C symbols. The second
        condition matters: a program can ``declare pengu_c_filum_mutex_new``
        and call it without ever importing ``std.filum``, and compiling that
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
        uses. ``pengu_project.py`` reads the same gates back out of the bundle
        to decide whether a precompiled header still matches.
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
                            existing = getattr(node, "_pengu_resolved_c_name", None)
                            if not (existing and existing in getattr(self.symbols, "monomorphized_functions", {})):
                                node._pengu_resolved_c_name = c_name
                    elif name in self.fn_info:
                        c_name = self.fn_info[name].get("c_name")
                        if c_name:
                            existing = getattr(node, "_pengu_resolved_c_name", None)
                            if not (existing and existing in getattr(self.symbols, "monomorphized_functions", {})):
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

    def _push_loop_scope(self, node: Tree, release: str = "") -> None:
        """Records an entered loop body for labeled-jump unwinding.

        C has no unwinding, so a `break outer` / `continue outer` that leaves an
        inner loop must run that inner loop's own cleanup *before* the `goto`.
        Each loop body pushes ``(label, release statement)``; the jump site looks
        its target up and emits the releases of everything above it.

        Args:
            node: the loop node being entered.
            release: the statement that releases the loop's temporaries (empty
                for a loop that owns nothing).
        """
        stack = getattr(self, "_loop_release_stack", None)
        if stack is None:
            stack = []
            self._loop_release_stack = stack
        stack.append((getattr(node, "loop_label", None), release))
        # Defer scopes opened inside the loop body must run when a `break` /
        # `continue` leaves them.  The baseline is the scope depth *outside* the
        # body, so the jump site can release exactly the scopes the jump leaves.
        depth_stack = getattr(self, "_loop_defer_baseline", None)
        if depth_stack is None:
            depth_stack = []
            self._loop_defer_baseline = depth_stack
        depth_stack.append(len(getattr(self, "defer_stack", []) or []))

    def _pop_loop_scope(self) -> None:
        """Leaves the innermost loop body (see :meth:`_push_loop_scope`)."""
        stack = getattr(self, "_loop_release_stack", None)
        if stack:
            stack.pop()
        depth_stack = getattr(self, "_loop_defer_baseline", None)
        if depth_stack:
            depth_stack.pop()

    def _scope_exit_defers(self, baseline: int = 0, ind: str = "") -> List[str]:
        """Cleanup lines for the defer scopes at or above ``baseline``.

        Args:
            baseline: first scope index to release. ``0`` means every active
                block scope (the `return` case); a loop baseline releases only
                the scopes opened inside that loop body.
            ind: indentation to prefix to each line.

        Returns:
            The concatenated ``defer`` cleanups, innermost scope first.
        """
        lines: List[str] = []
        stack = getattr(self, "defer_stack", None) or []
        for scope in reversed(stack[baseline:]):
            for deferred in reversed(scope):
                lines.append(self._format_defer_cleanup(deferred, ind))
        return lines

    def _loop_exit_releases(self) -> list:
        """Release statements for every loop a `return` leaves.

        A `return` unwinds the whole function, so each active owning loop's
        temporary must be released before the frame is popped.  The elements of a
        materialized iterable are copied into the loop variable, so releasing the
        buffer does not invalidate an element returned from inside the loop.
        """
        stack = getattr(self, "_loop_release_stack", None) or []
        return [release for _label, release in reversed(stack) if release]

    def _loop_jump_releases(self, label: str) -> list:
        """Release statements for the loops a labeled jump leaves behind.

        Returns the releases of every loop nested *inside* the loop named
        ``label``, outermost first (so an inner list is released before the
        outer one that may own it).  The target loop's own release is not
        included: a `break` lands on its anchor, which runs it, and a
        `continue` keeps the loop alive.

        Args:
            label: the target loop label of the jump.

        Returns:
            The statements to emit before the `goto` (empty when none).
        """
        stack = getattr(self, "_loop_release_stack", None) or []
        target = None
        for index in range(len(stack) - 1, -1, -1):
            if stack[index][0] == label:
                target = index
                break
        if target is None:
            return []
        return [release for _label, release in stack[target + 1:] if release]

    @staticmethod
    def _loop_label_target(node: Tree) -> Optional[str]:
        """Label of a ``break label`` / ``continue label`` node, or None.

        An unlabeled ``break``/``continue`` has no children; the labeled form
        carries the label as its first (and only) child.
        """
        children = getattr(node, "children", None)
        if not children:
            return None
        first = children[0]
        return str(first) if first is not None else None

    @staticmethod
    def _c_loop_label(label: str, kind: str) -> str:
        """C label name for the ``continue``/``break`` anchor of loop ``label``.

        The ``_pengu_`` prefix marks a compiler-generated identifier, and C
        labels live in their own namespace (separate from variables and tags),
        so the name cannot clash with a user identifier.  Two loops can never
        generate the same anchor: loop labels are unique per function (E0069).
        """
        return f"_pengu_label_{label}_{kind}"

    @staticmethod
    def _loop_label_is_used(node: Tree, label: str, kind: str) -> bool:
        """True when the loop subtree contains ``break label`` / ``continue label``.

        The anchor is emitted only when something jumps to it: an unused C label
        is ``-Wunused-label``, and this compiler builds its bundles with
        ``-Werror``.  A labeled loop that nobody breaks out of therefore costs
        exactly zero lines of C.
        """
        from pengu_parser.pengu_grammar import SIMPLE_STMT_ALIASES

        wanted = "break_stmt" if kind == "break" else "continue_stmt"
        for sub in node.iter_subtrees():
            if not isinstance(sub, Tree):
                continue
            data = SIMPLE_STMT_ALIASES.get(sub.data, sub.data)
            if data != wanted or not sub.children:
                continue
            first = sub.children[0]
            if first is not None and str(first) == label:
                return True
        return False

    def _loop_continue_label(self, node: Tree, body_ind: str) -> str:
        """``_<label>_continue: ;`` emitted at the end of a labeled loop body.

        Placed last inside the loop braces, so a ``goto`` from the body still
        runs the C loop's step expression and condition — exactly what
        ``continue`` does for the innermost loop.
        """
        label = getattr(node, "loop_label", None)
        if not label or not self._loop_label_is_used(node, label, "continue"):
            return ""
        return f"\n{body_ind}{self._c_loop_label(label, 'continue')}: ;"

    def _loop_break_label(self, node: Tree, ind: str) -> str:
        """``_<label>_break: ;`` emitted right after a labeled loop.

        Goes *before* the loop's own cleanup (e.g. the banish of a materialized
        iterable), so falling through the anchor runs that cleanup exactly once,
        and a jump out of the loop releases the temporaries it leaves by
        emitting them at the jump site (``_loop_jump_releases``).
        """
        label = getattr(node, "loop_label", None)
        if not label or not self._loop_label_is_used(node, label, "break"):
            return ""
        return f"\n{ind}{self._c_loop_label(label, 'break')}: ;"
