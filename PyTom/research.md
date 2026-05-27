# PyTom Codebase Research Report: Particle Classification

## Overview

PyTom (Python Tomography) is a cryo-electron tomography (cryo-ET) toolkit developed at Utrecht University (SBC-Utrecht). It covers the full subtomogram analysis pipeline: tomogram reconstruction, template-matching localization, subtomogram alignment, and classification. This report focuses on the classification subsystem.

---

## Pipeline Context

Classification in PyTom operates on **aligned subtomograms**. The expected workflow leading to classification is:

1. **Template matching** (`pytom/bin/localization.py`) — finds candidate particles in the tomogram.
2. **Subtomogram alignment** (`pytom/bin/align.py`, `pytom/bin/FRMAlignment.py`) — iteratively refines rotations, shifts, and cross-correlation scores for each particle.
3. **Classification** — groups aligned particles into structural classes. This requires the particles to already carry accurate rotation/shift metadata.

---

## Central Data Structure: ParticleList XML

Every classification method reads and writes a **ParticleList XML file**. This file is the universal interface between pipeline stages.

Each `<Particle>` entry contains:

| Field | Description |
|---|---|
| `Filename` | Path to the subtomogram volume (`.em` or `.mrc`) |
| `Rotation` | ZXZ Euler angles (Z1, X, Z2) from prior alignment |
| `Shift` | 3D translation (X, Y, Z) in voxels |
| `Class` | Integer class label (set/updated by classification) |
| `Score` | Numerical cross-correlation score from alignment |
| `Wedge` | Missing-wedge angles (half-angle pair, e.g., 30°/30°) |

The wedge information is critical: all correlation calculations apply cross-wedge correction so that the missing Fourier wedge of each tilt series does not bias classification.

---

## Classification Methods

PyTom implements four distinct classification approaches, living in `pytom/classification/` and invoked via scripts in `pytom/bin/`.

---

### Method 1: MCO-EXMX (K-Means Style, Expectation-Maximization)

**Entry point:** `pytom/bin/mcoEXMX.py`  
**Core algorithm:** `pytom/classification/mcoEXMX.py` — function `mcoEXMX()`  
**Structures:** `pytom/classification/mcoEXMXStructures.py` — `MCOEXMXJob`, `MCOEXMXWorker`

#### Algorithm

This is a 3D K-means classification driven by cross-correlation. Each iteration has two phases:

**E-step (Expectation / Averaging):**
- Particles in each class are averaged into a class reference volume (`clusterCenter`).
- Averaging is MPI-distributed: each worker node computes a partial average for one class.
- The wedge sum is tracked and used to compensate for missing Fourier information in the average.

**M-step (Maximization / Assignment):**
- Each particle is compared against every class reference using a scored alignment.
- Two modes exist (controlled by `doAlignment`):
  - **Score-only** (default): uses stored rotation/shift; computes `compareTwoVolumes()` score (FLCF — Fast Local Correlation Function) with bandpass filtering and wedge correction.
  - **FRM alignment** (`doAlignment=True`): uses `FRMAlignmentWrapper` (spherical harmonics Fast Rotational Matching) to find the best rotation before scoring.
- Each particle is assigned to the class with the highest score (`classifyParticleList()` in `mcoEXMX.py:7–67`).

**Convergence:** Stops when the fraction of particles that change class falls below `endThreshold`, or after `numberIterations` rounds.

**Adaptive resolution (optional):** After each iteration, per-class FSC (Fourier Shell Correlation) is computed. The lowpass filter for the next iteration is set to the minimum resolution determined across classes (×1.1 safety factor), ensuring scoring is not done beyond achievable resolution.

**Parallelization:** MPI. The master process (rank 0) orchestrates; worker processes compute alignment scores for subsets of particles. Requires `mpirun -np N` with N ≥ 2.

#### Required Inputs

| Input | Type | Notes |
|---|---|---|
| Job XML file (`-j`) | XML file | Encodes all parameters; built with `pytom/bin/mcoEXMXJob.py` |
| ParticleList | XML (via job) | Aligned subtomograms with rotation/shift/wedge/score |
| Destination directory | path | Must exist before running |
| Number of classes (`numberClasses`) | int | Used for random initialization if no pre-classified list |
| Number of iterations | int | Max EM rounds |
| End threshold | float (0–1) | Fraction of class changes to declare convergence |
| Mask | EM/MRC volume | 3D binary/soft mask applied during correlation |
| Score type | string | E.g., `FLCFScore` |
| Preprocessing | object | Bandpass filter: lowest + highest frequency cutoffs |
| Binning | int | Downsample factor when reading volumes (libtomc convention) |
| Symmetry | optional | `PointSymmetry(N)` or `HelicalSymmetry` |
| FRM alignment flag | bool | Enable FRM during M-step |
| FRM bandwidth | [low, high] | Spherical harmonics bandwidth range |

---

### Method 2: MCO-AC (Simulated Annealing Classification)

**Entry point:** `pytom/bin/mcoAC.py`  
**Core algorithm:** `pytom/classification/mcoAC.py` — function `mcoAC()`  
**Structures:** `pytom/classification/mcoACStructures.py` — `MCOACJob`

#### Algorithm

MCO-AC wraps MCO-EXMX with a simulated annealing outer loop to escape local minima — a common failure mode of pure K-means.

**Outer loop (annealing schedule):**
1. Run a small number (`localIncrement`) of EXMX iterations as local refinement.
2. Classify particles using a **temperature-dependent probabilistic criterion** (`criterion.apply()`): at high temperature, class swaps are allowed even when a competitor class scores slightly better, exploring the solution space broadly. At low temperature, behavior approaches greedy assignment.
3. Track the best particle list seen so far (highest sum-of-scores across all particles).
4. Decrease temperature and repeat until the annealing schedule says `cooledDown()` or convergence is reached.

The key distinction from EXMX is in `classifyParticleList()` in `mcoAC.py:8–78`: instead of always picking the maximum-score class, it applies the annealing criterion which may accept suboptimal assignments with a probability proportional to temperature.

**Convergence:** Same fraction-of-class-changes threshold as EXMX, checked on the deterministic assignment (not the annealed one).

**Parallelization:** Same MPI structure as EXMX (workers run `MCOEXMXWorker`).

#### Required Inputs

Same as MCO-EXMX, plus:

| Input | Notes |
|---|---|
| Temperature schedule | Initial temperature and cooling function |
| Criterion | Classification criterion with annealing probability |
| Local increment | Number of EXMX iterations per annealing round |
| Allow class collapse | Boolean; if False, prevents annealing from emptying classes |

---

### Method 3: CPCA (Constrained Principal Component Analysis)

This is a two-step pipeline: (1) compute a pairwise similarity matrix, then (2) reduce dimensionality and cluster.

#### Step 1: Correlation Matrix Computation

**Entry point:** `pytom/bin/calculate_correlation_matrix.py` (in build dir)  
**Core:** `pytom/classification/calculate_correlation_matrix.py` — `CMWorker`, `CMWorkerGPU`

For every pair of particles (i, j), compute the **normalized cross-correlation (nxcc)** with wedge correction:
- Apply the stored rotation/shift to both volumes.
- Apply each particle's missing wedge filter to the other particle's volume.
- Apply a lowpass filter to both.
- Compute `nxcc(wg.apply(vf), wf.apply(vg), mask)`.

The result is an N×N symmetric matrix saved as `correlation_matrix.csv` (comma-delimited, no header).

**CPU mode:** `CMWorker` distributes particle pairs across MPI nodes; each node computes a subset of pairwise scores.

**GPU mode:** `CMWorkerGPU` uses `CCCPlan` (CUDA-based batch CCC) to run many comparisons simultaneously per GPU; multiple GPUs are supported via MPI with one MPI rank per GPU plus one master.

**Required inputs:**
| Flag | Input | Notes |
|---|---|---|
| `-p` | ParticleList XML | Aligned particles |
| `-m` | Mask volume | EM/MRC, used in nxcc denominator |
| `-f` | Frequency | Integer pixel cutoff for lowpass filter (after binning) |
| `-b` | Binning | Integer downsample factor (default 1) |
| `-o` | Output directory | Where `correlation_matrix.csv` is saved |
| `-g` / `--gpuID` | GPU indices | Comma-separated, e.g. `0,1,2`; triggers GPU mode |

#### Step 2: CPCA Classification

**Entry point:** `pytom/bin/classifyCPCA.py`  
**Core:** `pytom/classification/CPCAfunctions.py` — `subTomoClust()`, `SVD_analysis()`, `kmeansCluster()`

Algorithm (`subTomoClust()`, line 6–43):
1. Load the CCC matrix (CSV).
2. **SVD decomposition** (`numpy.linalg.svd`): extract eigenvectors and eigenvalues; rescale eigenvectors by `sqrt(|eigenvalue|)` to weight by explained variance.
3. **K-means clustering** (`scipy.cluster.vq.kmeans2`) on the first `neig` eigenvectors, requesting `nclass` clusters with 50 iterations.
4. Assign class labels back to each particle in the ParticleList and write output XML.

**Required inputs:**

| Flag | Input | Notes |
|---|---|---|
| `-p` | ParticleList XML | Aligned particles (same order as rows of CCC matrix) |
| `-c` | CCC matrix CSV | Output of step 1 |
| `-e` | Number of eigenvectors (`neig`) | How many SVD components to use for clustering |
| `-n` | Number of classes (`nclass`) | K for k-means |
| `-o` | Output particle list XML | Classified result |
| `-a` | Class average prefix | Name stem for output class average volumes |

---

### Method 4: Auto-Focus Classification

**Entry point / module:** `pytom/classification/auto_focus_classify.py` (also `pytom/bin/auto_focus_classify.py`)  
**Main function:** `classify(pl, settings)`

#### Algorithm

This is the most sophisticated method. It is designed for cases where classes differ in only a subset of voxels (e.g., a flexible domain, a bound ligand). Instead of scoring each particle against a full reference, it uses **difference maps** to automatically identify and focus on discriminative voxels.

**Initialization (k-means++ style):**
- Particles are sorted by alignment score; poor-scoring particles can be excluded as noise.
- The first reference is the average of the top-scoring N/K particles.
- Each subsequent reference is seeded by selecting particles that are maximally distant (in nxcc-space) from all existing references, weighted by distance (k-means++ probability).

**Each iteration:**

1. **Difference map computation** (for every pair of class references):
   - Lowpass-filter both references.
   - Align one to the other via FRM.
   - Normalize both volumes to zero-mean, unit-std.
   - Optionally threshold by a sigma cutoff to focus on strong density.
   - Compute the pixel-wise STD map: `sqrt((avg - v1)^2 + (avg - v2)^2)`.
   - Threshold the STD map to retain only the most variable voxels.
   - Lowpass-filter the thresholded map to smooth it.
   - The result is two directional binary-ish masks, one per reference (class A looks different from B in region X; class B looks different from A in region Y).

2. **Alignment / scoring:**
   - Each particle is aligned to each class reference via FRM (`frm_align`): returns best shift, rotation, and score.
   - If `noalign=True`, stored rotation/shift from the ParticleList are used without re-alignment.

3. **Focused voting (class assignment):**
   - For each pair of classes (c1, c2):
     - Score the particle against c1 using the c1-vs-c2 difference map as a spatial weight (`focus_score` = nxcc inside the dmap region).
     - Score the particle against c2 using the c2-vs-c1 difference map.
     - The higher score wins one vote.
   - The class with the most pairwise votes is assigned to the particle.

4. **Noise handling:**
   - If `noise` is set, the fraction of particles whose correlation is consistently low across all references (high product of p-values) is flagged as class -1.

5. **Class management:**
   - Classes smaller than `max_class_size / dispersion` are collapsed to class -1 (noise).
   - The same number of large classes are split in two by score-ranking and halving.
   - This maintains a roughly constant number of active classes.

6. **Reference update:**
   - New class averages are computed (FSC-corrected, wedge-sum-divided).
   - Per-class resolution is determined from FSC at 0.5 criterion.

**Stopping:** < 0.5% class changes between iterations, or max iterations reached.

**Parallelization:** Uses `pytom.agnostic.mpi.MPI.parfor()` for distributed alignment and averaging. GPU averaging is supported for the averaging step.

#### Required Inputs

| Flag | Input | Notes |
|---|---|---|
| `-p` | ParticleList XML | Required |
| `-f` | Frequency | Required; max frequency in pixels for scoring/filtering |
| `-k` | Number of classes | Required unless using `-r` (external references) or `-l` (resume) |
| `-o` | Output directory | Default `./` |
| `-s` | Offset | Search offset in voxels (passed to FRM) |
| `-b` | Binning factor | Integer, default 1 |
| `-m` | Alignment mask | EM/MRC volume; used during FRM alignment and averaging |
| `-c` | Focus mask | EM/MRC volume; spatial constraint for difference map computation |
| `-i` | Number of iterations | Default 10 |
| `-d` | Dispersion | Integer; classes smaller than max/dispersion are removed |
| `-r` | External references | Comma-separated paths to reference EM volumes (skips initialization) |
| `-l` | Resume | Use class assignments already in the ParticleList as starting point |
| `-n` | Noise percentage | Float 0–1; fraction of lowest-scoring particles to flag as noise |
| `--sig` | Sigma | Density threshold for difference map computation |
| `-t` | Threshold | STD threshold for difference map, default 0.4 |
| `-a` | No-align flag | Skip FRM; use stored orientations only |
| `--gpuID` | GPU IDs | Comma-separated GPU indices for GPU-accelerated averaging |

---

## File Map Summary

```
pytom/classification/
├── mcoEXMX.py               # K-means EM algorithm + clusterKMeans utility
├── mcoEXMXStructures.py     # MCOEXMXJob, MCOEXMXWorker, KMDataSet, Cluster
├── mcoAC.py                 # Simulated annealing classification
├── mcoACStructures.py       # MCOACJob (annealing parameters)
├── CPCAfunctions.py         # CPCA: subTomoClust, SVD_analysis, kmeansCluster
├── correlationMatrix.py     # CMManager, CMWorker, calculateCorrelationVector (legacy CCC)
├── calculate_correlation_matrix.py  # CMWorker (CPU), CMWorkerGPU (GPU) for CCC
├── auto_focus_classify.py   # Auto-focus classification + __main__ entry
├── classificationResults.py # Result serialization helpers
├── clusterFunctions.py      # randomiseParticleListClasses utility
├── correlationMatrixStructures.py   # CorrelationVectorJob, CorrelationVector
└── analyze.py               # Post-classification analysis helpers

pytom/bin/
├── mcoEXMX.py               # CLI entry: runs MCOEXMXJob from XML
├── mcoEXMXJob.py            # CLI entry: creates MCOEXMXJob XML
├── mcoAC.py                 # CLI entry: runs MCOACJob from XML
├── mcoACJob.py              # CLI entry: creates MCOACJob XML
├── classifyCPCA.py          # CLI entry: CPCA step 2 (SVD + kmeans)
├── calculate_correlation_matrix.py  # CLI entry: CPCA step 1 (CCC matrix)
└── auto_focus_classify.py   # CLI entry: auto-focus classification
```

---

## Comparison of Methods

| Property | MCO-EXMX | MCO-AC | CPCA | Auto-Focus |
|---|---|---|---|---|
| Core algorithm | K-means EM | Simulated annealing K-means | SVD + k-means on CCC matrix | Difference-map-guided voting |
| Alignment during classification | Optional (FRM) | Optional (FRM) | No (uses stored alignment) | Yes (FRM per iteration) |
| Local minima risk | High | Lower (annealing) | Low | Low |
| Discriminative region | Whole volume | Whole volume | Whole volume | Focused (difference map) |
| GPU support | No | No | Yes (CCC matrix step) | Yes (averaging step) |
| Parallelization | MPI | MPI | MPI or multi-GPU | MPI |
| Prerequisite | Aligned ParticleList | Aligned ParticleList | Aligned ParticleList + CCC matrix | Aligned ParticleList |
| Noise class | No | No | No | Yes (class -1) |

---

## Common Prerequisites for All Methods

1. **Aligned ParticleList XML** — particles must have been pre-aligned; alignment provides the rotation, shift, wedge, and score fields that classifiers depend on.
2. **Subtomogram volumes** — EM or MRC format 3D arrays (floating point), typically 32–64 voxels on a side at the working binning.
3. **Mask volume** — a 3D binary or soft mask (same dimensions as subtomograms at working resolution) to restrict correlation to the region of interest.
4. **MPI environment** — all methods except CPCA step 2 require `mpirun`.

The CPCA workflow additionally requires the correlation matrix CSV as an intermediate file produced by step 1 before step 2 can run.
