# OPUS-TOMO

**Algorithm:** Variational autoencoder (VAE) continuous latent-space clustering  
**Environment:** `opuset` conda env (rebuilt 2026-06-05, cu128 PyTorch for RTX 5080 / CUDA 13.2)  
**Status:** ✅ T4P K=2 complete (cylindrical r=12 mask + skip-align) · ✅ FM_easy K=3 complete (ARI=0.021)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | K=8 / K=2 | cylindrical r=12, Y-axis (6.0%) | — (no GT) | **438 / 234** | Cylindrical mask + skip-align (orientation search OFF); reproduces the earlier ~2-population split. Val SNR²≈3.7. See `HANDOFF.md` + `T4P/research.md` |
| **FM_easy** | ✅ | K=3 / K=3 | threshold (28.3%) | **0.021** | 479/130/85 | Class C 100% isolated; A/B unseparated |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> **Mask note (updated):** **T4P** now uses a **cylindrical mask** (r=12, Y-axis, 6.0% voxels)
> and classifies cleanly (438/234) **when the in-training orientation search is disabled**
> (`train_skipalign.py`). An earlier, much tighter cylinder (2.7% voxels) *with the search ON*
> collapsed the VAE (668/4), which had been recorded as a package-wide "threshold-mask-required"
> constraint — that constraint does **not** hold for T4P once the search is off and the cylinder
> is on the correct (Y) axis. Other datasets here (e.g. FM_easy) still use threshold masks
> (28–31% voxels). See `T4P/research.md` (Steps 3–4) and `docs/datasets.md` §Per-Package Key Parameters.

> T4P to-do: re-run with K=3 (2+junk) per protocol and compute ARI vs PEET soft GT.

---

## Key Findings

- T4P: a cylindrical r=12 (Y-axis, 6.0% voxels) mask + disabling the in-training orientation search (`train_skipalign.py`) gives a clean K=2 split (438/234), val SNR²≈3.7.
- The earlier "VAE needs a broad (>25%) mask; tight cylinder collapses it" finding was an artifact of leaving the orientation search ON (and a too-tight 2.7% / wrong-axis cylinder) — it does not hold once the search is off. FM_easy still uses a threshold mask.
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
| `HANDOFF.md` | Top-level index for the T4P + opusPatches hand-off package |
| `opusPatches/` | 2 patched opusTomo source files (`models.py`, `pose.py`) + README; copy into `cryodrgn/` then `pip install -e .` |
| `T4P/scripts/` | Pipeline scripts 01–08, `train_skipalign.py`, runClassification.sh |
| `T4P/output/` | Tier-1 results (native opusTomo layout): config/split/z, `analyze.19/kmeans2/` (volumes + class averages), `split_star/` particle lists, mask.mrc, particles.star, pose_euler.pkl |
| `T4P/research.md` | Full replication doc (env, steps, bugs, results, what-to-share) |
| `FM_easy/scripts/` | FM_easy setup and runner scripts |
| `FM_easy/results/opus_project_motor_easy/` | FM_easy run outputs |
| `FM_easy/results/output/` | Additional FM_easy outputs |
| `outputs/FM_easy/opus/` | FM_easy prediction CSV and confusion PNG |
| `research.md` | Setup notes, bug patches, env rebuild |
| **Software:** `~/opusSrc/opusTOMO` | Patched source (not in repo). Env: `opuset`. |
