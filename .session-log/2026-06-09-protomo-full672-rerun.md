# 2026-06-09 — ProTomo Full-672 Rerun

## Goal
Investigate why the ProTomo T4P figure only used ~234 particles, document the root cause, and
rerun on all 672 particles so the result is benchmark-comparable.

## What Happened

**Root cause diagnosis:**
Two independent bugs conspired to limit ProTomo to 234 particles:
1. **`MRAAREA=0.8` overlap filter:** ProTomo checks whether each particle's aligned position has
   ≥80% box overlap. 438/672 T4P particles (65%) were picked near the z-boundaries of their
   source tomograms, leaving one side of the 80³ box zero-padded. ProTomo marked these as
   "overlap < 0.8" and excluded them. The initial run filtered them out before building
   `dataset_filtered.i3i` (234 particles).
2. **Broken symlinks from June 6 repo reorg:** The reorg moved particle MRCs from
   `STA/subtomos_mrc/` → `STA/data/T4P_subtomos/`. The symlinks in `protomo/prepare/stacks/`
   still pointed to the old path. `dataset.i3i` (full 672) was broken; `dataset_filtered.i3i`
   also broken but the rerun would have failed anyway.

**Fix:**
- Rebuilt all 672 symlinks: `prepare/stacks/` → `/home/jblaser2/Research/STA/data/T4P_subtomos/`
- Rebuilt `dataset.i3i` and `dataset_filtered.i3i` via `tomoprepare -log dataset.prep`
- Set `MRAAREA=0.0` in `param-template.sh` and `cycle-000/param.sh`
- Kept `MRAPKR="0 0 0"` (no translation search, particles prealigned) and
  `MSAIMGSIZE="32 32 32"` (SVD on central 32³ cube only — edge zero-padding doesn't affect it)

**Pipeline execution (from `~/Research/protomo/process/`):**
Steps hit along the way:
- `subvolglobalaverage.sh` requires a cycle number arg (use `subvolglobalaverage.sh 0`)
- `subvolhac.sh` fails if `t4p-000-class.i3i` already exists from a partial run (delete it first)
- `set -e` exits the script when `tomoprocess` logs "resampled area/volume < 0.8" warnings and
  exits non-zero, even though the computation succeeded — split into separate resume/finish scripts

**Result:**
- All 672 particles processed
- Split: **352 / 194 / 126 junk** (18.8% junk — same fraction as 234-particle run: 18.4%)
- Inter-class CC: **0.921** — identical to initial run
- Conclusion: edge-padded particles do not affect classification; result unchanged

## Files Changed

**Repo (committed ee4300e, pushed):**
- `packages/protomo/README.md` — detailed limitation note, updated results table + key findings
- `packages/protomo/T4P/results/class_averages_slices.png` — new figure (all 672)
- `packages/protomo/T4P/results/clustering_scatter.png` — new figure (all 672)
- `packages/README.md` — ProTomo row updated to 352/194/126 junk (all 672)
- `STATUS.md` — matrix row updated + ProTomo rerun bullet added

**Local only (not committed — `~/Research/protomo/`):**
- `prepare/stacks/` — symlinks rebuilt pointing to `data/T4P_subtomos/`
- `prepare/dataset.i3i` — rebuilt
- `prepare/dataset_filtered.i3i` — rebuilt
- `process/param-template.sh` — MRAAREA changed to 0.0
- `process/run_full672.sh` — new pipeline script
- `process/resume_full672.sh` — resume from step 2
- `process/finish_full672.sh` — run SVD+HAC+classavg only
- `process/cycle-000/` — full-672 classification results
- `process/cycle-000-filtered-backup/` — backup of original 234-particle run
- `process/visualize.py` — N_PARTICLES updated to 672

## Where I Stopped
All committed and pushed (ee4300e). ProTomo T4P result is now benchmark-comparable (all 672).

## Next Step
RELION GT-seeded k=2 on motor_switch 5 Å/px dataset (see STATUS.md MOTOR_SWITCH bullet).
Alternatively: EMAN2 motor_easy (still pending per last session log).
