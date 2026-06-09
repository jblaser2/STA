# ProTomo (I3)

**Algorithm:** Iterative 3D alignment + multi-reference classification on centered subtomograms  
**Environment:** Native binary (I3 / ProTomo 3.1.0, system install)  
**Status:** ✅ T4P 2-class run complete (did not separate the two phases) — lower priority for remaining datasets

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | 🟡 | k=2 / k=2 | none | — (no GT) | 234 particles (438 filtered) → rerun all 672 in progress | CC=0.921 between classes; trivial solution; edge filter discarded 65% of particles — see limitation note below |
| **FM_easy** | ⬜ | k=3 / k=3 | none | — | — | Lower priority |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> **T4P edge-filter limitation:** ProTomo's `.i3i` format stores original tomogram bounds for
> each particle. When individual pre-extracted 80³ MRCs are assembled into a dataset, ProTomo
> checks whether each extraction box has ≥80% overlap with its source tomogram volume
> (`MRAAREA=0.8`). 438 of 672 T4P particles (65%) fail this check because they were picked
> near the z-boundaries of their source tomograms without a margin exclusion. The initial run
> used the 234 "fully-centred" particles only. All other benchmark packages ingest the
> pre-extracted MRCs directly and do not apply this check — so the initial ProTomo result is
> **not comparable** to the rest of the benchmark. A rerun on all 672 is in progress
> (`~/Research/protomo/full672/`): `MRAPKR="0 0 0"` (translation-free, particles prealigned) and
> `MSAIMGSIZE="32 32 32"` (SVD uses only the central 32³ cube, unaffected by edge zero-padding)
> should make the classification valid even for edge particles. Class averages may appear
> slightly off-axis for the edge-particle subset but the SVD-based class assignments are valid.

---

## Key Findings

- **Initial run used only 234/672 particles** — not comparable to other benchmark packages.
  Root cause: ProTomo's `.i3i` metadata check discarded 438 particles as "near-edge" (see limitation note above). Rerun on all 672 in progress.
- High inter-class CC (0.921) in 234-particle run indicates trivial solution; one dominant class.
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
