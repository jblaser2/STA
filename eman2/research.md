# EMAN2 Codebase Research Report

## Overview

EMAN2 is a scientific image processing suite developed primarily at Baylor College of Medicine for cryo-electron microscopy (cryo-EM) and cryo-electron tomography (cryo-ET). It provides an end-to-end pipeline: from raw tilt series to reconstructed tomograms, particle picking, subtomogram extraction, iterative alignment/averaging, and classification. The codebase is structured as a collection of Python scripts in `programs/` backed by a C++ core library (`libEM/`) exposed through Python bindings (`libpyEM/`).

---

## Repository Structure

```
eman2/
├── programs/          # ~200 executable Python scripts (the main pipeline)
├── libpyEM/           # Python utility modules (EMAN2.py, EMAN2_utils.py, EMAN2jsondb.py)
├── libEM/             # C++ core library (EMData, Transform, Aligners, Processors, etc.)
├── sphire/            # SPHIRE package integration
├── sparx/             # SPARX package
├── examples/          # Test and example scripts
└── doc/               # Documentation
```

**Core Python utilities:**
- `libpyEM/EMAN2.py` — top-level import exposing EMData, Transform, Aligners, Processors, Comparators, Averagers
- `libpyEM/EMAN2_utils.py` — CTF calculation, missing wedge generation, TensorFlow import helper
- `libpyEM/EMAN2jsondb.py` — JSON-based persistent key-value store used throughout for per-particle metadata

---

## Tomography Workflow

### 1. Tomogram Reconstruction — `e2tomogram.py`

The main reconstruction script aligns an unaligned tilt series using landmark tracking (default: 20 gold fiducial markers) and reconstructs the 3D tomogram via Fourier-based methods.

**Key parameters:**
- `--npk`: Number of landmark particles (default 20)
- `--tltax`: Tilt axis angle
- `--tltkeep`: Fraction of tilt images to retain by quality score (default 0.9)
- `--filterres`: Low-pass filter output (default 40 Å)
- `--normslice`: Correct amplitude decay along Z
- `--bytile`: Tile-based reconstruction option

**Outputs:**
- 3D tomogram in HDF format (float32, or optionally 8-bit compressed)
- Sidecar JSON with tilt parameters, defocus, and phase metadata

### 2. Particle Picking — `e2spt_boxer.py`, `e2spt_autoboxer.py`, `e2spt_boxer_convnet.py`

Three modes of particle picking are available:

| Script | Mode |
|--------|------|
| `e2spt_boxer.py` | Interactive GUI — orthogonal XY/XZ/ZY views, manual coordinate editing |
| `e2spt_autoboxer.py` | Template-matching-based automated detection |
| `e2spt_boxer_convnet.py` | CNN-based automated detection (2D slices, PyTorch/TF) |

Picking outputs coordinate files, PDB-format positions, and particle stacks. Each particle pick is associated with a named **label** stored in tomogram metadata.

### 3. Particle Extraction — `e2spt_extract.py`

Extracts 3D subvolume stacks (and optionally 2D subtilt particle stacks) from the tilt series. Multiple extraction modes exist:

1. **From tomogram + coordinates:** `e2spt_extract.py tomogram.hdf --boxsz_unbin 128 --label <label>`
2. **From all tomograms at once:** `--alltomograms` flag
3. **From existing alignment JSON:** `--jsonali <json_from_refinement>` — re-extracts with updated box centers
4. **Along curves:** for filaments/helical particles
5. **From segmentation masks**

**Key parameters:**
- `--boxsz_unbin`: Box size in unbinned voxels
- `--shrink`: Downsampling factor for output particles
- `--maxtilt`: Max tilt angle to include in reconstruction (default 100°)
- `--noctf` / `--wiener`: CTF correction options
- `--rmbeadthr`: Remove high-contrast bead artifacts

**Output formats:**
- 3D particle stack: HDF (`.hdf`)
- 2D subtilt particle stack: HDF
- Particle list: LST format (text file with columns: index, filename, particle_index)
- Alignment metadata: JSON (`particle_parms_XX.json`)

---

## Data Formats and File Conventions

EMAN2 uses a consistent set of formats throughout the pipeline:

| Format | Description |
|--------|-------------|
| `.hdf` | Primary image format for all volumes and stacks (supports metadata in header) |
| `.mrc` / `.mrcs` | MRC format stacks (read/write supported) |
| `.lst` / `.lsx` | Particle list files — text with `index filename particle_index` per line |
| `.json` | Per-particle alignment metadata (`particle_parms_XX.json`) |

**Standard refinement directory (`spt_XX/`):**
```
spt_XX/
├── particle_parms_01.json    # Per-particle xform.align3d + score
├── threed_01.hdf             # 3D reconstruction
├── threed_01_even.hdf        # Even-particle half-set
├── threed_01_odd.hdf         # Odd-particle half-set
├── fsc_masked_01.txt         # Gold-standard FSC curve
├── fsc_unmasked_01.txt
├── aliptcls3d_01.lst         # Aligned 3D particle list
└── classmx_01.txt            # Classification assignment vector
```

**Particle metadata JSON format:**
Keys are string-encoded tuples: `"('path/to/particles.hdf', index)"`. Each value contains:
```json
{
  "xform.align3d": <4x4 rotation+translation matrix>,
  "score": <float (lower is better)>
}
```

---

## Iterative Subtomogram Refinement

### Core loop — `e2spt_refine.py`

The main refinement script (`programs/e2spt_refine.py`) orchestrates an iterative align-then-average loop:

```
for each iteration:
    e2spt_align.py   → compute per-particle xform.align3d + score → particle_parms_XX.json
    e2spt_average.py → Fourier-weighted average with missing wedge compensation → threed_XX.hdf
    e2refine_postprocess.py → FSC, masking, filtering
```

**Input flexibility:** The script accepts particles as:
- `.lst` / `.lsx` file (preferred)
- Plain `.hdf` stack (auto-converted to `input_ptcls.lst` via `e2proclst.py` at line 131–133)
- `.json` from a previous alignment

**Key parameters:**
- `--niter`: Number of iterations (default 5)
- `--sym`: Symmetry (c1, c2, d3, icos, …)
- `--goldstandard`: Resolution for phase randomization (gold-standard FSC)
- `--pkeep`: Fraction of highest-scoring particles to include in average (default 0.8)
- `--maxtilt`: Explicitly zeros Fourier data beyond this tilt angle (assumes Y tilt axis)
- `--refine`: Local refinement mode from existing transforms in particle headers
- `--maxang` / `--maxshift`: Angular and translational search limits

### Alignment — `e2spt_align.py`

Performs one alignment iteration for all particles against a reference.

**Algorithm:**
- **Aligner:** `rotate_translate_3d_tree` — a multi-resolution FFT-based coarse-to-fine search over SO(3) × R³
- **Comparator:** `ccc.tomo.thresh` — cross-correlation coefficient with threshold masking for tomographic data (handles asymmetric missing wedge bias)
- Even/odd particle splitting for gold-standard refinement
- Phase randomization at `--goldstandard` resolution to prevent overfitting bias
- Outputs per-particle `xform.align3d` (4×4 matrix) and `score` into `particle_parms_XX.json`

**Refinement search modes** (set via `--refine`, `--maxang`):
- Global: full angular search with tree-based pruning
- Local: small perturbation around existing transform, controlled by `--maxang` (degrees) and `--maxshift` (pixels)

### Averaging — `e2spt_average.py`

**Algorithm:**
- Averager: `mean.tomo` — Fourier-space weighted average that compensates for the missing wedge
- Missing wedge detection: `mask.wedgefill` processor with `thresh_sigma` (default 3.0) — identifies regions below noise floor per Fourier shell
- Explicit missing wedge zeroing: `--maxtilt` parameter forces zeros in Fourier beyond the specified tilt angle
- Symmetry: `xform.applysym` applied during averaging
- Even/odd halves averaged separately; FSC computed between them

---

## Particle Classification — Core Algorithms

EMAN2 provides six classification approaches for subtomogram data, each targeting different use cases.

---

### Algorithm 1: Reference-Based Score Classification — `e2spt_classify.py`

**Author:** Muyuan Chen, 2016-10  
**Method:** Multi-reference alignment + argmin score assignment

**Algorithm (lines 45–130):**

```
Initialize N reference volumes (low-pass filtered to random phase)
For each iteration:
    For each reference r_i:
        e2spt_align.py(particles, r_i) → particle_parms_XX_cls{i}.json
    For each particle p:
        scores[i] = alignment score against reference r_i
        class[p]  = argmin(scores)           # line 80: np.argmin(score, axis=0)
    For each class c_i:
        e2spt_average.py(particles in c_i) → new_reference_i
    Update references and repeat
```

**Output:**
- `classmx_XX.txt` — integer class assignment per particle
- `threed_XX_cls{i}.hdf` — 3D class average per class
- `ptcl_cls{i}.lst` — particle list files per class

**Strengths:** Simple, interpretable, leverages existing reference knowledge  
**Weakness:** Requires initial references; sensitive to reference bias

---

### Algorithm 2: Fourier-PCA + K-Means — `e2spt_pcasplit.py`

**Author:** Steven Ludtke  
**Method:** Dimensionality reduction in Fourier space, then K-Means clustering  
**Dependencies:** `sklearn.decomposition.PCA`, `sklearn.cluster.KMeans`

**Algorithm (lines 128–278):**

1. **Load aligned particles** from `particle_parms_XX.json`: apply stored `xform.align3d` transform to each particle
2. **Apply mask** (tight 3D mask from prior refinement, or user-specified)
3. **FFT transform:** `ef = np.fft.fftshift(np.fft.fftn(en))` — compute 3D Fourier transform
4. **Resolution clip:** crop Fourier volume to `--maxres` (default 30 Å)
5. **Missing wedge masking:** detect wedge region where `amplitude / structure_factor < 1.0` and set those Fourier voxels to 0 — this prevents the wedge from dominating the PCA
6. **Normalize by structure factor:** divide each Fourier shell by its mean amplitude
7. **Stack real + imaginary parts:** `imgsnp = np.hstack([dv.real, dv.imag])`
8. **PCA:** `pca = PCA(nbasis).fit_transform(imgsnp)` — projects to `--nbasis` basis vectors (default 3)
9. **Optional outlier removal:** `--clean` flag removes particles >2σ from PCA centroid before final decomposition
10. **K-Means clustering:** `KMeans(n_clusters=nclass).fit(pca_output)` — assigns class labels
11. **Write per-class LST files** and per-class class averages via `e2spt_average.py`

**Key parameters:**
- `--path` / `--iter`: Points to an existing `spt_XX/` refinement directory
- `--nclass`: Number of K-Means clusters (default 2)
- `--nbasis`: Number of PCA components (default 3)
- `--maxres`: Resolution cutoff in Å before PCA (default 30 Å)
- `--shrink`: Shrink factor before processing
- `--nowedgefill`: Skip wedge zeroing (not recommended)
- `--clean`: Remove outlier particles before final PCA

**Outputs:** `sptcls_XX/ptcls_cls01.lst`, `ptcls_cls02.lst`, …; PCA coordinates in `pca_ptcls.txt`; basis images in `pca_basis.hdf`

**Strengths:** Fully unsupervised; wedge-aware; Fourier-space analysis captures structural heterogeneity well  
**Weakness:** Requires a prior refinement run to generate alignment JSON; limited to low-dimensional signal (3 PCA components by default)

---

### Algorithm 3: Orthogonal Projection + MSA + K-Means — `e2spt_classify_byproj.py`

**Author:** Steven Ludtke, 2019  
**Method:** Reduce 3D particles to 2D projection triplets, apply MSA (PCA), then K-Means

**Algorithm (lines 47–200):**

1. **Apply alignment transform** from `particle_parms_XX.json` to each particle
2. **Generate three orthogonal projections** using central slabs (not full projections):
   ```python
   x = ptcl.process("misc.directional_sum", {"axis":"x", "first": center-layers, "last": center+layers+1})
   y = ptcl.process("misc.directional_sum", {"axis":"y", ...})
   z = ptcl.process("misc.directional_sum", {"axis":"z", ...})
   ```
   The `--layers` parameter (default 2) controls how many slabs around center are summed, effectively sampling the central density
3. **Normalize** each projection independently
4. **Concatenate** into a single 2D image: `[x | y | z]` packed side-by-side
5. **MSA/PCA** on the concatenated 2D projection triplets (`sklearn.decomposition`)
6. **K-Means** on the MSA-reduced feature space

**Key parameters:**
- `--ncls`: Number of classes
- `--nbasis`: MSA basis vectors (default 4)
- `--layers`: Slab thickness for projections (default 2 voxels each side)
- `--hp` / `--lp`: High/low-pass filter cutoffs

**Strengths:** Very fast (2D MSA is much cheaper than 3D PCA); captures projection-level structural differences  
**Weakness:** Loss of 3D information in projection step; may miss subtle interior heterogeneity

---

### Algorithm 4: K-Means on Raw Volumes — `e2classifykmeans.py`

**Author:** Steven Ludtke, 2006 (SPA origins, applicable to 3D)  
**Method:** Iterative K-Means on flat image vectors using EMAN2's C++ `kmeans` Analyzer

**Algorithm (lines ~100–200):**

1. Load all images into memory
2. Initialize K cluster centers randomly (or with `--fastseed`)
3. Iterate:
   - Assign each particle to nearest center by dot product (CCC)
   - Recompute centers as mean of assigned particles (`mean` averager)
   - Stop when reassignments < `--minchange`

**Key parameters:**
- `--ncls`: Number of classes (required)
- `--minchange`: Stop threshold (default: N / (ncls × 25))
- `--mininclass`: Min particles per class (default 2; small classes moved to outlier class)
- `--maxiter`: Max iterations (default computed as 16 × log₂(ncls))
- `--sigma`: Output per-class standard deviation maps

**Note:** This script predates the SPT workflow and works on any 2D or 3D image stack directly, without requiring pre-alignment metadata. It is primarily designed for SPA class averaging but can be applied to aligned 3D subtomogram stacks.

---

### Algorithm 5: CNN Good/Bad Classification — `e2classifycnn.py`

**Author:** Muyuan Chen, 2020-03  
**Method:** Binary CNN classifier for particle quality filtering (not structural classification)

**Architecture:**
```
Input: 96×96 2D particle image
Conv2D(32, 5×5) → MaxPool → Dropout(0.2)
Conv2D(64, 5×5) → MaxPool → Dropout(0.2)
Conv2D(128, 5×5) → MaxPool → Dropout(0.2)
Flatten → Dense(128) → BatchNorm → Dense(1, sigmoid)
Output: score ∈ [0,1] (1 = good particle)
```

**Usage:** Requires manual labeling of good/bad particles in a GUI. Once trained, applies to all particles and writes score files; particles below `--keep` threshold are discarded. This is a **quality filter**, not structural classification.

---

### Algorithm 6: GMM-Based Heterogeneity Refinement — `e2gmm_spt_refine.py`

**Author:** Muyuan Chen, 2023-04  
**Method:** Gaussian Mixture Model representation of 3D density + iterative refinement

This is a newer, more sophisticated approach:
1. The 3D density is represented as a sum of N Gaussian blobs (`--npt`, default 2000), computed via `e2segment3d.py --kmeans nseg=2000`
2. 2D projections are generated at multiple orientations via `e2project3d.py`
3. The GMM parameters (positions, amplitudes of Gaussians) are refined to match projections
4. Multiple refinement types can be scheduled: `p` (3D alignment), `r` (rotational subtilt), `t` (translational subtilt), `d` (defocus refinement)

This approach enables **continuous heterogeneity** analysis (conformational landscape) rather than discrete class assignment. Related scripts: `e2gmm_spt_align.py`, `e2gmm_spt_heterg.py`, `e2gmm_spt_heter_refine.py`.

---

## Summary Comparison of Classification Methods

| Method | Script | Supervised? | Requires Prior Alignment | Input | Best For |
|--------|--------|-------------|--------------------------|-------|----------|
| Multi-ref score | `e2spt_classify.py` | Yes (references) | No (aligns internally) | Particle stack + references | Known conformations |
| Fourier PCA + KMeans | `e2spt_pcasplit.py` | No | Yes (JSON) | Prior `spt_XX/` refinement | Structural heterogeneity |
| Projection MSA + KMeans | `e2spt_classify_byproj.py` | No | Yes (JSON) | Prior `spt_XX/` refinement | Fast unsupervised separation |
| K-Means (raw) | `e2classifykmeans.py` | No | No | Any aligned stack | Simple clustering |
| CNN binary | `e2classifycnn.py` | Yes (labeled) | No | 2D projections/slices | Quality filtering only |
| GMM refinement | `e2gmm_spt_refine.py` | No | No (refines internally) | Particle stack | Continuous heterogeneity |

---

## Using EMAN2 with Pre-Picked Particles in Subtomogram Volumes

**Short answer: Yes, with some preparation.**

EMAN2's refinement and classification pipeline can accept pre-existing subtomogram volumes (extracted by other software such as IMOD, Dynamo, RELION, etc.) stored as HDF or MRC stacks, provided the missing wedge geometry matches EMAN2's conventions.

### What Works Directly

**`e2spt_refine.py` accepts plain HDF/MRC stacks** at lines 130–133:
```python
# If not a .lst or .json, auto-convert to LST:
ptcllst = "{}/input_ptcls.lst".format(options.path)
run("e2proclst.py {} --create {}".format(ptcls, ptcllst))
```
So you can simply pass `my_particles.hdf` directly and EMAN2 will wrap it in an LST automatically. The same is true for `e2spt_classify.py`.

**`e2classifykmeans.py` requires no prior alignment or JSON metadata** — it operates directly on an image stack, making it the most straightforward entry point for externally-extracted subtomograms.

### The Missing Wedge Convention

EMAN2's missing wedge model assumes:
- **Tilt axis exactly on Y**
- **Zero-tilt plane in X-Y**
- The missing wedge is the cone of unmeasured Fourier space along Z

This is the standard convention for subtomograms aligned with the **Z axis as the primary particle axis** (which is also the typical output of most subtomogram averaging workflows). If your volumes are already aligned so that the particle symmetry axis is along Z, the missing wedge geometry is compatible.

Relevant code in `e2spt_average.py` (line 142):
```
--maxtilt: Explicitly zeroes data beyond specified tilt angle.
           Assumes tilt axis exactly on Y and zero tilt in X-Y plane.
```

And in `e2spt_pcasplit.py` (lines 165–171):
```python
# Missing wedge detection: Fourier regions where amplitude/structure_factor < 1
wdg = np.logical_and(div < 1., r > 1)
ef[wdg] = 0  # zero the wedge before PCA
```

### Recommended Workflow for Pre-Picked Particles

**Step 1: Format conversion (if needed)**

If your particles are in MRC format:
```bash
e2proc3d.py particles.mrcs particles.hdf
```

If particles are in separate MRC files, create an LST:
```bash
e2proclst.py particles.hdf --create sets/my_particles.lst
```

**Step 2: Initial refinement to generate alignment metadata**

The unsupervised classification methods (`e2spt_pcasplit.py`, `e2spt_classify_byproj.py`) require a `particle_parms_XX.json` file with per-particle `xform.align3d` transforms. If your particles are already aligned, run a short refinement starting from a reasonable reference (even one computed from the particles themselves):

```bash
# Compute initial reference from your particles
e2spt_make3d.py --input sets/my_particles.lst --output initial_ref.hdf

# Run 1-2 iterations of refinement to generate alignment JSON
e2spt_refine.py sets/my_particles.lst --ref initial_ref.hdf \
  --niter 2 --sym c1 --maxtilt 60 --path spt_00 --threads 12
```

Set `--maxtilt` to match your actual tilt series collection geometry (commonly 60°).

**Step 3: Apply classification**

Option A — Unsupervised (PCA/K-Means):
```bash
e2spt_pcasplit.py --path spt_00 --iter 2 --nclass 3 --nbasis 5 --maxres 25
```

Option B — Reference-based:
```bash
e2spt_classify.py sets/my_particles.lst \
  --refs class1_ref.hdf,class2_ref.hdf \
  --niter 3 --sym c1 --threads 12
```

Option C — Direct K-Means (no alignment JSON needed):
```bash
e2classifykmeans.py sets/my_particles.lst --ncls 3 --minchange 10
```

### Caveats and Limitations

1. **Pixel size metadata:** EMAN2 checks `apix_x` in the HDF header. Verify correct Å/pixel is set:
   ```bash
   e2proc3d.py particles.hdf particles_fixed.hdf --apix 3.54
   ```

2. **Box size must match reference:** `e2spt_refine.py` enforces `ep["nx"] == er["nx"]`. If your particles have a different box size than your reference, the script rescales the reference automatically, but you should ensure consistent sizes.

3. **Fourier-PCA wedge masking (`e2spt_pcasplit.py`):** The wedge detection heuristic (amplitude < structure factor) is designed for tomographically-extracted particles. If your subtomograms have been wedge-filled by another tool, disable wedge masking with `--nowedgefill`.

4. **Missing wedge direction:** If your particles were extracted from a tilt series with a different tilt axis orientation than EMAN2's convention (Y-axis), the `--maxtilt` zeroing will be applied in the wrong direction. The workaround is to pre-rotate the entire dataset or not use `--maxtilt` and rely on the statistical wedge detection (`wedgesigma` threshold in `e2spt_average.py`).

5. **No subtilt 2D particles:** The more powerful subtilt refinement modes (`e2spt_subtlt_local.py`, `e2spt_align_subtlt.py`) require the original 2D tilt series images — this information is not present in externally extracted 3D volumes. You would be limited to 3D-only refinement, which has somewhat reduced alignment accuracy.

6. **Gold-standard FSC:** With externally derived particles, the even/odd split for FSC is arbitrary. EMAN2 will still compute FSC but the resolution estimate may be less meaningful unless you split the dataset consistently.

---

## Key Code Locations Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| `programs/e2spt_refine.py` | Main refinement loop | 165–255 |
| `programs/e2spt_align.py` | Per-particle alignment | 59–665; aligner: line 622–625 |
| `programs/e2spt_average.py` | Fourier-space averaging | 83, 293–309 |
| `programs/e2spt_classify.py` | Reference-based classification | 45–153; argmin: line 80 |
| `programs/e2spt_pcasplit.py` | PCA + K-Means classification | 128–330; PCA: 262; KMeans: 278 |
| `programs/e2spt_classify_byproj.py` | Projection-based classification | 47–200; projections: lines 69–71 |
| `programs/e2classifykmeans.py` | Direct K-Means on stacks | ~100–200 |
| `programs/e2classifycnn.py` | CNN quality filter | 87–154 |
| `programs/e2gmm_spt_refine.py` | GMM heterogeneity refinement | 105–200 |
| `programs/e2spt_extract.py` | Particle extraction from tilt series | 41–500 |
| `programs/e2tomogram.py` | Tomogram reconstruction | full file |
| `programs/e2proclst.py` | LST file creation/manipulation | 50, 160–526 |
