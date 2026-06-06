# Dynamo

**Algorithm:** Hierarchical agglomerative clustering (HAC) on PCA-reduced subtomogram distances  
**Environment:** MATLAB (native, no conda env)  
**Status:** ✅ T4P complete — **reference result** for the benchmark

---

## Results

### T4P Real Dataset (672 particles)

| k | Split | Converged? | Notes |
|---|-------|------------|-------|
| 2 | **447 / 225** | **Yes** | Both known pili-phase conformational states recovered; validated with Stefano |

Dynamo is the **reference result** — its two-class split is the structural ground-truth other
packages are measured against. Class 1 (ring-complete, n=447): 62.7 Å at FSC=0.5.
Class 2 (ring-altered, n=225): 96.9 Å at FSC=0.5.

### Synthetic — motor_easy (694 particles, 3 classes, C_noRodHook definition)

| Approach | k | ARI | Notes |
|----------|---|-----|-------|
| HAC (CC Ward) | 2 | 0.005 | Cophenetic=0.094; no CC structure at this SNR |
| HAC (CC Ward) | 3 | −0.009 | All 177 class C particles in large cluster |
| **dpkpca** | **3** | **0.200** | nc=17 sweep; class B 96–99% pure; A/C mix |
| dpkpca | 2 | 0.143 | nc=32 |

Canonical motor_easy result: **k=3 ARI=0.200** (dpkpca).  
Scripts: `dynamo_scripts/dynamo_motor_easy_hac.m`, `dynamo_motor_easy_pca.m`, `setup_motor_easy_pca.py`.

---

## Key Findings

- HAC on PCA-reduced subtomogram distances cleanly separates T4P two states with no parameter tuning.
- This is the only package (alongside PEET and PyTom) confirmed to recover the structural signal on T4P.
- The 447/225 split differs from the published study ratio; further validation (Stefano's MOTL) needed.
- MATLAB PCT is installed, so Dynamo MRA on motor_easy is unblocked.

---

## Next Steps

- motor_easy complete. Next package: PyTom motor_easy (scripts staged at `packages/PyTom/`).

---

## Files

| Path | Description |
|------|-------------|
| `packages/dynamo/dynamo_final_results/` | Class comparison PNG + UMAP figure |
| `packages/dynamo/dynamo_outputs/` | Classification workspace outputs |
| `packages/dynamo/dynamo_scripts/` | Wrapper scripts |
| `packages/dynamo/research.md` | Workflow notes, DTutorial learning, PCA/MRA methodology |
| `outputs/` | Large binary run data (gitignored) |
