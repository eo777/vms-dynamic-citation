"""Glyph-unit sequences for transition analysis.

Two total, round-tripping unitizers built on the lossless atomizer in
:mod:`voynich_toolkit.eva`:

* ``raw`` - every plain EVA character is one unit (``ch`` is ``c`` + ``h``);
  extended ``@nnn;``, bench-extended ``{c@nnn;h}``, ligature ``{...}`` and
  literal atoms stay whole and are flagged rare.
* ``zattera`` - the Slot alphabet of Zattera (2022, section 2.2): benches and
  pedestalled gallows are one unit, maximal runs of ``e`` / ``i`` of length 1-3
  are one unit, everything outside the slot inventory is kept but flagged rare.

Neither unitizer rewrites the form: ``"".join(u.text for u in units(w, m)) == w``.
``?`` is always its own, never-rare unit so unreadable material stays visible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from .eva import Atom, parse_eva

MODES: Tuple[str, ...] = ("raw", "zattera")

# Canonical display orders (ordinary units only).  Unlisted non-"?" units
# follow alphabetically, then "?" last.
RAW_ORDER: Tuple[str, ...] = tuple("abcdefghijklmnopqrstuvxyz")
ZATTERA_ORDER: Tuple[str, ...] = (
    "q", "s", "d", "o", "y", "l", "r", "k", "t", "p", "f",
    "ch", "sh", "cth", "ckh", "cph", "cfh",
    "e", "ee", "eee", "a", "i", "ii", "iii", "m", "n",
)
_ZATTERA_SINGLE = frozenset("qsdoylrktpfamn")
_RUN_GLYPHS = ("e", "i")
_MAX_RUN = 3
_WHOLE_KINDS = frozenset(("extended", "bench_extended", "ligature", "literal"))


@dataclass(frozen=True)
class Unit:
    text: str
    rare: bool = False


def raw_units(word: str) -> Tuple[Unit, ...]:
    """Split ``word`` into single EVA characters; keep bracketed atoms whole."""
    out: List[Unit] = []
    for atom in parse_eva(word):
        if atom.kind in _WHOLE_KINDS:
            out.append(Unit(atom.raw, True))
        else:
            out.extend(Unit(ch) for ch in atom.raw)
    return tuple(out)


def zattera_units(word: str) -> Tuple[Unit, ...]:
    """Group ``word`` into Slot-alphabet units; flag anything outside it rare."""
    atoms = parse_eva(word)
    out: List[Unit] = []
    i = 0
    while i < len(atoms):
        atom = atoms[i]
        if atom.kind in _WHOLE_KINDS:
            out.append(Unit(atom.raw, True))
            i += 1
        elif atom.kind == "composite":
            out.append(Unit(atom.raw))
            i += 1
        elif atom.raw in _RUN_GLYPHS:
            j = i
            while j < len(atoms) and atoms[j].kind == "glyph" and atoms[j].raw == atom.raw:
                j += 1
            run = atom.raw * (j - i)
            out.append(Unit(run, rare=(j - i) > _MAX_RUN))
            i = j
        elif atom.raw == "?" or atom.raw in _ZATTERA_SINGLE:
            out.append(Unit(atom.raw))
            i += 1
        else:
            out.append(Unit(atom.raw, True))
            i += 1
    return tuple(out)


def units(word: str, mode: str) -> Tuple[Unit, ...]:
    if mode == "raw":
        return raw_units(word)
    if mode == "zattera":
        return zattera_units(word)
    raise ValueError("unknown unit mode %r; expected one of %r" % (mode, MODES))


def display_order(mode: str, observed: Iterable[str]) -> List[str]:
    """Canonical order first, then other units alphabetically, then ``?``."""
    if mode == "raw":
        canonical = RAW_ORDER
    elif mode == "zattera":
        canonical = ZATTERA_ORDER
    else:
        raise ValueError("unknown unit mode %r; expected one of %r" % (mode, MODES))
    seen = set(observed)
    ordered = [text for text in canonical if text in seen]
    rest = sorted(text for text in seen if text not in canonical and text != "?")
    ordered.extend(rest)
    if "?" in seen:
        ordered.append("?")
    return ordered
