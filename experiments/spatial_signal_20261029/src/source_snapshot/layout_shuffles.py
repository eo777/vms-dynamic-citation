"""Rearrangements of the manuscript text that keep its layout (28 October, user's requirement).

A shuffle that drops a word into another word's recorded rectangle gives it the wrong width, and a line moved into a
shorter slot overflows into the next line. Every variant here is therefore re-typeset into the manuscript's own line
frames at each line's letter size (page_geometry.fill_slots through component_check.synthetic_geometry: words left to
right inside the line's recorded text segments, following the line's drift and height), and the permutations are
size-matched so that what lands in a slot fits it:
  words_in_units(unit)  words permuted inside each unit (paragraph or page) among words of the SAME character length,
                        so every line keeps its character count and its word lengths in place;
  words_in_lines        the words of each line permuted inside that line (same characters, new order);
  reversed_lines        each line's words in reverse order;
  rotated_lines         line k rotated by k words (what stood in one column runs diagonally);
  lines_in_units(unit)  whole lines permuted inside each unit among lines whose character counts differ by at most
                        `tol` (default 15 percent), so a moved line fits its slot's frame.
typeset() lays a variant out and reports the carry-over (words that did not fit their slot and went to the next),
so the caller can see how far the layout departs from the manuscript's.
"""
from collections import defaultdict

import numpy as np

import component_check as CC


def paragraph_of_line(ms):
    return np.cumsum([bool(L['first']) for L in ms['lines']])


def page_of_line(ms):
    return np.array([L['page'] for L in ms['lines']])


def words_in_units(ms, unit, rng):
    lines = [list(L['words']) for L in ms['lines']]
    groups = defaultdict(list)
    for l, ws in enumerate(lines):
        for k, w in enumerate(ws):
            groups[(unit[l], len(w))].append((l, k))
    out = [list(ws) for ws in lines]
    moved = 0
    for slots in groups.values():
        words = [lines[l][k] for l, k in slots]
        perm = rng.permutation(len(slots))
        for (l, k), j in zip(slots, perm):
            out[l][k] = words[j]
            moved += words[j] != lines[l][k]
    return out, moved


def words_in_lines(ms, rng):
    return [[L['words'][k] for k in rng.permutation(len(L['words']))] for L in ms['lines']]


def reversed_lines(ms):
    return [list(reversed(L['words'])) for L in ms['lines']]


def rotated_lines(ms):
    out = []
    for k, L in enumerate(ms['lines']):
        ws = list(L['words'])
        s = k % len(ws) if ws else 0
        out.append(ws[s:] + ws[:s])
    return out


def lines_in_units(ms, unit, rng, band=0.5):
    """Lines permuted inside each unit among lines of comparable length: slots are visited in random order and each takes
    a line drawn at random among the unit's unassigned lines whose character count lies within a factor (1 + band) of the
    slot's own (the nearest unassigned line when none does). With the letter size then fitted to the slot (typeset_fit)
    this bounds the change of letter size to about that factor. Any permutation other than the identity must put some
    line into a slot of a different length, so a line shuffle cannot keep both the letter size and the slot exactly."""
    chars = np.array([L['chars'] for L in ms['lines']], float)
    lines = [list(L['words']) for L in ms['lines']]
    out = [None] * len(lines)
    moved = 0
    for u in np.unique(unit):
        idx = np.where(unit == u)[0]
        free = list(idx.tolist())
        for slot in idx[rng.permutation(len(idx))]:
            lo, hi = chars[slot] / (1 + band), chars[slot] * (1 + band)
            fits = [l for l in free if lo - 1e-9 <= chars[l] <= hi + 1e-9]
            pick = fits[rng.integers(len(fits))] if fits else min(free, key=lambda l: abs(chars[l] - chars[slot]))
            free.remove(pick)
            out[slot] = lines[pick]
            moved += pick != slot
    return out, moved


def typeset(ms, frames, line_words):
    """Lay the variant into the manuscript's frames; returns (line_words as placed, geometry, carried):
    `carried` is the number of words that did not fit their slot and continued on the next (or below the page)."""
    before = [len(ws) for ws in line_words]
    lines = [list(ws) for ws in line_words]
    geometry = CC.synthetic_geometry(lines, frames, ms)
    carried = sum(max(0, a - len(ws)) for a, ws in zip(before, lines))
    return lines, geometry, carried


def typeset_fit(ms, frames, line_words):
    """Each slot's words at the letter size that fills the slot (its segment width over the new line's characters), so a
    moved line fits where it lands and keeps its slot: a long line gets smaller letters, a short one larger. Any permutation
    of lines other than the identity must put some line into a slot shorter than its own, so a line shuffle needs either
    this or carry-over. Returns (lines, geometry, no_box, cw_ratio): words that still did not fit (segment splits) get no
    box, and cw_ratio is each slot's letter size over the manuscript's on that line."""
    from page_geometry import place_in_slot
    geometry, ratios, no_box = [], [], 0
    for l, ws in enumerate(line_words):
        fr = frames[l]
        if fr is None or not ws:
            geometry += [None] * len(ws)
            continue
        width = sum(b - a for a, b in fr[4])
        cw0 = width / max(ms['lines'][l]['chars'], 1)
        cw = width / max(len(' '.join(ws)), 1)
        placed, boxes = place_in_slot(ws, fr, cw)
        tries = 0
        while placed < len(ws) and tries < 8:
            cw *= 0.94
            placed, boxes = place_in_slot(ws, fr, cw)
            tries += 1
        geometry += boxes + [None] * (len(ws) - placed)
        no_box += len(ws) - placed
        ratios.append(cw / cw0)
    return [list(ws) for ws in line_words], geometry, no_box, np.array(ratios)


def variants(ms, frames, seed=1028):
    """Every variant typeset, in a fixed order: name -> dict(lines, geometry, carried, moved, cw_ratio)."""
    rng = np.random.default_rng(seed)
    par, page = paragraph_of_line(ms), page_of_line(ms)
    out = {}

    def add(name, lines, moved=None, fit=False):
        if fit:
            placed, geom, carried, ratio = typeset_fit(ms, frames, lines)
        else:
            placed, geom, carried = typeset(ms, frames, lines)
            ratio = None
        out[name] = dict(lines=placed, geometry=geom, carried=carried, moved=moved, cw_ratio=ratio)

    add('manuscript (synthetic boxes)', [list(L['words']) for L in ms['lines']])
    lines, moved = words_in_units(ms, par, rng)
    add('words shuffled in paragraphs (size-matched)', lines, moved)
    lines, moved = words_in_units(ms, page, rng)
    add('words shuffled in pages (size-matched)', lines, moved)
    lines, moved = words_in_units(ms, np.array([L['node'] for L in ms['lines']]), rng)
    add('words shuffled in bifolia (size-matched)', lines, moved)
    lines, moved = words_in_units(ms, np.zeros(len(ms['lines']), int), rng)
    add('words shuffled in whole manuscript (size-matched)', lines, moved)
    # words of any length permuted inside the paragraph: line lengths change, so the letter size is fitted to each slot
    tok_par = np.repeat(par, [len(L['words']) for L in ms['lines']])
    words = np.array([w for L in ms['lines'] for w in L['words']], dtype=object)
    for u in np.unique(tok_par):
        m = np.where(tok_par == u)[0]
        words[m] = words[rng.permutation(m)]
    at, lines = 0, []
    for L in ms['lines']:
        lines.append(list(words[at:at + len(L['words'])]))
        at += len(L['words'])
    add('words shuffled in paragraphs (any length, fitted letter size)', lines, None, fit=True)
    add('words shuffled in lines', words_in_lines(ms, rng))
    add('lines reversed', reversed_lines(ms))
    add('lines rotated (diagonal)', rotated_lines(ms))
    lines, moved = lines_in_units(ms, par, rng)
    add('lines shuffled in paragraphs (fitted letter size)', lines, moved, fit=True)
    lines, moved = lines_in_units(ms, page, rng)
    add('lines shuffled in pages (fitted letter size)', lines, moved, fit=True)
    return out
