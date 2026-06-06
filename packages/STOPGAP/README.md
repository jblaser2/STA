# STOPGAP

**Algorithm:** Subtomogram alignment + PCA + k-means clustering (MATLAB MCR compiled binaries)  
**Environment:** MATLAB R2023b MCR (compiled binaries); `stopgap` conda env for post-processing  
**Status:** 🟡 In progress — owned by Eben; full pipeline committed, not yet run on T4P

---

## Results

### T4P Real Dataset

Not yet run.

### Synthetic — motor_easy

Not yet run.

---

## Key Findings (Pipeline Design)

- Full source (`src/`, `sg_toolbox/`) and pipeline scripts committed to this directory.
- A 6-iteration alignment schedule has been designed: 3 blocks × 2 iterations each with
  stochastic hill-climb (SHC), coarse cone sampling, and per-block φ narrowing.
- A crash sentinel (`run_watcher_guarded`) was designed for `run_pipeline.slurm` but not yet
  added — adding it is the next step before running.
- Four source-level edits are already in-place in `src/`: `calculate_flcf.m`,
  `flcf_subtomo_scoring_function.m`, `check_crashes.m` (single-crash abort); plus two
  `exec/` file patches (`stopgap_config_slurm.sh`, `stopgap_parser.sh`).
- Compiled R2023b MCR binaries are excluded from git (gitignored at `exec/lib*/`); they must
  be recompiled on the target machine using `recompile_stopgap.slurm`.

---

## Next Steps

1. Add crash guard (`run_watcher_guarded`) to `run_pipeline.slurm`.
2. Run `build_inputs.m` to create the STOPGAP input files from T4P subtomograms.
3. Execute `run_pipeline.slurm` (direct `bash`, not `sbatch` — this machine has no SLURM).

---

## Files

| Path | Description |
|------|-------------|
| `packages/STOPGAP/src/` | C++ source tree (11 subdirectories) |
| `packages/STOPGAP/sg_toolbox/` | MATLAB toolbox (8 subdirectories) |
| `packages/STOPGAP/scripts/` | Helper MATLAB scripts (build_inputs.m, build_masks_ref.m, etc.) |
| `packages/STOPGAP/exec/` | Compiled MCR binaries (gitignored) + shell scripts |
| `packages/STOPGAP/run_pipeline.slurm` | Main pipeline script (adapt for direct bash) |
| `packages/STOPGAP/resume_pca.slurm` | PCA resume script |
| `packages/STOPGAP/recompile_stopgap.slurm` | Recompile script (R2023b MCR) |
| `packages/STOPGAP/research.md` | Codebase reference (590 lines) |
| `packages/STOPGAP/setup_notes.md` | Deep technical guide: shared files, data structures, pipeline modules (1286 lines) |
| `packages/STOPGAP/stopgap_0.7.5_manual.pdf` | Official user manual |
