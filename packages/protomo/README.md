# ProTomo (I3)

**Algorithm:** Iterative 3D alignment + multi-reference classification on centered subtomograms  
**Environment:** Native binary (I3 / ProTomo 3.1.0, system install)  
**Status:** ✅ T4P 2-class run complete on all 672 particles (did not separate the two phases) — lower priority for remaining datasets

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=2 / k=2 | none | — (no GT) | 352/194/126 junk (all 672) | CC=0.921 between classes; trivial solution — same result as 234-particle run. Symlink rebuild required after repo reorg (June 2026). See limitation note below. |
| **FM_easy** | ⬜ | k=3 / k=3 | none | — | — | Lower priority |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> **T4P edge-filter note:** ProTomo's `MRAAREA` parameter checks whether each particle's
> aligned position falls within 80% of the box volume. 438/672 T4P particles (65%) have
> overlap 0.63–0.64 — they were picked near the z-boundaries of their source tomograms,
> leaving one side of the 80³ box zero-padded. The initial run filtered these to 234
> particles only. The full-672 rerun used `MRAPKR="0 0 0"` (no translation search) and
> `MRAAREA=0.0` (no overlap filtering) with `MSAIMGSIZE="32 32 32"` (SVD on central 32³
> cube only, unaffected by edge zero-padding). Result is identical: CC=0.921 — the zero-
> padded particles do not affect classification. The repo reorganization (2026-06-06) also
> broke the symlinks in `prepare/stacks/`; these were rebuilt pointing to `data/T4P_subtomos/`.

---

## Key Findings

- Full-672 rerun complete: split 352/194/126 junk, inter-class CC=0.921 — identical to the 234-particle result. The edge particles do not affect the classification outcome.
- High inter-class CC (0.921) confirms ProTomo does not separate the two T4P phases — one dominant class.
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
