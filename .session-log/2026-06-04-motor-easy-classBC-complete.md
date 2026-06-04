# 2026-06-04 — motor_easy class B+C complete, GT separability validated

## Goal
Complete class C pipeline (simulate → reconstruct → extract → average → visualize), merge
all three classes, and validate that GT class labels are separable.

## What happened

### Class C pipeline (resumed from prior session)
- `run_classC.sh` completed: 5 runs × ~35 particles = **177 subtomos** in `merged_C/`
  - Runs: 37+37+35+35+33 (2 particles skipped near edge across 5 runs)
  - `reconstruct_metadata.py` ran automatically after each kill (quirk #11 fix)
- `avg_gt_classC.py`: GT-aligned average of 177 particles → `avg_classC_aligned.mrc`
- `visualize_classC.py`: 3 verification panels generated and sent to user (tomogram+circles,
  subtomo slices, GT-aligned average orthoslices)
- User confirmed class C output looks good

### Merge A+B+C
- Created `merged_all/` (634 subtomos, raw unaligned) with unified `labels.csv`
  - A=246, B=211, C=177
- Wrote `align_all_classes.py` (new script) to GT-rotate all subtomos using sim_metadata.json
  Euler angles (same P@R@P.T ZXZ convention as avg scripts)
- Created `merged_all_aln/` (634 GT-aligned subtomos) with unified `labels.csv`

### GT separability validation
- **PCA k-means (classify_quick.py)**: ARI=0.003 on both raw and GT-aligned subtomos.
  Expected failure — PCA without templates can't exploit class structure.
- **CC-template matching** (custom diagnostic):
  - Class average cross-correlations: CC(A,B)=0.72, CC(A,C)=0.66, CC(B,C)=0.83
    (B-C more similar than A-B/A-C, makes structural sense: both lack C-ring)
  - Per-particle CC-template assignment: **ARI=0.289**, ~68-73% correct per class
  - Confusion: A→167/246 correct, B→154/211, C→119/177
  - Within-class mean CC vs own average: A=0.18, B=0.21, C=0.15 (std ~0.13-0.20)
- **Conclusion**: Synthetic data is valid. Classes are structurally distinct in their averages.
  Per-particle separation is achievable (ARI=0.289 with simple template matching) and
  there is headroom for real classifiers (with iterative alignment + wedge compensation) to
  do much better. This is the expected difficulty level for "motor_easy".

## Files changed

### In STA repo
- `STATUS.md` — updated: class C → done, merged_all validated, next = run packages on synthetic

### In ~/Research/synthetic_sta/motor_easy/ (local, not in repo)
- `align_all_classes.py` — NEW: GT-aligns all 634 subtomos into merged_all_aln/
- `avg_gt_classC.py` — ran, output avg_classC_aligned.mrc
- `visualize_classC.py` — ran, output 3 PNG panels

### Outputs (local only, gitignored)
- `production/subtomos/merged_C/` — 177 class C subtomos + labels.csv
- `production/subtomos/merged_all/` — 634 raw subtomos + labels.csv
- `production/subtomos/merged_all_aln/` — 634 GT-aligned subtomos + labels.csv
- `production/subtomos/avg_classC_aligned.mrc`
- `production/subtomos/viz_A_C_tomogram_circles_run01.png`
- `production/subtomos/viz_B_C_subtomo_slices.png`
- `production/subtomos/viz_C_C_average.png`

## Where I stopped
All three motor_easy classes simulated, extracted, averaged, and validated. GT separability
confirmed via CC-template matching (ARI=0.289 per-particle; averages clearly distinct).

## Next step
Run the benchmark classification packages on `merged_all/` and `merged_all_aln/`:
1. **RELION** — use `merged_all/labels.csv` as ground truth; run 3D classification k=3;
   compute ARI/NMI vs GT labels
2. **Dynamo** — same input; Dynamo recovered the two real T4P phases well → compare on synthetic
3. Other packages as time allows
Also consider: running emClarity on synthetic data (it can't run real T4P but was installed
for synthetic track).
