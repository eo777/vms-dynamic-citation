"""Checks of page_geometry.py (27 October 2026).

1. Selector port: for every token of the manuscript (recorded rectangles, the app's own data) the Python pool equals the
   app's JavaScript pool, indices and weights (page_geometry_dump.js, node).
2. Layout: feeding a saved stream (runs/m_timm) word by word through Layout gives the template-availability study's
   synthetic geometry (component_check.synthetic_geometry) box for box.
3. For a --spatial run (argument: run folder): the pools the generator drew from against the pools the scorer computes on
   the finished stream (sizes per token; the scorer takes the page's word width and pitch from the stream's own boxes).

python page_geometry_check.py [runs/p_timm_spatial ...]
"""
import gzip
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import page_geometry as PG

STUDY_DIR = next((p for p in (PG.ROOT / 'research/mattr_template_link_20261026', PG.ROOT.parent / 'experiments/mattr_template_link') if p.exists()), None)


def dump_js(inp, options=None):
    with tempfile.TemporaryDirectory() as td:
        pin, pout = Path(td) / 'in.json', Path(td) / 'out.json'
        pin.write_text(json.dumps(inp), encoding='utf-8')
        r = subprocess.run(['node', str(HERE / 'page_geometry_dump.js'), str(pin), str(pout), str(PG.resolve(PG.APP_SELECTOR_REL)), json.dumps(options or {})],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return json.loads(pout.read_text(encoding='utf-8'))


def check_selector(geo):
    """The JS selector takes word width and pitch from the geometry it is given; here that is the recorded geometry."""
    app, ms = geo.app, geo.ms
    inp = dict(words=app['words'], lines=app['lines'], geometry=app['geometry'], components={w: app['components'][w] for w in set(app['words'])})
    js = dump_js(inp)
    centres = [None if b is None else ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0], b[3] - b[1]) for b in app['geometry']]
    line_of = np.zeros(len(app['words']), int)
    for k, L in enumerate(app['lines']):
        line_of[L['start']:L['end']] = k
    n_tok = n_same = 0
    max_w = 0.0
    bad = []
    for p in ms['pages']:
        idx = [i for l in range(p['start_line'], p['end_line']) for i in range(app['lines'][l]['start'], app['lines'][l]['end'])]
        boxes = [centres[i] for i in idx if centres[i]]
        W = float(np.median([b[2] for b in boxes])) or 1.0
        ys = []
        for l in range(p['start_line'], p['end_line']):
            a = [centres[i][1] for i in range(app['lines'][l]['start'], app['lines'][l]['end']) if centres[i]]
            ys.append(float(np.median(a)) if a else float('nan'))
        gaps = [b - a for a, b in zip(ys, ys[1:]) if np.isfinite(a) and np.isfinite(b) and b - a > 0]
        pitch = float(np.median(gaps)) if gaps else (float(np.median([b[3] for b in boxes])) * 1.6 if boxes else 1.0)
        have = [i for i in idx if app['geometry'][i]]
        g = np.array([app['geometry'][i] for i in have], float)
        lines_ = np.array([line_of[i] for i in have])
        pos_in = {i: k for k, i in enumerate(have)}
        for i in idx:
            if not app['geometry'][i]:
                continue
            k = pos_in[i]
            cand = dict(x0=g[:k, 0], y0=g[:k, 1], x1=g[:k, 2], y1=g[:k, 3], line=lines_[:k])
            ind, w, avail = PG.source_pool((app['geometry'][i], line_of[i]), cand, W, pitch)
            mine = sorted(zip([have[j] for j in ind], w))
            theirs = sorted(zip(js[i][0], js[i][1]))
            n_tok += 1
            if [a for a, _ in mine] == [a for a, _ in theirs] and avail == js[i][2]:
                n_same += 1
                if mine:
                    max_w = max(max_w, max(abs(a - b) for (_, a), (_, b) in zip(mine, theirs)))
            elif len(bad) < 5:
                bad.append((i, [a for a, _ in mine][:8], [a for a, _ in theirs][:8], avail, js[i][2]))
    print(f'selector port: {n_same} of {n_tok} manuscript tokens with the same source set and count in view; max weight difference {max_w:.1e}')
    for b in bad:
        print('   differs:', b)
    return n_same == n_tok


def read_lines(p, n=None):
    L = [l.split() for l in Path(p).read_text(encoding='utf-8-sig').splitlines() if l.strip() and not l.startswith('#')]
    return L if n is None else L[:n]


def check_layout(geo, stream):
    sys.path.insert(0, str(STUDY_DIR))
    import data as D
    import component_check as CC
    ms = D.manuscript()
    frames = CC.line_frames(geo.app, ms)
    lines = [list(l) for l in read_lines(stream, len(ms['lines']))]
    words_in = [w for l in lines for w in l]
    theirs = CC.synthetic_geometry(lines, frames, ms)
    words_out = [w for l in lines for w in l]
    lay = PG.Layout(geo)
    pos = 0
    for li, l in enumerate(read_lines(stream, len(ms['lines']))):
        for w in l:
            lay.add(pos, w, li)
            pos += 1
    lay.finish()
    mine = lay.geometry_in_order(pos)
    if words_in != words_out:
        print(f'layout: the study reorders {sum(a != b for a, b in zip(words_in, words_out))} tokens (page-end overflow after frameless slots); compared by position')
    same = sum(1 for a, b in zip(mine, theirs) if (a is None and b is None) or (a is not None and b is not None and max(abs(x - y) for x, y in zip(a, b)) < 1e-6))
    print(f'layout: {same} of {len(theirs)} boxes identical to the study\'s synthetic geometry ({Path(stream).parent.name}); boxed {sum(b is not None for b in mine)} / {sum(b is not None for b in theirs)}')
    return same == len(theirs)


def check_run(geo, run):
    sys.path.insert(0, str(STUDY_DIR))
    import data as D
    import component_check as CC
    run = Path(run)
    pools = json.load(gzip.open(run / 'spatial.json.gz', 'rt', encoding='utf-8'))
    ms = D.manuscript()
    frames = CC.line_frames(geo.app, ms)
    lines = [list(l) for l in read_lines(run / 'generated_text.txt', len(ms['lines']))]
    geom = CC.synthetic_geometry(lines, frames, ms)
    inp = CC.make_input(ms, lines, geom, CC.zattera)
    meas = CC.measure(inp)
    n_scorer = np.array([v if v is not None else -1 for v in meas['n']])
    n = min(len(n_scorer), len(pools))
    gen = np.array([p[0] if p else -1 for p in pools[:n]])
    avail = np.array([p[1] if p else -1 for p in pools[:n]])
    m = gen >= 0
    d = gen[m] - n_scorer[m]
    print(f'{run.name}: {m.sum()} of {n} tokens drew their source from the words in view; generator pool against scorer pool (same stream, finished): '
          f'identical size {np.mean(d == 0):.3f}, |difference| <= 2 {np.mean(np.abs(d) <= 2):.3f}, median difference {np.median(d):+.1f}, mean {d.mean():+.2f}; '
          f'mean pool {gen[m].mean():.1f} (in view {avail[m].mean():.1f}) against {n_scorer[m].mean():.1f}')
    return dict(tokens=int(n), spatial=int(m.sum()), same=float(np.mean(d == 0)), within2=float(np.mean(np.abs(d) <= 2)), mean_diff=float(d.mean()),
                mean_gen=float(gen[m].mean()), mean_in_view=float(avail[m].mean()), mean_scorer=float(n_scorer[m].mean()))


def main():
    geo = PG.PageGeometry()
    ok1 = check_selector(geo)
    ok2 = check_layout(geo, HERE / 'runs/m_timm/generated_text.txt')
    out = dict(selector_port_exact=ok1, layout_exact=ok2, runs={})
    for r in sys.argv[1:]:
        out['runs'][Path(r).name] = check_run(geo, r)
    (HERE / 'page_geometry_check.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
