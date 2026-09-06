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
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_symbols import resolve_imports
from pengu_parser.pengu_errors import ErrorReporter, PenguError
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_comptime import main_flag_requested, parse_cli_defines


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
            if yaml is not None:
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
        )


class CompileFailedError(RuntimeError):
    """Raised when the C compiler (gcc/clang/...) rejects the generated bundle."""


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
        self.parser = PenguParser()
        self.compile_env = parse_cli_defines(config.defines)
        # Entry-as-main mode: when enabled (pengu run <file> scripts, or an
        # explicit -D main define), only the *entry* module is compiled with
        # the compile-time 'main' flag true; imported modules keep it false.
        self.entry_as_main = bool(main_flag_requested(config.defines))
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
        self.checker = PenguChecker(base_dir=config.base_dir, compile_env=self.compile_env)
        # Verbose mode: print the resolved module order, the exact C commands
        # being executed and phase timings.
        self.verbose = False

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
        }, sort_keys=True)
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get_output_artifact_name(self) -> str:
        """Determines target output filename according to platform and OutputType.

        Returns:
            Resolved filename string.
        """
        out_name = self.config.output_name
        out_type = self.config.output
        is_win = sys.platform == "win32"
        is_mac = sys.platform == "darwin"

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

        Args:
            dest_dir: Target directory path where bundle.c is generated.

        Returns:
            Path to copied pengu_runtime.h.

        Raises:
            FileNotFoundError: If pengu_runtime.h cannot be found in search candidates.
        """
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        meipass = getattr(sys, "_MEIPASS", "")
        candidates = [
            os.path.join(self.config.base_dir, "pengu_runtime.h"),
            os.path.join(self.config.base_dir, "pengu_parser", "pengu_runtime.h"),
            os.path.join(self.config.base_dir, "runtime", "pengu_runtime.h"),
            os.path.join(self.config.base_dir, "build", "include", "pengu_runtime.h"),
            os.path.join(exe_dir, "runtime", "include", "pengu_runtime.h"),
            os.path.join(exe_dir, "runtime", "pengu_runtime.h"),
            os.path.join(exe_dir, "pengu_runtime.h"),
            os.path.join(exe_dir, "..", "runtime", "pengu_runtime.h"),
            os.path.join(meipass, "runtime", "include") if meipass else "",
            os.path.join(meipass, "runtime") if meipass else "",
            os.path.join(meipass, "pengu_runtime.h") if meipass else "",
            os.path.join(os.path.dirname(__file__), "pengu_runtime.h"),
            os.path.join(os.path.dirname(__file__), "pengu_parser", "pengu_runtime.h"),
        ]

        found_src = None
        for cand in candidates:
            if cand and os.path.isfile(cand):
                found_src = os.path.abspath(cand)
                break

        if not found_src:
            raise FileNotFoundError(
                "Cannot locate 'pengu_runtime.h'. Place pengu_runtime.h in project root or pengu_parser/"
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

        # 4. Standard runtime candidates
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        meipass = getattr(sys, "_MEIPASS", "")
        extra_inc_candidates = [
            os.path.join(self.config.base_dir, "build", "include"),
            os.path.join(self.config.base_dir, "runtime", "include"),
            os.path.join(self.config.base_dir, "runtime"),
            os.path.join(exe_dir, "runtime", "include"),
            os.path.join(exe_dir, "runtime"),
            os.path.join(exe_dir, "..", "runtime"),
            os.path.join(meipass, "runtime", "include") if meipass else "",
            os.path.join(meipass, "runtime") if meipass else "",
        ]
        for extra in extra_inc_candidates:
            if extra and os.path.isdir(extra):
                abs_e = os.path.abspath(extra)
                if abs_e not in dirs:
                    dirs.append(abs_e)

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

        # 4. Standard runtime candidates
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        meipass = getattr(sys, "_MEIPASS", "")
        extra_lib_candidates = [
            os.path.join(self.config.base_dir, "build", "lib"),
            os.path.join(self.config.base_dir, "runtime", "lib"),
            os.path.join(self.config.base_dir, "runtime"),
            os.path.join(exe_dir, "runtime", "lib"),
            os.path.join(exe_dir, "runtime"),
            os.path.join(exe_dir, "..", "runtime"),
            os.path.join(meipass, "runtime", "lib") if meipass else "",
            os.path.join(meipass, "runtime") if meipass else "",
        ]
        for extra in extra_lib_candidates:
            if extra and os.path.isdir(extra):
                abs_e = os.path.abspath(extra)
                if abs_e not in lib_dirs:
                    lib_dirs.append(abs_e)

        # 5. Automatically detect libraries to link in all lib_dirs
        for ld in lib_dirs:
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
                saved_hash = f.read().strip()
            if saved_hash != self.compute_config_hash():
                return False
        except Exception:
            return False

        bundle_mtime = os.path.getmtime(bundle_path)

        for mod_path in module_order:
            if os.path.isfile(mod_path):
                if os.path.getmtime(mod_path) > bundle_mtime:
                    return False

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

        bundle_path = output_file or os.path.join(build_dir, "bundle.c")
        entry_abs = self.config.resolve_entry()

        # 1. Resolve module order
        module_order: List[str] = []
        if os.path.isfile(entry_abs):
            module_order = resolve_imports(self.config.base_dir, entry_abs, self.parser)
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

        if self.verbose:
            self._vlog(f"[pengu] semantic check finished in {time.time() - t_check:.3f}s")
            t_codegen = time.time()

        # 4. Copy runtime header to build directory
        self.locate_and_copy_runtime(build_dir)

        # 5. Generate bundle.c via PenguCodegen
        from pengu_parser.pengu_codegen import PenguCodegen
        codegen = PenguCodegen(self.checker.symbols, module_order, self.config.base_dir, compile_env=self.compile_env)
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

        if self.verbose:
            self._vlog(f"[pengu] codegen finished in {time.time() - t_codegen:.3f}s")
            self._vlog(f"[pengu] bundle written: {bundle_path}")

        # 6. Save compilation configuration hash
        hash_file = os.path.join(os.path.dirname(bundle_path), ".bundle_hash")
        try:
            with open(hash_file, "w", encoding="utf-8") as f:
                f.write(self.compute_config_hash())
        except Exception:
            pass

        return bundle_path, False

    def check_sources(self) -> Tuple[bool, List[str]]:
        """Parses and semantically checks every module without generating code.

        Entry-as-main semantics are respected (the entry module compiles with
        the compile-time 'main' variable true when entry_as_main is enabled).

        Returns:
            Tuple of (ok, messages) where each message is a human readable
            problem line ("file:line:col [CODE] message").
        """
        entry_abs = self.config.resolve_entry()
        if os.path.isfile(entry_abs):
            module_order = resolve_imports(self.config.base_dir, entry_abs, self.parser)
        else:
            module_order = [entry_abs]

        ok = True
        messages: List[str] = []
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
                self.checker.check(tree, source=code, filename=mod_path, reset_symbols=(i == 0), import_order=module_order)
                if self.verbose:
                    self._vlog(f"[pengu] ok: {mod_path}")
            except Exception as e:  # noqa: BLE001 - any parse/semantic failure
                ok = False
                sub_list = getattr(e, "all_errors", None) or [e]
                for sub in sub_list:
                    err_line = getattr(sub, "line", None) or 0
                    err_col = getattr(sub, "column", None)
                    if err_col is None:
                        err_col = getattr(sub, "col", None) or 0
                    err_code = getattr(sub, "code", None) or ""
                    err_msg = getattr(sub, "message", None) or str(e)
                    code_str = f"[{err_code}] " if err_code else ""
                    messages.append(f"{mod_path}:{err_line}:{err_col} {code_str}{err_msg}")
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
        cc = self.config.cc
        out_type = self.config.output
        is_win = sys.platform == "win32"
        is_mac = sys.platform == "darwin"
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

        build_dir = self.get_build_directory()
        # Ensure build_dir is included in include search path for pengu_runtime.h
        common_flags.append(f"-I{build_dir}")

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
                    # POSIX: prefer the static archives in build/lib (searched
                    # first via -L) but fall back to the system libraries for
                    # the ones build_runtime.py skips on this platform
                    # (libxml2/libcurl/libmicrohttpd on Linux/macOS). Plain
                    # clang does not search the Homebrew prefix by default.
                    for brew_lib in ("/opt/homebrew/lib", "/usr/local/lib"):
                        if os.path.isdir(brew_lib) and f"-L{brew_lib}" not in link_flags:
                            link_flags.append(f"-L{brew_lib}")
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
        # --start-group, and Apple's ld64 (clang on macOS) rejects it outright,
        # so the group is applied only on GNU-ld hosts (Windows/MinGW, Linux).
        use_gnu_group = (
            not is_win or "cl" not in cc.lower() and "msvc" not in cc.lower()
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

        if out_type == OutputType.C:
            return []

        elif out_type == OutputType.OBJ:
            cmd = [cc, "-c", bundle_path] + c_sources + ["-o", output_path] + common_flags
            commands.append(cmd)

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
            return out_path, True

        commands = self.build_compile_commands(bundle_path, out_path)

        for cmd in commands:
            self._vlog(f"[pengu] running C compiler: {' '.join(cmd)}")
            t_cmd = time.time()
            res = subprocess.run(cmd, cwd=self.config.base_dir, capture_output=True, text=True)
            if self.verbose:
                self._vlog(f"[pengu] command finished in {time.time() - t_cmd:.3f}s (rc={res.returncode})")
            if res.returncode != 0:
                cmd_line = " ".join(cmd)
                detail = f"Command: {cmd_line}\nExit code: {res.returncode}"
                if res.stdout and res.stdout.strip():
                    detail += f"\n\nCompiler stdout:\n{res.stdout}"
                if res.stderr and res.stderr.strip():
                    detail += f"\n\nCompiler stderr:\n{res.stderr}"
                raise CompileFailedError(
                    f"C compilation failed ({self.config.name})\n\n{detail}"
                )

        return out_path, False


def build_project(
    config_path: Optional[str] = None,
    profile: str = "debug",
    entry: Optional[str] = None,
    output: Optional[str] = None,
    test: bool = False,
    defines: Optional[List[str]] = None,
    cc: Optional[str] = None,
    verbose: bool = False,
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

    print(f"\033[1;36m   Compiling\033[0m {config.name} v{config.version} ({config.output.value}) [{config.profile}]"
          + (" [test]" if test else ""))

    builder = PenguBuilder(config)
    builder.is_test_mode = test
    builder.verbose = verbose
    if output and (output.endswith(".c") or output == "bundle.c"):
        artifact, is_cached = builder.bundle(output_file=output)
    else:
        artifact, is_cached = builder.compile()
    elapsed = time.time() - t0

    if is_cached:
        print(f"\033[1;32m    Finished\033[0m (cached) [{config.profile}] target(s) in {elapsed:.2f}s -> {artifact}")
    else:
        print(f"\033[1;32m    Finished\033[0m [{config.profile}] target(s) in {elapsed:.2f}s -> {artifact}")
    return artifact


def check_project(
    config_path: Optional[str] = None,
    profile: str = "debug",
    entry: Optional[str] = None,
    defines: Optional[List[str]] = None,
    cc: Optional[str] = None,
    verbose: bool = False,
) -> bool:
    """Parses and type-checks every module without generating code (CI friendly).

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        entry: Optional entry file path override.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override (informational for 'when').
        verbose: True to print per-file progress.

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

    print(f"\033[1;36m   Checking\033[0m {config.name} v{config.version} [{config.profile}]")

    builder = PenguBuilder(config)
    builder.verbose = verbose
    ok, messages = builder.check_sources()
    elapsed = time.time() - t0

    if ok:
        print(f"\033[1;32m     Clean\033[0m no errors found in {elapsed:.2f}s")
    else:
        print(f"\033[1;31m   Errors\033[0m found in {elapsed:.2f}s")
        for msg in messages:
            print(f"  {msg}", file=sys.stderr)
    return ok


def _collect_pengu_files(paths: List[str]) -> List[str]:
    """Expands file/directory CLI arguments into a sorted .pengu file list."""
    files: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in os.walk(p):
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


def fmt_files(paths: List[str], check_only: bool = False, write: bool = True,
              indent: int = 2, tabs: bool = False, verbose: bool = False) -> int:
    """Formats .pengu files/directories with the standard style.

    Reuses the same formatting logic as the LSP's textDocument/formatting.

    Args:
        paths: Files and/or directories to format (directories are recursive).
        check_only: True to only report files that would change (never writes).
        write: True to overwrite files with formatted content.
        indent: Spaces per indentation level.
        tabs: True to indent with tabs.
        verbose: True to print every file considered.

    Returns:
        Number of files that changed (or would change with --check).
    """
    from pengu_lsp.formatting import format_pengu_source

    files = _collect_pengu_files(paths)
    changed: List[str] = []
    for fp in files:
        try:
            display = os.path.relpath(fp, os.getcwd())
        except ValueError:
            display = fp
        with open(fp, "r", encoding="utf-8") as f:
            original = f.read()
        formatted = format_pengu_source(original, tab_size=indent, insert_spaces=not tabs)
        if verbose:
            print(f"   fmt {display}")
        if formatted == original:
            continue
        changed.append(fp)
        if verbose or check_only:
            print(f"\033[1;33m would format\033[0m {display}")
        if write and not check_only:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(formatted)
            print(f"\033[1;32m  formatted\033[0m {display}")

    if check_only:
        print(f"\n{len(changed)} file(s) would be reformatted.")
    elif write:
        print(f"\n{len(changed)} file(s) formatted.")
    return len(changed)


def clean_project(config_path: Optional[str] = None) -> None:
    """Removes build directory and intermediate artifacts.

    Args:
        config_path: Optional path to config file or directory.
    """
    config = ProjectConfig.load(config_path)
    build_dir = os.path.abspath(os.path.join(config.base_dir, config.build_dir))

    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)
        print(f"\033[1;32m     Cleaned\033[0m build directory '{build_dir}'")
    else:
        print(f"\033[1;33m     Cleaned\033[0m nothing to clean.")


def _update_config_dependency(base_dir: str, dep_name: str, source: str, branch: Optional[str] = None) -> None:
    """Updates project configuration file (pengu.yaml, pengu.json, or pengu.toml) with a new dependency.

    Args:
        base_dir: Root directory of project.
        dep_name: Name identifier for the dependency.
        source: URL or local path.
        branch: Optional branch name.
    """
    candidates = ["pengu.yaml", "pengu.yml", "pengu.toml", "pengu.json", "Pengu.toml"]
    cfg_file = None
    for c in candidates:
        p = os.path.join(base_dir, c)
        if os.path.isfile(p):
            cfg_file = p
            break

    if cfg_file is None:
        cfg_file = os.path.join(base_dir, "pengu.yaml")

    ext = os.path.splitext(cfg_file)[1].lower()
    dep_info: Dict[str, Any] = {"url": source}
    if branch:
        dep_info["branch"] = branch

    if ext in (".yaml", ".yml"):
        content = ""
        if os.path.isfile(cfg_file):
            with open(cfg_file, "r", encoding="utf-8") as f:
                content = f.read()

        if yaml is not None:
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
        with open(cfg_file, "a", encoding="utf-8") as f:
            f.write(f'\n[dependencies.{dep_name}]\nurl = "{source}"\n')
            if branch:
                f.write(f'branch = "{branch}"\n')


def _run_dependency_build(target_dir: str, dep_name: str) -> bool:
    """Runs the dependency's build script (build.py / build.bat / build.sh / Makefile).

    Args:
        target_dir: Installed dependency directory.
        dep_name: Dependency display name.

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
        print(f"\033[1;36m    Building\033[0m dependency '{dep_name}' with {' '.join(build_cmd)}")
        res = subprocess.run(build_cmd, cwd=target_dir, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"\033[1;33m     Warning\033[0m build script returned code {res.returncode}:\n{res.stderr}", file=sys.stderr)
        return True
    return False


def update_project(config_path: Optional[str] = None, verbose: bool = False) -> int:
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
        print("\033[1;33m       Update\033[0m no dependencies configured.")
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
            print(f"\033[1;33m     Skipping\033[0m dependency '{dep_name}' (no source url configured).", file=sys.stderr)
            continue

        target_dir = os.path.join(lib_dir, dep_name)
        if not os.path.isdir(target_dir):
            print(f"\033[1;33m     Skipping\033[0m dependency '{dep_name}' (not installed at {target_dir}). "
                  f"Run 'pengu add {source}' first.", file=sys.stderr)
            continue

        print(f"\033[1;36m    Updating\033[0m dependency '{dep_name}'")

        git_dir = os.path.join(target_dir, ".git")
        if os.path.isdir(git_dir):
            cmd_fetch = ["git", "-C", target_dir, "pull"]
            if branch:
                cmd_fetch = ["git", "-C", target_dir, "pull", "origin", branch]
            if verbose:
                print(f"   $ {' '.join(cmd_fetch)}", file=sys.stderr)
            res = subprocess.run(cmd_fetch, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"\033[1;33m     Warning\033[0m git pull failed (code {res.returncode}):\n{res.stderr}", file=sys.stderr)
            else:
                tail = (res.stdout or res.stderr or "").strip()
                if tail:
                    print(f"   {tail.splitlines()[-1]}")
        else:
            print("   (local copy — nothing to pull)")

        _run_dependency_build(target_dir, dep_name)
        updated += 1

    print(f"\033[1;32m       Updated\033[0m {updated} dependency(ies).")
    return updated


def add_dependency(
    source: str,
    branch: Optional[str] = None,
    name: Optional[str] = None,
    config_path: Optional[str] = None,
    run_build: bool = True
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

    print(f"\033[1;36m    Fetching\033[0m dependency '{dep_name}' from {dep_source}")

    # 2. Check Git URL vs Local directory
    is_git_url = any(dep_source.startswith(p) for p in ("http://", "https://", "git://", "git@", "ssh://")) or dep_source.endswith(".git")

    if is_git_url:
        if os.path.isdir(target_dir):
            if os.path.isdir(os.path.join(target_dir, ".git")):
                print(f"\033[1;33m    Updating\033[0m existing Git repository in {target_dir}")
                cmd_fetch = ["git", "-C", target_dir, "pull"]
                subprocess.run(cmd_fetch, check=False)
            else:
                shutil.rmtree(target_dir, ignore_errors=True)
                clone_cmd = ["git", "clone"]
                if branch:
                    clone_cmd.extend(["-b", branch])
                clone_cmd.extend([dep_source, target_dir])
                res = subprocess.run(clone_cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"Git clone failed:\n{res.stderr}\n{res.stdout}")
        else:
            clone_cmd = ["git", "clone"]
            if branch:
                clone_cmd.extend(["-b", branch])
            clone_cmd.extend([dep_source, target_dir])
            res = subprocess.run(clone_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Git clone failed:\n{res.stderr}\n{res.stdout}")
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
        _run_dependency_build(target_dir, dep_name)

    # 5. Update configuration file
    _update_config_dependency(config.base_dir, dep_name, dep_source, branch)

    print(f"\033[1;32m       Added\033[0m dependency '{dep_name}' to {target_dir}")
    return target_dir


def init_project(
    name: str = "my_game",
    output_type: str = "exe",
    links: Optional[List[str]] = None,
    cc: str = "gcc",
    output_name: Optional[str] = None,
    target_dir: Optional[str] = None
) -> str:
    """Initializes a new PenguScript project directory with Cargo-style structure (src/, lib/, include/, c/).

    Args:
        name: Project directory name.
        output_type: Target artifact type ('exe', 'c', 'obj', 'static', 'shared').
        links: Optional list of library names to link (-l).
        cc: C compiler to configure.
        output_name: Optional custom output artifact name.
        target_dir: Optional destination base directory.

    Returns:
        Path to initialized project directory.
    """
    out_t = OutputType.from_string(output_type)
    out_name = output_name or name
    base_root = target_dir or os.getcwd()
    proj_dir = os.path.abspath(os.path.join(base_root, name)) if target_dir else os.path.abspath(name)

    src_dir = os.path.join(proj_dir, "src")
    lib_dir = os.path.join(proj_dir, "lib")
    inc_dir = os.path.join(proj_dir, "include")
    c_dir = os.path.join(proj_dir, "c")

    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(inc_dir, exist_ok=True)
    os.makedirs(c_dir, exist_ok=True)

    links_list = links or []
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

dependencies: {{}}

profiles:
  debug:
    cflags: ["-g", "-O0", "-Wall"]
    defines: ["DEBUG"]
  release:
    cflags: ["-O3", "-DNDEBUG"]
    defines: ["NDEBUG"]
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
        main_content = f"""// Static library {name}
weave add with a as int, b as int into int:
  return a + b

weave sub with a as int, b as int into int:
  return a - b
"""
    elif out_t == OutputType.SHARED:
        main_content = f"""// Shared library {name} - exported
weave add with a as int, b as int into int:
  return a + b
"""
    else:
        main_content = f"""weave main into void:
  var msg as string is "Hello from {name}!"
  calling print with msg
"""

    gitignore_content = """build/
*.o
*.a
*.lib
*.so
*.dylib
*.dll
*.exe
"""

    readme_content = f"""# {name}

A PenguScript v0.6 project targeting `{out_t.value}` output.

## Project Structure

```
{name}/
├── pengu.yaml          # Project & build configuration
├── src/                # PenguScript source files
│   └── main.pengu      # Main entry point
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

    with open(os.path.join(proj_dir, "pengu.yaml"), "w", encoding="utf-8") as f:
        f.write(yaml_content)
    with open(os.path.join(src_dir, "main.pengu"), "w", encoding="utf-8") as f:
        f.write(main_content)
    with open(os.path.join(proj_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    with open(os.path.join(proj_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\033[1;32m     Created\033[0m {out_t.value} project '{name}' at {proj_dir}")
    return proj_dir


def run_project(config_path: Optional[str] = None, profile: str = "debug", test: bool = False,
                defines: Optional[List[str]] = None, cc: Optional[str] = None,
                verbose: bool = False) -> int:
    """Builds and runs binary if output target is executable.

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        test: True to compile integrated unit tests in --test mode.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override.
        verbose: True to print module order, C commands and phase timings.

    Returns:
        Process exit code.
    """
    config = ProjectConfig.load(config_path, profile=profile)
    if cc:
        config.cc = cc
    artifact = build_project(config_path, profile=profile, test=test, defines=defines, cc=cc, verbose=verbose)
    if config.output == OutputType.EXE and os.path.isfile(artifact):
        print(f"\033[1;36m     Running\033[0m {artifact}\n")
        sys.stdout.flush()
        sys.stderr.flush()
        res = subprocess.run([artifact], cwd=config.base_dir)
        return res.returncode
    return 0


def run_script(script: str, defines: Optional[List[str]] = None,
               cc: Optional[str] = None, verbose: bool = False) -> int:
    """Compiles and runs a standalone .pengu file directly (script mode).

    The script itself is compiled as the entry point with the compile-time
    'main' variable set to true, so 'when main:' blocks inside it are emitted.
    Any module the script imports is compiled with 'main' false, regardless of
    this script's own mode.

    Args:
        script: Path to the .pengu file to execute.
        defines: Optional -D NAME / -D NAME=value compile-time defines.
        cc: Optional C compiler override (e.g. 'clang').
        verbose: True to print module order, C commands and phase timings.

    Returns:
        Process exit code of the executed binary.
    """
    script_abs = os.path.abspath(script)
    if not os.path.isfile(script_abs):
        raise FileNotFoundError(f"Script not found: {script}")
    if not script_abs.endswith(".pengu"):
        raise ValueError(f"Not a PenguScript file: {script}")

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
    )
    # Script runs get their own build sub-directory so concurrent/sequential
    # script executions (and test suites) never fight over a shared
    # bundle.c / pengu_runtime.h / executable in build/.
    cfg.build_dir = os.path.join("build", f"{out_name}_run")
    if defines:
        cfg.defines = list(cfg.defines or []) + defines
    if cc:
        cfg.cc = cc

    t0 = time.time()
    print(f"\033[1;36m   Scripting\033[0m {os.path.basename(script_abs)}")
    builder = PenguBuilder(cfg)
    builder.is_test_mode = False
    builder.entry_as_main = True
    builder.verbose = verbose
    artifact, is_cached = builder.compile()
    elapsed = time.time() - t0
    if is_cached:
        print(f"\033[1;32m    Finished\033[0m (cached) in {elapsed:.2f}s -> {artifact}")
    else:
        print(f"\033[1;32m    Finished\033[0m in {elapsed:.2f}s -> {artifact}")

    print(f"\033[1;36m     Running\033[0m {artifact}\n")
    sys.stdout.flush()
    sys.stderr.flush()
    res = subprocess.run([artifact], cwd=base_dir)
    return res.returncode


def test_project(config_path: Optional[str] = None, profile: str = "debug", entry: Optional[str] = None,
                 defines: Optional[List[str]] = None, cc: Optional[str] = None,
                 verbose: bool = False) -> int:
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
    config.output = OutputType.EXE

    t0 = time.time()
    print(f"\033[1;36m   Testing\033[0m {config.name} v{config.version} [--test, {config.profile}]")
    builder = PenguBuilder(config)
    builder.is_test_mode = True
    builder.verbose = verbose
    artifact, is_cached = builder.compile()
    elapsed = time.time() - t0
    if is_cached:
        print(f"\033[1;32m    Finished\033[0m (cached) in {elapsed:.2f}s -> {artifact}")
    else:
        print(f"\033[1;32m    Finished\033[0m in {elapsed:.2f}s -> {artifact}")

    print(f"\033[1;36m     Running\033[0m tests\n")
    sys.stdout.flush()
    sys.stderr.flush()
    res = subprocess.run([artifact], cwd=config.base_dir)
    return res.returncode


def create_cli_parser() -> argparse.ArgumentParser:
    """Constructs the Cargo-style CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pengu",
        description="PenguScript v0.6 Package & Build Manager",
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
  pengu clean
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    init_p = subparsers.add_parser("init", help="Create a new PenguScript project template")
    init_p.add_argument("name", help="Name of project directory to create")
    init_p.add_argument("--type", "-t", choices=["exe", "c", "obj", "static", "shared"], default="exe", help="Target output type")
    init_p.add_argument("--links", "-l", help="Comma-separated library names to link (e.g. raylib,m)")
    init_p.add_argument("--output-name", help="Custom output artifact base name")
    init_p.add_argument("--cc", default="gcc", help="C compiler command (default: gcc)")

    # add
    add_p = subparsers.add_parser("add", help="Add an external dependency or binding to the project")
    add_p.add_argument("source", help="Git repository URL or local folder path")
    add_p.add_argument("--branch", "-b", default=None, help="Git branch or tag to clone")
    add_p.add_argument("--name", "-n", default=None, help="Custom binding name override")
    add_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    add_p.add_argument("--no-build", action="store_true", help="Skip executing dependency build script")

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

    # test
    test_p = subparsers.add_parser("test", help="Compile and run the project's integrated unit tests")
    test_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    test_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    test_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    test_p.add_argument("--cc", default=None, help="C compiler override (e.g. 'clang')")
    test_p.add_argument("--verbose", action="store_true", help="Print module order, C commands and phase timings")
    test_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                        help="Compile-time define: -D NAME or -D os=linux / arch=x64 / compiler=clang / main (repeatable)")

    # check
    check_p = subparsers.add_parser("check", help="Parse and type-check every module without generating code (CI)")
    check_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    check_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    check_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    check_p.add_argument("--cc", default=None, help="C compiler override (informational for 'when compiler')")
    check_p.add_argument("--verbose", action="store_true", help="Print per-file progress")
    check_p.add_argument("-D", "--define", dest="defines", action="append", default=None,
                         help="Compile-time define: -D NAME or -D os=linux / arch=x64 / compiler=clang / main (repeatable)")

    # update
    update_p = subparsers.add_parser("update", help="Update dependencies: git pull + re-run build scripts")
    update_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    update_p.add_argument("--verbose", action="store_true", help="Print the git commands being executed")

    # bind
    bind_p = subparsers.add_parser("bind", help="Generate a .d.pengu binding from a C header")
    bind_p.add_argument("header", help="Path to the C header file (.h) to translate")
    bind_p.add_argument("--prefix", default="", help="Insignia prefix added to function names (e.g. webui_)")
    bind_p.add_argument("--links", nargs="*", default=[], help="Native libraries to emit as link \"...\" lines")
    bind_p.add_argument("--output", default="", help="Output .d.pengu path (default: next to the header)")
    bind_p.add_argument("--no-comments", action="store_true", help="Do not emit documentation comments")
    bind_p.add_argument("--ignore", nargs="*", default=[], help="Symbol names / regexes to skip")
    bind_p.add_argument("--include-paths", nargs="*", default=[], help="Extra include directories for the preprocessor")
    bind_p.add_argument("--no-cpp", dest="use_cpp", action="store_false", default=True,
                        help="Do not run the C preprocessor (simple headers only)")

    # fmt
    fmt_p = subparsers.add_parser("fmt", help="Format .pengu files or directories (standard style)")
    fmt_p.add_argument("paths", nargs="+", help="Files and/or directories to format (directories are searched recursively)")
    fmt_p.add_argument("--check", action="store_true", help="Do not write; exit non-zero when a file would change")
    fmt_p.add_argument("--write", action="store_true", default=True, help="Write formatted output back to disk (default)")
    fmt_p.add_argument("--indent", type=int, default=2, help="Spaces per indentation level (default: 2)")
    fmt_p.add_argument("--tabs", action="store_true", help="Indent with tabs instead of spaces")
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

    return parser


def _print_compile_error(err: "CompileFailedError") -> None:
    """Prints a formatted C-compilation error and exits with status 1."""
    print("\n\033[1;31mError:\033[0m", file=sys.stderr)
    print(str(err), file=sys.stderr)
    sys.exit(1)


def main():
    """Main execution entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()

    if args.command == "init":
        links_list = [i.strip() for i in args.links.split(",") if i.strip()] if args.links else []
        init_project(
            name=args.name,
            output_type=args.type,
            links=links_list,
            cc=args.cc,
            output_name=args.output_name
        )
    elif args.command == "add":
        add_dependency(
            source=args.source,
            branch=args.branch,
            name=args.name,
            config_path=args.config,
            run_build=not args.no_build
        )
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
                verbose=getattr(args, "verbose", False)
            )
        except CompileFailedError as e:
            _print_compile_error(e)
    elif args.command == "run":
        try:
            if getattr(args, "script", None):
                sys.exit(run_script(
                    script=args.script,
                    defines=getattr(args, "defines", None),
                    cc=getattr(args, "cc", None),
                    verbose=getattr(args, "verbose", False)
                ))
            sys.exit(run_project(
                config_path=args.config,
                profile=args.profile,
                test=getattr(args, "test", False),
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False)
            ))
        except CompileFailedError as e:
            _print_compile_error(e)
    elif args.command == "test":
        try:
            sys.exit(test_project(
                config_path=args.config,
                profile=args.profile,
                entry=getattr(args, "entry", None),
                defines=getattr(args, "defines", None),
                cc=getattr(args, "cc", None),
                verbose=getattr(args, "verbose", False)
            ))
        except CompileFailedError as e:
            _print_compile_error(e)
    elif args.command == "check":
        ok = check_project(
            config_path=args.config,
            profile=args.profile,
            entry=getattr(args, "entry", None),
            defines=getattr(args, "defines", None),
            cc=getattr(args, "cc", None),
            verbose=getattr(args, "verbose", False)
        )
        sys.exit(0 if ok else 1)
    elif args.command == "fmt":
        changed = fmt_files(
            paths=args.paths,
            check_only=args.check,
            write=args.write,
            indent=args.indent,
            tabs=args.tabs,
            verbose=args.verbose
        )
        sys.exit(1 if (args.check and changed > 0) else 0)
    elif args.command == "update":
        update_project(config_path=args.config, verbose=getattr(args, "verbose", False))
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
            )
            print(f"\033[1;32m     Bound\033[0m {args.header} -> {out}")
        except (HeaderParseError, FileNotFoundError, ValueError) as e:
            print(f"\033[1;31m       Bind\033[0m {e}", file=sys.stderr)
            sys.exit(1)
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
