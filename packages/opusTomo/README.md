# OPUS-TOMO

**Algorithm:** Variational autoencoder (VAE) continuous latent-space clustering  
**Environment:** `opuset` conda env (rebuilt 2026-06-05, cu128 PyTorch for RTX 5080 / CUDA 13.2)  
**Status:** ✅ T4P K=2 complete (threshold mask) · ✅ FM_easy K=3 complete (ARI=0.021)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | K=3 / K=2 | threshold (31.2%) | — (no GT) | **447 / 225** (+junk pending) | Matches Dynamo split; threshold mask required (cyl collapses VAE) |
| **FM_easy** | ✅ | K=3 / K=3 | threshold (28.3%) | **0.021** | 479/130/85 | Class C 100% isolated; A/B unseparated |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> **Mask exception:** OPUS-TOMO uses a **threshold mask** for all datasets (not the cylindrical v2
> used by other packages). The cylindrical mask (2.7% voxels) is too restrictive for the VAE
> reconstruction loss — causes classification collapse (668/4 split on T4P). The threshold mask
> covers 28–31% of voxels. This is a documented package-level constraint, not an error.
> See `docs/datasets.md` §Per-Package Key Parameters for full context.

> T4P to-do: re-run with K=3 (2+junk) per protocol and compute ARI vs PEET soft GT.

---

## Key Findings

- OPUS-TOMO succeeds with threshold mask — K=2 T4P split (447/225) matches Dynamo reference.
- VAE requires broad masks (>25% voxels); tight cylindrical mask prevents learning latent structure.
- FM_easy: Class C fully isolated (100% capture) but A/B distinction not resolved (ARI≈0).
- 4 bugs were patched before any runs could complete (CTF, HEALPix, `--split`, dummy CTF header).

---

## Next Steps

- Re-run T4P with K=3 (2+junk) per protocol.
- Compute ARI vs PEET soft GT for T4P K=2 threshold-mask result.

---

## Files

| Path | Description |
|------|-------------|
| `opusPatches/` | 4 bug patches (CTF, HEALPix, `--split`, dummy CTF header); apply to `~/opusSrc/opusTOMO/` |
| `T4P/scripts/` | Pipeline scripts 01–08, runClassification.sh |
| `T4P/configs/` | consensus.mrc, mask.mrc, particles.star, pose_euler.pkl |
| `FM_easy/scripts/` | FM_easy setup and runner scripts |
| `FM_easy/results/opus_project_motor_easy/` | FM_easy run outputs |
| `FM_easy/results/output/` | Additional FM_easy outputs |
| `outputs/FM_easy/opus/` | FM_easy prediction CSV and confusion PNG |
| `research.md` | Setup notes, bug patches, env rebuild |
| **Software:** `~/opusSrc/opusTOMO` | Patched source (not in repo). Env: `opuset`. |
