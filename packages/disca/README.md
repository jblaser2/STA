# DISCA

**Algorithm:** Template-free deep unsupervised clustering (pytorch, native sm_120 support)  
**Environment:** `disca` conda env  
**Status:** ✅ T4P k=2/3/4 complete — did not separate the two phases

---

## Results

### T4P Real Dataset (672 particles)

| k | Outcome | Converged? |
|---|---------|------------|
| 2 | ~94% dominant class + small noisy outlier | **No** |
| 3 | ~94% dominant class + small noisy outliers | **No** |
| 4 | ~94% dominant class + small noisy outliers | **No** |

All k values collapse to one dominant class (~630+ particles) with small residual clusters
that appear to capture noise outliers rather than structural signal. DISCA did not separate
the two known T4P conformational states.

### Synthetic — motor_easy

Not yet run.

---

## Key Findings

- Template-free deep clustering is not competitive with alignment-based methods at this SNR.
- The ~94% dominant class pattern is consistent with the method defaulting to a trivial solution
  (all particles look the same when SNR is low and there is no alignment-based focus mask).
- Provides a useful lower bound: purely learned feature representations without domain priors fail here.

---

## Next Steps

- Run on motor_easy after class C re-simulation (lower priority given T4P result).

---

## Files

| Path | Description |
|------|-------------|
| `packages/disca/research.md` | Package notes, installation, run commands |
| `packages/disca/results/` | Output directory |
| `scripts/data_prep/build_disca_input.py` | Input preparation script |
