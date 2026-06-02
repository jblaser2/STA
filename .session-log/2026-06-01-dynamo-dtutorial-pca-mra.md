# 2026-06-01 — Dynamo dtutorial synthetic data: PCA walkthrough + MRA setup

## Goal
Run Dynamo's `dtutorial` synthetic subtomogram-classification dataset, work through the
command-line PCA classification walkthrough, compare how it behaves, then set up and launch a
Dynamo MRA (multireference alignment) project on it.

## What happened
- **Data generated:** `dtutorial ttest128 -M 64 -N 64 -linear_tags 1 -tight 1` →
  `dynamo/dynamo_outputs/ttest128_tutorial/ttest128/`: 128 particles, **40³ box** (NOT 64³ — the
  256512-byte .em = 40³×4 + 512 header; the "128" is M+N particle count), two gross size-variant
  classes (templates thermo1/thermo2), c8 symmetry, noise 0.1, ±60° missing wedge. Ground-truth
  class = **col 22 of `real.tbl`** (1–64 → class 1, 65–128 → class 2).
- **PCA walkthrough (`dpkpca`)** ran headless on CPU. Blocker hit + fixed: `dynamo_mollify.m` crashed
  on `wb.unfold()` because this MATLAB lacked Image Processing Toolbox and the fallback's error line
  `o.e(...)` (undefined `o`) crashed instead of using the FFT path → patched that one line.
  - **`real.tbl` (perfect poses):** k-means k=2 vs GT = **acc 1.000 / ARI 1.000**; clean 2×2
    CC-matrix blocks; classes split on PC2.
  - **`initial.tbl` stress test:** that table is **all-zero angles + all-zero shifts** (particles
    fully unaligned, mean **118.7° / 4.9 vox** off truth). PCA collapses to **acc 0.578 / ARI 0.017
    (chance)**. ⇒ Dynamo PCA is a *post-alignment* heterogeneity tool; classification is entirely
    contingent on prior alignment quality. The walkthrough's `prealign` (single-ref to consensus)
    does NOT rescue unaligned particles.
- **Mid-session:** Josh installed Image Processing Toolbox (confirmed `imgaussfilt3` now present).
- **MRA project set up** (`mra_ttest128`, two-stage, user chose this over direct/both): rounds 1–3
  `nref=1` full-sphere→refine alignment; rounds 4–6 `nref=2` embedded MRA + class swapping.
  Validated with `dvcheck`/`dvunfold` (fixed along the way: `dim=40` per-round, `destination` must be
  a valid value, round params need explicit `_rN` suffixes).
- **Run BLOCKED:** Dynamo's in-MATLAB execution (`dpkmulticore.run`) always calls `parpool`/`parfor`,
  so it requires the **Parallel Computing Toolbox**. PCT is *licensed* here but *not installed* — even
  `destination='matlab',cores=1,mwa=1` dies on `Undefined function 'parpool'`. Same pattern as the IPT
  install.

## Files changed
- Scripts (new) in `dynamo/dynamo_outputs/ttest128_tutorial/`: `run_pca.m`, `run_pca_initial.m`,
  `pose_err.m`, `setup_mra.m`, `run_mra.m`.
- **Patched (local Dynamo repo, NOT STA):** `~/Research/dynamo/matlab/src/dynamo_mollify.m` (line ~84,
  broken `o.e` error handler → `disp` + FFT fallback).
- Memory (STA project memory): `dynamo-mollify-ipt-bug`, `dynamo-pca-walkthrough-run`,
  `dynamo-mra-project-scripting`, `dynamo-execution-needs-pct` (+ MEMORY.md index).
- Large outputs (.em/.tbl/.mat/.png, `mra_ttest128/` project) are local-only, not committed.

## Where I stopped
MRA project `mra_ttest128` fully set up + unfolded, waiting to run. Run cannot proceed until PCT is
installed. `run_mra.m` is already configured (`destination='matlab_parfor'`) to run as-is once PCT is in.

## Next step
1. Install **Parallel Computing Toolbox** (license already present — same route as IPT).
2. `matlab -batch run_mra` → then evaluate round-6 class labels (ARI vs GT col 22) and recovered
   poses (angular error vs `real.tbl`) to see how close Dynamo's cold-start align+classify gets to the
   ARI=1.0 ceiling. Compare against the PCA-on-`real.tbl` baseline.

---

## 2026-06-02 update — PCT installed, MRA run completed + evaluated

- **PCT installed** by Josh → `run_mra.m` (`destination='matlab_parfor'`, 8 cores) ran the full
  project: **6 rounds / 18 iterations, exit 0, `ok:1`** (`run_mra.log`). Parpool of 8 workers; round 1
  (full-sphere) was the heavy one, later rounds fast.
- **Evaluation** (`eval_mra.m` → `eval_mra.log`, `pca_scatter_mra.png`):
  - **Embedded-MRA classification COLLAPSED.** Only `refined_table_ref_001` ever existed across ites
    10–18 (the `nref=2` rounds); final reference field **col 34 = all 1s** for all 128 particles; log
    said "1 references remain". The clean "64/64" in **col 22 is a trap**: `initial.tbl` already carries
    GT labels in col 22 and the MRA table is identical to it row-for-row (0 differ) — passive carryover,
    NOT a recovered split. Dynamo's class-swapping never seeded/held a 2nd reference here.
  - **Cold-start alignment partly worked** (vs `real.tbl`, c8-folded angles): SHIFT mean 4.93→**2.06**
    vox (med 4.76→1.49); ANGLE within 20° **9/128 → 63/128** (median 87°→22°). Bimodal — about half
    the particles lock onto truth, half stay ~90°+ off (c8 local minima / flips).
  - **PCA on the MRA-aligned table → acc 0.969 / ARI 0.878** (k-means k=2, 5 comps), near the
    `real.tbl` ceiling of 1.000 and far above `initial.tbl` 0.017.
- **Takeaway:** on this synthetic set, Dynamo's usable heterogeneity signal comes from
  **alignment quality + PCA**, not from the embedded MRA class-swapping (which collapsed). Spectrum of
  PCA k=2 ARI vs GT: `initial` 0.017 | **cold-start MRA 0.878** | `real` 1.000.
- **Files added:** `eval_mra.m`, `eval_mra.log`, `pca_scatter_mra.png`, `mra_aligned.tbl`
  (table + logs local-only; only the `.m` commits). `mra_ttest128/` project is local-only.
- **Side note:** `dwrite(Tmra,'mra_aligned.tbl')` printed `dynamo_write` warnings but wrote a usable
  table (PCA indexed all 128 particles fine).

### Where I stopped (final)
Run complete, evaluated, results recorded. Side-track is **closed** — no Dynamo follow-up pending.
