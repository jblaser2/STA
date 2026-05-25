# Dynamo Classification — Final Results

Optimal classification of 672 pre-aligned cryo-ET subtomograms using Dynamo's HAC pipeline.
These results are intended for comparison against other classification packages.

---

## Parameters

| Parameter | Value |
|-----------|-------|
| Package | Dynamo v1.1.558 |
| Algorithm | HAC (Hierarchical Ascending Classification) |
| Particles | 672 |
| Box size | 80³ voxels |
| Pixel size | 13.328 Å/vox |
| Mask | Spherical, radius **7.2 voxels** (95.96 Å) |
| Linkage | Ward |
| Distance metric | 1 − Pearson CC (no missing-wedge correction) |
| N classes | 2 |
| Cophenetic correlation | **0.3727** |

The mask radius r=7.2 was selected by sweeping r=3–25 in steps of 1 (coarse) and r=7.0–9.0 in steps of 0.2 (fine), maximising the cophenetic correlation coefficient. See `../dynamo_outputs/hac_sweep_fine/summary/` for the full sweep results.

Missing-wedge correction was not applied because the original tomogram acquisition geometry was not available. Particles were pre-aligned prior to classification.

---

## Files

| File | Description |
|------|-------------|
| `class_averages/class_01.mrc` | Average density map, Class 1 |
| `class_averages/class_02.mrc` | Average density map, Class 2 |
| `class_comparison.png` | XY central slice, side by side, with FSC resolution labels |
| `embedding_umap.png` | UMAP of the 672×672 CC matrix, coloured by class |
| `embedding_tsne.png` | t-SNE of the 672×672 CC matrix, coloured by class |
| `embedding_coords.csv` | Per-particle: class, UMAP coords, t-SNE coords |
| `ccmatrix.npy` | Raw 672×672 Pearson CC matrix (float32 NumPy) |
| `class_assignments.csv` | Per-particle class label |
| `fsc/fsc_class01.txt` | FSC curve for Class 1 (split-half) |
| `fsc/fsc_class02.txt` | FSC curve for Class 2 (split-half) |
| `fsc/fsc_curves.png` | FSC curves plot with resolution markers |
| `fsc/resolution.txt` | Resolution table (FSC=0.5 and FSC=0.143) |
| `parameters.json` | All parameters, machine-readable |
| `view_classes.py` | Napari viewer — opens both class averages side by side |

---

## Class Sizes

| Class | Particles | Fraction |
|-------|-----------|----------|
| Class 1 | 192 | 28.6% | 96.9 Å (FSC=0.5) |
| Class 2 | 480 | 71.4% | 62.7 Å (FSC=0.5) |

Both classes reach 26.7 Å at FSC=0.143 (Nyquist for this box/pixel size).
See `fsc/fsc_curves.png` and `fsc/resolution.txt` for full details.

---

## Viewing the Class Averages

**Napari (interactive):**
```bash
DISPLAY=:0 QT_QPA_PLATFORM=xcb \
  /home/jblaser2/conda-envs/napari-0.4-env/bin/python3 \
  view_classes.py
```
Requires napari 0.4.19 environment. The viewer opens both classes side by side in XY, with pixel size set (13.328 Å/vox), so the scale bar reflects real space.

**IMOD / 3dmod:**
```bash
3dmod class_averages/class_01.mrc class_averages/class_02.mrc
```

---

## Loading the CC Matrix

```python
import numpy as np
cc = np.load('ccmatrix.npy')   # shape (672, 672), float32
dist = 1.0 - cc                # Pearson distance matrix
```

## Loading Embedding Coordinates

```python
import pandas as pd
df = pd.read_csv('embedding_coords.csv')
# columns: particle, class, umap1, umap2, tsne1, tsne2
```

---

## Notes for Cross-Package Comparison

- The CC matrix (`ccmatrix.npy`) is the fundamental pairwise similarity computed by Dynamo. Other packages may use different similarity measures; the CC matrix here is **not** wedge-corrected.
- `embedding_coords.csv` allows direct overlay of other packages' class labels onto the Dynamo embedding space.
- The cophenetic correlation (0.3727) is modest — the two classes are not sharply separated in CC-space. This is expected for similar pili conformations at this resolution.
- Resolution estimates are split-half FSC (not gold-standard half-maps), providing a rough reproducibility measure rather than a true structural resolution.
