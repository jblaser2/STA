# 2026-06-03 — PEET WMD PCA sweep + T4P classification ground-truth investigation

## Goal
Investigate whether we can reproduce Stefano's PEET classification (509:95, 5.4:1 ratio) on our
672 pre-aligned T4P subtomograms to establish per-particle ground-truth class labels.

## What happened

### Open questions resolved (from T4P_classification_handoff.md)
1. **Dynamo per-class counts (HAC, not MRA):** Class 1 = 447, Class 2 = 225 → ratio 2:1. No junk
   class was applied (k=2, all 672 assigned). This does NOT match the paper's 5.4:1 piliated ratio.
   The "Dynamo recovers them well" statement was qualitative only; ratio had never been checked.
2. **"~80 subtomograms":** This was Protomo's Class 1 result (80 of 234 filtered particles, 34.2%)
   from the 2026-05-29 Protomo session — not a per-cell average, not from Stefano's paper.
3. **Packages in scope for K=3 reproduction protocol:** PEET (reference) + Dynamo confirmed;
   RELION (k=3 already exists, needs ratio analysis); EMAN2 (needs k=3 run, env ready).

### PEET WMD PCA with ±60° tilt range
- **Problem identified:** Previous PEET runs had `tiltRange = {}` (no wedge correction). Added
  `tiltRange = {[-60, 60]}` and `flgWedgeWeight = 1` to prm (both repo and local copies).
- **Bug fixed:** `pca` iterationNumber arg is "alignment iterations completed" (n), which reads
  MOTL at Iter(n+1). We had 1 alignment iteration so MOTL is at Iter2 → use `iterationNumber=1`,
  not 2. Passing 2 caused "Error reading peet_single_MOTL_Tom1_Iter3.csv".
- **WMD PCA rerun:** `pca prm 1 672 peet_single_AvgVol_1P672.mrc 1` → `pca672_peet_wedge.mat`.
- **k-means sweep (14 configs):** PCs 1:3, 1:5, 1:10, 1:15, 2:10, 3:10, 1:5+7:10 × k=2 and k=3.
  Best result: **k=2, PCs 1:3 → 412:260 (1.58:1)**. No configuration approached 5.4:1.
- **HAC sweep (8 configs):** All degenerate → 671:1 regardless of feature selection.
- **Class averages generated:** `winner_class_1_avg.mrc` (412p) + `winner_class_2_avg.mrc` (260p),
  low-pass filtered to 30 Å for display. Viewed in 3dmod — user confirmed "definitely closer to
  Stefano's results."

### Root cause: why we can't reproduce 5:1
Stefano's PEET run had real per-particle tilt geometry — each particle from a different tomogram
at a different physical orientation, so every particle had a different missing-wedge direction.
PEET's WMD correction (WMD_i = particle_i ⊗ wedgeMask_ref − grandAvg ⊗ wedgeMask_i) did genuine
per-particle work. Our pre-aligned stack has all 672 particles in one "tomogram" with uniform
zero-angle poses → identical wedge direction for all particles → WMD degrades to applying the same
Fourier mask to all particles, removing structural signal rather than correcting for it.
The previous artifact-driven 602:70 split (no wedge mask) was largely missing-wedge artifact.
The ~1.5:1 k-means result (with wedge mask) is the true structural signal visible without proper
per-particle wedge geometry.

## Files changed
- **Updated:** `peet/peet_project_single.prm` — `tiltRange={[-60,60]}`, `flgWedgeWeight=1`
- **Updated:** `STATUS.md` — PEET matrix row, Now/Next/Parked, Open Decisions
- **Created (local only, not committed):**
  - `~/Research/peet/results/run_pca_sweep.sh` — WMD PCA + 14-config k-means sweep
  - `~/Research/peet/results/post_sweep.py` — parse sweep logs, generate class averages + PNG
  - `~/Research/peet/results/pca672_peet_wedge.mat` — WMD-corrected PCA output
  - `~/Research/peet/results/sweep_k*.log` + `sweep_*_MOTL.csv` — all sweep results
  - `~/Research/peet/results/winner_class_{1,2}_avg.mrc` — class averages from best split

## Where I stopped
Class averages generated and viewed in 3dmod. User confirmed visual improvement over previous
results. Did not establish exact match to paper's 5:1 split — fundamental limitation confirmed.

## Next step
1. **Email Stefano** for his PEET MOTL files (per-particle class labels from the preprint run).
   This is the only reliable path to exact ground-truth labels per subtomogram.
2. **Interim:** use Dynamo HAC labels (447:225, `dynamo/dynamo_final_results/class_assignments.csv`)
   as proxy ground truth for the benchmark — confirmed visually by Stefano.
3. **K=3 cross-package protocol:** implement the K=3 + junk-exclusion rule in
   `classification/protocol.md` (see handoff doc); then run RELION k=3 ratio analysis and EMAN2 k=3.
