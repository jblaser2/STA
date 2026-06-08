# PyTom

**Algorithm:** FRM (Fast Rotational Matching) alignment + k-means classification with cylindrical focus mask  
**Environment:** `pytom_env` conda env  
**Status:** ✅ T4P k=2 and k=3 complete (converged with v2 mask + `-a` flag) · ✅ motor_easy k=2/k=3 complete · k=4 (T4P) not yet run

---

## Results

### T4P Real Dataset (672 particles)

| k | Split | Iterations | Converged? | Notes |
|---|-------|-----------|------------|-------|
| 2 | **440 / 232** | 5 | **Yes** | Class 1 ≈ PEET ring_altered |
| 3 | **422 / 150 / 100** | 11 | **Yes** | |
| 4 | ⬜ | — | — | Not yet run |

**Fixed 2026-06-05:** Previous failures were due to wrong mask (symmetric r=7.2 defaults).
Correct config: v2 cylindrical mask (r=13, h_pos=0, h_neg=25) + `-a` flag.

The `-a` flag is required because the `_swig_frm` C extension is absent in this build — it
activates a pure-Python FRM fallback. Without it, PyTom silently uses a mode that does not
apply the focus mask properly.

### Synthetic — motor_easy (694 GT-aligned particles, 96³, 13.33 Å/px)

| k | ARI | Notes |
|---|-----|-------|
| 2 | 0.090 | v2 cylindrical mask |
| 3 | **0.134** | v2 cylindrical mask (best) |

Scripts: `packages/PyTom/setup_motor_easy_pytom.py`, `run_motor_easy_pytom.sh`.
Labels: `outputs/relion_motor_easy/pytom_motor_easy_k{2,3}.csv`.
Confusion PNGs: `outputs/relion_motor_easy/confusion_pytom_k{2,3}_motor_easy_*.png`.

---

## Key Findings

- PyTom successfully separates the T4P two conformational states with the correct cylindrical mask.
- The `-a` flag and v2 mask (below-center, r=13) are both required — neither alone is sufficient.
- Previous symmetric masks (r=7.2 default) captured noise outside the complex; cylindrical mask
  constrains classification to the structurally informative periplasmic ring region.
- motor_easy k=3 ARI=0.134 — middle of the motor_easy leaderboard (above PEET/OPUS-TOMO, below Dynamo).

---

## Next Steps

- Run k=4 on T4P.
- motor_easy complete.

---

## Files

| Path | Description |
|------|-------------|
| `packages/PyTom/instructions.md` | Usage guide |
| `packages/PyTom/research.md` | Detailed notes: FRM module absence, mask requirements, `-a` flag fix |
| `packages/PyTom/visualize_classification.py` | Plotting script for class results |
| `packages/PyTom/cylindrical_mask.em` / `.mrc` / `.npy` | v2 cylindrical mask (r=13, h_pos=0, h_neg=25) |
| `packages/PyTom/figures_v2mask_k2/` | k=2 result figures |
| `packages/PyTom/figures_v2mask_k3/` | k=3 result figures |
| `results/pytom_v2mask_k2.csv` | k=2 per-particle class assignments |
| `results/pytom_v2mask_k3.csv` | k=3 per-particle class assignments |
