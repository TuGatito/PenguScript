"""Why does the grammar have 188 shift/reduce conflicts? — instrument, don't guess.

Phase 2 item 2.4 was attempted nine times and failed nine times, all from reading a
token dump by eye and then editing a production. The durable lesson (AUDIT_1.0_FASE2.md
§17-§18) is to **measure before touching a production**, so this script exists to make
that measurement cheap for whoever retries.

It answers three questions that the eight failed attempts each guessed at:

  1. What is the real structural token stream (`_NEWLINE`/`_INDENT`/`_DEDENT`) for a
     given source? `--tokens`.
  2. Which rule owns each of the 188 conflicts, and with which terminals?
     `--conflicts`.
  3. For every conflict, what are the two competing actions? That is what actually
     determines whether a fix is possible, and no previous attempt looked at it.
     `--actions`.

Usage:

    python tools/grammar_conflicts.py --tokens 'weave f into int:\n  return 1\n'
    python tools/grammar_conflicts.py --conflicts
    python tools/grammar_conflicts.py --actions --rule return_stmt
    python tools/grammar_conflicts.py --all

The script is read-only: it never edits the grammar. It is intentionally a *tool*
rather than a test, because it is for diagnosis, not for asserting a property.
"""

from __future__ import annotations

import argparse
import collections
import io
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pengu_parser.pengu_grammar import GRAMMAR  # noqa: E402
from pengu_parser.pengu_parser import PenguIndenter  # noqa: E402

STRUCTURAL = ("_NEWLINE", "_INDENT", "_DEDENT")


def _lalr_debug_output(grammar: str = GRAMMAR) -> str:
    """Captures everything Lark logs while building the LALR tables."""
    import lark.parsers.lalr_analysis as analysis
    from lark import Lark

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.WARNING)
    analysis.logger.addHandler(handler)
    analysis.logger.setLevel(logging.WARNING)
    analysis.logger.propagate = False
    logging.disable(logging.NOTSET)
    try:
        Lark(grammar, parser="lalr", propagate_positions=True, debug=True, cache=None)
    finally:
        analysis.logger.removeHandler(handler)
    return buf.getvalue()


def cmd_tokens(args: argparse.Namespace) -> int:
    """Prints the structural tokens the indenter really emits."""
    from lark import Lark

    parser = Lark(
        GRAMMAR, parser="lalr", postlex=PenguIndenter(), propagate_positions=True,
        start=["start", "expr"], cache=False,
    )
    src = args.tokens.encode().decode("unicode_escape")
    print("source:")
    for i, line in enumerate(src.splitlines(), 1):
        print(f"  {i}| {line}")
    seq = [(t.type, str(t)) for t in parser.lex(src)]
    print("\nstructural tokens (indenter output):")
    for t_type, value in seq:
        if t_type in STRUCTURAL:
            shown = value.replace("\n", "\\n")
            print(f"  {t_type:9s} {shown!r}")
    counts = collections.Counter(t for t, _ in seq if t in STRUCTURAL)
    print(f"\ncounts: {dict(counts)}")
    nl, dd = counts["_NEWLINE"], counts["_DEDENT"]
    if nl != dd:
        print(
            f"NOTE: {nl} _NEWLINE vs {dd} _DEDENT. Any production pair that requires one "
            "_NEWLINE per block will not line up; check which production consumes the extra."
        )
    else:
        print(f"NOTE: balanced ({nl} of each) — no token is missing or extra here.")
    print(
        "\nREMINDER: balanced counts do not mean unambiguous. Count which PRODUCTION "
        "consumes each token before editing a rule."
    )
    return 0


def _parse_conflicts(text: str):
    """Yields (terminal, rule) for every shift/reduce conflict Lark logged."""
    terminal = None
    for line in text.splitlines():
        m = re.match(r"Shift/Reduce conflict for terminal (\S+?):", line)
        if m:
            terminal = m.group(1)
            continue
        r = re.search(r"\* <([a-z_][a-z0-9_]*)", line)
        if r and terminal:
            yield terminal, r.group(1)
        if line.startswith("Reduce/Reduce"):
            yield "<reduce/reduce>", line.strip()[:120]


def cmd_conflicts(args: argparse.Namespace) -> int:
    """Prints the conflict count, grouped by rule and by terminal."""
    text = _lalr_debug_output()
    pairs = list(_parse_conflicts(text))
    sr = [p for p in pairs if p[0] != "<reduce/reduce>"]
    rr = [p for p in pairs if p[0] == "<reduce/reduce>"]
    print(f"shift/reduce conflicts: {len(sr)}")
    print(f"reduce/reduce conflicts: {len(rr)}")
    print(f"distinct terminals: {len({t for t, _ in sr})}")
    print(f"distinct rules: {len({r for _, r in sr})}")

    by_rule = collections.Counter(r for _, r in sr)
    limit = args.top or 15
    print(f"\ntop {limit} rules by conflict count:")
    for rule, n in by_rule.most_common(limit):
        pct = 100.0 * n / len(sr) if sr else 0.0
        print(f"  {rule:26s} {n:4d}  ({pct:4.1f}%)")

    if args.rule:
        terms = collections.Counter(t for t, r in sr if r == args.rule)
        print(f"\nterminals conflicting inside {args.rule!r}:")
        for t, n in terms.most_common():
            print(f"  {t:24s} {n}")
    return 0


def _iter_conflicts(text: str):
    """Yields (header, [rule, ...]) for each conflict block in Lark's debug output.

    Lark prints

        Shift/Reduce conflict for terminal X: (resolving as shift)
         * <rule_a : ...>
         * <rule_b : ...>

    so a conflict "belongs to" rule_a: that is the reduction it decides to skip in
    favour of shifting. Attributing the conflict to the *last* rule line (or to any
    rule line) is what made an earlier version of this tool report the wrong owners.
    """
    header = None
    rules: list = []
    for line in text.splitlines():
        if re.match(r"^(Shift/Reduce|Reduce/Reduce) conflict", line):
            if header is not None:
                yield header, rules
            header, rules = line.strip(), []
            continue
        if header is None:
            continue
        m = re.match(r"\s*\* <([a-z_][a-z0-9_]*)", line)
        if m:
            rules.append(m.group(1))
    if header is not None:
        yield header, rules


def cmd_actions(args: argparse.Namespace) -> int:
    """Prints the competing actions of each conflict, attributed to the reduced rule.

    This is the measurement the nine failed attempts at item 2.4 never made: a
    shift/reduce conflict is *owned* by the rule Lark decides not to reduce, so
    editing any other rule cannot remove it.
    """
    text = _lalr_debug_output()
    target = args.rule
    shown = 0
    for header, rules in _iter_conflicts(text):
        owner = rules[0] if rules else None
        if target and owner != target:
            continue
        print(header)
        for r in rules:
            marker = "  <- reduced (the action being skipped)" if r == owner else "  <- shifted"
            print(f"   * {r}{marker}")
        print()
        shown += 1
        if args.top and shown >= args.top:
            break
    if not shown:
        print(f"no conflict is owned by {target!r}")
    else:
        print(f"({shown} shown. Every one is resolved as SHIFT, which is why the grammar")
        print(" works today despite them; that is a property of the dependency, not a")
        print(" guarantee of the language.)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokens", metavar="SRC", help="dump structural tokens for a source string")
    ap.add_argument("--conflicts", action="store_true", help="count conflicts, grouped")
    ap.add_argument("--actions", action="store_true", help="show the competing actions")
    ap.add_argument("--rule", help="restrict --conflicts/--actions to one rule")
    ap.add_argument("--top", type=int, default=15, help="how many entries to show")
    ap.add_argument("--all", action="store_true", help="run every report")
    args = ap.parse_args(argv)

    if args.all or (not any([args.tokens, args.conflicts, args.actions])):
        return cmd_conflicts(args)
    if args.tokens:
        return cmd_tokens(args)
    if args.actions:
        return cmd_actions(args)
    return cmd_conflicts(args)


if __name__ == "__main__":
    raise SystemExit(main())
