"""T2b. Does a repeated word sit under its earlier copy? (Timm's same-position source bonus as a signature.)

Timm's chooser takes the source at the same character position of a line above 29% of the time
(15% line-initially). A writer copying words from the lines above would also tend to find them
near the same horizontal position. For every interior token i (not line-first or line-last) and
every line l among the five lines above it on the same page: observed = mean |r_i - r_j| over
the interior tokens j of line l with the same spelling (if any); null = mean |r_i - r_j'| over all
interior tokens j' of line l. r is the centre of the word in the transcription line, 0..1. The
ratio observed/null below one means copies cluster under their source. Manuscript and streams.
"""
from collections import defaultdict
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import data as D

LINES_UP = 5


def same_position(tok, ms):
    words = tok['words']; line = tok['line']; page = tok['page']; pos = tok['pos']; ll = tok['linelen']
    r = (tok['chars_before'] + np.array([len(w) for w in words]) / 2) / np.maximum(tok['line_chars'], 1)
    # index tokens by line
    by_line = defaultdict(list)
    for i, l in enumerate(line):
        by_line[int(l)].append(i)
    interior = (pos > 0) & (pos < ll - 1)
    obs = defaultdict(list); null = defaultdict(list); near_obs = defaultdict(list); near_null = defaultdict(list)
    n_pairs = 0
    for i in np.where(interior)[0]:
        li = int(line[i]); g = ms['lines'][li]['group']
        for up in range(1, LINES_UP + 1):
            l = li - up
            if l < 0 or ms['lines'][l]['page'] != page[i]:
                break
            cand = [j for j in by_line[l] if interior[j]]
            if len(cand) < 3:
                continue
            same = [j for j in cand if words[j] == words[i]]
            if not same:
                continue
            o = np.mean([abs(r[i] - r[j]) for j in same]); z = np.mean([abs(r[i] - r[j]) for j in cand])
            obs[(g, up)].append(o); null[(g, up)].append(z)
            near_obs[(g, up)].append(np.mean([abs(r[i] - r[j]) < 0.1 for j in same])); near_null[(g, up)].append(np.mean([abs(r[i] - r[j]) < 0.1 for j in cand]))
            n_pairs += 1
    out = dict(pairs=n_pairs)
    def agg(keys):
        o = sum((obs[k] for k in keys), []); z = sum((null[k] for k in keys), [])
        no = sum((near_obs[k] for k in keys), []); nz = sum((near_null[k] for k in keys), [])
        if not o:
            return None
        return dict(n=len(o), obs=float(np.mean(o)), null=float(np.mean(z)), ratio=float(np.mean(o) / np.mean(z)),
                    near_obs=float(np.mean(no)), near_null=float(np.mean(nz)), near_ratio=float(np.mean(no) / np.mean(nz)) if np.mean(nz) else None)
    out['all'] = agg(list(obs))
    out['by_lines_up'] = {up: agg([k for k in obs if k[1] == up]) for up in range(1, LINES_UP + 1)}
    out['by_group'] = {g: agg([k for k in obs if k[0] == g]) for g in sorted({k[0] for k in obs})}
    return out


def main():
    ms = D.manuscript()
    results = {}
    texts = {'manuscript': [None]}
    for key, (label, srcs) in D.STREAMS.items():
        texts[key] = srcs
    for key, srcs in texts.items():
        per = []
        for s in srcs:
            tok = D.tokenize(ms, None if s is None else D.read_stream(s))
            per.append(same_position(tok, ms))
        def avg(objs):
            if objs[0] is None:
                return None
            if isinstance(objs[0], dict):
                return {k: avg([o[k] for o in objs]) for k in objs[0]}
            return float(np.mean([o for o in objs if o is not None]))
        res = avg(per); res['label'] = key if key == 'manuscript' else D.STREAMS[key][0]
        results[key] = res
        a = res['all']
        print(f"{key:13s} pairs/seed {res['pairs']:.0f}: mean offset observed {a['obs']:.3f} vs null {a['null']:.3f} ratio {a['ratio']:.3f}; within 0.1: {a['near_obs']:.3f} vs {a['near_null']:.3f} ratio {a['near_ratio']:.2f} | "
              + ' '.join(f"up{u}:{res['by_lines_up'][u]['ratio']:.2f}" for u in range(1, LINES_UP + 1) if res['by_lines_up'][u]))
    (D.HERE / 'position.json').write_text(json.dumps(results, indent=1, default=float), encoding='utf-8')
    print('\nby group (ratio of mean offsets):')
    groups = list(dict.fromkeys(n['group'] for n in ms['nodes']))
    for key, res in results.items():
        print(f"{key:13s} " + ' '.join(f"{g}:{res['by_group'][g]['ratio']:.2f}" for g in groups if res['by_group'].get(g)))


if __name__ == '__main__':
    main()
