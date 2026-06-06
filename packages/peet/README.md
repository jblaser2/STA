# PEET

**Algorithm:** PCA + k-means on aligned subtomograms with cylindrical masks; WMD (wedge-model-based) weighting  
**Environment:** IMOD (system install)  
**Status:** ✅ T4P complete (two runs) · ✅ motor_easy run (ARI=0.026, WMD limitation confirmed)

---

## Results

### T4P Real Dataset (672 particles)

| Run | Mask | k | Split | AIC | Converged? |
|-----|------|---|-------|-----|------------|
| v1 | Cylindrical r=11.2, h_pos=9.8, h_neg=15.8 | 3 | 388 / 216 / 68 | 518 | **Yes** |
| v2 (best) | Cylindrical r=13, h_pos=0, h_neg=25 (below-center) | 3 | **374 / 230 / 68** | 659 | **Yes** |

**v2 is the canonical result.** Class labels: `ring_complete` / `ring_altered` / `junk`.
The junk class (68 particles) matches exactly the bottom-68-by-CCC set flagged by Stefano.

Key insight: with the cylindrical mask, PC1 captures structural signal (include it). With a
sphere mask, PC1 captures noise (exclude it). The mask geometry is critical.

### Synthetic — motor_easy (694 particles)

| Config | k | ARI | Notes |
|--------|---|-----|-------|
| WMD-PCA, r=32px mask | 3 | **0.026** | Confirms WMD-PCA limitation on uniform-wedge pre-aligned stacks |

WMD weights are not meaningful when all particles have identical tilt geometry (pre-aligned
identity poses). This is expected; motor_easy was included to validate the scoring pipeline.

---

## Key Findings

- Cylindrical mask aligned to the complex axis is essential — sphere masks suppress the structural PC.
- v2 (below-center only, r=13) is best; extending above the pilus entry point adds noise.
- WMD-PCA should be avoided for uniform-wedge pre-aligned stacks (motor_easy ARI ≈ 0).
- Best available soft-GT for the real-data benchmark track until Stefano's MOTL files are shared.

---

## Next Steps

- Email Stefano for exact MOTL files (per-particle GT assignments from his published result).
- Use v2 assignments (374/230/68) as soft GT for cross-package ARI comparisons.

---

## Files

| Path | Description |
|------|-------------|
| `packages/peet/results/` | Class average figures; v1/v2 mask comparison PNG |
| `packages/peet/motor_easy.prm` | PEET project file for synthetic data |
| `packages/peet/motor_easy_stack.py` | Synthetic data stack-building script |
| `packages/peet/kmeans_motor_easy.py` | k-means scoring script for motor_easy |
| `packages/peet/PEET_classification_research.md` | Detailed research notes |
| `packages/peet/PEET_usage_guide.md` | Usage guide |
| `outputs/peet_motor_easy/` | Synthetic run outputs |
| `results/` | Aggregated scoring CSVs |
