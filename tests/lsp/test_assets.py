#!/usr/bin/env python3
"""Static checks for the VS Code language assets."""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXT = ROOT / "vscode-extension"


def fail(msg: str) -> None:
    raise AssertionError(msg)


def load(path: pathlib.Path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"{path}: {exc}")


def main() -> int:
    grammar = load(EXT / "syntaxes" / "pengus.tmLanguage.json")
    text = json.dumps(grammar)
    for word in ["set", "derive", "cyclus", "antiquus", "enchanting", "bind", "seal", "Real", "Iterabilis"]:
        if word not in text:
            fail(f"grammar misses {word}")
    includes = [p.get("include") for p in grammar["patterns"] if isinstance(p, dict)]
    if includes.index("#test_definition") > includes.index("#keywords"):
        fail("test_definition must run before keywords")
    if "#type_use" not in includes:
        fail("grammar misses type_use")
    if "##" not in text:
        fail("grammar misses doc comments")

    snippets = load(EXT / "snippets" / "pengus.json")
    if len(snippets) < 100:
        fail("too few snippets")
    prefixes = set()
    for name, body in snippets.items():
        if not body.get("body"):
            fail(f"empty snippet {name}")
        prefix = body.get("prefix")
        if isinstance(prefix, list):
            prefix = "|".join(prefix)
        key = str(prefix)
        if key in prefixes:
            fail(f"duplicate prefix {key}")
        prefixes.add(key)
    main = " ".join(snippets["Main Weave Entry Point (int)"]["body"])
    if "import std.spark" not in main:
        fail("main snippet misses std.spark import")
    concept = " ".join(snippets["Concept Definition"]["body"])
    if "with self" in concept:
        fail("concept snippet has an invalid self parameter")
    bind = " ".join(snippets["Concept Bind Implementation"]["body"])
    if "with self" in bind:
        fail("bind snippet has an invalid self parameter")

    config = load(EXT / "language-configuration.json")
    if not config.get("indentationRules"):
        fail("language configuration misses indentationRules")

    package = load(EXT / "package.json")
    engine = package.get("engines", {}).get("vscode", "")
    if engine != "^1.82.0":
        fail(f"unexpected engine {engine}")
    if "iconThemes" in package.get("contributes", {}):
        fail("invalid iconThemes contribution")
    commands = {c["command"] for c in package["contributes"]["commands"]}
    for cmd in ["pengus.run", "pengus.test", "pengus.runFile", "pengus.testFile", "pengus.showMenu"]:
        if cmd not in commands:
            fail(f"missing command {cmd}")
    if not package.get("contributes", {}).get("semanticTokenScopes"):
        fail("missing semanticTokenScopes")

    print("OK language asset tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
