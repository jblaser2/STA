# Session Log — 2026-06-09 — EMAN2 Canonical T4P k=3

## Goal
Run the canonical EMAN2 T4P k=3 classification (2 signal + 1 junk) on Josh's account.

## What happened

**Benchmark reorganization push:**
- Resolved merge conflict with Eben's EMAN2 T4P k=2 result (19b3f04) and ProTomo full-672 rerun.
- Rebased and pushed; STATUS.md conflict resolved (both "Last updated" lines merged).
- .gitignore conflict: kept both Eben's `.eman2settings.json` entry and `trash/`.
- `packages/eman2/T4P/scripts/make_identity_parms.py` placed in correct reorganized path.

**EMAN2 installation on Josh's account:**
- Package name on anaconda.org is `eman-dev` (not `eman2`) on the `cryoem` channel.
- Installed: `mamba create -n eman2 -c cryoem -c conda-forge "eman-dev==2.99.72=nogui*"`
- Env lives at `~/miniforge3/envs/eman2`. Verified with `e2spt_pcasplit.py --help`.
- Workspace created at `~/Research/eman2_project/` (local, gitignored).

**Canonical k=3 run:**
- Updated `run_pipeline.sh`: NCLASS=3, NONINTERACTIVE=1, paths changed to Josh's account.
- Updated `make_project.py`: PARTICLES_DIR → `~/Research/STA/data/T4P_subtomos`.
- `patch_scripts.py` worked without path changes (uses `shutil.which`).
- Run completed in ~5 min. Split: **270 / 317 / 85** (class 3 = junk, FSC=152Å vs 82Å).

**Mask re-run:**
- Converted `cylindrical_mask_v2.mrc` → `cylindrical_mask_v2.hdf` via `e2proc3d.py`.
- Re-ran pcasplit with cyl v2 mask → identical split (85/270/317, just relabeled). Mask makes no difference.
- Confirmed mask axis convention is consistent (MRC [Z,Y,X] convention matches between mask and particles). Y density profile is flat (pilus runs along Y), mask covers Y=15–40 (lower half from center) as intended.

**Simple averages:**
- Computed straight arithmetic means per class using `mrcfile` (bypassing EMAN2 averaging pipeline).
- User confirmed density/orientation "looks right."
- EMAN2 `threed_XX.hdf` averages look strange because: (1) WBP density inversion (protein=dark), (2) missing-wedge artifacts from `e2spt_average.py`, (3) classes aren't structural so they're blurry subsets.

**Figure update:**
- Added particle count `(n=XXX)` to row labels in `class_averages.png`.
- Fixed filter in `plot_class_averages.py` to exclude `_even_unmasked.hdf` / `_odd_unmasked.hdf`.

**Other:**
- ProTomo README: committed Eben's edge-filter limitation documentation + full-672 rerun result (352/194/126).
- .gitignore: added `trash/` (deduplicated) and `.eman2log.txt`.

## Files changed
- `packages/eman2/T4P/results/eman2_T4P_k3_none_r01_assignments.csv` — per-particle class assignments
- `packages/eman2/T4P/results/eman2_T4P_k3_none_r01_classavg.png` — class avg figure with n= counts
- `packages/eman2/T4P/scripts/run_pipeline.sh` — NCLASS=3, NONINTERACTIVE=1, Josh paths
- `packages/eman2/T4P/scripts/plot_class_averages.py` — added n= counts, fixed unmasked filter
- `packages/eman2/README.md` — updated T4P row to ✅, documented cyl mask re-run
- `packages/README.md` — EMAN2 row ✅, Package Descriptions updated
- `packages/protomo/README.md` — Eben's full-672 rerun documented
- `.gitignore` — trash/ (deduped), .eman2log.txt
- `STATUS.md` — updated

## Where I stopped
All committed and pushed through `56aaf07`. Workspace at `~/Research/eman2_project/` has:
- `sptcls_00/` — no-mask k=3 run (canonical)
- `sptcls_01/` — cyl v2 mask k=3 run (identical result)
- `simple_avgs/` — arithmetic mean averages, no-mask classes
- `simple_avgs_cylv2/` — arithmetic mean averages, cyl-mask classes

## Next step
- EMAN2 T4P is done (No convergence). 
- Remaining T4P canonical runs needed: Dynamo k=3+junk, PyTom k=3+junk, OPUS-TOMO k=3+junk, DISCA k=3, TomoFlow k=3, STOPGAP.
- motor_switch 5 Å/px: set up RELION GT-seeded k=2 baseline.
