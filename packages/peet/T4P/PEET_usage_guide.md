# PEET Usage Guide — Subtomogram Classification

## 1. Overview

PEET (Particle Estimation for Electron Tomography) is a subtomogram averaging and
classification package originally developed at the University of Colorado Boulder.
This guide documents the approach that was validated on the 672-particle dataset
in `STA/subtomos_mrc/`.

**Installed version**: PEET 1.18.2 (compiled MCR binary — no MATLAB license required)

PEET classification workflow:
1. Pre-process: stack all pre-aligned subtomograms into a single MRC, z-score normalize
2. `averageAll` — compute grand average of all particles
3. `pca` — PCA on aligned subvolumes (wedge-masked difference method)
4. `clusterPca` — K-means clustering on PCA scores
5. `usePcaMotiveLists` — write class labels back into the motive list (MOTL)
6. Python post-processing — compute per-class averages for visual inspection

---

## 2. Critical Discovery: Multi-Tomogram Approach Does NOT Work

**Do not** use the obvious approach of supplying 672 separate MRC files (one per particle)
as 672 entries in `fnVolume`. Although the parameter file accepts this, PEET's
`getInitialMOTL` only iterates over the first tomogram when all tomograms contain
exactly one particle. Confirmed via `strace`: PEET opened only
`peet_run_MOTL_Tom1_Iter2.csv` and `aligned_tom100_P0001.mrc` regardless of the 672
entries. This produces a rank-1 PCA matrix and a degenerate 671:1 K-means split.

**Working solution**: stack all 672 particles into a **single MRC file** with 672
contours in one IMOD model. PEET treats this as one tomogram with 672 particles.

---

## 3. Environment Setup

```bash
source ~/Applications/IMOD-linux.sh
source ~/Applications/Particle.sh
```

Verify:
```bash
which averageAll    # ~/Applications/Particle/bin/averageAll
which 3dmod         # ~/Applications/IMOD/bin/3dmod
```

All PEET commands (`averageAll`, `pca`, `clusterPca`, `usePcaMotiveLists`) are MCR
binaries installed under `~/Applications/Particle/bin/`.

---

## 4. Single-Stacked-Tomogram Approach

### Why z-score normalization is required

The 672 subtomograms have a **bimodal density distribution** — roughly 267 particles
have mean density ~5 and 402 have mean density ~150. Without normalization, PC1 captures
this brightness difference rather than structural variation, producing a trivial
brightness-based split. Per-particle z-score normalization (subtract mean, divide by std)
eliminates this artifact and forces PCA to capture genuine structural differences.

### Particle layout in the stacked volume

Each 80×80×80 particle is placed at Z-offset `i * 80` within the stacked MRC:

```
stacked_all.mrc  shape: (53760, 80, 80) = 672 × 80 along Z
particle i (0-indexed):  center at (X=40, Y=40, Z=40+i*80)
```

---

## 5. Step-by-Step Workflow

All commands run from `~/Research/peet/results/` after sourcing both env scripts.

### Step 1 — Build stacked MRC, IMOD model, and MOTL files

```bash
cd ~/Research/peet
~/miniforge3/bin/python3 scripts/create_single_tomo.py
```

This script (see `scripts/create_single_tomo.py`) does:
- Loads `~/Research/STA/subtomos_mrc/aligned_*.mrc` in sorted order
- Z-score normalizes each 80×80×80 particle (subtract mean, divide by std)
- Stacks them into `results/stacked_all.mrc` (53760×80×80)
- Creates `results/stacked_all.mod` — IMOD model with 672 scattered points
- Reads CCC values from existing PEET TEMP files (from a prior per-tomogram run)
- Writes `results/peet_single_MOTL_Tom1_Iter1.csv` (all zeros, for initialization)
- Writes `results/peet_single_MOTL_Tom1_Iter2.csv` (real CCC from prior alignment)
- Writes `peet_project_single.prm`

> **Note on CCC source**: If no prior per-tomogram TEMP files exist, the script
> falls back to `CCC=0` for all particles. This is fine — PEET only needs a valid
> Iter1 MOTL to start. Run `averageAll` twice (`nIter=2`) to let PEET compute real CCCs.

### Step 2 — Compute grand average (`averageAll`)

```bash
cd ~/Research/peet/results
averageAll ../peet_project_single.prm 1 2>&1 | tee averageAll_single.log
```

Check that 672 particles were processed:
```bash
grep -i "672\|particle" averageAll_single.log | tail -5
```

Output: `peet_single_AvgVol_1P672.mrc` — grand average of all 672 z-scored particles.

### Step 3 — Run PCA

```bash
pca ../peet_project_single.prm 1 672 peet_single_AvgVol_1P672.mrc 1 2>&1 | tee pca_single.log
```

Syntax: `pca <prm> <iterNum> <nParticles> <avgVolFile> <nComponents>`

The `avgVolFile` is the WMD (wedge-masked difference) reference — PEET subtracts this
grand average before computing the covariance matrix.

Check particle count:
```bash
grep -i "total particles\|672" pca_single.log | head -5
```

Output: `pca672_peet_single.mat` (HDF5 file; keys: `U`, `S`, `V`, `coeffs`, `iterNum`, `numParticles`).

### Step 4 — K-means clustering

```bash
clusterPca ../peet_project_single.prm pca672_peet_single.mat 2 "1:10" 1 0 kmeans 2>&1 | tee clusterPca.log
```

Syntax: `clusterPca <prm> <matFile> <nClasses> <pcRange> <iter> <flag> <method>`

- `nClasses = 2` — number of clusters
- `"1:10"` — use PCs 1 through 10
- `method = kmeans` (must be the string `kmeans` or `hac`, **not** an integer)

Output: `peet_single_cluster_pca672.mat` and `clusterPca.png` (scree plot).

### Step 5 — Write class labels into MOTL

```bash
usePcaMotiveLists ../peet_project_single.prm 1 2>&1 | tee usePcaMotiveLists.log || true
```

Syntax: `usePcaMotiveLists <prm> <iterNum>` (exactly 2 arguments — no particle count).

Updates `peet_single_MOTL_Tom1_Iter2.csv` column 20 with class assignments.

The command exits non-zero even on success; `|| true` suppresses the shell error.

### Step 6 — Compute class averages

```bash
cd ~/Research/peet
~/miniforge3/bin/python3 scripts/make_class_averages.py
```

Reads class assignments from the updated MOTL and computes per-class averages from the
**original (non-z-scored)** subtomograms, preserving physical density scale.

Outputs:
- `results/class_1_avg.mrc` — average of class-1 particles (original scale)
- `results/class_2_avg.mrc` — average of class-2 particles (original scale)

---

## 6. Parameter File Reference (`peet_project_single.prm`)

```
fnVolume       = {'/path/to/results/stacked_all.mrc'}
fnModParticle  = {'/path/to/results/stacked_all.mod'}
initMOTL       = {'/path/to/results/peet_single_MOTL_Tom1_Iter1.csv'}

fnOutput       = 'peet_single'    # prefix for all output files
szVol          = [78 78 78]       # extraction box (slightly smaller than 80 avoids edge)

maskType       = 'sphere'
insideMaskRadius  = 0
outsideMaskRadius = 9             # 9 voxels = 120 Å mask — captures central object only

yaxisType      = 0
sampleSphere   = 'none'           # no angular search (particles pre-aligned)

dPhi   = {[0], [0]}               # zero angular search
dTheta = {[0], [0]}
dPsi   = {[0], [0]}
searchRadius = {[0], [0]}         # zero translational search

lowCutoff = {[0.05 0.05], [0.05 0.05]}
hiCutoff  = {[0.45 0.05], [0.45 0.05]}

flgFairReference = 0
reference = 'reference_znorm78.mrc'   # pre-computed z-scored grand average (78^3)

refThreshold  = [672, 672]
refFlagAllTom = 1

tiltRange      = {}
flgWedgeWeight = 0                # no missing-wedge compensation (subtomograms)
nWeightGroup   = 8

lstThresholds  = [672]
lstFlagAllTom  = 1

pixelSpacing   = 13.328
CCMode         = 0
flgAbsValue    = 1
particlePerCPU = 8
debugLevel     = 1
nIter          = 2
```

### Key parameter notes

| Parameter | Value | Reason |
|---|---|---|
| `szVol` | `[78 78 78]` | 78 avoids edge voxels; particles are 80×80×80 |
| `outsideMaskRadius` | `9` | ~120 Å sphere around centre; isolates the particle of interest |
| `dPhi/dTheta/dPsi` | `[0]` | Particles are pre-aligned — no rotation search |
| `searchRadius` | `[0]` | Particles are pre-centred — no translation search |
| `flgWedgeWeight` | `0` | No tilt-series geometry available for subtomograms |
| `sampleSphere` | `'none'` | Disables angular sampling entirely |

---

## 7. MOTL Format (PEET 20-column CSV)

```
Col  1 (index 0):  CCC — cross-correlation coefficient
Col  4 (index 3):  pIndex — 1-based particle index
Col  6 (index 5):  adjCCC — adjusted CCC (THIS is what PEET uses for ranking, not col 1)
Col 17 (index 16): EulerZ(1)  Φ
Col 18 (index 17): EulerZ(3)  Ψ
Col 19 (index 18): EulerX(2)  Θ
Col 20 (index 19): class label (written by usePcaMotiveLists)
```

**Critical**: Python-generated MOTL files must set `adjCCC` (col 6) to the CCC value,
not leave it as zero. PEET uses `adjCCC` for particle inclusion thresholding — if it is
zero, particles may be excluded from averages.

Example MOTL row (Iter2, particle i, with real CCC):
```
{ccc:.6f},0,0,{i+1},0,{ccc:.6f},0,0,0,0,0,0,0,0,0,0,0,0,0,0
```

---

## 8. Results on This Dataset

Classification of 672 pre-aligned subtomograms (80×80×80, 13.328 Å/px):

| Metric | Value |
|---|---|
| Particles | 672 |
| Classes | 2 |
| Class 1 size | 349 particles (52%) |
| Class 2 size | 323 particles (48%) |
| Pearson CC (class averages, full) | 0.88 |
| Pearson CC (class averages, masked R=9) | 0.955 |
| ARI vs density group | 0.025 (structurally driven, not brightness artifact) |

PCA outputs: `pca672_peet_single.mat` (20 components, 672 particles)

Class averages: `results/class_1_avg.mrc`, `results/class_2_avg.mrc`

---

## 9. Scripts

All scripts are in `~/Research/peet/scripts/`. Copies are in `STA/peet/scripts/`.

| Script | Purpose |
|---|---|
| `create_single_tomo.py` | Build stacked MRC, IMOD model, Iter1/Iter2 MOTLs, and `.prm` |
| `make_class_averages.py` | Compute per-class averages from MOTL class assignments |
| `compare_to_dynamo.py` | Compare PEET class labels to Dynamo classification (benchmark) |

---

## 10. Troubleshooting

**Only 1 particle processed by pca/averageAll**
→ You are using the multi-tomogram approach. Switch to the single-stacked-tomogram
  approach (`create_single_tomo.py`).

**clusterPca: "Method must be one of 'kmeans' or 'hac'"**
→ Pass the string `kmeans`, not `1` or `2`, as the method argument.

**usePcaMotiveLists: "Too many input arguments"**
→ Correct syntax is `usePcaMotiveLists <prm> <iterNum>` — exactly 2 arguments,
  no particle count.

**`usePcaMotiveLists` exits non-zero but class labels ARE written**
→ This is a PEET bug. Use `|| true` to suppress the error; verify the class column
  (col 20) in the MOTL file was updated.

**Lopsided K-means split (e.g., 640:32)**
→ Bimodal density distribution is dominating PCA. Ensure z-score normalization is
  applied per particle in `create_single_tomo.py` before stacking.

**`point2model`: "The point file has contour numbers and the -number option cannot be used"**
→ Remove the `-number 1` flag when the input text file contains explicit contour numbers.
