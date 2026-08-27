#!/usr/bin/env python3
"""PenguScript Project & Build Manager (Cargo-style CLI).

Provides project configuration management, multi-target compilation (exe, c, obj, static, shared),
custom library linking (-l), build directory isolation, incremental compilation caching,
debug/release profiles, template initialization, and multi-platform compilation support.
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
from typing import List, Dict, Optional, Any, Tuple
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


@dataclass
class ProjectConfig:
    """Project configuration specifying build rules, libraries, profiles, and output target.

    Attributes:
        name: Project or binary name.
        version: Semantic version string.
        entry: Main entry .pengu source file.
        output: Target output type (exe, c, obj, static, shared).
        output_name: Base name for generated artifact.
        build_dir: Relative or absolute directory for intermediate/final build artifacts.
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
    entry: str = "main.pengu"
    output: OutputType = OutputType.EXE
    output_name: str = "app"
    build_dir: str = "build"
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
            "cflags": ["-O3", "-DNDEBUG"],
            "defines": ["NDEBUG"],
        }
    })
    profile: str = "debug"
    base_dir: str = field(default_factory=lambda: os.path.abspath(os.getcwd()))

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

        name = str(proj_sec.get("name", "pengu_app"))
        version = str(proj_sec.get("version", "0.1.0"))
        entry = str(proj_sec.get("entry", "main.pengu"))
        output_str = str(proj_sec.get("output", "exe"))
        output_type = OutputType.from_string(output_str)
        output_name = str(proj_sec.get("output_name", name))
        build_dir = str(build_sec.get("build_dir", "build"))

        includes = list(build_sec.get("includes", []))
        links = list(build_sec.get("links", []))
        lib_dirs = list(build_sec.get("lib_dirs", []))
        include_dirs = list(build_sec.get("include_dirs", []))
        cflags = list(build_sec.get("cflags", ["-O2", "-Wall", "-std=c11"]))
        ldflags = list(build_sec.get("ldflags", []))
        defines = list(build_sec.get("defines", []))
        cc = str(build_sec.get("cc", "gcc"))

        # Load custom profiles if present
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
        self.parser = PenguParser()
        self.checker = PenguChecker(base_dir=config.base_dir)

    def get_build_directory(self) -> str:
        """Returns absolute path to the designated build directory."""
        if os.path.isabs(self.config.build_dir):
            return self.config.build_dir
        return os.path.abspath(os.path.join(self.config.base_dir, self.config.build_dir))

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
            os.path.join(exe_dir, "runtime", "pengu_runtime.h"),
            os.path.join(exe_dir, "pengu_runtime.h"),
            os.path.join(exe_dir, "..", "runtime", "pengu_runtime.h"),
            os.path.join(meipass, "runtime", "pengu_runtime.h") if meipass else "",
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
            shutil.copy(found_src, dest_file)

        return dest_file

    def is_bundle_up_to_date(self, bundle_path: str, module_order: List[str]) -> bool:
        """Checks if bundle.c is newer than all source modules, config files, and options hash.

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
        entry_abs = os.path.join(self.config.base_dir, self.config.entry)

        # 1. Resolve module order
        module_order: List[str] = []
        if os.path.isfile(entry_abs):
            module_order = resolve_imports(self.config.base_dir, self.config.entry, self.parser)
        elif self.source_code is not None:
            module_order = [entry_abs]
        else:
            module_order = [entry_abs]

        # 2. Check if cached bundle.c is up-to-date
        if self.source_code is None and self.is_bundle_up_to_date(bundle_path, module_order):
            self.locate_and_copy_runtime(build_dir)
            return bundle_path, True

        # 3. Check all source files with PenguChecker and collect parsed trees
        parsed_trees: List[Tuple[str, Tree]] = []
        for i, mod_path in enumerate(module_order):
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


        # 4. Copy runtime header to build directory
        self.locate_and_copy_runtime(build_dir)

        # 5. Generate bundle.c via PenguCodegen
        from pengu_parser.pengu_codegen import PenguCodegen
        codegen = PenguCodegen(self.checker.symbols, module_order, self.config.base_dir)
        codegen.collect_declarations(parsed_trees)
        is_lib = self.config.output in (OutputType.STATIC, OutputType.SHARED, OutputType.OBJ)
        codegen.generate_bundle(
            custom_includes=self.config.includes,
            is_library=is_lib,
            output_path=bundle_path
        )

        # 6. Save compilation configuration hash
        hash_file = os.path.join(os.path.dirname(bundle_path), ".bundle_hash")
        try:
            with open(hash_file, "w", encoding="utf-8") as f:
                f.write(self.compute_config_hash())
        except Exception:
            pass

        return bundle_path, False


    def build_compile_commands(self, bundle_path: str, output_path: str) -> List[List[str]]:
        """Assembles list of shell commands required to compile bundle into target artifact.

        Merges base compiler flags with active profile flags (debug / release).

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
        # Candidate include and lib paths
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

        for inc in self.config.include_dirs:
            common_flags.append(f"-I{inc}")
        for c_inc in extra_inc_candidates:
            if c_inc and os.path.isdir(c_inc):
                c_flag = f"-I{c_inc}"
                if c_flag not in common_flags:
                    common_flags.append(c_flag)

        for ldir in self.config.lib_dirs:
            common_flags.append(f"-L{ldir}")
        for c_ldir in extra_lib_candidates:
            if c_ldir and os.path.isdir(c_ldir):
                c_flag = f"-L{c_ldir}"
                if c_flag not in common_flags:
                    common_flags.append(c_flag)

        link_flags: List[str] = []
        for link in self.config.links:
            if link in ("pengu_runtime", "libpengu_runtime"):
                link_flags.extend([
                    "-lpengu_runtime", "-lpcre2-8", "-lxml2", "-lcurl",
                    "-lmbedcrypto", "-lmicrohttpd", "-lz"
                ])
                if is_win:
                    link_flags.extend(["-lws2_32", "-lwinmm", "-ladvapi32", "-lcrypt32", "-lbcrypt"])
                else:
                    link_flags.extend(["-pthread", "-lm"])
            else:
                link_flags.append(f"-l{link}")

        for ldflag in self.config.ldflags:
            link_flags.append(ldflag)

        if out_type == OutputType.C:
            return []

        elif out_type == OutputType.OBJ:
            cmd = [cc, "-c", bundle_path, "-o", output_path] + common_flags
            commands.append(cmd)

        elif out_type == OutputType.STATIC:
            temp_obj = os.path.join(build_dir, "bundle.o")
            cmd_compile = [cc, "-c", bundle_path, "-o", temp_obj] + common_flags

            if is_win and ("cl" in cc.lower() or "msvc" in cc.lower()):
                cmd_ar = ["lib", f"/OUT:{output_path}", temp_obj]
            else:
                cmd_ar = ["ar", "rcs", output_path, temp_obj]

            commands.append(cmd_compile)
            commands.append(cmd_ar)

        elif out_type == OutputType.SHARED:
            if is_win:
                cmd = [cc, "-shared", bundle_path, "-o", output_path] + common_flags + link_flags
            elif is_mac:
                dyn_flag = "-dynamiclib" if "clang" in cc else "-shared"
                cmd = [cc, "-fPIC", dyn_flag, bundle_path, "-o", output_path] + common_flags + link_flags
            else:
                cmd = [cc, "-fPIC", "-shared", bundle_path, "-o", output_path] + common_flags + link_flags
            commands.append(cmd)

        else:  # EXE
            cmd = [cc, bundle_path, "-o", output_path] + common_flags + link_flags
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
            res = subprocess.run(cmd, cwd=self.config.base_dir, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Compilation failed with command: {' '.join(cmd)}\nStderr: {res.stderr}\nStdout: {res.stdout}"
                )

        return out_path, False


def build_project(
    config_path: Optional[str] = None,
    profile: str = "debug",
    entry: Optional[str] = None,
    output: Optional[str] = None
) -> str:
    """Builds project from configuration file with status printing.

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').
        entry: Optional entry file path override.
        output: Optional output file path override.

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

    print(f"\033[1;36m   Compiling\033[0m {config.name} v{config.version} ({config.output.value}) [{config.profile}]")

    builder = PenguBuilder(config)
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


def init_project(
    name: str = "my_game",
    output_type: str = "exe",
    links: Optional[List[str]] = None,
    cc: str = "gcc",
    output_name: Optional[str] = None,
    target_dir: Optional[str] = None
) -> str:
    """Initializes a new PenguScript project directory with configuration, source template, .gitignore and README.

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
    os.makedirs(proj_dir, exist_ok=True)

    links_list = links or []
    links_formatted = json.dumps(links_list)

    yaml_content = f"""project:
  name: "{name}"
  version: "0.1.0"
  entry: "main.pengu"
  output: "{out_t.value}"
  output_name: "{out_name}"

build:
  build_dir: "build"
  includes: []
  links: {links_formatted}
  lib_dirs: []
  include_dirs: []
  cflags: ["-Wall", "-std=c11"]
  ldflags: []
  defines: []
  cc: "{cc}"

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

## Building and Running

```bash
# Build in debug profile
python pengu_project.py build

# Build optimized release profile
python pengu_project.py build --profile release

# Run executable target
python pengu_project.py run

# Clean build artifacts
python pengu_project.py clean
```
"""

    with open(os.path.join(proj_dir, "pengu.yaml"), "w", encoding="utf-8") as f:
        f.write(yaml_content)
    with open(os.path.join(proj_dir, "main.pengu"), "w", encoding="utf-8") as f:
        f.write(main_content)
    with open(os.path.join(proj_dir, ".gitignore"), "w", encoding="utf-8") as f:
        f.write(gitignore_content)
    with open(os.path.join(proj_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\033[1;32m     Created\033[0m {out_t.value} project '{name}' at {proj_dir}")
    return proj_dir


def run_project(config_path: Optional[str] = None, profile: str = "debug") -> int:
    """Builds and runs binary if output target is executable.

    Args:
        config_path: Optional path to config file or directory.
        profile: Selected build profile ('debug' or 'release').

    Returns:
        Process exit code.
    """
    config = ProjectConfig.load(config_path, profile=profile)
    artifact = build_project(config_path, profile=profile)
    if config.output == OutputType.EXE and os.path.isfile(artifact):
        print(f"\033[1;36m     Running\033[0m {artifact}\n")
        sys.stdout.flush()
        sys.stderr.flush()
        res = subprocess.run([artifact], cwd=config.base_dir)
        return res.returncode
    return 0



def create_cli_parser() -> argparse.ArgumentParser:
    """Constructs the Cargo-style CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="pengu",
        description="PenguScript v0.6 Package & Build Manager",
        epilog="""Examples:
  pengu init my_game --type exe
  pengu init my_lib --type static --links m,pthread
  pengu build --profile release
  pengu run --profile debug
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

    # build
    build_p = subparsers.add_parser("build", help="Compile the project according to configuration")
    build_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    build_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    build_p.add_argument("--entry", "-e", default=None, help="Override entry file path")
    build_p.add_argument("--output", "-o", default=None, help="Override output file path (e.g. build/bundle.c)")

    # run
    run_p = subparsers.add_parser("run", help="Build and execute the project target")
    run_p.add_argument("--profile", "-p", default="debug", help="Build profile (e.g. debug, release)")
    run_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")
    run_p.add_argument("--entry", "-e", default=None, help="Override entry file path")

    # clean
    clean_p = subparsers.add_parser("clean", help="Remove build directory and generated artifacts")
    clean_p.add_argument("--config", "-c", default=None, help="Path to config file or project root")

    # lsp
    lsp_p = subparsers.add_parser("lsp", help="Launch the PenguScript Language Server Protocol (LSP)")
    lsp_p.add_argument("--stdio", action="store_true", default=True, help="Run LSP server over standard I/O (default)")
    lsp_p.add_argument("--tcp", action="store_true", help="Run LSP server over TCP socket")
    lsp_p.add_argument("--host", default="127.0.0.1", help="TCP bind host (default: 127.0.0.1)")
    lsp_p.add_argument("--port", type=int, default=2087, help="TCP bind port (default: 2087)")

    return parser


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
    elif args.command == "build":
        build_project(
            config_path=args.config,
            profile=args.profile,
            entry=getattr(args, "entry", None),
            output=getattr(args, "output", None)
        )
    elif args.command == "run":
        sys.exit(run_project(config_path=args.config, profile=args.profile))
    elif args.command == "clean":
        clean_project(config_path=args.config)
    elif args.command == "lsp":
        from pengu_lsp.server import server
        if args.tcp:
            print(f"Starting PenguScript LSP server on {args.host}:{args.port}...", file=sys.stderr)
            server.start_tcp(args.host, args.port)
        else:
            server.start_io()
    else:
        parser.print_help()



if __name__ == "__main__":
    main()
