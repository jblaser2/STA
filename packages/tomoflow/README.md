# TomoFlow

**Algorithm:** ContinuousFlex optical-flow-based conformational classification  
**Environment:** `tomoflow` conda env  
**Status:** ✅ T4P k=2 complete (unimodal landscape) · ✅ FM_easy 2-class hc k=2 (ARI=0.036, collapses)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | none | — (no GT) | — | Unimodal landscape; k=3 two large classes CC=0.956; did not separate phases |
| **FM_easy** (2-class hc, 542p) | ✅ | k=2 / k=2 | diff sphere (input) | **0.036** | 462/80 | OF landscape collapses (unimodal), as on T4P. Run at downsample 3 (32³) — native 96³ ≈7 hrs and result is collapse regardless. Confusion: `outputs/FM_easy/tomoflow/` |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P: ran k=2, k=3, k=4 historically — all showed same collapse. Protocol run (k=3 with junk)
> not yet done. Given the T4P result, FM_easy is lower priority.

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

- T4P: run k=3 (2+junk) per protocol.
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
