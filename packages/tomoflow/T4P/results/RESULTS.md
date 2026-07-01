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

## Conclusion

The mask removes the solvent/outlier signal that was driving the 95%/5% collapse, producing a
more balanced k=2 split (403/269). However, the inter-class CC actually **increases** from
0.840 → 0.970, meaning the two class averages are nearly identical. The structural landscape
is unimodal regardless of masking. TomoFlow cannot recover the T4P phase split in either
configuration. Finalized as **collapsed** in the benchmark.
