# Governed self-citation

An interactive report on a Voynich-text generator steered by a fitted model. Torsten Timm's self-citation generator
writes Voynich-like text by copying a word from the lines above and changing it slightly. Here three hooks let a
fitted positional model of the manuscript (expected shares of 1,324 spelling constructions at each of 50 bifolia in a
proposed order) steer two of its draws: which word is copied and whether a change is kept. A slot innovator supplies
new spellings where the text runs short of them. The app shows:

- every generated page of the original run, of the governed run and of the governed run without its far supply
  (the Runs menu switches comparison runs on and off; some carry statistics only), with the source window, the
  pressures and the decision behind each word, replayable step by step;
- per-bifolium results against the manuscript;
- minimum source edit distance and candidate-count overlays on the MATTR heatmap, with cleaned
  spatial windows and visible source spellings; counts can use distinct spellings or occurrences;
- a Reconstruction page for the 20 studied pages in five bifolia, with singulion-order playback,
  proposed parents, edit descriptions, source absence and strict-grammar filters. These are
  hindsight constructions with known targets, not successful predictions or historical attribution;
- a MATTR heatmap on recorded manuscript word rectangles, in bifolium order, with region selection and
  PNG/SVG downloads for Bio, 3c–Bio, 3b–3a and Pharma; adjustable window sizes and backward, forward or
  centered windows; MATTR, repeated-spelling or combined colors; click a word to highlight its exact
  calculation window directly on the pages (Escape restores the full map). Word repetition impact tests replacing
  one occurrence with a new spelling across all containing windows, while Step change separates the arriving
  word's gain from the departing word's loss. Spatial sources selects earlier same-page words to the left
  and above whose word boxes touch an adjustable cone, with distance/alignment or equal weights. Click to inspect the cone,
  weighted sources, source count and effective source count. Component diversity, glyph H1, conditional H2
  and component JS distance show the available glyph inventory and combinations. Spatial weights are an
  exploratory proxy rather than Timm's exact source probabilities; small pools can bias entropy estimates.
  Component color scales linearly span the full-path 5th–95th percentile range for the chosen settings,
  shared across every page and region; a spinner and percentage show calculation progress;
- a Comparison tab covering 31 methods and 66 completed streams: a ranked 19-statistic summary, all 50
  bifolium profiles, H1/H2, highlighted short passages, diversity failures, and explicit mechanism settings;
- innovation statistics: first appearances along the path and by slot, the shape of new forms, the governor's decisions;
- construction shares, word counts, rank–frequency, vocabulary growth, glyph and word bigrams;
- the held-out tests: held bifolia and held pages, scored where the targets never saw the text, and the pressure-scaling series;
- how the governor, innovator and bounded editor work, including why copy reserve and editing affect glyph
  entropy differently; baseline integration diffs and the experimental editor sources.

It compares generated Voynich-like text with the manuscript's text; it assigns no meanings.
Comparison links preserve the selected region, methods, weights, metric and text overlay. Experimental methods
are selectable on Charts and Innovation, with statistics and short excerpts only; no new page journals are included.
The default rank balances six statistic families. Two configurations with stalled attempts remain visible but unranked.
The region selector can exclude biological group 4a from rankings, profiles and A/B errors. Novelty retains
full-stream history, and regional entropy summaries average matched bifolium estimates rather than pooling text.

**Open the app:** https://eo777.github.io/vms-dynamic-citation/

## Running a copy

Everything is static, but the pages read their data with `fetch()`, so serve the folder (for example
`python -m http.server`) rather than opening the files from disk. Only a served copy checks for newer releases.

## Reproducing the runs

`reproduce/` holds what the generated texts were made with, copied unchanged from the research workspace in its own
folder layout, so that the scripts run as they are:

| Path under `reproduce/` | What it is |
|---|---|
| `research/dynamic_selfcitation_20261024/governed/` | `governor.py` (the governor and innovator), `build.py` (patches and compiles the generator), `Bridge.java` and `GovernedChooser.java` (the hooks), `novelty_target.json` (the manuscript's first-appearance rate per bifolium), and `runs/` with the featured runs: `generated_text.txt`, `run.json` (every argument, token count, SHA-256 of the text), `decisions.json.gz`, `slots.json.gz`, `conf.properties` |
| `research/dynamic_selfcitation_20261024/productive/runs/baseline_1/conf.properties` | Timm's configuration every run starts from (seed and line count are set per run) |
| `packages/voynich_gradients/` | The positional model: `positional_path1.json.gz` (constructions, bifolia, vocabulary, transitions), `path1_full.json.gz` and `path1_full.npz` (the fitted coefficients), and the four Python modules the governor imports |
| `solve/botanical_enrichment/echo7/copying_trace_20261014/generator/` | Timm's generator at the pinned commit (`upstream/`, MIT licence), `source_manifest.json` with the SHA-256 of each of its files, and `fetch_source.py`, which downloads that source and the compiler |

The three source files in `governed/human_design/` document the experimental editor and page-access policies.
They are reference sources; the full experimental scoring harness is not included in this reproduction kit.

Steps, with Python 3.9 or later and numpy, and a Java runtime on the PATH:

    cd reproduce
    python solve/botanical_enrichment/echo7/copying_trace_20261014/generator/fetch_source.py
    python research/dynamic_selfcitation_20261024/governed/build.py
    cd research/dynamic_selfcitation_20261024/governed
    python governor.py --seed 1 --beta-c 0 --beta-m 0 --log-all --out runs/check_timm
    python governor.py --seed 1 --beta-c 1 --beta-m 1 --source pressure --far 0.5 --retry 4 --horizon 256 --innovate --admit-lr --novelty-curve --slot-concat --kappa-l 2 --extend2 0.15 --adjacent --short-partner 0.35 --replace-short 0.7 --out runs/check_governed
    python governor.py --seed 1 --beta-c 0 --beta-m 0 --log-all --match-pages --spatial --out runs/check_timm_spatial

The third command is Timm's generator with its source draw taken from the words physically in view on the manuscript
page being written (`--spatial`, 27 October 2026): the app's own spatial selector, the cone above the word and the
reach to its left over the recorded word rectangles (`data/mattr_heatmap/words.json.gz` at the repository root), with
the generated words laid into the manuscript's lines as the template availability experiment lays every stream
(`page_geometry.py`; `page_geometry_check.py` verifies the selector port against the JavaScript and the layout against
the experiment's, with node on the PATH). `--match-pages` and `--spatial` read the manuscript's tokens from
`experiments/mattr_template_link/data/`. The runs `runs/p_timm_spatial*` and `runs/p_noinnov_spatial*` are the
published results of that mode; `run.json` → `stats` counts its draws and `spatial.json.gz` records, per token, the pool
the source was drawn from. The experiment's `RESULTS.md` (section 8, "The copier on the page's real geometry") measures
what the spatial draw changes.

`fetch_source.py` downloads the Eclipse compiler (`ecj.jar`, 3 MB, not stored here) and the pinned source again;
`build.py` checks every source file against `source_manifest.json` before patching and compiling. A run writes
`run.json` with `text_sha256`. The runs are deterministic, so the hashes below come out again (the Timm run takes
under a minute, a governed run about seven). `--trace` adds `trace.json.gz`, the journal this app's data was built
from, without changing the text. Seeds 2 and 3 are the same arguments with `--seed 2` and `--seed 3`.

| Run folder | Seed | Configuration | Tokens | SHA-256 of `generated_text.txt` |
|---|---|---|---|---|
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_far0` | 1 | governed + innovator, far 0, manuscript pages | 45,378 | `bde302fd97065c78d9cc1ded6110664f2f5b2a15128501898449084d71d9fdd2` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_far0_s2` | 2 | governed + innovator, far 0, manuscript pages | 45,282 | `df6180e1301fc834babb89b98c0eb2bbcf176cf39e1c10597c7d6c2f8729241d` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_far0_s3` | 3 | governed + innovator, far 0, manuscript pages | 45,508 | `ea79720a0898a4852ba5ee0e10ea1fa8a33d99622cbdcb9251874709f2ed6e39` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_final` | 1 | governed + innovator, manuscript pages | 42,074 | `ab6c6949c1fed99b5bb160bac273fca87c48f119c1f402ad0ff4ed257362f984` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_final_s2` | 2 | governed + innovator, manuscript pages | 42,031 | `7d858a5ad5a764623268bac03f4e207e81d185d90d36230c4e2434b32d55217c` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_final_s3` | 3 | governed + innovator, manuscript pages | 42,367 | `056f373e34ecbb13a1c3caef278069d4bc7557d9e58fb01004f73accae675a18` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/m_timm` | 1 | Timm (every temperature zero), manuscript pages | 45,952 | `f7f435dbbeefe67716e2464f7ede833e6420d74cefe2a4b8233ce70f3853d31b` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_final` | 1 | governed + innovator, manuscript pages | 43,094 | `a23947dd5f9fa42f1f343a961ab30e8a719313e5fd45feb528ffd6f9a8589b97` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_final_s2` | 2 | governed + innovator, manuscript pages | 43,089 | `0dacf0f4fc1268e3803dfa8fc64a550358f760d400bc931fd65531276161ae81` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_final_s3` | 3 | governed + innovator, manuscript pages | 43,135 | `177bf983315bec3f7e8581fa7772adaec84e9a373c3c7107ecf6bcf9af993615` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_list70` | 1 | governed + innovator, manuscript pages | 43,761 | `7ffac689ecea7198ab9d01d7c1d03758993df5b07d87c9e0a823ee569b428ccc` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_list70p` | 1 | governed + innovator, manuscript pages | 42,679 | `0fcd40b026bb30559c4117f76f8108081d0277b157d86eea210193ba4852b9fd` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_noinnov_far0` | 1 | governed, manuscript pages | 47,482 | `1a7ffb123d7d0f0f534eaa75d3c4d6cefbe61e80479d19815cd1fbf0d3ad1eea` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_noinnov_far0_s2` | 2 | governed, manuscript pages | 47,294 | `4fdc77f34b1dfbebb31a0d82ab24af017b5944b6bbfcac2454e1cc884663e840` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/n_noinnov_far0_s3` | 3 | governed, manuscript pages | 47,126 | `f4f943a19a462ad8ca580b580063f719d5e6af5bb286035ab91423f90bb1ea29` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_far0_spatial` | 1 | governed + innovator, far 0, manuscript pages | 45,258 | `0086aa0b470dbbeb4d16f30658128598bf5a55d11ce652e4134e55e582c5d63a` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_far0_spatial_s2` | 2 | governed + innovator, far 0, manuscript pages | 46,092 | `946f0e77ca48ab2c79137df140bf3f5b13062f41480c66050ad6da44e22d7b4e` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_far0_spatial_s3` | 3 | governed + innovator, far 0, manuscript pages | 45,202 | `511373d11f087eacb7e4bc4e394336530e9b6c660007b6ab68c316e22736ffb1` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_noinnov_spatial` | 1 | governed, manuscript pages | 48,850 | `0d686bfeaf20cf3d7765783ebc67e5a3c4b50d511b68c3b03c4046890629a5c3` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_noinnov_spatial_s2` | 2 | governed, manuscript pages | 49,802 | `3031568f9dcd119d804cd9a8bce120c4f19a6643d028143c6047ae97ea43015d` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_noinnov_spatial_s3` | 3 | governed, manuscript pages | 49,162 | `9ce56140dc23f571a491512bf1dce3122c297cc26517ff146feabaf9ae8133b7` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_timm_spatial` | 1 | Timm (every temperature zero), manuscript pages | 46,146 | `4d17f1e4e5aa84c1c628dfe48ccd2d03a270f9e3fc5f0b0ff9a08aab8e548ab2` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_timm_spatial_s2` | 2 | Timm (every temperature zero), manuscript pages | 45,431 | `e84b5c3c91ee465ad47972046c73c4bbf59ae9170d9401bed211c6a8900958a7` |
| `reproduce/research/dynamic_selfcitation_20261024/governed/runs/p_timm_spatial_s3` | 3 | Timm (every temperature zero), manuscript pages | 44,977 | `3e2cb4c21133fc897531d7ef8d0b93b30c44e24094ad88ef4f0a38aa7c1e3bf8` |

Not included: the manuscript's transliteration and the evaluation scripts. The comparisons with the manuscript shown
in the app were computed in the research workspace and are published as data under `data/`.
The newer experimental methods have settings, seed summaries and verified text hashes in
`data/comparison_index.json.gz` and `data/comparison_runs/`; their experimental generator variants are not part of
this original-run reproduction kit.

## The template availability experiment

`experiments/mattr_template_link/` is a self-contained reproduction kit for a follow-up study that asks whether
the manuscript's MATTR drops are the collapses that copying from the page produces in the generators: the
scripts, their inputs (the manuscript tokens in Path 1 order, the physical map, the recorded word rectangles,
the saved generator streams and the positional data from `reproduce/`, the comparison texts), the logs and
figures they wrote, and the write-up `RESULTS.md`. Its `README.md` gives the run order and the numbers to
check first. It reads the app's data and heatmap scripts and changes nothing in the app.

The `alignment_rerun_20261028/` subfolder rechecks the spatial-diversity/repetition result against the reviewed
word assignments, with paired paragraph/page shuffle controls and held-out prediction. Historical scripts
explicitly retain the 27 October geometry; this rerun compares it with the corrected and strict geometry.
Its results, input hashes and runnable checks are included. Manuscript images are not required.
The rerun defaults to its preserved `inputs/words_review_v1.json.gz` snapshot; use `--input` to choose
a newer app bundle explicitly. Later compound and boundary repairs therefore cannot silently replace
the input behind the saved results.

## Versions and caching

Each release has a version, `YYYY.MM.DD` (then `.2`, `.3` … for later releases the same day), shown in the menu and
in `version.json`. Every file the page loads is requested with a fingerprint of
its contents (`file.js?v=<hash>`), so a release replaces exactly the files that changed and a page never mixes two
releases. When served from GitHub Pages, a browser may reuse a page for up to ten minutes, so a served copy reads
`version.json`, bypassing the cache, and offers a reload when a newer release is live.

## Contents

| Path | What it is |
|---|---|
| `index.html` | Overview |
| `reconstruction.html`, `data/reconstruction.json.gz` | Hindsight copy-and-edit sequences for the five studied bifolia, with page-only source diagnostics |
| `heatmap.html`, `data/mattr_heatmap/` | Manuscript word-position heatmap, downloadable figures, coordinate attribution and scoring provenance |
| `pages.html`, `comparison.html`, `innovation.html`, `charts.html`, `validation.html`, `modifications.html` | The app's pages |
| `*.js`, `*.css` | App code and styles |
| `data/` | The data the app reads: run manifest, model constructions, per-page journals, statistics, diffs (gzip JSON) |
| `reproduce/` | The governor, the model files, the featured runs and the pinned generator source (see above) |
| `release.js`, `version.json` | The release stamp and the update check |

## Sources

- Generator: Torsten Timm, [SelfCitationTextgenerator](https://github.com/TorstenTimm/SelfCitationTextgenerator), the
  pinned commit named on the Modifications page.
- Text: the Zandbergen–Landini (ZL) transliteration in IVTFF format, from René Zandbergen's site
  [voynich.nu](https://www.voynich.nu/), as prepared for the positional model.
- The order of the bifolia and their groups come from an earlier composition study of the same project.
- Heatmap coordinates: The Voynichese Project (2014), Apache-2.0. The atlas uses word rectangles without scan images.

## This repository is generated

The app is developed in a separate research workspace, which is not published. A publishing script copies the app
and the reproduction files here, replacing the files it manages, so changes made here are overwritten. Files added
here by hand, such as `CNAME` or `LICENSE`, are left alone.
