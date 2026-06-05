# 2026-06-05 — T4P masked re-runs: PyTom success, RELION failure diagnosed

## Goal
Re-run failing T4P packages with the PEET v2 cylindrical mask (r=13, h_pos=0, h_neg=25)
to see if the signal missing from their original runs was due to the wrong mask.
Understand RELION's soft EM collapse and determine whether any parameter combination
can recover the T4P class separation.

---

## What happened

### Mask regeneration
- Regenerated `PyTom/cylindrical_mask.{em,mrc,npy}` with v2 params (r=13, h_pos=0, h_neg=25, box=80)
  via `conda run -n pytom_env python PyTom/generate_cylindrical_mask.py --radius 13 --height_pos 0 --height_neg 25 --box 80`
- Copied MRC to `T4P_mask/cylindrical_mask_v2.mrc` for RELION use
- Previous defaults (r=7.2, symmetric ±8.8) overwritten — the v2 geometry is now canonical

### PyTom auto_focus_classify — SUCCESS
- Discovered `-a` flag required: `_swig_frm` FRM compiled extension absent from pytom_env → MPI_ABORT without it. Pre-aligned particles (zero poses) make this scientifically correct.
- **k=2:** `mpirun -np 16 auto_focus_classify.py -k 2 -f 20 -m/-c cylindrical_mask.em -b 1 -i 15 -a -o autofocus_v2mask_k2/` → **440/232, converged iter 5** (2 particles changed). Class 1 (232) ≈ PEET ring_altered (230).
- **k=3:** same command, `-k 3` → **422/150/100, converged iter 11**
- Previous runs (autofocus_output/, autofocus_output_k2/) used wrong mask (r=7.2 symmetric) — that was the failure cause, not the algorithm.
- Results: `results/pytom_v2mask_k2.csv`, `results/pytom_v2mask_k3.csv`
- Figures: `PyTom/figures_v2mask_k{2,3}/` (clustering_map + class central slices)

### RELION T4P — algorithm failure fully diagnosed
Five configurations, all collapse to 672/0 by iter 1–2:

| Config | Result |
|---|---|
| + cylindrical mask (solvent_mask) | 672/0 |
| + ini_high=30, diameter=500, firstiter_cc (single ref) | 672/0 at iter 1 (all refs identical → CC tiebreak) |
| No --ref (random init [336/336]) + all fixes | 672/0 at iter 1 |
| PEET-seeded (PEET class avgs as starting refs) + all fixes | iter1: [42/630], iter2: 672/0; ARI=−0.03 vs PEET soft GT |
| PEET-seeded + no --skip_align (orientation search) | **still running** in tmux:sta:relion_noalign |

**Root cause:** Per-particle SNR too low for per-particle CC to be discriminative.
Soft EM Matthew effect: whichever class gets more particles at iter 1 produces a better
average → attracts even more particles → other class empties in 1 iter. This is
algorithm-level, not fixable by parameters.

**Cross-tab (PEET-seeded iter 1 vs PEET v2 soft GT, n=604):**
- RELION class 1: 38 ring_complete, 0 ring_altered
- RELION class 2: 336 ring_complete, 230 ring_altered
ARI = −0.03 (worse than chance)

### New scripts and files
- `scripts/data_prep/run_relion_class3d_masked.sh` — adds --solvent_mask to baseline
- `scripts/data_prep/run_relion_class3d_tuned.sh` — ini_high=30, diameter=500, firstiter_cc + mask
- `scripts/data_prep/run_relion_class3d_noref.sh` — random init + all fixes
- `scripts/data_prep/run_relion_class3d_peet_seed.sh` — PEET class avgs as --ref
- `scripts/data_prep/run_relion_class3d_noalign.sh` — PEET-seeded + orientation search (currently running)
- `scripts/data_prep/make_peet_seed_model.py` — creates RELION model.star seeded from arbitrary MRC refs
- `scripts/eval/extract_pytom_classes.py` — PyTom classified XML → predictions CSV (numeric iter sort)
- `outputs/relion/Class3D/peet_seed_model.star` — 2-class seed pointing to PEET v2 class avgs
- `PyTom/instructions.md` — updated: -a flag note, v2 mask params, v1 vs v2 history

---

## Files changed (repo)

| File | Change |
|---|---|
| `STATUS.md` | New bullet for T4P masked re-runs; GROUND TRUTH bullet updated; RELION + PyTom matrix rows updated |
| `PyTom/cylindrical_mask.{em,mrc,npy}` | Regenerated with v2 params (overwrites defaults) |
| `T4P_mask/cylindrical_mask_v2.mrc` | NEW — v2 mask for RELION |
| `PyTom/instructions.md` | -a flag note + v2 mask params |
| `scripts/data_prep/run_relion_class3d_{masked,tuned,noref,peet_seed,noalign}.sh` | NEW |
| `scripts/data_prep/make_peet_seed_model.py` | NEW |
| `scripts/eval/extract_pytom_classes.py` | NEW |
| `results/pytom_v2mask_k2.csv` | NEW — 440/232 final assignments |
| `results/pytom_v2mask_k3.csv` | NEW — 422/150/100 final assignments |
| `outputs/relion/Class3D/peet_seed_model.star` | NEW — PEET-seeded init model |
| `outputs/relion/Class3D/k2_wedge_{masked,tuned,noref,peet_seed}/` | NEW run dirs + logs |

---

## Where I stopped
- RELION no-align run (PEET-seeded + orientation search, k=2) still running in `tmux:sta:relion_noalign`
- PyTom k=4 not yet run (not prioritized)
- OPUS-TOMO with cylindrical mask not yet started

## Next step
1. Check relion_noalign result when done (tmux:sta:relion_noalign)
2. OPUS-TOMO with cylindrical mask: uncomment cylinder code in `opusTomo/scripts/03_make_mask.py`, retrain VAE
3. Optionally: EMAN2 k=3/k=4 (quick run, just needs more iterations)
