# EMAN2

**Algorithm:** PCA split on subtomogram stack with reference-based wedge-fill  
**Environment:** `eman2` conda env  
**Status:** 🟡 T4P k=2 run complete (misses two phases) — wedge-fill patch applied, not yet re-run

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | 🟡 | k=3 / k=2 | — | — | 393 / 279 (+junk pending) | Does not recover two phases; wedge-fill patch applied 2026-06-05, re-run needed |
| **FM_easy** | ⬜ | — | — | — | — | Not yet run |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P to-do: re-run with k=3 (2+junk, cyl v2 mask) using the wedge-fill patch.
> Previous 393/279 result used k=2 and pre-patch pipeline — not the canonical run.

---

## Key Findings

- EMAN2 k=2 splits particles but not into the two pili conformational states (likely contrast/noise axis).
- Wedge-fill was silently disabled before 2026-06-05 patch — the `--nowedgefill` flag was a no-op.
- Workspace lives at `~/src/eman2_project/` (local, not in repo).
- Use NO-ALIGNMENT variant: particles pre-aligned at identity → skip orientation search.

---

## Next Steps

1. Re-run k=3 (2 signal + 1 junk) with wedge-fill patch and cylindrical v2 mask.
2. Run FM_easy (k=3, no junk).

---

## Files

| Path | Description |
|------|-------------|
| `T4P/scripts/` | PCA-split pipeline scripts (make_project.py, run_pipeline.sh, patch_scripts.py, visualization) |
| `research.md` | Qt/OpenGL Wayland fix, PCA pipeline, wedge-fill patch details |
| **Workspace:** `~/src/eman2_project/` | Local workspace — spt_cls01/02/ outputs |
