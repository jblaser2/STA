# 2026-06-05 — Commit STOPGAP source and pipeline scripts to repo

## Goal
Stage and commit Eben's STOPGAP work (source, scripts, slurm jobs, research notes) so the repo
reflects the current state on Eben's machine.

## What happened

### Problem: nested git repo
`STOPGAP/` was copied from the original STOPGAP GitHub repo and still contained a nested `.git/`.
Git would have treated it as a submodule rather than regular files, blocking `git add`.
Resolution: Eben removed `STOPGAP/.git/` manually (`! rm -rf STOPGAP/.git/`).

### .gitignore updated
Added to root `.gitignore`:
- `*.m~`, `*.asv`, `*.bak.m`, `*.bak2.m`, `*.m.bak` — MATLAB autosave/backup files
- `STOPGAP/exec/lib*/sg_toolbox`, `.../stopgap`, `.../stopgap_parser`, `.../stopgap_watcher` —
  compiled ELF binaries (platform-specific R2023b MCR executables, cannot run on another machine)

`.codegraph/` was already covered by the existing `.codegraph` pattern.

### Committed (42122b0)
566 files, 40,327 insertions:
- `STOPGAP/scripts/` — 8 pipeline/analysis scripts (build_inputs.m, build_masks_ref.m, etc.)
- `STOPGAP/src/` — full STOPGAP source (incl. edited `check_crashes.m`)
- `STOPGAP/sg_toolbox/` — full toolbox source
- `STOPGAP/exec/bash/`, `exec/bin/`, `exec/lib/` — shell scripts + config (not binaries)
- `STOPGAP/exec/lib_r2023b/` — text metadata only (readme, requiredMCRProducts.txt, etc.)
- `STOPGAP/run_pipeline.slurm`, `resume_pca.slurm`, `recompile_stopgap.slurm`
- `STOPGAP/research.md`, `stopgap_0.7.5.md`, `changes.txt`, `stopgap_0.7.5_manual.pdf`
- `.gitignore` (updated)

## Files changed
- `.gitignore` — new MATLAB and STOPGAP binary patterns
- `STOPGAP/` — entire directory added (566 files)
- `STATUS.md` — STOPGAP row updated; last-updated date bumped

## Where I stopped
Commit done. No classifications run this session — STOPGAP is still at ⬜ for data-prep and runs.

## Next step
1. Add `run_watcher_guarded` crash guard to `run_pipeline.slurm` (described in research.md §7).
2. Run `build_inputs.m` → `sbatch run_pipeline.slurm` to execute first classification.
