# Spatial diversity–repetition signal: reproducibility kit

Version **2026-10-29.1**. Frozen analysis: **36,979 shuffled evaluations**, 17 text/geometry combinations and four additional original-line nulls. This is an exploratory follow-up on existing data, not a new manuscript sample.

Start with [AGENT_FOLLOWUP.md](AGENT_FOLLOWUP.md) for the question, key results and interpretation. The kit contains only the necessary inputs, scoring/preparation code, expected results and validation checkpoints. No internal discussion, agent logs, generated models, screenshots or superseded runs are included.

## Get the update

The repository location is `experiments/spatial_signal_20261029/` in `eo777/vms-dynamic-citation`. In an existing checkout on `main`, with local work safely preserved:

```text
git pull --ff-only
cd experiments/spatial_signal_20261029
```

Alternatively, extract the standalone kit and enter its `spatial_signal_20261029` directory. The commands below work in either location. They do not depend on the rest of the repository or contact the network after dependency installation. Old release `a97315b` does not contain this follow-up.

## Requirements

- Python **3.9–3.12** for the pinned dependency versions; Python 3.9.2 was used for the reference calculation.
- Node.js on `PATH`; the reference runtime was **24.15.0**.
- `numpy==2.0.2`, `scipy==1.13.1`.

```text
python -m pip install -r requirements.txt
python reproduce.py --verify-only
```

Use a virtual environment if appropriate. For an existing Python 3.13 environment, use a separate Python 3.12 environment for these pins rather than silently changing the numerical dependencies. Runtime differences are recorded, and reference comparisons fail explicitly on a mismatch.

## Recommended reproduction sequence

First run the short check across every text, geometry and null:

```text
python reproduce.py --suite all --smoke --jobs 4
python mirror_calibration.py
```

The smoke run uses 19 draws solely to check exact observed/seeded checkpoints, all statistics, independently calculated source-score aggregates, and independently calculated repeat outcomes. **Its p-values are not research results.**

Then reproduce the complete reported analysis:

```text
python reproduce.py --suite all --jobs 4
```

This uses 4,999 paragraph draws for each manuscript geometry and each geometry of Rhazes start 566; 999 for the other historical passages and copiers; and 999 original-line draws for manuscript/Rhazes start 566. Expect tens of minutes for the full suite, depending on hardware. Use `--jobs 1` or `2` on smaller machines; the seeds and results do not depend on scheduling. Allow roughly 1 GB of temporary disk and several GB of RAM for four simultaneous jobs.

For a focused check instead of the complete suite:

```text
python reproduce.py --suite manuscript --jobs 2
python reproduce.py --suite rhazes --jobs 2
```

These are alternatives to rerunning the complete suite. The Rhazes-only command verifies nominal results; the **48-test historical adjustment requires the complete historical family**, included in `--suite all`.

## What success means

Every run must print `PASS`. A full run compares observed values, null means and variances, exceedance counts, permutation p-values, regional results and primary block-bootstrap intervals with `expected_results.json`. It also checks fixed cohorts and deterministic draws against `expected_checkpoints.json`. Completed families must reproduce their Holm adjustments exactly.

`validation.json` records the release checks: all full-reference summaries and adjustments were recomputed from the saved draws; all 21 portable runs were rebuilt from the bundled inputs and passed the 19-draw check. The unchanged shuffle kernel generated the full reference calculation.

Outputs go to `runs/smoke/` or `runs/full/`, or an explicit `--output PATH`. `results.json` contains the selected suite and its runtime details; individual JSON summaries and compressed draw statistics remain beside it. Temporary pool arrays are discarded only after validation. Running another suite in the same output directory replaces the combined `results.json`; use different output directories when keeping separate suite summaries.

The optional `mirror_calibration.py` reproduces two **older, within-bifolium** mirror point estimates. It is a calibration check of the claimed universal directional ratio, not a jointly controlled directional inference or a significance/equivalence test.

## Frozen inputs and boundaries

`input_manifest.json` identifies the exact bundled inputs. `kit_manifest.json` hashes the distributed code, inputs, specifications and expected results. No current heatmap cache is used. “Recorded” explicitly means the frozen **legacy geometry** selected in this study; synthetic boxes use the frozen placement rule. A corrected/strict geometry policy is a separate analysis and must not silently replace this snapshot.

Natural texts use Latin/German letter pairs; manuscript and copier texts use Zattera glyph-unit pairs. Historical paragraph/line/bifolium assignments and layouts are borrowed from the manuscript, not the original printed books. Both Rhazes offsets are explicit; the passages overlap and are not independent replications.

The kit does not rerun generators, fit a copying model, or measure the irregular visual waves as a separate outcome. It establishes what the specified association does under its matched nulls.
