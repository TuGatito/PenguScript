#!/usr/bin/env python3
"""Generate / check the table of contents of a Markdown document.

The TOC lives between the markers ``<!-- toc -->`` and ``<!-- /toc -->``.
Entries are the H2 and H3 headings of the document, in order.

Usage:
    tools/docs/toc.py docs/LANGUAGE.md            # print the TOC
    tools/docs/toc.py docs/LANGUAGE.md --write    # replace the block
    tools/docs/toc.py docs/LANGUAGE.md --check    # exit 1 if stale
"""
import re
import sys

START = "<!-- toc -->"
END = "<!-- /toc -->"

HEADING = re.compile(r"^(#{2,3})\s+(.*?)\s*$")


def slug(text: str) -> str:
    """GitHub-flavoured anchor for a heading."""
    text = text.strip()
    text = re.sub(r"`([^`]*)`", r"\1", text)          # strip inline code
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # strip links
    text = text.replace("*", "").replace("_", "_")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text.strip())
    return text


def headings(lines):
    out = []
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            out.append((len(m.group(1)), m.group(2)))
    return out


def build(doc: str) -> str:
    lines = doc.splitlines()
    items = []
    for level, text in headings(lines):
        # drop anchors that would only add noise
        label = text
        indent = "" if level == 2 else "  "
        items.append(f"{indent}- [{label}](#{slug(text)})")
    return START + "\n" + "\n".join(items) + "\n" + END


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--print"
    with open(path, encoding="utf-8") as fh:
        doc = fh.read()

    block = build(doc)
    if mode == "--print":
        print(block)
        return 0

    if START not in doc or END not in doc:
        print(f"{path}: missing {START} / {END} markers", file=sys.stderr)
        return 2

    new = re.sub(re.escape(START) + r".*?" + re.escape(END), block, doc, flags=re.S)
    if mode == "--check":
        if new != doc:
            print(f"{path}: TOC is stale (run tools/docs/toc.py {path} --write)", file=sys.stderr)
            return 1
        print(f"{path}: TOC ok")
        return 0

    if mode == "--write":
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new)
        print(f"{path}: TOC updated")
        return 0

    print(f"unknown mode {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
