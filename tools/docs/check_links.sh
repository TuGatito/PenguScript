#!/usr/bin/env bash
# Check that relative markdown links in docs/ resolve to existing files.
# Usage: tools/docs/check_links.sh [dir ...]
set -u
cd "$(dirname "$0")/../.." || exit 1

dirs=("$@")
if [ ${#dirs[@]} -eq 0 ]; then dirs=(docs); fi

fail=0
total=0
for d in "${dirs[@]}"; do
  [ -d "$d" ] || continue
  while IFS= read -r f; do
    # strip fenced code blocks before scanning
    awk 'BEGIN{fence=0} /^[[:space:]]*```/{fence=!fence; next} fence==0{print}' "$f" |
    grep -oE '\]\([^)#]+(#[^)]*)?\)' |
    sed -E 's/^\]\(//; s/\)$//; s/#.*$//' |
    grep -vE '^(https?:|mailto:|#)' |
    while IFS= read -r link; do
      case "$link" in
        "") continue ;;
      esac
      target="$(dirname "$f")/$link"
      if [ ! -e "$target" ]; then
        printf '%s: broken link -> %s\n' "$f" "$link"
        echo "$f|$link" >> /tmp/pengu_doc_broken.$$
      fi
    done
  done < <(find "$d" -name '*.md' -not -path '*/api/*')
done

if [ -f /tmp/pengu_doc_broken.$$ ]; then
  total=$(wc -l < /tmp/pengu_doc_broken.$$)
  rm -f /tmp/pengu_doc_broken.$$
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "check_links: OK"
else
  echo "check_links: $total broken link(s)"
fi
exit "$fail"
