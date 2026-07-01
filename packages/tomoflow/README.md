# TomoFlow

**Algorithm:** ContinuousFlex optical-flow-based conformational classification  
**Environment:** `tomoflow` conda env  
**Status:** ✅ T4P k=2 complete (unimodal landscape) · ✅ FM_easy 2-class hc k=2 (ARI=0.036, collapses)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** (unmasked) | ✅ | k=2,3,4 | none | — (no GT) | — | Unimodal; k=2 → 638/34 (95%:5%), CC=0.840 |
| **T4P** (masked, 2026-07-01) | ✅ | k=2,3,4 | cyl v2 | **ARI≈0 vs Dynamo** | — | **Mask does not help**: k=2 → 403/269, CC=0.970. PCA landscape is bimodal but ARI=-0.001 vs Dynamo — split is on noise/wedge axis, not structural. |
| **FM_easy** (2-class hc, 542p) | ✅ | k=2 / k=2 | diff sphere (input) | **0.036** | 462/80 | OF landscape collapses (unimodal), as on T4P. Run at downsample 3 (32³) — native 96³ ≈7 hrs and result is collapse regardless. Confusion: `outputs/FM_easy/tomoflow/` |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P masked run on ORC (SLURM, P100): job 12460059, `~/Research/tomoflow_orc/`. Mask removes
> outlier/solvent signal driving the 95%/5% split; landscape is bimodal in PC1 but ARI vs Dynamo
> = -0.001 — the bimodal axis is noise/missing-wedge, not structural. CC goes UP (0.840→0.970).
> Conclusion: TomoFlow cannot find the T4P phase split with or without masking.

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

- T4P: masking confirmed to not help — result finalized as "collapsed" (unimodal landscape).
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
