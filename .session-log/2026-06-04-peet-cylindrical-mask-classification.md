# 2026-06-04 — PEET T4P classification with T4P cylindrical mask

## Goal
Re-run PEET classification on 672 T4P subtomograms using the biologically motivated T4P
cylindrical mask (from `T4P_mask/`) instead of generic sphere masks, aiming to separate
the lower periplasmic ring conformational change. Generate publication-quality comparison
figures vs Stefano's reference panels.

## What happened

### Sweep over generic sphere/cylinder masks (comprehensive)
- Identified **68 junk particles** via CCC threshold (bottom 10.1% by CCC < 0.186) — exact match
  to Stefano's junk count.
- Ran 200+ configurations: sphere R=9–38 vox, cylinder r=8–25 vox, PC ranges 1:3–2:20, WMD
  on/off, 604p vs 672p, 30–200 k-means reps.
- Best sphere result: **R=25, PCs 2:10, 100-rep → [414, 190, 68] dist=190** from target 509:95:68.
- Key finding: skipping PC1 (using PCs 2:X) helped for sphere masks — PC1 captured noise.

### Switch to T4P cylindrical mask (mask v1)
- Cropped `T4P_mask/cylindrical_mask.npy` (80³) to 78³ for PEET's `pcaFnParticleMask`.
- Params: radius=11.2 vox, height_pos=9.8, height_neg=15.8 → 10,025 active voxels.
- Sweep result: **PCs 1:20 (all 20), 200-rep → [388, 216, 68]**. AIC improvement=518, BIC=363.
  With cylindrical mask PC1 IS the signal (positive AIC with PC1; negative without).
- Saved to `saved_runs/cylindrical_v1_388_216_68/`, pushed as `peet_final_class_assignments.csv`.

### New mask v2 (user-designed)
- User requested: radius 13 vox, height_pos=0 (flush at center), height_neg=25 vox — captures
  only the below-center motor region (lower periplasmic ring focus).
- Generated preview image overlaid on starting average; user approved.
- Sweep result: **PCs 1:20, 200-rep → [374, 230, 68]**. AIC=659, BIC=504 (best AIC so far).
- Saved to `saved_runs/cylindrical_v2_374_230_68/`, pushed as `peet_final_class_assignments_v2.csv`.

### Figures generated
- `class_averages_v2_masked_xy_diff.png`: full 80×80 XY slice, green box showing mask v2 extent,
  full difference map. User: "That is perfect."
- `comparison_stefano_v1_v2.png`: Stefano reference panels (F/G, 509/95/68) alongside v1 and v2
  class averages, portrait crop, matched style. User: "Those look good."
- All class labels use `ring_complete` / `ring_altered` / `junk` (not piliated/non_piliated).

## Files changed (all pushed to GitHub)
- `peet/results/peet_final_class_assignments.csv` — v1, ring_complete=388, ring_altered=216, junk=68
- `peet/results/peet_final_class_assignments_v2.csv` — v2, ring_complete=374, ring_altered=230, junk=68
- `peet/results/README.md` — updated counts and method description
- `peet/results/class_averages_v2_masked_xy_diff.png` — full XY slice + green mask box
- `peet/results/class_averages_masked_xy_diff.png` — v1 masked difference
- `peet/results/comparison_stefano_v1_v2.png` — side-by-side comparison
- `peet/results/mask_v2_preview.png` — mask geometry preview

Local only (not committed):
- `~/Research/peet/results/saved_runs/cylindrical_v1_388_216_68/` — full v1 run backup
- `~/Research/peet/results/saved_runs/cylindrical_v2_374_230_68/` — full v2 run backup
- `~/Research/peet/results/pca604_t4p_cyl.mat` — v1 PCA mat
- `~/Research/peet/results/pca604_t4p_cyl_v2.mat` — v2 PCA mat
- `~/Research/peet/results/mask_t4p_cylindrical_78.mrc` — v1 mask (78³)
- `~/Research/peet/results/mask_t4p_cyl_v2_78.mrc` — v2 mask (78³)

## Where I stopped
Both mask runs complete, figures pushed, session ended. The v2 run (mask below center, r=13)
gave the best AIC/BIC (659/504) and the most visually convincing difference map per user.

## Next step
1. **Email Stefano** for his PEET MOTL files — still the only path to exact per-particle GT labels.
   Without them, Dynamo HAC (447:225) remains the proxy GT.
2. Potentially try additional mask geometries if Stefano's feedback warrants it.
3. Move on to running remaining packages (EMAN2 k=3/4, STOPGAP via Eben) against the v2
   class assignments as soft ground truth.
