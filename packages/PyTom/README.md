# PyTom

**Algorithm:** FRM (Fast Rotational Matching) alignment + k-means classification with cylindrical focus mask  
**Environment:** `pytom_env` conda env  
**Status:** ✅ T4P complete (converged, v2 mask + `-a` flag) · ✅ FM_easy complete

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | cyl v2 | — (no GT) | **440 / 232** (+junk pending) | Converged; requires `-a` flag AND v2 mask — both critical |
| **FM_easy** (2-class hc, 542p) | ✅ | k=2 / k=2 | diff sphere | **0.031** | 369/173 | auto_focus_classify `-a`; does not find the class axis on the hc set. Confusion: `outputs/FM_easy/pytom/` |
| FM_easy (old 3-class, 694p) | 🗄️ archived | k=3 | cyl v2 | 0.134 | — | Superseded; archived |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P canonical: k=3 run (2 signal + 1 junk), v2 cylindrical mask, `-a` flag.
> Junk class identification pending — current 440/232 result is from the pre-protocol run.
> Next run should use k=3 to isolate junk particles per `docs/datasets.md`.

---

## Key Findings

- The `-a` flag is required: `_swig_frm` C extension is absent in this build; `-a` activates
  a pure-Python FRM fallback. Without it, the focus mask is not applied correctly.
- Both v2 mask AND `-a` flag are necessary — neither alone recovers the two T4P phases.
- Previous failures used symmetric r=7.2 mask (wrong); v2 (r=13, h_pos=0, h_neg=25) constrains
  classification to the periplasmic ring region.
- FM_easy: k=3 ARI=0.134 — above PEET/OPUS-TOMO, below Dynamo.

---

## Next Steps

- Re-run T4P with k=3 (2+junk) per standard protocol.
- FM_easy complete.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/configs/cylindrical_mask.{em,mrc,npy}` | v2 cylindrical mask (r=13, h_pos=0, h_neg=25) |
| `T4P/configs/particle_list.xml` | T4P particle list |
| `T4P/configs/starting_average.{mrc,npy}` | Starting average for FRM |
| `T4P/results/figures_v2mask_k2/` | k=2 result figures (canonical) |
| `T4P/autofocus_v2mask_k2/` | k=2 run output directory (large, gitignored) |
| `T4P/scripts/` | Mask generation, classification, visualization scripts |
| `T4P/instructions.md` | Usage guide |
| `FM_easy/configs/motor_easy_mask.em` | FM_easy focus mask |
| `FM_easy/configs/particle_list_motor_easy.xml` | FM_easy particle list |
| `FM_easy/scripts/` | FM_easy setup and runner scripts |
| `research.md` | Notes: FRM module absence, mask requirements, `-a` flag fix |
| `outputs/FM_easy/pytom/` | FM_easy predictions CSVs and confusion PNGs |
