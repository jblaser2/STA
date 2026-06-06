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

### Synthetic — motor_easy (694 particles, 3 classes)

| k | ARI | Status |
|---|-----|--------|
| 3 | 🟡 pending | PCT confirmed installed; unblocked as of 2026-06-04 |

---

## Key Findings

- HAC on PCA-reduced subtomogram distances cleanly separates T4P two states with no parameter tuning.
- This is the only package (alongside PEET and PyTom) confirmed to recover the structural signal on T4P.
- The 447/225 split differs from the published study ratio; further validation (Stefano's MOTL) needed.
- MATLAB PCT is installed, so Dynamo MRA on motor_easy is unblocked.

---

## Next Steps

- Run Dynamo MRA on motor_easy (rebuild `merged_all_aln/` first after class C re-simulation).

---

## Files

| Path | Description |
|------|-------------|
| `packages/dynamo/dynamo_final_results/` | Class comparison PNG + UMAP figure |
| `packages/dynamo/dynamo_outputs/` | Classification workspace outputs |
| `packages/dynamo/dynamo_scripts/` | Wrapper scripts |
| `packages/dynamo/research.md` | Workflow notes, DTutorial learning, PCA/MRA methodology |
| `outputs/` | Large binary run data (gitignored) |
