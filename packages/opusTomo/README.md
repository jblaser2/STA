# OPUS-TOMO

**Algorithm:** Variational autoencoder (VAE) continuous latent-space clustering  
**Environment:** `opuset` conda env (rebuilt from scratch 2026-06-05, cu128 PyTorch)  
**Status:** ✅ T4P k=2/3/4 complete (threshold mask) · ARI vs PEET GT not yet computed

---

## Results

### T4P Real Dataset (672 particles)

| Mask | K | Split | Training Time | Converged? |
|------|---|-------|---------------|------------|
| Threshold (31.2% voxels) | 2 | **447 / 225** | ~2.5 min (epoch 19) | **Partial** |
| Y-axis cylinder (2.7% voxels) | 2 | 668 / 4 | — | **No** (collapses) |

Threshold mask (31.2% voxels): K=2 gives a 447/225 split consistent with the Dynamo reference.
Y-axis cylindrical mask (matching PyTom v2): K=2 collapses to 668/4 — the VAE needs a broader
mask to reconstruct its template during training. Too restrictive masks prevent the VAE from
learning meaningful latent structure.

ARI vs PEET soft GT not yet computed.

### Synthetic — motor_easy

Not yet run (pending class C re-simulation).

---

## Key Findings

- OPUS-TOMO succeeds with the threshold mask (31.2% voxels) — broad enough for VAE reconstruction.
- The cylindrical mask (2.7% voxels, matching PyTom v2) is too restrictive for the VAE.
- Four bugs were patched before any runs could complete (CTF, HEALPix, `--split`, dummy CTF header).
- The env had to be rebuilt completely (cu128 PyTorch for RTX 5080 / CUDA 13.2).

---

## Next Steps

- Compute ARI vs PEET soft GT for the threshold-mask K=2 result.
- Run on motor_easy after class C re-simulation.

---

## Files

| Path | Description |
|------|-------------|
| `packages/opusTomo/opusPatches/` | 4 bug patches (CTF, HEALPix, --split, dummy CTF header) |
| `packages/opusTomo/scripts/` | Classification runner + evaluation |
| `packages/opusTomo/runClassification.sh` | Main wrapper script |
| `packages/opusTomo/research.md` | Detailed setup notes, bugs, env rebuild |
| `results/opus_tomo_k2.csv` | Per-particle k=2 class assignments |
| `scripts/eval/extract_opus_tomo_classes.py` | Extraction script |

**Software:** OPUS-TOMO cloned to `~/opusSrc/opusTOMO` (patched). Env: `opuset`.
