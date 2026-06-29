# 2026-06-29 — T4P No-GT Evaluation Framework

## Goal
Iron out the evaluation framework for T4P (no ground truth). Specifically: cross-package
comparison using the 4 converging packages (Dynamo, PEET, PyTom, ProTomo) and a
noise/stability test to confirm packages are finding real signal not noise.

## What happened

### ProTomo per-particle CSV
ProTomo's T4P classification was previously only visual — no CSV existed.
- Source: `/home/jblaser2/Research/protomo/process/cycle-000/t4p-000-class.i3i`
- Extraction: `tomoinfo -cls` outputs `[ k ] idx class` (0-based idx, class 2 = junk)
- Particle order: sorted `.mrc` filenames in `prepare/stacks/` (matches Dynamo CSV order)
- New script: `scripts/eval/extract_protomo_classes.py`
- Output: `results/protomo_T4P_k2.csv` (334 class-0 / 212 class-1 / 126 junk excluded = 546 rows)

### Cross-package comparison updated
`scripts/eval/gen_cross_pkg_correlation.py` rebuilt:
- Now scoped to 4 converging packages only (Dynamo/PEET/PyTom/ProTomo; OPUS-TOMO + DISCA removed)
- PEET junk (class 3) filtered at load time; ProTomo junk already excluded at extraction
- ARI computed on intersection of non-junk particles per pair
- New 7th panel: per-particle consensus histogram (how many of 4 packages agree per particle)
- New figures: `packages/figures/T4P/cross_pkg_correlation.png`

### Key numbers from cross-package analysis
- Pairwise ARI (all 6 pairs): Dynamo–PEET 0.438, Dynamo–PyTom 0.492, Dynamo–ProTomo 0.431,
  PEET–PyTom 0.650, PEET–ProTomo 0.405, PyTom–ProTomo 0.456
- High-consensus core (3/3 other packages agree with Dynamo): **357/672 = 53%**

### New evaluation scripts
- `scripts/analysis/build_labels_matrix.py` — aggregates all 4 package CSVs → 672×5 matrix
  with consensus_score column; outputs `outputs/benchmark/T4P_labels_matrix.csv`
- `scripts/eval/clusterboot_t4p.py` — Hennig 2007 bootstrap Jaccard in Dynamo UMAP/tSNE space
  (only package with saved embeddings); 20 draws, 80% resample; Dynamo weighted avg Jaccard = 0.63
- `scripts/eval/noise_perturb_t4p.py` — Gaussian noise added to embedding coords at σ ∈ {0,0.1,
  0.25,0.5,1.0,1.5,2.0}×dim_std; ARI decays 0.54→0.07 (gradual = real structure); figure:
  `packages/figures/T4P/noise_perturb.png`

### Documentation
- `docs/benchmarkIdeas.md §12` — formal no-GT evidence chain (E1–E7 table with scripts + numbers)
- `packages/README.md` — cross-package figure + consensus numbers above T4P table
- `README.md` — cross-package eval section with embedded figure between UMAP and FM_easy

### Commit + push
All committed as `bdd8bcb` and pushed to GitHub. Cross-package correlation figure is now
embedded in both READMEs and renders directly on GitHub.

## Files changed
**New:** `scripts/eval/extract_protomo_classes.py`, `scripts/analysis/build_labels_matrix.py`,
`scripts/eval/clusterboot_t4p.py`, `scripts/eval/noise_perturb_t4p.py`,
`results/protomo_T4P_k2.csv`, `outputs/benchmark/T4P_labels_matrix.csv`,
`packages/figures/T4P/noise_perturb.png`

**Modified:** `scripts/eval/gen_cross_pkg_correlation.py`, `packages/figures/T4P/cross_pkg_correlation.png`,
`docs/benchmarkIdeas.md`, `README.md`, `packages/README.md`, `STATUS.md`

## Where I stopped
All scripts written and tested, figures generated, committed and pushed. The no-GT evidence
chain (§12) is complete through E6. E7 (FSC gain vs unsplit baseline) is the one remaining
data point — Dynamo has per-class FSC but the unsplit average FSC hasn't been computed.

## Next step
1. Compute unsplit T4P FSC (Dynamo half-set reconstruction on all 672 particles) → fill E7
2. Begin FM_hard package runs (k=3, start PEET/DISCA/Dynamo, use `diff_mask_hard.mrc`)
