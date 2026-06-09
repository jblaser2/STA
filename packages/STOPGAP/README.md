# STOPGAP

**Algorithm:** Subtomogram alignment + PCA + k-means clustering (MATLAB MCR compiled binaries)  
**Environment:** MATLAB R2023b MCR (compiled binaries); `stopgap` conda env for post-processing  
**Status:** 🟡 In progress — owned by Eben; T4P run complete (k=2/3/4); FM/T4SS not yet run

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=2/3/4 / k=2 | cc + align (`results/masks/`) | — (vs PEET GT TBD) | **70 / 602** (k=2, MRA) | PCA+k-means and independent MRA (6 iter). PCA splits 336/336, MRA collapses to one dominant class, cross-method ARI≈0 — **does not cleanly recover the two phases** (pending class-avg comparison to PEET reference) |
| **FM_easy** | ⬜ | k=3 / k=3 | — | — | — | Not yet run |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

**Class splits (all 672 particles) — two independent classifiers:**

| k | PCA + k-means (`allmotl_pca_k*_1`) | MRA final (`allmotl_mra_k*_6`) |
|---|------------------------------------|--------------------------------|
| 2 | **336 / 336** | **70 / 602** |
| 3 | 251 / 274 / 147 | 24 / 391 / 257 |
| 4 | 194 / 121 / 189 / 168 | 22 / 317 / 23 / 310 |

The two methods **disagree at chance level** — cross-method ARI = 0.001 / 0.003 / 0.003 for
k=2/3/4 (`results/meta/pca_vs_mra_agreement.csv`). PCA k-means slices a *continuous* PC axis into
near-equal groups (exactly 336/336 at k=2 — no gap in the embedding), while MRA collapses to one
dominant class (602/672 at k=2). Neither yields a reproducible discrete partition, so STOPGAP —
like RELION / DISCA / TomoFlow on T4P — **does not cleanly recover the two pili phases**; most
likely per-particle SNR too low for CC-based discrimination at 672 particles / 13.3 Å px. Full
breakdown in `research.md` §15.

---

## Key Findings (Pipeline Design)

- Full source (`src/`, `sg_toolbox/`) and pipeline scripts committed to `T4P/scripts/`.
- **Fail-loud orchestration** in `run_pipeline.slurm`: a `stage()` wrapper checks each
  stage's exit code, greps STOPGAP's real fatal markers (excluding benign `Warning: ACHTUNG`
  lines), checks for `crash_*` files, and `assert_exists` on key outputs.
- **Three genuine STOPGAP source bugs** on the PCA code path fixed (verified in-tree):
  `src/stopgap/stopgap.m`, `src/pca/exec/stopgap_pca.m`, `src/pca/exec/pca_prerotate_volumes.m`
  — research.md §11 bugs 6–8. All other fixes are config-level (no source touched).
  **Any `src/` edit requires a recompile** (`recompile_stopgap.slurm`).
- Compiled R2023b MCR binaries are gitignored (`exec/lib/`); a fresh clone must run
  `recompile_stopgap.slurm` once before the pipeline will launch.

---

## Next Steps

1. Compare final k=2 class averages (`results/ref/ref_mra_k2_6_{1,2}.mrc`) against the PEET
   reference (`ring_complete` / `ring_altered`) to confirm whether the 70-particle minority class
   is a real phase or junk, and compute ARI vs PEET soft GT.
2. After T4P: run FM_easy (k=3, no junk).

---

## T4P Results (`T4P/results/`)

Saved from the `Pili_class` run (8.4 GB working dir; `rvol/` + `temp/` excluded). Core set only:

| Subdir | Contents |
|--------|----------|
| `lists/` | Per-particle class assignments (MOTLs): final MRA `allmotl_mra_k{2,3,4}_6.star`, PCA k-means `allmotl_pca_k*_1.star`, input `allmotl_1.star`, `wedgelist.star`, `filter_list.star` |
| `ref/` | Final class volumes `ref_mra_k{2,3,4}_6_*.mrc`, PCA-stage class averages `class_pca_k*_1_*.mrc`, starting `ref_1.mrc` |
| `meta/` | `class_pca_pca_scatter.png`, class-avg montages, co-occurrence PNGs, `pca_vs_mra_agreement.csv` |
| `pca/` | `eigenfac_1.csv` (per-particle PCA coords), `eigenval_1.csv` |
| `params/` | Run configs: `pca_param.star`, `mra_k{2,3,4}.star`, `mraseed_param.star`, `avg_pca_param.star` |
| `masks/` | `mask_align.mrc`, `mask_cc.mrc` |
| `fsc/` | Per-class FSC curves (PDF) for all iterations |

`.mrc`/`.star` are gitignored (local-only) — this includes `lists/`, `ref/`, `masks/`, and
`params/`. The committed record is the PNG/PDF/CSV figures, `pca/*.csv`, `fsc/*.pdf`, and
`pca_settings.txt`. Half-maps (`ref_mra_k2_{A,B}_6_*`) were **not** copied — recompute from the
working dir if gold-standard FSC is needed.

---

## Files

| Path | Description |
|------|-------------|
| `src/` | MATLAB source tree compiled into the MCR binaries (11 subdirectories); 3 patched files (research.md §11) |
| `sg_toolbox/` | MATLAB `sg_*` helper toolbox (8 subdirectories) |
| `T4P/scripts/` | Pipeline: `run_pipeline.slurm`, `resume_pca.slurm`, `build_*.m`, `sg_pca_kmeans_cluster_fn.m`, `visualize_results.m`, `compare_methods.m` (self-contained; `SG` set to this repo) |
| `T4P/results/` | Committed outputs from the T4P run (see table above) |
| `exec/` | `bin/` wrappers + `lib/` config & compiled MCR binaries (binaries gitignored) |
| `recompile_stopgap.slurm` | Recompile the 4 binaries for R2023b → `exec/lib/` (run once per machine) |
| `research.md` | **Single replication reference**: codebase map (§1–9) + our pipeline (§10–14) + completed-run results (§15) |
| `setup_notes.md` | Deep technical guide: shared files, data structures, pipeline modules |
| `stopgap_0.7.5_manual.pdf` / `stopgap_0.7.5.md` / `changes.txt` | Upstream manual + license + changelog |
