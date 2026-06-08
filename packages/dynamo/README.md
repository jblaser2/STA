# Dynamo

**Algorithm:** Hierarchical agglomerative clustering (HAC) on PCA-reduced subtomogram distances  
**Environment:** MATLAB (native, no conda env)  
**Status:** ✅ T4P complete (reference result) · ✅ FM_easy complete

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | cyl v2 | — (no GT) | **447 / 225** (+junk pending) | Reference result; both pili phases recovered; validated with Stefano |
| **FM_easy** | ✅ | k=3 / k=3 | sphere (r=32, Y-10) | **0.200** | — | dpkpca nc=17; class B 96–99% pure; A/C mixed |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P canonical: k=3 run (2 signal + 1 junk), cylindrical mask v2. Junk class identification
> pending — current 447/225 result is the pre-junk-class run. Next run should add k=3 to isolate
> junk particles per protocol (see `docs/datasets.md`).

---

## Key Findings

- HAC on PCA-reduced subtomogram distances cleanly separates T4P two states with no parameter tuning.
- Only package (alongside PEET and PyTom) confirmed to recover the structural signal on T4P.
- The 447/225 split differs from the published study ratio; further validation (Stefano's MOTL) needed.
- FM_easy: dpkpca outperforms plain HAC at this SNR (ARI=0.200 vs HAC ARI≈0).
- MATLAB PCT is installed, so Dynamo MRA on FM_easy is available for robustness testing.

---

## Next Steps

- Re-run T4P with k=3 (2+junk) per standard protocol; identify junk class by CCC ranking.
- FM_easy complete.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/dynamo_final_results/` | Class comparison PNG, UMAP, FSC, class averages |
| `T4P/scripts/` | HAC classification scripts, FSC computation, visualization |
| `T4P/hac_classification/` | Large binary run outputs (gitignored) |
| `FM_easy/results/motor_easy_pca/` | dpkpca outputs (confusion PNGs, prediction CSVs) |
| `FM_easy/results/motor_easy_hac/` | HAC FM_easy outputs |
| `FM_easy/scripts/` | FM_easy runner scripts and scoring |
| `research.md` | Workflow notes, DTutorial, PCA/MRA methodology |
