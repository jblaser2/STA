# Session: packages/README.md figures gallery (2026-06-08)

## Goal
Add visual figures to `packages/README.md` so classification quality is
immediately scannable per dataset and per package.

## What happened

**Design decisions (via AskUserQuestion):**
- No confusion matrices for T4P (no ground truth); replace with cross-package
  pairwise co-tabulation heatmaps for the 4 converged packages
- Images in table cells (`<img width=...>` inline HTML)

**New scripts written:**
- `scripts/eval/gen_class_avg_panels.py` — standardized N-panel central-slice
  PNG from MRC or PNG inputs; used to fill pending cells when MRC files accessible
- `scripts/eval/gen_perfect_confusion.py` — 3×3 diagonal confusion matrix for
  motor_easy ground truth (A=246, B=271, C=177)
- `scripts/eval/gen_cross_pkg_correlation.py` — 6-pair pairwise co-tabulation
  grid from the 4 T4P package assignment CSVs

**Figures generated and committed:**
- `packages/figures/T4P/cross_pkg_correlation.png` — 6 pairwise heatmaps
- `packages/figures/T4P/pytom_k2_class_avgs.png` — combined 2-panel from
  existing `PyTom/figures_v2mask_k2/class_{0,1}_central_slice.png`
- `packages/figures/motor_easy/perfect_confusion.png` — ideal reference matrix

**README changes (`packages/README.md`):**
- T4P section: added PEET v2 reference-averages header image + cross-package
  correlation figure; new "Class Avgs (best k)" column in table
- motor_easy section: added GT reference (pending) + perfect-confusion header;
  new "Class Avgs (best k)" + "Best Confusion" columns in table

**Scientific finding from cross-pkg figure:** Dynamo, PyTom, and PEET agree
well on T4P particle assignments (pairwise ARI 0.36–0.53), confirming the
ring_complete/ring_altered split is stable. OPUS-TOMO's threshold-mask split
is entirely uncorrelated with all three (ARI ≈ 0), meaning it divides particles
along a different (unrelated) axis despite having a similar 447/225 count.

## Files changed
- `packages/README.md` (modified)
- `packages/figures/T4P/cross_pkg_correlation.png` (new)
- `packages/figures/T4P/pytom_k2_class_avgs.png` (new)
- `packages/figures/motor_easy/perfect_confusion.png` (new)
- `packages/dynamo/dynamo_outputs/motor_easy_pca/confusion_dynamo_k3_k3_pca_nc_best_cnew.png` (newly tracked)
- `scripts/eval/gen_class_avg_panels.py` (new)
- `scripts/eval/gen_cross_pkg_correlation.py` (new)
- `scripts/eval/gen_perfect_confusion.py` (new)
- `STATUS.md` (this handoff)

Committed + pushed as `4e1b90c`.

## Where I stopped
All figures that can be generated without local MRC files are done and committed.
Pending cells (marked `_(pending)_` in README):
- T4P: OPUS-TOMO k=2 class avgs, EMAN2 k=2 class avgs
- motor_easy: class-avg panels for RELION, PEET, Dynamo, OPUS-TOMO, and the
  GT reference averages

## Next step
For each pending cell, find the local class-average MRC files for that
package's run and call:
```bash
python3 scripts/eval/gen_class_avg_panels.py \
    --inputs <class0.mrc> <class1.mrc> [<class2.mrc>] \
    --labels "Class 0 (N)" "Class 1 (N)" ["Class 2 (N)"] \
    --title "<Package> k=<K> (<mask>)" \
    --out packages/figures/<dataset>/<pkg>_k<K>_class_avgs.png
```
Then replace the `_(pending)_` text in the README table cell with the
appropriate `<img src="figures/..." width="150">` tag.

After that: compute ARI between OPUS-TOMO T4P and PEET soft-GT (still listed
as uncomputed in STATUS.md OPUS-TOMO row).
