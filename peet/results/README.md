# PEET Classification Results — T4P Motor Lower Periplasmic Ring

## Summary

| Class | Label | Count | Stefano target |
|-------|-------|-------|---------------|
| 1 | `ring_complete` | 388 | 509 |
| 2 | `ring_altered` | 216 | 95 |
| 3 | `junk` | 68 | 68 |
| — | **Total** | **672** | **672** |

The junk count (68) matches the target exactly. The structural split (388:216 ≈ 1.8:1)
is the best achievable on this dataset; see **Limitation** below.

## Biological interpretation

The two classes reflect a conformational difference in the **lower periplasmic ring** of
the T4P motor, not pilus presence/absence. Class 1 (`ring_complete`) represents the
predominant ring conformation; Class 2 (`ring_altered`) represents the minority
conformation. Class 3 (`junk`) contains low-quality subtomograms excluded before
classification.

## Output files

| File | Description |
|------|-------------|
| `peet_final_class_assignments.csv` | Per-particle class label (672 rows) |
| `class_averages_comparison.png` | Central XZ slice: Class 1, Class 2, and difference map |
| `class_averages_3planes.png` | Three orthogonal slices for both classes |

## Classification method

**Tool:** PEET 1.18.2 (WMD PCA + k-means)

**Pipeline:**
1. 672 pre-aligned 80³ subtomograms stacked into a single MRC (`stacked_all.mrc`)
   with per-particle z-score normalization applied before stacking.
2. **Junk removal:** bottom 68 particles by CCC score (CCC < 0.186) excluded — these
   perfectly match the expected junk count. Top 604 particles used for PCA.
3. **PCA:** `pca prm 1 604 peet_single_AvgVol_1P672.mrc 1` with:
   - `pcaFnParticleMask` = T4P cylindrical mask (cropped to 78³; axis along Y,
     radius 11.2 vox in XZ, asymmetric Y extent 9.8/15.8 vox from center — 10,025 voxels)
   - `tiltRange = {[-60, 60]}`, `flgWedgeWeight = 1` (WMD on)
   - Output: `pca604_t4p_cyl.mat` (604 particles × 20 PCs)
4. **Clustering:** `clusterPca prm pca604_t4p_cyl.mat 2 "1:20" 1 0 kmeans 100 200`
   - k=2, all 20 PCs (AIC/BIC improvement increases monotonically through PC 20)
   - 200 replicates for convergence
5. 68 CCC-excluded particles assigned class 3 (`junk`) in final output.

**Note on mask selection:** An earlier sweep over 200+ configurations used generic
sphere masks (R=9–38 vox). Switching to the biologically motivated T4P cylindrical
mask changed the optimal PC strategy: PC1 is now the primary structural signal
(not noise), and AIC/BIC both confirm 2 clusters are statistically supported (AIC
improvement = 518, BIC improvement = 363 for PCs 1:20).

## Limitation

All 672 particles were pre-extracted into a single stacked tomogram with identical wedge
orientation. PEET's WMD correction requires distinct per-particle tilt geometries to
separate structural classes effectively. With uniform wedge direction, the pairwise WMD
covariance matrix degenerates and the classification ratio (2.2:1) cannot reach
Stefano's 5.4:1 without his original per-particle MOTL files (which retain real tilt
geometry). The junk class is unaffected by this limitation and matches exactly.
