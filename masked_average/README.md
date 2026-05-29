# Mask-Normalized Subtomogram Average

## What was done

Standard subtomogram averages normalize contrast across the entire 80³ box. When a bright or
dark object outside the T4P pilus sits in the box it dominates the contrast stretch and washes
out detail in the pilus itself.

To address this, a binary cylindrical mask (`T4P_mask/cylindrical_mask.npy`) that tightly
encloses the T4P pilus was used to re-normalize each subtomogram before averaging:

1. **Load** the cylindrical mask (80³, ~10,025 active voxels, 1.96% of box volume).
2. **For each of the 672 subtomograms**: compute mean (μ) and standard deviation (σ) using
   only the voxels inside the mask, then z-score the whole volume:
   `normed = (volume − μ) / σ`
   This anchors the contrast stretch to the pilus density rather than background artifacts.
3. **Average** all 672 normalized volumes element-wise.
4. **Save** the result as `masked_average.mrc` (local only — too large for GitHub).
5. **Compare** quantitatively and visually against `PyTom/starting_average.mrc`.

## Results

| Metric | Starting average | Masked average |
|--------|-----------------|----------------|
| In-mask std | 1.672 | 0.325 |
| In-mask / out-mask std ratio (SNR proxy) | 0.899 | 0.927 |
| SNR improvement | — | **1.032×** |

The modest numerical improvement (3.2%) is expected given the alignment was already high
quality. Visual inspection of the comparison figure shows whether the cylindrical density is
sharper or more symmetric in the masked average.

## Files

| File | Description |
|------|-------------|
| `masked_average.py` | Script to reproduce the average — run with `pytom_env` |
| `masked_average_comparison.png` | Side-by-side figure: starting average vs masked average (3 orthogonal slab views each + difference row) |
| `masked_average.mrc` | Output average — **local only**, not committed (large binary) |

## How to re-run

```bash
~/conda-envs/pytom_env/bin/python3 STA/masked_average/masked_average.py
```

Requires `mrcfile`, `numpy`, `matplotlib` (all present in `pytom_env`).
Reads from `STA/subtomos_mrc/`, `STA/T4P_mask/`, and `STA/PyTom/`.
Writes `masked_average.mrc` and `masked_average_comparison.png` into this directory.
