# Template availability test: reproduction kit

**28 October alignment recheck:** see [the rerun results](alignment_rerun_20261028/RESULTS.md).
The original scripts below now explicitly select `legacyGeometry` through `geometry_inputs.py`, so they
reproduce the 27 October numbers even when the app's default geometry changes. Historical heatmap caches
carry an input geometry hash; consumers reject stale or unversioned caches. Rebuild them with
`heatmap_variants.py`. The alignment rerun rebuilds every source pool directly and needs no cached variants.

From this study folder, run:

```text
python alignment_rerun_20261028/run.py --permutations 99
python alignment_rerun_20261028/calibration.py
python alignment_rerun_20261028/heldout.py
python alignment_rerun_20261028/verify.py
```

The held-out check additionally needs `pandas` and `scikit-learn`. The rerun uses the reviewed schema-3
app bundle, including historical boxes, canonical token IDs, original XML parts, explicit uncertainty flags,
and strict/sensitivity masks. It separates assignment repairs, exclusions, and the current app's line-pitch
calibration. It writes compact JSON only and does not download manuscript images. Saved generator texts
are rescored after rebuilding their layouts; generator trajectories themselves are not regenerated.

For a concise illustrated explanation, open [Spatial diversity, repetition, and MATTR (HTML)](SUMMARY.html) in a browser. It has compact figures that expand when selected, and all images are embedded so the file can be sent on its own. A [Markdown version](SUMMARY.md) is also available.

Rebuild the HTML from the Markdown and saved app captures with `python build_summary_html.py` (requires `markdown-it-py`).

The exploratory Bio figures are retained for reference but are not included in the current summary. Rebuild the opening-profile charts with `python summary_figures/build_bio_exploration.py`. The two static figures show saved paragraph-depth and page-start results. Plotted values and input hashes are saved in `summary_figures/bio_exploration.json`; no model is regenerated.

The within-bifolium Bio/Stars figures are built with `python summary_figures/build_bio_bifolium.py`. Two static charts compare distinct-form counts in the first and last 100 words of each page: one average profile across four pages, and one view of every individual bifolium. Five complete bifolia per section contribute equally to the average. The incomplete Stars bifolium 103|116 remains in the individual view. `summary_figures/bio_within_bifolium.json` retains the counts and within-bifolium boundary comparisons. No ordering between bifolia is used.

Run `python summary_figures/build_bio_historical.py` to build the five historical comparisons, each with the manuscript reference and both reflows. This reproduces deterministic placement, checks all 610 saved group/bifolium MATTR values against `layout_controls.json`, and retains compact endpoint counts in `summary_figures/bio_historical_controls.json`. It does not run generators or spatial scoring. Four Latin character-budget versions of f81r have overlapping first/last 100-word samples; these are marked explicitly.

Are the manuscript's MATTR drops the collapses that copying from the page produces in the self-citation
generators? This folder holds everything needed to rerun that study and check its numbers: the scripts, the
inputs they read (or pointers to the copies elsewhere in this repository), and the outputs they wrote (logs, JSON,
figures) so a rerun can be compared line by line. The write-up with every table is `RESULTS.md`; its final
section lists the same run order as below.

Nothing here changes the app at the repository root; the study only reads the app's data and, for its
verification pages, copies the app's heatmap scripts.

## Requirements

- Python 3.9 or newer with `numpy`, `matplotlib` and `pillow`.
- Node.js on the PATH (`node`). The spatial pool scores are computed by `component_measure.js`, which calls
  `component_source_math.js`, a verbatim copy of the selector used by the component-impact study and by the
  app's heatmap.
- About 300 MB of free disk for the verification pages (`heatmap_variants/`, regenerable, not committed).
- On Windows, clone into a short folder (the repository's longest path is 167 characters) or set
  `git config --global core.longpaths true` first.

Run every command from the repository root. The scripts find their inputs through `data.src()`, which looks in
`data/` beside the scripts, then in `reproduce/` (the governor's own reproduction kit) and at the repository root
(the app's files). The frame and placement rules of every synthetic layout (recorded text segments, drawing gaps,
vertical gaps shared by neighbouring lines, letter size, carry-over) are one implementation shared with the generator's
spatial source mode: `reproduce/research/dynamic_selfcitation_20261024/governed/page_geometry.py`, imported by
`component_check.py`.

## Inputs

| Input | Role | Where it is |
|---|---|---|
| `data/solve/.../tokens.json` | the manuscript's 34,977 paragraph-text tokens in 4,130 lines, Path 1 order | this folder |
| `data/solve/.../physical_map.csv` | bifolium, leaf, face and section of every page (team Golf) | this folder |
| `reproduce/packages/voynich_gradients/.../positional_path1.json.gz` | the positional model and the Path 1 order of the 50 bifolia (the positional data) | governor kit |
| `data/mattr_heatmap/words.json.gz` | the recorded word rectangles of every page, the app's own data | repository root |
| `reproduce/research/.../governed/runs/*/generated_text.txt` | the saved generator streams: `m_timm` (Original Timm), `n_noinnov_far0*` (page window, no innovator), `p_timm_spatial*`, `p_noinnov_spatial*` and `p_far0_spatial*` (the same two copiers and the far-0 configuration with the innovator, each with its page draws taken from the words in view on the recorded page geometry, `governor.py --spatial`, added 27 October), and the innovator-on runs `m_far0*`, `n_final*`, `m_final*`, which the study keeps in its tables marked † and leaves out of its figures and reading | governor kit |
| `data/research/timm_geometry_audit_20261026/history_prediction/records/model{2..5}_source.json.gz` | four further native Timm seeds from the layout audit | this folder |
| `data/research/timm_geometry_audit_20261026/component_impact_20261027/derived.json.gz` | the component-impact study's per-token results, used to check that this study reproduces its selector exactly | this folder |
| `data/research/reference_corpus/...` (10 text files) | the natural-language comparison texts: five Latin herbals and medical texts, a German printed herbal of 1487 (Gart der Gesundheit, Augsburg), Hildegard's Physica, and three training-split controls | this folder |
| `reproduce/packages/voynich_gradients/src/voynich_gradients/{glyph_units,eva}.py` | the Zattera glyph-unit segmentation used for component diversity and H2 | governor kit |
| `captures/*.png` | three captures of the app used by `method_infographic.py` | this folder |

## Run order

```
python experiments/mattr_template_link/decompose.py
python experiments/mattr_template_link/scales.py
python experiments/mattr_template_link/visibility.py
python experiments/mattr_template_link/profile.py
python experiments/mattr_template_link/position.py
python experiments/mattr_template_link/extras.py
python experiments/mattr_template_link/timing.py
python experiments/mattr_template_link/shuffle_check.py
python experiments/mattr_template_link/layout_within.py
python experiments/mattr_template_link/continuity.py
python experiments/mattr_template_link/pagestart.py
python experiments/mattr_template_link/bio_visibility.py
python experiments/mattr_template_link/herbal_boundary.py
python experiments/mattr_template_link/component_check.py     # node; reproduces the component-impact selector to 1e-13, then calibrates it on every stream
python experiments/mattr_template_link/layout_controls.py     # node; MATTR by group for every text laid into the manuscript's lines, Markov chains, prose reflows
python experiments/mattr_template_link/component_strata.py    # node
python experiments/mattr_template_link/native_layout.py       # node
python experiments/mattr_template_link/figures_layout.py
python experiments/mattr_template_link/figures_pages.py       # node
python experiments/mattr_template_link/heatmap_variants.py    # node; writes heatmap_variants/ (the verification pages)
python experiments/mattr_template_link/mechanism_check.py     # node; the pool-size-stratified contrast, by length class, section and Golf group
python experiments/mattr_template_link/direction_check.py     # node; the mirror-cone direction test (the cone above N against the same cone below), every copier seed
python experiments/mattr_template_link/overlap_check.py       # node; the cone without same-line reach, repeats counted outside the cone
python experiments/mattr_template_link/shuffle_layout_check.py # typesetting of the re-typeset rearrangements; renders f75r and f33v
python experiments/mattr_template_link/sweep_check.py         # node; 36 pool shapes on the manuscript, its rearrangements and three copiers (about 20 minutes)
python experiments/mattr_template_link/length_class_check.py  # node; the study selector inside exact word-length classes
python experiments/mattr_template_link/width_neutral_check.py # node; the selector with a width-neutral same-line distance (gap between boxes)
python experiments/mattr_template_link/residual_check.py      # node; components, H2 and word diversity under length x pool-size strata, 19 length-matched shuffles (about 6 minutes)
python experiments/mattr_template_link/prose_residual_check.py # node; the five historical texts under the same controls, recorded boxes and re-typeset
python experiments/mattr_template_link/shape_residual_check.py # node; pool shapes (lines above only, below only, the study selector) under the joint control
python experiments/mattr_template_link/example_pools.py       # node; the summary page's two qokeedy examples, pools split into same-line and above-line parts
python experiments/mattr_template_link/interior_check.py      # node; interior words only (line edges and truncated windows removed), four pool shapes, 19 shuffles (about 10 minutes)
python experiments/mattr_template_link/prose_interior_check.py # node; the five prose texts on the same interior cohort
python experiments/mattr_template_link/prose_shuffle_check.py  # node; each prose text against nine size-matched paragraph shuffles of itself (about 10 minutes)
python experiments/mattr_template_link/prose_shuffle_more.py   # node; Rhazes and Galen against 30 shuffles
python experiments/mattr_template_link/shuffle30_check.py manuscript        # node; 30 shuffles, two interior definitions (also la_rhazes_almansor, la_galen_simplicium)
python experiments/mattr_template_link/mattr_vs_components.py # node; MATTR coupling
python experiments/mattr_template_link/figures_small.py
python experiments/mattr_template_link/prose_route.py           # each historical text's own MATTR route (route_mattr_prose.png)
python experiments/mattr_template_link/figures_f29r.py          # the f29r layout check (vertical gap), before and after
python experiments/mattr_template_link/method_infographic.py
python experiments/mattr_template_link/compare_site.py        # node; writes heatmap_variants/compare.html
python experiments/mattr_template_link/figures_pages2.py
python experiments/mattr_template_link/figures.py
```

Each script prints its tables to standard output; the committed `*.log` files are those outputs as they were
when `RESULTS.md` was written (redirect a rerun to a file and `diff` it), and the `*.json` files hold the same
numbers for the figures. The whole chain takes about 25 minutes on one core; the two slowest steps are
`component_check.py` and `layout_controls.py`.

`heatmap_variants.py` writes the laid-out texts (`heatmap_variants/<text>/data/mattr_heatmap/words.json.gz`) that
`mechanism_check.py`, `mattr_vs_components.py`, `compare_site.py` and `figures_pages2.py` read, so it must run before
them. To check the pool-diversity result alone (is the next word more often a repeat when the words in view are less
diverse?), run `component_check.py`, `heatmap_variants.py` and `mechanism_check.py` in that order, about seven minutes.
`direction_check.py` (about 2 minutes, independent of the others) asks whether that association has the direction copying
from the page would give it: the cone above N against the same cone mirrored below N. `overlap_check.py` (about 2 minutes,
independent) asks whether the lines above N carry the association at all: the cone without its same-line reach, and N counted
as a repeat only against twins outside the cone. `length_class_check.py` (about 2 minutes) scores the selector inside exact
word-length classes, where the manuscript's association disappears and the copiers' remains (RESULTS section 7, item 9);
`sweep_check.py` (about 20 minutes) maps 36 pool shapes on re-typeset rearrangements (`layout_shuffles.py`, checked by
`shuffle_layout_check.py`, which renders f75r and f33v). `residual_check.py` (about 6 minutes) is the check to read last: under
joint control for exact length and pool size a residual association remains for every measure, above 19 length-matched shuffles
(RESULTS section 7, item 9, review).

To look at the verification pages, serve the folder they were written to:

```
cd experiments/mattr_template_link/heatmap_variants
python -m http.server 8766
```

and open <http://127.0.0.1:8766/> (one app-format heatmap page per text version, with a per-token CSV for
page f78r) or <http://127.0.0.1:8766/compare.html> (any bifolium, every text version side by side).

## What to check first

| Number | Where | Value |
|---|---|---|
| agreement with the component-impact study (max abs difference, components and H2) | `component_check.log`, line 1 | 1.3e-13 and 7.5e-15 |
| manuscript within-bifolium quintile contrast, components, all bifolia | `component_check.log`, region all | +0.034 (+0.014 to +0.054) |
| the same for Original Timm and the no-innovator far 0 run | same table | +0.115 and +0.118 |
| the same for the three copiers whose sources come from the words in view (Timm, no-innovator far 0, far 0 with innovator) | same table | +0.111, +0.097, +0.091 |
| f29r: synthetic words inside the plant's stem column (lines 3 to 8), before / with the vertical-gap rule | `figures_f29r.py` output | 7 / 0 |
| historical texts rising into Stars / falling into Bio, of 10 series | `prose_route.log` | 6 / 3 (manuscript +0.049 / −0.128) |
| pool-size-stratified contrast, word diversity, manuscript / shuffled in paragraphs / shuffled in pages (these shuffles kept the recorded rectangles; superseded, RESULTS section 7 item 9) | `mechanism_check.log` | +0.077 / +0.011 / −0.006 |
| the study selector inside exact word-length classes: manuscript / whole-manuscript size-matched shuffle / Original Timm page draw | `length_class_check.log` | −0.012 (−0.029 to +0.008) / +0.006 / +0.075 |
| study selector with uniform weights / other lines only, manuscript (the three copiers) | `sweep_check.log`, table A | +0.011 / −0.023 (+0.080 to +0.112 / +0.068 to +0.082) |
| words of the old recorded-box shuffle in boxes off by more than 1.5 times / after re-typesetting | `shuffle_layout_check.log` | 41.6% / 0.1% |
| width-neutral selector (gap distance), raw / inside length classes: manuscript; Original Timm page draw | `width_neutral_check.log` | +0.012 / −0.013; +0.094 / +0.080 |
| inside exact length x pool-size tertile, manuscript: components / H2 / word diversity; 19 length-matched shuffles exceeded (synthetic boxes) | `residual_check.log` | +0.026 / +0.035 / +0.013; 19, 19, 18 of 19 |
| the same for the three copiers (seed 1), components / H2 | same log | +0.053 to +0.056 / +0.019 to +0.060 |
| the same for five prose texts re-typeset into the frames, components / H2 | `prose_residual_check.log` | −0.017 to −0.057 / −0.004 to −0.038 |
| lines above only under the joint control, manuscript components / H2 (copiers) | `shape_residual_check.log` | −0.002 / +0.012 (+0.049 to +0.059 / +0.029 to +0.046) |
| the same on interior words only (line edges and windows under 15 words removed), manuscript recorded / synthetic; copiers | `interior_check.log` | +0.025 / +0.040; +0.045 to +0.048 (H2 +0.022 / +0.037; +0.020 to +0.035) |
| the same for five prose texts on the interior cohort, lines above only, re-typeset: components / H2 | `prose_interior_check.log` | −0.007 to +0.033 / −0.011 to +0.032 |
| prose texts above their own nine shuffles on that cut (lines above only, joint control) | `prose_shuffle_check.log` | 1 of 5 clearly (Rhazes +0.033 against at most +0.015); manuscript +0.040 against at most +0.036 |
| 30 shuffles, lines above only, joint control, interior A: manuscript synthetic / recorded (shuffles above, p); Rhazes | `shuffle30_manuscript.log`, `shuffle30_la_rhazes_almansor.log` | +0.040 (30/30, 0.03) / +0.025 (22/30, 0.29); +0.014 (22/30, 0.29) |
| mirror-cone test, components, manuscript: cone above / cone below / paired difference | `direction_check.log`, region all | +0.036 / +0.032 / +0.004 (−0.019 to +0.026) |
| the same for Original Timm (page draw) and for the no-innovator copier of the words in view | same table | +0.121 / +0.052 / +0.068; +0.099 / +0.088 / +0.010 |
| the same with the manuscript's lines shuffled inside paragraphs / words shuffled inside lines / words shuffled inside paragraphs (cone above) | same table | +0.046 / +0.029 / +0.009 |
| overlap test, cone of other lines only, repeats outside the cone, manuscript above / below; at fixed pool size; paragraph shuffle at fixed pool size | `overlap_check.log`, region all | −0.015 / −0.021; +0.014 / +0.022; +0.020 / +0.019 |
| the same for Original Timm (page draw) and the no-innovator copier of the words in view, above, unstratified | same table | +0.090; +0.066 |
| MATTR100 fall 3c → 4a, manuscript = bag + clustering | `layout_controls.log` | −0.128 = −0.118 − 0.011 |
| the same for Original Timm and the no-innovator far 0 run | `layout_controls.log` | −0.069 = −0.015 − 0.054; −0.099 = −0.050 − 0.049 |
| coupling of the MATTR colour with component diversity, manuscript, token level / page means | `mattr_vs_components.log` | +0.26 / +0.48 |

The random elements (bootstrap draws, shuffles, Markov samples, Gart layout starts) are seeded in the scripts,
so a rerun on the same inputs reproduces the logs; a fresh clone on the authors' machine reproduced
`component_check.log` with three values moved by 0.001 (floating-point summation order at 1e-13 breaks a few
quintile ties), and a different numpy version can move bootstrap intervals in the last digit.

## Notes

- `RESULTS.md` records the study's revisions as they happened, including the corrections made on
  27 October 2026: the innovator-on streams set aside, the overflow-placement defect in the synthetic layouts,
  and the restatement of the opening inference. The tables carry the final numbers.
- The Markov chains and the prose reflows are generated inside `layout_controls.py` from the inputs above; no
  external generator is needed.
- `figures_explained.py` and the composite figures it drew are superseded by `figures_small.py` and are not
  part of this kit.
