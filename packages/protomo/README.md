# ProTomo (I3)

**Algorithm:** Iterative 3D alignment + multi-reference classification on centered subtomograms  
**Environment:** Native binary (I3 / ProTomo 3.1.0, system install)  
**Status:** ✅ T4P 2-class run complete (did not separate the two phases) — lower priority for remaining datasets

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=2 / k=2 | none | — (no GT) | 234 particles (438 filtered) | CC=0.921 between classes; trivial solution; centering filter acts as junk removal |
| **FM_easy** | ⬜ | k=3 / k=3 | none | — | — | Lower priority |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P note: ProTomo's centering/edge filter removes 438 of 672 particles before classification —
> this acts as junk removal at the pre-classification stage, so k=2 is the reported result.
> Standard protocol (k=3, 2+junk) does not apply in the same way as other packages.

---

## Key Findings

- Centering filter discards 438/672 particles — reduces statistical power before classification.
- High inter-class CC (0.921) indicates trivial solution; one dominant class.
- ProTomo is primarily an alignment package; classification is a secondary capability.

---

## Next Steps

- Lower priority given T4P result. Revisit only if alignment quality is identified as the bottleneck.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/class_averages_slices.png` | Central slice comparison of two classes |
| `T4P/results/clustering_scatter.png` | Clustering scatter plot |
| `research.md` | Detailed workflow and configuration notes |
