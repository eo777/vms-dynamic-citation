"""Replace every literal p/f with k, ke, or t in unchanged MATTR windows."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import data as D

WINDOW = 100


def normalize(word, replacement='ke'):
    return word.replace('p', replacement).replace('f', replacement)


def measure(words, replacement='ke'):
    mapped = [normalize(w, replacement) for w in words]
    assert len(mapped) == len(words)
    original, changed = Counter(words[:WINDOW]), Counter(mapped[:WINDOW])
    totals = Counter()
    collision_windows, collision_loss = Counter(), Counter()
    for end in range(WINDOW, len(words)+1):
        if end > WINDOW:
            i = end-1
            for counter, old, new in [(original, words[i-WINDOW], words[i]),
                                       (changed, mapped[i-WINDOW], mapped[i])]:
                counter[old] -= 1
                if counter[old] == 0:
                    del counter[old]
                counter[new] += 1
        assert len(changed) <= len(original)
        buckets = defaultdict(list)
        for word, count in original.items():
            buckets[normalize(word, replacement)].append(word)
            if 'p' in word or 'f' in word:
                totals['pf_token_window_exposures'] += count
                if count == 1:
                    totals['pf_unique_before'] += 1
                    if changed[normalize(word, replacement)] == 1:
                        totals['pf_unique_after'] += 1
        loss = len(original)-len(changed)
        totals['original_distinct'] += len(original)
        totals['normalized_distinct'] += len(changed)
        totals['windows'] += 1
        totals['windows_changed'] += loss > 0
        for target, sources in buckets.items():
            if len(sources) > 1:
                collision_windows[target] += 1
                collision_loss[target] += len(sources)-1
                if target in sources:
                    totals['lost_types_pf_to_nonpf'] += len(sources)-1
                else:
                    totals['lost_types_pf_to_pf'] += len(sources)-1
    denominator = WINDOW*totals['windows']
    old = totals['original_distinct']/denominator
    new = totals['normalized_distinct']/denominator
    assert abs(old-D.mattr(words)) < 1e-12
    assert abs(new-D.mattr(mapped)) < 1e-12
    assert totals['lost_types_pf_to_nonpf']+totals['lost_types_pf_to_pf'] == totals['original_distinct']-totals['normalized_distinct']
    regional = defaultdict(Counter)
    for word in words:
        regional[normalize(word, replacement)][word] += 1
    collisions = []
    for target, sources in regional.items():
        if len(sources) > 1:
            collisions.append(dict(normalized=target, source_counts=dict(sources),
                                   original_windows_with_collision=collision_windows[target],
                                   mattr_loss=collision_loss[target]/denominator))
    collisions.sort(key=lambda x:x['mattr_loss'], reverse=True)
    pf_counts = Counter(w for w in words if 'p' in w or 'f' in w)
    matching_existing = [w for w in pf_counts if normalize(w, replacement) in regional[normalize(w, replacement)]]
    return dict(tokens=len(words), pf_tokens=sum(pf_counts.values()), pf_types=len(pf_counts),
                original_mattr=old, normalized_mattr=new, loss=old-new,
                relative_mattr_retained=new/old,
                pf_unique_in_window_before=totals['pf_unique_before']/totals['pf_token_window_exposures'],
                pf_unique_in_window_after=totals['pf_unique_after']/totals['pf_token_window_exposures'],
                previously_unique_pf_retained=totals['pf_unique_after']/totals['pf_unique_before'],
                windows_changed_fraction=totals['windows_changed']/totals['windows'],
                loss_pf_to_nonpf=totals['lost_types_pf_to_nonpf']/denominator,
                loss_pf_to_pf=totals['lost_types_pf_to_pf']/denominator,
                pf_types_matching_existing_nonpf=len(matching_existing),
                pf_tokens_matching_existing_nonpf=sum(pf_counts[w] for w in matching_existing),
                counts=dict(totals), collisions=collisions)


def main():
    ms = D.manuscript()
    saved = json.loads((HERE.parent/'layout_controls.json').read_text())
    words_by_group = {group: [w for row in ms['lines'] if row['group'] == group for w in row['words']]
                      for group in ['3c', '4c', '4a']}
    previous_ke_path = HERE/'normalization.json'
    previous_ke = json.loads(previous_ke_path.read_text()) if previous_ke_path.exists() else None
    comparison = {}
    for replacement in ['k', 'ke', 't']:
        results = {}
        for group, words in words_by_group.items():
            results[group] = measure(words, replacement)
            r = results[group]
            assert abs(r['original_mattr']-saved['manuscript'][0]['route']['groups'][group]['mattr100']) < 1e-12
            if replacement == 'ke' and previous_ke:
                assert r == previous_ke['groups'][group]
            print(f'{replacement}, {group}: {r["original_mattr"]:.8f} -> {r["normalized_mattr"]:.8f}; '
                  f'loss {r["loss"]*100:.5f} pp; originally unique PF retained {r["previously_unique_pf_retained"]*100:.3f}%')
        gap_before = results['3c']['original_mattr']-results['4a']['original_mattr']
        gap_after = results['3c']['normalized_mattr']-results['4a']['normalized_mattr']
        payload = dict(mapping={'p': replacement, 'f': replacement}, window=WINDOW,
                   method='Literal replacement everywhere in every word. No token deletion, reordering, or window changes. Original and normalized distinct counts scored in every original 100-word window within each group.',
                   uniqueness='A P/F-bearing token is unique in a window if its spelling occurs once there; retained uniqueness conditions on it being unique before normalization. Counts are over all token-window exposures, not globally unique word types.',
                   inputs_sha256={name: hashlib.sha256(p.read_bytes()).hexdigest() for name, p in [('tokens', D.TOKENS), ('path_asset', D.ASSET)]},
                   groups=results,
                   stars_to_bio_gap=dict(before=gap_before, after=gap_after, fraction_retained=gap_after/gap_before),
                   checks=dict(token_counts_unchanged=True, windows_unchanged=True, original_mattr_reproduced=True,
                               normalized_mattr_verified=True, collision_losses_sum=True))
        output = 'normalization.json' if replacement == 'ke' else f'normalization_{replacement}.json'
        (HERE/output).write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
        comparison[replacement] = dict(
            groups={group: {key: r[key] for key in ['original_mattr', 'normalized_mattr', 'loss',
                     'previously_unique_pf_retained', 'pf_unique_in_window_before', 'pf_unique_in_window_after']}
                    for group, r in results.items()},
            stars_to_bio_gap=payload['stars_to_bio_gap'])
    (HERE/'normalization_comparison.json').write_text(json.dumps(comparison, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
