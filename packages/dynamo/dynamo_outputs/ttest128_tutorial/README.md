# Dynamo `dtutorial` — synthetic subtomogram classification (methodology side-track)

A self-contained study of how **Dynamo** classifies a small synthetic subtomogram set, run
headlessly (no GUI) on CPU. The point was *methodological*: understand where Dynamo's
heterogeneity-classification signal actually comes from (alignment vs. its PCA tool vs. its
multireference class-swapping) before trusting it as the reference method on the real T4P data.

This is **not** part of the main T4P benchmark — it's the Dynamo `dtutorial` toy dataset, used to
calibrate intuition. Full narrative: `STA/.session-log/2026-06-01-dynamo-dtutorial-pca-mra.md`.

## The dataset

Generated with:

```
dtutorial ttest128 -M 64 -N 64 -linear_tags 1 -tight 1
```

- **128 particles, 40³ box** (the "128" is M+N particle count, *not* box size).
- **2 gross size-variant classes** (templates `thermo1` / `thermo2`), 64 particles each.
- c8 symmetry, additive noise 0.1, ±60° simulated missing wedge.
- **Ground-truth class label = column 22 of `real.tbl`** (tags 1–64 → class 1, 65–128 → class 2).
- Two starting tables ship with the tutorial: `real.tbl` (perfect poses) and `initial.tbl`
  (identity poses = particles effectively unaligned; it also *carries the GT labels in col 22*).

The raw `ttest128/` data, the `*.PCA/` workspaces and the `mra_ttest128/` project are **regenerable**
from the scripts here and are git-ignored (hundreds of MB). What's committed are the scripts plus the
small result artifacts below.

## Scripts (the experiments)

| Script | What it does |
|---|---|
| `run_pca.m` | Dynamo command-line **PCA classification** walkthrough on `real.tbl` (perfect poses). Builds CC-matrix → eigentable → eigenvolumes → t-SNE, then k-means k=2 vs GT. |
| `run_pca_initial.m` | Same PCA pipeline on `initial.tbl` (unaligned) — stress test. Includes the `score2` accuracy/ARI helper. |
| `pose_err.m` | Quantifies `initial.tbl` vs `real.tbl` pose offset (shift + Euler angle error). |
| `setup_mra.m` | Builds the two-stage cold-start **MRA** project `mra_ttest128`: rounds 1–3 `nref=1` align-to-consensus, rounds 4–6 `nref=2 mra=1` classify. |
| `run_mra.m` | Runs the MRA project (`destination='matlab_parfor'`; needs the Parallel Computing Toolbox). |
| `eval_mra.m` | Evaluates the finished MRA run: c8-folded angular + shift error vs `real.tbl`, Dynamo's own class labels (col 34), and **PCA re-classification on the MRA-aligned table**. |

## Results

**1. Dynamo PCA is a *post-alignment* tool.** Classification quality is entirely contingent on prior
alignment:

| Input poses | k-means k=2 accuracy | ARI vs GT |
|---|---|---|
| `real.tbl` (perfect) | 1.000 | **1.000** |
| `initial.tbl` (unaligned) | 0.578 | **0.017** (chance) |

**2. Cold-start MRA (`mra_ttest128`, 6 rounds / 18 iterations, started from `initial.tbl`).**

- Its **own embedded 2-class assignment COLLAPSED**: across every `nref=2` iteration only
  `refined_table_ref_001` ever existed and the final reference field (**col 34**) is all `1`s.
  ⚠️ The clean 64/64 split in **col 22 is a trap** — that's just the GT labels carried over unchanged
  from `initial.tbl` (identical row-for-row), *not* a recovered classification. Always read col 34.
- But the **alignment** partly worked (vs `real.tbl`, c8-folded):

  | metric | `initial.tbl` | MRA cold-start |
  |---|---|---|
  | shift error (mean / med, vox) | 4.93 / 4.76 | **2.06 / 1.49** |
  | angular error (median, deg) | 87 | **22** |
  | particles within 20° of truth | 9 / 128 | **63 / 128** |

  (bimodal: ~half the particles lock onto truth, ~half stay ~90°+ off in c8 local minima / flips.)

- **PCA on the MRA-aligned poses → accuracy 0.969 / ARI 0.878** — near the perfect-pose ceiling.

**Spectrum (PCA k=2 ARI vs GT):** `initial` 0.017  →  **cold-start MRA 0.878**  →  `real` 1.000.

**Takeaway:** on this set, Dynamo's usable heterogeneity signal comes from **alignment quality + PCA**,
not from its multireference class-swapping (which collapsed). A cold start gets most of the way to the
perfect-alignment ceiling.

## Committed output artifacts

- Figures: `ccmatrix.png`, `ccmatrix_initial.png`, `pca_scatter_gt.png`, `pca_scatter_initial.png`,
  `pca_scatter_mra.png`, `eigenvolumes_montage.png`.
- Numerical: `ground_truth_labels.txt`, `kmeans_labels.txt`, `ccmatrix.txt`, `eigencomponents.txt`,
  `mra_aligned.tbl` (the recovered cold-start poses, Dynamo table format).
- Run logs: `dtutorial_run.log`, `run_pca.log`, `run_pca_initial.log`, `setup_mra.log`,
  `run_mra.log`, `eval_mra.log`.

## Reproduce

From this directory, with Dynamo + MATLAB (Image Processing **and** Parallel Computing Toolboxes):

```
matlab -batch run_pca          # perfect-pose PCA  -> ARI 1.000
matlab -batch run_pca_initial  # unaligned PCA     -> ARI 0.017
matlab -batch setup_mra        # build mra_ttest128
matlab -batch run_mra          # run it (6 rounds / 18 iters)
matlab -batch eval_mra         # alignment + PCA-on-MRA evaluation
```

(One local Dynamo patch was needed for the no-Image-Processing-Toolbox path; see the session-log and
the `dynamo-mollify-ipt-bug` project memory.)
