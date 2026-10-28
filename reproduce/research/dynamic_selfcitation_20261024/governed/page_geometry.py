"""Page geometry for the governed generator (27 October 2026): the manuscript's recorded word rectangles, the governor
app's own data, laid under the generator's text lines, and the app's spatial source selector (cone above the word,
reach to its left, distance weights) ported to Python, so that `governor.py --spatial` can draw Timm's source from what
is physically in view on the page it is writing instead of from a uniform draw over the page's lines.

Layout rule (the same as the template-availability study's `component_check.fill_slots`, mode 'fixed', so that the
geometry the generator sees is the geometry the study's scorer puts under the finished stream): each generated text
line goes into the manuscript line at the same Path 1 index; its words are placed left to right at the line's letter
size (the recorded text width over the manuscript line's characters) inside the line's recorded text segments (split at
drawing gaps), following the recorded line's drift and height; words that do not fit carry over to the next slot, and
words left at the end of a page go below the page's lowest line. The target of a draw, whose spelling is not yet known,
is a provisional box one median recorded word wide at the next writing position.

Selector (port of `sourcePool` in the app's heatmap_sources.js): a word on an earlier line is in view when its
rectangle intersects the cone of `depth` line spacings above the target with half-angle `angle`; a word on the same line
when it lies within `left` median word widths to the left. Weight = alignment / (1 + distance)^2 (alignment = cos^2 of the
angle off the vertical, 1 on the same line), or 1 with weight 'uniform'; the `cap` heaviest are kept. The page's median
word width and line pitch are taken from the recorded rectangles of that page (the scorer takes them from the finished
stream's own boxes, which it cannot know while writing; `page_geometry_check.py` measures the difference).
"""
import gzip
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]   # the research workspace root, or <repository>/reproduce in the published kit

TOKENS_REL = 'solve/botanical_enrichment/echo7/preservation_model_20261014/data/tokens.json'
ASSET_REL = 'packages/voynich_gradients/src/voynich_gradients/assets/positional_path1.json.gz'
APP_WORDS_REL = 'apps/selfcitation_governor/data/mattr_heatmap/words.json.gz'
APP_SELECTOR_REL = 'apps/selfcitation_governor/heatmap_sources.js'
DEFAULTS = dict(left=3.0, depth=8.0, angle=45.0, weight='distance', cap=100)


def resolve(rel):
    """A workspace-relative input, found in the workspace itself or in the published kit: the template-availability
    experiment's data/ folder, the repository root for the app's own files, a data/ folder beside this module."""
    rel = rel.replace('\\', '/')
    app = 'apps/selfcitation_governor/'
    cands = [ROOT / rel, ROOT.parent / 'experiments/mattr_template_link/data' / rel, HERE / 'data' / rel]
    if rel.startswith(app):
        cands += [ROOT.parent / rel[len(app):], ROOT / rel[len(app):]]
    for c in cands:
        if c.exists():
            return c
    raise FileNotFoundError(rel)


def manuscript():
    """The study transcription's lines in Path 1 order (the order the governor's --match-pages writes page_spec.tsv in)
    and its pages as consecutive runs of one folio."""
    tok = json.loads(resolve(TOKENS_REL).read_text(encoding='utf-8'))['lines']
    asset = json.load(gzip.open(resolve(ASSET_REL), 'rt', encoding='utf-8'))
    by = defaultdict(list)
    for l in tok:
        by[l['folio']].append(l)
    lines, pages = [], []
    for node in asset['nodes']:
        for p in node['pages']:
            start = len(lines)
            for l in by[p]:
                lines.append(dict(folio=p, locus=l['locus'], words=l['words'], chars=len(' '.join(l['words'])), page=len(pages), node=node['id']))
            pages.append(dict(index=len(pages), folio=p, start_line=start, end_line=len(lines), node=node['id']))
    return dict(lines=lines, pages=pages)


def app_words():
    return json.load(gzip.open(resolve(APP_WORDS_REL), 'rt', encoding='utf-8'))


# ---- frames and placement: the study's rules (component_check.py, 27 October), unchanged ----

def oversized_flags(app, ms, width_factor=6.0, height_factor=2.5):
    """Per token: True when the recorded rectangle is wider than width_factor or taller than height_factor times the
    median box of its page (a defect of the source geometry)."""
    # Schema 3 geometry already applies the provenance-bearing alignment policy.
    # A tall original gallows box is not, by itself, an invalid rectangle.
    if app.get('spatialReview'):
        return [not t['strict'] for t in app['spatialReview']['tokens']]
    flags = [False] * len(app['geometry'])
    for p in ms['pages']:
        idx = [i for l in range(p['start_line'], p['end_line']) for i in range(app['lines'][l]['start'], app['lines'][l]['end']) if app['geometry'][i]]
        if not idx:
            continue
        w = np.median([app['geometry'][i][2] - app['geometry'][i][0] for i in idx])
        h = np.median([app['geometry'][i][3] - app['geometry'][i][1] for i in idx])
        for i in idx:
            g = app['geometry'][i]
            if g[2] - g[0] > width_factor * w or g[3] - g[1] > height_factor * h:
                flags[i] = True
    return flags


def vertical_gaps(app, ms, flags, min_share=0.5, overlap_share=0.3, near=2):
    """Drawing gaps that run down the page (a stem, a column of a diagram): per page, every inter-word gap wider than
    `min_share` of the page's median word width is a candidate; candidates on different lines whose x-intervals
    overlap by at least `overlap_share` of that width are clustered, and a cluster that joins two lines at most `near`
    lines apart is a vertical gap. Returns {line index: [(x_left, x_right), ...]} of the gaps to split at.
    (27 October 2026, user's observation on f29r: the plant stem splits lines 3, 5 and 6 by 64 to 98 units, under the
    isolated-gap rule of twice the median word width, so the synthetic layouts were written across it.)"""
    out = {}
    for p in ms['pages']:
        slots = list(range(p['start_line'], p['end_line']))
        idx = [i for l in slots for i in range(app['lines'][l]['start'], app['lines'][l]['end']) if app['geometry'][i] and not flags[i]]
        if not idx:
            continue
        W = float(np.median([app['geometry'][i][2] - app['geometry'][i][0] for i in idx]))
        cands = []    # (line, x_left, x_right)
        for k, l in enumerate(slots):
            boxes = sorted([app['geometry'][i] for i in range(app['lines'][l]['start'], app['lines'][l]['end']) if app['geometry'][i] and not flags[i]], key=lambda b: b[0])
            for a, b in zip(boxes, boxes[1:]):
                if b[0] - a[2] > min_share * W:
                    cands.append((k, float(a[2]), float(b[0])))
        if len(cands) < 2:
            continue
        parent = list(range(len(cands)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                if cands[i][0] == cands[j][0]:
                    continue
                if min(cands[i][2], cands[j][2]) - max(cands[i][1], cands[j][1]) >= overlap_share * W:
                    parent[find(i)] = find(j)
        groups = {}
        for i in range(len(cands)):
            groups.setdefault(find(i), []).append(i)
        for members in groups.values():
            ks = sorted({cands[i][0] for i in members})
            if len(ks) < 2 or min(b - a for a, b in zip(ks, ks[1:])) > near:
                continue
            for i in members:
                k, x0, x1 = cands[i]
                out.setdefault(slots[k], []).append((x0, x1))
    return out


def line_frames(app, ms):
    """Per manuscript line: horizontal extent and median vertical extent of the recorded rectangles, oversized ones
    excluded, with the line's text segments: split at gaps wider than twice the page's median word width (an
    isolated drawing) and at the vertical gaps shared by neighbouring lines (`vertical_gaps`)."""
    flags = oversized_flags(app, ms)
    gap_rule = {}
    for p in ms['pages']:
        idx = [i for l in range(p['start_line'], p['end_line']) for i in range(app['lines'][l]['start'], app['lines'][l]['end']) if app['geometry'][i] and not flags[i]]
        gap_rule[p['index']] = 2 * float(np.median([app['geometry'][i][2] - app['geometry'][i][0] for i in idx])) if idx else 120.0
    vgaps = vertical_gaps(app, ms, flags)
    frames = []
    for l, L in enumerate(app['lines']):
        boxes = sorted([app['geometry'][i] for i in range(L['start'], L['end']) if app['geometry'][i] and not flags[i]], key=lambda b: b[0])
        if not boxes:
            frames.append(None)
            continue
        rule = gap_rule[ms['lines'][l]['page']]
        cuts = vgaps.get(l, [])
        segments = [[boxes[0][0], boxes[0][2]]]
        for b in boxes[1:]:
            gap = (segments[-1][1], b[0])
            if b[0] - segments[-1][1] > rule or any(abs(gap[0] - x0) < 1e-6 and abs(gap[1] - x1) < 1e-6 for x0, x1 in cuts):
                segments.append([b[0], b[2]])
            else:
                segments[-1][1] = max(segments[-1][1], b[2])
        frames.append((min(b[0] for b in boxes), float(np.median([b[1] for b in boxes])), max(b[2] for b in boxes), float(np.median([b[3] for b in boxes])),
                       [(float(a), float(b)) for a, b in segments],
                       np.array([(b[0] + b[2]) / 2 for b in boxes], float), np.array([b[1] for b in boxes], float), np.array([b[3] for b in boxes], float)))
    return frames


def line_profile(fr):
    xs, tops, bottoms = fr[5], fr[6], fr[7]
    return lambda xc: (float(np.interp(xc, xs, tops)), float(np.interp(xc, xs, bottoms)))


def place_in_slot(ws, fr, cw, yshift=0.0, gap=1.0):
    """Place as many of ws as fit, left to right, inside the line's text segments at character width cw (a word that
    does not fit the current segment is tried in the next, past the drawing). Returns (number placed, boxes). A word
    longer than every segment is forced into the widest one only when nothing else has been placed in the slot."""
    segments = fr[4]
    yfun = line_profile(fr)
    out = []
    idx = 0
    for x0, x1 in segments:
        cap = (x1 - x0) / cw
        pos = 0.0
        while idx < len(ws) and pos + len(ws[idx]) <= cap + 1e-9:
            a = x0 + pos * cw
            b = a + len(ws[idx]) * cw
            top, bottom = yfun((a + b) / 2)
            out.append([a, top + yshift, b, bottom + yshift])
            pos += len(ws[idx]) + gap
            idx += 1
        if idx >= len(ws):
            break
    if idx == 0 and ws:
        x0, x1 = max(segments, key=lambda s: s[1] - s[0])
        a = x0
        b = a + len(ws[0]) * cw
        top, bottom = yfun((a + b) / 2)
        out.append([a, top + yshift, b, bottom + yshift])
        idx = 1
    return idx, out


# ---- the selector ----

def source_pool(target, cand, word_width, pitch, left=3.0, depth=8.0, angle=45.0, weight='distance', cap=100):
    """Port of sourcePool. target: box [x0,y0,x1,y1] and its line index as (box, line); cand: dict of numpy arrays
    x0,y0,x1,y1,line (earlier words with boxes, on the same page). Returns (indices into cand, weights, available)."""
    (tx0, ty0, tx1, ty1), tline = target
    tx, ty = (tx0 + tx1) / 2, (ty0 + ty1) / 2
    x0, y0, x1, y1, line = cand['x0'], cand['y0'], cand['x1'], cand['y1'], cand['line']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = cx - tx, ty - cy
    same = line == tline
    # same line: within `left` word widths to the left
    ok_same = same & (dx < 0) & (-dx <= left * word_width)
    dist_same = -dx / word_width
    # other lines: the rectangle intersects the finite cone
    near = np.maximum(0.0, ty - y1)
    far = np.minimum(depth * pitch, ty - y0)
    horizontal = np.maximum(np.maximum(x0 - tx, tx - x1), 0.0)
    tan = np.tan(np.radians(angle))
    ok_other = (~same) & (dy > 0) & (far > 0) & (near <= far) & (horizontal <= far * tan + 1e-8)
    with np.errstate(divide='ignore', invalid='ignore'):
        dist_other = np.hypot(dx, dy) / pitch
        align_other = dy * dy / (dx * dx + dy * dy)
    ok = ok_same | ok_other
    idx = np.flatnonzero(ok)
    if not len(idx):
        return idx, np.zeros(0), 0
    distance = np.where(same[idx], dist_same[idx], dist_other[idx])
    alignment = np.where(same[idx], 1.0, align_other[idx])
    w = np.ones(len(idx)) if weight == 'uniform' else alignment / (1.0 + distance) ** 2
    # heaviest first, ties by distance then by later position (as the app), then the cap
    order = np.lexsort((-idx, distance, -w))
    keep = order[:cap]
    return idx[keep], w[keep], int(len(idx))


class PageGeometry:
    """Frames of every manuscript line, the per-line letter size and the per-page word width and pitch."""

    def __init__(self, ms=None, app=None):
        self.ms = ms or manuscript()
        self.app = app or app_words()
        assert self.app['words'] == [w for L in self.ms['lines'] for w in L['words']], 'the app data and the transcription disagree'
        assert len(self.app['lines']) == len(self.ms['lines'])
        self.frames = line_frames(self.app, self.ms)
        flags = oversized_flags(self.app, self.ms)
        self.cw = [None if fr is None else sum(b - a for a, b in fr[4]) / max(L['chars'], 1) for fr, L in zip(self.frames, self.ms['lines'])]
        self.page_of = [L['page'] for L in self.ms['lines']]
        self.pitch, self.word_width, self.slots = {}, {}, {}
        for p in self.ms['pages']:
            slots = list(range(p['start_line'], p['end_line']))
            self.slots[p['index']] = slots
            centres = [(self.frames[l][1] + self.frames[l][3]) / 2 for l in slots if self.frames[l] is not None]
            gaps = [b - a for a, b in zip(centres, centres[1:]) if b - a > 0]
            self.pitch[p['index']] = float(np.median(gaps)) if gaps else 30.0
            widths = [self.app['geometry'][i][2] - self.app['geometry'][i][0] for l in slots for i in range(self.app['lines'][l]['start'], self.app['lines'][l]['end'])
                      if self.app['geometry'][i] and not flags[i]]
            self.word_width[p['index']] = float(np.median(widths)) if widths else 1.0

    @property
    def n_lines(self):
        return len(self.ms['lines'])


class Layout:
    """Incremental fill_slots: words arrive one at a time with their text line index; every word on a page that has a
    box so far is a candidate source for the next word. Boxes are final as soon as they are set (placement is left to
    right and a word's box does not depend on the words after it), except that a page's overflow is placed when the
    page is complete."""

    def __init__(self, geo):
        self.g = geo
        self.boxes = {}                    # position -> box or None
        self.words = {}                    # position -> word
        self.line_of = {}                  # position -> text line index
        self.page_tokens = defaultdict(list)   # page index -> positions with boxes, in writing order
        self.cur_line = None
        self.cur_page = None
        self.slot_words, self.slot_pos = [], []     # the words assigned to the current slot (carry first)
        self.carry_words, self.carry_pos = [], []
        self.last_framed = None
        self.widest = None
        self.lowest = None
        self.k_over = 0

    def _assign(self, pos, box):
        self.boxes[pos] = box
        if box is not None and self.cur_page is not None:
            self.page_tokens[self.cur_page].append(pos)

    def _place_slot(self):
        fr = self.g.frames[self.cur_line] if self.cur_line < self.g.n_lines else None
        if fr is None:
            for p in self.slot_pos:
                self.boxes[p] = None
            return len(self.slot_pos)
        placed, boxes = place_in_slot(self.slot_words, fr, self.g.cw[self.cur_line])
        for j, p in enumerate(self.slot_pos):
            if j < placed:
                if self.boxes.get(p, None) is None:
                    self._assign(p, boxes[j])
            else:
                self.boxes[p] = None
        return placed

    def _close_slot(self):
        if self.cur_line is None:
            return
        fr = self.g.frames[self.cur_line] if self.cur_line < self.g.n_lines else None
        if fr is None or not self.slot_words:
            self.carry_words, self.carry_pos = [], []     # a frameless slot absorbs its words and the carry, without boxes
            return
        placed = self._place_slot()
        self.carry_words, self.carry_pos = self.slot_words[placed:], self.slot_pos[placed:]
        self.last_framed = self.cur_line
        width = sum(b - a for a, b in fr[4])
        if self.widest is None or width > self.widest[1]:
            self.widest = (self.cur_line, width, self.g.cw[self.cur_line])
        if self.lowest is None or fr[3] > self.g.frames[self.lowest][3]:
            self.lowest = self.cur_line

    def _close_page(self):
        """Overflow below the page's lowest recorded line, in the widest line's segments at its letter size."""
        if self.cur_page is None:
            return
        pitch = self.g.pitch[self.cur_page]
        k = 0
        while self.carry_words and self.last_framed is not None:
            k += 1
            wl, _, wcw = self.widest
            shift = self.g.frames[self.lowest][3] - self.g.frames[wl][3] + k * pitch
            placed, boxes = place_in_slot(self.carry_words, self.g.frames[wl], wcw, yshift=shift)
            for j in range(placed):
                self._assign(self.carry_pos[j], boxes[j])
            self.carry_words, self.carry_pos = self.carry_words[placed:], self.carry_pos[placed:]
        for p in self.carry_pos:
            self.boxes[p] = None
        self.carry_words, self.carry_pos = [], []
        self.last_framed = self.widest = self.lowest = None

    def start_line(self, line):
        self._close_slot()
        page = self.g.page_of[line] if line < self.g.n_lines else None
        if page != self.cur_page:
            self._close_page()
            self.cur_page = page
        self.cur_line = line
        self.slot_words, self.slot_pos = list(self.carry_words), list(self.carry_pos)
        self.carry_words, self.carry_pos = [], []
        if self.slot_words:
            self._place_slot()

    def add(self, pos, word, line):
        if line != self.cur_line:
            self.start_line(line)
        self.words[pos] = word
        self.line_of[pos] = line
        self.slot_words.append(word)
        self.slot_pos.append(pos)
        self._place_slot()

    def finish(self):
        self._close_slot()
        self._close_page()
        self.cur_line = None

    def line_chars_used(self, line):
        """Characters of the current text line written so far (its own words, not the carry), with their spaces."""
        return sum(len(w) + 1 for p, w in zip(self.slot_pos, self.slot_words) if self.line_of[p] == line)

    def target_box(self, line, proxy_len):
        """The provisional box of the next word of `line` and the slot it lands in: a proxy word of proxy_len characters
        at the next writing position of the slot, by the placement rule. A word that does not fit its slot carries over
        to the next slot of the page (as the study's layout carries it), so the proxy is then placed, behind the slot's
        other overflow, at the start of the next slot that takes it. None when the page has no further slot for it."""
        if line != self.cur_line:
            self.start_line(line)
        fr = self.g.frames[line] if line < self.g.n_lines else None
        if fr is None:
            self.last_reason = 'no_frame'
            return None
        words = self.slot_words + ['x' * proxy_len]
        placed, boxes = place_in_slot(words, fr, self.g.cw[line])
        if placed == len(words):
            return boxes[-1], line
        overflow = words[placed:]
        page = self.g.page_of[line]
        for nxt in range(line + 1, self.g.n_lines):
            if self.g.page_of[nxt] != page:
                break
            fr2 = self.g.frames[nxt]
            if fr2 is None:
                continue
            p2, b2 = place_in_slot(overflow, fr2, self.g.cw[nxt])
            if p2 == len(overflow):
                return b2[-1], nxt
            overflow = overflow[p2:]
        self.last_reason = 'page_full'
        return None

    def candidates(self, page):
        pos = self.page_tokens.get(page, [])
        if not pos:
            return None, pos
        b = np.array([self.boxes[p] for p in pos], float)
        return dict(x0=b[:, 0], y0=b[:, 1], x1=b[:, 2], y1=b[:, 3], line=np.array([self.line_of[p] for p in pos])), pos

    def pool(self, line, options=None):
        """Sources in view for the next word of text line `line`: (positions, weights, available, target box)."""
        o = dict(DEFAULTS, **(options or {}))
        self.last_reason = ''
        if line >= self.g.n_lines:
            self.last_reason = 'beyond_manuscript'
            return None
        page = self.g.page_of[line]
        W, pitch = self.g.word_width[page], self.g.pitch[page]
        cw = self.g.cw[line]
        if cw is None:
            self.last_reason = 'no_frame'
            return None
        budget = self.g.ms['lines'][line]['chars'] - self.line_chars_used(line)
        proxy = max(1, min(int(round(W / cw)), budget if budget > 0 else 1))
        t = self.target_box(line, proxy)
        if t is None:
            return None
        target, tline = t
        cand, pos = self.candidates(page)
        if cand is None:
            return [], np.zeros(0), 0, target
        idx, w, available = source_pool((target, tline), cand, W, pitch, o['left'], o['depth'], o['angle'], o['weight'], o['cap'])
        return [pos[i] for i in idx], w, available, target

    def geometry_in_order(self, n):
        """Boxes of positions 0..n-1 (for the check against the study's synthetic geometry)."""
        return [self.boxes.get(i) for i in range(n)]
