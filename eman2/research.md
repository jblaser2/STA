# EMAN2 Codebase Research Report
_Last updated: 2026-05-27_

## Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Tomography Workflow](#tomography-workflow)
- [Data Formats and File Conventions](#data-formats-and-file-conventions)
- [Iterative Subtomogram Refinement](#iterative-subtomogram-refinement)
- [Particle Classification — Core Algorithms](#particle-classification--core-algorithms)
- [Summary Comparison of Classification Methods](#summary-comparison-of-classification-methods)
- [Using EMAN2 with Pre-Picked Particles in Subtomogram Volumes](#using-eman2-with-pre-picked-particles-in-subtomogram-volumes)
- [Bash Scripting with EMAN2 — fd-255 Script Corruption](#bash-scripting-with-eman2--fd-255-script-corruption)
- [Runtime Environment Notes (eman2 Conda Package)](#runtime-environment-notes-eman2-conda-package)
- [Key Code Locations Reference](#key-code-locations-reference)
- [Working Project Files](#working-project-files)
- [PCA Classification Pipeline Outputs](#pca-classification-pipeline-outputs)
- [Post-Classification Next Steps](#post-classification-next-steps)

---

## Overview

EMAN2 is a scientific image processing suite developed primarily at Baylor College of Medicine for cryo-electron microscopy (cryo-EM) and cryo-electron tomography (cryo-ET). It provides an end-to-end pipeline: from raw tilt series to reconstructed tomograms, particle picking, subtomogram extraction, iterative alignment/averaging, and classification. The codebase is structured as a collection of Python scripts in `programs/` backed by a C++ core library (`libEM/`) exposed through Python bindings (`libpyEM/`).

---

## Repository Structure

```
eman2/
├── programs/          # 276 executable Python scripts (the main pipeline)
├── libpyEM/           # Python utility modules + C++ binding wrappers
├── libEM/             # C++ core library (EMData, Transform, Aligners, Processors, etc.)
├── sphire/            # SPHIRE package integration
├── sparx/             # SPARX package
├── examples/          # Test and example scripts
├── broken/            # Deprecated/broken scripts kept for reference
├── rt/                # Regression test framework
└── doc/               # Documentation
```

**Core Python utilities (`libpyEM/`):**
- `EMAN2.py` — top-level import; exposes EMData, Transform, Aligners, Processors, Comparators, Averagers; contains `LSXFile` class and `launch_childprocess`/`run` helpers
- `EMAN2_utils.py` — CTF calculation (`calc_ctf`), missing wedge generation (`make_missing_wedge`), TensorFlow import helper (`import_tensorflow`), PDB/numpy converters, tile utilities
- `EMAN2jsondb.py` — JSON-based persistent key-value store (`js_open_dict`) used throughout for per-particle metadata; also defines `JSTask` base class for parallel task workers
- `EMAN2PAR.py` — parallel task dispatch; defines `EMTaskCustomer`, `EMLocalTaskHandler`, `EMMpiTaskHandler`, `EMSharedMemoryLocalTaskHandler`
- `EMAN2star.py` — STAR/CIF file reader (`StarFile`, `StarFile3` classes) for Relion interoperability
- `EMAN3.py` — newer Python API layer wrapping the same C++ core; experimental EMAN3 workflow support
- `EMAN3jsondb.py` — updated JSON metadata backend for EMAN3-style workflows
- `EMAN3star.py` — STAR file support updated for EMAN3 conventions
- `EMAN2db.py` — legacy database backend (BerkeleyDB-backed); largely superseded by EMAN2jsondb
- `Anneal.py` — simulated annealing optimizer (author: James Michael Bell)
- `Simplex.py` — Nelder-Mead simplex optimizer (third-party)
- `mpi_eman.py` — MPI initialization helpers
- `protein_constant.py` — amino acid masses and other protein constants
- `qtgui/` — 46 Qt5 GUI module files (browser, 2D/3D display, boxer, form builder, etc.)

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

**LSXFile API** (`LSXFile` is the Python class for reading/writing `.lst` files):
- `LSXFile(path, read_only)` — `read_only=False` to write/create, `True` to read
- `write(n, particle_index, filename, jsondict=None)` — `n=-1` appends; `particle_index` is the integer index within the HDF file; `filename` is the HDF path
- `read(n)` → `(particle_index, filename, jsondict)` — returns the nth entry as a tuple

**Standard refinement directory (`spt_XX/`):**
```
spt_XX/
├── 0_spt_params.json         # Run parameters (written by e2spt_refine.py at start)
├── particle_parms_01.json    # Per-particle xform.align3d + score
├── model_input.hdf           # Reference copied/scaled to match particle box size
├── alignref_even.hdf         # Phase-randomised even-set alignment reference
├── alignref_odd.hdf          # Phase-randomised odd-set alignment reference
├── threed_01.hdf             # 3D reconstruction (post-processed)
├── threed_01_even.hdf        # Even-particle half-set (post-processed)
├── threed_01_odd.hdf         # Odd-particle half-set (post-processed)
├── threed_raw_even.hdf       # Even half pre-amplitude-correction (written by e2spt_refine.py)
├── threed_raw_odd.hdf        # Odd half pre-amplitude-correction (written by e2spt_refine.py)
├── threed_even_unmasked.hdf  # Even half filtered but unmasked (written by e2refine_postprocess.py)
├── threed_odd_unmasked.hdf   # Odd half filtered but unmasked (written by e2refine_postprocess.py)
├── mask.hdf                  # Broad auto-mask used for FSC computation
├── mask_tight.hdf            # Tight mask (written by e2refine_postprocess.py)
├── fsc_masked_01.txt         # Gold-standard FSC (masked half-maps)
├── fsc_maskedtight_01.txt    # FSC using tighter mask
└── fsc_unmasked_01.txt       # Gold-standard FSC (unmasked half-maps)
```

Notes on standard `spt_XX/` output:
- `aliptcls3d_01.lst` and `classmx_01.txt` do **not** appear in standard `e2spt_refine.py` output. `aliptcls3d_01.lst` is written by newer-style subtilt refinement workflows; `classmx_01.txt` is written only by `e2spt_classify.py`.
- `threed_raw_even/odd.hdf` are the amplitude-uncorrected averages written at `e2spt_refine.py` line 277 before structure-factor correction is applied.
- `threed_even/odd_unmasked.hdf` are filtered-but-unmasked volumes written by `e2refine_postprocess.py` for use in local FSC/resolution calculations.
- `mask_tight.hdf` is produced by `e2refine_postprocess.py` (lines 328–363) and is the default mask used by `e2spt_pcasplit.py` when `--mask` is not specified. Its path is `{dirname(--output)}/mask_tight.hdf` — so for `--output spt_01/threed_01.hdf` it writes `spt_01/mask_tight.hdf` (note the trailing slash in the path string: `path=os.path.dirname(combfile)+"/"` at line 129).

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

The main refinement script (`programs/e2spt_refine.py`, 358 lines) orchestrates an iterative align-then-average loop:

```
for each iteration:
    [write alignref_even.hdf and alignref_odd.hdf from current reference]
    e2spt_align.py   → compute per-particle xform.align3d + score → particle_parms_XX.json
    e2spt_average.py → Fourier-weighted average with missing wedge compensation → threed_XX.hdf
    e2refine_postprocess.py → FSC, masking, filtering → threed_XX.hdf (post-processed)
```

**Input flexibility:** The script accepts particles as:
- `.lst` / `.lsx` file (preferred)
- Plain `.hdf` stack (auto-converted to `input_ptcls.lst` via `e2proclst.py` at lines 131–133)
- `.json` from a previous alignment

**Reference handling (lines 165–195):** Each iteration first writes alignment references:
- Without `--goldstandard`: copies current `ref` to both `{path}/alignref_even.hdf` and `{path}/alignref_odd.hdf`
- With `--goldstandard N`: on iteration 1, phase-randomizes past N Å before writing; on later iterations, uses the even/odd half-map output from the previous iteration
- `e2spt_align.py` is called as `e2spt_align.py ptcls {path}/alignref.hdf ... --goldcontinue`; the `--goldcontinue` flag causes e2spt_align to automatically look for `alignref[:-4]+"_even.hdf"` and `"_odd.hdf"` (line 139 of e2spt_align.py)

**Key parameters:**
- `--niter`: Number of iterations (default 5). With `--niter 1` and no prior state, produces `particle_parms_01.json`.
- `--threads`: CPU threads (default 12). When `--parallel` is not specified, automatically sets `--parallel thread:{threads}` (lines 110–111).
- `--sym`: Symmetry (c1, c2, d3, icos, …)
- `--goldstandard`: Resolution for phase randomization (gold-standard FSC)
- `--goldcontinue`: Resume gold-standard refinement from existing even/odd half-maps without re-randomizing
- `--pkeep`: Fraction of highest-scoring particles to include in average (default 0.8)
- `--maxtilt`: Explicitly zeros Fourier data beyond this tilt angle (assumes Y tilt axis). **Do not use if the tilt axis is not on Y** — it zeros the wrong Fourier voxels. Default 90 (no limit).
- `--refine`: Local refinement mode from existing transforms in particle headers. **Must be combined with `--maxang`** (the script enforces this at line 73–75; either both or neither must be specified).
- `--maxang` / `--maxshift`: Angular and translational search limits for local refinement
- `--refinentry`: Number of local perturbation seeds for `--refine` mode (default 8)
- `--realign`: After each iteration, realign the class average back to the initial reference to prevent drift (useful with `--refine` and symmetry)
- `--tophat`: Filter type: `'local'`, `'localwiener'`, or `'global'` (tophat replaces Wiener when specified)
- `--resume`: Resume from a previous run using an existing `threed_XX.hdf` as reference; infers `startitr` and resolution from that file

### Alignment — `e2spt_align.py`

Performs one alignment iteration for all particles against a reference (679 lines).

**Algorithm:**
- **Aligner:** `rotate_translate_3d_tree` — a multi-resolution FFT-based coarse-to-fine search over SO(3) × R³ (line 625)
- **Alternative aligner:** `rotate_translate_3d_local_tree` when `--flcf` is specified (line 622) — slower
- **Alignment parameters** (line 551): `sigmathis=0.1`, `sigmato=1.0` for Gaussian sigma weighting across resolution shells; `minres` and `maxres` pass frequency band limits
- **Even/odd split:** particles are split by `index % 2` and aligned to their respective even/odd reference (line 178). If `*__even.lst`/`*__odd.lst` files exist alongside the input LST, those are used instead
- Phase-randomized references are prepared by `e2spt_refine.py` and written to `{path}/alignref_even.hdf` / `{path}/alignref_odd.hdf` before `e2spt_align.py` is called. `e2spt_align.py` itself does not perform phase randomization — it merely loads the pre-prepared files when `--goldcontinue` is set (line 139)
- Outputs per-particle `xform.align3d` and `score` into `{path}/particle_parms_{iter:02d}.json`

**Refinement search modes** (set via `--refine`, `--maxang`):
- Global: full angular search with tree-based pruning (default)
- Local: small perturbation around existing transform (`--refine --maxang <degrees>` required together); generates `--refinentry` (default 8) perturbed start points using random rotations drawn from a Gaussian with sigma=`maxang/3` (lines 566–581)

### Averaging — `e2spt_average.py`

**Algorithm (422 lines):**
- **Averager:** `mean.tomo` — Fourier-space weighted average that compensates for the missing wedge (lines 83, 293–294)
- **`--wedgesigma`** (default 3.0): threshold (in units of per-shell standard deviations) used by the `mean.tomo` averager to identify missing-wedge Fourier voxels and downweight them
- **`--maxtilt`** (default 90, i.e. no limit): if < 90, calls `mask.wedgefill` on each particle's FFT with `thresh_sigma=0.0` and the specified tilt limit — zeros all data beyond that tilt angle (lines 97–99)
- **Particle selection:** `--keep` (fraction, overrides `--simthr`); `--simthr` (absolute score threshold, default −0.1); `--minalt`/`--maxalt` (altitude angle range)
- **Symmetry:** `xform.applysym` applied to final average (lines 338–339)
- **`--skippostp`:** skip FSC + masking steps (used internally by `e2spt_pcasplit.py` when calling this script)
- Even/odd halves averaged separately; unmasked FSC written; then full postprocessing via `e2refine_postprocess.py` (unless `--skippostp`)
- **Parallel mode:** when `--parallel` is specified and `--symalimasked` is not, uses `EMTaskCustomer`/`SptavgTask` for distributed averaging (line 219); otherwise uses Python `threading.Thread` (line 302)

---

## Particle Classification — Core Algorithms

EMAN2 provides six classification approaches for subtomogram data, each targeting different use cases.

---

### Algorithm 1: Reference-Based Score Classification — `e2spt_classify.py`

**Author:** Muyuan Chen, 2016-10  
**Method:** Multi-reference alignment + argmin score assignment  
**File:** `programs/e2spt_classify.py`, 165 lines

**Algorithm (lines 45–130):**

```
Initialize N reference volumes (low-pass filtered to random phase at 0.02 cutoff)
For each iteration:
    For each reference r_i:
        e2spt_align.py(particles, r_i) → particle_parms_XX.json → renamed particle_parms_XX_cls{i}.json
    For each particle p:
        scores[i] = alignment score against reference r_i
        class[p]  = argmin(scores)           # line 80: np.argmin(score, axis=0)
    For each class c_i:
        e2spt_average.py(particles in c_i) → new_reference_i
        e2refine_postprocess.py(even, odd) → FSC + filtered reference
    Update references and repeat
```

**Parameters:**
- `--refs`: Comma-separated list of reference HDF paths
- `--niter`: Iterations (default 3)
- `--threads`: Thread count (default 12; passed directly to `e2spt_align.py` — no `--parallel` argument)
- `--path`: Output directory (default: `num_path_last("spt_")` — uses the highest-numbered existing `spt_XX/`)

**Output:**
- `classmx_XX.txt` — integer class assignment per particle
- `threed_XX_cls{i:02d}.hdf` — 3D class average per class
- `ptcl_cls{i:02d}.lst` — particle list files per class (written at end of all iterations, line 131–154)

**Strengths:** Simple, interpretable, leverages existing reference knowledge  
**Weakness:** Requires initial references; sensitive to reference bias; uses `--threads` not `--parallel`, so no MPI

---

### Algorithm 2: Fourier-PCA + K-Means — `e2spt_pcasplit.py`

**Author:** Steven Ludtke  
**Method:** Dimensionality reduction in Fourier space, then K-Means clustering  
**File:** `programs/e2spt_pcasplit.py`, 337 lines  
**Dependencies:** `sklearn.decomposition.PCA`, `sklearn.cluster.KMeans`, `scipy.signal.find_peaks_cwt`

**Algorithm (lines 125–330):**

1. **Load aligned particles** from `particle_parms_XX.json`: apply stored `xform.align3d` transform to each particle
2. **Apply mask** (tight 3D mask from prior refinement, or user-specified; `--mask none` for no mask)
3. **FFT transform:** `ef = np.fft.fftshift(np.fft.fftn(en))` — compute 3D Fourier transform (line 155)
4. **Resolution clip:** crop Fourier volume to `--maxres` (default 30 Å) — removes high-frequency Fourier voxels (lines 156–157)
5. **Missing wedge masking** (unless `--nowedgefill`): per-voxel amplitude divided by shell-mean; voxels where ratio < 1.0 AND radius > 1 are zeroed (lines 162–171). The radial shell binning uses `r = r.astype(np.int)` at **line 162** — this is the known `np.int` deprecation bug (see Known Bugs below).
6. **Stack real + imaginary parts:** wedge-weighted mean subtracted across particles, divided by global `std(|residuals|)`, then stacked: `imgsnp = np.hstack([dv.real, dv.imag])` (line 195)
7. **PCA:** `pca = PCA(nbasis).fit_transform(imgsnp)` (line 263) — projects to `--nbasis` basis vectors (default 3)
8. **Optional outlier removal:** `--clean` flag removes particles >2σ from PCA centroid before final decomposition (lines 247–259)
9. **K-Means clustering:** `KMeans(n_clusters=nclass).fit(pca_output)` (line 278) — assigns class labels
10. **Write per-class LST files** (lines 303–312) and per-class class averages via `e2spt_average.py` (line 330)

**Key parameters:**
- `--path` / `--iter`: Points to an existing `spt_XX/` refinement directory. `--iter` default is `-2` which resolves to `max(iteration_numbers) - 1` (second-to-last).
- `--nclass`: Number of K-Means clusters (default 2)
- `--nbasis`: Number of PCA components (default 3)
- `--maxres`: Resolution cutoff in Å before PCA (default 30 Å)
- `--shrink`: Shrink factor before processing (default 1, no shrink)
- `--nowedgefill`: Skip the amplitude-based wedge zeroing step. **Required** when the missing wedge is not in EMAN2's expected orientation (Y tilt axis). Without this flag, the wedge detector zeros voxels in the wrong direction for particles whose tilt axis was rotated during extraction.
- `--clean`: Remove outlier particles (>2σ from centroid) before final PCA
- `--dotest N`: Use only N randomly-selected particles (for rapid testing)

**Outputs:** `sptcls_XX/ptcls_cls01.lst`, `ptcls_cls02.lst`, …; PCA coordinates in `pca_ptcls.txt`; PCA basis images in `pca_basis.hdf`; per-class alignment JSON `particle_parms_01.json`, `particle_parms_02.json`, …; per-class 3D averages `threed_01.hdf`, `threed_02.hdf`, …

The output directory is auto-numbered by `num_path_new("sptcls")` (line 198) and starts at `sptcls_00` (zero-based), incrementing on each run. Class list files inside use **one-based** numbering (`ptcls_cls01.lst`, `ptcls_cls02.lst`, …).

**Strengths:** Fully unsupervised; wedge-aware; Fourier-space analysis captures structural heterogeneity well  
**Weakness:** Requires a prior refinement run to generate alignment JSON; limited to low-dimensional signal (3 PCA components by default); averaging call at line 330 uses `os.system` not `launch_childprocess`

**Known bugs:**
- **Line 289:** `print("{}: {}".format(lb, np.sum(lb==i)))` — `lb` should be `lb[i]`; prints the entire label array instead of the class index for the loop variable `i`. Cosmetic only (the class assignments themselves are correct).
- **Line 330:** `os.system("e2spt_average.py --path {} --iter {} --threads 10 ...")` — thread count is hardcoded to 10 and cannot be overridden at the command line. Also uses `os.system` rather than `launch_childprocess`, so errors are not propagated back.
- **Line 162 (source tree):** `r = r.astype(np.int)` — `np.int` alias was removed in NumPy 1.24. **Status:** the installed `e2spt_pcasplit.py` at `/home/ejl62/miniforge3/envs/eman2/bin/e2spt_pcasplit.py` has been patched to `np.int64` by `patch_scripts.py`. The source file at `programs/e2spt_pcasplit.py` still has the unfixed `np.int`.

---

### Algorithm 3: Orthogonal Projection + MSA + K-Means — `e2spt_classify_byproj.py`

**Author:** Steven Ludtke (author header `sludtke@bcm.edu`, 2003-era; SPT classification added ~2019)  
**Method:** Reduce 3D particles to 2D projection triplets, compute PCA (for basis inspection), then K-Means directly on the projections  
**File:** `programs/e2spt_classify_byproj.py`, 370 lines

**Algorithm (core logic distributed across `ptclextract`/`ptclextract_new` helpers and `main()`):**

1. **Apply alignment transform** from `particle_parms_XX.json` (old-style) or `aliptcls3d_XX.lst` (new-style) to each particle. The script auto-detects which format is present (lines 180–197).
2. **Generate three orthogonal projections** using central slabs (not full projections):
   ```python
   x = ptcl.process("misc.directional_sum", {"axis":"x", "first": center-layers, "last": center+layers+1})
   y = ptcl.process("misc.directional_sum", {"axis":"y", ...})
   z = ptcl.process("misc.directional_sum", {"axis":"z", ...})
   ```
   The `--layers` parameter (default 2) controls how many slabs around center are summed — `layers=2` sums 5 slabs (`2*layers+1 = 5` pixels wide)
3. **Normalize** each projection independently; apply `--hp`/`--lp` filters if specified
4. **Concatenate** into a single 2D image: `[x | y | z]` packed side-by-side
5. **PCA** on the concatenated 2D projection triplets (`sklearn.decomposition.PCA`, line 281) — the `--nbasis` basis vectors are written to `classes_basis_{iter:02d}_{crun:02d}.hdf` for inspection
6. **K-Means** is run directly on the **original 2D projection triplets** (`prjs`) using EMAN2's C++ `kmeans` Analyzer (line 294) — the PCA output is **not** used as K-Means input (PCA is inspection-only)
7. **3D class averages** are computed by re-reading original particles and applying stored transforms (lines 321–341)

**Key parameters:**
- `--ncls`: Number of classes (default 3)
- `--nbasis`: MSA basis vectors for PCA inspection (default 4)
- `--layers`: Slab thickness for projections (default 2 voxels each side, i.e. 5-pixel slab)
- `--hp` / `--lp`: High/low-pass filter cutoffs (specify in Å)
- `--shrink`: Shrink particles before processing
- `--saveali`: Also write aligned particle stacks per class

**Multi-run support:** A `crun` counter tracks how many classification runs have been done within the same `--path` directory; each run appends a new `crun` index to output filenames.

**Outputs:** `sets/{path}_{iter:02d}_{crun:02d}_{cls:02d}.lst` per-class particle lists; `classes_{iter:02d}_{crun:02d}.hdf` 3D class averages; `classes_sec_{iter:02d}_{crun:02d}.hdf` 2D section-space class centers; `classes_basis_{iter:02d}_{crun:02d}.hdf` PCA basis images

**Strengths:** Very fast (2D K-Means on section images is much cheaper than 3D PCA); captures projection-level structural differences  
**Weakness:** Loss of 3D information in projection step; may miss subtle interior heterogeneity; PCA output is not actually used for classification

---

### Algorithm 4: K-Means on Raw Volumes — `e2classifykmeans.py`

**Author:** Steven Ludtke, 2006-03-04 (SPA origins, applicable to 3D)  
**Method:** Iterative K-Means on flat image vectors using EMAN2's C++ `kmeans` Analyzer  
**File:** `programs/e2classifykmeans.py`, 292 lines

**Algorithm (lines 50–210):**

1. Load all images into memory
2. Initialize K cluster centers: `--fastseed` uses fast random seeding (`slowseed=0`); default uses slow/consistent seeding
3. Iterate:
   - Assign each particle to nearest center by dot product (CCC)
   - Recompute centers as mean of assigned particles
   - Stop when reassignments < `--minchange`
4. Write class averages and (optionally) standard deviation maps

**Key parameters:**
- `--ncls` / `-N`: Number of classes (required)
- `--minchange`: Stop threshold (default: `len(data) / (ncls × 25) + 1`, line 129)
- `--mininclass`: Min particles per class (default 2; small classes optionally moved to outlier class via `--outlierclass`)
- `--maxiter`: Max iterations (default: `16 × int(log₂(ncls))`, line 132)
- `--sigma`: Output per-class standard deviation maps alongside averages

**Note:** Predates the SPT workflow; works on any 2D or 3D image stack directly without pre-alignment metadata. Primarily designed for SPA class averaging but can be applied to aligned 3D subtomogram stacks.

---

### Algorithm 5: CNN Good/Bad Classification — `e2classifycnn.py`

**Author:** Muyuan Chen, 2020-03  
**Method:** Binary CNN classifier for particle quality filtering (not structural classification)  
**File:** `programs/e2classifycnn.py`, 397 lines

**Architecture (lines 94–106):**
```
Input: N×N 2D particle image (N = particle boxsize, default 96)
Conv2D(32, 5×5, relu) → MaxPool → Dropout(0.2)
Conv2D(64, 5×5, relu) → MaxPool → Dropout(0.2)
Conv2D(128, 5×5, relu) → MaxPool → Dropout(0.2)
Flatten → Dense(128, relu) → BatchNormalization → Dense(1, sigmoid)
Output: score ∈ [0,1] (1 = good particle)
```

**Usage:** Requires TensorFlow (loaded via `import_tensorflow` from `EMAN2_utils.py`). Requires manual labeling of good/bad particles in a GUI. Once trained, applies to all particles and writes score files; particles below `--keep` threshold are discarded. This is a **quality filter**, not structural classification.

**CUDA note:** Even though CUDA packages are present in the conda environment (`cuda-cudart 12.9`, `cudnn 9.10`), these are dependencies of other conda packages. The EMAN2 C++ library itself (`libEM2.so`) has CUDA support compiled out — `EMUtil::cuda_available()` always returns `false` (see `libEM/emutil.h` line 358–363). TensorFlow within the same conda environment may use CUDA independently for CNN inference.

---

### Algorithm 6: GMM-Based Heterogeneity Refinement — `e2gmm_spt_refine.py`

**Author:** Muyuan Chen, 2023-04  
**Method:** Gaussian Mixture Model representation of 3D density + iterative refinement  
**File:** `programs/e2gmm_spt_refine.py`, 205 lines

**Algorithm (lines 100–184):**
1. Copy particle metadata (`particle_info_2d.lst`, `particle_info_3d.lst`) and initial 3D volumes from an existing SPT refinement folder.
2. For each iteration `itype` in `--iters` (default `"r,p,r"`):
   - Generate 2D projections of the current volume via `e2project3d.py` at `delta=4°` angular sampling (line 140)
   - Initialize or update the GMM: on iteration 1 use `e2segment3d.py` k-means with `nseg=npt` blobs (line 148), then fit via `e2gmm_refine_new.py` (line 150); on later iterations, continue from previous GMM (line 153)
   - `itype='p'`: run `e2gmm_spt_align.py` — 3D subtomogram translation/rotation alignment against GMM projections
   - `itype='r'`: run `e2gmm_spt_subtlt.py` — subtilt rotational refinement
   - (additional types defined but not shown: `'t'` translational subtilt, `'T'` translational CCF, `'d'` defocus, `'x'` skip, `'z'` stop)
   - Reconstruct 3D maps from updated 2D particles with `e2spa_make3d.py`
   - Run `e2refine_postprocess.py` with `--tophat localwiener`
   - Track resolution via FSC < 0.2 criterion

**Key parameters:**
- `--npt`: Number of Gaussian blobs (default 2000; ignored if `--initpts` provided)
- `--iters`: Comma-separated iteration schedule (default `"r,p,r"`); repeat counts supported (e.g. `"r3,p2"` = 3 subtilt + 2 alignment iterations)
- `--startres`: Starting resolution in Å (required; must be specified explicitly)
- `--parallel` / `--threads`: Parallelism (default `"thread:32"`, 32 threads)
- `--keep`: Fraction of particles to keep by score (default 0.9)

**Output directory:** `gmm_XX/` (auto-numbered by `num_path_new("gmm_")`). Contains `particle_info_2d.lst`, `particle_info_3d.lst`, `threed_{iter:02d}_{eo}.hdf`, `aliptcls2d_{iter:02d}_{eo}.lst`, `model_{iter:02d}_{eo}.txt`.

This approach enables **continuous heterogeneity** analysis (conformational landscape) rather than discrete class assignment. Related scripts: `e2gmm_spt_align.py`, `e2gmm_spt_heterg.py`, `e2gmm_spt_heter_refine.py`, `e2gmm_spt_subtlt.py`, `e2gmm_spt_rigidbody.py`.

---

## Summary Comparison of Classification Methods

| Method | Script | Supervised? | Requires Prior Alignment | Input | Best For |
|--------|--------|-------------|--------------------------|-------|----------|
| Multi-ref score | `e2spt_classify.py` | Yes (references) | No (aligns internally) | Particle stack + references | Known conformations |
| Fourier PCA + KMeans | `e2spt_pcasplit.py` | No | Yes (JSON) | Prior `spt_XX/` refinement | Structural heterogeneity |
| Projection PCA + KMeans | `e2spt_classify_byproj.py` | No | Yes (JSON) | Prior `spt_XX/` refinement | Fast unsupervised separation |
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

Relevant code in `e2spt_average.py` (argument definition at line 142, zeroing at lines 97–99):
```
--maxtilt: Explicitly zeroes data beyond specified tilt angle.
           Assumes tilt axis exactly on Y and zero tilt in X-Y plane.
```

And in `e2spt_pcasplit.py` (lines 170–171 in the source tree):
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
  --niter 2 --sym c1 --path spt_00 --threads 12
```

Only add `--maxtilt 60` if the tilt axis is on Y (EMAN2's default convention). If particles were rotated during extraction (e.g., symmetry axis aligned to Z), the wedge is in a non-standard orientation — omit `--maxtilt` and let the `mean.tomo` averager handle it statistically.

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

## Bash Scripting with EMAN2 — fd-255 Script Corruption

**Problem:** When running EMAN2 commands from a bash script via a pipeline (`cmd | tee log`), bash keeps the script file open on fd 255 to track its read position. When bash forks for the pipeline subshell, the child inherits fd 255 (pointing into the script file). EMAN2 programs use `launch_childprocess` (see below), which calls `subprocess.Popen(cmd, shell=True)`. Python does not close fd 255 on startup, so the script fd remains open throughout the subprocess tree. If anything in that subprocess tree advances the shared file-offset on fd 255, bash resumes reading the script from the wrong byte position after the pipeline exits, and may try to execute garbage content — manifesting as errors like `run_pipeline.sh: line 62: i: command not found` even on a blank line.

**Fix:** Close fd 255 in the context where the long-running EMAN2 pipeline runs:
```bash
{ e2spt_refine.py ... 2>&1 | tee refine.log; } 255>&-
{ e2spt_pcasplit.py ... 2>&1 | tee pca_classify.log; } 255>&-
```
`255>&-` is a no-op when fd 255 is not open (tested on bash 5.2.26), so it is always safe to include.

**`launch_childprocess` implementation** (in `libpyEM/EMAN2.py`, lines 1513–1529):
```python
def launch_childprocess(cmd, handle_err=0):
    p = subprocess.Popen(f"{RUN_PREFIX}{cmd} --ppid {os.getpid()} {RUN_POSTFIX}", shell=True)
    if get_platform() == 'Windows':
        error = p.wait()          # os.waitpid does not work on Windows
    else:
        error = os.waitpid(p.pid, 0)[1]
    if error and handle_err:
        print("Error {} running: {}".format(error, cmd))
        sys.exit(1)
    return error
```
Key points:
- `shell=True` — runs through `/bin/sh -c cmd`
- `RUN_PREFIX` and `RUN_POSTFIX` are read from environment variables `EMAN_RUN_PREFIX` / `EMAN_RUN_POSTFIX` at module import time (lines 87–93); both default to empty string
- No explicit `stdin`/`stdout`/`stderr` redirection — inherits from the calling process
- `close_fds` defaults to `True` in Python 3 for subprocess children, so fd 255 IS closed in each `/bin/sh` child but NOT in the Python process itself
- Appends `--ppid {pid}` to every command so subprocesses can report status back to the parent
- A `run(cmd)` wrapper that also prints the command exists both in `EMAN2.py` (line 1508–1511) and redefined locally in several scripts (`e2spt_refine.py`, `e2spt_classify.py`)

---

## Runtime Environment Notes (eman2 Conda Package)

Confirmed for the eman2 conda installation at `/home/ejl62/miniforge3/envs/eman2/`:

| Package | Version | Notes |
|---------|---------|-------|
| EMAN2 | 2.99.72 | Built 2026-05-27, git hash `e15d7fc6c` — matches source tree at `/home/ejl62/src/eman2/` |
| Python | 3.12 | |
| NumPy | 2.4.6 | `np.int` alias removed — see patch note below |
| SciPy | 1.17.1 | `find_peaks_cwt` still present (imported by `e2spt_pcasplit.py` but not called) |
| scikit-learn | 1.8.0 | PCA and KMeans APIs unchanged |
| CUDA (EMAN2 C++) | Unavailable | `EMUtil::cuda_available()` hardcoded to `return false` in `libEM/emutil.h` line 362; EMAN2 itself has no GPU acceleration |
| CUDA (conda env) | 12.9 | `cuda-cudart`, `cuda-nvcc`, `cudnn 9.10` are present as dependencies of other packages; TensorFlow within the env may use GPU |

**Installed scripts location:** `/home/ejl62/miniforge3/envs/eman2/bin/e2*.py`

**Source vs installed:** The installed scripts are separate copies from the source tree. The source tree at `/home/ejl62/src/eman2/programs/` is **not** on the Python path; when running `e2spt_pcasplit.py` the installed copy at `/home/ejl62/miniforge3/envs/eman2/bin/` is used.

**np.int patch status:**
- **Installed** `/home/ejl62/miniforge3/envs/eman2/bin/e2spt_pcasplit.py`: patched (`np.int64` at line 162). Backup at `.bak` suffix.
- **Source** `/home/ejl62/src/eman2/programs/e2spt_pcasplit.py`: still has `np.int` (unpatched). The patch script is `eman2_project/patch_scripts.py`.

**PATH issue:** `conda activate eman2` does not always prepend the env bin ahead of `/usr/bin`, so `python` may resolve to the system Python. Explicitly prepend:
```bash
export PATH="/home/ejl62/miniforge3/envs/eman2/bin:$PATH"
```

---

## Key Code Locations Reference

| File | Lines | Purpose | Key locations |
|------|-------|---------|---------------|
| `programs/e2spt_refine.py` | 358 | Main refinement loop | loop: 165–348; LST auto-create: 131–133; parallel auto-set: 110–111; reference writing: 168–195 |
| `programs/e2spt_align.py` | 679 | Per-particle alignment | aligner call: 622–625; aligndic: 551; even/odd split: 178; gold-continue ref loading: 136–144 |
| `programs/e2spt_average.py` | 422 | Fourier-space averaging | SptavgTask.execute: 74–116; main thread path: 293–294; maxtilt zeroing: 97–99; skippostp: 361 |
| `programs/e2spt_classify.py` | 165 | Reference-based classification | loop: 51–129; argmin: 80; output LSTs: 131–154 |
| `programs/e2spt_pcasplit.py` | 337 | PCA + K-Means | FFT+clip: 155–157; wedge mask: 162–171 (np.int bug here in source); PCA: 262–263; KMeans: 278; os.system call: 330 |
| `programs/e2spt_classify_byproj.py` | 370 | Projection-based classification | projections: 69–71 & 112–114; PCA: 281–289; K-Means: 294–298 |
| `programs/e2classifykmeans.py` | 292 | Direct K-Means on stacks | main: 50–210; params: 129–134 |
| `programs/e2classifycnn.py` | 397 | CNN quality filter | architecture: 94–106 |
| `programs/e2gmm_spt_refine.py` | 205 | GMM heterogeneity refinement | main loop: 128–184; iter types: 114; GMM init: 148–150 |
| `programs/e2spt_extract.py` | 1093 | Particle extraction from tilt series | main: 41–; key params: 62–103 |
| `programs/e2tomogram.py` | ~750 | Tomogram reconstruction | full file |
| `programs/e2proclst.py` | 695 | LST file creation/manipulation | `--create`: line 50; main: 41–695 |
| `programs/e2refine_postprocess.py` | ~560 | Post-processing / FSC / masking | path: 129; mask_tight write: 328–363 |
| `libpyEM/EMAN2.py` | ~3000 | Core Python API | launch_childprocess: 1513–1529; run: 1508–1511; LSXFile: 2471–2700; num_path_new: 503 |
| `libpyEM/EMAN2jsondb.py` | ~700 | JSON metadata store | js_open_dict: ~287; JSTask: ~499 |
| `libpyEM/EMAN2PAR.py` | ~950 | Parallel task dispatch | EMTaskCustomer: 75; EMLocalTaskHandler: 761 |
| `libpyEM/EMAN2star.py` | ~400 | STAR/CIF file I/O | StarFile: 181; StarFile3: 75 |
| `libEM/emutil.h` | ~400 | C++ utilities | cuda_available: 358 (always false) |

## Working Project Files

Scripts live in `/home/ejl62/src/eman2_project/` and are not part of the EMAN2 distribution.

### Dataset

The particles are **pili** subtomograms — bacterial appendages imaged by cryo-ET.

| Property | Value |
|----------|-------|
| Particles | 672 MRC files, `aligned_tom{NNN}_P{MMMM}.mrc` |
| Source path | `/home/ejl62/src/particles/` |
| Box size | 80 × 80 × 80 voxels |
| Pixel size | 13.328 Å/px |
| Nyquist resolution | 26.7 Å |
| Physical box | ~1066 Å (~106 nm) |
| Unique tomograms | 294 |
| Particles per tomogram | 1–8 (median 2) |
| Particle orientation | Pili axis along Z (rotated post-extraction) |
| Tilt range | ±60° |
| Missing wedge | Rotated with particles — **not** at the standard EMAN2 orientation |
| References | None |
| Target classes | 2–3 |

### Adapting to Your Workstation

**Threads:** Set `THREADS` in `run_pipeline.sh` to the number of **physical cores** on your machine. EMAN2 does not benefit from hyperthreading — use `lscpu | grep "Core(s) per socket"` and multiply by socket count. Oversubscribing with logical threads wastes memory and may slow alignment.

**Memory:** The PCA step loads all particles into RAM simultaneously. For N particles of box size B (voxels), the working set is roughly `N × B³ × 8 bytes` (float32 × real+imag after FFT). For this dataset (672 × 80³) that is ~11 GB. Ensure at least that much free RAM before running `e2spt_pcasplit.py`; the refinement step has a smaller footprint as particles are processed one at a time.

**GPU:** EMAN2's C++ core (`libEM2.so`) has CUDA support compiled out — `EMUtil::cuda_available()` always returns `false`. The GPU is not used by refinement, averaging, or PCA classification. It is only available to TensorFlow-backed tools (`e2classifycnn.py`) if TF finds a compatible CUDA runtime in the conda environment.

**RHEL PATH:** On RHEL, `conda activate` does not always prepend the environment's `bin/` ahead of `/usr/bin`, so `python` may resolve to the system Python. The manual step-by-step below includes `export PATH=".../envs/eman2/bin:$PATH"` — always include this when running steps outside the pipeline script.

**Disk:** Budget approximately: raw MRC stack (~400 MB for 672 × 80³ float32) + `particles.hdf` (~same) + `spt_01/` refinement outputs (~1–2 GB including half-maps) + each `sptcls_XX/` (~500 MB). A few GB is sufficient for a full run.

### Pipeline Logic

The pipeline has three phases:

1. **Data ingestion** — 672 individual MRC files are stacked into a single EMAN2 HDF file, a particle list (LST) is built, and a simple mean average is computed as an initial reference. No structural analysis happens here.

2. **Alignment refinement (1 iteration)** — `e2spt_refine.py` aligns each particle to the reference using cross-correlation in Fourier space. After one iteration every particle has a `xform.align3d` transform stored in `spt_01/particle_parms_01.json`. The post-processing step also produces `spt_01/mask_tight.hdf`, an auto-generated mask that concentrates the PCA on the particle density rather than surrounding noise.

3. **PCA classification** — `e2spt_pcasplit.py` reads the aligned particles and the mask, transforms each particle to Fourier space, low-pass filters to 30 Å, normalises per shell, and assembles a data matrix. Scikit-learn PCA reduces this to `nbasis` eigenvectors; K-Means then partitions the particles into `nclass` clusters.

**Why align before classifying?** PCA on unaligned particles finds orientation differences rather than structural heterogeneity. The one refinement iteration brings all particles to a common frame of reference so that the PCA captures conformational variance instead of rotational variance.

**Why Fourier-PCA?** Operating in Fourier space and normalising per shell makes the analysis resolution-dependent and de-emphasises shot noise at high spatial frequencies. The low-pass filter (`--maxres 30`) further suppresses noise beyond the expected information limit. This is more principled than voxel-space K-Means (see the Alternative below).

### Missing Wedge Handling

The particles were rotated post-extraction so that the pili axis aligns with Z. The missing wedge (the unsampled Fourier cone from ±60° tilt range) was rotated with the particles and is therefore **not** in the standard EMAN2 orientation (which assumes the tilt axis along Y, with the wedge aligned to Z).

Two consequences for every pipeline run:

- **In refinement — do not pass `--maxtilt`**. That flag zeros Fourier voxels assuming the wedge is at Y-axis, which would corrupt the wrong voxels. Instead, the `mean.tomo` averager uses per-shell statistical weighting (`wedgesigma=3.0`) to suppress low-SNR voxels without assuming a particular wedge geometry.
- **In classification — always pass `--nowedgefill`**. Without it, `e2spt_pcasplit.py` uses an amplitude-based heuristic to detect and zero wedge voxels — also assuming Y-axis orientation — which would zero signal in the wrong direction.

### Scripts

| File | Purpose |
|------|---------|
| `run_pipeline.sh` | Master pipeline: patches `np.int`, ingests data, runs refinement + PCA, enters interactive loop for re-running PCA with different parameters. Configuration variables (`NCLASS`, `NBASIS`, `MAXRES`, `THREADS`, `CLEAN`) are at the top of the file. Steps 2 (ingestion) and 3 (refinement) are skipped if their output files already exist — safe to re-run after interruption. |
| `make_project.py` | Reads all `aligned_tom*.mrc` files, stacks into `particles.hdf` with pixel size set to 13.328 Å, writes `ptcls.lst`, and computes a simple arithmetic mean as `initial_ref.hdf`. Takes ~1–2 min. If `particles.hdf` already exists it is deleted and rebuilt. |
| `patch_scripts.py` | Locates `e2spt_pcasplit.py` on PATH and replaces `r = r.astype(np.int)` with `r = r.astype(np.int64)` (NumPy 2.4.6 removed `np.int`). Backs up the original to `.bak` on first run. Idempotent — exits without changes if the patch is already applied. |
| `plot_pca.py` | Reads `pca_ptcls.txt` from the specified path (or auto-detects the latest `sptcls_XX/`). Plots pairwise scatter of the first three PCA components, saves `pca_scatter.png`. Uses non-interactive matplotlib backend (no display required). |
| `plot_class_averages.py` | Loads each `threed_NN.hdf` class average from the specified `sptcls_XX/` directory, extracts the central XY, XZ, and YZ slices, and saves a contrast-stretched PNG grid as `class_averages.png`. No display required. |

### Directory Layout

```
/home/ejl62/src/eman2_project/
├── run_pipeline.sh            # master pipeline script — run this
├── make_project.py            # data ingestion
├── patch_scripts.py           # np.int → np.int64 patch
├── plot_pca.py                # PCA scatter plot
├── plot_class_averages.py     # class average slice images
├── particles.hdf              # stacked HDF (672 particles)
├── ptcls.lst                  # EMAN2 particle list
├── initial_ref.hdf            # simple average used as refinement seed
├── refine.log                 # stdout from e2spt_refine.py
├── pca_classify.log           # stdout from e2spt_pcasplit.py
├── spt_01/                    # refinement output
│   ├── particle_parms_01.json # per-particle xform.align3d + score
│   ├── threed_01.hdf          # refined average
│   ├── threed_01_even.hdf
│   ├── threed_01_odd.hdf
│   ├── mask_tight.hdf         # auto-generated mask (used by pcasplit)
│   ├── fsc_masked_01.txt
│   └── fsc_unmasked_01.txt
└── sptcls_XX/                 # pcasplit output (auto-numbered per run, zero-based)
    ├── ptcls_cls01.lst        # class 1 particle list (one-based)
    ├── ptcls_cls02.lst        # class 2 particle list
    ├── pca_ptcls.txt          # particle IDs + PCA coordinates
    ├── pca_scatter.png        # scatter plot (written by plot_pca.py)
    ├── class_averages.png     # central slices grid (written by plot_class_averages.py)
    ├── pca_basis.hdf          # PCA eigenvector volumes
    ├── particle_parms_01.json # class 1 alignment subset
    ├── particle_parms_02.json # class 2 alignment subset
    ├── threed_01.hdf          # class 1 average (one-based)
    └── threed_02.hdf          # class 2 average
```

### How to Run

**Quick start:**

```bash
cd /home/ejl62/src/eman2_project
./run_pipeline.sh
```

`run_pipeline.sh` activates the conda environment itself — no manual `conda activate` needed.

**Manual step-by-step** (if the pipeline script fails or you need to run steps individually):

```bash
cd /home/ejl62/src/eman2_project
source /home/ejl62/miniforge3/etc/profile.d/conda.sh && conda activate eman2
export PATH="/home/ejl62/miniforge3/envs/eman2/bin:$PATH"
# The export is required — without it, `python` may resolve to the system Python

python patch_scripts.py
python make_project.py

e2spt_refine.py ptcls.lst --ref initial_ref.hdf --path spt_01 \
  --niter 1 --sym c1 --threads 24 --verbose 1

e2spt_pcasplit.py --path spt_01 --iter 1 \
  --nclass 2 --nbasis 8 --maxres 30 --sym c1 --nowedgefill --verbose 1

python plot_pca.py
python plot_class_averages.py
```

**Interactive classification loop** (entered automatically by `run_pipeline.sh` after each PCA run):

```
Options:
  [Enter]   Accept — exit the loop
  n <N>     Change --nclass to N       (e.g. 'n 3')
  b <N>     Change --nbasis to N       (e.g. 'b 10')
  r <N>     Change --maxres to N Å     (e.g. 'r 40')
  c         Toggle --clean             (remove outliers before PCA)
  q         Quit without saving
```

Each re-run of PCA creates a new auto-numbered `sptcls_XX/` directory; previous results are never overwritten.

### Classification Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--nclass` | 2 | Number of K-Means clusters. Start with 2; try 3 if the scatter shows three distinct groups. |
| `--nbasis` | 8 | PCA components retained before clustering. 5–10 is typical; more components capture subtler variance. |
| `--maxres` | 30 Å | Low-pass filter applied before PCA. 30 Å is a safe margin above the 26.7 Å Nyquist. Try 40 Å if structure is not visible. |
| `--sym` | c1 | No symmetry imposed — pili may have helical symmetry but classify without it first. |
| `--nowedgefill` | always on | **Required for this dataset** — wedge is not at EMAN2's expected Y-axis orientation. |
| `--clean` | off | Remove statistical outliers (>2σ from PCA centroid) before fitting K-Means. Enable if scatter shows a fringe of isolated points. |

**Interpreting the scatter plot:**

| Pattern | Interpretation | Action |
|---------|---------------|--------|
| 2–3 tight clusters | Distinct structural classes | Accept; `--nclass` should match cluster count |
| Continuous cloud | Conformational continuum | Classes are still meaningful; boundaries are soft |
| Outlier fringe | Junk/damaged particles | Re-run with `--clean` |
| Uniform noise | No separable signal | Try `--maxres 40` or `--nbasis 12` |

### Alternative: Direct K-Means

Does not require alignment — operates on the raw HDF stack in voxel space. Less principled than Fourier-PCA (no missing wedge handling, no dimensionality reduction) but fast and useful as a sanity check:

```bash
e2classifykmeans.py particles.hdf --ncls 2 --normalize --verbose 1
```

### Expected Resolution After Per-Class Refinement

With ~300–400 particles per class at 13.328 Å/px, expect **~30–50 Å resolution** from gold-standard FSC after 3–5 iterations of per-class refinement.

### Current Pipeline State

- `spt_01/` — refinement complete (1 iteration); `particle_parms_01.json` and `mask_tight.hdf` present
- `sptcls_00/` — first PCA run (2 classes, `--nowedgefill`)
- `sptcls_01/` — second PCA run (2 classes, `--nowedgefill`); includes `pca_scatter.png`

---

## PCA Classification Pipeline Outputs

Each run of the PCA classification step (`e2spt_pcasplit.py`) produces a new auto-numbered directory `sptcls_XX/` (zero-based, incremented on every run). The directory contains the following files:

| File | Written by | Description |
|------|-----------|-------------|
| `ptcls_cls01.lst` … `ptcls_clsNN.lst` | `e2spt_pcasplit.py` | Per-class particle lists in LST format. One-based class numbering. Each line: `index  particles.hdf  particle_index`. These are the primary output used for downstream per-class refinement. |
| `pca_ptcls.txt` | `e2spt_pcasplit.py` | Space-separated text file with one row per particle. Column 0 is the particle index; columns 1…N are the coordinates along each PCA component. Used by `plot_pca.py` to produce scatter plots. |
| `pca_basis.hdf` | `e2spt_pcasplit.py` | HDF stack of the PCA basis volume images (one per basis vector). Useful for inspecting what structural variation each principal component captures. |
| `threed_01.hdf` … `threed_NN.hdf` | `e2spt_average.py` (called by pcasplit) | Post-processed 3D class average volumes, one per class. One-based numbering. Each has been through `e2refine_postprocess.py`: FSC-weighted filtering, masking, and amplitude correction. |
| `particle_parms_01.json` … `particle_parms_NN.json` | `e2spt_average.py` (called by pcasplit) | Per-class alignment JSON. Same format as the main refinement output — keys are `"('path', index)"` tuples, values contain `xform.align3d` and `score`. One file per class. |
| `pca_scatter.png` | `plot_pca.py` (project script) | Scatter plots of PC1–PC3 pairs, one panel per pair. Points represent individual particles. Used to assess cluster separation visually. |
| `class_averages.png` | `plot_class_averages.py` (project script) | Central orthogonal slices (XY, XZ, YZ) of each class average volume, displayed in a grid (one row per class). Contrast-stretched per slice using the 1st–99th percentile. Useful for quick visual comparison of class density maps. |

**Notes on numbering:** `e2spt_pcasplit.py` uses one-based numbering for class files inside each `sptcls_XX/` directory, but zero-based numbering for the directory itself (`sptcls_00`, `sptcls_01`, …). The `threed_NN.hdf` files use a two-digit zero-padded suffix matching the class index (e.g. `threed_01.hdf` = class 1).

**Downstream use:** The `ptcls_clsNN.lst` files are the intended input for per-class refinement:
```bash
e2spt_refine.py sptcls_XX/ptcls_cls01.lst \
  --ref sptcls_XX/threed_01.hdf \
  --path spt_cls01 --niter 3 --sym c1 --threads 24 --goldstandard 30
```

---

## Post-Classification Next Steps

After accepting a classification result in `sptcls_XX/`, the following steps are available depending on what you want to achieve.

---

### 1. Per-Class Iterative Refinement

Run independent refinement on each class to improve alignment and resolution. Use the class average as the starting reference and the class particle list as input. Gold-standard FSC requires at least ~100 particles per class to be meaningful.

```bash
# Repeat for each class (adjust CLS= and path accordingly)
CLS=01
e2spt_refine.py sptcls_XX/ptcls_cls${CLS}.lst \
  --ref sptcls_XX/threed_${CLS}.hdf \
  --path spt_cls${CLS} \
  --niter 5 \
  --sym c1 \
  --threads 24 \
  --goldstandard 30 \
  --verbose 1 \
  2>&1 | tee refine_cls${CLS}.log
```

After refinement, `spt_cls01/threed_05.hdf` (final iteration) is the refined class average and `spt_cls01/fsc_masked_05.txt` gives the gold-standard resolution.

---

### 2. Check Resolution (FSC)

The FSC curve is written automatically after each refinement iteration. To read the resolution from an existing FSC file:

```bash
# Print the FSC file — columns are: spatial_frequency  FSC_value
# Resolution at FSC=0.143 (gold-standard criterion):
awk '$2 <= 0.143 {print "Resolution at FSC=0.143:", 1/$1, "Angstroms"; exit}' \
  spt_cls01/fsc_masked_05.txt
```

To recompute FSC between two half-maps manually (e.g. after external masking):

```bash
e2proc3d.py spt_cls01/threed_05_even.hdf fsc_manual.txt \
  --calcfsc spt_cls01/threed_05_odd.hdf
```

---

### 3. Further Sub-Classification of a Single Class

If one class is still heterogeneous, run PCA classification on its particle list. Point `--path` at the per-class refinement directory that contains the alignment JSON.

```bash
e2spt_pcasplit.py \
  --path spt_cls01 \
  --iter 5 \
  --nclass 3 \
  --nbasis 8 \
  --maxres 30 \
  --sym c1 \
  --nowedgefill \
  --verbose 1 \
  2>&1 | tee pca_cls01.log

# Plot the new sub-classification
python eman2_project/plot_pca.py sptcls_XX/pca_ptcls.txt
python eman2_project/plot_class_averages.py sptcls_XX
```

---

### 4. Export Class Averages to MRC (for ChimeraX, RELION, etc.)

Other software (ChimeraX, UCSF Chimera, RELION, Dynamo) reads MRC format. Convert with `e2proc3d.py`:

```bash
# Convert a single class average
e2proc3d.py sptcls_XX/threed_01.hdf sptcls_XX/threed_01.mrc

# Convert all class averages at once
for f in sptcls_XX/threed_*.hdf; do
    e2proc3d.py "$f" "${f%.hdf}.mrc"
done
```

If the pixel size header is wrong, set it explicitly:

```bash
e2proc3d.py sptcls_XX/threed_01.hdf sptcls_XX/threed_01.mrc --apix 13.328
```

---

### 5. Apply Symmetry to a Class Average

If a class average displays symmetry that was not enforced during refinement, apply it post-hoc:

```bash
# Example: apply C4 symmetry
e2proc3d.py sptcls_XX/threed_01.hdf sptcls_XX/threed_01_c4.hdf --sym c4

# Then recheck FSC with the symmetrised map (compare against the unsymmetrised half-maps)
e2proc3d.py sptcls_XX/threed_01_c4.hdf fsc_sym.txt \
  --calcfsc spt_cls01/threed_05_odd.hdf
```

---

### 6. Mask and Filter a Class Average

Generate a tight mask and apply a resolution-matched low-pass filter for figure-quality display:

```bash
# Auto-generate a mask from the density (threshold at 0.5× maximum)
e2proc3d.py sptcls_XX/threed_01.hdf sptcls_XX/mask_cls01.hdf \
  --process mask.auto3d:threshold=0.5:radius=5:nshells=5:nshellsgauss=5

# Apply the mask and low-pass filter to the final average
e2proc3d.py sptcls_XX/threed_01.hdf sptcls_XX/threed_01_masked.hdf \
  --multfile sptcls_XX/mask_cls01.hdf \
  --process filter.lowpass.gauss:cutoff_freq=0.1
```

---

### 7. Interactive 3D Display

EMAN2's built-in viewer can display volumes and stacks interactively (requires a display):

```bash
# View all class averages as a stack
e2display.py sptcls_XX/threed_01.hdf sptcls_XX/threed_02.hdf

# View PCA basis volumes
e2display.py sptcls_XX/pca_basis.hdf
```

---

### 8. Count Particles Per Class

Quick sanity check on class sizes before committing to per-class refinement:

```bash
for f in sptcls_XX/ptcls_cls*.lst; do
    echo "$(basename $f): $(wc -l < $f) particles"
done
```

Classes with fewer than ~50–100 particles at this pixel size (13.328 Å/px) will not yield a meaningful gold-standard FSC and should either be merged with a neighbouring class or discarded.
