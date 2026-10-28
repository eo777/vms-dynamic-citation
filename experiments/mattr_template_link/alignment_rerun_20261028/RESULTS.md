# Positional recheck of the spatial-diversity / repetition finding

Input pinning: this report uses review `2026-10-28.1`. The CLI now defaults to
`inputs/words_review_v1.json.gz`, preserving these results after the app's v2 boundary/compound repairs.
`inputs/run_v1.py` retains the exact runner hashed by the original metrics; current `run.py` adds
explicit input selection. `verify.py` checks those original bytes and the geometry provenance.
The v2 follow-up is recorded in `research/spatial_alignment_review_20261028/RESULTS.md`.

28 October 2026. The corrected assignments preserve the finding. The assignment-only
effect is extremely small; applying the additional conservative exclusions changes
more windows and gives a larger point estimate for this association. These are separate tests.

## What was rerun

All 34,977 paragraph-text tokens, 4,130 lines and 50 bifolia in the original Path 1
order. The source window is unchanged: same-page earlier words, three median word
widths left, eight line pitches above, 45-degree half-angle, rectangle/cone
intersection, distance weights, cap 100. The original selector is preserved verbatim.

The primary statistic is the original T17 contrast: within each pool-size tertile,
form low/high source-word-diversity quintiles within bifolium, compare the target
word's replacement impact, then average the three contrasts. Positive means the
target is more repetitive when the preceding spatial pool is less diverse. Word
diversity is distance-weighted Gini-Simpson diversity. Impact is the fraction of
containing 100-token windows with another instance of the target spelling, numerically
the MATTR **percentage-point** gain from replacing this one token with a novel type.
These numbers are not percentage changes in whole-manuscript MATTR and are not a
test of predicting the following 100 words.

We also recomputed component diversity, conditional glyph entropy H2, unstratified
contrasts, MATTR correlations, regional results, and a common-target comparison.
`heldout.py` reruns the original grouped five-fold ridge/spline prediction of the
same token's impact, including additive and arrival burdens. `calibration.py`
rebuilds all 13 T17 comparison layouts in memory, including five saved copier texts,
three bigram controls and three German-prose layouts.

## Geometry comparisons

| Geometry | Located tokens | Eligible primary targets | Primary contrast |
|---|---:|---:|---:|
| Historical recorded rectangles | 34,912 | 22,210 | +0.076804 |
| Corrected assignments, same historical rules | 34,904 | 22,204 | +0.076870 |
| Historical, original oversized-box exclusion | 34,796 | 22,156 | +0.077164 |
| Corrected, same oversized-box exclusion | 34,790 | 22,152 | +0.078945 |
| Reviewed sensitivity policy | 34,703 | 22,122 | +0.079542 |
| Reviewed strict policy, historical selector | 31,127 | 19,831 | +0.089994 |
| Reviewed strict policy, current app selector | 31,127 | 19,835 | +0.091629 |

The final metrics JSON is authoritative for cohort counts and full-precision values.
Assignment repairs change 29 token rectangles in this study's paragraph-text subset
(0.083% of its tokens); the whole-manuscript alignment review has a broader scope.
All canonical spellings, token order and line membership are unchanged. Zero-area
XML placeholders remain unlocated, as in the original renderer.

The raw assignment-only contrast changes by +0.000066, about 0.086% of its original
value. With the previous oversized-box exclusion it changes by +0.001780 (2.3%).
The paired bifolium-bootstrap interval for the raw assignment-only change is
[-0.00281, +0.00285], consistent with no change.
The 95% bifolium-bootstrap interval is [0.0584, 0.0949] historically and
[0.0571, 0.0962] after assignment repairs; for the current strict app it is
[0.0699, 0.1175]. On the identical 19,812 targets valid in all seven arms, the
contrast is +0.08038 historically, +0.07643 after repairs and +0.09046 in the
current strict app. The effect persists when the target cohort is held fixed.
Strict review removes ambiguous single-word locations as well as structurally bad
assignments; it is deliberately more restrictive and must not be described as just
the 29 coordinate repairs. A separate `strict_live` arm also includes the current
app's line-center calibration (midpoint of median top/bottom, rather than median
word-center). This prevents that selector change from being misattributed to repairs.

## Order controls

The exact historical paragraph/page shuffles reproduce their original contrasts:
+0.010985 / -0.005685, against +0.076804 for the actual order. With assignment repairs
they become +0.008666 / -0.004175, against +0.076870. The current strict app yields
+0.006214 / -0.014308, against +0.091629.

In addition, 99 independently seeded paragraph shuffles and 99 page shuffles are
paired across all seven geometry arms. Every shuffle preserves its paragraph/page
word multiset and fixed physical slots. Geometry eligibility stays attached to the
slot; it is never recomputed from the shuffled spelling. The fast word-diversity
scorer is checked against the complete frozen/current scorer at every token before
processing shuffles. None of the 99 controls in either family reaches the observed
contrast in any arm (one-sided Monte Carlo p = 0.01, the resolution of this run).
The actual word order matters; the result is not just a statement about which forms
occur in a paragraph or what proportion of forms have a possible nearby copy.

## Held-out prediction and comparison texts

The original five-fold prediction results reproduce to numerical precision. The
global-baseline error reductions for nonlinear component diversity and H2 are:

| Geometry | Component-diversity error reduction | H2 error reduction |
|---|---:|---:|
| Historical | 0.7315% | 0.9539% |
| Assignment repairs only | 0.7249% | 0.9454% |
| Strict, historical selector | 0.7487% | 1.2495% |
| Strict, current app selector | 0.7557% | 1.2448% |

This remains a modest predictive association, despite being reproducible. The
order controls support a real local-arrangement effect; they do not establish that
copying alone generated the manuscript.

All 13 legacy calibration layouts reproduce all 12 main/length/label contrasts
(word diversity, components, H2) within 1e-10. Assignment-only geometry leaves the
copier-versus-bigram pattern intact. The current strict app gives primary contrasts
of +0.083 to +0.126 for the five saved copiers, versus -0.013 to +0.014 for the three
bigram controls. Prose remains layout-sensitive: roughly -0.007 with one word per
recorded box, +0.074 with character-budget reflow and +0.100 with its own lines.
Thus the statistic is not a unique signature of self-citation.

These runs rescore the saved generator words on rebuilt layouts. They do not
regenerate the spatial generators' writing trajectories under a changed adapter;
that would be a different model experiment. Geometry-free MATTR decompositions
have unchanged inputs and unchanged token outcomes. The old reconstruction routes
and model training are outside this recheck.

## Reproduction and data integrity

From this directory:

```text
python run.py --permutations 99
python calibration.py
python heldout.py
python verify.py
```

Python needs numpy; heldout.py additionally needs pandas and scikit-learn. Existing
study imports also require matplotlib and pillow. Node.js must be on PATH. All
inputs resolve in both the research workspace and the packaged reproduction kit.
No manuscript images or downloaded scans are required or written.

`geometry_inputs.py` makes geometry selection explicit. Historical scripts use
`legacyGeometry`; the rerun compares corrected, sensitivity and strict geometry.
The schema-3 app bundle contains token IDs, original XML parts, reviewed groups,
exclusions and historical rectangles. It is the positional source for this recheck;
the fitted `positional_path1.json.gz` asset supplies the unchanged Path 1 order and
model metadata, not manuscript word rectangles.

All 13 active variant caches were compared word-for-word and box-for-box with freshly rebuilt
legacy layouts before their provenance was stamped. Scientific cache consumers now
reject unversioned or mismatched caches. The rerun itself never consumes those caches.
Canonical token IDs, loci, shared-group membership, strict masks and box unions are
verified; original coordinate integrity is covered by the alignment review tests.
Two obsolete local variants (`bigram_by_group`, `far0_page_window`) are not consumed
by this experiment and remain uncertified; the new cache check would reject them.

A detached copy of the analysis kit reproduced all seven arms' source pools,
observed/matched statistics, bootstrap intervals and historical shuffle controls
exactly (the detached check did not repeat the additional 99-shuffle sweep).
All eight alignment-review tests and eight release-bundle tests passed. The
release manifest includes this rerun and its dependencies; no public push was made.
An optional local figure-export helper remains outside the release bundle, with
publication validation unchanged. The scientific reproduction scripts are included.

Compact outputs: `metrics.json` (all arms, regional/matched results, cluster-bootstrap
intervals, shuffle distributions and dependency hashes), `calibration.json`,
`heldout.json`, and `verification.json` (integrity checks, paired-change intervals,
dependency manifest). Historical results are retained separately. Additional disk
use is kept below 100 MB including temporary reproduction checks; no fitted models,
prediction arrays, manuscript images or copied study trees are retained.
