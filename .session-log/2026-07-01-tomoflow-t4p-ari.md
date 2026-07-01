# 2026-07-01 — TomoFlow T4P ARI + reclassification

## Goal
Extract TomoFlow k=2 cluster assignments from the ORC masked run, compute ARI vs Dynamo and
other packages, and update the all-10-package classification agreement grid.

## What happened

**ARI computation:**
- Copied `embedding.npy` (672×2 PCA landscape) and `keys.txt` from ORC masked run
  (`~/Research/tomoflow_orc/output/`)
- Re-ran k-means k=2 (best inertia over 30 seeds) → 403/269 split (reproducible from earlier run)
- ARI vs Dynamo k=2: **−0.001** (≈ 0); ARI vs PEET k=3 non-junk: **+0.001**
- Cross-tabulation confirmed: both TomoFlow clusters have ~66/34 Dynamo-class ratio = population
  base rate → split is orthogonal to structural axis

**Key discovery — cross-package ARI:**
- When the full 10×10 grid was built, TomoFlow masked k=2 showed:
  - **DISCA vs TomoFlow: ARI = 1.000**
  - **EMAN2 vs TomoFlow: ARI = 0.993**
  - **OPUS vs TomoFlow: ARI = 0.887**
- TomoFlow is NOT collapsed — it finds the same contrast/intensity axis as the non-structural group
- Reclassified: **collapsed → non-structural**

**Files created/changed:**
- `results/T4P/tomoflow_k2_std.csv` — 672 per-particle assignments (new)
- `packages/figures/T4P/tomoflow_class_avgs_std.png` — standardised 2-panel (1256×583, matches format)
- `packages/figures/T4P/all_pkg_grid.png` — now a true 10×10 matrix, no sidebar
- `scripts/eval/gen_t4p_full_pkg_grid.py` — TomoFlow moved to non_structural, title/legend updated
- `scripts/eval/gen_t4p_class_avg_panels.py` — TomoFlow entry added; MRCs at `outputs/T4P/tomoflow/`
- `packages/tomoflow/README.md` — category, result table, notes updated
- `packages/tomoflow/T4P/results/RESULTS.md` — cross-package ARI table + updated conclusion
- `packages/tomoflow/research.md` — masked run paragraph rewritten
- `packages/README.md` — TomoFlow row + gallery + description paragraph updated
- `STATUS.md` — new TomoFlow bullet + Package Matrix row + Ground Truth bullet updated

**Commits pushed:**
- `218d910` — standardised class avg panel
- `bf1bcfa` — per-particle CSV + reclassification + 10×10 grid

## Where I stopped
All TomoFlow T4P work is fully committed and pushed. Status.md staged (not committed).

## Next step
- Consider updating `docs/benchmarkIdeas.md` §12 no-GT evidence chain: TomoFlow adds a 4th
  independent vote to the contrast-axis group (ARI=1.0 with DISCA) — strengthens the two-axis story
- Consider T3SS on aligned particles (mirror FM_easy alignment fix)
- Run STOPGAP on FM_easy locally (first local STOPGAP run)
