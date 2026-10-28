#!/usr/bin/env python3
"""Entry point for the frozen ``pengu-bind`` helper (F10).

This is build-time only: release artifacts contain the PyInstaller onefile
binary, never this script.  The generator itself lives in ``pengu_bind.py``.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

VERSION = "0.10.0"
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pengu-bind",
        description="Generate a .d.pengu binding from a C header.",
    )
    p.add_argument("--version", action="version", version=f"pengu-bind {VERSION}")
    p.add_argument("header", nargs="?", help="C header file")
    p.add_argument("--prefix", default="")
    p.add_argument("--links", nargs="*", default=[])
    p.add_argument("--output", default="", help="Output path, or '-' for stdout")
    p.add_argument("--no-comments", action="store_true")
    p.add_argument("--ignore", nargs="*", default=[])
    p.add_argument("--include-paths", nargs="*", default=[])
    p.add_argument("--define", "-D", dest="defines", action="append", default=[])
    p.add_argument("--cpp-flags", default=None)
    p.add_argument("--system-includes", action="store_true", default=False)
    p.add_argument("--preprocessed", default=None)
    p.add_argument("--no-blank-extensions", dest="blank_extensions",
                   action="store_false", default=True)
    p.add_argument("--no-cpp", dest="use_cpp", action="store_false", default=True)
    p.add_argument("--auto-import", dest="auto_import", default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.header:
        print("pengu-bind: missing HEADER", file=sys.stderr)
        return 2
    try:
        from pengu_bind import HeaderParseError, generate_bind_file
    except Exception as exc:  # pragma: no cover - broken frozen bundle
        print(f"pengu-bind: cannot load generator: {exc}", file=sys.stderr)
        return 1

    stdout = args.output == "-"
    output = ""
    temp_path = ""
    if stdout:
        fd, temp_path = tempfile.mkstemp(prefix="pengu-bind-", suffix=".d.pengu")
        os.close(fd)
        output = temp_path
    else:
        output = args.output or ""
    try:
        out = generate_bind_file(
            header=args.header,
            output=output or None,
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
        if stdout:
            with open(out, "r", encoding="utf-8") as f:
                sys.stdout.write(f.read())
        else:
            print(f"     Bound {args.header} -> {out}", file=sys.stderr)
        return 0
    except (HeaderParseError, FileNotFoundError, ValueError) as exc:
        print(f"pengu-bind: {exc}", file=sys.stderr)
        return 1
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
