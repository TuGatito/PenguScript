#!/usr/bin/env python3
"""pengu_semver.py — SemVer parsing and constraint matching for dependencies.

PenguScript has no central registry: a dependency is a git (or local) repository
and its versions are the repository's **git tags**.  This module implements the
pure half of roadmap 4.2 — parsing ``1.2.3`` tags and the constraint syntax
accepted in the manifest (``^1.2.0``, ``~1.2.0``, ``>=1.0, <2.0``, ``=1.2.3``,
``1.2.3``, ``*``) — plus "pick the highest tag that satisfies the constraints".

The resolver (see ``pengu_project.resolve_transitive_dependencies``) is
deliberately forward-only: it never backtracks.  If two requirements cannot be
satisfied at once it fails with an actionable conflict error instead of trying
exponential combinations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

_VERSION_RE = re.compile(
    r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.\-]+))?(?:\+[0-9A-Za-z.\-]+)?$"
)
_CONSTRAINT_RE = re.compile(r"^\s*(\^|~|>=|<=|>|<|=|==)?\s*v?([0-9][0-9A-Za-z.\-+]*|\*|x|X)\s*$")


class SemVerError(ValueError):
    """Raised for a malformed version or constraint."""


@dataclass(frozen=True)
class Version:
    """A parsed semantic version."""

    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, text: str) -> "Version":
        m = _VERSION_RE.match(str(text).strip())
        if not m:
            raise SemVerError(f"invalid version '{text}'")
        return cls(
            major=int(m.group(1)),
            minor=int(m.group(2) or 0),
            patch=int(m.group(3) or 0),
            prerelease=m.group(4) or "",
        )

    @classmethod
    def try_parse(cls, text: str) -> Optional["Version"]:
        try:
            return cls.parse(text)
        except SemVerError:
            return None

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base

    def _sort_key(self):
        # A release outranks any prerelease of the same numbers.
        return (self.major, self.minor, self.patch, 0 if self.prerelease else 1, self.prerelease)

    def __lt__(self, other: "Version") -> bool:  # type: ignore[override]
        if not isinstance(other, Version):
            return NotImplemented
        return self._sort_key() < other._sort_key()

    def __le__(self, other: "Version") -> bool:  # type: ignore[override]
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:  # type: ignore[override]
        if not isinstance(other, Version):
            return NotImplemented
        return other < self

    def __ge__(self, other: "Version") -> bool:  # type: ignore[override]
        return self == other or other < self


@dataclass(frozen=True)
class Constraint:
    """One comparison, e.g. ``>=1.2.0``."""

    op: str
    version: Optional[Version] = None

    def matches(self, v: Version) -> bool:
        if self.op == "*":
            return True
        assert self.version is not None
        if self.op == "=":
            return v == self.version
        if self.op == ">":
            return self.version < v
        if self.op == ">=":
            return self.version <= v
        if self.op == "<":
            return v < self.version
        if self.op == "<=":
            return v <= self.version
        if self.op == "^":
            return self._caret(v, self.version)
        if self.op == "~":
            return self._tilde(v, self.version)
        raise SemVerError(f"unknown operator '{self.op}'")

    @staticmethod
    def _caret(v: Version, base: Version) -> bool:
        """Cargo-style caret: ``^1.2.3`` → ``>=1.2.3, <2.0.0`` (and narrower for 0.x)."""
        if v < base:
            return False
        if base.major > 0:
            return v.major == base.major
        if base.minor > 0:
            return v.major == 0 and v.minor == base.minor
        return v.major == 0 and v.minor == 0 and v.patch == base.patch

    @staticmethod
    def _tilde(v: Version, base: Version) -> bool:
        """Tilde: ``~1.2.3`` → ``>=1.2.3, <1.3.0``; ``~1`` → ``>=1.0.0, <2.0.0``."""
        if v < base:
            return False
        return v.major == base.major and v.minor == base.minor


def parse_constraint(text: str) -> List[Constraint]:
    """Parses a constraint string; commas mean AND (``>=1.0, <2.0``)."""
    raw = (text or "").strip()
    if raw in ("", "*", "x", "X", "any", "latest"):
        return [Constraint("*")]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return [Constraint("*")]
    out: List[Constraint] = []
    for part in parts:
        if part in ("*", "x", "X"):
            out.append(Constraint("*"))
            continue
        m = _CONSTRAINT_RE.match(part)
        if not m:
            raise SemVerError(f"invalid version constraint '{part}'")
        op = m.group(1) or "="
        if op == "==":
            op = "="
        ver_txt = m.group(2)
        if ver_txt in ("*", "x", "X"):
            out.append(Constraint("*"))
            continue
        out.append(Constraint(op, Version.parse(ver_txt)))
    return out


def satisfies(version: Version, constraints: Sequence[Constraint]) -> bool:
    return all(c.matches(version) for c in constraints)


def select_version(tags: Iterable[str], constraint: str) -> Optional[Tuple[str, Version]]:
    """Highest tag satisfying ``constraint``; returns ``(tag, version)`` or None.

    Prereleases are skipped unless the constraint itself mentions one (npm/Cargo
    behaviour), so ``^1.0.0`` never silently picks ``1.1.0-rc1``.
    """
    constraints = parse_constraint(constraint)
    prerelease_ok = any(c.version is not None and c.version.prerelease for c in constraints)
    best: Optional[Tuple[str, Version]] = None
    for tag in tags:
        v = Version.try_parse(tag)
        if v is None:
            continue
        if v.prerelease and not prerelease_ok:
            continue
        if not satisfies(v, constraints):
            continue
        if best is None or best[1] < v:
            best = (tag, v)
    return best


@dataclass
class Requirement:
    """A dependency requirement collected while walking the graph."""

    name: str
    constraint: str
    source: str
    branch: Optional[str] = None
    required_by: str = "<root>"


@dataclass
class ResolutionConflict:
    name: str
    requirements: List[Requirement] = field(default_factory=list)


class DependencyConflictError(RuntimeError):
    """Two requirements on the same dependency cannot be satisfied at once.

    Carries the project-layer diagnostic code ``E0062``.  ``pengu_project.py``
    documented that code for this error while the message did not actually
    contain it, so no tool (or user) could match the diagnostic; the code is now
    emitted with the message and catalogued in ``LANGUAGE.md`` §22.3.1.
    """

    def __init__(self, conflict: ResolutionConflict):
        reqs = "\n".join(
            f"    - {r.source} ({r.constraint or '*'}) required by {r.required_by}"
            for r in conflict.requirements
        )
        super().__init__(
            f"[E0062] conflicting version requirements for dependency '{conflict.name}':\n{reqs}\n"
            f"  Fix it by pinning one version in your manifest, or by using "
            f"compatible constraints."
        )
        self.conflict = conflict
