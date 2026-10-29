# Agent handoff: reproduce the surviving diversity–repetition signal

**Version 2026-10-29.1 — AI-assisted analysis, supplied for independent reproduction.**

Please explain to Koen at the outset: **the manuscript signal is not a test of whether Timm’s citation model generated the manuscript.** Timm and other saved generators are mechanism controls. A generator’s mismatch constrains that configuration; it is not, without a demonstrated general criterion, a rejection of every process that reuses or transforms existing material.

## Question and result

Does source diversity predict target repetition beyond the relationship created by word length, pool geometry and the vocabulary of the assigned paragraph?

For the full source selector, the manuscript’s **H2** relationship survives 4,999 paragraph × exact-length permutations in each geometry. Lower H2 accompanies a higher target repeat-window score.

| Geometry | Targets | Observed contrast, pp | Mean shuffled contrast, pp | Excess, pp | Exceedances | One-sided p | Holm p, four primary tests |
|---|---:|---:|---:|---:|---:|---:|---:|
| Recorded | 15,842 | 3.220205 | 0.690028 | 2.530178 | 24/4,999 | 0.0050 | 0.0150 |
| Synthetic | 15,614 | 3.494241 | 0.864378 | 2.629863 | 16/4,999 | 0.0034 | 0.0136 |

This is a reproducible, arrangement-dependent association that remains difficult to explain. The result is not explained by the fixed slot lengths, source geometry or unordered paragraph vocabulary alone under this null. It is not a measurement of copying probability or of a change in global MATTR.

Copying or another generative process selecting pre-existing material supplies a concrete possible mechanism. One saved no-innovator spatial copier has full-pool H2 excess **4.151178 pp**, p = **0.001** with 999 draws. The other two selected copiers do not show a significant full-pool H2 excess. The finding is compatible with copying, not a universally necessary or sufficient diagnostic of it.

## What the statistic means

- **Outcome:** for target token i, the fraction of its 100 containing, complete 100-token windows in which its spelling appears more than once. Targets must have 99 preceding and 99 following tokens within their bifolium. This outcome includes both past and future repetition.
- **Full source pool:** previous tokens on the same page, in the eight-line-pitch cone above the target (45-degree half-angle), plus same-line reach of three **median word widths**, capped at 100 sources and weighted by alignment/(1 + distance)^2. It is not “three previous words.”
- **Components:** effective number of adjacent glyph-unit pairs, using each word’s normalized pair distribution before weighted pooling.
- **H2:** conditional glyph entropy within those source words. It is not next-word entropy of the text stream.
- **Word diversity:** weighted Simpson diversity of source word spellings. It is a separate measure and includes a weight-only contribution.
- **Primary contrast:** low minus high diversity quintile within each bifolium × exact character length 2–9 × pool-count band cell; at least 25 targets per cell. Each cell’s contrast receives weight equal to its target count. Pool-band cutpoints are pooled-cohort 33rd/67th percentiles, fixed across permutations, with boundary values in the lower band.

## Essential constraints and controls

1. **H2 is the most consistent result.** Primary component p-values are 0.1818 recorded and 0.0182 synthetic; the latter has Holm p = 0.0364. Plain word-diversity p-values are 0.1992/0.0018 as secondary tests. Do not combine them into an assertion that every diversity measure survives equally.
2. **Further pool control and target-anchor checks:** the exact pool-count residual test retains H2 evidence, p = 0.0012/0.0090. It reports −r, a different statistic from the quintile contrast. The left-edge target-anchor test on a shared cohort gives p = 0.0002/0.0006. Five-band quintiles weaken the synthetic result, including on the same cohort as three bands (p = 0.0092 versus 0.0696).
3. **Original-line null:** H2 p = 0.025/0.034, Holm p = 0.100/0.102. This preserves original transcription-line × length bags, before synthetic reflow. It does not preserve every final visible row. Its weaker result does not establish that line vocabulary organization caused the association; copying can create structure that this null retains.
4. **Location:** Stars-dominant groups 3c/4c supply about 60% of primary targets and substantial support. Removing them leaves positive estimates but p = 0.1738/0.1380. Bio is inconsistent; the eligible Herbal samples are small. Do not infer absence outside Stars from a nonsignificant subset test.
5. **Historical controls:** all twelve passage/geometry combinations from five historical texts, including two Rhazes passages, have negative full-pool H2 excesses. This distinguishes the manuscript within that control set, not among all possible languages or generative processes.
6. **Rhazes:** start 566 has nominal above-only matches, including synthetic H2 p = 0.0018, but best Holm p across the 48 historical above-only comparisons is 0.0864. Start 16,785 does not show convincing above-only departures. Neither passage reproduces the positive full-pool H2 result. Preserve this distinction; do not combine the two passages into one enlarged shuffle run.

These corrections cover the declared families, not every earlier exploratory choice. The geometries and overlapping passages are not independent replications.

## Responding to the four forum points

**Directionality.** A forward causal process can leave associations on both sides of a token in the finished text, particularly with this symmetric repeat outcome. Symmetry is not a proof of backward causation or a general disproof of reuse. The supplied mirror attachment uses full above-left/below-right pools, includes same-line words, does not jointly length/pool-control its component comparison, uses one manuscript shuffle, and does not calculate H2. Its separate directional bootstrap intervals are not a paired directional test.

The repository also supplies a concrete calibration counterexample: `p_noinnov_spatial_s2` has the older component mirror estimates **up = 0.0964007308**, **down = 0.0974928948**, approximately symmetric. Run `python mirror_calibration.py` to reproduce the full-precision reference values. This does not assert exact equivalence or replace a controlled H2 direction test. It demonstrates that a 2.5 ratio is not universal even among the saved copying processes. The attachment itself also reports approximately symmetric word-diversity contrasts for its selected copiers.

**Normal repetition and excessive simulated troughs.** A model can overshoot overall repetition or trough frequency while reuse remains a possible contributor to the manuscript. Marginal repetition amount and a conditional source-diversity relationship are different properties. The reported “five times” trough claim is not operationally documented in the supplied mirror attachment; do not present it as independently reproduced by this kit.

**Near-misses.** The forum’s reported 1.3 enrichment and Caesar/Alice comparison concern an edit-neighbour statistic. They constrain a joint combination of source selection, mutation, distance definition and background vocabulary, not mutation alone. They do not directly test H2. Their calculation is not present in the mirror attachment and is not independently reproduced here.

**Stable forms.** Intact recurrence and lack of a nearby edit neighbour constrain compulsory local-mutation models. They do not establish that no words were reused or generated from pre-existing material. Do not claim that all forms drift under every copying process, or that stable forms are a mutation-only question; source access and the mixture of processes matter too. The ycheey/shedal counts and neighbourhood exclusions are not supplied by the mirror attachment and are not recalculated here.

**Memory and burstiness.** Naming either is not a demonstrated explanation of the controlled signal. Paragraph shuffles preserve the assigned paragraph vocabulary and frequencies while reducing the association. A sufficient explanation must account for which words occupy which positions. Do not claim that this rules out every memory process: sequential or position-sensitive memory can itself create shuffle-sensitive ordering. Likewise, a burst-only explanation requires a specified model that reproduces the controlled result. The original raw association does not become exactly zero in every shuffle; the reported excess is above a generally nonzero null mean.

**Source/outcome overlap.** The same overlapping source/outcome definitions are used in every shuffle, and both quantities are recomputed. The shuffle baseline therefore measures the coupling generated by those definitions under this null. Demonstrating a positive raw correlation from overlap is insufficient to explain the observed excess. Conversely, the excess alone does not separate copying from every other process that creates local ordering.

## Reproduction plan

1. Re-pull `eo777/vms-dynamic-citation` and enter `experiments/spatial_signal_20261029/`, or extract the standalone kit. Follow [README.md](README.md) for the pinned runtime/dependencies.
2. Run `python reproduce.py --verify-only`. Stop on any altered hash; do not silently replace the frozen input with a newer app bundle or cached geometry.
3. Run `python reproduce.py --suite all --smoke --jobs 4`. Every observed/seeded checkpoint, fixed cohort, independently calculated aggregate and repeat outcome must match. The 19 draws are validation only.
4. Run `python reproduce.py --suite all --jobs 4` for all reported counts and multiplicity families. The manuscript-only option is sufficient to reproduce the four primary tests; Rhazes-only cannot independently reconstruct the 48-test correction.
5. Run `python mirror_calibration.py` for the separate, older mirror calibration. Do not mix its estimates or cohorts with the new controlled statistics.
6. Report the exact input version, geometry, selector, cohort, metric, statistic, null, B, exceedance count, effect size and applicable adjustment. Return a discrepancy only after identifying which of these differs.

## Pooling and comparison rules — do not change these silently

- Keep **length and pool-size controls together**. A length-only analysis is a different test.
- Do not clip length tails to 2 and 9 and call the resulting cells exact length. The primary test excludes lengths outside 2–9; a separate agent-like sensitivity explicitly clips them.
- Do not pool all low and high observations across cells with different weights. Compute the per-cell contrast, then use the prescribed common cell-size weights. Do not replace this with an equal average of tertile contrasts.
- Keep tertile boundaries, their inclusion convention, minimum cell size and target masks fixed. A source-count boundary choice can move many tied targets between bands.
- Keep pools, weights and geometry fixed under same-length substitutions. Compare recorded observations with recorded nulls and synthetic observations with synthetic nulls.
- Use a cohort guaranteed to remain valid under every allowed permutation: ≥5 pair-bearing sources and pair-weight ESS ≥3. Do not let metric validity or cohort membership select different targets in each draw.
- Recompute **both source-content scores and repeat outcomes** after each word shuffle. Retaining observed outcomes tests a different null.
- Keep every text’s own null baseline. Do not compare a manuscript excess with an unsubtracted copier or prose contrast.
- Freeze the Rhazes passage and original block assignments explicitly. Do not let random-call order select a new passage.
- Quantize all score values to ten decimal places before ranking/residualization, for observations and nulls alike; preserve ties in quantile interpolation. Pointwise agreement to floating-point precision does not by itself guarantee identical quintile groups.
- Use `(1 + exceedances)/(B + 1)` with null ≥ observed (tolerance 1e−12). Zero exceedances does not mean p = 0. Keep the fixed draw counts; do not stop at a desired p-value.
- Keep full pools, above-only pools, below-only pools, and the full mirrored selector distinct. A significant test in one and nonsignificant test in another is not a test of their difference.

## Next discriminating test, after reproduction

A direct directional follow-up should compare the full above-left selector and its full below-right mirror on one common, guaranteed-valid cohort, with joint length/pool control, the same matched shuffles, and a paired upstream-minus-downstream statistic. Calibrate it across multiple seeds and copying configurations, including the approximately symmetric spatial copier. Include H2 explicitly and report region-specific estimates without treating the many exploratory comparisons as independent confirmation.

A separate test is needed for the irregular spatial waves: define a quantitative spatial-pattern statistic and test it against controls that preserve the relevant text-order and layout constraints. Neither the older mirror ratio nor the present scalar association alone measures that phenomenon. Do not present an untested alternative as an established explanation, or treat this surviving association as proof of a unique historical mechanism.
