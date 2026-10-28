# Summary figures

## Illustration-section repeat contrasts

`contrast_by_illustration_components_h2.png` (also SVG) uses each page's `section` field from `physical_map.csv`, combining Currier labels within the same illustration section. It retains the Golf chart's controls, legacy geometry and pool-size-stratified repeat contrast. This is a fresh target-level grouping, not an average of Golf-group estimates. The 172 scored Cosmological targets are shown; the 75 Astrological targets cannot support all three bands, so that panel is omitted with a note.

`illustration_contrasts.json` records all plotted values, per-band support, page assignments, input hashes, and verification against the existing Golf and section/Currier estimates. Run `python summary_figures/build_illustration_contrasts.py` to redraw from that compact JSON. Add `--recompute` to rescore the saved text/geometry bundles and rebuild the section statistics. No model is rerun; per-token measurements are temporary.

## MATTR swings

The local report draft now leads with bifolium views. `mattr_bifolia_models.png` and `mattr_bifolia_markov.png` show all 50 bifolia plus an enlarged Herbal B → Stars → Bio stretch. `mattr_bifolia_prose.png` shows the same late stretch for five historical texts separately, each in both reflows; `mattr_bifolia_prose_all.png` shows their complete routes. Section names describe the dominant content of route stretches; mixed bifolia are not reassigned or split. Horizontal labels are physical leaf pairs.

The HTML report collects all seven MATTR figures in one gallery. A thumbnail switches the main chart, caption and selected state; the main chart opens in the full-size viewer. Arrow keys, Home and End also select charts. The Markdown retains the individual figures for standalone reading.

Rebuild these four plots with `python summary_figures/build_bifolium_mattr.py`. Add `--verify-streams` to verify all 50 bifolium values in the manuscript and ten saved copying streams. The resulting `mattr_bifolia.json` records the plotted values, source hash and exact-match verification. The existing group charts also now label every group with its section name.

`mattr_swings_models.png` compares Original Timm's fixed-rule baseline and spatial-source variant with the manuscript, alongside the three Markov controls. `mattr_swings_prose.png` shows all five historical texts individually in both reflows. `mattr_swings_governed.png` keeps the three governed variants separate from the fixed-rule comparison. SVG copies are also saved.

Rebuild these plots from the study's frozen `layout_controls.json` with `python summary_figures/build_mattr_swings.py`. Add `--verify-streams` to recompute group MATTR from the saved manuscript and ten copying streams. The verification matched every group exactly and checked the seed-1 baseline settings (`beta_c=beta_m=retry=far=0`, innovator off, manuscript page structure enabled). Two saved seeds per copying configuration and three per Markov configuration match the original route charts. The bands show copying-seed ranges, not uncertainty intervals. `mattr_swings.json` records the input hash, all plotted values, changes, and verification results. No models or spatial pools are regenerated.

## Spatial examples

`../SUMMARY.html` embeds these figures in a portable HTML report with a compact overview, paired close-ups, and a full-size image viewer. Rebuild it from the study directory with `python build_summary_html.py` (requires `markdown-it-py`). The overview uses `f75r_page.png` with A/B markers in the same native coordinates as the PNG figure below; it does not alter the captured word boxes or their colors.

`f75r_page_context.png` shows translucent component-diversity colors on the manuscript's recorded word boxes before the close-ups in `component_diversity_examples.png`. Both close-ups are screenshots of the alignment viewer with its original Voynichese image, green word boxes, text labels, source cone and left-reach indicator. Rebuild the figures with:

```sh
python summary_figures/build_component_examples.py
```

The captures are `f75r_page_app.jpg`, `f75r_high_app.jpg` and `f75r_low_app.jpg`. Each has a matching `_capture.json` with the browser viewport, crop bounds, URL and displayed score. The builder crops these screenshots and adds figure titles, a color scale and the A/B location markers; it does not redraw the source windows. The full-page colors use the heatmap app's palette and full-path 5th–95th percentile range (9.5344–27.2994 effective pairs), with 58% fill opacity.

The examples are study tokens 32564 (`f75r.28@73:80`, 22.0999 effective pairs) and 32673 (`f75r.41@26:33`, 13.6280 effective pairs). `component_examples.json` records their scores, source memberships, weights, original image URL and word-bundle hash. The coordinates are the native `display_parts` used by the source viewer. Guide lengths use a uniform page scale of 0.7159525, checked against 422 corresponding native/XML box centers (maximum axis residual 1.445 display pixels); each guide is anchored to the exact displayed target center. The word boxes themselves are not fitted or rescaled from XML rectangles.

Overview colors for boxes without a scored study-token position are computed at each original XML rectangle, using the same source inventory. These display scores do not change the study's saved aggregate results.

For the close-ups, open the local app's `alignment.html`, select f75r and the desired target, and enable **Original Voynichese image**, **ZL labels over boxes**, **Spatial source window**, and **Close-up**. For the full page, clear the selection and choose **Box colors: Component diversity**. The capture URLs preserve these settings. Both examples were also visually inspected with the labels hidden to check the boxes against the handwriting.

`method_spatial.png` combines a capture from the heatmap app with an explanation of the repeat statistic. Rebuild it with:

```sh
python summary_figures/build_method.py
```

The app capture was taken on 28 October 2026 in the light theme, with f78r expanded and the third `otedy` selected (study token 31343). Selecting the word displays the source spellings over their boxes. The app reported 40 source words and 20.3 effective pairs, matching the study example.

View settings:

```text
heatmap.html#scope=4a&window=100&direction=spatial&colors=components&left=3&depth=8&angle=45&weight=distance&expanded=f78r
```

`f78r_otedy_app_full.jpg` preserves the actual app screenshot. The builder crops its page graphic to `f78r_otedy_app.png`, omitting the controls and readouts. It does not redraw the boxes, text or source cone.

`method_example.json` contains the frozen study example used for the repeat-window illustration. `export_method_example.js` documents its extraction; the figure builder needs only the saved JSON and screenshot. The example's repeat score is 83/100. The +0.061 aggregate contrast is from the original study's comparison stratified by source-pool size.

The recorded word coordinates are from The Voynichese Project (2014), Apache-2.0; see the app's `data/mattr_heatmap/NOTICE.txt`.

`pages_f75r_f116r.png` is the replacement page comparison supplied by the author, copied without modification.
