# 2026-06-04 — Class B expansion (run_07/08) + mask sizing visualization

## Goal
- Add 2 more class B simulation runs to balance the synthetic dataset (B was underrepresented at 211 vs A=246)
- Visualize the global GT-aligned average with a cylindrical mask overlay to size the mask for PEET/Dynamo runs

## What happened

### Mask visualization
- Wrote `~/Research/synthetic_sta/motor_easy/visualize_avg_with_mask.py`
- Loads `outputs/relion_motor_easy/initial_ref.mrc` (mean of 634 GT-aligned subtomos), plots central XY slice (Z=48) with voxel axes + colorbar + dashed circle mask overlay
- Josh adjusted: final mask = **r=32 px (427 Å), center offset Y=−10 → center at (48, 38)** in 96³ box
- PNG saved to `outputs/relion_motor_easy/avg_central_slice_with_mask.png`

### Class B run_07 and run_08
- Generated `production/coords/run_08.txt` (38 particles, seed=8) via `gen_coords_random.py`
- Created `production/class_B/run_07/configs.yaml` and `run_08/configs.yaml` (copy of run_01, coord + root updated)
- Updated `run_classB.sh`: all 4 loops extended to `run_07 run_08`; merge changed from `range(1,7)` → `range(1,9)`
- Updated `align_all_classes.py`: CLASS_RUNS["B"] now includes run_07 and run_08
- Updated `avg_gt_classB.py`: RUNS list extended to include run_07 and run_08

### Two ETSim pipeline bugs encountered and fixed

**Bug 1 — ETSim needs `output/` pre-created:**
ETSim calls `os.mkdir(output/raw_data)` — single `mkdir`, not `makedirs`. If `output/` doesn't exist, it fails with `FileNotFoundError: output/raw_data`. Fix: added `mkdir -p "$PROD/class_B/$RUN/output"` to `run_classB.sh` before launching ETSim. Also pre-created manually for run_07/08.

**Bug 2 — `sim_metadata.json` truncated to `[` on kill timing:**
When ETSim is killed immediately after the MRC is written, the JSON file may not be flushed. Fixed both runs via `reconstruct_metadata.py`.

### Final results
- run_07: 36 subtomos (2 near-edge skipped)
- run_08: 24 subtomos (14 near-edge skipped — wider XY spread with seed=8)
- `merged_B/`: 271 total class B subtomos
- `avg_classB_aligned.mrc` recomputed from all 271 particles

### Dataset state after this session
| Class | Runs | Subtomos |
|---|---|---|
| A | 7 | 246 |
| B | 8 | 271 |
| C | 5 | 177 |
| **Total** | **20** | **694** |

**`merged_all_aln/` NOT yet rebuilt** — still has 634 particles. Must run `align_all_classes.py` before rebuilding RELION/PEET inputs.

## Files changed

### In STA repo (local edits, not yet committed)
- `STATUS.md` — updated class B counts, mask params, unblocked Dynamo
- `outputs/relion_motor_easy/avg_central_slice_with_mask.png` (untracked, gitignored)
- `outputs/relion_motor_easy/avg_classB_central_slice.png` (untracked, gitignored)

### Local only (~/Research/synthetic_sta/motor_easy/)
- `visualize_avg_with_mask.py` — NEW
- `run_classB.sh` — extended to run_07/08, added `mkdir -p output/`
- `align_all_classes.py` — CLASS_RUNS["B"] extended
- `avg_gt_classB.py` — RUNS extended
- `production/coords/run_08.txt` — NEW (38 particles, seed=8)
- `production/class_B/run_07/configs.yaml` — NEW
- `production/class_B/run_08/configs.yaml` — NEW
- `production/subtomos/class_B/run_07/` — 36 MRCs + labels.csv
- `production/subtomos/class_B/run_08/` — 24 MRCs + labels.csv
- `production/subtomos/avg_classB_aligned.mrc` — recomputed (271 particles)

## Where I stopped
Class B fully simulated, reconstructed, extracted, merged (271 particles). Average recomputed. `merged_all_aln/` not yet rebuilt.

## Next step
1. **Rebuild merged dataset** (now 694 particles):
   ```bash
   conda run -n relion-5.0 python3 ~/Research/synthetic_sta/motor_easy/align_all_classes.py
   ```
2. **Rebuild RELION inputs:**
   ```bash
   cd ~/Research/STA
   conda run -n relion-5.0 python3 scripts/data_prep/make_initial_ref.py \
     --subtomo-dir ~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln \
     --out outputs/relion_motor_easy/initial_ref.mrc --pixel-size 13.329
   conda run -n relion-5.0 python3 scripts/data_prep/build_relion_star.py \
     --subtomo-dir ~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln \
     --outdir outputs/relion_motor_easy \
     --wedge-ctf outputs/relion_motor_easy/ctf/wedge_ctf.mrc \
     --uniform-ctf outputs/relion_motor_easy/ctf/uniform_ctf.mrc \
     --pixel-size 13.329
   ```
3. **Rebuild PEET stack:**
   ```bash
   conda run -n relion-5.0 python3 peet/motor_easy_stack.py
   ```
4. **Re-run RELION without `--skip_align`** on the 694-particle dataset (k=2, k=3)
5. **Run Dynamo on motor_easy** (PCT confirmed installed; use mask r=32 px, center=(48,38))
