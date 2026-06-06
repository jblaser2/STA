# PEET Classification: Internals and Design

Research notes from reading the PEET 1.18.2 man pages, parameter templates, release
history, and inspecting actual runtime outputs. Author: Claude Sonnet 4.6, 2026-05-27.

---

## 1. Classification in Context: Where It Fits in the Pipeline

PEET classification is always a **post-alignment step**. You must have at least one
completed alignment iteration before running PCA — the PCA operates on aligned
subvolumes (extracted and rotated/shifted according to the MOTL). The pipeline is:

```
prepareEM / initMOTL
      ↓
alignSubset × N_toms  (parallel, per tomogram)
      ↓
mergeEM  (collects TEMP files → Iter(n+1) MOTLs with CCC scores)
      ↓
averageAll  (grand average for reference)
      ↓
pca  (eigendecomposition of aligned particle stack)
      ↓
clusterPca  (k-means or HAC on PCA scores)
      ↓
usePcaMotiveLists  (activate class labels in active MOTLs)
      ↓
averageAll with selectClassID  (per-class averages)
```

Classification can be **repeated as many times as needed** on the same alignment
without re-running alignSubset — `clusterPca` just re-clusters the already-computed
`.mat` file.

---

## 2. The PCA Step (`pca` / `pcaSP`)

### Algorithm

PEET implements the **Wedge-Masked Difference (WMD) corrected covariance PCA**, first
published in:

> Heumann, J. et al. "Clustering and variance maps for cryo-electron tomography using
> wedge-masked differences." *J. Struct. Biol.* **175**:288–299 (2011).
> doi:10.1016/j.jsb.2011.05.011

**Method 1 (default, recommended)**: Full PCA with WMD correction.

For each particle *i*, compute the Wedge-Masked Difference:

```
WMD_i = particle_i ⊗ wedgeMask_ref  −  grandAverage ⊗ wedgeMask_i
```

where `⊗` denotes Fourier-domain masking with the missing wedge of the other party.
This compensates for the fact that different particles have differently oriented
missing wedges: subtracting a wedge-masked average prevents the missing-wedge artifact
from dominating the first principal components.

The WMD covariance matrix is then eigendecomposed. The `avgFilename` argument is the
grand average to subtract. **Omitting `avgFilename` disables WMD correction entirely
and is not recommended.**

**Method 2**: SVD of re-scaled cross-correlation. Less accurate, slower.

**Method 3**: SVD of constrained cross-correlation. Slightly less accurate than
method 1, but much slower.

### Inputs

```bash
pca prmFile iterationNumber numParticles [avgFilename] [autoclose]
```

- `iterationNumber` — which MOTL iteration to read particles from
- `numParticles` — number to include (selects top-CCC particles from MOTL)
- `avgFilename` — the WMD reference; use the output of `averageAll` at the same iter

### PRM-level parameters for `pca`

| Parameter | Default | Description |
|---|---|---|
| `pcaMethod` | 1 | 1=PCA+WMD (recommended), 2=rescaled CC SVD, 3=constrained CC SVD |
| `pcaSzSubvol` | szVol | Central sub-box to analyze. Can be smaller than szVol to focus on center |
| `pcaFnParticleMask` | (none) | MRC binary mask — restricts PCA to specific voxels |
| `pcaNumEigenimages` | 4 | How many eigenimage MRC files to save |
| `pcaMaxNumComponents` | 20 | Maximum PCs to save in the output .mat file |
| `flgNormalize` | 0 | If 1: z-score each particle before PCA (zero mean, unit variance) |
| `selectClassID` | [] | Restrict PCA to particles of these class IDs only |

> **Note on `pcaSzSubvol`**: This is the built-in equivalent of our manual z-score +
> mask approach. Setting `pcaSzSubvol` smaller than `szVol` focuses PCA on the
> central region of the subvolume, analogous to our `outsideMaskRadius = 9`.
> `pcaFnParticleMask` provides even finer control via an arbitrary binary mask.

> **Note on `flgNormalize`**: This is PEET's built-in z-score normalization, applied
> per-particle before PCA. In our single-stacked-tomogram workaround we performed
> z-scoring *before* stacking (in `create_single_tomo.py`). Setting `flgNormalize=1`
> in the prm would have been the cleaner alternative, but only works correctly when
> the multi-tomogram iteration bug is not a factor.

### Outputs

| File | Description |
|---|---|
| `pca{N}_{basename}.mat` | Main output: SVD matrices + PCA scores for all N particles |
| `eigenImage{1-4}.mrc` | Spatial maps of the first eigenvectors (high magnitude = variable voxel) |
| `pcaFig1.pdf` | Plot: fractional + cumulative sum of singular values vs component number |
| `pcaFig2.pdf` | Histogram of first 10 singular values |
| `pcaFig3.pdf` | Histograms of first 8 coefficient distributions |

### `.mat` file structure (HDF5)

Inspected from `pca672_peet_single.mat` (our 672-particle run, szVol=78^3):

| Key | Shape | Description |
|---|---|---|
| `U` | (20, 474552) | Left singular vectors — eigenvectors in voxel space (78^3 = 474552 flattened) |
| `S` | (20, 20) | Diagonal matrix of singular values |
| `V` | (20, 672) | Right singular vectors — per-particle projections, transposed |
| `coeffs` | (672, 20) | PCA scores per particle (= V^T × S); this is what clusterPca reads |
| `iterNum` | scalar | Alignment iteration used |
| `numParticles` | scalar | Number of particles analyzed |

The singular values on our dataset (first 10):

```
2108, 1721, 1594, 1508, 1367, 1283, 1161, 1098, 1029, 999
```

Variance explained per PC (σ² / Σσ²):

| PC | Var (%) | Cumulative (%) |
|---|---|---|
| 1 | 15.4 | 15.4 |
| 2 | 10.3 | 25.7 |
| 3 | 8.8 | 34.5 |
| 4 | 7.9 | 42.5 |
| 5 | 6.5 | 49.0 |

The relatively flat spectrum (no single dominant PC capturing >25%) is consistent with
structural variation spread across many modes, as expected for pre-aligned particles
with no brightness artifact.

### Memory and compute requirements

PEET's documentation states: "a fast, multi-core machine with **at least 32 GB of RAM**
is suggested for typical applications (e.g. 600 particles of size 140×140×140 voxels)."
Requirements scale roughly with `volume_size × num_particles`.

**Single-precision variant `pcaSP`**: functionally identical to `pca` but uses
single-precision arithmetic, cutting memory requirements by ~2×. Recommended when
memory is a bottleneck.

---

## 3. The Clustering Step (`clusterPca`)

### Algorithm

```bash
clusterPca prmFile matFilename nClusters features [autoclose] [flgPdf] [method] [maxIter] [nReplicates]
```

Reads the `coeffs` matrix from the `.mat` file and runs:
- **K-means** (`method = 'kmeans'`, default): minimizes intra-cluster variance.
  Runs `nReplicates` (default 10) times with different random seeds and keeps the
  best result. `maxIter` (default 100) controls convergence per replicate.
- **HAC** (`method = 'hac'`, available since v1.15.0): hierarchical ascendant
  clustering. More deterministic than k-means but slower for large datasets.

The `features` argument selects which PCs to use. Examples:
- `"1:10"` — use PCs 1 through 10
- `"1,3,5"` — use PCs 1, 3, and 5
- `"1:4,6:8"` — use PCs 1-4 and 6-8 (skip PC5)

### Model selection metrics

`clusterPca` reports **AIC** and **BIC** and their improvement over a null
(single-cluster) model. The man page states: "Both improvements should be well above
zero for the chosen cluster to be judged significant, with larger improvements
corresponding to larger (penalized, negative log) likelihoods."

These metrics help decide both the number of clusters (run clusterPca with k=2,3,4,5
and compare AIC/BIC) and which PCs to use.

### Outputs

| File | Description |
|---|---|
| `clusterPca.png` | 3D scatter plot of particles in PC space, colored by class. If >3 PCs used, projected onto first 3. |
| `pca_{basename}_MOTL_Tom{T}_Iter{I+1}.csv` | Updated MOTLs with class labels in col 20. **Prefixed with `pca_` — not active yet.** |
| `class_tom{T}_{modname}.mod` | IMOD model per tomogram; object I contains particles of class I. For viewing only. |

> **Critical**: `clusterPca` writes MOTLs to `pca_*` prefixed files. These are
> **NOT** the active MOTLs that `averageAll`, `pca`, etc. read. Run
> `usePcaMotiveLists` to activate them.

### Choosing features (PCs)

The `pcaFig` plots from `pca` are the primary guide. The variance plot (pcaFig1)
shows how much each PC contributes. The coefficient histograms (pcaFig3) show the
distribution of each PC score across all particles — multimodal histograms indicate
PCs that may correspond to structural sub-populations.

In practice, the recommended workflow is:
1. Run `pca` → inspect `pcaFig1.pdf` for scree-plot elbow
2. Run `clusterPca` with `features = "1:K"` where K is the elbow
3. Re-run with different feature selections if AIC/BIC improvements are small

---

## 4. Activating Classes (`usePcaMotiveLists`)

```bash
usePcaMotiveLists prmFile [iterationNumber]
```

This program:
1. Backs up current active MOTLs to `*~` files
2. Copies `pca_*_MOTL_Tom{T}_Iter{I}.csv` → `{basename}_MOTL_Tom{T}_Iter{I}.csv`

After this, `averageAll`, `calcFSC`, and other programs see the class labels in
column 20 and can filter by class using `selectClassID`.

**Known issue (v1.18.2)**: `usePcaMotiveLists` exits with a non-zero status even on
success. Use `|| true` in scripts to suppress the false error.

**Syntax gotcha**: Takes exactly 2 arguments (`prmFile` and `iterNum`). Passing a
third argument (e.g. numParticles) causes "Too many input arguments" and exits
without writing anything.

---

## 5. Per-Class Averages

After `usePcaMotiveLists`, run `averageAll` with `selectClassID` to get per-class
average volumes:

```
selectClassID = [1]   # in the prm file
```

Then:
```bash
averageAll prmFile iterNum 2>&1 | tee averageAll_class1.log
```

Alternatively, use the Python script `make_class_averages.py` which reads the MOTL
directly and averages from the original MRC files — useful when PEET's on-the-fly
extraction approach doesn't apply (e.g. the stacked-tomogram workaround).

---

## 6. Large Dataset Strategies

### `usePreviousPca` / `usePreviousPcaSP`

For very large datasets where full PCA is infeasible:

```bash
# Step 1: Run pca on a representative subset (e.g. 200 of 2000 particles)
pca prmFile 2 200 avg.mrc 1

# Step 2: Project all 2000 particles onto the subset's principal components
usePreviousPca pca200_basename.mat prmFile 2 2000 avg.mrc 1
```

`usePreviousPca` reads the eigenvectors from the subset `.mat` file and computes
PCA coefficients for all particles by projection, without recomputing the full
covariance matrix. Output is a new `.mat` with the same structure, compatible
with `clusterPca`.

**Important**: `pcaMethod` must be 1 (or omitted) for `usePreviousPca`. Methods 2 and
3 are not supported.

### `pcaSP` / `usePreviousPcaSP`

Single-precision variants of `pca` and `usePreviousPca`. Functionally identical but
use float32 instead of float64, reducing memory by ~2×. Use when 32-bit precision is
sufficient (nearly always the case for classification).

---

## 7. The MOTL: How Classes Are Stored

The motive list (MOTL) is a 20-column CSV. Column 20 (1-indexed, `parts[19]` in
Python) holds the class label. Default value is 0 (unclassified). Special value
-9999 marks duplicate particles (set by `removeDuplicates`).

Full column layout as documented in `alignSubset(1)`:

| Col | Label | Description |
|---|---|---|
| 1 | CCC | Cross-correlation coefficient from alignment |
| 2 | reserved | |
| 3 | reserved | |
| 4 | pIndex | 1-based particle index within this tomogram |
| 5 | wedgeWT | Wedge weight |
| 6 | adjCCC | **Adjusted CCC — used by PEET for ranking/selection** |
| 7–10 | NA | Reserved |
| 11 | xOffset | X shift from model position (pixels) |
| 12 | yOffset | Y shift |
| 13 | zOffset | Z shift |
| 14–16 | NA/oldClass | Reserved; col 16 stores previous class when particle is marked duplicate |
| 17 | EulerZ(1) | Φ — first Z rotation (ZXZ Euler convention, active extrinsic) |
| 18 | EulerZ(3) | Ψ — second Z rotation |
| 19 | EulerX(2) | Θ — X rotation |
| 20 | class | **Class label — written by `clusterPca`/`usePcaMotiveLists`** |

> **Key insight on adjCCC (col 6)**: PEET uses `adjCCC` (not `CCC`) for particle
> ranking when selecting the top-N particles for reference generation and averaging.
> Python-generated MOTLs that set only col 1 (CCC) but leave col 6 as 0 will cause
> all particles to appear equally ranked and may result in incorrect particle
> selection. Always set col 6 = col 1 in programmatically generated MOTLs.

PEET file naming convention for MOTL files:
```
{fnOutput}_MOTL_Tom{tomNum}_Iter{iterNum}.csv     ← active MOTL
{fnOutput}_MOTL_Tom{tomNum}_Iter{iterNum}.csv~    ← backup (after usePcaMotiveLists)
pca_{fnOutput}_MOTL_Tom{tomNum}_Iter{iterNum}.csv ← clusterPca output (not active)
{fnOutput}_TEMP_Tom{tomNum}_Iter{iterNum}_P1-1.csv ← alignSubset temporary output
```

---

## 8. Masking During Classification

PEET applies its reference mask (the same `maskType`/`insideMaskRadius`/
`outsideMaskRadius` from the prm) during PCA extraction. This means:
- Only voxels inside the mask contribute to the covariance matrix
- The eigenimages will be non-zero only within the mask

For classifying a central object, set `outsideMaskRadius` to just enclose the
object of interest. This suppresses edge artifacts and background noise from
entering the PCA.

Additional PCA-specific masking:
- `pcaSzSubvol`: crops a central sub-box before PCA (simpler than a mask)
- `pcaFnParticleMask`: arbitrary binary MRC mask in particle space

The effective region analyzed by `pca` is the intersection of all active masks.

---

## 9. Variance Maps

`varianceMap` is a related program that computes per-voxel variance across aligned
particles, optionally with missing-wedge correction:

```bash
varianceMap prmFile iterNum numParticles [avgFile]
```

Outputs:
- `{fnOutput}_VarianceMap_Iter{N}_{M}.mrc`
- `{fnOutput}_StandardDeviationMap_Iter{N}_{M}.mrc`

Variance maps show which voxels are most heterogeneous across particles —
complementary to eigenimages and useful for understanding where structural
variation is concentrated.

---

## 10. `flgNormalize` vs Manual Z-Scoring

PEET has a built-in per-particle normalization flag:

```
flgNormalize = 1
```

If set, PEET adjusts each subvolume to zero mean and unit variance before averaging,
clustering, or computing variance maps. This is equivalent to the per-particle
z-score normalization we performed manually in `create_single_tomo.py`.

**Important distinction**: `flgNormalize` acts at extraction time inside PEET,
so it applies to the voxels within the extraction box (`szVol`). Our manual z-scoring
was applied to the full 80×80×80 particle before stacking, which is slightly different
(the normalization includes voxels outside the 78×78×78 extraction box).

For future runs, `flgNormalize = 1` in the prm is the cleaner approach and avoids the
need to pre-process the stacked MRC.

---

## 11. The `flgUseExtractedParticles` Native Workaround

PEET v1.16.0 (2023) added official support for pre-extracted particle stacks:

```
flgUseExtractedParticles = 1
```

When enabled, `fnVolume` entries must point to **ParticleStack** MRC files (a PEET-
specific format generated by `extractParticles` or `extractAllParticles`). Each
ParticleStack contains multiple subvolumes; the corresponding model uses **time
values** to identify which subvolume each model point refers to.

This is the officially supported alternative to the multi-tomogram (one-particle-per-
tomogram) approach — and avoids the multi-tomogram iteration bug we encountered.

**Practical considerations**:
- The model format is PEET-specific (time values required)
- `extractParticles` / `extractAllParticles` generate compatible stacks from existing
  tomograms + model files
- These ParticleStacks display correctly in `3dmod` versions ≥ 4.12.47
- This approach was NOT available until v1.16.0; our manual stacked-MRC workaround
  predates it and achieves the same result with a different model format

Our stacked-MRC approach works because PEET treats 672 model contours in a single
IMOD model as 672 particles in a single "tomogram" — effectively the same as a
ParticleStack without requiring `flgUseExtractedParticles`.

---

## 12. Version History of Classification Features

| Version | Date | Classification-relevant additions |
|---|---|---|
| ~1.6.0 | ~2010 | Experimental clustering code (source only) |
| 1.7.1 | 2011 | WMD paper published (Heumann et al.) |
| 1.8.0 | 2012 | `pca` and `clusterPca` fully supported as compiled executables |
| 1.8.2 | 2012 | Allow user-settable `pcaNumEigenimages` |
| 1.15.0 | 2021 | `clusterPca` adds HAC (hierarchical ascendant clustering) |
| 1.16.0 | 2023 | `flgUseExtractedParticles` support (native pre-extracted particle stacks) |
| 1.17.0 | 2024 | `usePcaMotiveLists` added as a standalone program |
| 1.18.2 | 2025 | Current version (fixes `updateRotAxes` bug; classification unchanged) |

---

## 13. Quick Command Reference

```bash
# Source environment
source ~/Applications/IMOD-linux.sh && source ~/Applications/Particle.sh

# Run from results/ directory
cd ~/Research/peet/results

# Grand average at iteration 2
averageAll ../peet_project_single.prm 2

# PCA (WMD method 1, 672 particles, use grand average as reference)
pca ../peet_project_single.prm 2 672 peet_single_AvgVol_1P672.mrc 1

# K-means, k=2, PCs 1-10, 10 replicates (default)
clusterPca ../peet_project_single.prm pca672_peet_single.mat 2 "1:10" 1 0 kmeans

# K-means, k=3, PCs 1-5, 20 replicates for better convergence
clusterPca ../peet_project_single.prm pca672_peet_single.mat 3 "1:5" 1 0 kmeans 100 20

# HAC, k=3 (more deterministic than k-means)
clusterPca ../peet_project_single.prm pca672_peet_single.mat 3 "1:10" 1 0 hac

# Activate class labels
usePcaMotiveLists ../peet_project_single.prm 2 || true

# Per-class average (add selectClassID = [1] to prm first)
averageAll ../peet_project_single.prm 2

# Large dataset: project full set onto subset PCs
usePreviousPca pca200_basename.mat ../prm.prm 2 2000 avg.mrc 1
```

---

## 14. Common Errors and Causes

| Error | Cause | Fix |
|---|---|---|
| `clusterPca`: "Method must be one of 'kmeans' or 'hac'" | Passed integer instead of string | Use `kmeans` not `1` |
| `usePcaMotiveLists`: "Too many input arguments" | Passed 3 args (numParticles) | Use exactly 2 args: `prmFile iterNum` |
| `usePcaMotiveLists` exits non-zero despite success | Known PEET bug v1.18.2 | Use `|| true` in scripts |
| `pca` shows 1 particle processed | Multi-tomogram iteration bug: 1 particle per tomogram | Use stacked-MRC or `flgUseExtractedParticles` |
| Lopsided K-means split (e.g. 640:32) | Bimodal density dominates PC1 | Use `flgNormalize=1` or z-score before stacking |
| Class averages look identical | Classification not structurally driven, or too many PCs (noise included) | Try fewer PCs; check eigenimages for interpretable structure |
| `adjCCC = 0` in all particles | Python-generated MOTL only set col 1, not col 6 | Set col 6 = col 1 in all generated MOTL rows |
