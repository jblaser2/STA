# TomoFlow conformational analysis — T4P (672 subtomograms)

3D optical flow (farneback3d) vs global average → PCA landscape → k-means.

## Run 1: Unmasked (original)

| k | class sizes (occupancy) | inter-class CC |
|---|---|---|
| 2 | 638 (95%), 34 (5%) | 0.840 |
| 3 | 252 (38%), 29 (4%), 391 (58%) | 0.773–0.956 |
| 4 | 305 (45%), 327 (49%), 26 (4%), 14 (2%) | 0.532–0.964 |

## Run 2: Cylindrical mask v2 applied (2026-07-01, ORC SLURM job 12460059)

| k | class sizes (occupancy) | inter-class CC |
|---|---|---|
| 2 | 403 (60%), 269 (40%) | 0.970 |
| 3 | 149 (22%), 402 (60%), 121 (18%) | 0.934–0.960 |
| 4 | 225 (33%), 130 (19%), 178 (26%), 139 (21%) | 0.933–0.947 |

## Cross-package ARI (masked run, k=2)

ARI computed against Dynamo k=2 assignments (447 ring_complete / 225 ring_altered):

| Reference package | n shared | ARI |
|---|---|---|
| Dynamo k=2 | 672 | **-0.001** |
| PEET k=3 (non-junk) | 604 | **+0.001** |

Cross-tabulation vs Dynamo (TomoFlow rows × Dynamo cols):

|  | Dynamo class 1 | Dynamo class 2 |
|---|---|---|
| TomoFlow class 0 (n=269) | 179 (67%) | 90 (33%) |
| TomoFlow class 1 (n=403) | 268 (66%) | 135 (34%) |

Both TomoFlow clusters have the same ~66/34 ratio as the Dynamo marginal — the split is
completely orthogonal to the structural axis.

## Conclusion

The masked PCA landscape is bimodal (two separated blobs in PC1) but the separation axis
corresponds to a **noise/missing-wedge axis**, not the ring_complete/ring_altered structural
axis. ARI ≈ 0 vs all structural references confirms the split is degenerate. The mask removes
the outlier/solvent signal driving the 95%/5% unmasked split, but the remaining landscape
captures only noise. TomoFlow **cannot recover the T4P phase split** in either configuration.
Finalized as **collapsed** in the benchmark.
