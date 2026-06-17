# RELION

**Algorithm:** Soft EM (3D maximum-likelihood classification with gold-standard FSC regularization)  
**Environment:** `relion-5.0` conda env  
**Status:** ✅ T4P exhausted (algorithm-level failure) · ✅ FM_easy 2-class hc: blind ARI=0.008 (GT-seeded 0.764 = supervised upper bound, not blind)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ (exhausted) | k=3 / k=2 | cyl v2 | ≈ 0 | 672/0 | Algorithm-level SNR failure; all 6 configurations collapse to global average |
| **FM_easy** (2-class hc, 542p) | ✅ | k=2 / k=2 | diff sphere | **0.008 (blind)** | 56/486 | Blind soft-EM near-collapse (global-avg init, no GT). GT-seeded iter1=**0.764**/acc 0.937 is a *supervised upper bound* (≈logreg 0.745), NOT blind — excluded from ranking. Confusion: `outputs/FM_easy/relion/run_k2_blind/` |
| FM_easy (old 3-class, 694p) | 🗄️ archived | k=3 | sphere | 0.475 (GT) / 0.006 (blind) | — | Superseded by 2-class hc set; archived in `outputs/FM_easy/_archive_3class_k3/` |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P canonical result: ARI≈0. Soft EM places all K classes at global average at initialization;
> diverges within 2 iterations. Root cause: per-particle SNR too low for EM CC discrimination.
> No parameter fix is possible. This is an algorithm-level finding, not a configuration issue.

> FM_easy best: GT-seeded iter 1 ARI=0.475 (upper bound only). Blind run ARI=0.006.
> Use `--skip_align` for pre-aligned particles.

---

## Key Findings

- RELION soft EM consistently fails on low-SNR sparse-particle CryoET data (T4P, 672 particles).
- Even GT-seeded runs collapse to near-chance by iteration 2 — the algorithm smooths away signal.
- FM_easy GT-seeded ARI=0.475 at iter 1 shows the signal exists; EM cannot maintain separation.
- 6 T4P configurations tested (cylindrical mask, tuned params, random init, PEET-seeded, etc.) — all fail.

---

## Next Steps

- No further T4P parameter search — confirmed exhausted.
- FM_easy: blind run (no GT seeding) complete. Document as canonical FM_easy result.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/scripts/` | STAR file builder, T4P runner scripts |
| `T4P/configs/` | Canonical T4P RELION config (k=3, cyl mask, documents the failure) |
| `FM_easy/scripts/` | FM_easy runner scripts (v2=blind, v3=GT-seeded) |
| `FM_easy/configs/` | STAR files, solvent mask (r=32px, Y-10 offset) |
| `outputs/T4P/relion/run_r01/` | T4P classification run outputs |
| `outputs/FM_easy/relion/run_r01/` | FM_easy run outputs; class_refs.star; solvent_mask.mrc |
| `docs/Relion-algorithm-use.md` | RELION algorithm documentation |
| `results/synthetic_scores.csv` | ARI/AMI/V-measure scores |
