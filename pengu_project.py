#!/usr/bin/env python3
"""PenguScript Project & Build Manager (Cargo-style CLI).

Provides project configuration management, multi-target compilation (exe, c, obj, static, shared),
custom library linking (-l), external dependency & binding management (lib/<binding>/),
build directory isolation, incremental compilation caching, debug/release profiles,
template initialization, and multi-platform compilation support.
"""

from __future__ import annotations
import os
import sys
import time
import json
import shutil
import hashlib
import argparse
import subprocess
import tempfile
import re
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Set, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only (see from __future__ above)
    from lark import Tree

from dataclasses import dataclass, field, replace

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

# 'yaml' is imported lazily (see _load_yaml_module): it costs ~15 ms of startup
# and is only needed when a pengu.yaml is actually parsed.
yaml = None  # type: ignore


def _load_yaml_module():
    """Imports PyYAML on first use (None when it is not installed)."""
    global yaml
    if yaml is None:
        try:
            import yaml as _yaml  # type: ignore
            yaml = _yaml
        except ImportError:
            yaml = False  # type: ignore
    return yaml or None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# The compiler front end (Lark, checker, codegen) is imported on first use: a
# 'pengu run' cache hit never needs it, and importing Lark costs ~45 ms.
_LAZY_IMPORTS = {
    "PenguParser": ("pengu_parser.pengu_parser", "PenguParser"),
    "PenguChecker": ("pengu_parser.pengu_checker", "PenguChecker"),
    "resolve_imports": ("pengu_parser.pengu_symbols", "resolve_imports"),
    "ErrorReporter": ("pengu_parser.pengu_errors", "ErrorReporter"),
    "PenguError": ("pengu_parser.pengu_errors", "PenguError"),
    "PenguCodegen": ("pengu_parser.pengu_codegen", "PenguCodegen"),
    "main_flag_requested": ("pengu_parser.pengu_comptime", "main_flag_requested"),
    "parse_cli_defines": ("pengu_parser.pengu_comptime", "parse_cli_defines"),
}


def __getattr__(name: str):
    """PEP 562 lazy import of the compiler front end."""
    entry = _LAZY_IMPORTS.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    module = importlib.import_module(entry[0])
    value = getattr(module, entry[1])
    globals()[name] = value
    return value


from pengu_version import __version__ as PENGU_VERSION
from pengu_parser.pengu_codegen import set_release_unsafe as _set_release_unsafe
from pengu_semver import (
    DependencyConflictError,
    Requirement,
    ResolutionConflict,
    Version,
    parse_constraint,
    satisfies,
    select_version,
)
from pengu_paths import (
    find_runtime_header,
    runtime_include_dirs,
    runtime_lib_dirs,
    std_dirs,
    version_files,
    pkg_config_cflags,
    pkg_config_libs,
)
from pengu_cache import (
    cache_disabled,
    cache_root,
    cache_summary,
    clear_script_cache,
    gc_script_cache,
    lookup_cached_binary,
    script_cache_key,
    store_cached_binary,
)
from pengu_tcc import pick_dev_compiler, tcc_available, tcc_version, find_tcc



def file_content_digest(path: str) -> str:
    """Returns a short content digest of a file, or ``""`` when unreadable.

    Used by the incremental build cache: the cache key must depend on the
    *content* of the sources, not on their mtimes, because `build/` is shared by
    every program built in the same directory.

    Args:
        path: File to digest.

    Returns:
        Hex digest of the file bytes (empty string when the file cannot be read).
    """
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()



class OutputType(Enum):
    """Supported compilation output artifact targets."""
    EXE = "exe"
    C = "c"
    OBJ = "obj"
    STATIC = "static"
    SHARED = "shared"

    @classmethod
    def from_string(cls, val: str) -> OutputType:
        """Parses output type from configuration string.

        Args:
            val: String representation ('exe', 'c', 'obj', 'static', 'shared').

        Returns:
            Matching OutputType enum member.
        """
        val_lower = val.lower().strip()
        for member in cls:
            if member.value == val_lower:
                return member
        return cls.EXE


def extract_lib_name(filename: str) -> Optional[str]:
    """Extracts library linking name from file (e.g. libwebui.a -> webui, raylib.lib -> raylib).

    Args:
        filename: Base filename or path.

    Returns:
        Library name suitable for -l flag, or None if not recognized as library.
    """
    base = os.path.basename(filename)
    name, ext = os.path.splitext(base)
    ext_lower = ext.lower()
    if ext_lower not in (".a", ".so", ".dylib", ".lib", ".dll"):
        return None
    if name.endswith(".dll"):  # e.g. libfoo.dll.a
        name = os.path.splitext(name)[0]
    if name.startswith("lib"):
        name = name[3:]
    return name if name else None


@dataclass(frozen=True)
class TargetTriple:
    """Parsed cross-compilation target triple (roadmap 3.5)."""
    raw: str
    arch: str
    os: str
    env: str

    @property
    def is_windows(self) -> bool:
        return self.os == "windows"

    @property
    def is_macos(self) -> bool:
        return self.os == "darwin"

    @property
    def is_linux(self) -> bool:
        return self.os == "linux"


def host_os() -> str:
    """Host OS in triple vocabulary ('windows' | 'darwin' | 'linux')."""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def parse_target_triple(text: str) -> TargetTriple:
    """Parses a target triple like ``x86_64-w64-mingw32`` or ``aarch64-apple-darwin``.

    Only the OS/environment are interpreted (Linux ⇄ Windows is the supported
    cross pair); the architecture is kept for diagnostics and compiler lookup.
    """
    raw = (text or "").strip()
    low = raw.lower()
    if not raw:
        return TargetTriple(raw="", arch="", os="", env="")
    if "mingw" in low or "windows" in low or "win32" in low or "msvc" in low:
        os_name = "windows"
    elif "darwin" in low or "apple" in low or "macos" in low:
        os_name = "darwin"
    elif "linux" in low or "musl" in low or "gnu" in low:
        os_name = "linux"
    else:
        os_name = ""
    env = ""
    if "musl" in low:
        env = "musl"
    elif "msvc" in low:
        env = "msvc"
    elif "mingw" in low:
        env = "mingw"
    elif "gnu" in low:
        env = "gnu"
    arch = raw.split("-")[0].lower()
    return TargetTriple(raw=raw, arch=arch, os=os_name, env=env)


@dataclass
class ProjectConfig:
    """Project configuration specifying build rules, directories, libraries, profiles, and output target.

    Attributes:
        name: Project or binary name.
        version: Semantic version string.
        entry: Main entry .pengu source file.
        output: Target output type (exe, c, obj, static, shared).
        output_name: Base name for generated artifact.
        build_dir: Relative or absolute directory for intermediate/final build artifacts.
        src_dir: Directory containing project .pengu sources (default: 'src').
        lib_dir: Directory containing external bindings/dependencies (default: 'lib').
        include_dir: Directory containing project C headers (default: 'include').
        c_dir: Directory containing project C glue/sources (default: 'c').
        dependencies: Dictionary mapping dependency names to source URLs or local paths.
        includes: List of C headers required by project.
        links: List of libraries to link via -l flags (without -l prefix).
        lib_dirs: List of search directories for libraries (-L flags).
        include_dirs: List of search directories for C headers (-I flags).
        cflags: List of default C compiler options.
        ldflags: List of default linker options.
        defines: List of default preprocessor macro definitions (-D flags).
        cc: C compiler executable (default: 'gcc').
        profiles: Dictionary mapping profile names ('debug', 'release') to custom flags.
        profile: Selected active profile name (default: 'debug').
        base_dir: Root project directory path.
    """
    name: str = "pengu_app"
    version: str = "0.1.0"
    entry: str = "src/main.pengu"
    output: OutputType = OutputType.EXE
    output_name: str = "app"
    build_dir: str = "build"
    src_dir: str = "src"
    lib_dir: str = "lib"
    include_dir: str = "include"
    c_dir: str = "c"
    dependencies: Dict[str, Any] = field(default_factory=dict)
    includes: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    lib_dirs: List[str] = field(default_factory=list)
    include_dirs: List[str] = field(default_factory=list)
    cflags: List[str] = field(default_factory=lambda: ["-O2", "-Wall", "-std=c11"])
    ldflags: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    cc: str = "gcc"
    profiles: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "debug": {
            "cflags": ["-g", "-O0", "-Wall"],
            "defines": ["DEBUG"],
        },
        "release": {
            "cflags": ["-O3", "-flto", "-DNDEBUG"],
            "defines": ["NDEBUG"],
        }
    })
    profile: str = "debug"
    base_dir: str = field(default_factory=lambda: os.path.abspath(os.getcwd()))
    assets_dir: str = "assets"
    assets_module: str = "arca"
    assets_embed: bool = True
    assets_exclude: List[str] = field(default_factory=list)
    # Roadmap Phase 2: portable C output.
    # ``strict_c99`` forbids GNU statement expressions / __auto_type in the
    # emitted C; ``target_compiler`` selects the attribute/restrict dialect
    # ("gcc" | "clang" | "msvc" | "tcc"; empty = infer from ``cc``).
    strict_c99: bool = False
    release_unsafe: bool = False
    deny_deprecated: bool = False
    target_compiler: str = ""
    # Roadmap 3.5: cross-compilation target triple (empty = host).  Only
    # Linux ⇄ Windows is supported; the target runtime must be provided
    # separately via PENGU_RUNTIME_CROSS (see docs).
    target: str = ""

    def resolve_entry(self) -> str:
        """Resolves main entry file path checking configured paths, src/ directory, and root.

        Returns:
            Absolute file path to the project entry point.
        """
        cands = [
            os.path.abspath(os.path.join(self.base_dir, self.entry)),
            os.path.abspath(os.path.join(self.base_dir, self.src_dir, self.entry)),
            os.path.abspath(os.path.join(self.base_dir, "src", self.entry)),
            os.path.abspath(os.path.join(self.base_dir, self.src_dir, "main.pengu")),
            os.path.abspath(os.path.join(self.base_dir, "src", "main.pengu")),
            os.path.abspath(os.path.join(self.base_dir, "main.pengu")),
        ]
        for cand in cands:
            if os.path.isfile(cand):
                return cand
        return os.path.abspath(os.path.join(self.base_dir, self.entry))

    @classmethod
    def load(cls, path_or_dir: Optional[str] = None, profile: Optional[str] = None) -> ProjectConfig:
        """Discovers and loads project configuration from TOML, YAML, or JSON file.

        Searches in order:
        1. Explicit path if provided.
        2. pengu.toml
        3. pengu.yaml / pengu.yml
        4. pengu.json
        5. Pengu.toml

        If no configuration file is found, returns default configuration.

        Args:
            path_or_dir: Path to configuration file or project root directory.
            profile: Optional active profile override ('debug' or 'release').

        Returns:
            Instantiated and validated ProjectConfig.
        """
        search_dir = os.path.abspath(os.getcwd())
        config_path = None

        if path_or_dir:
            if os.path.isfile(path_or_dir):
                config_path = os.path.abspath(path_or_dir)
                search_dir = os.path.dirname(config_path)
            elif os.path.isdir(path_or_dir):
                search_dir = os.path.abspath(path_or_dir)

        if config_path is None:
            candidates = ["pengu.toml", "pengu.yaml", "pengu.yml", "pengu.json", "Pengu.toml"]
            for cand in candidates:
                p = os.path.join(search_dir, cand)
                if os.path.isfile(p):
                    config_path = p
                    break

        if config_path is None:
            cfg = cls(base_dir=search_dir)
            # No project file (bare checkout, single-file build): the Pengu
            # runtime is still required because pengu_string_copy & friends are
            # compiled into libpengu_runtime.a rather than being header-only.
            if "pengu_runtime" not in cfg.links:
                cfg.links.append("pengu_runtime")
            if profile:
                cfg.profile = profile
            return cfg

        raw_data = cls._parse_file(config_path)
        cfg = cls._from_dict(raw_data, base_dir=search_dir)
        if profile:
            cfg.profile = profile
        return cfg

    @classmethod
    def _parse_file(cls, filepath: str) -> Dict[str, Any]:
        """Parses configuration file using appropriate decoder."""
        ext = os.path.splitext(filepath)[1].lower()
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if ext == ".json":
            return json.loads(content)

        elif ext in (".yaml", ".yml"):
            if _load_yaml_module() is not None:
                return yaml.safe_load(content) or {}
            return cls._fallback_yaml_parse(content)

        elif ext == ".toml":
            if tomllib is not None:
                return tomllib.loads(content)
            return {}

        try:
            return json.loads(content)
        except Exception:
            return cls._fallback_yaml_parse(content)

    @staticmethod
    def _fallback_yaml_parse(text: str) -> Dict[str, Any]:
        """Simple fallback parser for key-value, sections, and list YAML files."""
        result: Dict[str, Any] = {}
        section_stack: List[Tuple[int, Dict[str, Any]]] = [(0, result)]

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))

            while len(section_stack) > 1 and indent <= section_stack[-1][0]:
                section_stack.pop()

            curr_dict = section_stack[-1][1]

            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip()
                if not v:
                    new_sec: Dict[str, Any] = {}
                    curr_dict[k] = new_sec
                    section_stack.append((indent, new_sec))
                else:
                    if v.startswith("[") and v.endswith("]"):
                        items = [i.strip().strip("\"'") for i in v[1:-1].split(",") if i.strip()]
                        curr_dict[k] = items
                    else:
                        curr_dict[k] = v.strip("\"'")

        return result

    @classmethod
    def _from_dict(cls, data: Dict[str, Any], base_dir: str) -> ProjectConfig:
        """Constructs ProjectConfig from parsed dictionary representation."""
        proj_sec = data.get("project", data)
        build_sec = data.get("build", data)
        profiles_sec = data.get("profiles", {})
        deps_sec = data.get("dependencies", proj_sec.get("dependencies", {}))

        name = str(proj_sec.get("name", "pengu_app"))
        version = str(proj_sec.get("version", "0.1.0"))
        entry = str(proj_sec.get("entry", "src/main.pengu"))
        output_str = str(proj_sec.get("output", "exe"))
        output_type = OutputType.from_string(output_str)
        output_name = str(proj_sec.get("output_name", name))
        build_dir = str(build_sec.get("build_dir", "build"))

        src_dir = str(build_sec.get("src_dir", proj_sec.get("src_dir", "src")))
        lib_dir = str(build_sec.get("lib_dir", proj_sec.get("lib_dir", "lib")))
        include_dir = str(build_sec.get("include_dir", proj_sec.get("include_dir", "include")))
        c_dir = str(build_sec.get("c_dir", proj_sec.get("c_dir", "c")))

        dependencies = deps_sec if isinstance(deps_sec, dict) else {}
        includes = list(build_sec.get("includes", []))
        links = list(build_sec.get("links", []))
        lib_dirs = list(build_sec.get("lib_dirs", []))
        include_dirs = list(build_sec.get("include_dirs", []))
        cflags = list(build_sec.get("cflags", ["-O2", "-Wall", "-std=c11"]))
        ldflags = list(build_sec.get("ldflags", []))
        defines = list(build_sec.get("defines", []))
        cc = str(build_sec.get("cc", "gcc"))

        resolved_profiles = {
            "debug": {"cflags": ["-g", "-O0", "-Wall"], "defines": ["DEBUG"]},
            "release": {"cflags": ["-O3", "-flto", "-DNDEBUG"], "defines": ["NDEBUG"]},
        }

        if isinstance(profiles_sec, dict):
            for p_name, p_vals in profiles_sec.items():
                if isinstance(p_vals, dict):
                    resolved_profiles[p_name] = p_vals

        assets_sec = data.get("assets", {}) or {}
        assets_dir = str(assets_sec.get("dir", "assets"))
        assets_module = str(assets_sec.get("module", "arca"))
        assets_embed = bool(assets_sec.get("embed", True))
        assets_exclude = list(assets_sec.get("exclude", []))

        strict_c99 = bool(build_sec.get("strict_c99", proj_sec.get("strict_c99", False)))
        target_compiler = str(build_sec.get("target_compiler", proj_sec.get("target_compiler", "")))
        target = str(build_sec.get("target", proj_sec.get("target", "")))

        return cls(
            name=name,
            version=version,
            entry=entry,
            output=output_type,
            output_name=output_name,
            build_dir=build_dir,
            src_dir=src_dir,
            lib_dir=lib_dir,
            include_dir=include_dir,
            c_dir=c_dir,
            dependencies=dependencies,
            includes=includes,
            links=links,
            lib_dirs=lib_dirs,
            include_dirs=include_dirs,
            cflags=cflags,
            ldflags=ldflags,
            defines=defines,
            cc=cc,
            profiles=resolved_profiles,
            base_dir=base_dir,
            assets_dir=assets_dir,
            assets_module=assets_module,
            assets_embed=assets_embed,
            assets_exclude=assets_exclude,
            strict_c99=strict_c99,
            target_compiler=target_compiler,
            target=target,
        )


class CompileFailedError(RuntimeError):
    """Raised when the C compiler (gcc/clang/...) rejects the generated bundle."""


class EntryPointNotFoundError(RuntimeError):
    """Raised (as a diagnostic) when the project entry file does not exist.

    Carries the same ``message``/``help`` attribute shape as a compiler
    ``PenguError`` so it can flow through the shared diagnostic builders.
    """

    def __init__(self, message: str, help: Optional[str] = None, code: str = "E0000"):
        super().__init__(message)
        self.message = message
        self.help = help
        self.code = code
        self.line = 0
        self.col = 0


class PenguBuilder:
    """Orchestrates parsing, semantic checking, C bundling, runtime copying, and compilation."""

    def __init__(self, config: ProjectConfig, source_code: Optional[str] = None):
        """Initializes builder with project configuration.

        Args:
            config: ProjectConfig instance.
            source_code: Optional in-memory source code override.
        """
        self.config = config
        self.source_code = source_code
        self.is_test_mode = False
        self.release_unsafe: bool = bool(getattr(config, "release_unsafe", False))
        self.deny_deprecated: bool = bool(getattr(config, "deny_deprecated", False))
        self._target_triple: Optional[TargetTriple] = None
        from pengu_parser.pengu_parser import PenguParser as _PenguParser
        from pengu_parser.pengu_comptime import main_flag_requested as _main_flag_requested
        from pengu_parser.pengu_comptime import parse_cli_defines as _parse_cli_defines

        self.parser = _PenguParser()
        self.compile_env = _parse_cli_defines(config.defines)
        explicit_debug = any(str(d).strip() == "debug" or str(d).strip().startswith("debug=") for d in (config.defines or []))
        if not explicit_debug:
            self.compile_env.is_debug = (getattr(config, "profile", "debug") == "debug")
        # Entry-as-main mode: when enabled (pengu run <file> scripts, or an
        # explicit -D main define), only the *entry* module is compiled with
        # the compile-time 'main' flag true; imported modules keep it false.
        self.entry_as_main = bool(_main_flag_requested(config.defines))
        self._entry_abs_cache: Optional[str] = None
        if config.cc:
            from pengu_parser.pengu_comptime import default_compiler_name
            cc_base = os.path.basename(config.cc).lower()
            compiler_name = "msvc" if (cc_base == "cl" or "msvc" in cc_base) else ("clang" if "clang" in cc_base else ("gcc" if ("gcc" in cc_base or "mingw" in cc_base) else (cc_base or default_compiler_name())))
            # An explicit 'compiler=...' entry wins over config.cc.
            explicit = any(str(d).strip().startswith("compiler=") for d in (config.defines or []))
            if not explicit:
                old_compiler = self.compile_env.compiler
                if compiler_name != old_compiler:
                    self.compile_env.compiler = compiler_name
                    self.compile_env.defines.pop(old_compiler, None)
                    self.compile_env.defines[compiler_name] = True
        from pengu_parser.pengu_checker import PenguChecker as _PenguChecker
        self.checker = _PenguChecker(base_dir=config.base_dir, compile_env=self.compile_env,
                                     lib_dir=getattr(config, "lib_dir", "lib"))
        # Verbose mode: print the resolved module order, the exact C commands
        # being executed and phase timings.
        self.verbose = False
        # Script runs ('pengu run x.pengu') trade debug info for startup speed: a
        # build that is cached or thrown away never needs -g, PLT stubs, ident
        # strings or unwind tables.
        self.dev_fast_flags = False
        # Precompiled header of pengu_runtime.h (gcc/clang only, opt-in: on a
        # normal build gcc's own startup plus the link dominates the front end,
        # so the PCH only pays off when the compile is header-bound).
        self.use_pch = False
        # Development builds may use a different compiler than the project's
        # configured one (TCC for 'pengu run').  When that compiler fails, the
        # build is retried once with this one instead of dying: TCC is fast but
        # is not a complete C11 implementation.
        self.fallback_cc: Optional[str] = None
        # Phase timings collected for 'pengu time' / '--verbose'.
        self.timings: Dict[str, float] = {}

    # ------------------------------------------------------- verbose helpers

    def _vlog(self, message: str) -> None:
        """Prints a verbose debug line when verbose mode is enabled."""
        if getattr(self, "verbose", False):
            print(message, file=sys.stderr)

    def get_build_directory(self) -> str:
        """Returns absolute path to the designated build directory."""
        if os.path.isabs(self.config.build_dir):
            return self.config.build_dir
        return os.path.abspath(os.path.join(self.config.base_dir, self.config.build_dir))

    def _is_main_file(self, mod_path: str) -> bool:
        """Returns True when mod_path is the entry module and entry-as-main is on.

        Only the file being executed as the program entry point is compiled with
        the compile-time 'main' variable true; every imported module is compiled
        with 'main' false regardless of the build mode.
        """
        if not getattr(self, "entry_as_main", False):
            return False
        if self._entry_abs_cache is None:
            self._entry_abs_cache = os.path.abspath(self.config.resolve_entry())
        try:
            left = os.path.normcase(os.path.abspath(os.path.normpath(mod_path)))
            right = os.path.normcase(self._entry_abs_cache)
            return left == right
        except Exception:
            return False

    def compute_config_hash(self) -> str:
        """Computes SHA-256 hash of compilation configuration options."""
        key = json.dumps({
            "profile": getattr(self.config, "profile", ""),
            "cflags": sorted(self.config.cflags),
            "ldflags": sorted(self.config.ldflags),
            "defines": sorted(self.config.defines),
            "includes": sorted(self.config.includes),
            "links": sorted(self.config.links),
            "output": str(self.config.output),
            "test_mode": bool(getattr(self, "is_test_mode", False)),
            "entry_main": bool(getattr(self, "entry_as_main", False)),
            "cc": str(getattr(self.config, "cc", "") or ""),
            "include_dirs": sorted(getattr(self.config, "include_dirs", []) or []),
            "lib_dirs": sorted(getattr(self.config, "lib_dirs", []) or []),
            "assets_embed": bool(getattr(self.config, "assets_embed", True)),
            "assets_module": str(getattr(self.config, "assets_module", "arca")),
            "src_dir": str(getattr(self.config, "src_dir", "") or ""),
            "c_dir": str(getattr(self.config, "c_dir", "") or ""),
            "output_name": str(getattr(self.config, "output_name", "") or ""),
            "strict_c99": bool(getattr(self.config, "strict_c99", False)),
            "release_unsafe": bool(getattr(self.config, "release_unsafe", False)),
            "target": str(getattr(self.config, "target", "") or ""),
            "target_compiler": str(getattr(self.config, "target_compiler", "") or ""),
            # Environment-injected flags change the emitted binary, so they must
            # invalidate the cache (a sanitizer build must never reuse a plain one).
            "env_cflags": os.environ.get("PENGU_CFLAGS", "").strip(),
            "env_ldflags": os.environ.get("PENGU_LDFLAGS", "").strip(),
        }, sort_keys=True)
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def compute_sources_fingerprint(self, module_order: List[str]) -> str:
        """Computes a content fingerprint of the entry, its modules and the C glue.

        The build cache must key on content, not on mtimes: `build/bundle.c` and
        `build/app.exe` are shared by every program built in the same directory,
        and comparing mtimes against `bundle.c` let a *different* program's older
        bundle look "up to date" (the stale-binary bug).

        Args:
            module_order: Entry + imported modules in topological order.

        Returns:
            Hex digest covering the resolved entry path, every module's relative
            path and content, the project C sources and the compile options.
        """
        digest = hashlib.sha256()
        digest.update(self.compute_config_hash().encode("utf-8"))
        try:
            entry_abs = os.path.normcase(os.path.abspath(self.config.resolve_entry()))
        except Exception:  # noqa: BLE001 - unresolved entry: fingerprint what we can
            entry_abs = ""
        digest.update(b"\0entry\0" + entry_abs.encode("utf-8"))

        for mod in module_order:
            try:
                rel = os.path.relpath(os.path.abspath(mod), self.config.base_dir)
            except ValueError:
                rel = os.path.abspath(mod)
            digest.update(b"\0module\0" + rel.replace("\\", "/").encode("utf-8") + b"\0")
            digest.update(file_content_digest(mod).encode("ascii"))

        for c_file in sorted(self.collect_c_sources()):
            digest.update(b"\0csrc\0" + os.path.normcase(os.path.abspath(c_file)).encode("utf-8") + b"\0")
            digest.update(file_content_digest(c_file).encode("ascii"))

        # Embedded assets content fingerprint
        assets_dir_rel = getattr(self.config, "assets_dir", None)
        assets_dir = None
        if assets_dir_rel:
            assets_dir = (assets_dir_rel if os.path.isabs(assets_dir_rel)
                          else os.path.join(self.config.base_dir, assets_dir_rel))
        if assets_dir and os.path.isdir(assets_dir):
            digest.update(b"\0assets_embed\0" + (b"1" if getattr(self.config, "assets_embed", True) else b"0"))
            # The .incbin threshold changes the generated asset sources, so it
            # must invalidate the artifact cache too (roadmap 6.0.f).
            try:
                from pengu_assets import _incbin_threshold as _threshold

                digest.update(b"\0assets_incbin\0" + str(_threshold()).encode("ascii"))
            except Exception:  # noqa: BLE001 - optional asset support
                pass
            for root, _, files in os.walk(assets_dir):
                for f in sorted(files):
                    fp = os.path.join(root, f)
                    try:
                        rel = os.path.relpath(fp, self.config.base_dir).replace("\\", "/")
                    except ValueError:
                        rel = fp
                    digest.update(b"\0asset\0" + rel.encode("utf-8") + b"\0")
                    digest.update(file_content_digest(fp).encode("ascii"))

        return digest.hexdigest()

    # ------------------------------------------------------------ cross-compile
    @property
    def target_triple(self) -> Optional[TargetTriple]:
        """Parsed ``--target`` triple, or None when building for the host."""
        if self._target_triple is None:
            raw = str(getattr(self.config, "target", "") or "")
            self._target_triple = parse_target_triple(raw) if raw else TargetTriple("", "", "", "")
        return self._target_triple if self._target_triple.os else None

    @property
    def target_os(self) -> str:
        """Target OS in triple vocabulary (windows/darwin/linux)."""
        triple = self.target_triple
        return triple.os if triple and triple.os else host_os()

    @property
    def is_cross(self) -> bool:
        return self.target_os != host_os()

    def resolve_compiler(self) -> str:
        """Compiler to use, auto-detecting a cross compiler when needed.

        ``--cc`` always wins.  Otherwise, for a Linux ⇄ Windows build the
        conventional ``<triple>-gcc`` / ``x86_64-w64-mingw32-gcc`` names are
        probed, and a clear error is raised when none is installed (instead of
        failing later with a confusing host-compiler link error).
        """
        cc = str(getattr(self.config, "cc", "") or "")
        if not self.is_cross:
            return cc
        triple = self.target_triple
        if triple and triple.raw and cc not in ("", "gcc"):
            return cc
        candidates: List[str] = []
        if triple and triple.raw:
            candidates.append(f"{triple.raw}-gcc")
        if self.target_os == "windows":
            if triple and triple.arch in ("i686", "i386", "x86"):
                candidates.append("i686-w64-mingw32-gcc")
            candidates.append("x86_64-w64-mingw32-gcc")
            candidates.append("mingw32-gcc")
        for cand in candidates:
            if shutil.which(cand):
                return cand
        raise CompileFailedError(
            f"no cross compiler found for target '{getattr(self.config, 'target', '')}'.\n"
            f"Install one (e.g. 'apt install mingw-w64') or pass --cc <compiler>.\n"
            f"Cross-compilation also needs a runtime built for the target; point "
            f"PENGU_RUNTIME_CROSS at its directory."
        )

    def cross_runtime_flags(self) -> List[str]:
        """``-L``/``-I`` flags for a cross-compiled runtime (PENGU_RUNTIME_CROSS)."""
        root = os.environ.get("PENGU_RUNTIME_CROSS", "").strip()
        if not root or not self.is_cross:
            return []
        flags: List[str] = []
        if os.path.isdir(os.path.join(root, "lib")):
            flags.append(f"-L{os.path.join(root, 'lib')}")
        else:
            flags.append(f"-L{root}")
        if os.path.isdir(os.path.join(root, "include")):
            flags.append(f"-I{os.path.join(root, 'include')}")
        return flags

    def get_output_artifact_name(self) -> str:
        """Determines target output filename according to platform and OutputType.

        Returns:
            Resolved filename string.
        """
        out_name = self.config.output_name
        out_type = self.config.output
        target_os = self.target_os
        is_win = target_os == "windows"
        is_mac = target_os == "darwin"

        if out_type == OutputType.C:
            return "bundle.c"
        elif out_type == OutputType.OBJ:
            return f"{out_name}.o"
        elif out_type == OutputType.STATIC:
            return f"{out_name}.a" if not is_win else f"{out_name}.lib"
        elif out_type == OutputType.SHARED:
            if is_win:
                return f"{out_name}.dll"
            elif is_mac:
                return f"lib{out_name}.dylib"
            else:
                return f"lib{out_name}.so"
        else:  # EXE
            return f"{out_name}.exe" if is_win else out_name

    def locate_and_copy_runtime(self, dest_dir: str) -> str:
        """Locates pengu_runtime.h and copies it to destination directory if needed.

        Search is delegated to ``pengu_paths`` so that FHS installs
        (``$PREFIX/include/pengu``), portable bundles (``<exe_dir>/runtime``),
        source checkouts (``build/include``) and PyInstaller ``_MEIPASS``
        payloads are all handled uniformly.
        """
        # The project root may ship its own pengu_runtime.h (vendored runtime);
        # honour it first, then fall back to the toolchain-wide search.
        project_local = os.path.join(self.config.base_dir, "pengu_runtime.h")
        found_src: Optional[str] = None
        if os.path.isfile(project_local):
            found_src = os.path.abspath(project_local)
        else:
            found = find_runtime_header()
            if found is not None:
                found_src = str(found)

        if not found_src:
            raise FileNotFoundError(
                "Cannot locate 'pengu_runtime.h'. Run 'python build_runtime.py', "
                "install the PenguScript runtime (e.g. via install.sh), or set "
                "PENGU_INCLUDE_DIR / PENGU_RUNTIME_HEADER to override the search path."
            )


        dest_file = os.path.join(dest_dir, "pengu_runtime.h")
        if os.path.abspath(found_src) != os.path.abspath(dest_file):
            # Windows (Defender / AV) can briefly lock a freshly written header
            # when many tests share the build dir; retry instead of failing.
            last_err: Optional[Exception] = None
            for _attempt in range(6):
                try:
                    shutil.copy(found_src, dest_file)
                    last_err = None
                    break
                except OSError as e:  # permission / sharing violations
                    last_err = e
                    time.sleep(0.15)
            if last_err is not None:
                raise last_err

        return dest_file

    def generate_assets(self, force: bool = False) -> Optional[dict]:
        """Generates src/<module>.pengu and build/<module>_assets.c.

        Returns dict from `pengu_assets.generate()` or None if assets dir does not exist.
        """
        assets_dir_rel = getattr(self.config, "assets_dir", None)
        if not assets_dir_rel:
            return None
        from pathlib import Path
        from pengu_assets import AssetConfig, generate

        src_dir = os.path.abspath(os.path.join(self.config.base_dir, self.config.src_dir))
        build_dir = self.get_build_directory()
        assets_dir = (assets_dir_rel if os.path.isabs(assets_dir_rel)
                      else os.path.abspath(os.path.join(self.config.base_dir, assets_dir_rel)))
        if not os.path.isdir(assets_dir):
            return None
        cfg = AssetConfig(
            project_root=Path(self.config.base_dir),
            src_dir=Path(src_dir),
            build_dir=Path(build_dir),
            assets_dir=Path(assets_dir),
            module=getattr(self.config, "assets_module", "arca"),
            embed=getattr(self.config, "assets_embed", True),
            exclude=getattr(self.config, "assets_exclude", []),
        )
        return generate(cfg, force=force)

    def collect_c_sources(self) -> List[str]:
        """Collects all C glue/source files from project c_dir and all lib/*/c/ directories.

        Returns:
            Sorted, deduplicated list of absolute .c file paths.
        """
        c_files: List[str] = []

        # 1. Project C sources (from config.c_dir and c/)
        cand_c_dirs = [
            os.path.abspath(os.path.join(self.config.base_dir, self.config.c_dir)),
            os.path.abspath(os.path.join(self.config.base_dir, "c")),
        ]
        for c_dir in set(cand_c_dirs):
            if os.path.isdir(c_dir):
                for root, _, files in os.walk(c_dir):
                    for f in files:
                        if f.endswith(".c"):
                            c_files.append(os.path.abspath(os.path.join(root, f)))

        # 2. Binding C sources (lib/*/c/)
        lib_root = os.path.abspath(os.path.join(self.config.base_dir, self.config.lib_dir))
        if os.path.isdir(lib_root):
            try:
                for entry in os.scandir(lib_root):
                    if entry.is_dir():
                        binding_c = os.path.join(entry.path, "c")
                        if os.path.isdir(binding_c):
                            for root, _, files in os.walk(binding_c):
                                for f in files:
                                    if f.endswith(".c"):
                                        c_files.append(os.path.abspath(os.path.join(root, f)))
            except Exception:
                pass

        # 3. Generated embedded assets C source (build/<module>_assets.c)
        if getattr(self.config, "assets_module", None):
            gen_c = os.path.join(self.get_build_directory(), f"{self.config.assets_module}_assets.c")
            if os.path.isfile(gen_c):
                abs_gen_c = os.path.abspath(gen_c)
                if abs_gen_c not in c_files:
                    c_files.append(abs_gen_c)

        return sorted(list(set(c_files)))

    def collect_include_dirs(self) -> List[str]:
        """Collects C header include directories from project include_dir and lib/*/include/.

        Returns:
            Deduplicated list of absolute directory paths.
        """
        dirs: List[str] = []

        # 1. Project include dir
        cand_inc = [
            os.path.abspath(os.path.join(self.config.base_dir, self.config.include_dir)),
            os.path.abspath(os.path.join(self.config.base_dir, "include")),
        ]
        for inc in set(cand_inc):
            if os.path.isdir(inc) and inc not in dirs:
                dirs.append(inc)

        # 2. Binding include dirs (lib/*/include/ and lib/*/)
        lib_root = os.path.abspath(os.path.join(self.config.base_dir, self.config.lib_dir))
        if os.path.isdir(lib_root):
            try:
                for entry in os.scandir(lib_root):
                    if entry.is_dir():
                        b_inc = os.path.join(entry.path, "include")
                        if os.path.isdir(b_inc):
                            abs_b_inc = os.path.abspath(b_inc)
                            if abs_b_inc not in dirs:
                                dirs.append(abs_b_inc)
                        # Check if binding directory directly contains headers
                        has_headers = any(f.endswith(".h") for f in os.listdir(entry.path) if os.path.isfile(os.path.join(entry.path, f)))
                        if has_headers:
                            abs_entry = os.path.abspath(entry.path)
                            if abs_entry not in dirs:
                                dirs.append(abs_entry)
            except Exception:
                pass

        # 3. Configured include dirs
        for inc in self.config.include_dirs:
            abs_inc = os.path.abspath(os.path.join(self.config.base_dir, inc)) if not os.path.isabs(inc) else inc
            if os.path.isdir(abs_inc) and abs_inc not in dirs:
                dirs.append(abs_inc)

        # 4. Toolchain runtime include dirs (source checkout, portable bundle,
        #    FHS install, PyInstaller _MEIPASS).  Also covers <project>/runtime
        #    when the user vendored the runtime into the project tree.
        for extra_dir in (self.config.base_dir,):
            for sub in ("build/include", "runtime/include", "runtime"):
                p = os.path.join(extra_dir, sub)
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        for extra in runtime_include_dirs():
            s = str(extra)
            if os.path.isdir(s) and s not in dirs:
                dirs.append(s)

        return dirs

    def collect_lib_dirs_and_links(self) -> Tuple[List[str], List[str]]:
        """Collects library search paths (-L) and automatically detected library names (-l) from lib/ and lib/*/lib/.

        Returns:
            Tuple of (lib_directories_list, auto_detected_library_names_list).
        """
        lib_dirs: List[str] = []
        auto_links: List[str] = []

        # 1. Project lib dir
        cand_lib = [
            os.path.abspath(os.path.join(self.config.base_dir, self.config.lib_dir)),
            os.path.abspath(os.path.join(self.config.base_dir, "lib")),
        ]
        for ld in set(cand_lib):
            if os.path.isdir(ld) and ld not in lib_dirs:
                lib_dirs.append(ld)

        # 2. Binding lib dirs (lib/*/lib/ and lib/*/)
        lib_root = os.path.abspath(os.path.join(self.config.base_dir, self.config.lib_dir))
        if os.path.isdir(lib_root):
            try:
                for entry in os.scandir(lib_root):
                    if entry.is_dir():
                        b_lib = os.path.join(entry.path, "lib")
                        if os.path.isdir(b_lib):
                            abs_b_lib = os.path.abspath(b_lib)
                            if abs_b_lib not in lib_dirs:
                                lib_dirs.append(abs_b_lib)
                        has_libs = any(extract_lib_name(f) is not None for f in os.listdir(entry.path) if os.path.isfile(os.path.join(entry.path, f)))
                        if has_libs:
                            abs_entry = os.path.abspath(entry.path)
                            if abs_entry not in lib_dirs:
                                lib_dirs.append(abs_entry)
            except Exception:
                pass

        # 3. Configured lib dirs
        for ld in self.config.lib_dirs:
            abs_ld = os.path.abspath(os.path.join(self.config.base_dir, ld)) if not os.path.isabs(ld) else ld
            if os.path.isdir(abs_ld) and abs_ld not in lib_dirs:
                lib_dirs.append(abs_ld)

        # 4. Automatically detect libraries to link in project and binding lib_dirs only
        # (toolchain runtime libraries must be linked explicitly via `link "..."` or config.links)
        for ld in list(lib_dirs):
            if os.path.isdir(ld):
                try:
                    for fname in os.listdir(ld):
                        fpath = os.path.join(ld, fname)
                        if os.path.isfile(fpath):
                            lname = extract_lib_name(fname)
                            if lname and lname not in auto_links:
                                auto_links.append(lname)
                except Exception:
                    pass

        # 5. Toolchain runtime lib dirs (source checkout, portable bundle,
        #    FHS install, PyInstaller _MEIPASS), plus a project-local runtime/
        #    vendored next to the project. These provide search paths (-L) so
        #    explicit links (e.g. -lpengu_runtime, -lraylib) resolve.
        for sub in ("build/lib", "runtime/lib", "runtime"):
            p = os.path.join(self.config.base_dir, sub)
            if os.path.isdir(p) and p not in lib_dirs:
                lib_dirs.append(p)
        for extra in runtime_lib_dirs():
            s = str(extra)
            if os.path.isdir(s) and s not in lib_dirs:
                lib_dirs.append(s)

        return lib_dirs, auto_links

    def is_bundle_up_to_date(self, bundle_path: str, module_order: List[str]) -> bool:
        """Checks if bundle.c is newer than all source modules, C glue files, headers, and config.

        Args:
            bundle_path: Path to bundle.c.
            module_order: List of source module file paths.

        Returns:
            True if bundle.c is newer than all sources and config hash matches, False otherwise.
        """
        if not os.path.isfile(bundle_path):
            return False

        hash_file = os.path.join(os.path.dirname(bundle_path), ".bundle_hash")
        if not os.path.isfile(hash_file):
            return False
        try:
            with open(hash_file, "r", encoding="utf-8") as f:
                saved = f.read().strip()
        except Exception:
            return False

        # The cache key is "<config hash> <sources fingerprint>". A single-token
        # file is the old format (config hash only), which cannot prove that this
        # bundle belongs to this program: treat it as stale.
        parts = saved.split()
        if len(parts) != 2:
            return False
        saved_config, saved_fingerprint = parts
        if saved_config != self.compute_config_hash():
            return False
        if saved_fingerprint != self.compute_sources_fingerprint(module_order):
            return False

        # Headers (include dirs), C glue and the runtime header are still tracked
        # by mtime: content-hashing every header of every include directory would
        # cost more than the rebuild it avoids.
        bundle_mtime = os.path.getmtime(bundle_path)

        c_files = self.collect_c_sources()
        for cf in c_files:
            if os.path.isfile(cf) and os.path.getmtime(cf) > bundle_mtime:
                return False

        inc_dirs = self.collect_include_dirs()
        for inc_d in inc_dirs:
            if os.path.isdir(inc_d):
                try:
                    for root, _, files in os.walk(inc_d):
                        for f in files:
                            if f.endswith(".h"):
                                hp = os.path.join(root, f)
                                if os.path.getmtime(hp) > bundle_mtime:
                                    return False
                except Exception:
                    pass

        config_files = ["pengu.toml", "pengu.yaml", "pengu.yml", "pengu.json", "Pengu.toml"]
        for cf in config_files:
            cfp = os.path.join(self.config.base_dir, cf)
            if os.path.isfile(cfp) and os.path.getmtime(cfp) > bundle_mtime:
                return False

        runtime_candidates = [
            os.path.join(self.config.base_dir, "pengu_parser", "pengu_runtime.h"),
            os.path.join(self.config.base_dir, "pengu_runtime.h"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "pengu_parser", "pengu_runtime.h"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "pengu_runtime.h"),
        ]
        for rp in runtime_candidates:
            if os.path.isfile(rp) and os.path.getmtime(rp) > bundle_mtime:
                return False

        return True

    def bundle(self, output_file: Optional[str] = None) -> Tuple[str, bool]:
        """Generates single monolithic bundle.c in build directory from modules in topological order.

        Args:
            output_file: Optional output file path override for bundle.c.

        Returns:
            Tuple of (bundle_file_path, is_cached_boolean).
        """
        build_dir = self.get_build_directory()
        os.makedirs(build_dir, exist_ok=True)

        # Regenerate embedded assets if configured
        self.generate_assets()

        bundle_path = output_file or os.path.join(build_dir, "bundle.c")
        entry_abs = self.config.resolve_entry()

        # 1. Resolve module order
        module_order: List[str] = []
        if os.path.isfile(entry_abs):
            from pengu_parser.pengu_symbols import resolve_imports as _resolve_imports
            module_order = _resolve_imports(self.config.base_dir, entry_abs, self.parser,
                                            lib_dir=getattr(self.config, "lib_dir", "lib"))
        elif self.source_code is not None:
            module_order = [entry_abs]
        else:
            module_order = [entry_abs]

        if self.verbose:
            self._vlog(f"[pengu] entry: {entry_abs}")
            self._vlog(f"[pengu] module order ({len(module_order)}):")
            for mo in module_order:
                self._vlog(f"[pengu]   - {mo}")
            self._vlog(f"[pengu] build dir: {build_dir}")
            self._vlog(f"[pengu] output: {self.config.output} profile: {self.config.profile}")
            self._vlog(f"[pengu] defines: {sorted(self.config.defines or [])}")

        t_check = time.time()

        # 2. Check if cached bundle.c is up-to-date
        if self.source_code is None and self.is_bundle_up_to_date(bundle_path, module_order):
            self.locate_and_copy_runtime(build_dir)
            return bundle_path, True

        # 3. Check all source files with PenguChecker and collect parsed trees
        parsed_trees: List[Tuple[str, Tree]] = []
        for i, mod_path in enumerate(module_order):
            # 'main' is a per-module compile-time variable: only the entry module
            # sees main=true (when entry-as-main mode is on); imports see false.
            self.compile_env.is_main = self._is_main_file(mod_path)
            if os.path.isfile(mod_path):
                with open(mod_path, "r", encoding="utf-8") as f:
                    code = f.read()
            elif self.source_code is not None:
                code = self.source_code
            else:
                code = ""
            if code:
                tree = self.parser.parse(code)
                self.checker.check(tree, source=code, filename=mod_path, reset_symbols=(i == 0), import_order=module_order)
                parsed_trees.append((mod_path, tree))

        self.timings["check"] = time.time() - t_check
        if self.verbose:
            self._vlog(f"[pengu] semantic check finished in {time.time() - t_check:.3f}s")
        t_codegen = time.time()

        # 4. Copy runtime header to build directory
        self.locate_and_copy_runtime(build_dir)

        # 5. Generate bundle.c via PenguCodegen
        from pengu_parser.pengu_codegen import PenguCodegen, set_release_unsafe
        codegen = PenguCodegen(self.checker.symbols, module_order, self.config.base_dir,
                               compile_env=self.compile_env,
                               use_gnu_extensions=not getattr(self.config, "strict_c99", False),
                               target_compiler=getattr(self.config, "target_compiler", ""))
        codegen.entry_main_mode = bool(getattr(self, "entry_as_main", False))
        codegen.entry_file = os.path.abspath(self.config.resolve_entry())
        codegen.collect_declarations(parsed_trees)
        is_lib = self.config.output in (OutputType.STATIC, OutputType.SHARED, OutputType.OBJ)
        codegen.generate_bundle(
            custom_includes=self.config.includes,
            is_library=is_lib,
            output_path=bundle_path,
            is_test=self.is_test_mode
        )

        self.timings["codegen"] = time.time() - t_codegen
        if self.verbose:
            self._vlog(f"[pengu] codegen finished in {time.time() - t_codegen:.3f}s")
            self._vlog(f"[pengu] bundle written: {bundle_path}")
        try:
            self.timings["bundle_bytes"] = os.path.getsize(bundle_path)
            with open(bundle_path, "r", encoding="utf-8", errors="replace") as fh:
                self.timings["bundle_lines"] = sum(1 for _ in fh)
        except OSError:
            pass

        # Dead-code elimination metrics (the pass runs inside generate_bundle,
        # before a single section is emitted).  Without DCE this bundle is the
        # "before" size, so report both the weave counts and the final C size.
        dce_stats = getattr(codegen, "dce_stats", None) or {}
        if dce_stats.get("dropped"):
            self.timings["dce"] = dce_stats.get("seconds", 0.0)
            self.timings["dce_dropped"] = dce_stats["dropped"]
            self.timings["dce_before"] = dce_stats["before"]
            self.timings["dce_after"] = dce_stats["after"]
            if self.verbose:
                self._vlog(f"[pengu] {dce_stats.get('message', 'DCE applied')} "
                           f"in {self.timings['dce'] * 1000:.1f}ms")
                if "bundle_lines" in self.timings:
                    self._vlog(f"[pengu] DCE: bundle.c is now "
                               f"{self.timings['bundle_lines']} lines "
                               f"({self.timings.get('bundle_bytes', 0) / 1024:.1f} KB)")

        # 6. Save the compilation cache key: config hash + content fingerprint
        hash_file = os.path.join(os.path.dirname(bundle_path), ".bundle_hash")
        try:
            with open(hash_file, "w", encoding="utf-8") as f:
                f.write(f"{self.compute_config_hash()} {self.compute_sources_fingerprint(module_order)}")
        except Exception:
            pass

        return bundle_path, False

    def check_sources_diagnostics(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Like :meth:`check_sources` but returns structured diagnostics.

        Each diagnostic is a dict with ``file``, ``line``, ``col``, ``code``,
        ``severity``, ``message``, ``help`` and ``note`` keys, suitable for
        ``pengu check --json``.
        """
        cached = getattr(self, "_diagnostics_cache", None)
        if cached is not None:
            return cached[0], [dict(d) for d in cached[1]]

        self.generate_assets()
        entry_abs = self.config.resolve_entry()

        def _diag(exc: Any, fpath: str) -> Dict[str, Any]:
            line = getattr(exc, "line", None) or 0
            col = getattr(exc, "column", None)
            if col is None:
                col = getattr(exc, "col", None) or 0
            return {
                "file": fpath,
                "line": int(line),
                "col": int(col),
                "code": getattr(exc, "code", None) or "",
                "severity": "error",
                "message": getattr(exc, "message", None) or str(exc),
                "help": getattr(exc, "help", None),
                "note": getattr(exc, "note", None),
            }

        if os.path.isfile(entry_abs):
            try:
                from pengu_parser.pengu_symbols import resolve_imports as _resolve_imports
                module_order = _resolve_imports(self.config.base_dir, entry_abs, self.parser,
                                            lib_dir=getattr(self.config, "lib_dir", "lib"))
            except Exception as e:  # noqa: BLE001 - parse/import failure in the entry graph
                return False, [_diag(e, entry_abs)]
        else:
            # A missing entry point is an error, not an empty module list.
            # Returning ok=True here is what made `pengu check` print "Clean"
            # in any directory without src/main.pengu (blocker B2).
            exc = EntryPointNotFoundError(
                f"entry point not found: {entry_abs}",
                help=f"Create '{os.path.relpath(entry_abs, self.config.base_dir)}', "
                     "or pass --entry <path> to point at a different file.",
            )
            return False, [_diag(exc, entry_abs)]

        def _warning_diag(text: str, fpath: str) -> Dict[str, Any]:
            """Turns a checker warning string into a structured diagnostic."""
            import re as _re
            m = _re.match(r"\[(W\d{4})\]\s*(.*?)(?:\s+on line\s+(\d+))?$", text)
            code = m.group(1) if m else "W0000"
            message = m.group(2) if m else text
            line = int(m.group(3)) if (m and m.group(3)) else 0
            severity = "warning"
            note = None
            if self.deny_deprecated and code == "W0006":
                severity = "error"
                note = "promoted to an error by --deny-deprecated"
            return {
                "file": fpath,
                "line": line,
                "col": 0,
                "code": code,
                "severity": severity,
                "message": message,
                "help": None,
                "note": note,
            }

        ok = True
        diagnostics: List[Dict[str, Any]] = []
        for i, mod_path in enumerate(module_order):
            self.compile_env.is_main = self._is_main_file(mod_path)
            try:
                if os.path.isfile(mod_path):
                    with open(mod_path, "r", encoding="utf-8") as f:
                        code = f.read()
                elif self.source_code is not None:
                    code = self.source_code
                else:
                    code = ""
                if not code:
                    continue
                tree = self.parser.parse(code)
                _warn_before = len(getattr(self.checker, "warnings", []) or [])
                self.checker.check(tree, source=code, filename=mod_path, reset_symbols=(i == 0), import_order=module_order)
                # Warnings were computed but never surfaced (roadmap 5.4): turn
                # them into diagnostics so `pengu check` reports them and
                # --deny-deprecated can fail a build on W0006.
                for _w in (getattr(self.checker, "warnings", []) or [])[_warn_before:]:
                    diag = _warning_diag(str(_w), mod_path)
                    diagnostics.append(diag)
                    if diag["severity"] == "error":
                        ok = False
                if self.verbose:
                    self._vlog(f"[pengu] ok: {mod_path}")
            except Exception as e:  # noqa: BLE001 - any parse/semantic failure
                ok = False
                sub_list = getattr(e, "all_errors", None) or [e]
                for sub in sub_list:
                    diagnostics.append(_diag(sub, mod_path))
        self._diagnostics_cache = (ok, [dict(d) for d in diagnostics])
        return ok, diagnostics

    def check_sources(self) -> Tuple[bool, List[str]]:
        """Parses and semantically checks every module without generating code.

        Entry-as-main semantics are respected (the entry module compiles with
        the compile-time 'main' variable true when entry_as_main is enabled).

        Returns:
            Tuple of (ok, messages) where each message is a human readable
            problem line ("file:line:col [CODE] message").
        """
        ok, diagnostics = self.check_sources_diagnostics()
        messages: List[str] = []
        for d in diagnostics:
            code_str = f"[{d['code']}] " if d.get("code") else ""
            messages.append(f"{d['file']}:{d['line']}:{d['col']} {code_str}{d['message']}")
        return ok, messages

    def build_compile_commands(self, bundle_path: str, output_path: str) -> List[List[str]]:
        """Assembles list of shell commands required to compile bundle and C glue into target artifact.

        Merges base compiler flags with active profile flags (debug / release),
        includes project and binding headers, links project and binding libraries,
        and adds project and binding C glue files.

        Args:
            bundle_path: Path to generated bundle.c.
            output_path: Path to target output artifact.

        Returns:
            List of command argument lists to execute sequentially.
        """
        cc = self.resolve_compiler()
        out_type = self.config.output
        is_win = self.target_os == "windows"
        is_mac = self.target_os == "darwin"
        commands: List[List[str]] = []

        # Merge base flags with profile flags
        active_prof = self.config.profiles.get(self.config.profile, {})
        prof_cflags = list(active_prof.get("cflags", []))
        prof_defines = list(active_prof.get("defines", []))

        merged_cflags: List[str] = []
        for cf in self.config.cflags:
            merged_cflags.append(cf)
        for cf in prof_cflags:
            if cf not in merged_cflags:
                merged_cflags.append(cf)

        merged_defines: List[str] = []
        for d in self.config.defines:
            merged_defines.append(f"-D{d}")
        for d in prof_defines:
            flag = f"-D{d}"
            if flag not in merged_defines:
                merged_defines.append(flag)

        common_flags: List[str] = merged_cflags + merged_defines

        # Cross-compilation: the target runtime lives outside the host prefix.
        for _flag in self.cross_runtime_flags():
            if _flag not in common_flags:
                common_flags.append(_flag)

        # Extra flags from the environment (CFLAGS/LDFLAGS convention).  Used by
        # CI for -fsanitize=... runs without touching the project manifest.
        _env_cflags = _env_flag_list("PENGU_CFLAGS")
        for _flag in _env_cflags:
            if _flag not in common_flags:
                common_flags.append(_flag)

        # Safety checks are decoupled from the profile (roadmap 5.2): they are ON
        # in every profile and only `--release-unsafe` removes them, both from the
        # generated code (set_release_unsafe) and from the runtime helpers.
        _set_release_unsafe(self.release_unsafe)
        if self.release_unsafe:
            for flag in ("-DPENGU_BOUNDS_CHECK=0", "-DPENGU_OVERFLOW_CHECK=0"):
                if flag not in common_flags:
                    common_flags.append(flag)
        else:
            # Integer overflow policy (roadmap 5.1).  C leaves signed overflow as
            # undefined behaviour, which lets -O2 rewrite arithmetic in ways that
            # break the wrapping users expect.  Debug traps, release wraps:
            #   debug    -> -ftrapv  (SIGABRT on signed overflow)
            #   release  -> -fwrapv  (two's-complement wrapping, no UB)
            # TCC and MSVC have no -ftrapv; MSVC's signed arithmetic wraps in
            # practice, so release needs no flag there either.
            _cc_l = os.path.basename(cc).lower()
            if "tcc" not in _cc_l and _cc_l not in ("cl", "cl.exe"):
                _ovf = "-ftrapv" if self.config.profile == "debug" else "-fwrapv"
                if _ovf not in common_flags and _ovf not in merged_cflags:
                    common_flags.append(_ovf)

        cc_base = os.path.basename(cc).lower()
        is_tcc = "tcc" in cc_base
        is_msvc = cc_base in ("cl", "cl.exe") or "msvc" in cc_base

        if is_msvc:
            # MSVC (cl.exe) does not understand the GNU flags of the default
            # profiles; map them and force a C dialect with designated
            # initializers / compound literals (roadmap 2.2.f).
            remap = {
                "-O0": "/Od", "-O1": "/O1", "-O2": "/O2", "-O3": "/O2",
                "-g": "/Zi", "-Wall": "/W3", "-Wextra": "/W4",
                "-std=c11": "/std:c11", "-std=c99": "/std:c11",
            }
            new_flags: List[str] = []
            for f in common_flags:
                if f in remap:
                    new_flags.append(remap[f])
                elif f.startswith("-D"):
                    new_flags.append("/D" + f[2:])
                elif f.startswith("-I"):
                    new_flags.append("/I" + f[2:])
                elif f.startswith("-flto") or f in (
                        "-fno-plt", "-pipe", "-fno-ident", "-g0", "-O0",
                        "-fno-asynchronous-unwind-tables"):
                    continue
                else:
                    new_flags.append(f)
            if "/std:c11" not in new_flags:
                new_flags.append("/std:c11")
            common_flags = new_flags

        # Development runs do not need debug info or PLT/unwind metadata: the
        # binary is cached or discarded, never debugged.  TCC rejects unknown
        # options, so it only gets '-O0'.
        if self.dev_fast_flags and not is_msvc:
            if is_tcc:
                if "-O0" not in merged_cflags:
                    common_flags.append("-O0")
            else:
                for flag in ("-g0", "-fno-plt", "-pipe", "-fno-ident",
                             "-fno-asynchronous-unwind-tables"):
                    if flag not in common_flags:
                        common_flags.append(flag)
                # Drop the debug-info flags of the profile: '-g0' already wins on
                # gcc, but removing '-g' keeps the command line (and the PCH
                # signature) clean.
                common_flags = [f for f in common_flags if f != "-g"]

        build_dir = self.get_build_directory()

        # A precompiled header of pengu_runtime.h saves the front-end work of
        # parsing the (large) runtime on every compile.  It must be generated
        # with the same -I/-D/-std set the build uses, otherwise gcc silently
        # ignores it.
        if self.use_pch and not is_tcc and not is_msvc:
            prebuilt = self._runtime_pch_exists()
            if prebuilt:
                # build_runtime.py (and the release archive) ship a shared
                # pengu_runtime.h.gch next to the header: reuse it instead of
                # paying ~115 ms to regenerate a throw-away one per build.  If
                # our -D/-I differ gcc ignores it silently (documented
                # limitation, not an error).
                if f"-I{prebuilt}" not in common_flags:
                    common_flags.insert(0, f"-I{prebuilt}")
                if self.verbose:
                    self._vlog(f"[pengu] reusing shared runtime PCH in {prebuilt}")
            else:
                pch_dir = self._ensure_runtime_pch(build_dir, common_flags, cc)
                if pch_dir:
                    common_flags.insert(0, f"-I{pch_dir}")

        # Ensure build_dir is included in include search path for pengu_runtime.h
        common_flags.append(f"-I{build_dir}")

        # POSIX: the runtime is linked against the system libxml2 / libcurl /
        # libmicrohttpd (build_runtime.py skips the Windows-tuned static
        # builds there), so we must ask pkg-config where their headers live.
        # Plain clang on macOS does not search the Homebrew prefix by
        # default, so we also add it explicitly.
        if not is_win:
            for pkg in ("libxml-2.0", "libcurl", "libmicrohttpd", "mbedtls"):
                for tok in pkg_config_cflags(pkg):
                    if tok not in common_flags:
                        common_flags.append(tok)
            for brew_inc in ("/opt/homebrew/include", "/usr/local/include"):
                flag = f"-I{brew_inc}"
                if os.path.isdir(brew_inc) and flag not in common_flags:
                    common_flags.append(flag)

        # Include directories (-I)
        include_dirs = self.collect_include_dirs()
        for inc in include_dirs:
            inc_flag = f"-I{inc}"
            if inc_flag not in common_flags:
                common_flags.append(inc_flag)

        # Library search directories (-L) & detected auto links
        lib_dirs, auto_links = self.collect_lib_dirs_and_links()
        for ldir in lib_dirs:
            ldir_flag = f"-L{ldir}"
            if ldir_flag not in common_flags:
                common_flags.append(ldir_flag)

        if not is_win:
            for brew_lib in ("/opt/homebrew/lib", "/usr/local/lib"):
                ldir_flag = f"-L{brew_lib}"
                if os.path.isdir(brew_lib) and ldir_flag not in common_flags:
                    common_flags.append(ldir_flag)
            for pkg in ("libxml-2.0", "libcurl", "libmicrohttpd", "mbedtls"):
                for tok in pkg_config_libs(pkg):
                    if tok.startswith("-L") and tok not in common_flags:
                        common_flags.append(tok)

        # Collect C glue/support files
        c_sources = self.collect_c_sources()

        # Merge links: config.links + checker.symbols.links + auto_links
        all_links: List[str] = []
        for link in self.config.links:
            if link not in all_links:
                all_links.append(link)
        if hasattr(self.checker, "symbols") and self.checker.symbols:
            for link in self.checker.symbols.links:
                if link not in all_links:
                    all_links.append(link)
        for link in auto_links:
            if link not in all_links:
                all_links.append(link)
        # Item 4.17: every build links the runtime archive. `pengu_string_copy`
        # and friends live in libpengu_runtime.a, not in the header, and each
        # bundle carries a reference to `pengu_abi_version` so a stale archive
        # fails at link time. This is a build policy, not a parsing rule, so it
        # is applied here and not in ProjectConfig.load().
        if "pengu_runtime" not in all_links:
            all_links.append("pengu_runtime")

        link_flags: List[str] = []
        for link in all_links:
            if link in ("pengu_runtime", "libpengu_runtime"):
                link_flags.extend([
                    "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl",
                    "-lmbedcrypto", "-lmicrohttpd", "-lz"
                ])
                if is_win:
                    link_flags.extend([
                        "-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt",
                        # windowing / UI platform libraries (raylib, webui, ...)
                        "-lopengl32", "-lgdi32", "-lole32", "-luuid", "-lshell32",
                        # libuv platform libraries (psapi/userenv/iphlpapi)
                        "-lpsapi", "-luserenv", "-liphlpapi",
                    ])
                else:
                    for pkg in ("libxml-2.0", "libcurl", "libmicrohttpd", "mbedtls"):
                        for tok in pkg_config_libs(pkg):
                            if tok.startswith("-l") and tok not in link_flags:
                                link_flags.append(tok)
            else:
                link_flags.append(f"-l{link}")

        if not is_win and all_links:
            # Platform tail: provider libraries must come AFTER every archive
            # (single-pass linkers resolve only later libraries). Math for the
            # stb/sqlite/xlsxio objects, OpenSSL for libzip's crypto backend on
            # Linux, and CoreFoundation for std.uuid on macOS. Only emitted
            # when the project actually links libraries (all_links non-empty).
            if sys.platform.startswith("linux"):
                link_flags += ["-lrt", "-lcrypto", "-lssl"]
            elif sys.platform.startswith("darwin"):
                link_flags += ["-framework", "CoreFoundation"]
            link_flags += ["-pthread", "-lm", "-ldl"]

        # GNU ld: wrap static archives in a group so inter-archive dependencies
        # resolve regardless of -l order (libzip needs zlib's crc32/zError, the
        # xlsxio/zip/yaml stack has several such edges). MSVC's link.exe has no
        # --start-group, Apple's ld64 rejects it outright, and TCC's built-in
        # linker driver answers "unsupported linker option '--start-group'", so
        # the group is applied only where it is actually understood.
        use_gnu_group = (
            (not is_win or "cl" not in cc.lower() and "msvc" not in cc.lower())
            and not is_tcc
        )
        if sys.platform.startswith("darwin"):
            use_gnu_group = False
        if use_gnu_group and link_flags:
            link_flags = ["-Wl,--start-group"] + link_flags + ["-Wl,--end-group"]

        # xlsxio headers are DLL_EXPORT-only on _WIN32 unless STATIC is defined.
        if any(l in ("xlsxio_read", "xlsxio_write") for l in all_links):
            if "-DSTATIC" not in common_flags:
                common_flags.append("-DSTATIC")

        for ldflag in self.config.ldflags:
            link_flags.append(ldflag)

        for _flag in _env_flag_list("PENGU_LDFLAGS"):
            if _flag not in link_flags:
                link_flags.append(_flag)

        if out_type == OutputType.C:
            return []

        elif out_type == OutputType.OBJ:
            if not c_sources:
                cmd = [cc, "-c", bundle_path, "-o", output_path] + common_flags
                commands.append(cmd)
            else:
                temp_objs = [os.path.join(build_dir, "bundle.o")]
                cmd_bundle = [cc, "-c", bundle_path, "-o", temp_objs[0]] + common_flags
                commands.append(cmd_bundle)

                for i, c_file in enumerate(c_sources):
                    c_base = os.path.splitext(os.path.basename(c_file))[0]
                    c_obj = os.path.join(build_dir, f"{c_base}_{i}.o")
                    temp_objs.append(c_obj)
                    commands.append([cc, "-c", c_file, "-o", c_obj] + common_flags)

                if is_win and ("cl" in cc.lower() or "msvc" in cc.lower()):
                    cmd_combine = ["link", "-lib", f"/OUT:{output_path}"] + temp_objs
                else:
                    cmd_combine = [cc, "-r", "-nostdlib", "-o", output_path] + temp_objs
                commands.append(cmd_combine)

        elif out_type == OutputType.STATIC:
            temp_objs = [os.path.join(build_dir, "bundle.o")]
            cmd_bundle = [cc, "-c", bundle_path, "-o", temp_objs[0]] + common_flags
            commands.append(cmd_bundle)

            for i, c_file in enumerate(c_sources):
                c_base = os.path.splitext(os.path.basename(c_file))[0]
                c_obj = os.path.join(build_dir, f"{c_base}_{i}.o")
                temp_objs.append(c_obj)
                commands.append([cc, "-c", c_file, "-o", c_obj] + common_flags)

            if is_win and ("cl" in cc.lower() or "msvc" in cc.lower()):
                cmd_ar = ["lib", f"/OUT:{output_path}"] + temp_objs
            else:
                cmd_ar = ["ar", "rcs", output_path] + temp_objs
            commands.append(cmd_ar)

        elif out_type == OutputType.SHARED:
            if is_win:
                cmd = [cc, "-shared", bundle_path] + c_sources + ["-o", output_path] + common_flags + link_flags
            elif is_mac:
                dyn_flag = "-dynamiclib" if "clang" in cc else "-shared"
                cmd = [cc, "-fPIC", dyn_flag, bundle_path] + c_sources + ["-o", output_path] + common_flags + link_flags
            else:
                cmd = [cc, "-fPIC", "-shared", bundle_path] + c_sources + ["-o", output_path] + common_flags + link_flags
            commands.append(cmd)

        else:  # EXE
            cmd = [cc, bundle_path] + c_sources + ["-o", output_path] + common_flags + link_flags
            commands.append(cmd)

        return commands

    def _runtime_pch_exists(self) -> Optional[str]:
        """Directory containing a *packaged* ``pengu_runtime.h.gch``, if any.

        ``build_runtime.py`` writes one into ``build/include/`` and the release
        archives ship it, so ``pengu build``/``pengu run`` can reuse it without
        regenerating a throw-away PCH for every temporary build directory.
        """
        try:
            from pengu_paths import runtime_include_dirs
            for directory in runtime_include_dirs():
                try:
                    if os.path.isfile(os.path.join(str(directory), "pengu_runtime.h.gch")):
                        return str(directory)
                except OSError:
                    continue
        except Exception:
            pass
        return None

    def _ensure_runtime_pch(self, build_dir: str, base_flags: List[str],
                            cc: str) -> Optional[str]:
        """Builds (or reuses) ``<build>/pch/pengu_runtime.h.gch``.

        Returns the directory to put *before* ``build_dir`` in the include path
        so that gcc/clang picks up the precompiled header, or ``None`` when the
        PCH is unavailable/disabled (the build then proceeds normally).
        """
        from pengu_paths import find_runtime_header
        try:
            runtime_src = find_runtime_header()
        except Exception:
            runtime_src = None
        if not runtime_src:
            return None
        pch_dir = os.path.join(build_dir, "pch")
        try:
            os.makedirs(pch_dir, exist_ok=True)
        except OSError:
            return None
        header_copy = os.path.join(pch_dir, "pengu_runtime.h")
        gch = header_copy + ".gch"
        # The .gch is tied to the flags used to create it, so reuse exactly the
        # build's base flags (minus outputs/inputs).  The signature is checked on
        # *every* call — not only when the header is newer — because a changed
        # -D/-I means the existing .gch is unusable even if it is newer.
        sig = self._pch_signature(base_flags)
        sig_file = gch + ".sig"
        try:
            with open(sig_file, encoding="utf-8") as fh:
                sig_matches = fh.read() == sig
        except OSError:
            sig_matches = False
        needs_build = not os.path.isfile(gch) or not sig_matches
        if not needs_build:
            try:
                needs_build = os.path.getmtime(str(runtime_src)) > os.path.getmtime(gch)
            except OSError:
                needs_build = True
        if needs_build:
            try:
                shutil.copy2(str(runtime_src), header_copy)
            except OSError:
                return None
            header_flags = [f for f in base_flags if f.startswith(("-I", "-D", "-U"))]
            cmd = [cc, "-x", "c-header", header_copy, "-o", gch, "-std=c11", "-O0"] + header_flags
            if self.verbose:
                self._vlog(f"[pengu] building runtime PCH: {' '.join(cmd)}")
            t_pch = time.time()
            try:
                res = subprocess.run(cmd, cwd=self.config.base_dir,
                                     capture_output=True, text=True)
            except OSError:
                return None
            if res.returncode != 0:
                # Best effort: a failed PCH must never fail the build.
                if self.verbose:
                    self._vlog("[pengu] PCH generation failed; continuing without it")
                try:
                    os.unlink(gch)
                except OSError:
                    pass
                return None
            try:
                with open(sig_file, "w", encoding="utf-8") as fh:
                    fh.write(sig)
            except OSError:
                pass
            if self.verbose:
                self._vlog(f"[pengu] PCH ready in {time.time() - t_pch:.3f}s -> {gch}")
        elif self.verbose:
            self._vlog(f"[pengu] reusing runtime PCH {gch}")
        return pch_dir

    @staticmethod
    def _pch_signature(base_flags: List[str]) -> str:
        """Flags that must match between the PCH and the compilation."""
        relevant = [f for f in base_flags if f.startswith(("-I", "-D", "-U", "-std"))]
        return " ".join(sorted(relevant))

    def compile(self, bundle_path: Optional[str] = None) -> Tuple[str, bool]:
        """Bundles and compiles project according to ProjectConfig and profile.

        Args:
            bundle_path: Optional pre-existing bundle.c path.

        Returns:
            Tuple of (output_artifact_path, is_cached_boolean).
        """
        is_cached = False
        if bundle_path is None:
            bundle_path, is_cached = self.bundle()

        if self.config.output == OutputType.C:
            return bundle_path, is_cached

        build_dir = self.get_build_directory()
        out_name = self.get_output_artifact_name()
        out_path = os.path.join(build_dir, out_name)

        if is_cached and os.path.isfile(out_path):
            # The bundle being up to date is not enough: the artifact must have
            # been produced *from* it. A regenerated bundle is newer than the
            # previous binary, so rebuild instead of shipping a stale executable.
            if os.path.getmtime(out_path) >= os.path.getmtime(bundle_path):
                return out_path, True

        def _run_commands(commands: List[List[str]]) -> Optional[str]:
            """Runs every command; returns None on success or the error detail."""
            for cmd in commands:
                self._vlog(f"[pengu] running C compiler: {' '.join(cmd)}")
                t_cmd = time.time()
                try:
                    res = subprocess.run(cmd, cwd=self.config.base_dir,
                                         capture_output=True, text=True)
                except OSError as exc:
                    # The compiler does not exist / is not executable.  Report it
                    # like a failed command so the TCC → configured-compiler
                    # fallback below can recover instead of crashing the CLI.
                    return f"Command: {' '.join(cmd)}\nCould not execute: {exc}"
                if self.verbose:
                    self._vlog(f"[pengu] command finished in {time.time() - t_cmd:.3f}s "
                               f"(rc={res.returncode})")
                if res.returncode != 0:
                    detail = f"Command: {' '.join(cmd)}\nExit code: {res.returncode}"
                    if res.stdout and res.stdout.strip():
                        detail += f"\n\nCompiler stdout:\n{res.stdout}"
                    if res.stderr and res.stderr.strip():
                        detail += f"\n\nCompiler stderr:\n{res.stderr}"
                    return detail
            return None

        # 'cc' measures the compiler invocations only: assembling the command
        # line probes pkg-config several times, which has nothing to do with the
        # C compile and would dominate the phase on a TCC build.
        commands = self.build_compile_commands(bundle_path, out_path)
        # Pre-flight (item 4.17): the bundle references `pengu_abi_version`, so a
        # missing archive would surface as an obscure `undefined reference`.
        # Report it before invoking the compiler instead. Linking steps only:
        # `c` output is just the emitted bundle and object outputs are archives
        # whose undefined symbols are resolved by their consumer.
        if self.config.output not in (OutputType.C, OutputType.OBJ, OutputType.STATIC):
            if _find_runtime_archive() is None:
                raise CompileFailedError(_missing_runtime_archive_message())
        t_cc_all = time.time()
        error = _run_commands(commands)

        # TCC (and any PENGU_DEV_CC override) is a development optimisation, not
        # a hard requirement: if it cannot compile the bundle, retry once with
        # the project's configured compiler and normal flags before failing.
        if error is not None and self.fallback_cc:
            used = os.path.basename(commands[0][0]).lower() if commands else ""
            fallback = self.fallback_cc
            if used and used != os.path.basename(fallback).lower():
                print(f"[pengu] development compiler failed; retrying with {fallback}",
                      file=sys.stderr)
                self.config.cc = fallback
                self.fallback_cc = None
                self.dev_fast_flags = False
                commands = self.build_compile_commands(bundle_path, out_path)
                error = _run_commands(commands)

        if error is not None:
            raise CompileFailedError(
                f"C compilation failed ({self.config.name})\n\n{error}"
            )

        self.timings["cc"] = time.time() - t_cc_all
        return out_path, False


def _env_flag_list(name: str) -> List[str]:
    """Reads a space-separated flag list from an environment variable.

    Mirrors the CFLAGS/LDFLAGS convention so CI (and users) can inject extra
    flags without editing the manifest.  Quotes are honoured.
    """
    import shlex

    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    try:
        return shlex.split(raw)
    except ValueError:
        return raw.split()


def _env_flag_list_doc() -> str:  # pragma: no cover - documentation helper
    return "PENGU_CFLAGS / PENGU_LDFLAGS"


def _lock_target(config: "ProjectConfig") -> str:
    """Canonicalized target recorded in the lockfile (roadmap 4.1 + 3.5).

    Triples that describe the same platform (``x86_64-w64-mingw32`` and
    ``x86_64-pc-windows-gnu``) must produce the same lock entry, otherwise
    ``--frozen`` fails spuriously across machines/CI images.  The canonical form
    is ``<arch>-<os>-<env>`` with the Windows GNU environments folded together.
    """
    raw = str(getattr(config, "target", "") or "").strip()
    if not raw:
        return host_os()
    triple = parse_target_triple(raw)
    if not triple.os:
        return raw
    env = triple.env
    if triple.os == "windows" and env in ("mingw", "gnu", ""):
        env = "gnu"
    parts = [p for p in (triple.arch, triple.os, env) if p]
    return "-".join(parts)


def _ensure_lockfile(config: "ProjectConfig", locked: bool = False,
                     frozen: bool = False, verbose: bool = False) -> Optional[str]:
    """Resolves the dependency graph and enforces / updates ``pengu.lock``.

    - default: writes (or refreshes) ``pengu.lock``;
    - ``--locked``: verifies it and fails on any mismatch, never writes;
    - ``--frozen``: like ``--locked`` and additionally requires it to exist, so
      nothing new can be resolved (offline/CI builds).

    Returns the lock path (or None when the project has no dependencies).
    """
    from pengu_lock import (
        LockError,
        build_lock_from_graph,
        diff_locks,
        read_lock,
        write_lock,
    )

    has_deps = bool(_manifest_dependencies(config.base_dir))
    existing = read_lock(config.base_dir)
    if not has_deps and existing is None:
        return None

    strict = locked or frozen
    if strict and existing is None:
        flag = "--frozen" if frozen else "--locked"
        raise LockError(
            f"[E0061] {flag} requires an existing pengu.lock, but none was found.\n"
            f"  Run `pengu build` once without {flag} to generate it, then commit it."
        )

    graph = resolve_transitive_dependencies(
        config,
        install_missing=not strict,
        verbose=verbose,
    )
    current = build_lock_from_graph(graph, target=_lock_target(config))
    lock_path = os.path.join(config.base_dir, "pengu.lock")

    if existing is not None and strict:
        problems = diff_locks(existing, current, target=_lock_target(config))
        if problems:
            raise LockError(
                "[E0061] pengu.lock is out of date or the dependencies changed:\n  - "
                + "\n  - ".join(problems)
                + "\n  Run `pengu update` (or `pengu build` without --locked/--frozen) "
                  "and commit the updated pengu.lock."
            )
        return lock_path

    if strict:
        return lock_path
    return write_lock(config.base_dir, current)


def _report_denied_deprecations(diags: List[Dict[str, Any]], json_output: bool = False) -> None:
    """Prints the denied W0006 diagnostics and aborts (roadmap 5.4 / 6.0.c)."""
    denied = [d for d in diags if d.get("severity") == "error" and d.get("code") == "W0006"]
    if not denied:
        return
    if json_output:
        for d in diags:
            print(json.dumps({"type": "diagnostic", **d}, ensure_ascii=False))
        print(json.dumps({"type": "summary", "ok": False, "errors": len(denied)},
                         ensure_ascii=False))
    else:
        for d in denied:
            emit(f"     Error {d['file']}:{d['line']}:{d['col']} "
                  f"[{d['code']}] {d['message']}", file=sys.stderr, level="error")
        emit("     Error deprecated symbol used with --deny-deprecated",
              file=sys.stderr, level="error")
    raise SystemExit(1)


def enforce_deny_deprecated(builder: "PenguBuilder", json_output: bool = False) -> None:
    """Runs the deprecation gate on an existing builder (single pass, memoised).

    Used by build_project and run_script so the flag means the same thing for a
    project and for a standalone script (roadmap 6.0.c / 6.0.d).
    """
    if not getattr(builder, "deny_deprecated", False):
        return
    _ok, diags = builder.check_sources_diagnostics()
    _report_denied_deprecations(diags, json_output=json_output)


def build_project(
    config_path: Optional[str] = None,
    profile: str = "debug",
    entry: Optional[str] = None,
    output: Optional[str] = None,
    test: bool = False,
    defines: Optional[List[str]] = None,
    cc: Optional[str] = None,
    verbose: bool = False,
    pch: bool = False,
    no_dce: bool = False,
    strict_c99: bool = False,
    target_compiler: str = "",
    target: str = "",
    locked: bool = False,
    frozen: bool = False,
    release_unsafe: bool = False,
    deny_deprecated: bool = False,
    json_output: bool = False,
) -> str:
    """Builds project from configuration file with status printing.

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        entry: Optional entry file path override.
        output: Optional output file path override.
        test: True to compile integrated unit tests in --test mode.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override (e.g. 'clang'), wins over config.
        verbose: True to print module order, C commands and phase timings.
        strict_c99: True to forbid GNU extensions in the emitted C.
        target_compiler: Attribute/restrict dialect ("gcc"|"clang"|"msvc"|"tcc").

    Returns:
        Path to generated build artifact.
    """
    t0 = time.time()
    config = ProjectConfig.load(config_path, profile=profile)
    if entry:
        config.entry = entry
    if output:
        if output.endswith(".c") or output == "bundle.c":
            config.output = OutputType.C
    if defines:
        config.defines = list(config.defines or []) + defines
    if cc:
        config.cc = cc
    if strict_c99:
        config.strict_c99 = True
    if target_compiler:
        config.target_compiler = target_compiler
    if target:
        config.target = target
    config.release_unsafe = bool(release_unsafe)
    config.deny_deprecated = bool(deny_deprecated)
    _set_release_unsafe(config.release_unsafe)

    try:
        _ensure_lockfile(config, locked=locked, frozen=frozen,
                         verbose=verbose and not json_output)
    except Exception as exc:  # noqa: BLE001 - lock errors abort the build
        if json_output:
            print(json.dumps({"type": "diagnostic", "file": os.path.join(config.base_dir, "pengu.lock"),
                              "line": 0, "col": 0, "code": "E0061", "severity": "error",
                              "message": str(exc), "help": "Run `pengu build` without --locked/--frozen.",
                              "note": None}, ensure_ascii=False))
            print(json.dumps({"type": "summary", "ok": False, "errors": 1}, ensure_ascii=False))
            raise SystemExit(1)
        emit(f"     Error {exc}", file=sys.stderr, color="red", level="error")
        raise SystemExit(1)

    try:
        _require_entry_file(config)
    except EntryPointNotFoundError as e:
        if json_output:
            print(json.dumps({"type": "diagnostic", **_diagnostic_message(e, config.resolve_entry())},
                             ensure_ascii=False))
            print(json.dumps({"type": "summary", "ok": False, "errors": 1, "warnings": 0,
                              "duration_ms": 0.0}, ensure_ascii=False))
            raise SystemExit(1)
        emit(f"     Error {e.message}", file=sys.stderr, color="red", level="error")
        if e.help:
            print(f"      help: {e.help}", file=sys.stderr)
        raise SystemExit(1)

    if not json_output:
        emit(f"   Compiling {config.name} v{config.version} ({config.output.value}) [{config.profile}]"
              + (" [test]" if test else ""), level="progress")

    builder = PenguBuilder(config)
    builder.is_test_mode = test
    builder.verbose = verbose and not json_output
    builder.use_pch = bool(pch)
    builder.deny_deprecated = bool(deny_deprecated)
    # The deprecation gate runs on this very builder (roadmap 6.0.c): one module
    # resolution and one memoised check pass, instead of a throwaway second one.
    enforce_deny_deprecated(builder, json_output=json_output)
    # PENGU_NO_DCE is read by PenguCodegen, so it must be set for the whole
    # bundle/compile and restored afterwards (build_project is also a library
    # entry point called from long-lived processes).
    prev_no_dce = os.environ.get("PENGU_NO_DCE")
    if no_dce:
        os.environ["PENGU_NO_DCE"] = "1"
    try:
        if output and (output.endswith(".c") or output == "bundle.c"):
            artifact, is_cached = builder.bundle(output_file=output)
        else:
            artifact, is_cached = builder.compile()
    except Exception as exc:  # noqa: BLE001 - report any build failure as JSON
        if json_output:
            line = getattr(exc, "line", None) or 0
            col = getattr(exc, "column", None) or getattr(exc, "col", None) or 0
            print(json.dumps({
                "type": "diagnostic",
                "file": getattr(exc, "filename", None) or config.resolve_entry(),
                "line": int(line),
                "col": int(col),
                "code": getattr(exc, "code", None) or "",
                "severity": "error",
                "message": getattr(exc, "message", None) or str(exc),
                "help": getattr(exc, "help", None),
                "note": getattr(exc, "note", None),
            }, ensure_ascii=False))
            print(json.dumps({"type": "summary", "ok": False, "errors": 1,
                              "duration_ms": round((time.time() - t0) * 1000, 2)},
                             ensure_ascii=False))
            raise SystemExit(1)
        raise
    finally:
        if no_dce:
            if prev_no_dce is None:
                os.environ.pop("PENGU_NO_DCE", None)
            else:
                os.environ["PENGU_NO_DCE"] = prev_no_dce
    elapsed = time.time() - t0

    if json_output:
        print(json.dumps({
            "type": "summary",
            "ok": True,
            "artifact": artifact,
            "cached": bool(is_cached),
            "profile": config.profile,
            "duration_ms": round(elapsed * 1000, 2),
        }, ensure_ascii=False))
    elif is_cached:
        emit(f"    Finished (cached) [{config.profile}] target(s) in {elapsed:.2f}s -> {artifact}", color="green", level="progress")
    else:
        emit(f"    Finished [{config.profile}] target(s) in {elapsed:.2f}s -> {artifact}", color="green", level="progress")
    return artifact


def check_project(
    config_path: Optional[str] = None,
    profile: str = "debug",
    entry: Optional[str] = None,
    defines: Optional[List[str]] = None,
    cc: Optional[str] = None,
    verbose: bool = False,
    json_output: bool = False,
    deny_deprecated: bool = False,
) -> bool:
    """Parses and type-checks every module without generating code (CI friendly).

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        entry: Optional entry file path override.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override (informational for 'when').
        verbose: True to print per-file progress.
        json_output: Emit machine-readable JSON Lines (for CI) instead of text.

    Returns:
        True when every module passes parse + semantic checking.
    """
    t0 = time.time()
    config = ProjectConfig.load(config_path, profile=profile)
    if entry:
        config.entry = entry
    if defines:
        config.defines = list(config.defines or []) + defines
    if cc:
        config.cc = cc

    if not json_output:
        emit(f"   Checking {config.name} v{config.version} [{config.profile}]", color="cyan", level="progress")

    builder = PenguBuilder(config)
    builder.verbose = verbose and not json_output
    builder.deny_deprecated = bool(deny_deprecated)
    ok, diagnostics = builder.check_sources_diagnostics()
    elapsed = time.time() - t0

    if json_output:
        for d in diagnostics:
            print(json.dumps({"type": "diagnostic", **d}, ensure_ascii=False))
        print(json.dumps({
            "type": "summary",
            "ok": ok,
            "errors": sum(1 for d in diagnostics if d.get("severity") == "error"),
            "warnings": sum(1 for d in diagnostics if d.get("severity") == "warning"),
            "duration_ms": round(elapsed * 1000, 2),
        }, ensure_ascii=False))
        return ok

    def _fmt(d: Dict[str, Any]) -> str:
        code_str = f"[{d['code']}] " if d.get("code") else ""
        return f"  {d['file']}:{d['line']}:{d['col']} {code_str}{d['message']}"

    warnings = [d for d in diagnostics if d.get("severity") == "warning"]
    errors = [d for d in diagnostics if d.get("severity") != "warning"]
    for d in warnings:
        emit(f"   Warning{_fmt(d)[1:]}", file=sys.stderr, color="yellow", level="warning")
    if ok:
        suffix = f" ({len(warnings)} warning(s))" if warnings else ""
        emit(f"     Clean no errors found in {elapsed:.2f}s{suffix}", color="green", level="progress")
    else:
        emit(f"   Errors found in {elapsed:.2f}s", color="red", level="error")
        for d in errors:
            print(_fmt(d), file=sys.stderr)
    return ok


def _diagnostic_message(exc: Any, fpath: str) -> Dict[str, Any]:
    """Builds a structured diagnostic dict from a compiler exception.

    Kept in one place so the project path and the positional-file path of
    ``pengu check`` report identically shaped diagnostics.
    """
    line = getattr(exc, "line", None) or 0
    col = getattr(exc, "column", None)
    if col is None:
        col = getattr(exc, "col", None) or 0
    return {
        "file": fpath,
        "line": int(line),
        "col": int(col),
        "code": getattr(exc, "code", None) or "",
        "severity": "error",
        "message": getattr(exc, "message", None) or str(exc),
        "help": getattr(exc, "help", None),
        "note": getattr(exc, "note", None),
    }


def _report_check_results(ok: bool, diagnostics: List[Dict[str, Any]], elapsed: float,
                          json_output: bool) -> bool:
    """Prints a check result in text or JSON Lines form and returns ``ok``."""
    if json_output:
        for d in diagnostics:
            print(json.dumps({"type": "diagnostic", **d}, ensure_ascii=False))
        print(json.dumps({
            "type": "summary",
            "ok": ok,
            "errors": sum(1 for d in diagnostics if d.get("severity") == "error"),
            "warnings": sum(1 for d in diagnostics if d.get("severity") == "warning"),
            "duration_ms": round(elapsed * 1000, 2),
        }, ensure_ascii=False))
        return ok

    def _fmt(d: Dict[str, Any]) -> str:
        code_str = f"[{d['code']}] " if d.get("code") else ""
        return f"  {d['file']}:{d['line']}:{d['col']} {code_str}{d['message']}"

    warnings = [d for d in diagnostics if d.get("severity") == "warning"]
    errors = [d for d in diagnostics if d.get("severity") != "warning"]
    for d in warnings:
        emit(f"   Warning{_fmt(d)[1:]}", file=sys.stderr, color="yellow", level="warning")
    if ok:
        suffix = f" ({len(warnings)} warning(s))" if warnings else ""
        emit(f"     Clean no errors found in {elapsed:.2f}s{suffix}", color="green", level="progress")
    else:
        emit(f"   Errors found in {elapsed:.2f}s", color="red", level="error")
        for d in errors:
            print(_fmt(d), file=sys.stderr)
    return ok


def _require_entry_file(config: ProjectConfig) -> None:
    """Fails fast when the project entry point does not exist.

    Without this, a missing entry surfaces either as an opaque C link error
    ("referencia a `main' sin definir", as before Phase 1) or -- worse, for
    ``pengu test`` -- as a green "No tests to run." because the generated test
    harness always produces a valid C program (blocker B2).

    Args:
        config: Resolved project configuration.

    Raises:
        EntryPointNotFoundError: When the entry file is absent.
    """
    entry_abs = config.resolve_entry()
    if os.path.isfile(entry_abs):
        return
    rel = os.path.relpath(entry_abs, config.base_dir)
    raise EntryPointNotFoundError(
        f"entry point not found: {entry_abs}",
        help=f"Create '{rel}', or pass --entry <path> to point at a different file.",
    )


def check_files(
    files: List[str],
    config_path: Optional[str] = None,
    profile: str = "debug",
    defines: Optional[List[str]] = None,
    cc: Optional[str] = None,
    verbose: bool = False,
    json_output: bool = False,
    deny_deprecated: bool = False,
) -> bool:
    """Parses and type-checks an explicit list of ``.pengu`` files.

    Each file is checked in place: it is treated as the entry point and its own
    directory becomes the base directory, so a sibling ``import`` resolves. The
    project configuration is still loaded (when one can be found) so that
    ``lib_dir``, ``include_dirs``, ``defines`` and ``links`` from ``pengu.toml``
    apply -- ``import std.spark`` must resolve exactly as it does in a build.

    Args:
        files: ``.pengu`` paths to check. A path that does not exist is an error.
        config_path: Optional path to config file or project root.
        profile: Selected build profile ('debug' or 'release').
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override (informational for 'when').
        verbose: True to print per-file progress.
        json_output: Emit machine-readable JSON Lines (for CI) instead of text.
        deny_deprecated: Treat the use of a @deprecated symbol (W0006) as an error.

    Returns:
        True when every given file passes parse + semantic checking.
    """
    t0 = time.time()
    config = ProjectConfig.load(config_path, profile=profile)
    if defines:
        config.defines = list(config.defines or []) + defines
    if cc:
        config.cc = cc

    if not json_output:
        label = f"{len(files)} file{'s' if len(files) != 1 else ''}"
        emit(f"   Checking {label} [{profile}]", color="cyan", level="progress")

    ok = True
    diagnostics: List[Dict[str, Any]] = []
    for raw in files:
        path = os.path.abspath(raw)
        if not os.path.isfile(path):
            ok = False
            diagnostics.append({
                "file": path,
                "line": 0,
                "col": 0,
                "code": "",
                "severity": "error",
                "message": f"entry point not found: {path}",
                "help": "Pass an existing .pengu file (or omit the argument to check the project entry).",
                "note": None,
            })
            continue
        if not path.endswith(".pengu"):
            ok = False
            diagnostics.append({
                "file": path,
                "line": 0,
                "col": 0,
                "code": "",
                "severity": "error",
                "message": f"not a PenguScript file: {path}",
                "help": "Only '.pengu' sources can be checked.",
                "note": None,
            })
            continue

        # Check the file in place: its own directory is the base_dir so that
        # sibling imports resolve, and it is the entry point of its own graph.
        file_cfg = replace(
            config,
            base_dir=os.path.dirname(path),
            entry=os.path.basename(path),
            name=os.path.splitext(os.path.basename(path))[0],
        )
        builder = PenguBuilder(file_cfg)
        builder.verbose = verbose and not json_output
        builder.deny_deprecated = bool(deny_deprecated)
        try:
            file_ok, file_diags = builder.check_sources_diagnostics()
        except Exception as exc:  # noqa: BLE001 - never let one file abort the sweep
            file_ok, file_diags = False, [_diagnostic_message(exc, path)]
        ok = ok and file_ok
        diagnostics.extend(file_diags)

    return _report_check_results(ok, diagnostics, time.time() - t0, json_output)


#: Directory names never walked by :func:`_collect_pengu_files`. These are
#: build artifacts, VCS/venv state and caches: they are gitignored, may hold
#: stale generated sources, and are not part of the repository's source tree, so
#: reporting them to `pengu fmt --check` would make the gate unusable.
_FMT_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", "build", "dist", "target", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".eggs",
})


def _collect_pengu_files(paths: List[str]) -> List[str]:
    """Expands file/directory CLI arguments into a sorted .pengu file list.

    Directories named in :data:`_FMT_SKIP_DIRS` (build output, caches, VCS and
    virtualenv state) are not descended into. An explicit file argument is
    always honoured, even inside such a directory.
    """
    files: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d not in _FMT_SKIP_DIRS)
                for name in sorted(names):
                    if name.endswith(".pengu"):
                        files.append(os.path.join(root, name))
        elif os.path.isfile(p):
            if not p.endswith(".pengu"):
                raise ValueError(f"Not a PenguScript file: {p}")
            files.append(os.path.abspath(p))
        else:
            raise FileNotFoundError(f"Path not found: {p}")
    return sorted(set(files))


def _resolve_indent(cfg: Optional[Dict[str, object]], indent: Optional[int]) -> int:
    """Resolves the indentation unit with  ``CLI flag > config > default``.

    ``indent`` is the value of ``--indent``: ``None`` when the flag was not
    given, which is what makes an explicit flag beat ``.pengufmt.toml`` instead
    of being silently overridden by it.

    Args:
        cfg: Parsed formatting config, or None when none was found.
        indent: Explicit ``--indent`` value, or None when not provided.

    Returns:
        Spaces per indentation level (default 4).
    """
    if indent is not None:
        return int(indent)
    if cfg and cfg.get("tab_size") is not None:
        return int(cfg["tab_size"])
    return 4


def _resolve_insert_spaces(cfg: Optional[Dict[str, object]], tabs: Optional[bool]) -> bool:
    """Resolves spaces-vs-tabs with ``CLI flag > config > default``.

    Mirrors :func:`_resolve_indent`: ``tabs`` is ``None`` when ``--tabs`` was not
    given, so an explicit flag wins over ``insert_spaces``/``use_tabs`` in
    ``.pengufmt.toml`` instead of being silently overridden by it.

    Args:
        cfg: Parsed formatting config, or None when none was found.
        tabs: True when ``--tabs`` was given, None when it was omitted.

    Returns:
        True to indent with spaces, False to indent with tabs.
    """
    if tabs is not None:
        return not tabs
    if cfg and cfg.get("insert_spaces") is not None:
        return bool(cfg["insert_spaces"])
    return True


def _find_runtime_archive() -> Optional[str]:
    """Returns the path of ``libpengu_runtime.a``, or None when it is missing.

    The archive is a hard build requirement (item 4.17): every bundle carries a
    reference to ``pengu_abi_version``, so without it the linker would fail with
    an inscrutable ``undefined reference``. Locating it up front lets the CLI
    report an actionable error instead.
    """
    try:
        for d in runtime_lib_dirs():
            candidate = os.path.join(str(d), "libpengu_runtime.a")
            if os.path.isfile(candidate):
                return candidate
    except Exception:
        pass
    return None


def _missing_runtime_archive_message() -> str:
    """Actionable error text for a build with no ``libpengu_runtime.a``."""
    searched = [str(d) for d in runtime_lib_dirs()]
    paths = "\n".join(f"    {os.path.join(d, 'libpengu_runtime.a')}" for d in searched) \
        or "    (no runtime library directory found)"
    return (
        "libpengu_runtime.a not found.\n"
        "  Every PenguScript build links the runtime, so the archive is required.\n"
        "  Run `python build_runtime.py` to build it, set PENGU_LIB_DIR to the\n"
        "  directory that holds it, or install a release that ships it.\n"
        f"  Searched:\n{paths}"
    )


def fmt_files(paths: List[str], check_only: bool = False, write: bool = True,
              indent: Optional[int] = None, tabs: Optional[bool] = None,
              verbose: bool = False,
              diff: bool = False, use_config: bool = True) -> int:
    """Formats .pengu files/directories with the standard style.

    Reuses the same formatting logic as the LSP's textDocument/formatting.

    Args:
        paths: Files and/or directories to format (directories are recursive).
        check_only: True to only report files that would change (never writes).
        write: True to overwrite files with formatted content.
        indent: Spaces per indentation level, or None to take the nearest
            ``.pengufmt.toml`` and fall back to 4. An explicit value always wins
            over the config file.
        tabs: True to indent with tabs, None to take the nearest config.
        verbose: True to print every file considered.
        diff: True to print a unified diff for every file that would change.
        use_config: True to honour a nearby ``.pengufmt.toml`` / ``pengu.yaml``.

    Returns:
        Number of files that changed (or would change with --check).
    """
    import difflib
    from pengu_lsp.formatting import format_pengu_source, load_format_config

    files = _collect_pengu_files(paths)
    changed: List[str] = []
    for fp in files:
        try:
            display = os.path.relpath(fp, os.getcwd())
        except ValueError:
            display = fp
        with open(fp, "r", encoding="utf-8") as f:
            original = f.read()
        head = "\n".join(original.splitlines()[:5])
        if "@generated" in head:
            if verbose:
                print(f"   skip (generated) {display}")
            continue
        cfg = load_format_config(fp) if use_config else None
        eff_indent = _resolve_indent(cfg, indent)
        eff_spaces = _resolve_insert_spaces(cfg, tabs)
        blank_max = cfg.get("blank_lines_max") if cfg else None
        formatted = format_pengu_source(
            original, tab_size=int(eff_indent), insert_spaces=bool(eff_spaces),
            blank_lines_max=blank_max if isinstance(blank_max, int) else None,
        )
        if verbose:
            print(f"   fmt {display}")
        if formatted == original:
            continue
        changed.append(fp)
        if diff:
            for dline in difflib.unified_diff(
                original.splitlines(), formatted.splitlines(),
                fromfile=display, tofile=display + " (formatted)", lineterm="",
            ):
                print(dline)
        elif verbose or check_only:
            emit(f" would format {display}", color="yellow", level="progress")
        if write and not check_only and not diff:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(formatted)
            if not diff:
                emit(f"  formatted {display}", color="green", level="progress")

    if not diff:
        if check_only:
            print(f"\n{len(changed)} file(s) would be reformatted.")
        elif write:
            print(f"\n{len(changed)} file(s) formatted.")
    return len(changed)


def fmt_stdin(indent: Optional[int] = None, tabs: Optional[bool] = None,
              config_path: Optional[str] = None, check_only: bool = False) -> int:
    """Formats stdin to stdout (editor / pipeline integration).

    Returns 0 when the input was already formatted (or was written), 1 with
    ``--check`` when it would change (nothing is written in check mode).
    """
    from pengu_lsp.formatting import format_pengu_source, load_format_config

    text = sys.stdin.read()
    cfg = load_format_config(config_path or os.getcwd())
    eff_indent = _resolve_indent(cfg, indent)
    eff_spaces = _resolve_insert_spaces(cfg, tabs)
    blank_max = cfg.get("blank_lines_max") if cfg else None
    formatted = format_pengu_source(
        text, tab_size=int(eff_indent), insert_spaces=bool(eff_spaces),
        blank_lines_max=blank_max if isinstance(blank_max, int) else None,
    )
    if check_only:
        return 1 if formatted != text else 0
    sys.stdout.write(formatted)
    return 0


def clean_project(config_path: Optional[str] = None) -> None:
    """Removes build directory and intermediate artifacts.

    Args:
        config_path: Optional path to config file or directory.
    """
    config = ProjectConfig.load(config_path)
    build_dir = os.path.abspath(os.path.join(config.base_dir, config.build_dir))

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
        emit(f"     Cleaned build directory '{build_dir}'", color="green", level="progress")
    else:
        emit("     Cleaned nothing to clean.", color="yellow", level="progress")


def _toml_scalar(value: Any) -> str:
    """Serializes a scalar/list value as TOML (JSON strings are valid TOML)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        # A None here is a caller bug; writing "" would corrupt the manifest.
        raise TypeError("cannot serialize None to TOML")
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_scalar(v) for v in value) + "]"
    raise TypeError(f"cannot serialize {type(value).__name__} to TOML")


def _dump_toml(data: Dict[str, Any], prefix: str = "") -> List[str]:
    """Minimal TOML writer for the shapes a ``pengu.toml`` uses.

    Scalars of a table are emitted before its sub-tables, which is what TOML
    requires.  Only dict/list/scalar values are supported; lists of tables are
    not needed by the manifest.
    """
    lines: List[str] = []
    scalars = {k: v for k, v in data.items() if not isinstance(v, dict)}
    tables = {k: v for k, v in data.items() if isinstance(v, dict)}
    for key, value in scalars.items():
        lines.append(f"{key} = {_toml_scalar(value)}")
    for key, value in tables.items():
        header = f"{prefix}{key}"
        lines.append("")
        lines.append(f"[{header}]")
        lines.extend(_dump_toml(value, prefix=f"{header}."))
    return lines


def _write_toml_file(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(_dump_toml(data)) + "\n")


def _update_config_dependency(base_dir: str, dep_name: str, source: str, branch: Optional[str] = None) -> None:
    """Updates the project manifest with a new dependency.

    TOML is the canonical format (roadmap 4.11): an existing ``pengu.toml`` is
    preferred, and when no manifest exists a ``pengu.toml`` is created.  YAML and
    JSON manifests are still updated in place for backwards compatibility.

    Args:
        base_dir: Root directory of project.
        dep_name: Name identifier for the dependency.
        source: URL or local path.
        branch: Optional branch name.
    """
    candidates = ["pengu.toml", "Pengu.toml", "pengu.yaml", "pengu.yml", "pengu.json"]
    cfg_file = None
    for c in candidates:
        p = os.path.join(base_dir, c)
        if os.path.isfile(p):
            cfg_file = p
            break

    if cfg_file is None:
        cfg_file = os.path.join(base_dir, "pengu.toml")

    ext = os.path.splitext(cfg_file)[1].lower()
    dep_info: Dict[str, Any] = {"url": source}
    if branch:
        dep_info["branch"] = branch

    if ext == ".toml":
        data: Dict[str, Any] = {}
        if os.path.isfile(cfg_file):
            try:
                with open(cfg_file, "rb") as f:
                    data = tomllib.load(f)
            except Exception:
                data = {}
        if not isinstance(data.get("dependencies"), dict):
            data["dependencies"] = {}
        data["dependencies"][dep_name] = dep_info
        _write_toml_file(cfg_file, data)
        return

    if ext in (".yaml", ".yml"):
        content = ""
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                content = f.read()

        if _load_yaml_module() is not None:
            try:
                parsed = yaml.safe_load(content) or {}
                if "dependencies" not in parsed or not isinstance(parsed["dependencies"], dict):
                    parsed["dependencies"] = {}
                parsed["dependencies"][dep_name] = dep_info
                with open(cfg_file, "w", encoding="utf-8") as f:
                    yaml.dump(parsed, f, sort_keys=False)
                return
            except Exception:
                pass

        # Fallback manual YAML update
        if "dependencies:" in content:
            lines = content.splitlines()
            new_lines = []
            deps_added = False
            for line in lines:
                new_lines.append(line)
                if line.strip() == "dependencies:" or line.strip().startswith("dependencies:"):
                    new_lines.append(f"  {dep_name}:")
                    new_lines.append(f'    url: "{source}"')
                    if branch:
                        new_lines.append(f'    branch: "{branch}"')
                    deps_added = True
            if not deps_added:
                new_lines.append("dependencies:")
                new_lines.append(f"  {dep_name}:")
                new_lines.append(f'    url: "{source}"')
                if branch:
                    new_lines.append(f'    branch: "{branch}"')
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
        else:
            with open(cfg_file, "a", encoding="utf-8") as f:
                f.write(f'\ndependencies:\n  {dep_name}:\n    url: "{source}"\n')
                if branch:
                    f.write(f'    branch: "{branch}"\n')

    elif ext == ".json":
        data: Dict[str, Any] = {}
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
        if "dependencies" not in data or not isinstance(data["dependencies"], dict):
            data["dependencies"] = {}
        data["dependencies"][dep_name] = dep_info
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    elif ext == ".toml":
        content = ""
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                content = f.read()
        section = f"[dependencies.{dep_name}]"
        if section in content:
            pattern = re.compile(rf"\[dependencies\.{re.escape(dep_name)}\][^\[]*", re.MULTILINE)
            block = f'[dependencies.{dep_name}]\nurl = "{source}"\n'
            if branch:
                block += f'branch = "{branch}"\n'
            content = pattern.sub(block, content, count=1)
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(cfg_file, "a", encoding="utf-8") as f:
                f.write(f'\n[dependencies.{dep_name}]\nurl = "{source}"\n')
                if branch:
                    f.write(f'branch = "{branch}"\n')



def _dependency_build_allowed(dep_name: str, trusted: bool = False) -> bool:
    """Decides whether a dependency's build script may run (roadmap 5.3).

    A build script (``build.py``/``build.sh``/``Makefile``) is arbitrary code
    from a third party.  It only runs when explicitly trusted: ``--trust``,
    ``PENGU_TRUST_ALL=1``, or an interactive "yes".  In a non-interactive shell
    without trust it is skipped with a warning instead of silently executing.
    """
    if trusted:
        return True
    if os.environ.get("PENGU_TRUST_ALL", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    if not sys.stdin.isatty():
        emit(f"     Skipped '{dep_name}' has a build script but was not "
              f"trusted; pass --trust to run it.", file=sys.stderr, level="progress")
        return False
    try:
        answer = input(f"    Trust run the build script of '{dep_name}'? [y/N] ", color="yellow")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in ("y", "yes")


def _run_dependency_build(target_dir: str, dep_name: str, trusted: bool = False) -> bool:
    """Runs the dependency's build script (build.py / build.bat / build.sh / Makefile).

    Args:
        target_dir: Installed dependency directory.
        dep_name: Dependency display name.
        trusted: True when the caller already trusted this dependency (--trust).

    Returns:
        True when a build script was found and executed.
    """
    build_py = os.path.join(target_dir, "build.py")
    build_bat = os.path.join(target_dir, "build.bat")
    build_sh = os.path.join(target_dir, "build.sh")
    makefile = os.path.join(target_dir, "Makefile")

    build_cmd = None
    if os.path.isfile(build_py):
        build_cmd = [sys.executable, "build.py"]
    elif sys.platform == "win32" and os.path.isfile(build_bat):
        build_cmd = ["cmd.exe", "/c", "build.bat"]
    elif sys.platform != "win32" and os.path.isfile(build_sh):
        build_cmd = ["sh", "build.sh"]
    elif os.path.isfile(makefile):
        build_cmd = ["make"]

    if build_cmd:
        if not _dependency_build_allowed(dep_name, trusted=trusted):
            return False
        emit(f"    Building dependency '{dep_name}' with {' '.join(build_cmd)}", color="cyan", level="progress")
        res = subprocess.run(build_cmd, cwd=target_dir, capture_output=True, text=True)
        if res.returncode != 0:
            emit(f"     Warning build script returned code {res.returncode}:\n{res.stderr}", file=sys.stderr, color="yellow", level="warning")
        return True
    return False


def update_project(config_path: Optional[str] = None, verbose: bool = False,
                   trusted: bool = False) -> int:
    """Updates every configured dependency: git pull + re-run build scripts.

    Args:
        config_path: Optional path to pengu config file or project root.
        verbose: True to print the git commands being executed.

    Returns:
        Number of dependencies updated.
    """
    config = ProjectConfig.load(config_path)
    deps = config.dependencies or {}
    if not deps:
        emit("       Update no dependencies configured.", color="yellow", level="progress")
        return 0

    lib_dir = os.path.abspath(os.path.join(config.base_dir, config.lib_dir))
    updated = 0
    for dep_name, info in deps.items():
        if isinstance(info, dict):
            source = info.get("url") or info.get("source") or ""
            branch = info.get("branch")
        else:
            source = str(info or "")
            branch = None
        if not source:
            emit(f"     Skipping dependency '{dep_name}' (no source url configured).", file=sys.stderr, color="yellow", level="progress")
            continue

        target_dir = os.path.join(lib_dir, dep_name)
        if not os.path.isdir(target_dir):
            emit(f"     Skipping dependency '{dep_name}' (not installed at {target_dir}). "
                  f"Run 'pengu add {source}' first.", file=sys.stderr, level="progress")
            continue

        emit(f"    Updating dependency '{dep_name}'", color="cyan", level="progress")

        git_dir = os.path.join(target_dir, ".git")
        if os.path.isdir(git_dir):
            cmd_fetch = ["git", "-C", target_dir, "pull"]
            if branch:
                cmd_fetch = ["git", "-C", target_dir, "pull", "origin", branch]
            if verbose:
                print(f"   $ {' '.join(cmd_fetch)}", file=sys.stderr)
            res = subprocess.run(cmd_fetch, capture_output=True, text=True)
            if res.returncode != 0:
                emit(f"     Warning git pull failed (code {res.returncode}):\n{res.stderr}", file=sys.stderr, color="yellow", level="warning")
            else:
                tail = (res.stdout or res.stderr or "").strip()
                if tail:
                    print(f"   {tail.splitlines()[-1]}")
        else:
            print("   (local copy — nothing to pull)")

        _run_dependency_build(target_dir, dep_name, trusted=trusted)
        updated += 1

    # Refresh pengu.lock so the new commits/tags are recorded (roadmap 4.1.g).
    try:
        _ensure_lockfile(config, verbose=verbose)
    except Exception as exc:  # noqa: BLE001 - a lock failure must not hide the update
        emit(f"     Warning could not refresh pengu.lock: {exc}", file=sys.stderr, color="yellow", level="warning")

    emit(f"       Updated {updated} dependency(ies).", color="green", level="progress")
    return updated


def _dep_cache_root() -> Optional[str]:
    """Root of the global dependency cache (roadmap 4.7); None when disabled."""
    if os.environ.get("PENGU_NO_DEP_CACHE", "").strip().lower() in ("1", "true", "yes", "on"):
        return None
    override = os.environ.get("PENGU_DEP_CACHE", "").strip()
    if override:
        return os.path.abspath(override)
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "pengu", "deps")


def _dep_cache_key(source: str, branch: Optional[str]) -> str:
    raw = f"{source}\0{branch or ''}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _copy_dep_tree(src: str, dst: str) -> None:
    """Copies a dependency, skipping build outputs but keeping ``.git``."""
    if os.path.exists(dst):
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("build", "__pycache__"))


def _restore_from_cache(source: str, branch: Optional[str], target_dir: str) -> bool:
    """Copies a previously downloaded dependency out of the global cache."""
    root = _dep_cache_root()
    if not root:
        return False
    cached = os.path.join(root, _dep_cache_key(source, branch))
    if not os.path.isdir(cached):
        return False
    try:
        _copy_dep_tree(cached, target_dir)
    except OSError:
        return False
    emit(f"    Cached dependency from {cached}", color="cyan", level="progress")
    return True


def _populate_cache(source: str, branch: Optional[str], source_dir: str) -> None:
    """Stores a freshly fetched dependency in the global cache."""
    root = _dep_cache_root()
    if not root or not os.path.isdir(source_dir):
        return
    dest = os.path.join(root, _dep_cache_key(source, branch))
    try:
        os.makedirs(root, exist_ok=True)
        if not os.path.isdir(dest):
            _copy_dep_tree(source_dir, dest)
    except OSError:
        pass


def _vendor_dir(config: "ProjectConfig") -> str:
    return os.path.abspath(os.path.join(config.base_dir, "vendor"))


def _restore_from_vendor(config: "ProjectConfig", name: str, target_dir: str) -> bool:
    """Restores a dependency from ``vendor/<name>`` (offline builds, roadmap 4.6)."""
    vendored = os.path.join(_vendor_dir(config), name)
    if not os.path.isdir(vendored):
        return False
    try:
        _copy_dep_tree(vendored, target_dir)
    except OSError:
        return False
    emit(f"   Vendored dependency '{name}'", color="cyan", level="progress")
    return True


def vendor_dependencies(config: "ProjectConfig", verbose: bool = False) -> str:
    """Copies every installed dependency into ``vendor/`` for offline builds.

    The vendored copies exclude ``build/`` outputs but keep ``.git`` so
    ``pengu upgrade`` still works from a vendored tree.  A fresh clone can then
    restore ``lib/`` without network access (``pengu build --frozen`` restores
    automatically when ``lib/<name>`` is missing).

    Returns:
        The ``vendor/`` directory path.
    """
    from pengu_lock import read_lock, write_lock

    graph = resolve_transitive_dependencies(config, install_missing=False, verbose=verbose)
    out_dir = _vendor_dir(config)
    os.makedirs(out_dir, exist_ok=True)
    copied = 0
    for name in sorted(graph):
        src = os.path.join(config.base_dir, config.lib_dir, name)
        if not os.path.isdir(src):
            continue
        _copy_dep_tree(src, os.path.join(out_dir, name))
        copied += 1
    lock = read_lock(config.base_dir)
    if lock is not None:
        write_lock(out_dir, lock)
    with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            "# vendor/\n\n"
            "Dependency snapshots generated by `pengu vendor`.\n\n"
            "They let a fresh clone build without network access: when `lib/<name>/`\n"
            "is missing, `pengu build` restores it from here (and `--frozen` verifies\n"
            "the recorded commits and content hashes).\n"
        )
    emit(f"    Vendored {copied} dependency(ies) into {out_dir}", color="green", level="progress")
    return out_dir


def add_dependency(
    source: str,
    branch: Optional[str] = None,
    name: Optional[str] = None,
    config_path: Optional[str] = None,
    run_build: bool = True,
    trusted: bool = False,
    _resolve_transitive: bool = True,
    _record_in_manifest: bool = True,
) -> str:
    """Adds an external dependency / binding to the project in lib/<name>/.

    Clones a Git repository or copies a local path into lib/<name>,
    organizes the binding structure, executes any build scripts, and updates pengu.yaml.

    Args:
        source: Git repository URL (https://, git@, etc.) or local directory path.
        branch: Optional git branch or tag to checkout.
        name: Optional custom binding name override.
        config_path: Optional path to pengu config file or project root.
        run_build: Whether to execute build scripts (build.py, build.sh, build.bat, Makefile) if present.

    Returns:
        Path to installed binding directory.
    """
    config = ProjectConfig.load(config_path)
    dep_source = source.strip()

    # 1. Determine binding name
    if name:
        dep_name = name.strip()
    else:
        clean_src = dep_source.rstrip("/\\")
        if clean_src.endswith(".git"):
            clean_src = clean_src[:-4]
        dep_name = os.path.basename(clean_src)
        if not dep_name:
            dep_name = "binding"

    lib_dir = os.path.abspath(os.path.join(config.base_dir, config.lib_dir))
    os.makedirs(lib_dir, exist_ok=True)
    target_dir = os.path.join(lib_dir, dep_name)

    emit(f"    Fetching dependency '{dep_name}' from {dep_source}", color="cyan", level="progress")

    # 2. Check Git URL vs Local directory
    is_git_url = any(dep_source.startswith(p) for p in ("http://", "https://", "git://", "git@", "ssh://")) or dep_source.endswith(".git")

    if is_git_url:
        if os.path.isdir(target_dir):
            if os.path.isdir(os.path.join(target_dir, ".git")):
                emit(f"    Updating existing Git repository in {target_dir}", color="yellow", level="progress")
                cmd_fetch = ["git", "-C", target_dir, "pull"]
                subprocess.run(cmd_fetch, check=False)
            else:
                shutil.rmtree(target_dir, ignore_errors=True)
        if not os.path.isdir(target_dir):
            # Offline/vendor and global-cache hits avoid the network entirely.
            restored = (_restore_from_vendor(config, dep_name, target_dir)
                        or _restore_from_cache(dep_source, branch, target_dir))
            if not restored:
                clone_cmd = ["git", "clone"]
                if branch:
                    clone_cmd.extend(["-b", branch])
                clone_cmd.extend([dep_source, target_dir])
                res = subprocess.run(clone_cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"Git clone failed:\n{res.stderr}\n{res.stdout}")
                _populate_cache(dep_source, branch, target_dir)
    else:
        src_path = os.path.abspath(dep_source)
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Dependency source path '{dep_source}' does not exist.")
        if os.path.abspath(src_path) != os.path.abspath(target_dir):
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, target_dir)
            else:
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy(src_path, target_dir)

    # 3. Standardize internal structure (pengu/, c/, include/, lib/)
    pengu_sub = os.path.join(target_dir, "pengu")
    c_sub = os.path.join(target_dir, "c")
    inc_sub = os.path.join(target_dir, "include")
    lib_sub = os.path.join(target_dir, "lib")
    os.makedirs(pengu_sub, exist_ok=True)
    os.makedirs(c_sub, exist_ok=True)
    os.makedirs(inc_sub, exist_ok=True)
    os.makedirs(lib_sub, exist_ok=True)

    # Copy root .pengu files to pengu/ if they exist only in root
    for item in os.listdir(target_dir):
        item_p = os.path.join(target_dir, item)
        if os.path.isfile(item_p) and item.endswith(".pengu"):
            dest_p = os.path.join(pengu_sub, item)
            if not os.path.exists(dest_p):
                shutil.copy(item_p, dest_p)

    # 4. Run build script if present
    if run_build:
        _run_dependency_build(target_dir, dep_name, trusted=trusted)

    # 5. Update configuration file (skipped for transitive installs: those
    #    belong to their parent's manifest, not to the project's).
    if _record_in_manifest:
        _update_config_dependency(config.base_dir, dep_name, dep_source, branch)

    emit(f"       Added dependency '{dep_name}' to {target_dir}", color="green", level="progress")

    # 6. Pull the dependency's own dependencies (roadmap 4.2).  On a version
    #    conflict the whole add is rolled back, so the project never keeps a
    #    dependency whose graph cannot be resolved.
    if _resolve_transitive:
        try:
            resolve_transitive_dependencies(config, install_missing=True, verbose=False)
        except DependencyConflictError:
            if _record_in_manifest:
                _remove_config_dependency(config.base_dir, dep_name)
            shutil.rmtree(target_dir, ignore_errors=True)
            raise
    return target_dir


def _find_manifest(base_dir: str) -> Optional[str]:
    """Returns the canonical manifest path (existing, or the default to create)."""
    for cand in ("pengu.toml", "Pengu.toml", "pengu.yaml", "pengu.yml", "pengu.json"):
        p = os.path.join(base_dir, cand)
        if os.path.isfile(p):
            return p
    return os.path.join(base_dir, "pengu.toml")


def _read_config_dependency(base_dir: str, dep_name: str) -> Optional[Dict[str, Any]]:
    """Returns the manifest entry of a dependency, or None."""
    manifest = _find_manifest(base_dir)
    if not os.path.isfile(manifest):
        return None
    ext = os.path.splitext(manifest)[1].lower()
    try:
        if ext == ".json":
            with open(manifest, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif ext == ".toml" and tomllib is not None:
            with open(manifest, "rb") as f:
                data = tomllib.load(f)
        else:
            data = _load_yaml_module()
            with open(manifest, "r", encoding="utf-8") as f:
                data = data.safe_load(f) if data is not None else {}
    except Exception:
        return None
    deps = (data or {}).get("dependencies")
    if isinstance(deps, dict):
        entry = deps.get(dep_name)
        if isinstance(entry, dict):
            return entry
    return None


def _remove_config_dependency(base_dir: str, dep_name: str) -> bool:
    """Removes a dependency entry from the manifest. Returns True if it existed."""
    manifest = _find_manifest(base_dir)
    if not os.path.isfile(manifest):
        return False
    ext = os.path.splitext(manifest)[1].lower()
    if ext == ".json":
        with open(manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
        existed = isinstance(data.get("dependencies"), dict) and dep_name in data["dependencies"]
        if existed:
            del data["dependencies"][dep_name]
            with open(manifest, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
        return existed
    if ext == ".toml":
        if tomllib is None:
            return False
        with open(manifest, "rb") as f:
            data = tomllib.load(f)
        deps = data.get("dependencies")
        existed = isinstance(deps, dict) and dep_name in deps
        if existed:
            del deps[dep_name]
            _write_toml_file(manifest, data)
        return existed
    yaml = _load_yaml_module()
    if yaml is None:
        return False
    with open(manifest, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    deps = data.get("dependencies")
    existed = isinstance(deps, dict) and dep_name in deps
    if existed:
        del deps[dep_name]
        with open(manifest, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False)
    return existed


def remove_dependency(name: str, config_path: Optional[str] = None,
                      keep_files: bool = False) -> str:
    """Removes a dependency from lib/<name>/ and from the project manifest.

    Args:
        name: Dependency/binding name (the ``lib/<name>`` directory).
        config_path: Optional path to the project config file or root.
        keep_files: True to only drop the manifest entry, leaving lib/<name>/.

    Returns:
        Path of the removed dependency directory.
    """
    config = ProjectConfig.load(config_path)
    dep_name = (name or "").strip()
    if not dep_name:
        raise ValueError("dependency name is required")
    target_dir = os.path.abspath(os.path.join(config.base_dir, config.lib_dir, dep_name))
    lib_root = os.path.abspath(os.path.join(config.base_dir, config.lib_dir))
    if os.path.commonpath([target_dir, lib_root]) != lib_root:
        raise ValueError(f"refusing to remove '{dep_name}': outside {lib_root}")

    existed_entry = _remove_config_dependency(config.base_dir, dep_name)
    removed_dir = os.path.isdir(target_dir)
    if removed_dir and not keep_files:
        shutil.rmtree(target_dir)
    if not existed_entry and not removed_dir:
        raise FileNotFoundError(
            f"dependency '{dep_name}' is not installed (no {target_dir} and no manifest entry)"
        )
    if keep_files:
        emit(f"     Removed dependency '{dep_name}' from the manifest", color="green", level="progress")
    else:
        emit(f"     Removed dependency '{dep_name}' ({target_dir})", color="green", level="progress")
    return target_dir


def upgrade_dependency(name: str, version: Optional[str] = None,
                       branch: Optional[str] = None,
                       config_path: Optional[str] = None) -> str:
    """Updates one dependency (git pull or checkout of a tag) and its manifest.

    Args:
        name: Dependency/binding name.
        version: Optional git tag / SemVer constraint to record and check out.
        branch: Optional branch override recorded in the manifest.
        config_path: Optional path to the project config file or root.

    Returns:
        Path of the upgraded dependency directory.
    """
    config = ProjectConfig.load(config_path)
    dep_name = (name or "").strip()
    if not dep_name:
        raise ValueError("dependency name is required")
    target_dir = os.path.abspath(os.path.join(config.base_dir, config.lib_dir, dep_name))
    if not os.path.isdir(target_dir):
        raise FileNotFoundError(f"dependency '{dep_name}' is not installed at {target_dir}")

    entry = _read_config_dependency(config.base_dir, dep_name) or {}
    source = str(entry.get("url") or entry.get("source") or "")
    if not source:
        raise ValueError(
            f"dependency '{dep_name}' has no 'url' in the manifest; cannot upgrade"
        )
    is_git = os.path.isdir(os.path.join(target_dir, ".git"))
    if not is_git:
        emit(f"    Skipping '{dep_name}' (local copy, not a git checkout)", color="yellow", level="progress")
        return target_dir

    fetch = subprocess.run(["git", "-C", target_dir, "fetch", "--tags", "--prune"],
                           capture_output=True, text=True)
    if fetch.returncode != 0:
        raise RuntimeError(f"git fetch failed for '{dep_name}':\n{fetch.stderr}")

    ref = version or branch or entry.get("branch")
    if ref:
        checkout = subprocess.run(["git", "-C", target_dir, "checkout", str(ref)],
                                  capture_output=True, text=True)
        if checkout.returncode != 0:
            raise RuntimeError(
                f"git checkout '{ref}' failed for '{dep_name}':\n{checkout.stderr}"
            )
    else:
        pull = subprocess.run(["git", "-C", target_dir, "pull", "--ff-only"],
                              capture_output=True, text=True)
        if pull.returncode != 0:
            raise RuntimeError(f"git pull failed for '{dep_name}':\n{pull.stderr}")

    new_entry: Dict[str, Any] = {"url": source}
    if branch:
        new_entry["branch"] = branch
    elif entry.get("branch"):
        new_entry["branch"] = entry["branch"]
    if version:
        new_entry["version"] = version
    _set_config_dependency(config.base_dir, dep_name, new_entry)
    head = subprocess.run(["git", "-C", target_dir, "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    emit(f"   Upgraded dependency '{dep_name}'"
          + (f" to {version}" if version else (f" to {ref}" if ref else ""))
          + (f" ({head})" if head else ""), level="progress")
    return target_dir


def _set_config_dependency(base_dir: str, dep_name: str, entry: Dict[str, Any]) -> None:
    """Writes a full dependency entry into the manifest (TOML/YAML/JSON)."""
    manifest = _find_manifest(base_dir)
    ext = os.path.splitext(manifest)[1].lower()
    if ext == ".toml":
        if tomllib is None:
            raise RuntimeError("TOML manifests require tomllib/tomli")
        data: Dict[str, Any] = {}
        if os.path.isfile(manifest):
            with open(manifest, "rb") as f:
                data = tomllib.load(f)
        if not isinstance(data.get("dependencies"), dict):
            data["dependencies"] = {}
        data["dependencies"][dep_name] = entry
        _write_toml_file(manifest, data)
        return
    if ext == ".json":
        data = {}
        if os.path.isfile(manifest):
            with open(manifest, "r", encoding="utf-8") as f:
                data = json.load(f)
        if not isinstance(data.get("dependencies"), dict):
            data["dependencies"] = {}
        data["dependencies"][dep_name] = entry
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        return
    yaml = _load_yaml_module()
    if yaml is None:
        raise RuntimeError("YAML manifests require PyYAML")
    data = {}
    if os.path.isfile(manifest):
        with open(manifest, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    if not isinstance(data.get("dependencies"), dict):
        data["dependencies"] = {}
    data["dependencies"][dep_name] = entry
    with open(manifest, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False)


def _manifest_dependencies(base_dir: str) -> Dict[str, Any]:
    """Reads the ``dependencies`` table from a project manifest."""
    manifest = _find_manifest(base_dir)
    if not os.path.isfile(manifest):
        return {}
    ext = os.path.splitext(manifest)[1].lower()
    try:
        if ext == ".json":
            with open(manifest, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif ext == ".toml":
            if tomllib is None:
                return {}
            with open(manifest, "rb") as f:
                data = tomllib.load(f)
        else:
            yaml = _load_yaml_module()
            if yaml is None:
                return {}
            with open(manifest, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    deps = (data or {}).get("dependencies")
    return deps if isinstance(deps, dict) else {}


def _git_tags(url: str) -> List[str]:
    """Remote tag names of a git dependency (empty when not a git remote)."""
    if not url:
        return []
    try:
        res = subprocess.run(["git", "ls-remote", "--tags", "--refs", url],
                             capture_output=True, text=True, timeout=60)
    except Exception:
        return []
    if res.returncode != 0:
        return []
    tags = []
    for line in res.stdout.splitlines():
        parts = line.split("refs/tags/")
        if len(parts) == 2:
            tags.append(parts[1].strip())
    return tags


def _installed_version(path: str) -> Optional[Version]:
    """Version of an installed dependency: nearest git tag, else manifest value."""
    if os.path.isdir(os.path.join(path, ".git")):
        res = subprocess.run(["git", "-C", path, "describe", "--tags", "--abbrev=0"],
                             capture_output=True, text=True)
        if res.returncode == 0:
            v = Version.try_parse(res.stdout.strip())
            if v is not None:
                return v
    entry = _read_config_dependency(os.path.dirname(os.path.dirname(path)),
                                    os.path.basename(path)) or {}
    declared = entry.get("version")
    if isinstance(declared, str):
        try:
            constraints = parse_constraint(declared)
        except Exception:
            return None
        # A constraint is not a concrete version; only an exact/pinned one is.
        for c in constraints:
            if c.op == "=" and c.version is not None:
                return c.version
    return None


def _checkout_matching_tag(path: str, constraint: str, verbose: bool = False) -> Optional[Version]:
    """Checks out the highest installed tag satisfying ``constraint``."""
    res = subprocess.run(["git", "-C", path, "tag", "--list"], capture_output=True, text=True)
    if res.returncode != 0:
        return None
    best = select_version(res.stdout.split(), constraint)
    if best is None:
        subprocess.run(["git", "-C", path, "fetch", "--tags", "--prune"],
                       capture_output=True, text=True)
        res = subprocess.run(["git", "-C", path, "tag", "--list"], capture_output=True, text=True)
        best = select_version(res.stdout.split(), constraint)
    if best is None:
        return None
    tag, ver = best
    co = subprocess.run(["git", "-C", path, "checkout", "--quiet", tag],
                        capture_output=True, text=True)
    if co.returncode == 0:
        if verbose:
            print(f"[pengu] {os.path.basename(path)} -> {tag}")
        return ver
    return None


@dataclass
class DependencyNode:
    """One node of the resolved dependency graph."""
    name: str
    source: str
    constraint: str
    required_by: List[str] = field(default_factory=list)
    resolved_version: Optional[str] = None
    commit: Optional[str] = None
    path: str = ""
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "constraint": self.constraint,
            "required_by": sorted(self.required_by),
            "version": self.resolved_version,
            "commit": self.commit,
            "children": sorted(set(self.children)),
        }


def resolve_transitive_dependencies(
    config: "ProjectConfig",
    install_missing: bool = True,
    max_depth: int = 5,
    verbose: bool = False,
) -> Dict[str, DependencyNode]:
    """Walks the dependency graph, installing/honouring transitive dependencies.

    Forward-only (no backtracking): for each dependency it selects the highest
    installed/remote tag satisfying every collected constraint.  Cycles are
    detected and reported, and incompatible requirements raise
    :class:`DependencyConflictError` (roadmap 4.2, error E0062).

    Returns:
        ``name -> DependencyNode`` for every dependency in the graph.
    """
    lib_root = os.path.abspath(os.path.join(config.base_dir, config.lib_dir))
    graph: Dict[str, DependencyNode] = {}
    resolved: Dict[str, Optional[Version]] = {}
    requirements: Dict[str, List[Requirement]] = {}

    root_deps = _manifest_dependencies(config.base_dir)
    queue: List[Tuple[str, Dict[str, Any], str, int]] = [
        (name, entry, "<root>", 0)
        for name, entry in root_deps.items()
        if isinstance(entry, dict)
    ]
    visiting: List[str] = []

    while queue:
        name, entry, parent, depth = queue.pop(0)
        source = str(entry.get("url") or entry.get("source") or "")
        constraint = str(entry.get("version") or "*")
        branch = entry.get("branch")

        requirements.setdefault(name, []).append(Requirement(
            name=name, constraint=constraint, source=source,
            branch=str(branch) if branch else None, required_by=parent,
        ))

        target = os.path.join(lib_root, name)
        node = graph.get(name)
        if node is None:
            node = DependencyNode(name=name, source=source, constraint=constraint, path=target)
            graph[name] = node
        else:
            if source and not node.source:
                node.source = source
        if parent not in node.required_by:
            node.required_by.append(parent)

        if name in resolved:
            # Already installed: verify the new constraint is compatible.
            ver = resolved[name]
            if ver is not None:
                try:
                    cons = parse_constraint(constraint)
                except Exception:
                    cons = []
                if cons and not satisfies(ver, cons):
                    raise DependencyConflictError(ResolutionConflict(
                        name=name, requirements=requirements[name]))
            if parent not in ("<root>",) and parent in graph:
                graph[parent].children.append(name)
            continue

        if not os.path.isdir(target) and source and _restore_from_vendor(config, name, target):
            pass  # restored offline from vendor/
        elif not os.path.isdir(target) and install_missing and source:
            try:
                add_dependency(source=source, branch=str(branch) if branch else None,
                               name=name, config_path=config.base_dir, run_build=False,
                               _resolve_transitive=False, _record_in_manifest=False)
            except Exception as exc:  # noqa: BLE001 - surface as a clear warning
                emit(f"     Warning could not install '{name}': {exc}",
                      file=sys.stderr, level="warning")
                resolved[name] = None
                continue

        ver: Optional[Version] = None
        if os.path.isdir(target):
            if constraint and constraint != "*" and os.path.isdir(os.path.join(target, ".git")):
                ver = _checkout_matching_tag(target, constraint, verbose=verbose)
            if ver is None:
                ver = _installed_version(target)
        resolved[name] = ver
        node.resolved_version = str(ver) if ver is not None else None
        if os.path.isdir(os.path.join(target, ".git")):
            commit = subprocess.run(["git", "-C", target, "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True).stdout.strip()
            node.commit = commit or None

        if parent != "<root>" and parent in graph:
            graph[parent].children.append(name)

        if depth >= max_depth:
            continue
        for child_name, child_entry in _manifest_dependencies(target).items():
            if not isinstance(child_entry, dict):
                continue
            if child_name in visiting or child_name in resolved:
                continue
            if child_name == name:
                emit(f"     Warning dependency cycle ignored: "
                      f"{name} -> {child_name}", file=sys.stderr, level="warning")
                continue
            queue.append((child_name, child_entry, name, depth + 1))

    return graph


def _same_source(a: str, b: str) -> bool:
    """Compares two dependency sources tolerantly (trailing '/', '.git', case)."""

    def _norm(x: str) -> str:
        x = (x or "").strip().rstrip("/")
        if x.endswith(".git"):
            x = x[:-4]
        return x.replace("\\", "/").lower()

    return _norm(a) == _norm(b)


def verify_project(config_path: Optional[str] = None, verbose: bool = False) -> int:
    """Verifies every installed dependency against ``pengu.lock`` (roadmap 5.3).

    Checks that each locked package is present, that its checked-out commit
    matches the one recorded, and that its content tree still hashes to the
    locked SHA-256.  Returns 0 when everything matches, 1 otherwise.

    Args:
        config_path: Optional path to the config file or project root.
        verbose: Print the per-package detail even when everything matches.
    """
    from pengu_lock import compute_tree_hash, read_lock

    config = ProjectConfig.load(config_path)
    lock = read_lock(config.base_dir)
    if lock is None:
        emit("     Error no pengu.lock found; run `pengu build` first.",
              file=sys.stderr, level="error")
        return 1

    problems: List[str] = []
    for pkg in lock.packages:
        dep_dir = os.path.join(config.base_dir, config.lib_dir, pkg.name)
        if not os.path.isdir(dep_dir):
            problems.append(f"{pkg.name}: not installed at {dep_dir}")
            continue
        if pkg.source and os.path.isdir(os.path.join(dep_dir, ".git")):
            # A dependency replaced by a different repository of the same name
            # would otherwise pass verification (roadmap 6.0.e).
            origin = subprocess.run(["git", "-C", dep_dir, "remote", "get-url", "origin"],
                                    capture_output=True, text=True).stdout.strip()
            if origin and not _same_source(origin, pkg.source):
                problems.append(f"{pkg.name}: origin '{origin}' != locked '{pkg.source}'")
        if pkg.commit and os.path.isdir(os.path.join(dep_dir, ".git")):
            head = subprocess.run(["git", "-C", dep_dir, "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()
            if head and not head.startswith(pkg.commit[:7]) and not pkg.commit.startswith(head[:7]):
                problems.append(f"{pkg.name}: commit {head[:12]} != locked {pkg.commit[:12]}")
        if pkg.sha256:
            actual = compute_tree_hash(dep_dir)
            if actual != pkg.sha256:
                problems.append(f"{pkg.name}: content sha256 {actual[:12]}… != locked {pkg.sha256[:12]}…")
        if verbose and not problems:
            emit(f"  ok {pkg.name} {pkg.version} {pkg.commit[:12] if pkg.commit else ''}", color="green", level="progress")

    if problems:
        emit(f"     Failed pengu.lock verification ({len(problems)} problem(s)):",
              file=sys.stderr, level="error")
        for prob in problems:
            print(f"  - {prob}", file=sys.stderr)
        return 1
    emit(f"   Verified {len(lock.packages)} package(s) match pengu.lock", color="green", level="progress")
    return 0


def print_dependency_tree(config: "ProjectConfig", as_json: bool = False) -> int:
    """Prints the resolved dependency graph (`pengu tree` / `metadata --json`).

    The JSON form is a **single line** (JSON Lines), matching every other
    ``--json`` command so a consumer can parse stdout line by line (item 4.7).
    """
    graph = resolve_transitive_dependencies(config, install_missing=False, verbose=False)
    if as_json:
        print(json.dumps({
            "type": "tree",
            "project": config.name,
            "version": config.version,
            "dependencies": [n.to_dict() for n in sorted(graph.values(), key=lambda n: n.name)],
        }, ensure_ascii=False))
        return 0

    roots = [
        name for name, node in graph.items()
        if node.required_by == ["<root>"] or "<root>" in node.required_by
    ]
    if not roots:
        emit(f"   {config.name} — no dependencies", color="cyan", level="progress")
        return 0

    emit(f"{config.name} v{config.version}", color="cyan", level="progress")

    def render(name: str, prefix: str, is_last: bool, seen: set) -> None:
        node = graph.get(name)
        if node is None:
            return
        connector = "└── " if is_last else "├── "
        version = node.resolved_version or node.constraint or "?"
        print(f"{prefix}{connector}{name} {version}"
              + (f" ({node.commit})" if node.commit else ""))
        if name in seen:
            print(f"{prefix}    (cycle)")
            return
        seen = seen | {name}
        children = sorted(set(node.children))
        for i, child in enumerate(children):
            render(child, prefix + ("    " if is_last else "│   "), i == len(children) - 1, seen)

    for i, root in enumerate(sorted(roots)):
        render(root, "", i == len(roots) - 1, set())
    return 0


def init_project(
    name: str = "my_game",
    output_type: Optional[str] = None,
    links: Optional[List[str]] = None,
    cc: str = "gcc",
    output_name: Optional[str] = None,
    target_dir: Optional[str] = None,
    manifest_format: str = "toml",
    template: str = "exe",
) -> str:
    """Initializes a new PenguScript project directory with Cargo-style structure (src/, lib/, include/, c/).

    Args:
        name: Project directory name.
        output_type: Target artifact type ('exe', 'c', 'obj', 'static', 'shared').
        links: Optional list of library names to link (-l).
        cc: C compiler to configure.
        output_name: Optional custom output artifact name.
        target_dir: Optional destination base directory.
        manifest_format: ``"toml"`` (canonical, roadmap 4.11) or ``"yaml"``.
        template: Template flavour (``"exe"``, ``"cli"``, ``"lib"``, ``"game"``).

    Returns:
        Path to initialized project directory.
    """
    # `--template lib` produces a static library unless the caller explicitly
    # chose an output type (roadmap 4.10).
    out_t = OutputType.from_string(output_type or "exe")
    if (template or 'exe').strip().lower() == 'lib' and output_type is None:
        out_t = OutputType.STATIC
    out_name = output_name or name
    base_root = target_dir or os.getcwd()
    proj_dir = os.path.abspath(os.path.join(base_root, name)) if target_dir else os.path.abspath(name)

    src_dir = os.path.join(proj_dir, "src")
    lib_dir = os.path.join(proj_dir, "lib")
    inc_dir = os.path.join(proj_dir, "include")
    c_dir = os.path.join(proj_dir, "c")
    assets_dir = os.path.join(proj_dir, "assets")

    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(inc_dir, exist_ok=True)
    os.makedirs(c_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)

    links_list = [str(l) for l in (links or [])]
    # The game template needs raylib on the link line; without it every raylib
    # import fails with "undefined reference" (roadmap 6.2 / BUG-6.5).
    if (template or "exe").strip().lower() == "game" and "raylib" not in links_list:
        links_list.append("raylib")
    links_formatted = json.dumps(links_list)

    yaml_content = f"""project:
  name: "{name}"
  version: "0.1.0"
  entry: "src/main.pengu"
  output: "{out_t.value}"
  output_name: "{out_name}"

build:
  src_dir: "src"
  lib_dir: "lib"
  include_dir: "include"
  c_dir: "c"
  build_dir: "build"
  includes: []
  links: {links_formatted}
  lib_dirs: []
  include_dirs: []
  cflags: ["-Wall", "-std=c11"]
  ldflags: []
  defines: []
  cc: "{cc}"

assets:
  dir: "assets"
  module: "arca"
  embed: true

dependencies: {{}}

profiles:
  debug:
    cflags: ["-g", "-O0", "-Wall"]
    defines: ["DEBUG"]
  release:
    cflags: ["-O3", "-DNDEBUG"]
    defines: ["NDEBUG"]
"""

    # TOML is the canonical manifest (roadmap 4.11); YAML stays available with
    # `--format yaml` for backwards compatibility, and `ProjectConfig.load` reads
    # both (preferring pengu.toml when both exist).
    toml_links = ", ".join(json.dumps(str(l)) for l in links_list)
    toml_content = f"""[project]
name = {json.dumps(name)}
version = "0.1.0"
entry = "src/main.pengu"
output = {json.dumps(out_t.value)}
output_name = {json.dumps(out_name)}

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
includes = []
links = [{toml_links}]
lib_dirs = []
include_dirs = []
cflags = ["-Wall", "-std=c11"]
ldflags = []
defines = []
cc = {json.dumps(cc)}

[assets]
dir = "assets"
module = "arca"
embed = true

[dependencies]

[profiles.debug]
cflags = ["-g", "-O0", "-Wall"]
defines = ["DEBUG"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG"]
defines = ["NDEBUG"]
"""

    if out_t == OutputType.EXE:
        main_content = f"""weave main into void:
  var msg as string is "Hello from {name}!"
  calling print with msg
"""
    elif out_t == OutputType.C:
        main_content = f"""weave main into void:
  var msg as string is "Hello from C bundle {name}!"
"""
    elif out_t == OutputType.OBJ:
        main_content = """weave add with a as int, b as int into int:
  return a + b
"""
    elif out_t == OutputType.STATIC:
        main_content = f"""# Static library {name}
weave add with a as int, b as int into int:
  return a + b

weave sub with a as int, b as int into int:
  return a - b
"""
    elif out_t == OutputType.SHARED:
        main_content = f"""# Shared library {name} - exported
weave add with a as int, b as int into int:
  return a + b
"""
    else:
        main_content = f"""weave main into void:
  var msg as string is "Hello from {name}!"
  calling print with msg
"""

    # Template flavours (roadmap 4.10).  `exe` is the historical default; the
    # others only change the generated entry point (and, for `lib`, the output
    # type when the caller did not choose one explicitly).
    template_name = (template or "exe").strip().lower()
    if template_name == "lib":
        # A library template ships a smoke test so `pengu test` proves the
        # exports work (roadmap 6.2 / BUG-6.7).
        main_content = """import std.ward

## Adds two integers.
weave add with a as int, b as int into int:
  return a + b

## Subtracts `b` from `a`.
weave sub with a as int, b as int into int:
  return a - b

test "add works":
  calling ward.assert_eq_int with (calling add with 2, 3), 5

test "sub works":
  calling ward.assert_eq_int with (calling sub with 5, 3), 2
"""
    elif template_name == "cli":
        # A real CLI skeleton: typed options parsed with std.invoke from the
        # process arguments (roadmap 6.2 / BUG-6.6).
        main_content = f"""import std.invoke
import std.rites
import std.spark

## Builds the argument parser for {name}.
weave build_parser into invoke.Parser:
  var p as invoke.Parser is calling invoke.new_parser with "{name}", "TODO: describe {name}"
  calling p.add_flag with "verbose", "v", "Enable verbose output", false
  calling p.add_option with "output", "o", "Write the result to FILE", false, ""
  calling p.add_positional with "input", "Input file to process", false, ""
  return p

## Entry point: parses the command line and reports what it understood.
weave main into int:
  var parser as invoke.Parser is calling build_parser
  var argv as list of string is calling rites.get_args
  var res as invoke.ParseResult is calling parser.parse with argv
  if calling res.get_bool_or with "verbose", false:
    calling spark.println with "verbose: on"
  var out as string is calling res.get_or with "output", ""
  if out != "":
    calling spark.println with "output -> {{out}}"
  var source as string is calling res.get_or with "input", ""
  if source != "":
    calling spark.println with "input  -> {{source}}"
  return 0
"""
    elif template_name == "game":
        # A real window loop: the roadmap's acceptance criterion is that
        # `pengu run` opens a window (roadmap 6.2 / BUG-6.4, BUG-6.5).  raylib is
        # linked through the generated manifest.
        main_content = f"""import std.ffi
import std.raylib

## Entry point: opens a window and runs the frame loop until it is closed.
weave main into int:
  var title as ref to char is calling ffi.cstr_from_string with "Hello from {name}!"
  calling raylib.InitWindow with 800, 450, title
  calling raylib.SetTargetFPS with 60

  while not calling raylib.WindowShouldClose:
    calling raylib.BeginDrawing
    calling raylib.ClearBackground with raylib.RAYWHITE
    calling raylib.DrawText with title, 190, 200, 20, raylib.LIGHTGRAY
    calling raylib.EndDrawing

  calling raylib.CloseWindow
  return 0
"""

    gitignore_content = """build/
*.o
*.a
*.lib
*.so
*.dylib
*.dll
*.exe
# src/arca.pengu is committed intentionally so IDE navigation works
# on fresh clones. Remove this comment if you prefer to regenerate it.
"""

    assets_readme_content = """# Assets

Files placed here are embedded into the binary by `pengu build` / `pengu run`
(when `assets.embed` is `true`) or read from disk at runtime
(when `assets.embed` is `false`).

The generator produces `src/arca.pengu` — import it from your code:

    import arca

    weave main into int:
        let icon_bytes is calling arca.bytes with "icon.png"
        return 0

Run `pengu assets --list` to see the current embedded assets.
"""

    manifest_name = "pengu.toml" if manifest_format == "toml" else "pengu.yaml"
    readme_content = f"""# {name}

A PenguScript v{PENGU_VERSION} project targeting `{out_t.value}` output.

## Project Structure

```
{name}/
├── {manifest_name:<17s} # Project & build configuration
├── src/                # PenguScript source files
│   └── main.pengu      # Main entry point
├── assets/             # Project assets (embedded via arca)
├── lib/                # External bindings & dependencies
├── include/            # C header files (.h)
├── c/                  # C glue/source files (.c)
└── build/              # Generated build artifacts
```

## Building and Running

```bash
# Add an external binding or library
pengu add <git-url-or-local-path>

# Build in debug profile
pengu build

# Build optimized release profile
pengu build --profile release

# Run executable target
pengu run

# Clean build artifacts
pengu clean
```
"""

    with open(os.path.join(proj_dir, "pengu.toml" if manifest_format == "toml" else "pengu.yaml"),
              "w", encoding="utf-8") as f:
        f.write(toml_content if manifest_format == "toml" else yaml_content)
    with open(os.path.join(src_dir, "main.pengu"), "w", encoding="utf-8") as f:
        f.write(main_content)
    with open(os.path.join(assets_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(assets_readme_content)
    with open(os.path.join(proj_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    with open(os.path.join(proj_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    emit(f"     Created {out_t.value} project '{name}' at {proj_dir}", color="green", level="progress")
    if (template or "exe").strip().lower() == "game":
        emit("       Note the 'game' template links raylib; "
              "build it with `python build_runtime.py` if `pengu run` reports "
              "missing raylib symbols.", file=sys.stderr, level="warning")
    return proj_dir


def _cc_version(cc: str) -> Optional[str]:
    """First line of ``<cc> --version``, or None when the compiler is unusable."""
    try:
        res = subprocess.run([cc, "--version"], capture_output=True, text=True,
                             timeout=5)
        if res.returncode == 0:
            first = (res.stdout or res.stderr or "").strip().splitlines()
            if first:
                return first[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def doctor_report(as_json: bool = False) -> int:
    """Reports the health of the toolchain (used by ``pengu doctor``)."""
    import platform

    def _writable(path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".pengu_probe")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("")
            os.unlink(probe)
            return True
        except OSError:
            return False

    runtime = find_runtime_header()
    std_dir = None
    try:
        dirs = std_dirs()
        std_dir = str(dirs[0]) if dirs else None
    except Exception:
        std_dir = None
    tcc_path = find_tcc()
    # A shared PCH shipped next to the runtime header (build_runtime.py / release).
    shared_pch = None
    try:
        for directory in runtime_include_dirs():
            cand = os.path.join(str(directory), "pengu_runtime.h.gch")
            if os.path.isfile(cand):
                shared_pch = cand
                break
    except Exception:
        shared_pch = None
    # The system compiler behind TCC: what 'pengu build' uses when TCC is absent
    # or rejects a source.  Prefer an explicit override, then gcc, then clang/cc.
    cc_name = (os.environ.get("PENGU_DEV_CC")
               or shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
               or "gcc")
    info = {
        "pengu": PENGU_VERSION,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "cc": cc_name,
        "cc_version": _cc_version(cc_name),
        "tcc": tcc_path,
        "tcc_version": tcc_version(tcc_path) if tcc_path else None,
        "pch": shared_pch,
        "runtime_header": str(runtime) if runtime else None,
        "std_dir": std_dir,
        "cache_root": cache_root(),
        "cache_writable": _writable(cache_root()),
        "cache_disabled": cache_disabled(),
        "runtime_libs": [str(p) for p in runtime_lib_dirs()],
    }
    problems = []
    if not info["cc_version"]:
        problems.append(f"C compiler '{cc_name}' not found or not executable")
    if not runtime:
        problems.append("pengu_runtime.h not found (run build_runtime.py)")
    if not std_dir:
        problems.append("std/ directory not found")
    if not info["cache_writable"] and not info["cache_disabled"]:
        problems.append(f"cache directory is not writable: {info['cache_root']}")
    try:
        libs = runtime_lib_dirs()
        if not any(os.path.isfile(os.path.join(str(d), "libpengu_runtime.a")) for d in libs):
            problems.append("libpengu_runtime.a not built (run build_runtime.py)")
    except Exception:
        pass
    info["problems"] = problems

    if as_json:
        print(json.dumps(info))
        return 1 if problems else 0

    def row(label: str, value: object) -> None:
        print(f"  {label:<18} {value}")

    emit("PenguScript doctor", color="cyan", level="progress")
    row("version", info["pengu"])
    row("python", f"{info['python']} ({'frozen bundle' if info['frozen'] else 'source checkout'})")
    row("platform", info["platform"])
    row("C compiler", f"{info['cc']} — {info['cc_version']}" if info["cc_version"]
        else f"{info['cc']} — NOT FOUND")
    row("tcc", f"{tcc_path} ({info['tcc_version']})" if tcc_path else "not available (falls back to gcc/clang)")
    row("pch (shared)", shared_pch or "absent (opt-in; build_runtime.py generates it)")
    row("runtime header", runtime or "MISSING")
    row("std/", std_dir or "MISSING")
    row("cache root", cache_root())
    row("cache writable", info["cache_writable"])
    if cache_disabled():
        row("cache", "disabled by PENGU_CACHE=0")
    for line in cache_summary():
        print(f"  {line}")
    if problems:
        emit("problems:", color="red", level="progress")
        for prob in problems:
            print(f"  - {prob}")
        return 1
    emit("  everything looks good", color="green", level="progress")
    return 0


def expand_script(script: str, output: Optional[str] = None,
                  defines: Optional[List[str]] = None,
                  verbose: bool = False) -> int:
    """Prints the generated ``bundle.c`` of a script (no project tree changes)."""
    script_abs = os.path.abspath(script)
    if not os.path.isfile(script_abs):
        raise FileNotFoundError(f"Script not found: {script}")
    out_name = os.path.splitext(os.path.basename(script_abs))[0]
    tmp = tempfile.mkdtemp(prefix=f"pengu_expand_{out_name}_")
    try:
        cfg = ProjectConfig(
            entry=script_abs,
            base_dir=os.getcwd(),
            output=OutputType.C,
            output_name=out_name,
            name=out_name,
            links=["pengu_runtime"],
            build_dir=tmp,
        )
        if defines:
            cfg.defines = list(cfg.defines or []) + defines
        builder = PenguBuilder(cfg)
        builder.entry_as_main = True
        builder.verbose = verbose
        bundle_path, _ = builder.bundle()
        text = Path(bundle_path).read_text(encoding="utf-8")
        if output:
            Path(output).write_text(text, encoding="utf-8")
            print(f"wrote {output} ({len(text.splitlines())} lines, {len(text)} bytes)")
        else:
            sys.stdout.write(text)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def time_script(script: str, defines: Optional[List[str]] = None,
                cc: Optional[str] = None, script_args: Optional[List[str]] = None,
                use_cache: bool = True, no_dce: bool = False) -> int:
    """Runs a script and reports the time spent in every phase."""
    import platform
    t_start = time.time()
    script_abs = os.path.abspath(script)
    base_dir = os.getcwd()
    out_name = os.path.splitext(os.path.basename(script_abs))[0]
    tmp = tempfile.mkdtemp(prefix=f"pengu_time_{out_name}_")
    phases: Dict[str, float] = {}
    prev_no_dce = os.environ.get("PENGU_NO_DCE")
    if no_dce:
        os.environ["PENGU_NO_DCE"] = "1"
    try:
        cfg = ProjectConfig(
            entry=script_abs,
            base_dir=base_dir,
            output=OutputType.EXE,
            output_name=out_name,
            name=out_name,
            links=["pengu_runtime"],
            build_dir=tmp,
        )
        if defines:
            cfg.defines = list(cfg.defines or []) + defines
        configured_cc = cfg.cc or cc or "gcc"
        cfg.cc = pick_dev_compiler(configured_cc)
        t_imports = time.time()
        try:
            from pengu_cache import resolve_module_list_cached
            from pengu_parser.pengu_parser import PenguParser as _P
            from pengu_parser.pengu_symbols import resolve_imports as _ri
            module_order = resolve_module_list_cached(
                script_abs, lambda: _ri(base_dir, script_abs, _P()))
        except Exception:
            module_order = [script_abs]
        phases["resolve imports"] = time.time() - t_imports

        builder = PenguBuilder(cfg)
        builder.entry_as_main = True
        if os.path.basename(cfg.cc).lower() != os.path.basename(configured_cc).lower():
            builder.fallback_cc = configured_cc
        t_build = time.time()
        artifact, _ = builder.compile()
        phases["total build"] = time.time() - t_build
        for key, label in (("dce", "dead-code elim"), ("check", "parse + check"),
                           ("codegen", "codegen"), ("cc", "C compiler (incl. link)")):
            if key in builder.timings:
                phases[label] = builder.timings[key]
        if "bundle_lines" in builder.timings:
            phases["bundle.c"] = 0.0
        t_run = time.time()
        rc = subprocess.run([artifact] + list(script_args or []), cwd=base_dir).returncode
        phases["run"] = time.time() - t_run
        phases["TOTAL"] = time.time() - t_start
        emit("\nphase timings", color="cyan", level="progress")
        for label, seconds in phases.items():
            if label == "bundle.c":
                print(f"  {label:<24} {builder.timings.get('bundle_lines', 0)} lines, "
                      f"{builder.timings.get('bundle_bytes', 0) / 1024:.1f} KB")
                continue
            print(f"  {label:<24} {seconds * 1000:8.1f} ms")
        print(f"  {'modules':<24} {len(module_order)}")
        print(f"  {'compiler':<24} {cfg.cc} ({platform.system()})")
        if builder.timings.get("dce_dropped"):
            print(f"  {'DCE pruned':<24} {builder.timings['dce_dropped']} weave(s) "
                  f"({builder.timings.get('dce_before', 0)} -> "
                  f"{builder.timings.get('dce_after', 0)})")
        return rc
    finally:
        if no_dce:
            if prev_no_dce is None:
                os.environ.pop("PENGU_NO_DCE", None)
            else:
                os.environ["PENGU_NO_DCE"] = prev_no_dce
        shutil.rmtree(tmp, ignore_errors=True)


def eval_expression(expression: str, defines: Optional[List[str]] = None,
                    cc: Optional[str] = None, no_cache: bool = False) -> int:
    """Runs a one-liner expression through a generated temporary script."""
    # Explicit concatenation, never an f-string: `expression` may legitimately
    # contain '{' or '}' (`pengu eval '"{"'`, `pengu eval 'my_map{"k"}'`), and an
    # f-string would either fail or mangle the braces.  Binding the expression
    # first also keeps nested string literals valid.
    script = (
        "import std.spark\n"
        "\n"
        "weave main into int:\n"
        "    var __value is " + expression + "\n"
        '    calling spark.println with "{__value}"\n'
        "    return 0\n"
    )
    tmp = tempfile.mkdtemp(prefix="pengu_eval_")
    try:
        path = os.path.join(tmp, "eval.pengu")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(script)
        return run_script(path, defines=defines, cc=cc, no_cache=no_cache,
                          ephemeral=True, quiet=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def watch_script(script: str, defines: Optional[List[str]] = None,
                 cc: Optional[str] = None, keep: bool = False,
                 interval: float = 0.4) -> int:
    """Re-runs a script whenever it (or one of its imports) changes."""
    script_abs = os.path.abspath(script)
    base_dir = os.getcwd()
    try:
        from pengu_parser.pengu_parser import PenguParser as _P
        from pengu_parser.pengu_symbols import resolve_imports as _ri
        watched = _ri(base_dir, script_abs, _P())
    except Exception:
        watched = [script_abs]

    def snapshot() -> Dict[str, float]:
        stamps = {}
        for path in list(watched) + [script_abs]:
            try:
                stamps[path] = os.path.getmtime(path)
            except OSError:
                stamps[path] = 0.0
        return stamps

    emit(f"   Watching {os.path.basename(script_abs)} "
          f"({len(watched)} module(s)); Ctrl-C to stop", level="progress")
    last = snapshot()
    try:
        while True:
            rc = run_script(script_abs, defines=defines, cc=cc, keep=keep)
            emit(f"   exit={rc}; waiting for changes…", color="dim", level="progress")
            while True:
                time.sleep(interval)
                current = snapshot()
                if current != last:
                    last = current
                    emit("    Change detected, rebuilding", color="yellow", level="progress")
                    try:
                        from pengu_parser.pengu_parser import PenguParser as _P2
                        from pengu_parser.pengu_symbols import resolve_imports as _ri2
                        watched = _ri2(base_dir, script_abs, _P2())
                    except Exception:
                        pass
                    break
    except KeyboardInterrupt:
        emit("\n   stopped", color="dim", level="progress")
        return 0


def _consume_script_args(raw: Optional[List[str]]) -> List[str]:
    """Strips argparse's leading '--' from the script argument list.

    With ``nargs=argparse.REMAINDER`` the separator itself is part of the list;
    ``pengu run x.pengu -- --flag`` must hand ``--flag`` (not ``-- --flag``) to
    the script, which reads it through ``std.rites.get_args``.
    """
    args = list(raw or [])
    if args and args[0] == "--":
        args = args[1:]
    return args


def run_project(config_path: Optional[str] = None, profile: str = "debug", test: bool = False,
                defines: Optional[List[str]] = None, cc: Optional[str] = None,
                verbose: bool = False, pch: bool = False, no_dce: bool = False,
                strict_c99: bool = False, target_compiler: str = "",
                target: str = "", locked: bool = False, frozen: bool = False,
                release_unsafe: bool = False,
                deny_deprecated: bool = False) -> int:
    """Builds and runs binary if output target is executable.

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        test: True to compile integrated unit tests in --test mode.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override.
        verbose: True to print module order, C commands and phase timings.
        pch: True to precompile pengu_runtime.h for this build.
        no_dce: True to keep every std/lib weave in bundle.c.

    Returns:
        Process exit code.
    """
    config = ProjectConfig.load(config_path, profile=profile)
    if cc:
        config.cc = cc
    artifact = build_project(config_path, profile=profile, test=test, defines=defines,
                             cc=cc, verbose=verbose, pch=pch, no_dce=no_dce,
                             strict_c99=strict_c99, target_compiler=target_compiler,
                             target=target, locked=locked, frozen=frozen,
                             release_unsafe=release_unsafe)
    if config.output == OutputType.EXE and os.path.isfile(artifact):
        emit(f"     Running {artifact}\n", color="cyan", level="progress")
        sys.stdout.flush()
        sys.stderr.flush()
        res = subprocess.run([artifact], cwd=config.base_dir)
        return res.returncode
    return 0


def run_script(script: str, defines: Optional[List[str]] = None,
               cc: Optional[str] = None, verbose: bool = False,
               keep: bool = False, no_cache: bool = False,
               clear_cache: bool = False, ephemeral: bool = False,
               script_args: Optional[List[str]] = None,
               quiet: bool = False, no_pch: bool = True,
               no_dce: bool = False, strict_c99: bool = False,
               target_compiler: str = "", target: str = "",
               locked: bool = False, frozen: bool = False,
               release_unsafe: bool = False,
               deny_deprecated: bool = False) -> int:
    """Compiles and runs a standalone .pengu file directly (script mode).

    The script itself is compiled as the entry point with the compile-time
    'main' variable set to true, so 'when main:' blocks inside it are emitted.
    Any module the script imports is compiled with 'main' false, regardless of
    this script's own mode.

    By default the *binary* is cached under ``~/.cache/pengu/scripts/<key>``
    (keyed by content hashes), nothing is written to the project's ``build/``
    and the temporary build directory is removed afterwards:

    ``--keep``       build in ``build/<name>_run/`` and keep it (old behaviour)
    ``--ephemeral``  build in a fresh temp dir and never populate the cache
    ``--no-cache``   ignore the cache (read and write) for this run
    ``--clear-cache`` wipe the script cache before running

    Args:
        script: Path to the .pengu file to execute.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override (e.g. 'clang').
        verbose: True to print module order, C commands and phase timings.
        keep: Compile in ``build/<name>_run`` and keep the artefacts.
        no_cache: Bypass the binary cache for this invocation.
        clear_cache: Empty the script cache before running.
        ephemeral: Use a throw-away temp directory and do not cache the binary.
        script_args: Extra arguments forwarded to the script (``pengu run x -- a``).
        quiet: Suppress the progress banner (errors still go to stderr).

    Returns:
        Process exit code of the executed binary.
    """
    script_abs = os.path.abspath(script)
    if not os.path.isfile(script_abs):
        raise FileNotFoundError(f"Script not found: {script}")
    if not script_abs.endswith(".pengu"):
        raise ValueError(f"Not a PenguScript file: {script}")

    def say(message: str, **kwargs) -> None:
        """Progress line for script mode; the `quiet` parameter wins."""
        if quiet:
            return
        emit(message, **kwargs, level="progress")

    if clear_cache:
        removed = clear_script_cache(verbose=verbose)
        say(f"    Cleared {removed} cached script(s)", color="cyan")

    base_dir = os.getcwd()
    rel = os.path.relpath(script_abs, base_dir)
    entry = rel if not rel.startswith("..") else script_abs
    out_name = os.path.splitext(os.path.basename(script_abs))[0]

    cfg = ProjectConfig(
        entry=entry,
        base_dir=base_dir,
        output=OutputType.EXE,
        output_name=out_name,
        name=out_name,
        assets_dir="",
        # 'pengu run script.pengu' needs the runtime archive: the string /
        # container helpers it calls live in libpengu_runtime.a.
        links=["pengu_runtime"],
    )
    if defines:
        cfg.defines = list(cfg.defines or []) + defines
    if cc:
        cfg.cc = cc
    if strict_c99:
        cfg.strict_c99 = True
    if target_compiler:
        cfg.target_compiler = target_compiler
    if target:
        cfg.target = target
    cfg.release_unsafe = bool(release_unsafe)
    cfg.deny_deprecated = bool(deny_deprecated)
    _set_release_unsafe(cfg.release_unsafe)
    # A standalone script rarely has dependencies, but honour the lock flags when it does.
    if locked or frozen:
        _ensure_lockfile(cfg, locked=locked, frozen=frozen)

    # --- cache lookup -----------------------------------------------------
    # Resolving the import graph only parses the modules (no semantic checks),
    # and the parser tables are cached, so this costs a few milliseconds.
    module_order: List[str] = []
    try:
        from pengu_cache import resolve_module_list_cached
        from pengu_parser.pengu_parser import PenguParser

        from pengu_parser.pengu_symbols import resolve_imports as _resolve_imports3
        from pengu_parser.pengu_parser import PenguParser as _PenguParser2

        def _resolve() -> List[str]:
            return _resolve_imports3(base_dir, script_abs, _PenguParser2())

        module_order = resolve_module_list_cached(script_abs, _resolve)
    except Exception:
        module_order = [script_abs]
    if script_abs not in module_order:
        module_order.append(script_abs)

    # A development build prefers TCC ('pengu run' is throw-away or cached, so
    # compile speed matters more than codegen quality).  Keep the project's
    # compiler around: it is the fallback when TCC rejects the bundle.
    configured_cc = cfg.cc or "gcc"
    dev_cc = pick_dev_compiler(configured_cc)
    cfg.cc = dev_cc

    use_cache = not no_cache and not ephemeral and not cache_disabled()
    cache_key: Optional[str] = None
    # '--keep' exists to inspect the generated C, so it always rebuilds (but it
    # still refreshes the cache entry).
    use_lookup = use_cache and not keep
    if use_cache:
        try:
            include = find_runtime_header()
        except Exception:
            include = None
        cache_key = script_cache_key(
            script_abs,
            module_order,
            version=PENGU_VERSION,
            profile="debug",
            cc=dev_cc,
            defines=cfg.defines,
            links=cfg.links,
            cflags=cfg.cflags,
            runtime_header=str(include) if include else None,
            # DCE and the Phase 2 portability knobs are build options: they must
            # not reuse (or pollute) the entry of a build made with other flags.
            extra_digests=[
                d for d in (
                    "dce=off" if no_dce else None,
                    "release-unsafe" if getattr(cfg, "release_unsafe", False) else None,
                    (f"env-cflags={os.environ.get('PENGU_CFLAGS', '').strip()}"
                     if os.environ.get("PENGU_CFLAGS", "").strip() else None),
                    "strict-c99" if getattr(cfg, "strict_c99", False) else None,
                    f"target={cfg.target_compiler}" if getattr(cfg, "target_compiler", "") else None,
                    f"triple={cfg.target}" if getattr(cfg, "target", "") else None,
                ) if d
            ] or None,
        )
        cached = lookup_cached_binary(cache_key) if use_lookup else None
        if cached:
            if verbose:
                print(f"[pengu] cache hit {cache_key} -> {cached}")
            say("    Finished (cached)", color="green")
            say(f"     Running {cached}\n", color="cyan")
            sys.stdout.flush()
            sys.stderr.flush()
            return subprocess.run([cached] + list(script_args or []), cwd=base_dir).returncode
        if verbose:
            print(f"[pengu] cache miss {cache_key} (cc={dev_cc})")

    # --- build ------------------------------------------------------------
    # '--keep' reproduces the historical layout; everything else builds in a
    # throw-away directory so the project tree stays clean.
    build_root: Optional[str] = None
    if keep:
        cfg.build_dir = os.path.join("build", f"{out_name}_run")
    else:
        build_root = tempfile.mkdtemp(prefix=f"pengu_run_{out_name}_")
        cfg.build_dir = build_root

    t0 = time.time()
    say(f"   Scripting {os.path.basename(script_abs)}", color="cyan")
    # DCE is decided when PenguCodegen is constructed (it reads PENGU_NO_DCE), so
    # the flag must be in place before the builder runs and restored afterwards:
    # the toolchain is also imported as a library from long-lived processes.
    prev_no_dce = os.environ.get("PENGU_NO_DCE")
    if no_dce:
        os.environ["PENGU_NO_DCE"] = "1"
    try:
        builder = PenguBuilder(cfg)
        builder.is_test_mode = False
        builder.entry_as_main = True
        builder.verbose = verbose
        builder.dev_fast_flags = True
        builder.use_pch = not no_pch
        # `pengu run --deny-deprecated script.pengu` must mean the same as for a
        # project; without this the flag was silently ignored (roadmap 6.0.d).
        enforce_deny_deprecated(builder, json_output=False)
        if os.path.basename(dev_cc).lower() != os.path.basename(configured_cc).lower():
            builder.fallback_cc = configured_cc
        try:
            artifact, is_cached = builder.compile()
            elapsed = time.time() - t0
            if is_cached:
                say(f"    Finished (cached) in {elapsed:.2f}s -> {artifact}", color="green")
            else:
                say(f"    Finished in {elapsed:.2f}s -> {artifact}", color="green")

            if cache_key and not ephemeral:
                stored = store_cached_binary(cache_key, artifact)
                if stored and verbose:
                    print(f"[pengu] cached binary -> {stored}")

            run_target = artifact
            if cache_key and not ephemeral:
                run_target = lookup_cached_binary(cache_key) or artifact
            say(f"     Running {run_target}\n", color="cyan")
            sys.stdout.flush()
            sys.stderr.flush()
            res = subprocess.run([run_target] + list(script_args or []), cwd=base_dir)
            return res.returncode
        finally:
            if build_root:
                shutil.rmtree(build_root, ignore_errors=True)
    finally:
        if no_dce:
            if prev_no_dce is None:
                os.environ.pop("PENGU_NO_DCE", None)
            else:
                os.environ["PENGU_NO_DCE"] = prev_no_dce


def _find_watch_files(base_dir: str) -> List[str]:
    """Finds all .pengu source files and project config files to watch."""
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("build", "dist", "venv", "__pycache__")]
        for fn in filenames:
            if fn.endswith(".pengu") or fn in ("pengu.yaml", "pengu.toml"):
                files.append(os.path.join(root, fn))
    return files


def _watch_and_test(config_path: Optional[str] = None, profile: str = "debug", entry: Optional[str] = None,
                    defines: Optional[List[str]] = None, cc: Optional[str] = None,
                    verbose: bool = False, json_output: bool = False) -> int:
    """Watches source files and re-runs tests on modification."""
    config = ProjectConfig.load(config_path, profile=profile)
    base_dir = config.base_dir
    # Initial run
    try:
        test_project(config_path=config_path, profile=profile, entry=entry,
                     defines=defines, cc=cc, verbose=verbose, json_output=json_output)
    except Exception as exc:
        print(f"Initial test failed: {exc}", file=sys.stderr)
        print("Watching for changes...", file=sys.stderr)

    files = _find_watch_files(base_dir)
    mtimes = {f: os.path.getmtime(f) for f in files if os.path.exists(f)}

    try:
        while True:
            time.sleep(0.5)
            files = _find_watch_files(base_dir)
            changed = False
            for f in files:
                try:
                    m = os.path.getmtime(f)
                    if f not in mtimes or m > mtimes[f]:
                        changed = True
                        mtimes[f] = m
                except OSError:
                    pass
            if changed:
                if not json_output and _OUTPUT.color:
                    # Screen clear for the watch loop: only with colours enabled
                    # (`--no-color` / NO_COLOR / a pipe keeps output plain).
                    sys.stdout.write("\033[2J\033[H")
                    sys.stdout.flush()
                emit("[watching] change detected, rebuilding...",
                     color="cyan",
                     file=sys.stderr if json_output else None, level="progress")
                try:
                    test_project(config_path=config_path, profile=profile, entry=entry,
                                 defines=defines, cc=cc, verbose=verbose, json_output=json_output)
                except Exception as exc:
                    print(f"Error during test: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        return 0


def test_project(config_path: Optional[str] = None, profile: str = "debug", entry: Optional[str] = None,
                 defines: Optional[List[str]] = None, cc: Optional[str] = None,
                 verbose: bool = False, json_output: bool = False,
                 strict_c99: bool = False, target_compiler: str = "",
                 target: str = "", locked: bool = False, frozen: bool = False,
                 release_unsafe: bool = False,
                 deny_deprecated: bool = False) -> int:
    """Compiles the project in --test mode and executes the integrated unit tests.

    The project entry is built as an executable whose main runs every 'test'
    block declared in the compilation units.

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        entry: Optional entry file path override.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override.
        verbose: True to print module order, C commands and phase timings.
        json_output: Emit machine-readable JSON Lines to stdout (for CI).

    Returns:
        Test process exit code (0 when every test passed).
    """
    config = ProjectConfig.load(config_path, profile=profile)
    if entry:
        config.entry = entry
    if defines:
        config.defines = list(config.defines or []) + defines
    if cc:
        config.cc = cc
    if strict_c99:
        config.strict_c99 = True
    if target_compiler:
        config.target_compiler = target_compiler
    if target:
        config.target = target
    config.release_unsafe = bool(release_unsafe)
    config.deny_deprecated = bool(deny_deprecated)
    _set_release_unsafe(config.release_unsafe)
    _ensure_lockfile(config, locked=locked, frozen=frozen)
    config.output = OutputType.EXE

    try:
        _require_entry_file(config)
    except EntryPointNotFoundError as e:
        if json_output:
            print(json.dumps({"type": "diagnostic", **_diagnostic_message(e, config.resolve_entry())},
                             ensure_ascii=False))
            print(json.dumps({"type": "summary", "ok": False, "errors": 1, "warnings": 0,
                              "duration_ms": 0.0}, ensure_ascii=False))
        else:
            emit(f"     Error {e.message}", color="red", level="error")
            if e.help:
                print(f"      help: {e.help}", file=sys.stderr)
        return 1

    t0 = time.time()
    if not json_output:
        emit(f"   Testing {config.name} v{config.version} [--test, {config.profile}]", color="cyan", level="progress")
    builder = PenguBuilder(config)
    builder.is_test_mode = True
    builder.verbose = verbose
    builder.deny_deprecated = bool(deny_deprecated)
    enforce_deny_deprecated(builder, json_output=json_output)
    try:
        artifact, is_cached = builder.compile()
    except CompileFailedError as e:
        # Item 4.6: the JSON contract must hold on the failure path too. Before
        # this, a compilation error escaped `test --json` as a traceback with
        # zero JSON lines on stdout. Reported through the same edge the script
        # paths use (item 4.8).
        return report_pengu_error(e, json_output=json_output,
                                  source=config.resolve_entry())
    except _user_input_errors() as e:
        return report_pengu_error(e, json_output=json_output,
                                  source=config.resolve_entry())
    elapsed = time.time() - t0
    if not json_output:
        if is_cached:
            emit(f"    Finished (cached) in {elapsed:.2f}s -> {artifact}", color="green", level="progress")
        else:
            emit(f"    Finished in {elapsed:.2f}s -> {artifact}", color="green", level="progress")

        emit("     Running tests\n", color="cyan", level="progress")
        sys.stdout.flush()
        sys.stderr.flush()
        res = subprocess.run([artifact], cwd=config.base_dir)
        return res.returncode

    # JSON output mode
    env = dict(os.environ)
    env["PENGU_TEST_JSON"] = "1"
    res = subprocess.run([artifact], cwd=config.base_dir, env=env, capture_output=True, text=True)
    saw_end = False
    if res.stdout:
        for line in res.stdout.splitlines():
            line_s = line.strip()
            if not line_s:
                continue
            try:
                obj = json.loads(line_s)
                if isinstance(obj, dict) and obj.get("event") == "end":
                    saw_end = True
                print(line_s)
            except Exception:
                print(line, file=sys.stderr)
    if not saw_end:
        print(json.dumps({"event": "end", "aborted": res.returncode != 0, "exit_code": res.returncode}))
    if res.stderr:
        print(res.stderr, file=sys.stderr, end="" if res.stderr.endswith("\n") else "\n")
    sys.stdout.flush()
    sys.stderr.flush()
    return res.returncode


# ---------------------------------------------------------------------------
# CLI output (items 4.4 and 4.5)
#
# Every user-facing line the CLI writes goes through `emit()`, so that colour
# (`--no-color` / NO_COLOR) is decided in one place instead of being baked into
# each `print`. `configure_output()` is called once from `main()`; the defaults
# keep library/test use (which never calls it) colour-free unless a caller opts in.
# ---------------------------------------------------------------------------

_ANSI_RESET = "\033[0m"
_ANSI_COLORS = {
    "cyan": "\033[1;36m",
    "green": "\033[1;32m",
    "yellow": "\033[1;33m",
    "red": "\033[1;31m",
    "dim": "\033[1;90m",
    "faint": "\033[2m",
}


class _OutputState:
    """Process-wide CLI output settings."""

    def __init__(self) -> None:
        self.quiet = False
        self.color = False


_OUTPUT = _OutputState()


def configure_output(quiet: bool = False, no_color: bool = False,
                     stream: Optional[object] = None) -> None:
    """Sets the process-wide output mode (call once, from ``main``).

    Colour precedence: an explicit ``--no-color`` (or the presence of the
    ``NO_COLOR`` environment variable, per https://no-color.org, which ignores
    its value) disables ANSI; otherwise colour is used only when the stream is a
    terminal, so piping always yields plain text.

    Args:
        quiet: True to suppress progress lines (errors still print).
        no_color: True when ``--no-color`` was given.
        stream: Stream used for the TTY probe (defaults to ``sys.stdout``).
    """
    _OUTPUT.quiet = bool(quiet)
    if no_color or os.environ.get("NO_COLOR") is not None:
        _OUTPUT.color = False
        return
    probe = stream if stream is not None else sys.stdout
    try:
        _OUTPUT.color = bool(probe.isatty())
    except Exception:
        _OUTPUT.color = False


def emit(message: str = "", *, color: Optional[str] = None,
         level: str = "info", file: Optional[object] = None,
         end: str = "\n") -> None:
    """Writes one CLI line, honouring ``--quiet`` and ``--no-color``.

    Args:
        message: Text to write (may already contain its own newlines).
        color: Name in :data:`_ANSI_COLORS`, or None for plain text.
        level: ``"progress"`` lines are suppressed by ``--quiet``; errors
            and warnings always print.
        file: Destination stream (defaults to ``sys.stdout``).
        end: Line terminator.
    """
    if _OUTPUT.quiet and level == "progress":
        return
    text = message
    if color is not None and _OUTPUT.color and _ANSI_COLORS.get(color):
        text = f"{_ANSI_COLORS[color]}{message}{_ANSI_RESET}"
    out = sys.stdout if file is None else file
    out.write(text + end)


def create_cli_parser() -> argparse.ArgumentParser:
    """Constructs the Cargo-style CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pengu",
        description=f"PenguScript v{PENGU_VERSION} Package & Build Manager",
        epilog="""Examples:
  pengu init my_game --type exe
  pengu add https://github.com/webui-dev/webui
  pengu add ../local_binding -n my_binding
  pengu build --profile release
  pengu build --cc clang --verbose
  pengu check                       # parse + type-check without codegen (CI)
  pengu fmt src/ tests/             # format files/directories
  pengu fmt --check src/            # verify formatting (exit 1 if changes)
  pengu run --profile debug
  pengu run hello.pengu             # run a standalone script (when main: enabled)
  pengu update                      # git pull + rebuild every dependency
  pengu bind webui.h --prefix webui_ --links webui-2-static ole32 stdc++ uuid
  pengu assets                      # regenerate src/arca.pengu & build/arca_assets.c
  pengu assets --list               # list tracked assets, sizes, and identifiers
  pengu clean
"""
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"pengu {PENGU_VERSION}",
        help="Print the PenguScript toolchain version and exit",
    )
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress progress output (errors still go to stderr)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colours (also honoured: NO_COLOR=1)")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    init_p = subparsers.add_parser("init", help="Create a new PenguScript project template")
    init_p.add_argument("name", help="Name of project directory to create")
    init_p.add_argument("--type", "-t", choices=["exe", "c", "obj", "static", "shared"], default=None,
                        help="Target output type (default: exe, or static for --template lib)")
    init_p.add_argument("--links", "-l", help="Comma-separated library names to link (e.g. raylib,m)")
    init_p.add_argument("--output-name", help="Custom output artifact base name")
    init_p.add_argument("--cc", default="gcc", help="C compiler command (default: gcc)")
    init_p.add_argument("--format", dest="manifest_format", choices=["toml", "yaml"], default="toml",
                        help="Project manifest format (default: toml, the canonical one)")
    init_p.add_argument("--template", choices=["exe", "cli", "lib", "game"], default=None,
                        help="Project template flavour (default: derived from --type)")

    # add
    add_p = subparsers.add_parser("add", help="Add an external dependency or binding to the project")
    add_p.add_argument("source", help="Git repository URL or local folder path")
    add_p.add_argument("--branch", "-b", default=None, help="Git branch or tag to clone")
    add_p.add_argument("--name", "-n", default=None, help="Custom binding name override")
    add_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    add_p.add_argument("--no-build", action="store_true", help="Skip executing dependency build script")
    add_p.add_argument("--trust", action="store_true",
                       help="Trust and run the dependency build scripts (build.py/build.sh/Makefile)")

    # remove
    remove_p = subparsers.add_parser("remove", help="Remove an installed dependency (lib/<name> + manifest)")
    remove_p.add_argument("name", help="Dependency / binding name (the lib/<name> directory)")
    remove_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    remove_p.add_argument("--keep-files", action="store_true",
                          help="Only drop the manifest entry; leave lib/<name>/ on disk")

    # upgrade
    upgrade_p = subparsers.add_parser("upgrade", help="Upgrade one dependency (git pull / checkout a tag)")
    upgrade_p.add_argument("name", help="Dependency / binding name")
    upgrade_p.add_argument("--version", "-v", default=None,
                           help="Git tag or SemVer constraint to record and check out (e.g. ^1.2.0)")
    upgrade_p.add_argument("--branch", "-b", default=None, help="Branch override recorded in the manifest")
    upgrade_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")

    # tree / metadata
    tree_p = subparsers.add_parser("tree", help="Show the resolved dependency graph")
    tree_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    tree_p.add_argument("--json", action="store_true", help="Emit the graph as JSON (alias of metadata)")

    metadata_p = subparsers.add_parser("metadata", help="Machine-readable project metadata (JSON)")
    metadata_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")

    # verify
    verify_p = subparsers.add_parser("verify", help="Verify installed dependencies against pengu.lock")
    verify_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    verify_p.add_argument("--verbose", action="store_true", help="Print every verified package")

    # vendor
    vendor_p = subparsers.add_parser("vendor", help="Snapshot dependencies into vendor/ for offline builds")
    vendor_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    vendor_p.add_argument("--verbose", action="store_true", help="Print progress")

    # build
    build_p = subparsers.add_parser("build", help="Compile the project according to configuration")
    build_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    build_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    build_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    build_p.add_argument("--output", "-o", default=None, help="Override output file path (e.g. build/bundle.c)")
    build_p.add_argument("--test", action="store_true", help="Compile integrated unit tests (test blocks) into the bundle")
    build_p.add_argument("--cc", default=None, help="C compiler override (e.g. 'clang'); wins over pengu.yaml")
    build_p.add_argument("--verbose", action="store_true", help="Print module order, C commands and phase timings")
    build_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                         help="Compile-time define: -D NAME or -D os=linux / arch=x64 / compiler=clang / main (repeatable)")
    build_p.add_argument("--pch", action="store_true",
                         help="Precompile pengu_runtime.h (gcc/clang; off by default, see docs/PERFORMANCE.md)")
    build_p.add_argument("--no-pch", "--no_pch", dest="no_pch", action="store_true",
                         help="Force the precompiled header off (it is already the default)")
    build_p.add_argument("--no-dce", "--no_dce", dest="no_dce", action="store_true",
                         help="Keep every std/lib weave in bundle.c (disable dead-code elimination)")
    build_p.add_argument("--json", action="store_true",
                         help="Emit machine-readable JSON Lines (for CI)")

    # run
    run_p = subparsers.add_parser("run", help="Build and execute the project target, or run a standalone .pengu script")
    run_p.add_argument("script", nargs="?", default=None,
                       help="Optional .pengu file to run directly as a script (when main: enabled); omit to run the project")
    run_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    run_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    run_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    run_p.add_argument("--test", action="store_true", help="Build in --test mode and run the unit tests")
    run_p.add_argument("--cc", default=None, help="C compiler override (e.g. 'clang')")
    run_p.add_argument("--verbose", action="store_true", help="Print module order, C commands and phase timings")
    run_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                       help="Compile-time define: -D NAME or -D os=linux / arch=x64 / compiler=clang / main (repeatable)")
    run_p.add_argument("--keep", action="store_true",
                       help="Compile scripts into build/<name>_run/ and keep bundle.c and the binary")
    run_p.add_argument("--no-cache", "--no_cache", dest="no_cache", action="store_true",
                       help="Ignore the binary cache (do not read or write it) for this run")
    run_p.add_argument("--clear-cache", "--clear_cache", dest="clear_cache", action="store_true",
                       help="Empty the cached script binaries before running (alias of 'pengu gc --all')")
    run_p.add_argument("--ephemeral", action="store_true",
                       help="Build in a throw-away temp directory and never populate the cache (CI)")
    run_p.add_argument("--pch", action="store_true",
                       help="Precompile pengu_runtime.h (off by default; see docs/PERFORMANCE.md)")
    run_p.add_argument("--no-pch", "--no_pch", dest="no_pch", action="store_true",
                       help="Force the precompiled header off (already the default)")
    run_p.add_argument("--no-dce", "--no_dce", dest="no_dce", action="store_true",
                       help="Disable dead-code elimination of unused std weaves")
    # Roadmap Phase 2: portable C output (build/run share the same knobs).
    for _p in (build_p, run_p):
        _p.add_argument("--strict-c99", "--strict_c99", dest="strict_c99", action="store_true",
                        help="Emit portable C99: no GNU statement expressions nor __auto_type")
        _p.add_argument("--target-compiler", "--target_compiler", dest="target_compiler", default=None,
                        choices=["gcc", "clang", "msvc", "tcc"],
                        help="C compiler dialect used for attributes/restrict (default: infer from --cc)")
        _p.add_argument("--target", dest="target", default=None,
                        help="Cross-compilation target triple (e.g. x86_64-w64-mingw32); "
                             "Linux <-> Windows only, needs a cross compiler and PENGU_RUNTIME_CROSS")
        _p.add_argument("--locked", action="store_true",
                        help="Fail if pengu.lock is missing or out of date (never writes it)")
        _p.add_argument("--frozen", action="store_true",
                        help="Like --locked but also requires pengu.lock to exist (offline/CI builds)")
        _p.add_argument("--release-unsafe", dest="release_unsafe", action="store_true",
                        help="Disable bounds and integer-overflow checks (unsafe; default is checks ON in every profile)")
        _p.add_argument("--deny-deprecated", dest="deny_deprecated", action="store_true",
                        help="Fail the build when a @deprecated symbol (W0006) is used")
    # Script arguments are collected with parse_known_args: 'pengu run x.pengu -- a b'
    # and 'pengu run x.pengu a b' both forward 'a b'.

    # doctor
    doctor_p = subparsers.add_parser("doctor", help="Report toolchain health (compiler, tcc, runtime, cache, std/)")
    doctor_p.add_argument("--json", action="store_true", help="Emit the report as a single JSON object")

    # gc
    gc_p = subparsers.add_parser("gc", help="Garbage-collect the global caches")
    gc_p.add_argument("--all", action="store_true", help="Remove every cached script (ignore the age threshold)")
    gc_p.add_argument("--max-age", "--max_age", dest="max_age", type=int, default=30,
                      help="Remove cached scripts unused for N days (default: 30)")
    gc_p.add_argument("--verbose", action="store_true", help="List the removed entries")
    gc_p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    # expand
    expand_p = subparsers.add_parser("expand", help="Print the generated bundle.c of a script to stdout")
    expand_p.add_argument("script", help="Path to the .pengu file")
    expand_p.add_argument("--output", "-o", default=None, help="Write the bundle to this file instead of stdout")
    expand_p.add_argument("--verbose", action="store_true", help="Print module order and phase timings")
    expand_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                          help="Compile-time define (repeatable)")

    # time
    time_p = subparsers.add_parser("time", help="Run a script and report per-phase timings")
    time_p.add_argument("script", help="Path to the .pengu file")
    time_p.add_argument("--cc", default=None, help="C compiler override")
    time_p.add_argument("--no-dce", "--no_dce", dest="no_dce", action="store_true",
                        help="Disable dead-code elimination of unused std weaves")
    time_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                        help="Compile-time define (repeatable)")
    time_p.add_argument("script_args", nargs="*", default=None,
                        help="Arguments forwarded to the script (after '--')")

    # eval
    eval_p = subparsers.add_parser("eval", help="Evaluate a one-line PenguScript expression")
    eval_p.add_argument("expression", help="Expression to evaluate, e.g. '1 + 2'")
    eval_p.add_argument("--cc", default=None, help="C compiler override")
    eval_p.add_argument("--no-cache", "--no_cache", dest="no_cache", action="store_true",
                        help="Do not use or populate the binary cache")
    eval_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                        help="Compile-time define (repeatable)")

    # watch
    watch_p = subparsers.add_parser("watch", help="Re-run a script whenever it or its imports change")
    watch_p.add_argument("script", help="Path to the .pengu file")
    watch_p.add_argument("--cc", default=None, help="C compiler override")
    watch_p.add_argument("--keep", action="store_true", help="Keep the build directory of each run")
    watch_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                         help="Compile-time define (repeatable)")

    # test
    test_p = subparsers.add_parser("test", help="Compile and run the project's integrated unit tests")
    test_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    test_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    test_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    test_p.add_argument("--cc", default=None, help="C compiler override (e.g. 'clang')")
    test_p.add_argument("--verbose", action="store_true", help="Print module order, C commands and phase timings")
    test_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                        help="Compile-time define: -D NAME or -D os=linux / arch=x64 / compiler=clang / main (repeatable)")
    test_p.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON Lines to stdout (for CI)")
    test_p.add_argument("--watch", action="store_true",
                        help="Watch source files and re-run tests on modification")
    test_p.add_argument("--strict-c99", "--strict_c99", dest="strict_c99", action="store_true",
                        help="Emit portable C99: no GNU statement expressions nor __auto_type")
    test_p.add_argument("--target-compiler", "--target_compiler", dest="target_compiler", default=None,
                        choices=["gcc", "clang", "msvc", "tcc"],
                        help="C compiler dialect used for attributes/restrict (default: infer from --cc)")
    test_p.add_argument("--target", dest="target", default=None,
                        help="Cross-compilation target triple (e.g. x86_64-w64-mingw32)")
    test_p.add_argument("--locked", action="store_true",
                        help="Fail if pengu.lock is missing or out of date")
    test_p.add_argument("--frozen", action="store_true",
                        help="Like --locked but also requires pengu.lock to exist")
    test_p.add_argument("--release-unsafe", dest="release_unsafe", action="store_true",
                        help="Disable bounds and integer-overflow checks (unsafe)")
    test_p.add_argument("--deny-deprecated", dest="deny_deprecated", action="store_true",
                        help="Fail when a @deprecated symbol (W0006) is used")

    # check
    check_p = subparsers.add_parser("check", help="Parse and type-check every module without generating code (CI)")
    check_p.add_argument("files", nargs="*", default=None,
                         help="Specific .pengu files to check (default: the project entry and its imports)")
    check_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    check_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    check_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    check_p.add_argument("--cc", default=None, help="C compiler override (informational for 'when compiler')")
    check_p.add_argument("--verbose", action="store_true", help="Print per-file progress")
    check_p.add_argument("--json", action="store_true",
                         help="Emit machine-readable JSON Lines (for CI)")
    check_p.add_argument("--deny-deprecated", dest="deny_deprecated", action="store_true",
                         help="Treat the use of @deprecated symbols (W0006) as an error")
    check_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                         help="Compile-time define: -D NAME or -D os=linux / arch=x64 / compiler=clang / main (repeatable)")

    # update
    update_p = subparsers.add_parser("update", help="Update dependencies: git pull + re-run build scripts")
    update_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    update_p.add_argument("--verbose", action="store_true", help="Print the git commands being executed")
    update_p.add_argument("--trust", action="store_true",
                          help="Trust and re-run dependency build scripts")

    # bind
    bind_p = subparsers.add_parser("bind", help="Generate a .d.pengu binding from a C header")
    bind_p.add_argument("header", help="Path to the C header file (.h) to translate")
    bind_p.add_argument("--prefix", default="", help="Insignia prefix added to function names (e.g. webui_)")
    bind_p.add_argument("--links", nargs="*", default=[], help="Native libraries to emit as link \"...\" lines")
    bind_p.add_argument("--output", default="", help="Output .d.pengu path (default: next to the header)")
    bind_p.add_argument("--no-comments", action="store_true", help="Do not emit documentation comments")
    bind_p.add_argument("--ignore", nargs="*", default=[], help="Symbol names / regexes to skip")
    bind_p.add_argument("--include-paths", nargs="*", default=[], help="Extra include directories for the preprocessor")
    bind_p.add_argument("--define", "-D", dest="defines", action="append", default=[],
                        help="Define a preprocessor macro (e.g. -D Z_SOLO or --define NAME=val)")
    bind_p.add_argument("--cpp-flags", default=None,
                        help="Raw flags passed directly to the preprocessor (e.g. \"-DZ_SOLO -DXXH_INLINE_ALL=0\")")
    bind_p.add_argument("--system-includes", action="store_true", default=False,
                        help="Use compiler system headers instead of minimal stubs (keeps _WIN32/_MSC_VER and omits -nostdinc)")
    bind_p.add_argument("--preprocessed", default=None, metavar="FILE.i",
                        help="Parse an already preprocessed .i file directly without running gcc")
    bind_p.add_argument("--no-blank-extensions", dest="blank_extensions", action="store_false", default=True,
                        help="Do not blank GNU compiler extensions (__attribute__, __asm__, etc.)")
    bind_p.add_argument("--no-cpp", dest="use_cpp", action="store_false", default=True,
                        help="Do not run the C preprocessor (simple headers only)")
    bind_p.add_argument("--auto-import", dest="auto_import", default=None, metavar="DIR",
                        help="Directory with sibling .d.pengu bindings; emit 'import' lines for "
                             "the headers this header includes (default: the output directory, "
                             "pass an empty value to disable)")

    # fmt
    fmt_p = subparsers.add_parser("fmt", help="Format .pengu files or directories (standard style)")
    fmt_p.add_argument("paths", nargs="*", help="Files and/or directories to format (directories are searched recursively)")
    fmt_p.add_argument("--check", action="store_true", help="Do not write; exit non-zero when a file would change")
    fmt_p.add_argument("--diff", action="store_true", help="Print a unified diff for every file that would change")
    fmt_p.add_argument("--stdin", action="store_true", help="Read from stdin and write the formatted result to stdout")
    fmt_p.add_argument("--config", "-c", default=None, help="Project root for .pengufmt.toml / pengu.yaml formatting config")
    fmt_p.add_argument("--write", action="store_true", default=True, help="Write formatted output back to disk (default)")
    fmt_p.add_argument("--indent", type=int, default=None,
                       help="Spaces per indentation level; wins over .pengufmt.toml (default: 4)")
    fmt_p.add_argument("--tabs", action="store_true", default=None,
                       help="Indent with tabs; wins over .pengufmt.toml (default: spaces)")
    fmt_p.add_argument("--verbose", action="store_true", help="Print every file considered")


    # clean
    clean_p = subparsers.add_parser("clean", help="Remove build directory and generated artifacts")
    clean_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")

    # lsp
    lsp_p = subparsers.add_parser("lsp", help="Launch the PenguScript Language Server Protocol (LSP)")
    lsp_p.add_argument("--stdio", action="store_true", default=True, help="Run LSP server over standard I/O (default)")
    lsp_p.add_argument("--tcp", action="store_true", help="Run LSP server over TCP socket")
    lsp_p.add_argument("--host", default="127.0.0.1", help="TCP bind host (default: 127.0.0.1)")
    lsp_p.add_argument("--port", type=int, default=2087, help="TCP bind port (default: 2087)")

    # doc
    doc_p = subparsers.add_parser("doc", help="Generate Markdown documentation from ## comments")
    doc_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    doc_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    doc_p.add_argument("--output", "-o", default=None, help="Output directory (default: <project>/docs)")

    # assets
    assets_p = subparsers.add_parser("assets", help="Generate or inspect embedded asset modules")
    assets_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    assets_p.add_argument("--list", action="store_true", help="List tracked assets with sizes and PenguScript asset constants")
    assets_p.add_argument("--force", action="store_true", help="Force regeneration ignoring caches")

    # Item 4.5: accept `--no-color` after the subcommand too (`pengu check
    # --no-color`), not only as a global flag. SUPPRESS keeps it from clobbering
    # the already-parsed global value when the flag is not repeated.
    for _sub in subparsers.choices.values():
        _sub.add_argument("-q", "--quiet", action="store_true", default=argparse.SUPPRESS,
                          help="Suppress progress output (errors still go to stderr)")
        _sub.add_argument("--no-color", action="store_true", default=argparse.SUPPRESS,
                          help="Disable ANSI colours (also honoured: NO_COLOR=1)")

    return parser


_CC_DIAG_RE = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<kind>error|warning|note|fatal error):\s*(?P<msg>.*)$"
)


def remap_c_diagnostics(text: str) -> List[str]:
    """Rewrites gcc/clang 'bundle.c:LINE:COL' diagnostics to .pengu positions.

    The bundle carries ``#line N "source.pengu"`` markers, so passing the bundle
    through ``gcc -E`` (or trusting gcc's own file report) is enough; gcc usually
    prints the *original* file already.  What it does not do is normalise the
    shape, so this adds a stable ``[gcc]`` prefix, keeps the code, and drops the
    bundle path when gcc fell back to it.
    """
    out: List[str] = []
    for raw in (text or "").splitlines():
        match = _CC_DIAG_RE.match(raw.strip())
        if not match:
            continue
        fname = match.group("file")
        if fname.endswith("bundle.c"):
            continue  # not actionable for the user; the .pengu marker follows
        kind = match.group("kind")
        prefix = "error" if kind in ("error", "fatal error") else kind
        out.append(f"{fname}:{match.group('line')}:{match.group('col')} "
                   f"[cc] {prefix}: {match.group('msg')}")
    return out


def _print_compile_error(err: "CompileFailedError") -> None:
    """Prints a formatted C-compilation error and exits with status 1."""
    emit("\nError:", file=sys.stderr, color="red", level="error")
    text = str(err)
    mapped = remap_c_diagnostics(text)
    if mapped:
        # Lead with the remapped, user-actionable lines, then the raw output.
        print("C compiler diagnostics (mapped to .pengu sources):", file=sys.stderr)
        for line in mapped[:40]:
            print("  " + line, file=sys.stderr)
        print("", file=sys.stderr)
    print(text, file=sys.stderr)
    sys.exit(1)


def _user_input_errors() -> Tuple[type, ...]:
    """Exception types the CLI edge must report instead of crashing.

    ``PenguError`` is imported lazily (the compiler front end pulls in Lark,
    ~100 ms) so it cannot be named directly here: PEP 562's module ``__getattr__``
    only serves attribute access, not bare names inside a function body.
    ``FileNotFoundError``/``ValueError`` are included because the script entry
    points raise those for user input too (a missing ``.pengu`` file, a
    non-``.pengu`` path).
    """
    import importlib

    pengu_error = getattr(importlib.import_module("pengu_parser.pengu_errors"), "PenguError")
    return (pengu_error, FileNotFoundError, ValueError)


def report_pengu_error(exc: BaseException, *, json_output: bool = False,
                       source: Optional[str] = None) -> int:
    """Reports a user-input error the way every script path should.

    Human output is a one-line `file:line:col [code] message` (the same shape
    `pengu check` uses, via :func:`_diagnostic_message`), plus `help`/`note`
    when the error carries them. With ``json_output`` the diagnostic and a
    summary are emitted as JSON Lines instead.

    Args:
        exc: The exception to report.
        json_output: True to emit JSON Lines rather than text.
        source: Source file the error refers to, when known.

    Returns:
        The process exit code (always non-zero).
    """
    path = source or getattr(exc, "filename", None) or getattr(exc, "file", None) or "<input>"
    message = getattr(exc, "message", None) or str(exc)
    if json_output:
        diag = _diagnostic_message(exc, str(path))
        print(json.dumps({"type": "diagnostic", **diag}, ensure_ascii=False))
        print(json.dumps({
            "type": "summary", "ok": False, "errors": 1, "warnings": 0,
        }, ensure_ascii=False))
    else:
        line = getattr(exc, "line", None) or 0
        col = getattr(exc, "column", None) or getattr(exc, "col", None) or 0
        code = getattr(exc, "code", None) or ""
        where = f"{path}:{int(line)}:{int(col)}" if line else str(path)
        code_str = f" [{code}]" if code else ""
        emit(f"  {where}{code_str} {message}", file=sys.stderr,
             color="red", level="error")
        help_text = getattr(exc, "help", None)
        if help_text:
            emit(f"    help: {help_text}", file=sys.stderr, level="error")
        note_text = getattr(exc, "note", None)
        if note_text:
            emit(f"    note: {note_text}", file=sys.stderr, level="error")
    return 1


def _run_command(action: Callable[[], int], *,
                 json_output: bool = False,
                 source: Optional[str] = None) -> None:
    """Runs one command body, reporting user-input errors instead of crashing.

    This is the CLI edge for the script paths (`run <script>`, `eval`, `expand`,
    `time`, `watch`): an error caused by the user's input is printed once, in
    the standard shape, with a non-zero exit code — never as a Python traceback.

    Args:
        action: Zero-argument callable with the command body; its return value
            becomes the process exit code.
        json_output: True to report errors as JSON Lines.
        source: Source file to blame in the diagnostic, when known.
    """
    try:
        sys.exit(action())
    except _user_input_errors() as exc:
        sys.exit(report_pengu_error(exc, json_output=json_output, source=source))


def main():
    """Main execution entry point."""
    parser = create_cli_parser()
    # parse_known_args (instead of parse_args) lets 'pengu run script.pengu'
    # forward *unknown* arguments to the script -- the `run` subparser declares
    # no REMAINDER positional, so everything after the script path arrives here.
    #
    # Everywhere else an unrecognised argument is a user error (a typo such as
    # '--strictc99' for '--strict-c99' silently disabling a guarantee is the
    # exact failure this guards against), so it is rejected with rc=2.
    args, unknown = parser.parse_known_args()
    # Items 4.4/4.5: decide colour and verbosity once, here. `NO_COLOR`'s mere
    # presence disables ANSI (https://no-color.org) and is read by
    # `configure_output`, which is why it is no longer rewritten into the
    # environment: the variable belongs to the user, and other tools may read it.
    configure_output(
        quiet=bool(getattr(args, "quiet", False)),
        no_color=bool(getattr(args, "no_color", False)),
    )
    if getattr(args, "command", None) == "run" and getattr(args, "script", None):
        forwarded = list(getattr(args, "script_args", None) or []) + list(unknown)
        setattr(args, "script_args", forwarded)
    elif unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")

    if args.command == "init":
        links_list = [i.strip() for i in args.links.split(",") if i.strip()] if args.links else []
        init_project(
            name=args.name,
            output_type=args.type,
            links=links_list,
            cc=args.cc,
            output_name=args.output_name,
            manifest_format=getattr(args, "manifest_format", "toml"),
            template=getattr(args, "template", None) or "exe",
        )
    elif args.command == "add":
        try:
            add_dependency(
                source=args.source,
                branch=args.branch,
                name=args.name,
                config_path=args.config,
                run_build=not args.no_build,
                trusted=getattr(args, "trust", False),
            )
        except (DependencyConflictError, RuntimeError, FileNotFoundError) as e:
            emit(f"     Error {e}", file=sys.stderr, color="red", level="error")
            sys.exit(1)
    elif args.command == "remove":
        try:
            remove_dependency(
                name=args.name,
                config_path=args.config,
                keep_files=getattr(args, "keep_files", False),
            )
        except (FileNotFoundError, ValueError) as e:
            emit(f"     Error {e}", file=sys.stderr, color="red", level="error")
            sys.exit(1)
    elif args.command == "upgrade":
        try:
            upgrade_dependency(
                name=args.name,
                version=getattr(args, "version", None),
                branch=getattr(args, "branch", None),
                config_path=args.config,
            )
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            emit(f"     Error {e}", file=sys.stderr, color="red", level="error")
            sys.exit(1)
    elif args.command == "verify":
        sys.exit(verify_project(config_path=args.config,
                                verbose=getattr(args, "verbose", False)))
    elif args.command == "vendor":
        try:
            vendor_dependencies(ProjectConfig.load(args.config),
                                verbose=getattr(args, "verbose", False))
        except (DependencyConflictError, RuntimeError) as e:
            emit(f"     Error {e}", file=sys.stderr, color="red", level="error")
            sys.exit(1)
    elif args.command in ("tree", "metadata"):
        try:
            sys.exit(print_dependency_tree(
                ProjectConfig.load(args.config),
                as_json=(args.command == "metadata") or getattr(args, "json", False),
            ))
        except DependencyConflictError as e:
            emit(f"     Error {e}", file=sys.stderr, color="red", level="error")
            sys.exit(1)
    elif args.command == "build":
        try:
            build_project(
                config_path=args.config,
                profile=args.profile,
                entry=getattr(args, "entry", None),
                output=getattr(args, "output", None),
                test=getattr(args, "test", False),
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False),
                pch=getattr(args, "pch", False) and not getattr(args, "no_pch", False),
                no_dce=getattr(args, "no_dce", False),
                strict_c99=getattr(args, "strict_c99", False),
                target_compiler=getattr(args, "target_compiler", "") or "",
                target=getattr(args, "target", "") or "",
                locked=getattr(args, "locked", False),
                frozen=getattr(args, "frozen", False),
                release_unsafe=getattr(args, "release_unsafe", False),
                deny_deprecated=getattr(args, "deny_deprecated", False),
                json_output=getattr(args, "json", False),
            )
        except CompileFailedError as e:
            _print_compile_error(e)
    elif args.command == "run":
        try:
            if getattr(args, "script", None):
                # '--pch' opts in, '--no-pch' wins when both are given.
                want_pch = getattr(args, "pch", False)
                no_pch = getattr(args, "no_pch", False) or not want_pch
                sys.exit(run_script(
                    script=args.script,
                    defines=getattr(args, "defines", None),
                    cc=getattr(args, "cc", None),
                    verbose=getattr(args, "verbose", False),
                    keep=getattr(args, "keep", False),
                    no_cache=getattr(args, "no_cache", False),
                    clear_cache=getattr(args, "clear_cache", False),
                    ephemeral=getattr(args, "ephemeral", False),
                    script_args=_consume_script_args(getattr(args, "script_args", None)),
                    quiet=getattr(args, "quiet", False),
                    no_pch=no_pch,
                    no_dce=getattr(args, "no_dce", False),
                    strict_c99=getattr(args, "strict_c99", False),
                    target_compiler=getattr(args, "target_compiler", "") or "",
                    target=getattr(args, "target", "") or "",
                    locked=getattr(args, "locked", False),
                    frozen=getattr(args, "frozen", False),
                    release_unsafe=getattr(args, "release_unsafe", False),
                    deny_deprecated=getattr(args, "deny_deprecated", False),
                ))
            sys.exit(run_project(
                config_path=args.config,
                profile=args.profile,
                test=getattr(args, "test", False),
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False),
                pch=getattr(args, "pch", False) and not getattr(args, "no_pch", False),
                no_dce=getattr(args, "no_dce", False),
                strict_c99=getattr(args, "strict_c99", False),
                target_compiler=getattr(args, "target_compiler", "") or "",
                target=getattr(args, "target", "") or "",
                locked=getattr(args, "locked", False),
                frozen=getattr(args, "frozen", False),
                release_unsafe=getattr(args, "release_unsafe", False),
                deny_deprecated=getattr(args, "deny_deprecated", False),
            ))
        except CompileFailedError as e:
            _print_compile_error(e)
        except _user_input_errors() as e:
            # Script mode (`pengu run x.pengu`) reaches the compiler directly, so
            # a syntax error or a missing file used to surface as a traceback.
            sys.exit(report_pengu_error(e, source=getattr(args, "script", None)))
    elif args.command == "test":
        try:
            if getattr(args, "watch", False):
                sys.exit(_watch_and_test(
                    config_path=args.config,
                    profile=args.profile,
                    entry=getattr(args, "entry", None),
                    defines=getattr(args, "defines", None),
                    cc=getattr(args, "cc", None),
                    verbose=getattr(args, "verbose", False),
                    json_output=getattr(args, "json", False),
                ))
            sys.exit(test_project(
                config_path=args.config,
                profile=args.profile,
                entry=getattr(args, "entry", None),
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False),
                json_output=getattr(args, "json", False),
                strict_c99=getattr(args, "strict_c99", False),
                target_compiler=getattr(args, "target_compiler", "") or "",
                target=getattr(args, "target", "") or "",
                locked=getattr(args, "locked", False),
                frozen=getattr(args, "frozen", False),
                release_unsafe=getattr(args, "release_unsafe", False),
                deny_deprecated=getattr(args, "deny_deprecated", False),
            ))
        except CompileFailedError as e:
            _print_compile_error(e)
    elif args.command == "check":
        # Positional files win over the project entry: 'pengu check a.pengu'
        # checks exactly that file, not whatever pengu.toml happens to point at.
        check_files_arg = getattr(args, "files", None)
        if check_files_arg:
            ok = check_files(
                files=check_files_arg,
                config_path=args.config,
                profile=args.profile,
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False),
                json_output=getattr(args, "json", False),
                deny_deprecated=getattr(args, "deny_deprecated", False),
            )
        else:
            ok = check_project(
                config_path=args.config,
                profile=args.profile,
                entry=getattr(args, "entry", None),
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False),
                json_output=getattr(args, "json", False),
                deny_deprecated=getattr(args, "deny_deprecated", False),
            )
        sys.exit(0 if ok else 1)
    elif args.command == "fmt":
        if getattr(args, "stdin", False):
            sys.exit(fmt_stdin(
                indent=args.indent, tabs=args.tabs,
                config_path=getattr(args, "config", None),
                check_only=args.check,
            ))
        if not args.paths:
            fmt_p_error = "fmt requires at least one path (or --stdin)"
            print(fmt_p_error, file=sys.stderr)
            sys.exit(2)
        changed = fmt_files(
            paths=args.paths,
            check_only=args.check,
            write=args.write,
            indent=args.indent,
            tabs=args.tabs,
            verbose=args.verbose,
            diff=getattr(args, "diff", False),
            use_config=getattr(args, "config", None) is None,
        )
        sys.exit(1 if (args.check and changed > 0) else 0)
    elif args.command == "update":
        update_project(config_path=args.config, verbose=getattr(args, "verbose", False),
                       trusted=getattr(args, "trust", False))
    elif args.command == "bind":
        from pengu_bind import HeaderParseError, generate_bind_file
        try:
            out = generate_bind_file(
                header=args.header,
                output=args.output or None,
                prefix=args.prefix,
                links=args.links,
                ignore=args.ignore,
                include_paths=args.include_paths,
                use_cpp=args.use_cpp,
                no_comments=args.no_comments,
                auto_import=args.auto_import,
                defines=args.defines,
                cpp_flags=args.cpp_flags,
                system_includes=args.system_includes,
                preprocessed=args.preprocessed,
                blank_extensions=args.blank_extensions,
            )
            emit(f"     Bound {args.header} -> {out}", color="green", level="progress")
        except (HeaderParseError, FileNotFoundError, ValueError) as e:
            emit(f"       Bind {e}", file=sys.stderr, color="red", level="progress")
            sys.exit(1)
    elif args.command == "doctor":
        sys.exit(doctor_report(as_json=getattr(args, "json", False)))
    elif args.command == "gc":
        removed = gc_script_cache(max_age_days=getattr(args, "max_age", 30),
                                  verbose=getattr(args, "verbose", False),
                                  everything=getattr(args, "all", False))
        if getattr(args, "json", False):
            print(json.dumps({"removed": removed, "cache_root": cache_root()}))
        else:
            emit(f"    Collected {removed} cached script(s)", color="green", level="progress")
        sys.exit(0)
    elif args.command == "expand":
        _run_command(
            lambda: expand_script(args.script, output=getattr(args, "output", None),
                                  defines=getattr(args, "defines", None),
                                  verbose=getattr(args, "verbose", False)),
            source=args.script)
    elif args.command == "time":
        _run_command(
            lambda: time_script(args.script, defines=getattr(args, "defines", None),
                                cc=getattr(args, "cc", None),
                                script_args=_consume_script_args(getattr(args, "script_args", None)),
                                no_dce=getattr(args, "no_dce", False)),
            source=args.script)
    elif args.command == "eval":
        _run_command(
            lambda: eval_expression(args.expression, defines=getattr(args, "defines", None),
                                    cc=getattr(args, "cc", None),
                                    no_cache=getattr(args, "no_cache", False)),
            source="<eval>")
    elif args.command == "watch":
        _run_command(
            lambda: watch_script(args.script, defines=getattr(args, "defines", None),
                                 cc=getattr(args, "cc", None),
                                 keep=getattr(args, "keep", False)),
            source=args.script)
    elif args.command == "clean":
        clean_project(config_path=args.config)
    elif args.command == "lsp":
        # Force SelectorEventLoopPolicy on Windows before importing pygls
        import asyncio
        if sys.platform == "win32":
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except AttributeError:
                    pass
        from pengu_lsp.server import server
        try:
            if args.tcp:
                print(f"Starting PenguScript LSP server on {args.host}:{args.port}...", file=sys.stderr)
                server.start_tcp(args.host, args.port)
            else:
                server.start_io()
        except (BrokenPipeError, ConnectionResetError, ValueError) as e:
            if "I/O operation on closed file" in str(e) or "Broken pipe" in str(e):
                pass
            else:
                print(f"[LSP] Server stopped: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            pass
    elif args.command == "doc":
        from pengu_doc import doc_project
        doc_project(config_path=args.config, output=args.output, entry=getattr(args, "entry", None))
    elif args.command == "assets":
        config = ProjectConfig.load(args.config)
        if not getattr(config, "assets_dir", None):
            print("No assets directory configured in pengu.yaml.")
            sys.exit(0)
        assets_abs = os.path.abspath(os.path.join(config.base_dir, config.assets_dir))
        if not os.path.isdir(assets_abs):
            print(f"Assets directory not found: {assets_abs}")
            sys.exit(1)

        from pengu_assets import _collect, _asset_const_name
        items = _collect(Path(assets_abs), getattr(config, "assets_exclude", []))
        if getattr(args, "list", False):
            mode = "embed" if getattr(config, "assets_embed", True) else "disk"
            print(f"Assets for {config.name} (dir: {config.assets_dir}, module: {config.assets_module}, mode: {mode}):")
            if not items:
                print("  (no assets found)")
            else:
                total_bytes = 0
                for rel, full_path in items:
                    sz = full_path.stat().st_size
                    const_name = _asset_const_name(rel, module=getattr(config, "assets_module", "arca"))
                    total_bytes += sz
                    print(f"  {rel:40} {const_name:45} {sz:>10} bytes")
                print(f"Total: {len(items)} asset(s), {total_bytes} bytes")
        else:
            builder = PenguBuilder(config)
            res = builder.generate_assets(force=getattr(args, "force", False))
            if res:
                emit(f"    Assets generated {res['interface_path']} and {res['c_path']} ({len(res['assets'])} assets)", color="green", level="progress")
            else:
                emit(f"    Assets no assets found in {config.assets_dir}", color="yellow", level="progress")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
