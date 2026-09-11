"""Compile-time configuration environment for PenguScript 'when' clauses.

Provides the evaluation variables exposed to conditional-compilation code:

- ``os``:  host operating system string ('windows', 'linux', 'macos', ...)
- ``arch``: host CPU architecture string ('x64', 'x86', 'arm64', ...)
- ``compiler``: C compiler in use ('gcc', 'clang', 'msvc', ...)
- ``main``: True when the current module is compiled as the script/entry point
  (enables ``when main:`` blocks); False for imported modules.
- ``defined(NAME)``: True when NAME was defined via -D NAME (or built-in defaults)

The evaluator is intentionally small: it understands literals, the three
context variables, ``defined(NAME)``, arithmetic/bitwise/comparison operators,
boolean not, and the ternary ``when a then b else c`` expression -- enough for
platform selection while keeping conditions side-effect free.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional, Set
from lark import Tree, Token


def default_os_name() -> str:
    """Maps sys.platform to the 'os' compile-time variable value."""
    p = sys.platform.lower()
    if p.startswith("win"):
        return "windows"
    if p.startswith("linux"):
        return "linux"
    if p.startswith("darwin"):
        return "macos"
    if p.startswith("freebsd"):
        return "freebsd"
    return p


def default_arch_name() -> str:
    """Maps platform.machine() to the 'arch' compile-time variable value."""
    m = (platform_machine() or "").lower()
    if m in ("x86_64", "amd64", "x64"):
        return "x64"
    if m in ("i386", "i486", "i586", "i686", "x86"):
        return "x86"
    if m in ("aarch64", "arm64"):
        return "arm64"
    if m in ("armv7l", "armv6l", "arm"):
        return "arm"
    return m or "unknown"


def platform_machine() -> Optional[str]:
    try:
        import platform
        return platform.machine()
    except Exception:
        return None


def default_compiler_name() -> str:
    """Picks a sensible default compiler; overridable via the CC/PENGU_CC env var."""
    cc = os.environ.get("PENGU_CC") or os.environ.get("CC") or "gcc"
    base = os.path.basename(cc).lower()
    if "clang" in base:
        return "clang"
    if "msvc" in base or base == "cl":
        return "msvc"
    if "gcc" in base or "mingw" in base:
        return "gcc"
    return base or "gcc"


class CompileTimeEnv:
    """Environment consulted when evaluating 'when' compile-time conditions."""

    def __init__(
        self,
        os_name: Optional[str] = None,
        arch: Optional[str] = None,
        compiler: Optional[str] = None,
        defines: Optional[Dict[str, bool]] = None,
        is_main: bool = False,
    ):
        self.os_name = os_name if os_name is not None else default_os_name()
        self.arch = arch if arch is not None else default_arch_name()
        self.compiler = compiler if compiler is not None else default_compiler_name()
        self.is_main = is_main
        merged: Dict[str, bool] = {
            self.os_name: True,
            self.arch: True,
            self.compiler: True,
        }
        if defines:
            for k, v in defines.items():
                if v is None:
                    merged[k] = True
                else:
                    merged[k] = bool(v)
        self.defines = merged

    def defined(self, name: str) -> bool:
        """Returns True when the given name was defined at compile time."""
        return bool(self.defines.get(name, False))

    def copy(self) -> "CompileTimeEnv":
        return CompileTimeEnv(
            os_name=self.os_name,
            arch=self.arch,
            compiler=self.compiler,
            defines=dict(self.defines),
            is_main=self.is_main,
        )

    def with_override(self, **kwargs) -> "CompileTimeEnv":
        """Returns a new env overriding os/arch/compiler or extra defines."""
        defines = dict(self.defines)
        defines.update(kwargs.pop("defines", {}) or {})
        return CompileTimeEnv(
            os_name=kwargs.pop("os_name", self.os_name),
            arch=kwargs.pop("arch", self.arch),
            compiler=kwargs.pop("compiler", self.compiler),
            defines=defines,
            is_main=kwargs.pop("is_main", self.is_main),
        )

    def with_main(self, is_main: bool = True) -> "CompileTimeEnv":
        """Returns a copy of this environment with the 'main' flag adjusted."""
        return self.with_override(is_main=is_main)

    def __repr__(self) -> str:
        return f"CompileTimeEnv(os={self.os_name!r}, arch={self.arch!r}, compiler={self.compiler!r}, main={self.is_main!r})"


def default_env() -> CompileTimeEnv:
    """Builds the environment used when the caller does not supply one."""
    return CompileTimeEnv()


def parse_cli_defines(defines: Optional[list]) -> CompileTimeEnv:
    """Builds an environment from repeated -D NAME / -D NAME=value CLI arguments.

    Plain '-D NAME' sets defined(NAME); '-D os=linux', '-D arch=x64' and
    '-D compiler=clang' override the corresponding context variables.
    '-D main' / '-D main=true' enables the 'main' compile-time flag (the flag
    is *not* added to the macro set: 'main' is only ever consulted by 'when').
    """
    if not defines:
        return default_env()
    dflt = default_env()
    os_name = dflt.os_name
    arch = dflt.arch
    compiler = dflt.compiler
    is_main = False
    extras: Dict[str, bool] = {}
    for item in defines:
        spec = str(item)
        if "=" in spec:
            key, _, value = spec.partition("=")
            key = key.strip()
            value = value.strip()
            if key == "os":
                os_name = value
            elif key == "arch":
                arch = value
            elif key == "compiler":
                compiler = value
            elif key == "main":
                low = value.lower()
                is_main = low not in ("0", "false", "no", "off")
            else:
                extras[key] = bool(value)
        else:
            name = spec.strip()
            if name:
                if name == "main":
                    is_main = True
                else:
                    extras[name] = True
    return CompileTimeEnv(os_name=os_name, arch=arch, compiler=compiler, defines=extras, is_main=is_main)


def main_flag_requested(defines: Optional[list]) -> bool:
    """Returns True when a -D main / -D main=true flag appears in the defines.

    Used by the builder to enable entry-main semantics only for the entry module
    (imported modules always compile with 'main' false).
    """
    if not defines:
        return False
    for item in defines:
        spec = str(item)
        if "=" in spec:
            key, _, value = spec.partition("=")
            if key.strip() == "main":
                return value.strip().lower() not in ("0", "false", "no", "off")
        elif spec.strip() == "main":
            return True
    return False


def eval_comptime(env: CompileTimeEnv, node: Any) -> Optional[Any]:
    """Evaluates a compile-time expression tree.

    Returns the Python value (bool/int/float/str) or None when the expression is
    not a compile-time constant.
    """
    if node is None:
        return None
    if isinstance(node, Token):
        if node.type == "INT":
            return int(str(node), 0)
        if node.type == "FLOAT":
            return float(str(node))
        if node.type == "STRING":
            return str(node)[1:-1] if (str(node).startswith('"') and str(node).endswith('"')) else str(node)
        return None
    if not isinstance(node, Tree):
        return None

    rule = node.data
    if rule == "int_lit":
        return int(str(node.children[0]), 0)
    if rule == "float_lit":
        return float(str(node.children[0]))
    if rule == "string_lit":
        raw = str(node.children[0]) if node.children else ""
        return raw[1:-1] if (raw.startswith('"') and raw.endswith('"') and len(raw) >= 2) else raw
    if rule in ("true_lit",):
        return True
    if rule in ("false_lit",):
        return False
    if rule == "var_ref":
        name = str(node.children[0])
        if name == "os":
            return env.os_name
        if name == "arch":
            return env.arch
        if name == "compiler":
            return env.compiler
        if name == "main":
            return env.is_main
        return None
    if rule == "defined_expr":
        name = str(node.children[0]) if node.children else ""
        return env.defined(name)
    if rule == "neg":
        v = eval_comptime(env, node.children[0])
        return -v if isinstance(v, (int, float)) else None
    if rule == "log_not":
        v = eval_comptime(env, node.children[0])
        return not bool(v) if isinstance(v, bool) else None
    if rule == "bit_not":
        v = eval_comptime(env, node.children[0])
        return ~int(v) if isinstance(v, int) else None

    # Boolean logical operators short-circuit: the right operand is only
    # evaluated when the left one does not settle the result.
    if rule in ("bool_and", "bool_or"):
        left = eval_comptime(env, node.children[0])
        if not isinstance(left, bool):
            return None
        if rule == "bool_and" and left is False:
            return False
        if rule == "bool_or" and left is True:
            return True
        right = eval_comptime(env, node.children[1])
        return right if isinstance(right, bool) else None

    if rule in ("add", "sub", "mul", "div", "mod", "bitwise_or", "bitwise_and", "bitwise_xor", "shl", "shr"):
        left = eval_comptime(env, node.children[0])
        right = eval_comptime(env, node.children[1])
        if left is None or right is None:
            return None
        try:
            if rule == "add":
                return left + right
            if rule == "sub":
                return left - right
            if rule == "mul":
                return left * right
            if rule == "div":
                return left // right if isinstance(left, int) and isinstance(right, int) else left / right
            if rule == "mod":
                return left % right
            if rule == "bitwise_or":
                return left | right if isinstance(left, bool) and isinstance(right, bool) else int(left) | int(right)
            if rule == "bitwise_and":
                return left & right if isinstance(left, bool) and isinstance(right, bool) else int(left) & int(right)
            if rule == "bitwise_xor":
                return left ^ right if isinstance(left, bool) and isinstance(right, bool) else int(left) ^ int(right)
            if rule == "shl":
                return int(left) << int(right)
            if rule == "shr":
                return int(left) >> int(right)
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            return None
        return None

    if rule in ("eq", "ne", "lt", "le", "gt", "ge"):
        left = eval_comptime(env, node.children[0])
        right = eval_comptime(env, node.children[1])
        if left is None or right is None:
            return None
        try:
            if rule == "eq":
                return left == right
            if rule == "ne":
                return left != right
            if rule == "lt":
                return left < right
            if rule == "le":
                return left <= right
            if rule == "gt":
                return left > right
            if rule == "ge":
                return left >= right
        except Exception:
            return None
        return None

    if rule == "if_expr":
        cond = eval_comptime(env, node.children[0])
        if cond is True:
            return eval_comptime(env, node.children[1])
        if cond is False:
            return eval_comptime(env, node.children[2])
        return None

    if rule == "when_expr":
        cond = eval_comptime(env, node.children[0])
        if cond is True:
            return eval_comptime(env, node.children[1])
        if cond is False:
            return eval_comptime(env, node.children[2])
        return None

    if len(node.children) == 1:
        return eval_comptime(env, node.children[0])
    return None
