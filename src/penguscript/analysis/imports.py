"""Module dependency graph, import path resolution, and cycle detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from penguscript.analysis.collector import collect
from penguscript.analysis.diagnostics import Diagnostic, Label
from penguscript.analysis.symbols import RawModuleDecl
from penguscript.frontend.ast_nodes import InvokeDecl
from penguscript.frontend.parser import parse
from penguscript.frontend.span import Span


def resolve_import_path(
    import_path_str: str,
    from_file: Path,
    project_root: Path,
    std_root: Path | None = None,
) -> tuple[Path | None, Diagnostic | None]:
    """Resolve an import path string to a canonical filesystem Path.

    Returns (resolved_path, None) on success, or (None, diagnostic) on error.
    """
    clean_str = import_path_str.strip()
    proj_root_resolved = project_root.resolve()

    # E2004: Empty import path
    if not clean_str:
        diag = Diagnostic(
            code="E2004",
            message="Import path cannot be empty",
            source_file=from_file,
        )
        return None, diag

    # Relative imports (./ or ../)
    if clean_str.startswith("./") or clean_str.startswith("../"):
        base_dir = from_file.parent if from_file.is_file() else from_file
        candidate_file = (base_dir / clean_str).with_suffix(".pengu")
        candidate_dir = base_dir / clean_str / "index.pengu"

        # Check project root boundary (E2005)
        for cand in (candidate_file, candidate_dir):
            try:
                cand.resolve().relative_to(proj_root_resolved)
            except ValueError:
                diag = Diagnostic(
                    code="E2005",
                    message=(
                        f"Relative import '{clean_str}' escapes project root '{proj_root_resolved}'"
                    ),
                    source_file=from_file,
                    hint="Relative imports cannot reference files outside the project root",
                )
                return None, diag

        if candidate_file.is_file():
            return candidate_file.resolve(), None
        if candidate_dir.is_file():
            return candidate_dir.resolve(), None

        diag = Diagnostic(
            code="E2001",
            message=f"Module '{clean_str}' not found",
            source_file=from_file,
            notes=(f"Looked for '{candidate_file}' and '{candidate_dir}'",),
        )
        return None, diag

    # Bare / project imports (e.g. "math", "utils/strings", "std/io")
    candidates: list[Path] = [
        proj_root_resolved / "src" / f"{clean_str}.pengu",
        proj_root_resolved / "src" / clean_str / "index.pengu",
        proj_root_resolved / f"{clean_str}.pengu",
        proj_root_resolved / clean_str / "index.pengu",
    ]

    # Standard library root candidates if std_root provided or "std/" prefix
    if std_root is not None:
        std_resolved = std_root.resolve()
        sub_path = clean_str[4:] if clean_str.startswith("std/") else clean_str
        candidates.append(std_resolved / f"{sub_path}.pengu")
        candidates.append(std_resolved / sub_path / "index.pengu")

    for cand in candidates:
        if cand.is_file():
            return cand.resolve(), None

    # E2001: Module not found
    diag = Diagnostic(
        code="E2001",
        message=f"Module '{clean_str}' not found",
        source_file=from_file,
        notes=(
            f"Looked for '{clean_str}.pengu' and '{clean_str}/index.pengu' in "
            f"'{proj_root_resolved}'",
        ),
    )
    return None, diag


@dataclass(slots=True)
class ModuleGraph:
    """Dependency graph of modules within a project."""

    project_root: Path
    modules: dict[Path, RawModuleDecl] = field(default_factory=dict)
    dependencies: dict[Path, list[Path]] = field(default_factory=dict)
    dependents: dict[Path, list[Path]] = field(default_factory=dict)
    import_spans: dict[tuple[Path, Path], Span] = field(default_factory=dict)
    import_nodes: dict[tuple[Path, Path], InvokeDecl] = field(default_factory=dict)
    topological_order: list[Path] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def is_acyclic(self) -> bool:
        """Return True if the dependency graph contains no cycles."""
        return not any(d.code == "E2002" for d in self.diagnostics)


class ModuleGraphBuilder:
    """Builder that resolves imports and constructs a validated ModuleGraph."""

    def __init__(
        self,
        project_root: Path,
        std_root: Path | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.std_root = std_root.resolve() if std_root else None
        self.graph = ModuleGraph(project_root=self.project_root)

    def build(
        self,
        modules: dict[Path, RawModuleDecl] | None = None,
        entry_points: list[Path] | None = None,
    ) -> ModuleGraph:
        """Build the module graph, discovering dependencies and sorting topologically."""
        # Seed known modules
        if modules:
            for p, decl in modules.items():
                self.graph.modules[p.resolve()] = decl

        # If entry points provided, load them
        if entry_points:
            for ep in entry_points:
                self._ensure_module_loaded(ep.resolve())

        # If neither provided, find all *.pengu in project_root
        if not self.graph.modules:
            for file_path in self.project_root.rglob("*.pengu"):
                if file_path.is_file():
                    self._ensure_module_loaded(file_path.resolve())

        # Initialize adjacency lists for all known modules
        for mod_path in self.graph.modules:
            self.graph.dependencies.setdefault(mod_path, [])
            self.graph.dependents.setdefault(mod_path, [])

        # Resolve all imports and build graph edges
        # Use list of keys because new modules may be added dynamically
        visited_modules: set[Path] = set()
        queue = list(self.graph.modules.keys())

        while queue:
            current_path = queue.pop(0)
            if current_path in visited_modules:
                continue
            visited_modules.add(current_path)

            raw_decl = self.graph.modules[current_path]
            for invoke in raw_decl.imports:
                target_path, diag = resolve_import_path(
                    import_path_str=invoke.path,
                    from_file=current_path,
                    project_root=self.project_root,
                    std_root=self.std_root,
                )

                if diag is not None:
                    # Attach invoke span if diagnostic doesn't have one
                    if diag.span is None and invoke.span is not None:
                        diag = Diagnostic(
                            code=diag.code,
                            message=diag.message,
                            severity=diag.severity,
                            span=invoke.span,
                            source_file=current_path,
                            secondary_labels=diag.secondary_labels,
                            notes=diag.notes,
                            hint=diag.hint,
                        )
                    self.graph.diagnostics.append(diag)
                    continue

                assert target_path is not None
                target_resolved = target_path.resolve()

                # Self-import check (E2008)
                if target_resolved == current_path:
                    self.graph.diagnostics.append(
                        Diagnostic(
                            code="E2008",
                            message=f"Module '{current_path.name}' cannot import itself",
                            span=invoke.span,
                            source_file=current_path,
                        )
                    )
                    continue

                # Record edge
                self.graph.dependencies.setdefault(current_path, [])
                if target_resolved not in self.graph.dependencies[current_path]:
                    self.graph.dependencies[current_path].append(target_resolved)

                self.graph.dependents.setdefault(target_resolved, [])
                if current_path not in self.graph.dependents[target_resolved]:
                    self.graph.dependents[target_resolved].append(current_path)

                if invoke.span is not None:
                    self.graph.import_spans[(current_path, target_resolved)] = invoke.span
                self.graph.import_nodes[(current_path, target_resolved)] = invoke

                # Ensure target module is loaded
                if target_resolved not in self.graph.modules:
                    self._ensure_module_loaded(target_resolved)
                    if target_resolved not in visited_modules:
                        queue.append(target_resolved)

        # Detect cycles and compute topological ordering
        self._detect_cycles_and_sort()
        return self.graph

    def _ensure_module_loaded(self, path: Path) -> None:
        """Parse and collect a module if not already loaded."""
        canonical = path.resolve()
        if canonical in self.graph.modules:
            return

        if not canonical.is_file():
            return

        try:
            text = canonical.read_text(encoding="utf-8")
            mod_ast = parse(text)
            raw = collect(mod_ast, path=canonical)
            self.graph.modules[canonical] = raw
            # Propagate any collector diagnostics
            self.graph.diagnostics.extend(raw.diagnostics)
        except Exception as exc:
            self.graph.diagnostics.append(
                Diagnostic(
                    code="E2001",
                    message=f"Failed to read or parse module '{canonical.name}': {exc}",
                    source_file=canonical,
                )
            )

    def _detect_cycles_and_sort(self) -> None:
        """Detect import cycles using 3-color DFS and produce topological ordering."""
        # 0 = WHITE (unvisited), 1 = GRAY (currently visiting), 2 = BLACK (finished)
        colors: dict[Path, int] = {p: 0 for p in self.graph.modules}
        call_stack: list[Path] = []
        visited_order: list[Path] = []
        reported_cycles: set[frozenset[Path]] = set()

        def dfs(node: Path) -> None:
            colors[node] = 1
            call_stack.append(node)

            for neighbor in self.graph.dependencies.get(node, []):
                if neighbor not in colors:
                    continue

                if colors[neighbor] == 1:
                    # Cycle detected!
                    cycle_start_idx = call_stack.index(neighbor)
                    cycle_nodes = call_stack[cycle_start_idx:] + [neighbor]
                    cycle_set = frozenset(cycle_nodes)

                    if cycle_set not in reported_cycles:
                        reported_cycles.add(cycle_set)
                        self._emit_cycle_diagnostic(cycle_nodes)

                elif colors[neighbor] == 0:
                    dfs(neighbor)

            call_stack.pop()
            colors[node] = 2
            visited_order.append(node)

        for mod_path in sorted(self.graph.modules.keys()):
            if colors[mod_path] == 0:
                dfs(mod_path)

        # In visited_order, dependencies finish before dependents.
        # So visited_order is already a valid topological evaluation order!
        self.graph.topological_order = visited_order

    def _emit_cycle_diagnostic(self, cycle_nodes: list[Path]) -> None:
        """Emit an E2002 diagnostic with primary span and secondary labels for each hop."""
        cycle_chain_str = " -> ".join(p.name for p in cycle_nodes)
        closing_from = cycle_nodes[-2]
        closing_to = cycle_nodes[-1]
        closing_span = self.graph.import_spans.get((closing_from, closing_to))

        # Build secondary labels for intermediate hops
        secondary: list[Label] = []
        for i in range(len(cycle_nodes) - 2):
            hop_from = cycle_nodes[i]
            hop_to = cycle_nodes[i + 1]
            hop_span = self.graph.import_spans.get((hop_from, hop_to))
            if hop_span is not None:
                secondary.append(
                    Label(
                        span=hop_span,
                        message=f"imports '{hop_to.name}' here",
                    )
                )

        self.graph.diagnostics.append(
            Diagnostic(
                code="E2002",
                message=f"Import cycle detected: {cycle_chain_str}",
                span=closing_span,
                source_file=closing_from,
                secondary_labels=tuple(secondary),
                notes=(
                    "Circular dependencies between modules are not allowed; "
                    "combine declarations into the same realm or extract shared symbols",
                ),
            )
        )


def build_module_graph(
    modules: dict[Path, RawModuleDecl] | None = None,
    project_root: Path | str = ".",
    entry_points: list[Path] | None = None,
    std_root: Path | None = None,
) -> ModuleGraph:
    """Build and validate the module graph for a project."""
    root = Path(project_root) if isinstance(project_root, str) else project_root
    builder = ModuleGraphBuilder(project_root=root, std_root=std_root)
    return builder.build(modules=modules, entry_points=entry_points)


__all__ = [
    "ModuleGraph",
    "ModuleGraphBuilder",
    "build_module_graph",
    "resolve_import_path",
]
