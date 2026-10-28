#!/usr/bin/env bash
# Fast, currently-green compiler smoke used by CI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
cd "$ROOT"
for f in \
  tests/pengu/lexer_unit.pengu \
  tests/pengu/parser_unit.pengu \
  tests/pengu/lexer_corpus.pengu \
  tests/pengu/parser_corpus.pengu \
  tests/pengu/flag.pengu; do
  if [ -f "$f" ]; then
    "$PSC" run "$f" --no-cache
  fi
done
echo "OK compiler smoke"
