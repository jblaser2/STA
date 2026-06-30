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

---

## Session continuation (2026-06-29 — class avg panels + FSC)

### Standardised class-average figures (all 7 T4P packages)
- New script: `scripts/eval/gen_t4p_class_avg_panels.py`
  - For each package: 3-panel figure (ring_complete | ring_altered | junk), XY central slice only,
    particle counts labeled, dark background, consistent display
  - For packages without a pre-computed junk MRC (PEET junk, PyTom all classes, DISCA, OPUS),
    averages computed on-the-fly from raw particles via standardised CSVs
  - Output: `packages/figures/T4P/<pkg>_class_avgs_std.png` for all 7 packages
- `packages/README.md` updated: all Class Avgs cells now point to `figures/T4P/*_class_avgs_std.png`
  (old per-package result-dir paths replaced)

### FSC computation (E7 filled)
- New script: `scripts/eval/compute_t4p_fsc.py`
  - Computes half-set FSC (even/odd particle split) for unsplit 672p, Dynamo k=2 classes, PyTom k=3 classes
  - Outputs: `packages/figures/T4P/fsc_comparison.png`, `results/T4P/fsc_summary.csv`
- Key results:
  - Unsplit (672p): FSC=0.143 at Nyquist (26.7 Å); FSC=0.5 also at Nyquist — classes share gross structure
  - Dynamo ring_complete (447p): FSC=0.5 at 63.3 Å; ring_altered (225p): FSC=0.5 at 98.3 Å
  - **PyTom class 3 (100p): FSC=0.143 at 63.2 Å → CONFIRMED JUNK** (signal classes both at Nyquist)
- PyTom junk status updated: 🟡 → ✅ in STATUS.md, packages/README.md, memory

### Files changed
- **New:** `scripts/eval/gen_t4p_class_avg_panels.py`
- **New:** `scripts/eval/compute_t4p_fsc.py`
- **New:** `packages/figures/T4P/*_class_avgs_std.png` (7 files)
- **New:** `packages/figures/T4P/fsc_comparison.png`
- **New:** `results/T4P/fsc_summary.csv`
- **Modified:** `packages/README.md` (class avg cells + FSC block + PyTom junk ✅)
- **Modified:** `docs/benchmarkIdeas.md` (E7 filled, files generated list updated)
- **Modified:** `STATUS.md` (last-updated block, NEXT list trimmed)

## Where I stopped
Evidence chain E1–E7 complete. PyTom junk confirmed. All 7 T4P packages have standardised
class-average figures in packages/README.md.

## Next step
1. Re-run Dynamo/DISCA/OPUS at k=3 with junk class for T4P
2. Begin FM_hard package runs (k=3, start PEET/DISCA/Dynamo, use `diff_mask_hard.mrc`)

---

## Session continuation (2026-06-29 — STOPGAP compile + T4P stability tests + k=3 junk)

### k=3 junk class added for Dynamo, DISCA, OPUS (T4P)
- **Dynamo k=3**: Ward HAC re-cut at k=3 from existing `ccmatrix.npy` → 447/157/68junk; `dynamo_k3_std.csv`
- **DISCA k=3**: standardized from existing `disca_cyl_v2_k3.csv` → 315/267/90junk; `disca_k3_std.csv`
- **OPUS k=3**: retrained 20 epochs (~2 min RTX 5080), k-means at k=3 → 368/221/83junk; `opus_k3_std.csv`
- Class-avg panels generated for k=3 variants; packages/README.md updated

### T4P stability tests updated (actual computed values)
`clusterboot_t4p.py` and `noise_perturb_t4p.py` updated to include PEET PCA (from `pca672_peet_wedge.mat::coeffs`):
- **Dynamo UMAP Jaccard (Hennig 20×80%)**: 0.562 weighted [MODERATE] (class1: 0.587±0.044; class2: 0.513±0.040)
- **PEET PCA Jaccard**: ~0.247 [FRAGILE] — invalid due to WMD gap (PEET's original clustering used WMD-weighted k-means, not raw PCA)
- **Dynamo UMAP noise ARI**: σ=0: 0.351 (not 1.0 — HAC-vs-k-means method gap), σ=0.5: 0.244, σ=2.0: 0.050
- `docs/benchmarkIdeas.md §12` updated with actual values and PEET WMD caveat
- `results/T4P/clusterboot_summary.csv` and `results/T4P/noise_perturb_summary.csv` generated

### STOPGAP compiled locally
- User installed MATLAB Compiler toolbox (R2024a); `mcc` now at `~/Applications/matlab/bin/mcc`
- `packages/STOPGAP/compile_local_r2024a.sh` written and run successfully
  - **Key fix:** MATLAB `-batch` rejects multi-line bash strings; solution = write commands to temp `.m` file and call `matlab -batch "run('$FILE')"`
  - `compile_toolbox.m` paths patched via `sed -i` (was hardcoded to Eben's `/home/ejl62/...`)
  - All 4 binaries compiled, verified, smoke-tested: stopgap, stopgap_parser, stopgap_watcher, sg_toolbox
- STOPGAP can now run locally with `run_type='local'` + `mpiexec` (no SLURM needed)
- STATUS.md updated: STOPGAP row changed from "blocked (cluster)" → "UNBLOCKED"

### STOPGAP T4P PCA k-means CSV extracted
- Particle order from alphabetical sort of `aligned_tom*_P*.mrc` (matches `build_inputs.m` MATLAB `dir()`)
- k-means on `eigenval_1.csv` (672×10 PCA scores, StandardScaler + top-10 components)
- k=2 result: 385/287; **ARI=0.07 vs Dynamo** → confirms STOPGAP non-convergence on T4P
- Saved: `results/T4P/stopgap_k2_std.csv`

### Cross-package correlation (re-verified)
- Script already uses ProTomo (not OPUS) as the 4th converging package
- Re-run: pairwise ARI 0.40–0.65 (Dynamo×PyTom 0.510, PEET×PyTom 0.653)
- 309/672 (46%) high-consensus core confirmed

## Files changed (continuation)
**New:** `packages/STOPGAP/compile_local_r2024a.sh`, `results/T4P/clusterboot_summary.csv`,
`results/T4P/noise_perturb_summary.csv`, `results/T4P/stopgap_k2_std.csv`

**Modified:** `scripts/eval/clusterboot_t4p.py` (added PEET PCA), `scripts/eval/noise_perturb_t4p.py`
(added PEET PCA + CSV output), `packages/STOPGAP/src/stopgap/compile_toolbox.m` (paths patched),
`packages/STOPGAP/exec/lib/stopgap_config_local.sh` (R2024a matlabRoot),
`packages/STOPGAP/exec/lib/stopgap_config_slurm.sh`, `packages/STOPGAP/exec/lib/stopgap_config.sh`,
`packages/figures/T4P/noise_perturb.png`, `docs/benchmarkIdeas.md` (§12 values updated),
`STATUS.md` (STOPGAP UNBLOCKED + actual stability numbers)

## Where I stopped
All T4P evaluation framework work complete. STOPGAP compiled locally. Changes staged, not committed.

## Next step
1. Run FM_hard on all 10 packages (k=3, `diff_mask_hard.mrc`, start PEET/DISCA/Dynamo)
2. Run STOPGAP on FM_easy locally (first test of local STOPGAP pipeline)
