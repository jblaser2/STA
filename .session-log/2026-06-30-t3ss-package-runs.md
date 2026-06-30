# Session Log — 2026-06-30: T3SS Package Runs Complete

## What was done

Ran all 10 benchmark classification packages on the T3SS injectisome synthetic dataset
(415 particles: 215 class_B / 120 class_C / 80 junk; 48³, 13.33 Å/px, EMD-8544).

### Classification results (ARI on signal particles B vs C only)

| Package | k=2 ARI | k=3 ARI | Notes |
|---------|---------|---------|-------|
| DISCA   | 0.720   | 0.812   | CNN; immune to registration wall |
| PEET    | 0.069   | 0.083   | pc1_10; best PCA method |
| STOPGAP | 0.020   | 0.025   | compiled binary eigenfac k-means |
| PyTom   | 0.005   | 0.009   | FRM + cylinder mask |
| OPUS-TOMO | −0.013 | 0.041 | VAE |
| ProTomo | −0.032  | N/A     | SVD+HAC k=2 only |
| Dynamo  | 0.000   | 0.000   | dpkpca collapsed |
| EMAN2   | N/A     | 0.000   | k=3 only |
| TomoFlow | 0.000  | 0.000   | OF collapsed at 24³ |
| RELION  | 0.000   | 0.014   | soft-EM collapse |

### Key finding

**Registration wall confirmed on T3SS.** All PCA/OF-based methods collapse (ARI ≈ 0) because
GT-pose synthetic particles mis-register WBP reconstructions, collapsing the discriminative PCA
axes. Only DISCA (CNN operating directly on raw voxel patterns) escapes. This is the same wall
diagnosed on FM_easy — now generalized to a structurally distinct complex (T3SS injectisome
vs. flagellar motor).

### Fixes encountered

- **STOPGAP:** bash wrapper (`stopgap_pca_parser.sh`) uses incompatible new API (`scoring_fcn`,
  `data_type awpd`) but compiled binary uses old API — bypassed wrapper, called binary directly.
  MPI requires explicit path `/usr/lib64/openmpi/bin/mpiexec`. Timing error on ccmat is benign
  (eigenfac_1.csv still produced correctly).
- **TomoFlow:** `--downsample 2` makes volumes 24³ but mask stays 48³ → shape mismatch.
  Fixed by pre-downsampling mask with scipy.ndimage.zoom(0.5) before passing to tomoflow_run.py.
- **RELION:** Soft-EM collapses (all 415 → 1 class) at both K=2 and K=3. Consistent with
  FM_easy / T4P behavior. ARI = 0.000 / 0.014.

## Files created/modified

- `packages/STOPGAP/T3SS/scripts/run_stopgap_t3ss.sh` — complete rewrite using compiled binary
- `packages/tomoflow/T3SS/scripts/run_t3ss_tomoflow.sh` — added mask downsampling step
- `packages/relion/T3SS/scripts/setup_t3ss_relion.py` — builds all RELION T3SS inputs
- `packages/relion/T3SS/scripts/run_t3ss_relion.sh` — runs K=2 and K=3 with scoring
- `outputs/T3SS/*/` — prediction CSVs for all 10 packages (committed, small CSVs only)
- `STATUS.md` — T3SS section fully updated with results table
- `packages/README.md` — T3SS section added with results table

## What's next

Per STATUS.md: **Run FM_hard on all 10 packages** (k=3, `diff_mask_hard.mrc`).
Start with PEET / DISCA / Dynamo as leaders.
Input: `~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/` + `labels.csv`.
