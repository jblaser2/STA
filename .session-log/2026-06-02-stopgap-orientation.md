# 2026-06-02: STOPGAP Orientation (Eben)

## Goal
Get oriented with the STOPGAP work — understand what scripts exist, what optimizations have been designed, and what still needs to be done before submitting the first classification job.

## What Happened
Read through all files in `stopgap/`:

**Scripts ready to use (`classificationScripts/`):**
- `createStopgapInputs.m` — sets up `subtomo_project/` (symlinks, motivelist, wedgelist, refs, masks)
- `subtomoParams.sh` — generates 6-iter alignment param file (3 blocks × 2 iters; shc + coarse cone + per-block phi narrowing)
- `runClassification.sh` — full SLURM pipeline (Phase 1: subtomo alignment, Phase 2: PCA, Phase 3: k-means)
- `runPostClassification.sh` — per-class averages + PCA scatter plots
- `compileStopgap.sh` — recompile only if needed; binaries already in `matlabr2023bCompiledBinaries/`

**Edited STOPGAP source files (`editedSTOPGAPfiles/`):**
- `calculate_flcf.m` — optional 5th arg `fmask_in` to skip `fftn(mask)` for spherical masks
- `flcf_subtomo_scoring_function.m` — sphere-mask detection at `'init'`; skips 2 `sg_rotate_vol` + 1 FFT per angle in `'score'`
- `stopgap_config_slurm.sh` — fixes `${LD_LIBRARY_PATH}` unbound-variable crash
- `stopgap_parser.sh` — sources `stopgap_config_slurm.sh` (the file that actually exists)

**Key gap identified:** `research.md` §7 documents a `run_watcher_guarded` bash function and a `check_crashes.m` edit that abort on the first worker crash (not all-cores-crash). These are designed but NOT yet in `runClassification.sh` — the script still calls `${watcher}` directly. Without this, a single crashed MPI worker leaves the job polling silently until 2-day wall-time expires.

**Known bugs already fixed (documented in research.md):**
- Halfset field must be `'A'`/`'B'` not `'h1'`/`'h2'` (corrupts motivelist STAR output)
- `rootdir` must end with trailing slash (parser re-read bug in blocks 2–3)
- `*_name` params must NOT include directory prefix (doubled path crash)
- Reference must be written as two halfset files `_A_1.mrc`/`_B_1.mrc`

## Files Changed
None — read-only orientation session. Pre-existing modified files in the working tree are Eben's prior work:
- `stopgap/classificationScripts/runClassification.sh` (staged: 9→6 iterations, FINAL_ITER=7)
- `stopgap/classificationScripts/subtomoParams.sh` (unstaged: shc + coarse + per-block phi)
- `stopgap/research.md` (unstaged: §performance-optimizations + §7 crash guard)
- `stopgap/editedSTOPGAPfiles/calculate_flcf.m` (new untracked)
- `stopgap/editedSTOPGAPfiles/flcf_subtomo_scoring_function.m` (new untracked)

## Where I Stopped
Orientation complete. Have a clear picture of what's ready and what's missing.

## Next Step
1. Add `run_watcher_guarded` crash sentinel to `runClassification.sh` (see research.md §7)
2. Copy edited STOPGAP source files into the STOPGAP source tree
3. `cd ~/nobackup/autodelete/stopgapClassification/subtomo_project && matlab -nodisplay -nosplash -r "addpath(genpath('/home/ejl62/summerResearch/STOPGAP/sg_toolbox')); addpath('/home/ejl62/summerResearch/STOPGAP'); createStopgapInputs; exit;"`
4. `bash /home/ejl62/summerResearch/STOPGAP/subtomoParams.sh`
5. `sbatch /home/ejl62/summerResearch/STOPGAP/runClassification.sh`
