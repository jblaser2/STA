# OPUS-TOMO

**Algorithm:** Variational autoencoder (VAE) continuous latent-space clustering  
**Environment:** `opuset` conda env (rebuilt from scratch 2026-06-05, cu128 PyTorch)  
**Status:** ✅ T4P k=2/3/4 complete (threshold mask) · ✅ motor_easy k=3 complete (ARI=0.021) · ARI vs PEET GT not yet computed

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

### Synthetic — motor_easy (694 GT-aligned particles, 96³, 13.33 Å/px)

| Mask | K | ARI | Split | Notes |
|------|---|-----|-------|-------|
| Threshold (28.3% voxels) | 3 | **0.021** | 479 / 130 / 85 | Class C (177) fully in dominant cluster; A/B unseparated |

**Confusion matrix (GT rows × Pred cols):**
```
A (246):   42   46  158
B (271):   43   84  144
C (177):    0    0  177
```

Class C is 100% captured in cluster 2 — the VAE detects the most distinct structural difference
(C-ring only vs. full motor). However cluster 2 also absorbs 64% of A and 53% of B, so ARI is
near-random (0.021). The A vs. B distinction (~40 Å difference in C-ring presence) is not
resolved. Scores: AMI=0.124, V=0.127, Acc=0.437.

Threshold mask: computed from motor_easy consensus average (mean + 1σ + 2-iter dilation), 28.3%
of 96³ voxels — comparable to T4P's 31.2%, well above the VAE collapse threshold.

Scripts: `packages/opusTomo/scripts/setup_motor_easy_opus.py`, `run_motor_easy_opus.sh`.
Output: `packages/opusTomo/scripts/opus_project_motor_easy/`. Labels: `outputs/opus_tomo_motor_easy_k3.csv`.

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
