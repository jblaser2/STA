# PEET

**Algorithm:** PCA + k-means on aligned subtomograms with cylindrical masks; WMD weighting  
**Environment:** IMOD (system install)  
**Status:** ✅ T4P complete (v2 mask, best result) · ✅ FM_easy complete (WMD limitation confirmed)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | cyl v2 | — (no GT) | **374 / 230** (+68 junk) | Converged; junk class matches Stefano's bottom-68-by-CCC exactly |
| **FM_easy** | ✅ | k=3 / k=3 | — | **0.050** (k=3); 0.116 (k=2) | — | WMD-PCA broken on uniform-wedge stacks; set WMD=off |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P canonical result: v2 mask (r=13, h_pos=0, h_neg=25, below-center only), k=3 (2+junk).
> Class labels: `ring_complete` (374) / `ring_altered` (230) / `junk` (68).
> With cylindrical mask, PC1 captures structural signal (include it). With sphere mask, PC1
> captures noise (exclude it).

---

## Key Findings

- Cylindrical mask aligned to the complex axis is essential — sphere masks suppress the structural PC.
- v2 (below-center only, r=13) is best; extending above the pilus entry point adds noise.
- WMD-PCA meaningless for uniform-wedge pre-aligned stacks — set `flgWedgeWeight=0` always.
- Best available soft-GT for the real-data benchmark track until Stefano's MOTL files are shared.

---

## Next Steps

- Email Stefano for exact MOTL files (per-particle GT assignments from his published result).
- Use v2 assignments (374/230/68) as soft GT for cross-package ARI comparisons.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/class_averages_v2_masked_xy_diff.png` | Canonical T4P result figure |
| `T4P/results/mask_v2_preview.png` | Cylindrical mask v2 preview (middle column = canonical mask) |
| `T4P/results/peet_final_class_assignments_v2.csv` | Per-particle class assignments (374/230/68) |
| `T4P/configs/peet_project_single.prm` | PEET project file for T4P |
| `T4P/scripts/` | Class average generation, comparison scripts |
| `T4P/PEET_usage_guide.md` | Parameter reference and mask notes |
| `T4P/PEET_classification_research.md` | Detailed research notes |
| `FM_easy/configs/motor_easy.prm` | PEET project file for FM_easy |
| `FM_easy/scripts/` | k-means scoring and stack-building scripts |
| `outputs/FM_easy/peet/` | FM_easy run outputs (confusion PNGs, prediction CSVs) |
