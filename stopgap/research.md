# STOPGAP 0.7.5 — Deep Technical Research Report

## Table of Contents

- [Shared Files Setup](#shared-files-setup)
- [Overview](#overview)
- [Repository Layout](#repository-layout)
- [Central Data Structures](#central-data-structures)
- [Euler Angle Convention](#euler-angle-convention)
- [File Formats](#file-formats)
- [The Execution Model](#the-execution-model)
- [Pipeline Modules in Detail](#pipeline-modules-in-detail)
- [Signal Processing](#signal-processing)
- [Filtering Infrastructure](#filtering-infrastructure)
- [Parameter Configuration System](#parameter-configuration-system)
- [Toolbox (`sg_toolbox/`)](#toolbox-sg_toolbox)
- [Notable Implementation Details](#notable-implementation-details)
- [Typical User Workflow](#typical-user-workflow)
- [Version History Highlights](#version-history-highlights-from-changestxt-and-stopgap_075md)
- [Performance Optimizations Applied (2026-06-02)](#performance-optimizations-applied-2026-06-02)
- [Summary](#summary)
- [Compilation Notes (BYU HPC, R2023b)](#compilation-notes-byu-hpc-r2023b)
- [Practical Setup Guide for Classification (BYU HPC)](#practical-setup-guide-for-classification-byu-hpc)

---

## Shared Files Setup

Place files from the shared archive into a fresh STOPGAP 0.7.5 source tree as described below. For step-by-step usage instructions see the [Practical Setup Guide for Classification (BYU HPC)](#practical-setup-guide-for-classification-byu-hpc); for the general end-to-end pipeline see [Typical User Workflow](#typical-user-workflow).

### Classification scripts → `STOPGAP/`

Copy each script to the root of the STOPGAP source directory.

| File | What it does |
|------|-------------|
| `compileStopgap.sh` | Compiles all four STOPGAP binaries from source using MATLAB R2023b `mcc`. Submit as a SLURM job. Only needed if binaries are missing or MCR is updated. |
| `createStopgapInputs.m` | MATLAB script run once per project from `subtomo_project/`. Reads pre-extracted subvolumes, creates numbered symlinks, and writes the initial motivelist, wedgelist, per-halfset references, and masks. |
| `subtomoParams.sh` | Calls the STOPGAP parser three times to write `params/subtomo_param.star`: a 6-iteration alignment schedule (3 blocks × 2 iterations each) with stochastic hill-climb (`shc`), coarse cone sampling, and per-block phi narrowing (±180° → ±15° → ±9°). |
| `runClassification.sh` | Main SLURM job. Runs the full pipeline sequentially: 6-iteration subtomogram alignment → PCA covariance decomposition → k-means clustering into 3 classes. Wraps every watcher invocation in a crash sentinel (`run_watcher_guarded`) that aborts within ~20 s if any worker writes a `crash_*` marker, plus pre-flight input checks, an ERR trap, and post-phase output/warning surfacing — so failures land in `logs/` instead of hanging silently (see [§7](#7--silent-failure-guards-robustness)). |
| `plotPCA.py` | Python script (requires conda env `stopgap` with numpy + matplotlib). Reads `eigenfac.star` and `motl_classified.star`; saves pairwise PC scatter plots (PC1–PC4) and a scree plot to a specified output directory. |
| `runPostClassification.sh` | Post-classification SLURM job. Phase A: activates conda env `stopgap` and runs `plotPCA.py`. Phase B: seeds per-class references from the final consensus halfset refs, generates `params/multiclass_param.star`, and runs `ali_multiclass` (no angular search) to produce one averaged reference per class. |

### Edited STOPGAP files → replace in-place

Modified versions of files that ship with STOPGAP 0.7.5. Copy them over the originals before running anything.

| File | Destination in `STOPGAP/` | Why it was changed |
|------|--------------------------|-------------------|
| `stopgap_config_slurm.sh` | `exec/lib/stopgap_config_slurm.sh` | Fixes `${LD_LIBRARY_PATH}` unbound-variable crash under `set -o nounset` (see [Compilation Notes](#compilation-notes-byu-hpc-r2023b)) |
| `stopgap_parser.sh` | `exec/bin/stopgap_parser.sh` | Updated to source `stopgap_config_slurm.sh` instead of the nonexistent `stopgap_config.sh` |
| `src/func/calculate_flcf.m` | `src/func/calculate_flcf.m` | Added optional 5th argument `fmask_in`; when provided, skips `fftn(mask)` (saves one FFT per angle for rotation-invariant masks). Backward-compatible — all TM callers pass only 4 args. |
| `src/subtomo/func/flcf_subtomo_scoring_function.m` | `src/subtomo/func/flcf_subtomo_scoring_function.m` | `'init'` case now detects spherical masks via a test rotation and precomputes their FFTs into `o.fmask_cache`. `'score'` case skips `sg_rotate_vol` for spherical alignment and CC masks, and passes the cached FFT to `calculate_flcf`. |
| `src/func/check_crashes.m` | `src/func/check_crashes.m` | Now aborts the watcher on the **first** worker crash (was: only when *all* cores crashed). A single dead core can never complete its packets, so the old behavior left the watcher polling forever until SLURM wall-time killed the job silently. ⚠️ Compiled into `stopgap_watcher` — requires recompile (`compileStopgap.sh`) to take effect; the bash crash sentinel in `runClassification.sh` covers the same failure mode without recompiling. See [§7](#7--silent-failure-guards-robustness). |

### Compiled binaries → `STOPGAP/exec/lib/`

Pre-compiled against MATLAB R2023b MCR. Copy all four files into `exec/lib/` and mark them executable.

| Binary | Role |
|--------|------|
| `stopgap` | Main alignment/averaging worker |
| `stopgap_watcher` | Job orchestrator — reads param file, dispatches workers, monitors completion |
| `stopgap_parser` | Generates and updates parameter STAR files |
| `sg_toolbox` | Standalone toolbox binary for post-processing utilities |

```bash
cp matlabr2023bCompiledBinaries/* STOPGAP/exec/lib/
chmod +x STOPGAP/exec/lib/stopgap STOPGAP/exec/lib/stopgap_watcher \
         STOPGAP/exec/lib/stopgap_parser STOPGAP/exec/lib/sg_toolbox
```

---

## Overview

STOPGAP (Subtomogram Processing and General Analysis Package) is a MATLAB software package for **cryo-electron tomography (cryo-ET) subtomogram averaging**. Its primary purpose is high-resolution structural determination of macromolecular complexes inside cellular tomograms, executed efficiently on HPC clusters or local multi-core systems. The current release is version 0.7.5.

The package covers the full cryo-ET STA pipeline:

| Module | Purpose |
|--------|---------|
| **Template Matching (TM)** | Find particle positions and initial orientations in raw tomograms |
| **Subtomogram Averaging (subtomo)** | Iterative angular refinement and consensus average generation |
| **Extraction (extract)** | Cut individual subtomogram volumes from full tomograms |
| **PCA** | Principal-component-based classification and variability analysis |
| **VMAP** | Variance mapping (amplitude-weighted phase differences) |
| **Tube Power Spectrum (TPS)** | Azimuthally-averaged power spectra for helical structures |

---

## Repository Layout

```
STOPGAP/
├── exec/           Shell execution layer (bash scripts, SLURM config, watcher helpers)
│   ├── bash/       User-facing launcher scripts
│   ├── bin/        Low-level wrapper scripts (MCR, parser, toolbox, watcher)
│   └── lib/        Configs (global_settings.txt, SLURM/local setup scripts)
├── sg_toolbox/     Standalone MATLAB toolbox — utility functions, geometry, I/O
│   ├── io/         Per-module parameter read/write helpers (subtomo, tm, pca, tps, vmap)
│   ├── other/      Basic rotation matrices (Rx, Ry, Rz)
│   ├── private/    Internal helpers (FSC helpers, motl field definitions)
│   ├── standalone/ Compiled toolbox entry point
│   └── tom/        Third-party rotation code (tom_rotate*)
└── src/            Core MATLAB source — all pipeline modules
    ├── extract/    Extraction (exec, func, parser, watcher)
    ├── func/       Shared utilities used by all modules
    ├── io/         Low-level file I/O (MRC, EM, STAR, wedgelist, motl)
    ├── pca/        PCA (exec, func, parser, watcher)
    ├── stopgap/    Package entry points + compiler scripts
    ├── subtomo/    Subtomogram alignment/averaging (exec, func, parser, watcher)
    ├── tm/         Template matching (exec, func, parser, watcher)
    ├── tube_ps/    Tube power spectrum (exec, func, parser, watcher)
    └── vmap/       Variance maps (exec, func, parser, watcher)
```

Each pipeline module follows the same four-subfolder pattern: **exec** (top-level orchestrators), **func** (module-specific helpers), **parser** (parameter file parsing), **watcher** (job progress monitoring).

---

## Central Data Structures

### The Motivelist (motl)

The motivelist is the spine of the entire package. Every particle tracked by STOPGAP has one or more entries here. Fields (from `sg_toolbox/sg_get_motl_fields.m`):

| Field | Type | Description |
|-------|------|-------------|
| `motl_idx` | int | Unique particle identifier (groups multiple entries from the same physical particle) |
| `tomo_num` | int | Tomogram number the particle lives in |
| `object` | int | Object/region identifier within the tomogram |
| `subtomo_num` | int | Extracted subtomogram file index |
| `halfset` | string | Half-dataset assignment (`'A'` or `'B'`) for gold-standard FSC |
| `orig_x, orig_y, orig_z` | float | Particle position in the full tomogram (pixels) |
| `score` | float | Best alignment/matching score |
| `x_shift, y_shift, z_shift` | float | Refined sub-pixel shifts from the current reference frame |
| `phi, psi, the` | float | Euler angles describing current orientation (ZXZ convention, degrees) |
| `class` | int | Reference class number for multi-reference averaging |

**Storage**: STAR format (`.star` files). Human-readable, portable, extendable.

**Type 1 vs Type 2**: Two internal format variants exist (`sg_motl_convert_type1_to_type2.m`). Type 2 allows multiple entries per `motl_idx` (e.g., multi-reference scoring). Conversion utilities are provided.

**Halfset assignment** is random per iteration (seeded per iteration) to avoid systematic bias. Halfsets enable independent half-map averaging for unbiased FSC calculation.

---

### The Wedgelist

One row per tomogram; stores imaging metadata needed to compute missing-wedge masks and CTF filters. Every unique `tomo_num` value in the motivelist must have a corresponding wedgelist entry — missing entries cause worker crashes at runtime.

| Field | Description |
|-------|-------------|
| `tomo_num` | Tomogram index |
| `tilt_angle` | Array of tilt angles used during acquisition (typically ±60°) |
| `defocus` | Underfocus value in micrometers (optional; required for CTF correction) |
| `pixelsize` | Pixel/voxel size in Ångströms |
| `exposure` | Cumulative electron dose in e⁻/Å² (optional; for dose weighting) |
| `tomo_x, tomo_y, tomo_z` | Tomogram box dimensions in voxels |

Read/written with `sg_toolbox/sg_wedgelist_read.m` and `sg_wedgelist_write.m`.

---

### The Reflist

A list of reference volumes used for multi-reference averaging. Entries specify file paths to `.mrc` reference volumes, one per class. Managed via `sg_toolbox/sg_reflist_read.m`, `sg_reflist_write.m`, `sg_reflist_add_entry.m`.

---

## Euler Angle Convention

STOPGAP adopts the **AV3 ZXZ convention** (same as MATLAB's `euler2matrix` in many cryo-EM packages):

- **φ (phi)**: first rotation about Z axis
- **θ (the)**: rotation about the (new) X axis
- **ψ (psi)**: second rotation about the (new) Z axis

Rotation matrix (from `sg_toolbox/sg_euler2matrix.m`):
```
R = Rz(φ) · Rx(θ) · Rz(ψ)
```

Euler angles are normalized to `[0, 360)` after each iteration (`sg_motl_normalize_euler_angles.m`). Conversion utilities exist for ZYZ→ZXZ, quaternion↔Euler, axis-angle↔quaternion, etc.

---

## File Formats

### MRC

The dominant 3D volume format for tomograms, subtomograms, reference maps, and masks.

- **Header**: 256 × int32 words (1024 bytes) describing dimensions, data type, pixel size, labels
- **Data types supported**: int8, int16, uint16, float32
- **Read/write**: `sg_toolbox/sg_mrcread.m`, `sg_mrcwrite.m`; low-level `src/io/read_mrc.m`, `write_mrc.m`

### EM

Alternative volumetric format (IMOD convention). Supported but less common.

- **Read/write**: `sg_toolbox/sg_emread.m`, `sg_emwrite.m`

### STAR

Plain-text relational table format (borrowed from RELION). Used for:
- Motivelists
- Wedgelists
- Parameter files
- Timing logs
- Template lists, reference lists

Structure:
```
data_stopgap_motivelist
loop_
_motl_idx
_tomo_num
...
1   1   0   1   h1   100.5   200.3   ...
```

Read/write via `sg_toolbox/stopgap_star_read.m`, `stopgap_star_write.m`.

### Parameter Files (`.star`)

Each pipeline module maintains a STAR-format parameter file (e.g., `subtomo_param.star`, `tm_param.star`). These contain:
- Task blocks (one per planned iteration)
- Status flags (boolean fields indicating step completion)
- Algorithm settings (scoring function, CTF flags, filter parameters, etc.)
- I/O paths (directories, filename roots)

The **watcher** pattern advances through tasks by finding the first task block with incomplete status flags, then marking flags complete once each parallel step finishes.

---

## The Execution Model

### Parallelization Architecture

STOPGAP uses a **three-layer parallel model**:

1. **MPI layer**: Multiple compute nodes launched via SLURM (`exec/lib/stopgap_config_slurm.sh`) or local MPI (`exec/lib/stopgap_config_local.sh`). Each process is assigned a unique integer `procnum` from 1 to `n_cores`.

2. **Packet layer**: Work (particles or tomogram tiles) is split into `n_packets = n_cores × packets_per_core` (default 2×). Cores claim packets dynamically — faster cores pick up leftover packets after finishing their own. This achieves near-linear scaling.

3. **Inner loop**: Within a packet, computation is serial (per particle, per angle).

### Synchronization via Filesystem Markers

All inter-process coordination is done by **creating empty directories** (atomic `mkdir` acts as a lock-free flag):

```
communication/
  alipacket_{n}/          → Packet n has been claimed
  sg_ali_{procnum}/       → Core procnum finished all alignment packets
  sg_p_avg_{procnum}/     → Core procnum finished parallel averaging
  sg_f_avg_{class}/       → Final average for class complete
  complete_stopgap_ali/   → Entire iteration done
```

Core 1 acts as coordinator: it watches for all-cores-done flags, triggers final assembly, updates the parameter file, then either loops for the next iteration or exits.

### The Watcher Pattern

`src/stopgap/stopgap_watcher.m` and per-module variants (`subtomo_watcher.m`, `stopgap_tm_watcher.m`, etc.) implement the following loop:

1. Read parameter file, find next incomplete task
2. Prepare job parameters; distribute across cores
3. Call parallel execution function
4. Watch for completion flags
5. Call final assembly function
6. Update parameter file (mark task complete, advance iteration counter)
7. Repeat

### Local Data Copying (HPC Optimization)

When `copy_local=1` is set:
- The first core on each physical node copies required tomograms and references to node-local SSD or ramdisk
- Other cores on the same node read from local storage instead of NFS
- After computation, results are copied back to the shared filesystem
- Implemented in `src/func/check_copy_local.m`, `copy_file_to_local_temp.m`, `tm_check_copy_local.m`, etc.

This dramatically reduces I/O bottlenecks on large HPC clusters.

---

## Pipeline Modules in Detail

### 1. Template Matching (`src/tm/`)

**Entry point**: `src/tm/exec/stopgap_template_match.m`

**Purpose**: Exhaustive 6D cross-correlation search (3 translational + 3 rotational DOF) to find all candidate particle positions and orientations in raw tomograms.

#### Algorithm

**Setup** (`prepare_parallel_tm.m`):
- Divide the tomogram into **overlapping tiles** of size `tilesize + template_size`
  - Tiling prevents boundary artefacts and enables coarse parallelization
  - Each tile is processed independently; scores from overlapping regions are reconciled in the final step
- Build a **matchlist** of (tile_idx, angle_idx) pairs — the unit of parallel work
- Distribute matchlist into packets for load-balanced parallel execution

**Per-tile computation** (`stopgap_parallel_tm.m`):
For each (tile, angle) pair in the core's packets:
1. Load tile from disk (or local temp)
2. Read and rotate the template and its mask by the trial Euler angles
3. Apply bandpass filter to the rotated template
4. Pad template to tile size
5. Normalize template under its soft mask (zero mean, unit std)
6. Compute the **Fast Local Correlation Function (FLCF)** between tile and template
7. Find the maximum FLCF value and its location
8. Optionally compute a noise-reference correlation for significance testing
9. Accumulate into partial score map, orientation map, and (optionally) noise map

**Final assembly** (`stopgap_final_tm.m`):
- For each tomogram, read all partial maps from all cores
- For each voxel, retain the angle with the highest score across all partials
- Optional noise subtraction: `score_final = score - noise_score`
- Apply tomogram boundary mask (edges excluded)
- Output complete score map, orientation index map, optional template index map

**Outputs** per tomogram:
| File | Content |
|------|---------|
| `smap_*.mrc` | Correlation score volume |
| `omap_*.mrc` | Best-angle index volume (lookup into angle list) |
| `noise_*.mrc` | Noise correlation map (optional) |
| `tmap_*.mrc` | Template index map (multi-template mode) |

After TM, `sg_toolbox/sg_tm_generate_motl.m` converts the score/orientation maps to an initial motivelist by peak-picking above a user-defined threshold.

---

### 2. Subtomogram Alignment & Averaging (`src/subtomo/`)

**Entry point**: `src/subtomo/exec/stopgap_subtomo.m`

**Purpose**: Iterative refinement of particle positions and orientations against a reference structure, followed by weighted averaging to generate a higher-resolution consensus map.

#### Alignment Step (`align_subtomos.m`)

**Setup**:
- Load motivelist, references, and masks
- Build angular search grid (`compose_search_eulers.m`): exhaustive (full sphere), cone (around current orientation), or limited angular range
- Initialize Fourier-crop indices if `fcrop=true`
- Initialize per-tomogram filter cache (`initialize_subtomo_filters.m`)

**Per-particle loop** (parallel over packets):
1. Load subtomogram from disk
2. For the current Euler angles (from motivelist):
   a. Iterate over all trial rotation offsets in the search list
   b. For each trial: rotate the reference, apply filters, compute score via the active scoring function
   c. Track the best-scoring angle and shift
3. Update motivelist entry with best angle and refined shift
4. Write partial motivelist to disk

**Scoring functions** (selectable via parameter):

| Mode | Function | Description |
|------|----------|-------------|
| `flcf` | `flcf_subtomo_scoring_function.m` | Fourier-domain fast local correlation (default) |
| `pearson` | `pearson_subtomo_scoring_function.m` | Real-space Pearson; fminsearch for shift refinement |

FLCF is the default and is significantly faster. Pearson is more flexible and can be used when precise shift refinement is critical.

**Search strategies** (selectable):
- **Exhaustive**: Full angular search over all entries in the search list
- **Stochastic**: Hill-climbing — exit early when score improves (faster; may miss global optimum)
- **Simulated annealing**: Probabilistically accept downhill steps (slower; better at escaping local minima)

**Assembly** (`assemble_new_motl.m`):
- Core 1 waits for all alignment completion flags
- Reads `splitmotl_{procnum}.star` from each core
- Merges by `motl_idx`, normalizes Euler angles
- Writes the updated motivelist as `{motl_name}_{iter+1}.star`

#### Averaging Step (`parallel_average.m` + `final_average.m`)

**Parallel averaging**:
- Each core processes its batch of particles
- Per particle (score must exceed threshold):
  1. Load subtomogram
  2. Optionally upsample (supersampling mode)
  3. Rotate/shift into reference frame using best Euler angles + shifts
  4. Apply per-particle weights (wedge, CTF, exposure, score-based)
  5. Accumulate into halfset sums and weight accumulators

**Final averaging**:
1. Sum partial volumes across all cores
2. Divide by weight accumulator (Fourier-space normalization)
3. Compute **FSC** between halfsets (with phase-randomization bias correction)
4. Compute **Figure of Merit (FOM)**: `C = sqrt(2|FSC| / (1 + |FSC|))`
5. Apply FOM weighting: `avg_final = (h1·C + h2·C) / (2C)`
6. Write halfset averages, weighted average, and FSC data

---

### 3. Subtomogram Extraction (`src/extract/`)

**Entry point**: `src/extract/exec/stopgap_extract_subtomos.m`

**Purpose**: Cut cubic boxes from full tomograms at the positions specified in the motivelist.

**Algorithm** (`extract_subtomos.m`):
1. Load motivelist; group particles by tomogram
2. For each tomogram:
   a. Load the full 3D volume into memory
   b. Optionally compute a pixel-size rescaling factor
   c. For each particle position (`orig_x, orig_y, orig_z`):
      - Extract a `boxsize³` voxel cube centered at that position
      - Handle out-of-bounds gracefully (zero-pad or skip)
      - Optionally rescale to target pixel size (Fourier-based rescaling)
      - Write to disk as `subtomo_{subtomo_num}.{ext}`
3. Write completion markers

**Output**: One file per particle, named by `subtomo_num`. Format determined by `ext` parameter (`.mrc` or `.em`).

**Tomolist mode**: For fresh extractions, `extract_initialize_tomolist.m` builds a tomolist from the wedgelist specifying which tomogram files to open.

---

### 4. PCA Classification (`src/pca/`)

**Entry point**: `src/pca/exec/stopgap_pca.m`

**Purpose**: Identify conformational heterogeneity; classify particles into distinct states using principal component analysis.

**Tasks** (each is a separately scheduled step):

| Task | Function | Description |
|------|----------|-------------|
| `rot_vol` | `pca_prerotate_volumes.m` | Rotate all particles into the reference frame using refined Euler angles |
| `calc_ccmat` | `pca_calculate_ccmatrix.m` | Compute pairwise cross-correlation matrix between all pre-rotated particles |
| `calc_pca_ccmat` | `pca_ccmat_calculate_eigenfactors.m` | Eigendecompose the CC matrix; compute eigenvectors and eigenvalues |
| `calc_covar` | `pca_calculate_covariance_matrix.m` | Direct covariance matrix from density differences (alternative to CC matrix) |
| `calc_eigenval` | `pca_calculate_eigenvalues.m` | Eigenvalues from covariance matrix |
| `calc_eigenvec` | `pca_calculate_eigenvectors_parallel.m` | Parallel eigenvector computation |

**Classification** (`sg_toolbox/sg_pca_kmeans_cluster.m`, `sg_pca_hierarchical_cluster_references.m`):
- Particles projected onto eigenvector basis → per-particle component scores
- k-means or hierarchical clustering in PC space assigns class labels
- Class labels written back into the motivelist `class` field

**Dataset-size notes**: `calc_covar` scales as O(N²) in particle count — for 672 particles this is trivial. With 672 particles, reliable separation into more than ~3–5 classes is statistically marginal; fewer classes yield more trustworthy results.

---

### 5. Variance Mapping (`src/vmap/`)

**Entry point**: `src/vmap/exec/stopgap_vmap.m`

**Purpose**: Generate voxel-wise heterogeneity maps using **amplitude-weighted phase differences** (Himes & Bharat method).

**Algorithm** (`parallel_vmap.m`, `final_vmap.m`):
1. For each particle, rotate into reference frame
2. Compute the amplitude-weighted phase difference relative to the reference at each voxel
3. Sum across all particles and normalize
4. Output: 3D variance map highlighting structurally variable regions

Variance maps complement FSC (which gives a global resolution estimate) by localizing *where* variability occurs — useful for identifying flexible domains, conformational states, or heterogeneity from sample preparation.

---

### 6. Tube Power Spectrum (`src/tube_ps/`)

**Entry point**: `src/tube_ps/exec/stopgap_tube_ps.m`

**Purpose**: Compute azimuthally-averaged power spectra for helical/tubular structures to analyze helical symmetry parameters.

**Algorithm** (`tps_parallel_ps.m`):
1. Load motivelist and a radius list defining the tube geometry
2. For each particle:
   - Rotate into reference frame using refined Euler angles
   - For each radial layer (defined in radius list):
     - Extract a cylindrical shell
     - Unwrap from Cartesian to cylindrical coordinates
     - Fourier transform each radial slice
     - Accumulate amplitudes
3. Sum across particles, normalize
4. Output: 2D power spectrum image (radial frequency × axial frequency)

The resulting spectrum can be used to determine the helical rise, twist, and symmetry order, or to diagnose alignment quality for helical assemblies.

---

## Signal Processing

### Fast Local Correlation Function (FLCF)

**Reference**: Roseman (2003), doi:10.1016/S0304-3991(02)00333-9

**Implementation**: `src/func/calculate_flcf.m`

The FLCF computes normalized cross-correlation in Fourier space, where the local variance of the target under a sliding mask is also computed via FFTs:

```
numerator = IFFT( FFT(reference) · conj(FFT(particle)) )

σ_particle(r) = sqrt[ IFFT(FFT(mask) · conj(FFT(particle²)))/N
                     − (IFFT(FFT(mask) · conj(FFT(particle)))/N)² ]

FLCF(r) = numerator(r) / (N · σ_ref · σ_particle(r))
```

Where N is the number of voxels under the mask. All three FFT pairs are computed once per reference rotation, making the inner loop over translations very cheap.

**Sphere mask optimization**: `calculate_flcf` accepts an optional 5th argument `fmask_in`. When provided, `fftn(mask)` is skipped and the pre-computed value is used directly. `flcf_subtomo_scoring_function` detects spherical masks at 'init' time (one 90° test rotation; negligible cost), caches `fftn(mask)` in `o.fmask_cache`, and also skips the two `sg_rotate_vol` calls per angle evaluation (rotating a sphere is a mathematical no-op). Combined, this eliminates 2 of the ~3 `sg_rotate_vol` calls and 1 of the ~7 FFTs per angle, roughly halving per-angle cost for spherical masks.

### Fourier Shell Correlation (FSC)

**Implementation**: `sg_toolbox/sg_calculate_FSC.m`

Standard FSC between halfsets:
```
FSC(k) = |Σ F₁(k)·conj(F₂(k))| / sqrt( Σ|F₁(k)|² · Σ|F₂(k)|² )
```

**Phase-randomization bias correction** (enabled by default):
1. For each repeat, randomize Fourier phases independently in both halfsets above a cutoff frequency
2. Compute FSC on the phase-randomized maps
3. Subtract random-phase FSC: `FSC_true ≈ (FSC_raw − FSC_random) / (1 − FSC_random)`
4. Average over multiple repeats for stability

**Figure-of-Merit weighting**:
```
FOM = sqrt( 2|FSC| / (1 + |FSC|) )
```
Used to weight each Fourier shell of the final average — suppresses shells with low correlation and emphasizes high-confidence shells.

### CTF Correction

**Implementation**: `src/tm/func/generate_tm_ctf_filter.m`, `src/subtomo/func/calculate_subtomo_ctf_filter.m`

When defocus metadata is available in the wedgelist:

1. Compute the standard CTF phase component:
   ```
   χ(f) = π·λ·Δz·f² − (π/2)·Cs·λ³·f⁴
   CTF(f) = −sin(χ(f))
   ```
   Where λ = relativistic electron wavelength, Δz = defocus, Cs = spherical aberration coefficient.

2. Multiply by an amplitude envelope (`exp(−B·f²)`) to account for envelope functions.

3. Extend the 1D radial CTF to 3D by radial symmetry.

4. Apply in Fourier domain: `F_corrected = F_reference × CTF_3D`

For advanced datasets, a **per-tilt-slice CTF** can be applied: each z-slice of the subtomogram receives a defocus value adjusted for its depth within the tomogram.

### Exposure (Dose) Weighting

**Implementation**: `src/tm/func/generate_tm_exposure_filter.m`

Based on Grant & Grigorieff (2015), doi:10.1016/j.ultramic.2015.05.018:
```
W(f) = exp(−D · (f / f_Nyquist)²)
```
Where D is the cumulative electron dose in e⁻/Å². Higher doses cause greater high-frequency attenuation. Applied per-tomogram using the exposure field from the wedgelist.

### Score-Based Weighting

**Implementation**: `src/func/score_based_weighting.m`

Particles with low alignment scores contribute less to the average at high frequencies:
```
Weight(score, f) = exp( w_f · (max_score − score) · f² )
```
Where `w_f` is a frequency-dependent factor derived from the `score_weight` parameter (0–1). This prevents poorly-aligned particles from degrading high-resolution signal.

---

## Filtering Infrastructure

The filter system is designed for efficiency in the inner loop. Filters are cached in a struct `f` and only recomputed when inputs change.

**Filter hierarchy** (`src/subtomo/func/refresh_subtomo_filters.m`):

| Trigger | Filters recomputed |
|---------|-------------------|
| New tomogram | Wedge mask, CTF filter, exposure filter |
| New class | Score-based weighting array |
| New subtomogram | Full filter recombination |

**Composite filter in frequency domain**:
```
filter_total = wedge_mask · CTF_filter · exposure_filter · bandpass_filter · score_weight
```

The bandpass filter (`calculate_3d_bandpass_filter.m`) applies cosine-edge transitions at the low-pass and high-pass cutoff frequencies to avoid Gibbs ringing.

---

## Parameter Configuration System

### Directory Layout Convention

```
rootdir/
  params/
    subtomo_param.star        ← Master parameter file (read by watcher)
  subtomo/bin{X}/
    iteration_{N}/
      motive_lists/
        motl_{N}.star
      refs/
        ref_class{C}.mrc
      masks/
        mask.mrc
      subtomos/
        subtomo_{k}.mrc
      wedgelists/
        wedgelist.star
  communication/
    sg_ali_{procnum}/         ← Job completion flags
```

### Parameter File Structure

Each module's parameter STAR file contains one task block per planned iteration:

```
data_task_1
loop_
_iteration
_motl_name
_ref_name
_mask_name
_lp_freq
_hp_freq
_score_type
_ctf_correction
_complete_subtomo_ali
_complete_subtomo_avg
...
1   motl_init   ref_class1   mask   0.5   0.0   flcf   0   0   0
```

Status flags (`_complete_*`) are set to 1 by the watcher after each step. The watcher scans tasks top-to-bottom and executes the first task with all flags = 0.

### Global Settings

`exec/lib/global_settings.txt` stores package-wide defaults (MCR path, MATLAB binary, queue settings) that are sourced by all bash launchers.

---

## Toolbox (`sg_toolbox/`)

The toolbox is a standalone MATLAB library providing utility functions used both by the pipeline and by end users for post-processing. Key groups:

### Motl Manipulation
- `sg_motl_read.m`, `sg_motl_write.m`, `sg_motl_read2.m`, `sg_motl_write2.m` — I/O
- `sg_motl_concatenate.m` — merge two motive lists
- `sg_motl_distance_clean.m` — remove particles within a minimum distance of each other
- `sg_motl_check_tomo_edges.m` — flag particles too close to tomogram boundaries
- `sg_motl_clean_by_local_geometry.m` — remove outliers based on local neighborhood geometry
- `sg_motl_clean_by_neighbor_geometry.m` — neighbor-based geometric cleaning
- `sg_motl_score_clean.m`, `sg_motl_score_clean_by_tomo.m` — score-threshold cleaning (global or per-tomogram)
- `sg_motl_apply_shifts.m` — apply refined shifts back to `orig_x/y/z`
- `sg_motl_split_by_tomo.m` — separate by tomogram for parallel I/O
- `sg_motl_batch_sphere.m`, `sg_motl_batch_filament.m`, `sg_motl_batch_tube.m` — initialize motl from geometric primitives (sphere surface, filament, tube)
- `sg_motl_randomize_eulers_by_symmetry.m` — symmetry-aware Euler randomization

### Geometry & Math
- `sg_euler2matrix.m`, `sg_matrix2euler.m` — Euler ↔ rotation matrix
- `sg_euler2quaternion.m`, `sg_quaternion2euler.m` — Euler ↔ quaternion
- `sg_quaternion_multiply.m`, `sg_quaternion_rotate.m` — quaternion algebra
- `sg_get_icosahedral_angles.m`, `sg_get_octahedral_angles.m`, `sg_get_dihedral_angles.m` — symmetry-equivalent angle lists
- `sg_ali_cone_angles.m` — angular sampling for cone search
- `sg_distancearray.m`, `sg_pairwise_dist.m` — distance computations
- `sg_sphere.m`, `sg_cylinder.m`, `sg_tube.m`, `sg_annulus.m` — mask shape generators

### Volume I/O & Processing
- `sg_mrcread.m`, `sg_mrcwrite.m`, `sg_emread.m`, `sg_emwrite.m` — volumetric I/O
- `sg_volume_read.m`, `sg_volume_write.m` — format-agnostic wrappers
- `sg_fourier_rescale_volume.m`, `sg_fourier_rescale_image.m` — Fourier-based resampling
- `sg_crop_volume.m`, `sg_pad_volume.m` — spatial cropping/padding
- `sg_rotate_vol.m`, `sg_rotate_cubic.m`, `sg_rotate_linear.m` — 3D interpolated rotation
- `sg_symmetrize_volume.m` — apply point-group symmetry to a volume
- `sg_sharpen_reference.m` — B-factor sharpening of reference maps
- `sg_normalize_under_mask.m` — normalize density statistics under a mask; returns `[mref, n_pix, m_idx]` — use only the first output
- `sg_bandpass_filter_tomogram.m`, `sg_gaussian_filter_tomogram.m` — tomogram preprocessing

### FSC & Resolution
- `sg_calculate_FSC.m` — FSC with optional phase randomization
- `sg_calcualte_fourier_shells.m` — Fourier shell binning

### IMOD Integration
- `sg_read_IMOD_tiltcom.m`, `sg_IMOD_parse_tiltcom.m` — parse IMOD tilt.com files
- `sg_read_IMOD_xf.m` — read IMOD alignment transforms

---

## Notable Implementation Details

### Packet-Based Dynamic Load Balancing

The inner loop is not uniformly fast — templates near particle-dense regions take longer to score. STOPGAP avoids load imbalance by:
1. Generating `n_cores × 2` packets at job start
2. Each core claims and processes one packet at a time (via `mkdir` atomicity)
3. Faster cores pick up unclaimed packets from the shared pool
4. A final "stragglers" check ensures no packets are left unprocessed

### FFT Wisdom Caching

Before any tight FFT loop, `src/func/optimize_fft_wisdom.m` computes and caches FFTW plan ("wisdom") for the specific box size used:
```matlab
fftw('planner', 'exhaustive');
fft(rand(boxsize, boxsize, boxsize, 'single'));
fftw('wisdom', wisdom_file);
```
The wisdom file is reloaded in subsequent runs, giving a 2–5× speedup on repeated FFTs of the same size.

### Fourier Cropping

When `fcrop=1`, the alignment operates on a Fourier-cropped version of the subtomogram:
- Only central frequencies (up to `fcrop_size`) are retained
- Reduces the effective box size for the angular search
- Pre-calculated crop indices (`fcrop_calculate_3d_idx.m`) avoid per-iteration index recomputation
- Must be uncropped before final averaging

### Supersampling for Averaging

When `avg_ss > 1`:
- Subtomograms are zero-padded in Fourier space before averaging (Fourier upsampling)
- Rotational interpolation artefacts are reduced at the cost of memory
- Final average is Fourier-cropped back to original box size
- Effective pixel size during averaging = `pixelsize / avg_ss`

### Core Naming in Logs

All diagnostic `disp()` calls are prefixed with `s.cn` (core name string, e.g., `'[Node03:Core2] '`). This makes logs trivially sortable and greppable by node or core.

### Crash Recovery

If a parallel job fails, a `crash_{procnum}` file is written in `rootdir/`. The watcher (`check_crashes.m`) checks for these every poll. **As shipped**, STOPGAP 0.7.5 only treats a crash as fatal once *every* core has crashed — a single dead core leaves the watcher polling forever for completion flags that never arrive, so the job hangs until SLURM wall-time kills it with no clear error (the silent-failure mode observed in practice). The edited `check_crashes.m` aborts on the first crash instead (see [§7](#7--silent-failure-guards-robustness)). The `crash_*` markers double as checkpoints — `rootdir/<n>` packet completion markers let a re-run skip already-finished work.

### Random Seed per Iteration

`src/io/get_random_seed.m` returns a new seed each iteration. This ensures halfset assignments and stochastic search perturbations vary between iterations, preventing the optimizer from cycling.

### Partial Motivelist Pattern

Rather than shared-memory accumulation (which would require locks), each core writes its own `splitmotl_{procnum}.star` during alignment. Core 1 merges these after all cores complete. This eliminates race conditions and allows partial recovery if some cores fail.

---

## Typical User Workflow

```
1. Acquire tomograms → reconstruct with IMOD or AreTomo

2. Prepare wedgelist (tilt angles, pixel size, defocus per tomogram)

3. Run Template Matching:
   - Provide template + mask
   - Set angular search range + step size
   - Output: score maps + orientation maps

4. Generate initial motivelist:
   sg_tm_generate_motl() — peak-pick score maps above threshold

5. Extract subtomograms:
   - Run extraction module with boxsize + pixel size
   - Produces one MRC file per particle

6. Iterative subtomogram alignment/averaging:
   - Configure subtomo_param.star (10–20 iterations typical)
   - Each iteration: align → average → FSC → update param
   - Progressively tighten angular search range (from ±30° to ±5°)
   - Apply masks at appropriate resolution stages

7. Clean motivelist:
   sg_motl_score_clean()           — remove low-score particles
   sg_motl_distance_clean()        — remove overlapping duplicates
   sg_motl_check_tomo_edges()      — remove particles near boundaries

8. Optional classification:
   - Run PCA module → k-means clustering → update class field
   - Re-average per class

9. Optional variance mapping:
   - Run VMAP module to locate flexible regions

10. Post-processing:
    sg_sharpen_reference()          — B-factor sharpening
    sg_symmetrize_volume()          — apply point symmetry
```

---

## Version History Highlights (from `changes.txt` and `stopgap_0.7.5.md`)

- **0.7.5**: Tiling-based template matching (improved scalability for large tomograms); multi-template support; improved local CTF; exposure weighting in TM
- **0.7.x**: Introduction of STAR format for all metadata; VMAP module; TPS module; refactored filter system
- **Earlier versions**: EM-format motivelists (Type 1/2), simpler non-tiled TM, basic FSC without phase randomization

---

## Performance Optimizations Applied (2026-06-02)

The following changes were made to reduce classification runtime for 672 z-axis-aligned particles on 32 cores. The bottleneck is angle-evaluation count (not I/O or parallelism), so all optimizations target the inner angular search loop.

### §1 — Per-block phi narrowing (`subtomoParams.sh`)

Full ±180° in-plane search is only needed in block 1 (to find the unknown φ). Blocks 2–3 now use ±15° (5°×3) and ±9° (3°×3). Reduces phi steps from 37 to 7 in blocks 2–3, giving ~5× fewer evaluations there.

### §2 — Coarse cone sampling (`subtomoParams.sh`)

`cone_search_type='coarse'` uses DYNAMO-style sparse cone sampling instead of the denser `'complete'` grid (~1.5–1.8× fewer orientations per cone).

### §3 — Stochastic hill-climb (`subtomoParams.sh`)

`search_mode='shc'` exits the angle loop as soon as any trial score beats the starting score. For well-converged particles in blocks 2–3, this exits within the first few trials (2–5× fewer evaluations per particle). The `'hc'` (exhaustive) mode always evaluates all angles.

### §4 — Fewer total iterations (`subtomoParams.sh`, `runClassification.sh`)

6 iterations (2 per block) instead of 9 (3 per block). Sufficient for convergence of z-aligned particles. `FINAL_ITER=7` in `runClassification.sh`.

### §5 — Lower `lp_rad` to keep Fourier cropping engaged (`subtomoParams.sh`)

lp_rad = 13 / 16 / 17 across blocks (down from 13 / 17 / 22). At lp_rad ≥ ~22 for an 80-voxel box, STOPGAP disables Fourier cropping and operates on the full 80³ volume (~1.9× more voxels). Keeping lp_rad ≤ 17 maintains cropping throughout.

**Combined §1–§5 reduction**: ~6.5× fewer angle evaluations versus the original exhaustive 9-iteration schedule.

### §6 — Sphere mask optimization (`src/func/calculate_flcf.m`, `src/subtomo/func/flcf_subtomo_scoring_function.m`)

Both `ali_mask` and `ccmask` are `sg_sphere()` objects (confirmed in `createStopgapInputs.m`). Rotating a sphere is a mathematical no-op. At 'init' time, `flcf_subtomo_scoring_function` tests each mask with a 90° rotation; if the relative L2 error is < 1%, it marks the mask as spherical and precomputes `fftn(mask)` into `o.fmask_cache`. In the 'score' inner loop:
- `sg_rotate_vol(ali_mask, …)` is skipped — the mask is used as-is
- `calculate_flcf` receives `o.fmask_cache{class_idx}` instead of recomputing `fftn(mask)` each angle
- `sg_rotate_vol(ccmask, …)` is skipped — `rccmask = o.ccmask` directly

This eliminates 2 of ~3 `sg_rotate_vol` calls and 1 of ~7 FFTs per angle evaluation, roughly halving per-angle cost. Non-spherical mask workflows are unaffected (fallback to original code path).

**Overall speedup estimate**: §1–§5 give ~6.5× reduction in angle count; §6 gives ~2× reduction in per-angle cost → **~13–15× total** versus the original schedule.

### §7 — Silent-failure guards (robustness)

Files: `src/func/check_crashes.m`, `runClassification.sh`.

Not a speed change — this fixes runs that previously failed *silently*. The observed failure: one MPI worker dies (e.g. `crash_1` with exit code 249), but the stock watcher only aborts when **all** cores crash, so it polls forever for completion flags that never arrive and the job hangs until the 2-day wall-time expires, with no useful error in the log.

Two independent fixes, so robustness does not depend on recompiling:

- **`check_crashes.m`** (source / watcher binary): aborts on the *first* crash with a message naming the crashed core(s) and project dir. A single dead core can never finish its packets, so continuing is pointless. Same per-poll cost (no slowdown). ⚠️ Compiled into `stopgap_watcher` — only effective after `compileStopgap.sh` recompile.
- **`runClassification.sh`** (bash layer, effective immediately, no recompile):
  - `run_watcher_guarded` runs the watcher in the background and polls for `crash_*` markers every 20 s; on detection it prints the marker, kills the watcher, and `exit 1`s. Negligible overhead.
  - `preflight` verifies all required seeds/params/masks exist before consuming wall-time.
  - An `ERR` trap reports the failing line and command to `logs/classify_%j.err`.
  - After Phase 1 it verifies `motl_${FINAL_ITER}.star` exists and dumps any `ref/warning_*.txt` (Fourier dynamic-range, empty class) into the job log instead of leaving them buried in the project dir.

Net effect: a worker crash now aborts loudly within ~20 s with the cause in `logs/`, instead of a multi-hour silent hang.

---

## Summary

STOPGAP is a mature, production-grade cryo-ET subtomogram averaging package built around:

- A **central motivelist** (STAR format) tracking all particle positions, orientations, scores, and class assignments
- A **modular pipeline** (TM → extract → subtomo → PCA/VMAP/TPS) with consistent parameter file and watcher patterns
- **Scalable parallel execution** via MPI + packet-based dynamic load balancing, with optional local data copying for HPC clusters
- **Gold-standard FSC** with phase-randomization bias correction and FOM weighting
- **Flexible filtering** (bandpass, wedge, CTF, exposure, score-based) applied per-particle in Fourier domain
- **FLCF scoring** (Roseman's method) for efficient template matching and alignment
- A rich **sg_toolbox** library for all auxiliary tasks: motl manipulation, geometric cleaning, volume I/O, symmetry operations, and IMOD integration

---

## Compilation Notes (BYU HPC, R2023b)

Learned from compiling against R2023b on this specific cluster.

### Cluster-specific paths

- MATLAB R2023b root: `/apps/matlab/r2023b` (symlink; the real path is `/vapps/rhel9/x86_64/matlab/r2023b/` — both work)
- `graph2d` toolbox (required `-a` argument for toolbox mcc): `/apps/matlab/r2023b/toolbox/matlab/graph2d/`

### Binary names produced by mcc

Each `compile_*.m` function calls `mcc -mv <entrypoint>.m`. The binary name matches the entry-point `.m` filename, not the compile function name:

| Compile function | Entry point | Binary produced |
|-----------------|-------------|----------------|
| `compile_parser` | `stopgap_parser.m` | `stopgap_parser` |
| `compile_stopgap` | `stopgap.m` | `stopgap` |
| `compile_watcher` | `stopgap_watcher.m` | `stopgap_watcher` |
| toolbox (manual) | `sg_toolbox.m` | `sg_toolbox` |

The toolbox binary is **`sg_toolbox`**, not `stopgap_toolbox`. Any verification check or script referencing the toolbox binary must use `sg_toolbox`.

### `compile_toolbox.m` must be bypassed

`src/stopgap/compile_toolbox.m` hardcodes the developer's cluster paths:
```matlab
sg_toolbox_dir = '/dors/wan_lab/home/wanw/research/software/stopgap/0.7.5/sg_toolbox/';
matlab_root = '/perutz/os/modules/software/MATLAB/2020b/';
```
Neither path exists outside the developer's institution. Always bypass this function and call `mcc` directly:
```matlab
cd('<STOPGAP_SRC>/sg_toolbox/standalone');
mcc('-R', '-nosplash', '-d', target_dir, '-mv', 'sg_toolbox.m', ...
    '-a', '<STOPGAP_SRC>/sg_toolbox/', ...
    '-a', '<MATLAB_ROOT>/toolbox/matlab/graph2d/');
system(['chmod +x ' target_dir 'sg_toolbox']);
```
Note: the toolbox mcc call does **not** include `-R nojvm` or `-R -nodisplay` flags (unlike parser/stopgap/watcher) because `sg_toolbox` is an interactive console application.

### Multiline `-r "..."` quoting fails on this cluster's MATLAB wrapper

Passing a multiline MATLAB block via `-r "..."` on this cluster silently fails — MATLAB prints "No MATLAB command specified for -r command line argument" and exits without running anything. Fix: write MATLAB commands to a temp `.m` file and use a single-line `-r` call:
```bash
COMPILE_SCRIPT=$(mktemp /tmp/sg_compile_XXXXXX.m)
cat > "${COMPILE_SCRIPT}" << MATLAB_EOF
... matlab commands ...
MATLAB_EOF
matlab -nodisplay -nosplash -r "run('${COMPILE_SCRIPT}'); exit;"
rm -f "${COMPILE_SCRIPT}"
```
The heredoc (`<< MATLAB_EOF`) expands bash variables at write time, so `${STOPGAP_SRC}` etc. are substituted correctly.

### Stale binaries mask compilation failures

If `exec/lib/` contains binaries from a previous run, the `if [ -f ... ]` verification check will report "OK" even if the current MATLAB invocation silently failed. Before resubmitting after a failed compile job:
```bash
rm -f exec/lib/stopgap exec/lib/stopgap_watcher exec/lib/stopgap_parser exec/lib/sg_toolbox
```

### `rootdir` must have a trailing slash

`subtomo_parser.m` normalizes directory paths with `sg_check_dir_slash` into a local copy `p`, but the read-back of an existing param file (line 421) uses the raw `parser.Results.rootdir` instead of `p.rootdir`. As a result, `sg_read_subtomo_param` concatenates rootdir + paramfilename without a separator, producing a broken path and failing with "ACHTUNG!!! Error reading params/subtomo_param.star!!!".

This only manifests on the second and third parser calls (blocks 2 and 3) because block 1 creates a fresh file — it never reads the existing one.

**Fix**: always include a trailing slash in `rootdir` in `subtomoParams.sh`:
```bash
rootdir='/home/<USER_ID>/nobackup/autodelete/stopgapClassification/subtomo_project/'
```

The same rule applies to any other param-generation script that passes `rootdir` to `stopgap_parser`.

### Motivelist `halfset` field must be `'A'` or `'B'` — NOT `'h1'`/`'h2'`

STOPGAP's `sg_motl_write` builds a `%-Nc` printf format where N = the maximum halfset string length. MATLAB's `fprintf` with `%c` format iterates over every character in a string argument, so a 2-char value like `'h1'` produces **two printf values** from one MATLAB argument. The 17th value (`'1'` or `'2'`) causes format recycling: MATLAB restarts from `'\n'` in the format string, inserting a stray newline and writing the extra character using the motl_idx format. This corrupts every particle entry into two lines.

At runtime, `sg_motl_read2` (line 146) fails with:
```
Unable to perform assignment because the left and right sides have a different number of elements.
MATLAB:matrix:singleSubscriptNumelMismatch
```

The correct halfset values are `'A'` and `'B'` (single characters). This is used throughout STOPGAP source:
- `sg_motl_assign_halfsets.m`: assigns `'A'`/`'B'`
- `determine_subtomograms_per_average.m`: compares against `'A'`

**Fix in `createStopgapInputs.m`**: replace `sprintf('h%d', x)` with `{'A','B'}{x}` in the halfset assignment. After fixing, delete the corrupt `motl_1.star` and re-run the script.

### File names in `subtomoParams.sh` must NOT include their directory prefix

STOPGAP automatically prepends the default subdirectory (e.g., `lists/`, `masks/`) to each `*_name` parameter. If you include the directory in the name, the path is doubled and STOPGAP fails at runtime with "ACHTUNG!!! Error reading .../lists//lists/wedgelist.star!!!".

The confirmed convention (taken from the example inside `subtomo_parser.m` line 15) is:

| Parameter | Correct value | Wrong value |
|-----------|--------------|-------------|
| `wedgelist_name` | `wedgelist.star` | `lists/wedgelist.star` |
| `mask_name` | `ali_mask.mrc` | `masks/ali_mask.mrc` |
| `ccmask_name` | `ccmask.mrc` | `masks/ccmask.mrc` |
| `motl_name` | `motl` | `lists/motl` |

When `listdir='none'` or `maskdir='none'`, STOPGAP defaults to `lists/` and `masks/` respectively. Setting `*dir='none'` does **not** suppress this — it triggers the default.

After fixing this, delete any existing `params/subtomo_param.star` and re-run `subtomoParams.sh`:
```bash
rm -f /home/<USER_ID>/nobackup/autodelete/stopgapClassification/subtomo_project/params/subtomo_param.star
bash /home/<USER_ID>/summerResearch/STOPGAP/subtomoParams.sh
```

### Initial reference must be written as two per-halfset files `_A_1.mrc` / `_B_1.mrc`

`load_subtomo_references.m` (lines 65–87) always loads references in a loop `for h = 1:2`, constructing:
```
{refdir}/{ref_name}_{char(64+h)}_{iteration}.mrc
```
where `char(65)='A'`, `char(66)='B'`. For `ref_name='ref_class1'` at iteration 1 this gives:
- `ref/ref_class1_A_1.mrc`
- `ref/ref_class1_B_1.mrc`

A single file `ref_class1_1.mrc` is **never read** — all workers crash immediately with:
```
ACHTUNG!!! Error reading file ref//ref_class1_A_1.mrc!!!
```

**Fix in `createStopgapInputs.m`**: write both halfset files instead of the merged file:
```matlab
sg_mrcwrite('ref/ref_class1_A_1.mrc', ref);
sg_mrcwrite('ref/ref_class1_B_1.mrc', ref);
```
Starting with identical content for both halfsets is correct — STOPGAP diverges them after the first averaging iteration.

---

### `stopgap_config_slurm.sh` fails with "unbound variable" under `set -o nounset`

`runClassification.sh` uses `set -o nounset`. The LD_LIBRARY_PATH append lines in `stopgap_config_slurm.sh` use `${LD_LIBRARY_PATH}` bare, which throws "unbound variable" if the SLURM job environment hasn't pre-exported it.

**Fix** (already applied): use `${LD_LIBRARY_PATH:-}` so it defaults to empty rather than erroring:
```bash
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}":$matlabRoot/runtime/glnxa64/"
```

### `stopgap_parser.sh` sources `stopgap_config_slurm.sh` directly

`exec/bin/stopgap_parser.sh` originally sourced `$STOPGAPHOME/lib/stopgap_config.sh`, but that file does not exist in this repo — only `stopgap_config_slurm.sh` and `stopgap_config_local.sh` exist. The file was edited to source `stopgap_config_slurm.sh` directly:

```bash
source $STOPGAPHOME/lib/stopgap_config_slurm.sh
```

If the other wrapper scripts (`stopgap.sh`, `stopgap_watcher.sh`, `sg_toolbox.sh`) show the same "No such file or directory" error, apply the same fix to each.

### Non-deployable toolbox warnings are harmless

During toolbox compilation, `mcc` emits warnings about excluded non-deployable files (`codetools/`, `helptools/`, `uitools/`). These are expected — the functions are interactive IDE tools that cannot be bundled. They do not affect the compiled binary's runtime behavior.

---

## Practical Setup Guide for Classification (BYU HPC)

This section is a step-by-step replication guide. The scripts referenced are all in `/home/<USER_ID>/summerResearch/STOPGAP/`. The project data lives in `/home/<USER_ID>/nobackup/autodelete/stopgapClassification/`.

### Prerequisites

- MATLAB R2023b is available via `module load matlab/r2023b`
- STOPGAP source is at `/home/<USER_ID>/summerResearch/STOPGAP/`
- Pre-extracted, z-axis-aligned subvolumes are in `subtomo_project/subtomograms/`, named `aligned_tom{N}_P{K}.mrc`

---

### Step 1 — Compile STOPGAP

Compilation is a one-time step. The compiled binaries are already in `exec/lib/` from job 11991429, so **this step is already done**. If you ever need to recompile (e.g., after an MCR update):

```bash
# From the STOPGAP source root:
rm -f exec/lib/stopgap exec/lib/stopgap_watcher exec/lib/stopgap_parser exec/lib/sg_toolbox
sbatch compileStopgap.sh
```

Monitor the job with `squeue -u <USER_ID>`. After it completes, confirm all four binaries exist:
```bash
ls -lh exec/lib/stopgap exec/lib/stopgap_watcher exec/lib/stopgap_parser exec/lib/sg_toolbox
```

The `exec/lib/stopgap_config_slurm.sh` is already set to `/apps/matlab/r2023b/` (correct for this cluster). If MATLAB is updated, edit the `matlabRoot` line in that file.

**See the "Compilation Notes" section above** for known pitfalls (bypassing `compile_toolbox.m`, multiline `-r` quoting failure, binary naming).

---

### Step 2 — Set up the project directory

The `subtomo_project/` directory must have these subdirectories before any scripts are run:

```
subtomo_project/
  subtomograms/   ← aligned_tom{N}_P{K}.mrc files live here (already present)
  lists/          ← create if missing
  ref/            ← create if missing
  masks/          ← create if missing
  params/         ← create if missing
```

Create any missing directories:
```bash
cd ~/nobackup/autodelete/stopgapClassification/subtomo_project
mkdir -p lists ref masks params
```

---

### Step 3 — Run `createStopgapInputs.m`

This MATLAB script reads the `subtomograms/` directory, creates numbered symlinks, and generates the motivelist, wedgelist, initial reference, and masks. **It must be run from `subtomo_project/`**.

**Important**: MATLAB's `run()` with an absolute path temporarily changes the working directory to the script's folder, breaking the relative `subtomograms/` lookup. The correct invocation uses `addpath` + direct function call:

```bash
cd ~/nobackup/autodelete/stopgapClassification/subtomo_project
matlab -nodisplay -nosplash -r \
  "addpath(genpath('/home/<USER_ID>/summerResearch/STOPGAP/sg_toolbox')); \
   addpath('/home/<USER_ID>/summerResearch/STOPGAP'); \
   createStopgapInputs; exit;"
```

What the script produces:
| Output | Description |
|--------|-------------|
| `subtomograms/subtomo_1.mrc … subtomo_672.mrc` | Numbered symlinks → original `aligned_tom*_P*.mrc` files |
| `lists/subtomo_mapping.txt` | Maps subtomo_num → tomo_num → original filename (for traceability) |
| `lists/motl_1.star` | Initial motivelist: 672 particles, z-axis aligned (phi=psi=the=0), random halfset assignment |
| `lists/wedgelist.star` | One entry per unique tomogram, tilt range ±60°, pixel_size=13.33 Å |
| `ref/ref_class1_A_1.mrc` | Initial reference for halfset A: normalized average of all 672 particles |
| `ref/ref_class1_B_1.mrc` | Initial reference for halfset B: identical content to `_A_` at iteration 1 |
| `masks/ali_mask.mrc` | Soft sphere alignment mask (radius = box/2 − 3 = 37 voxels) |
| `masks/ccmask.mrc` | Small sphere cross-correlation mask (radius = box/8 = 10 voxels) |

**Dataset parameters used** (edit these at the top of `createStopgapInputs.m` if they change):
- `box_size = 80` voxels
- `pixel_size = 13.33` Å
- `tomo_x/y/z = 500/500/300` voxels
- tilt range: ±60°

---

### Step 4 — Generate the subtomo parameter file

Run `subtomoParams.sh` from the STOPGAP source root. This calls `stopgap_parser` three times, appending one task block per call to `params/subtomo_param.star`. Two important rules:

1. **`rootdir` must end with a trailing slash** — the parser has a bug where it reads back the existing param file using the raw `rootdir` string without a separator, so omitting the slash causes blocks 2 and 3 to fail.
2. **`*_name` parameters must not include their directory prefix** — STOPGAP automatically prepends `lists/`, `masks/`, etc. from the default `listdir`/`maskdir`. Writing `wedgelist_name='lists/wedgelist.star'` doubles the path to `lists/lists/wedgelist.star` and causes all worker processes to crash.

```bash
bash /home/<USER_ID>/summerResearch/STOPGAP/subtomoParams.sh
```

This produces a 6-iteration alignment schedule in three blocks:

| Block | Iterations | angincr | angiter | Half-cone | lp_rad | Effective resolution | phi search |
|-------|-----------|---------|---------|-----------|--------|---------------------|-----------|
| 1 | 1–2 | 10° | 2 | ±20° | 13 | ~82 Å | ±180° (full, 10°×18) |
| 2 | 3–4 | 5° | 3 | ±15° | 16 | ~67 Å | ±15° (5°×3) |
| 3 | 5–6 | 3° | 3 | ±9° | 17 | ~63 Å | ±9° (3°×3) |

In-plane phi: full ±180° only in block 1 (to find the unknown in-plane angle); blocks 2–3 refine locally. Cone search is used throughout because all particles are pre-aligned to the z-axis. `search_mode='shc'` (stochastic hill-climb) exits the angle loop as soon as a score beats the starting score; `cone_search_type='coarse'` uses sparser DYNAMO-style cone sampling. Combined, these reduce angle evaluations by ~6.5× versus the original exhaustive schedule.

`lp_rad` is kept ≤17 so Fourier cropping stays engaged; lp_rad ≥ ~22 on an 80-voxel box disables cropping and forces the full 80³ volume (~1.9× more voxels per evaluation).

After 6 iterations the final motivelist is `lists/motl_7.star` and the final reference is `ref/ref_class1_7.mrc`.

**Monitoring resolution**: after each iteration STOPGAP writes FSC curves to `fsc/`. Tighten `lp_rad` in subsequent blocks only when the FSC shows genuine signal at higher resolution. The formula is `resolution ≈ (box_size × pixel_size) / lp_rad`. The maximum useful value is `box_size / 2 = 40` (Nyquist for an 80-voxel box). Keep lp_rad ≤17 to maintain Fourier cropping.

---

### Step 5 — Submit the classification job

```bash
sbatch /home/<USER_ID>/summerResearch/STOPGAP/runClassification.sh
```

Monitor with `squeue -u <USER_ID>`; logs go to `logs/classify_<jobid>.log` and `.err`.

**Wall time**: the script is set to `--time=2:00:00`. For 672 particles on 32 cores with the tuned 6-iteration schedule, subtomo alignment should take well under 2 hours; leave at least `2:00:00` as a margin.

`runClassification.sh` runs three phases sequentially within a single SLURM allocation:

#### Phase 1 — Subtomogram alignment (6 iterations)

The watcher reads `params/subtomo_param.star` and executes all 6 task blocks in sequence. Each block: align all particles → average per halfset → compute FSC → write updated motl. Completion is signalled through filesystem flags in `subtomo_project/comm/`.

Output: `lists/motl_7.star` (refined orientations), `ref/ref_class1_7.mrc` (final reference).

#### Phase 2 — PCA

Files are first copied from `subtomo_project` into `pca_project`:
- `lists/motl_7.star`, `lists/wedgelist.star` → `pca_project/lists/`
- `ref/ref_class1_7.mrc` → `pca_project/ref/`
- `masks/ali_mask.mrc` → `pca_project/masks/pca_mask.mrc`
- `subtomograms/` → symlinked (not copied) to avoid duplicating 672 files

Four PCA tasks run in sequence, each written to `pca_param.star` and immediately executed by the watcher (the PCA param file is **overwritten** per task, not appended):

| Task | What it does |
|------|-------------|
| `rot_vol` | Pre-rotates all 672 particles into the reference frame using refined Euler angles from `motl_7.star`; writes `rvol/*.mrc` |
| `calc_covar` | Builds the covariance matrix (`data_type=awpd`, amplitude-weighted phase differences) across all particles under `pca_mask.mrc`; writes `pca/covar.star` |
| `calc_eigenval` | Decomposes the covariance matrix; writes `pca/eigenval.star` (`n_eigs=10`) |
| `calc_eigenvec` | Projects all particles onto the eigenvectors; writes `pca/eigenfac.star` (per-particle scores on each component) |

#### Phase 3 — k-means clustering

MATLAB is called non-interactively. It reads `pca/eigenfac.star`, runs k-means on the first 4 principal components (`n_components=4`, `n_classes=3`, 10 replicates, random seed 42), and writes class labels back into the motivelist as `pca_project/lists/motl_classified.star`.

Key parameters (edit at the top of `runClassification.sh` before submitting):
- `n_cores=32` (must match `#SBATCH --ntasks`)
- `N_CLASSES=3`
- `FINAL_ITER=7` (total iterations + 1; must match the schedule in `subtomoParams.sh`)

---

### Step 6 — Create the conda environment (one-time)

`plotPCA.py` requires Python with numpy and matplotlib. Create the `stopgap` conda environment before submitting `runPostClassification.sh`:

```bash
conda create -n stopgap python=3.11 numpy matplotlib -y
```

This only needs to be done once. `runPostClassification.sh` sources `~/miniconda3/etc/profile.d/conda.sh` and activates the environment automatically at job start.

---

### Step 7 — Generate per-class averages and PCA plots

After `runClassification.sh` completes, submit the post-classification job:

```bash
sbatch /home/<USER_ID>/summerResearch/STOPGAP/runPostClassification.sh
```

**Phase A — PCA scatter plots** (`plotPCA.py`): reads `pca_project/pca/eigenfac.star` (per-particle PC scores) and `pca_project/lists/motl_classified.star` (class labels); saves pairwise scatter plots for all PC1–PC4 combinations plus a scree plot with cumulative variance to `pca_project/plots/`. If the classes overlap heavily in PC space, the classification may not reflect real structural heterogeneity.

**Phase B — Per-class averages** (`ali_multiclass`, `angiter=0`):

With `angiter=0` and `phi_angiter=0`, no angular search is performed — each particle is averaged at its current refined orientation from Phase 1 alignment.

**Reference naming convention** (confirmed from `refresh_reflist.m` and `load_subtomo_references.m`):

When `ref_name` is a bare string (no `.star` extension), STOPGAP auto-generates a reflist with one entry per unique class in the motivelist, all sharing the same `ref_name`. It loads input references named:
```
ref/{ref_name}_{A,B}_{iteration}_{class}.mrc
```
And writes output references named:
```
ref/{ref_name}_{A,B}_{iteration+1}_{class}.mrc    (per-halfset)
ref/{ref_name}_{iteration+1}_{class}.mrc           (FOM-weighted merged)
```
With `ref_name=ref_multiclass` and `startidx=1`, the script seeds `ref/ref_multiclass_{A,B}_1_{1..N}.mrc` from the final consensus halfset refs (`ref_class1_{A,B}_7.mrc`), and the job writes `ref/ref_multiclass_2_{1..N}.mrc` as the final merged per-class averages.

**ccmask is required even with `angiter=0`**: it is applied unconditionally in `flcf_subtomo_scoring_function.m` for peak finding regardless of angular search depth. The script copies `ccmask.mrc` from `subtomo_project/masks/` to `pca_project/masks/` before running the watcher.

**Expected outputs:**
```
pca_project/
  plots/
    pca_pc1_vs_pc2.png
    pca_pc1_vs_pc3.png
    pca_pc2_vs_pc3.png
    pca_scree.png              (requires eigenval.star in pca/; added automatically)
  ref/
    ref_multiclass_2_1.mrc    ← class 1 average (open in ChimeraX)
    ref_multiclass_2_2.mrc    ← class 2 average
    ref_multiclass_2_3.mrc    ← class 3 average
```

**Wall time**: the multiclass averaging step is fast — comparable to a single `p_avg` step (seconds to low minutes at 32 cores for 672 particles). Total job time under 30 minutes.

---

### Data flow summary

```
aligned_tom{N}_P{K}.mrc        (pre-extracted subvolumes)
        ↓  createStopgapInputs.m
subtomo_project/
  subtomograms/subtomo_N.mrc   (numbered symlinks)
  lists/motl_1.star            (initial motivelist)
  lists/wedgelist.star         (per-tomogram metadata)
  ref/ref_class1_A_1.mrc       (initial reference — halfset A)
  ref/ref_class1_B_1.mrc       (initial reference — halfset B)
  masks/ali_mask.mrc           (alignment mask)
  masks/ccmask.mrc             (CC search mask)
        ↓  subtomoParams.sh
  params/subtomo_param.star    (6-iteration schedule: shc + coarse cone + per-block phi)
        ↓  runClassification.sh Phase 1 (subtomo watcher, 6 iterations)
  lists/motl_7.star            (refined orientations)
  ref/ref_class1_7.mrc         (final reference)
        ↓  runClassification.sh Phase 2 (file copy + PCA watcher)
pca_project/
  rvol/rvol_*.mrc              (particles rotated into reference frame)
  pca/covar.star               (covariance matrix)
  pca/eigenval.star            (eigenvalues)
  pca/eigenfac.star            (per-particle PC scores, N×10)
        ↓  runClassification.sh Phase 3 (k-means, MATLAB)
  lists/motl_classified.star   (class labels assigned; 3 classes)
        ↓  runPostClassification.sh Phase A (plotPCA.py, conda stopgap)
  plots/pca_pc1_vs_pc2.png     (pairwise PC scatter plots, colored by class)
  plots/pca_scree.png          (variance explained per component)
        ↓  runPostClassification.sh Phase B (ali_multiclass, angiter=0)
  ref/ref_multiclass_2_1.mrc   (class 1 average, FOM-weighted merged halfsets)
  ref/ref_multiclass_2_2.mrc   (class 2 average)
  ref/ref_multiclass_2_3.mrc   (class 3 average)
```
