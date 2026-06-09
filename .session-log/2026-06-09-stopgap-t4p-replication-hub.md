# 2026-06-09 — STOPGAP T4P: document completed run + consolidate replication hub

## Goal
Make `packages/STOPGAP/` a self-contained one-stop replication hub for the T4P
classification problem: ensure `research.md` is a comprehensive replication doc, bring
`README.md` up to date, and confirm nothing else needs copying in.

## What happened
- **Discovered the run is complete.** The full STOPGAP T4P pipeline ran end-to-end as
  SLURM job **12114811** (2026-06-05, ~58 min on 64 cores, clean exit, empty `.err`).
  Results already sit in `packages/STOPGAP/T4P/results/` (copied in an earlier session).
  Verified the committed class splits directly from the `.star` files:
  - PCA + k-means: k=2 **336/336**, k=3 251/274/147, k=4 194/121/189/168
  - MRA (6 iter, classify-only): k=2 **70/602**, k=3 24/391/257, k=4 22/317/23/310
  - Cross-method ARI ≈ 0.0012 / 0.0027 / 0.0034 (matches `meta/pca_vs_mra_agreement.csv`
    and the run log exactly). → STOPGAP does **not** cleanly recover the two pili phases
    (PCA slices a continuous PC axis 336/336; MRA collapses to one dominant class;
    methods disagree at chance). Same SNR-limited failure as RELION/DISCA/TomoFlow.
- **Critical hub fix:** the three SLURM scripts hard-coded `SG=/home/ejl62/…/STA/STOPGAP`
  (the *transient* dir) and added `$SG/scripts` to the MATLAB path, but the helpers now
  live in `T4P/scripts/`. As written the pipeline would not run from the persistent repo.
  Repointed `SG` → `…/packages/STOPGAP` and the matlab path → `$SG/T4P/scripts` in
  `run_pipeline.slurm`, `resume_pca.slurm`, `recompile_stopgap.slurm`.
- **recompile_stopgap.slurm:** renamed the misleading `lib_r2020b` backup → `lib_prev`
  (no R2020b binaries exist here; live binaries are R2023b). Removed a stale `LP_RAD=17`
  placeholder comment in run_pipeline.slurm (pipeline hardcodes `lp_rad 13.33`).
- **research.md rewritten for accuracy:** repo root → packages/STOPGAP; §1 now shows the
  full hub layout (T4P/scripts, T4P/results, exec/lib gitignored, FM_hard/T4SS); §8/§9
  exec-lib facts corrected; §10 helper paths → T4P/scripts; §11/§13/§14 "pending/
  unverified/timed-out" language replaced (run completed); **new §15 Results** with
  provenance (job 12114811), split + ARI tables, honest interpretation, committed-vs-
  gitignored output map, and remaining analysis steps.
- **README.md reconciled:** replaced MRA-only split line with a two-method PCA-vs-MRA
  table (fixed earlier wording that implied MRA was seeded from PCA — it's seeded from
  random classes); fixed the "source-level edits" bullet to the verified §11 trio
  (`stopgap.m`, `stopgap_pca.m`, `pca_prerotate_volumes.m` — confirmed in-tree), fixed
  `src/` "C++"→MATLAB, replaced stale crash-sentinel bullet with the real `stage()`
  fail-loud wrapper, refreshed the Files table.
- **Confirmed nothing else needs copying.** Diffed transient `/STA/STOPGAP` vs persistent
  `packages/STOPGAP`: only unique items in the transient dir are recompilable old binaries
  (gitignored), editor junk (`.asv`/`.bak`/`.m~`), and SLURM run logs. All source,
  toolbox, scripts, results, params, masks, figures, docs, and runnable R2023b binaries
  (in `exec/lib/`) are present. Caveat documented: binaries are gitignored, so a fresh
  clone must run `recompile_stopgap.slurm` once before launching.

## Files changed
- `packages/STOPGAP/research.md` — comprehensive rewrite (layout, paths, §15 results)
- `packages/STOPGAP/README.md` — results table, source-edit bullet, files table
- `packages/STOPGAP/T4P/scripts/run_pipeline.slurm` — SG + matlab path; stale comment
- `packages/STOPGAP/T4P/scripts/resume_pca.slurm` — SG + matlab path
- `packages/STOPGAP/recompile_stopgap.slurm` — SG path; lib_r2020b → lib_prev
- `STATUS.md` — Now/Next bullet, STOPGAP matrix row ✅, GT + completion bullets
- `packages/README.md` — STOPGAP T4P row ✅ + class-avg thumbnail; description row

## Where I stopped
All docs/scripts updated, staged. STOPGAP T4P is ✅ across STATUS.md, packages/README.md,
and packages/STOPGAP. No code/run executed this session — documentation + path consolidation only.

## Next step
**Analysis (not pipeline):** (1) visually compare `T4P/results/ref/ref_mra_k2_6_{1,2}.mrc`
and `class_pca_k2_1_{1,2}.mrc` against PEET `ring_complete`/`ring_altered` (is the
70-particle MRA minority real or junk? are tight-mask averages over-cropped?); (2) compute
ARI of STOPGAP labels vs PEET soft GT (`scripts/eval/`); (3) then run FM_hard / T4SS
(placeholders staged, pipeline reusable as-is).
