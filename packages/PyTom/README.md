# PyTom

**Algorithm:** FRM (Fast Rotational Matching) alignment + k-means classification with cylindrical focus mask  
**Environment:** `pytom_env` conda env  
**Status:** ✅ T4P k=2 and k=3 complete (converged with v2 mask + `-a` flag) · k=4 not yet run

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

### Synthetic — motor_easy

Not yet run (pending class C re-simulation).

---

## Key Findings

- PyTom successfully separates the T4P two conformational states with the correct cylindrical mask.
- The `-a` flag and v2 mask (below-center, r=13) are both required — neither alone is sufficient.
- Previous symmetric masks (r=7.2 default) captured noise outside the complex; cylindrical mask
  constrains classification to the structurally informative periplasmic ring region.

---

## Next Steps

- Run k=4 on T4P.
- Run on motor_easy after class C re-simulation.

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
