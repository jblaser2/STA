# T4P Mask and Global Average

Reference mask and global particle average for the T4P (*Vibrio*) subtomogram dataset used in the STA classification benchmark.

---

## Contents

| File | Committed | Description |
|------|-----------|-------------|
| `cylindrical_mask.em` | yes | Binary cylindrical mask in PyTom EM format |
| `cylindrical_mask.npy` | yes | Same mask as NumPy array (used by napari viewer) |
| `starting_average.npy` | yes | Global average of all 672 subtomograms as NumPy array |
| `starting_average.mrc` | no (gitignored) | Same average in MRC format — regenerate with `compute_starting_average.py` |
| `generate_cylindrical_mask.py` | yes | Script to regenerate the mask with any parameters |
| `compute_starting_average.py` | yes | Script to recompute the global average from raw subtomograms |
| `view_average_mask.py` | yes | Napari viewer: opens average + mask overlaid |

---

## Dataset

- **Organism:** *Vibrio cholerae* T4P (Type IV Pili)
- **Particles:** 672 hand-picked, pre-aligned subtomograms
- **Box size:** 80 × 80 × 80 voxels
- **Pixel size:** 13.328 Å/vox
- **Raw data:** `STA/subtomos_mrc/` (local only, gitignored)

---

## Cylindrical Mask

The mask covers the T4P pilus density in each subtomogram. The pilus filament axis runs along **Y**; the circular cross-section is in the **XZ** plane.

**Current parameters:**

| Parameter | Value | Physical size |
|-----------|-------|---------------|
| Radius (XZ) | 11.2 vox | ~149 Å |
| Extent +Y from center | 9.8 vox | ~131 Å |
| Extent −Y from center | 15.8 vox | ~211 Å |
| Total height | 25.6 vox | ~341 Å |
| Active voxels | 10,025 / 512,000 | ~2% of box |

The asymmetric Y extent reflects the actual density distribution of the T4P structure relative to the box center.

This mask is used for **both** the alignment mask (`-m`) and the focus classification mask (`-c`) in PyTom `auto_focus_classify.py`, and can be adapted for other packages.

### Regenerating the mask

```bash
conda run -n pytom_env python generate_cylindrical_mask.py \
  --height_pos 9.8 --height_neg 15.8 --radius 11.2 \
  --output cylindrical_mask
```

To adjust geometry, use `--height_pos`, `--height_neg`, and `--radius`. Run with `--help` for all options.

---

## Global Average (starting_average)

The straight arithmetic mean of all 672 subtomograms with no alignment refinement or classification applied. Useful as a sanity check that particles are coherently oriented and as a reference for mask placement.

### Regenerating the average

Requires access to the raw subtomograms at `STA/subtomos_mrc/` (local only):

```bash
conda run -n pytom_env python compute_starting_average.py
```

---

## Viewing the average and mask in napari

Requires the `napari-0.4-env` conda environment:

```bash
conda run -n napari-0.4-env python view_average_mask.py
```

This opens a napari viewer with:
- **`global_average`** — gray colormap
- **`cylindrical_mask`** — green additive overlay at 40% opacity

Use the Z-slice slider to step through the volume. Toggle layer visibility with the eye icon to compare the mask boundary against the T4P density.
