"""Fuzzy string matching and Levenshtein distance suggestions for diagnostics."""

from __future__ import annotations

from collections.abc import Iterable


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def find_best_matches(
    query: str,
    candidates: Iterable[str],
    limit: int = 3,
    max_distance: int = 3,
) -> list[str]:
    """Find up to `limit` closest candidate strings within `max_distance`."""
    scored: list[tuple[int, str]] = []
    seen: set[str] = set()

    for cand in candidates:
        if cand == query or cand in seen:
            continue
        seen.add(cand)
        dist = levenshtein_distance(query, cand)
        if dist <= max_distance:
            scored.append((dist, cand))

    scored.sort(key=lambda x: (x[0], x[1]))
    return [cand for _, cand in scored[:limit]]


__all__ = ["find_best_matches", "levenshtein_distance"]
