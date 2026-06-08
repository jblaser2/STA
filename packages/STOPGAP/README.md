# STOPGAP

**Algorithm:** Subtomogram alignment + PCA + k-means clustering (MATLAB MCR compiled binaries)  
**Environment:** MATLAB R2023b MCR (compiled binaries); `stopgap` conda env for post-processing  
**Status:** 🟡 In progress — owned by Eben; full pipeline committed, not yet run

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ⬜ | k=3 / k=2 | cyl v2 | — | — | Pipeline committed; crash guard + build_inputs.m needed before run |
| **FM_easy** | ⬜ | k=3 / k=3 | — | — | — | Not yet run |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

---

## Key Findings (Pipeline Design)

- Full source (`src/`, `sg_toolbox/`) and pipeline scripts committed to `T4P/scripts/`.
- 6-iteration alignment schedule designed: 3 blocks × 2 iterations with stochastic hill-climb
  (SHC), coarse cone sampling, and per-block φ narrowing.
- Crash sentinel (`run_watcher_guarded`) designed for `run_pipeline.slurm` but not yet added.
- Four source-level edits in-place in `src/`: `calculate_flcf.m`,
  `flcf_subtomo_scoring_function.m`, `check_crashes.m`; plus two `exec/` patches.
- Compiled R2023b MCR binaries are gitignored (`exec/lib*/`); must recompile on target machine.

---

## Next Steps

1. Add crash guard (`run_watcher_guarded`) to `T4P/scripts/run_pipeline.slurm`.
2. Run `T4P/scripts/build_inputs.m` to create STOPGAP input files from T4P subtomograms.
3. Execute `run_pipeline.slurm` with direct `bash` (no SLURM scheduler on this machine).
4. After T4P: run FM_easy (k=3, no junk).

---

## Files

| Path | Description |
|------|-------------|
| `src/` | C++ source tree (11 subdirectories); patched files in `src/` |
| `sg_toolbox/` | MATLAB toolbox (8 subdirectories) |
| `T4P/scripts/` | Pipeline scripts: build_inputs.m, run_pipeline.slurm, resume_pca.slurm, etc. |
| `exec/` | Compiled MCR binaries (gitignored) + shell scripts |
| `recompile_stopgap.slurm` | Recompile script (R2023b MCR) |
| `research.md` | Codebase reference |
| `setup_notes.md` | Deep technical guide: shared files, data structures, pipeline modules |
| `stopgap_0.7.5_manual.pdf` | Official user manual |
