# RELION

**Algorithm:** Soft EM (3D maximum-likelihood classification with gold-standard FSC regularization)  
**Environment:** `relion-5.0` conda env  
**Status:** ✅ T4P exhausted (confirmed algorithm-level failure) · ✅ motor_easy run (GT-seeded ARI=0.380, then collapses)

---

## Results

### T4P Real Dataset (672 particles)

| Config | k | Result | ARI | Notes |
|--------|---|--------|-----|-------|
| cylindrical mask | 2–4 | 672/0 at iter 1 | ≈0 | |
| tuned (ini_high=30, diam=500, firstiter_cc) | 2–4 | 672/0 at iter 1–2 | ≈0 | |
| random init | 2–4 | 672/0 at iter 1–2 | ≈0 | |
| PEET-seeded | 2–4 | 672/0 | −0.03 | Seeding from PEET GT does not help |
| PEET-seeded + orientation search | 2–4 | 672/0 | ≈0 | |
| 694-particle GT-seeded (iter 1) | 3 | — | **0.380** | Collapses to 0.099 at iter 2 |

**Canonical result: ARI≈0.** Root cause: per-particle SNR too low for EM CC discrimination.
Soft EM initialization places all K classes at the global average → diverges in 2 iterations.
No parameter fix is possible at this SNR level.

### Synthetic — motor_easy (694 particles)

| Config | k | ARI iter 1 | ARI iter 2 | Notes |
|--------|---|-----------|-----------|-------|
| v3 GT-seeded (firstiter_cc + skip_align + tau=8) | 3 | **0.380** | 0.099 | GT seeding gives upper bound at iter 1; collapses after |
| blind (k3_wedge, no seeding) | 3 | 0.006 | — | Canonical blind result |

`--skip_align` is correct for pre-aligned identity-pose particles. GT-seeded ARI=0.380 is an
upper bound showing the signal is present but EM cannot maintain the separation.

---

## Key Findings

- RELION soft EM consistently fails on low-SNR sparse-particle CryoET data (T4P, 672 particles).
- Even GT-seeded runs collapse to near-chance by iteration 2 — the algorithm smooths away the signal.
- motor_easy GT-seeded ARI=0.380 at iter 1 shows the signal exists; EM just cannot exploit it.
- This is an algorithm-level finding, not a configuration issue.

---

## Next Steps

- Re-run motor_easy after class C re-simulation (new `class_C_noRodHook.mrc`).
- No further T4P parameter search — exhausted.

---

## Files

| Path | Description |
|------|-------------|
| `scripts/data_prep/build_relion_star.py` | Build T4P STAR file for RELION |
| `scripts/data_prep/build_relion_motor_easy.py` | Build motor_easy STAR file |
| `scripts/run_relion_motor_easy_v2.sh` | motor_easy runner v2 |
| `scripts/run_relion_motor_easy_v3.sh` | motor_easy runner v3 (GT-seeded, canonical) |
| `outputs/relion/` | T4P classification run outputs |
| `outputs/relion_motor_easy/` | Synthetic run outputs; solvent_mask.mrc (r=32px, Y-10); class_refs.star |
| `results/synthetic_scores.csv` | ARI/AMI/V-measure scores |
| `docs/Relion-algorithm-use.md` | RELION algorithm documentation |
