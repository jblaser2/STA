# 2026-06-08 — OPUS-TOMO motor_easy + PyTom backfill

## Goal
Run OPUS-TOMO on the motor_easy 3-class synthetic dataset (k=3) and update docs.

## What Happened

**OPUS-TOMO motor_easy k=3:**
- Created two new scripts: `packages/opusTomo/scripts/setup_motor_easy_opus.py` (writes particles.star
  + dummy CTF for 694 motor_easy particles, 96³ box) and `run_motor_easy_opus.sh` (8-step pipeline:
  STAR → pose → consensus mask → train 20 epochs → analyze k=3 → volumes → extract labels → score).
- Mask: threshold from motor_easy consensus (mean + 1σ + 2-iter dilation) → 28.3% of voxels,
  consistent with T4P approach (31.2%).
- Result: **ARI=0.021** (near-random). Split: 479/130/85. Class C (177 particles) 100% in dominant
  cluster, but cluster also absorbs 64% of A and 53% of B — A/B completely unseparated.
- Interpretation: VAE continuous latent space does not resolve discrete 3-class structure. OPUS-TOMO
  fails at what gradient-based PCA methods (Dynamo, PyTom) partially succeed at.
- Committed `356edee` (scripts, labels CSV, confusion PNG, docs).

**PyTom motor_easy backfill:**
- User noticed packages/README.md "All others ⬜" was wrong — PyTom motor_easy had already been run
  in a prior session but STATUS.md was never updated.
- Confirmed from synthetic_scores.csv: k=2 ARI=0.090, k=3 ARI=0.134 (v2mask, same mask as T4P).
- Committed the untracked files (scripts, label CSVs, confusion PNGs) and updated STATUS/READMEs.
- Committed `b932ab7`.
- Root cause of miss: /status reads the session log (dated 2026-06-06) but doesn't cross-check
  synthetic_scores.csv. When a run is done but not handoff'd, it's invisible to /status.

## Files Changed

- `packages/opusTomo/scripts/setup_motor_easy_opus.py` — new
- `packages/opusTomo/scripts/run_motor_easy_opus.sh` — new
- `outputs/opus_tomo_motor_easy_k3.csv` — new
- `outputs/confusion_opus-tomo_k3_threshold_mask.png` — new
- `packages/PyTom/setup_motor_easy_pytom.py` — committed (was untracked)
- `packages/PyTom/run_motor_easy_pytom.sh` — committed (was untracked)
- `packages/PyTom/auto_focus_classify_nofrm.py` — committed (was untracked)
- `packages/PyTom/particle_list_motor_easy.xml` — committed (was untracked)
- `outputs/relion_motor_easy/pytom_motor_easy_k{2,3}.csv` — committed
- `outputs/relion_motor_easy/confusion_pytom_k{2,3}_*.png` — committed
- `packages/opusTomo/README.md` — updated with motor_easy results
- `packages/PyTom/README.md` — updated with motor_easy results
- `packages/README.md` — PyTom motor_easy row added, "All others" note updated
- `STATUS.md` — OPUS-TOMO motor_easy bullet + PyTom backfill bullet + matrix rows updated
- `results/synthetic_scores.csv` — OPUS-TOMO row appended (PyTom rows were already present)
- `packages/dynamo/dynamo_scripts/score_dynamo_motor_easy.py` — path fix from repo reorg

## Where I Stopped
All docs synced, both commits pushed (`356edee`, `b932ab7`). motor_easy leaderboard:
RELION(GT)=0.475, Dynamo=0.200, PyTom=0.134, PEET=0.050, OPUS-TOMO=0.021.

## Next Step
Run motor_easy on EMAN2 (next in queue). T4P: EMAN2 k=3/k=4 also still pending.
OPUS-TOMO T4P ARI vs PEET soft GT still not computed.
