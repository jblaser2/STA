# EMAN2

**Algorithm:** PCA split on subtomogram stack with reference-based wedge-fill  
**Environment:** `eman2` conda env  
**Status:** ✅ T4P k=2 complete (misses two phases) · k=3/4 not yet run · wedge-fill patch applied

---

## Results

### T4P Real Dataset (672 particles)

| k | Split | Converged? | Notes |
|---|-------|------------|-------|
| 2 | 393 / 279 | **No** | Splits particles but not into the two pili conformational states |
| 3 | ⬜ | — | Not yet run |
| 4 | ⬜ | — | Not yet run |

EMAN2 k=2 splits particles but the resulting classes do not correspond to ring-complete vs
ring-altered. The split likely reflects a different feature axis (possibly contrast variation
or noise).

**2026-06-05 patches (Eben):**
- Patch 2 re-activates `mask.wedgefill` in `e2spt_pcasplit.py` active path (the `--nowedgefill`
  flag was a no-op since fill lived only in a commented-out block).
- `run_pipeline.sh` now uses NO-ALIGNMENT variant (particles pre-aligned at identity → skip
  orientation search).
Not yet re-run with these patches.

### Synthetic — motor_easy

Not yet run.

---

## Key Findings

- EMAN2 misses the T4P two phases at k=2.
- Wedge-fill was silently disabled before the 2026-06-05 patch — may improve results.
- Workspace lives at `~/src/eman2_project/` (local, not in repo).

---

## Next Steps

- Re-run k=2 with wedge-fill patch applied and verify the result changes.
- Run k=3 and k=4.

---

## Files

| Path | Description |
|------|-------------|
| `packages/eman2/research.md` | Comprehensive notes: Qt/OpenGL Wayland fix, PCA pipeline, wedge-fill patch |
| `packages/eman2/pcaScripts/` | PCA-split helper scripts |
| **Workspace:** `~/src/eman2_project/` | Local workspace (not in repo) — outputs at `spt_cls01/02/` |
