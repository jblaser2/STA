# TomoFlow

**Algorithm:** ContinuousFlex optical-flow-based conformational classification  
**Environment:** `tomoflow` conda env  
**Status:** ✅ T4P k=2 complete (non-structural; ARI=1.00 vs DISCA, 0.99 vs EMAN2) · ✅ FM_easy 2-class hc k=2 (ARI=0.036)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** (unmasked) | ✅ | k=2,3,4 | none | — (no GT) | — | Unimodal; k=2 → 638/34 (95%:5%), CC=0.840 |
| **T4P** (masked, 2026-07-01) | ✅ | k=2,3,4 | cyl v2 | **ARI=1.00 vs DISCA** | — | k=2 → 403/269. ARI=-0.001 vs Dynamo but **1.000 vs DISCA, 0.993 vs EMAN2, 0.887 vs OPUS** — OF finds the same contrast/intensity axis as the non-structural group. |
| **FM_easy** (2-class hc, 542p) | ✅ | k=2 / k=2 | diff sphere (input) | **0.036** | 462/80 | OF landscape collapses (unimodal), as on T4P. Run at downsample 3 (32³) — native 96³ ≈7 hrs and result is collapse regardless. Confusion: `outputs/FM_easy/tomoflow/` |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P masked run on ORC (SLURM, P100): job 12460059, `~/Research/tomoflow_orc/`. k=2 → 403/269.
> ARI vs Dynamo = -0.001, but **ARI=1.000 vs DISCA, 0.993 vs EMAN2, 0.887 vs OPUS** — the masked
> OF landscape finds the same contrast/intensity axis as the non-structural group. Reclassified
> from "collapsed" to **non-structural** in the benchmark.

---

## Key Findings

- Optical-flow methods assume a continuous conformational landscape; T4P may have too discrete
  a transition for this model (binary ring-complete vs ring-altered states).
- k=3: two large classes with CC=0.956 — nearly identical; third class captures outliers.
- Requires subtomogram-average reference (not an atomic model) — hence included in benchmark.
- Required porting `farneback3d` off CUDA texture-references for CUDA 13.2 / sm_120 (RTX 5080).
  See `research.md` §2 for the patch details.

---

## Next Steps

- T4P: finalized as **non-structural** — OF finds contrast/intensity axis (ARI=1.00 vs DISCA, 0.99 vs EMAN2), not the structural axis.
- FM_easy: run k=3 when bandwidth allows (lower priority).

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/tomoflow_k2_classes.png` | k=2 result figure (both classes nearly identical) |
| `T4P/results/tomoflow_landscape.png` | Conformational landscape visualization |
| `T4P/results/RESULTS.md` | Run notes and output details |
| `research.md` | Workflow notes; CUDA texture-ref porting patch for sm_120 |
| `scripts/data_prep/tomoflow_run.py` | Input preparation and run script |
