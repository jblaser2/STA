# TomoFlow

**Algorithm:** ContinuousFlex optical-flow-based conformational classification (requires subtomogram average reference)  
**Environment:** `tomoflow` conda env  
**Status:** ✅ T4P k=2/3/4 complete — unimodal landscape, did not separate the two phases

---

## Results

### T4P Real Dataset (672 particles)

| k | Outcome | Converged? |
|---|---------|------------|
| 2 | One dominant class | **No** |
| 3 | Two large classes CC=0.956 + small third | **No** |
| 4 | Similar collapse | **No** |

The conformational landscape is effectively unimodal — k=3 produces two large classes with
cross-correlation 0.956, meaning they are nearly identical. TomoFlow treats the T4P ensemble
as a single structural state.

### Synthetic — motor_easy

Not yet run.

---

## Key Findings

- Optical-flow-based methods assume a continuous conformational landscape; T4P may have too
  discrete a transition for this model.
- Unlike MDTOMO/HEMNMA-3D, TomoFlow needs only a subtomogram-average reference (not an atomic
  model), so it was included in the benchmark.
- Required porting of `farneback3d` off CUDA texture-references for CUDA 13.2 / sm_120
  (RTX 5080 specific). See `research.md` §2 for the patch details.

---

## Next Steps

- Run on motor_easy after class C re-simulation (lower priority given T4P result).

---

## Files

| Path | Description |
|------|-------------|
| `packages/tomoflow/research.md` | Workflow notes; CUDA texture-ref porting patch for sm_120 |
| `packages/tomoflow/results/` | Output directory |
| `scripts/data_prep/tomoflow_run.py` | Input preparation and run script |
