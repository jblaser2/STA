# Dynamo

**Algorithm:** Hierarchical agglomerative clustering (HAC) on PCA-reduced subtomogram distances  
**Environment:** MATLAB (native, no conda env)  
**Status:** ✅ T4P complete (reference result) · ✅ FM_easy complete · ✅ FM_switch complete

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | cyl v2 | — (no GT) | **447 / 225** (+junk pending) | Reference result; both pili phases recovered; validated with Stefano |
| **FM_easy** | ✅ | k=3 / k=3 | sphere (r=32, Y-10) | **0.200** | — | dpkpca nc=17; class B 96–99% pure; A/C mixed |
| **FM_switch** | ✅ | k=2 / k=2 | RELION ellipsoid (r_xz=38, r_y=65) | **−0.001** | 229 / 222 | dpkpca 50 eigs; CCW/CW split ~50/50 across both clusters; unsupervised failure (cf. PEET 0.007); only GT-seeded RELION found signal (0.379) |
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
- FM_switch: dpkpca fails (ARI≈0) — the CCW↔CW rotational switch is not captured on the leading PCA axes; clusters split on noise. Matches PEET's unsupervised failure (0.007); only GT-seeded RELION recovered any signal (0.379).
- MATLAB PCT is installed, so Dynamo MRA on FM_easy is available for robustness testing.
- **160³ ccmatrix parpool quirk:** at 160³, the implicit pool (`cores='*'`=24 workers) tears down mid-`ccmatrix` parfor (libgtk ServiceHost crash-loop), killing the step. Fix in `dynamo_motor_switch_pca.m`: `setenv('MW_SERVICE_HOST_DISABLE','1')`, one explicit `parpool('Processes',16)` with `IdleTimeout=Inf`, and `cores=16`. Launch detached (`nohup … &`) so a closing shell can't SIGHUP it.

---

## Next Steps

- Re-run T4P with k=3 (2+junk) per standard protocol; identify junk class by CCC ranking.
- FM_easy complete.
- FM_switch complete.
- FM_hard / T4SS not yet run.

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
| `FM_switch/results/` | FM_switch k=2 confusion PNG |
| `FM_switch/scripts/` | FM_switch dpkpca runner (`dynamo_motor_switch_pca.m`), setup, scorer, nc-sweep |
| `dynamo_outputs/motor_switch_pca/` | dpkpca workflow, eigencomponents, CC matrix, predictions (gitignored) |
| `research.md` | Workflow notes, DTutorial, PCA/MRA methodology |
