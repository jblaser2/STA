# ProTomo (I3)

**Algorithm:** Iterative 3D alignment + multi-reference classification on centered subtomograms  
**Environment:** Native binary (I3 / ProTomo 3.1.0, system install)  
**Status:** ✅ T4P 2-class run complete — did not separate the two phases

---

## Results

### T4P Real Dataset (672 → 234 centered particles)

| k | Particles | CC | Converged? |
|---|-----------|-----|------------|
| 2 | 234 (of 672) | 0.921 | **No** |

Only 234 of 672 particles passed the centering/edge filter (438 edge-filtered). The 2-class
result gives CC=0.921 between classes, meaning they are nearly identical — one dominant class
with no structural differentiation.

### Synthetic — motor_easy

Not yet run.

---

## Key Findings

- ProTomo's edge-filtering step discards a large fraction of T4P particles (438/672 removed),
  reducing statistical power before classification begins.
- The high inter-class CC (0.921) indicates the method converged to a trivial solution.
- I3/ProTomo is primarily an alignment package; classification is a secondary capability.

---

## Next Steps

- Lower priority given T4P result; revisit if motor_easy results from other packages suggest
  a path where alignment quality is the bottleneck.

---

## Files

| Path | Description |
|------|-------------|
| `packages/protomo/research.md` | Detailed workflow and configuration notes |
| `packages/protomo/results/` | Output directory |
| `packages/protomo/tutorial/` | Example data |
