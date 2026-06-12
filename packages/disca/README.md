# DISCA

**Algorithm:** Template-free deep unsupervised clustering (pytorch)  
**Environment:** `disca` conda env  
**Status:** ✅ T4P k=2/3/4 complete (masked + unmasked) — does NOT recover the two pili phases

---

## Results Summary

| Dataset | Status | k | Mask | ARI vs converging pkgs | Split | Notes |
|---------|--------|---|------|------------------------|-------|-------|
| **T4P** | ✅ | k=2 | none | — | ~630/42 | Collapses to ~94% dominant class (trivial solution) |
| **T4P** | ✅ | k=2 | cyl v2 (r=13, h_neg=25) | ≈0 (PEET −0.002, Dynamo −0.001, PyTom −0.003) | **398/274** | Balanced split, but uncorrelated with the conformational axis |
| **T4P** | ✅ | k=3 | cyl v2 | ≈0 | 315/90/267 | — |
| **T4P** | ✅ | k=4 | cyl v2 | ≈0 | 94/311/212/55 | — |
| **FM_easy** | ⬜ | k=3 | — | — | — | Lower priority given T4P result |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> **Masking changes the failure mode but not the conclusion.** Without a mask DISCA collapses to a
> trivial ~94% dominant class. With the cylindrical v2 mask (same mask used for PyTom/PEET/OPUS-TOMO)
> it produces a *balanced* 398/274 split — but that split is uncorrelated with the two-phase ground
> truth (ARI ≈ 0 vs PEET/PyTom/Dynamo). Notably DISCA's split agrees strongly with **OPUS-TOMO**
> (ARI = 0.678): both deep-learning methods cluster on a contrast/intensity axis rather than the
> conformational axis that the template/CC methods (PEET, PyTom, Dynamo) recover.

---

## Key Findings

- Template-free deep clustering does not recover the two pili phases at this SNR, masked or unmasked.
- Unmasked: trivial ~94% dominant-class collapse. Masked: balanced split on the wrong (contrast) axis.
- DISCA and OPUS-TOMO (the two learned-feature methods) agree with each other (ARI 0.678) but neither
  agrees with the alignment/CC-based converging cluster — a clean benchmark signal that learned
  features without an alignment-based focus default to a non-conformational discriminant.

---

## Next Steps

- FM_easy: run k=3 when bandwidth allows (lower priority given the T4P result).

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/disca_k2_classes.png` | k=2 result figure (unmasked) |
| `T4P/results/RESULTS.md` | Run notes and output details |
| `research.md` | Package notes, installation, run commands |
| `scripts/data_prep/build_disca_input.py` | Input prep (now supports `--mask`) |
| `scripts/data_prep/run_disca_cyl_v2.sh` | Masked (cyl v2) run driver, k=2/3/4 |
| `scripts/eval/score_disca_t4p.py` | Builds assignment CSVs + pairwise ARI vs converging pkgs |
| `results/disca_cyl_v2_k{2,3,4}.csv` | Per-particle assignments (masked) |
