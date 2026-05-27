# PEET Usage Guide for Subtomogram Averaging and Classification

## 1. Overview

PEET (Particle Estimation for Electron Tomography) is a subtomogram averaging and
classification package originally developed at the University of Colorado Boulder.
The core algorithms run in **MATLAB**; IMOD provides pre/post-processing utilities,
the Etomo GUI, and helper programs.

PEET workflow at a glance:
1. Provide particle positions (model files) and volumes (tomograms or subtomograms)
2. PEET extracts subvolumes and cross-correlates them against a reference
3. Iterative alignment: each particle is rotated/shifted to maximize CCC with the reference
4. Final average is computed at user-specified particle thresholds
5. **Classification**: PCA on aligned subvolumes → K-means into k classes → per-class averages

Architecture:
- IMOD (`/home/jblaser2/Applications/IMOD/`) provides: `etomo` GUI, `subtomosetup`,
  `point2model`, `clonemodel`, `clonevolume`, `subimstat`
- PEET MATLAB package (must be downloaded separately — see Section 7) provides the
  actual averaging engine: `PEET()`, `PEETclassify()`, etc.

---

## 2. Dataset Summary

| Property | Value |
|---|---|
| Number of subtomograms | 672 |
| Volume dimensions | 80 × 80 × 80 voxels |
| File size (each) | ~2 MB |
| Location | `STA/subtomos_mrc/aligned_tom{ID}_P{NNNN}.mrc` |
| Source tomograms | 294 unique tomograms (tom1–tom294) |
| Particles per tomogram | 1–8 |
| Existing MOTL | `STA/outputs/motl.txt` (672 rows × 20 cols, Dynamo format) |
| MATLAB | `/home/jblaser2/matlab/bin/matlab` (R2024a) |
| IMOD/PEET tools | `/home/jblaser2/Applications/IMOD/bin/` |

---

## 3. Key Input Files PEET Requires

PEET needs three inputs specified in the `.prm` parameter file:

### 3a. `fnVolume` — list of tomogram MRC files
A MATLAB cell array of strings. Because our subtomograms are **pre-extracted**, we
treat each 80×80×80 `.mrc` file as its own tiny "tomogram" with one particle at its
center. This avoids needing the original tomogram data.

```matlab
fnVolume = {'aligned_tom1_P0001.mrc';
            'aligned_tom1_P0002.mrc';
            ...
            'aligned_tom294_P0008.mrc'}
```

### 3b. `fnModParticle` — one IMOD model file per volume
Each model file contains a single point at the center of the 80×80×80 volume (40, 40, 40).
Generate with IMOD's `point2model` (see Section 5 for the setup script).

```bash
echo "40 40 40" | point2model -circle 3 -input /dev/stdin -output particle.mod
```

### 3c. `initMOTL` — initial motive list (orientations)
Two options:
- `initMOTL = 0` — all angles set to zero (appropriate if subtomograms are already
  roughly aligned)
- `initMOTL = {'motl_vol001.csv'; ...}` — supply per-volume MOTL CSV files
  (one CSV per volume) converted from `STA/outputs/motl.txt`

For classification benchmarking, `initMOTL = 3` (uniform random rotations) is a
useful baseline to test whether PEET recovers consistent orientations.

---

## 4. MOTL Format: PEET vs Dynamo (20-column)

Both use a 20-column matrix; columns differ in meaning.

| Col | PEET meaning | Dynamo meaning (our `motl.txt`) |
|-----|-------------|----------------------------------|
| 1 | Cross-correlation coefficient (CCC) | CCC score |
| 2 | Particle number within this tomogram | Global particle ID |
| 3 | Volume/tomogram index (1-indexed in fnVolume) | Tomogram ID |
| 4 | 1 (flag) | Class label |
| 5 | X coordinate in tomogram (pixels) | X coordinate |
| 6 | Y coordinate in tomogram (pixels) | Y coordinate |
| 7 | Z coordinate in tomogram (pixels) | Z coordinate |
| 8 | Phi (Euler angle, ZXZ convention) | dX shift |
| 9 | Psi (Euler angle) | dY shift |
| 10 | Theta (Euler angle) | dZ shift |
| 11 | dX translation | Phi |
| 12 | dY translation | Psi |
| 13 | dZ translation | Theta |
| 14–19 | Reserved (zeros) | Reserved (zeros) |
| 20 | Half-set assignment (1 or 2) | Half-set (1 or 2) |

**Important**: when converting from `motl.txt` to PEET CSV format, remap the Euler
angles from cols 11–13 to cols 8–10, and shifts from cols 8–10 to cols 11–13.

The existing `motl.txt` has all angles = 0 and shifts = 0 (subtomograms are
pre-extracted and pre-aligned), so in practice `initMOTL = 0` is equivalent.

---

## 5. Setting Up the PEET Project (Pre-Extracted Subtomogram Workaround)

Because our subtomograms are already extracted, we bypass `subtomosetup` and set
up the project directly. The key insight: **set `szVol` equal to the full 80×80×80
volume so PEET "extracts" the whole file as the subvolume**.

### Step 1: Environment setup
```bash
source ~/Applications/IMOD-linux.sh
export PATH=/home/jblaser2/matlab/bin:$PATH
```

### Step 2: Create the PEET project directory
```bash
mkdir -p ~/Research/STA/peet
cd ~/Research/STA/peet
```

### Step 3: Generate model files (one per subtomogram)
Each model file has a single point at (40, 40, 40) — the center of our 80×80×80 volumes.

```bash
SUBTOMOS=~/Research/STA/subtomos_mrc

for mrc in "$SUBTOMOS"/aligned_*.mrc; do
    base=$(basename "$mrc" .mrc)
    # Write a single point at voxel center (40,40,40); point2model uses 0-indexed coords
    echo "40 40 40" | point2model -circle 3 -input /dev/stdin \
        -output "models/${base}.mod"
done
```

This creates `models/aligned_tom1_P0001.mod`, etc.

### Step 4: Create the PEET parameter file

Either use the Etomo GUI (Section 7) to generate the `.prm`, or write it by hand:

```matlab
% peet_project.prm  (MATLAB-syntax cell array format)
fnVolume = {
  '../subtomos_mrc/aligned_tom1_P0001.mrc';
  '../subtomos_mrc/aligned_tom1_P0002.mrc';
  % ... all 672 entries
};

fnModParticle = {
  'models/aligned_tom1_P0001.mod';
  % ...
};

initMOTL            = 0          % zero all angles (subtomograms already aligned)
fnOutput            = 'peet_run' % base name for output files
szVol               = [80 80 80] % full volume size — no sub-extraction
maskType            = 'sphere'
insideMaskRadius    = 0
outsideMaskRadius   = 35         % ~87% of 40px radius; excludes edge artifacts
dPhi                = [20]       % angular search range around Y axis (degrees)
dTheta              = [20]       % angular search range around Z axis
dPsi                = [20]       % angular search range around X axis
searchRadius        = [3]        % translational search radius (pixels)
lowCutoff           = [0.05 0.05]
hiCutoff            = [0.45 0.05]
refThreshold        = 100        % use top 100% of particles for reference
lstThresholds       = [672]      % compute final average with all 672 particles
flgWedgeWeight      = 0          % disable missing-wedge compensation (pre-extracted)
flgFairReference    = 1          % multiparticle reference (more robust than single)
reference           = 2          % 2-level binary search → 4-particle reference
CCMode              = 0          % standard normalized CCC
particlePerCPU      = 8
nIter               = 3          % number of alignment iterations before classification
```

Generate the full `fnVolume`/`fnModParticle` lists with a helper script:

```python
# generate_peet_prm.py
import os, glob

subtomos = sorted(glob.glob('../subtomos_mrc/aligned_*.mrc'))

with open('peet_project.prm', 'w') as f:
    f.write("fnVolume = {\n")
    for p in subtomos:
        f.write(f"  '{p}';\n")
    f.write("};\n\nfnModParticle = {\n")
    for p in subtomos:
        base = os.path.basename(p).replace('.mrc','')
        f.write(f"  'models/{base}.mod';\n")
    f.write("};\n")
    # Append remaining parameters below...
```

---

## 6. Key `.prm` Parameters Reference

| Parameter | Description | Recommended value for this dataset |
|---|---|---|
| `szVol` | Subvolume extraction size | `[80 80 80]` |
| `maskType` | Reference masking | `'sphere'` |
| `outsideMaskRadius` | Sphere mask radius (px) | `35` (out of 40 max) |
| `dPhi/dTheta/dPsi` | Angular search ranges (°) | `[20]` for first iter, `[5]` for refinement |
| `searchRadius` | Translational search (px) | `[3]` |
| `nIter` | Alignment iterations | `3` |
| `flgWedgeWeight` | Missing wedge compensation | `0` (disable; no tilt info) |
| `flgFairReference` | Multiparticle reference | `1` |
| `reference` | Binary search levels for reference | `2` (→ 4 particles) |
| `refThreshold` | % particles used to build reference | `100` |
| `lstThresholds` | Final average particle counts | `[672]` or `[336 672]` |
| `lowCutoff` | Low-freq filter [cutoff sigma] | `[0.05 0.05]` |
| `hiCutoff` | High-freq filter [cutoff sigma] | `[0.45 0.05]` |
| `particlePerCPU` | Particles per CPU thread | `8` |
| `CCMode` | Cross-correlation mode | `0` (normalized CCC) |

---

## 7. Running PEET

### Download the PEET MATLAB package
PEET's MATLAB core is **separate from IMOD** and must be downloaded:
- URL: https://bio3d.colorado.edu/PEET/
- Extract to e.g. `~/Applications/PEET/`
- In MATLAB, add it to the path: `addpath(genpath('~/Applications/PEET/'))`

### Option A: Etomo GUI (recommended for first-time setup)
```bash
source ~/Applications/IMOD-linux.sh
export PATH=/home/jblaser2/matlab/bin:$PATH
etomo &
```
In Etomo:
1. File → New PEET Project
2. Browse to `.prm` file (or let Etomo create one)
3. Fill in fnVolume, fnModParticle, szVol, initMOTL
4. Click **Run** to start iterations

### Option B: MATLAB command line
```matlab
% In MATLAB after addpath for PEET and IMOD
cd('/home/jblaser2/Research/STA/peet')

% Load and run the project
PEET('peet_project.prm')

% Or run a specific number of iterations
PEET('peet_project.prm', 'nIter', 3)
```

### Option C: MATLAB batch (non-interactive)
```bash
/home/jblaser2/matlab/bin/matlab -nodisplay -nosplash -r \
  "addpath(genpath('~/Applications/PEET')); \
   addpath(genpath('~/Applications/IMOD/MATLAB')); \
   PEET('peet_project.prm'); exit"
```

---

## 8. Classification Workflow

Classification in PEET uses PCA on aligned particles followed by K-means clustering.
Run this **after** at least one averaging iteration to have aligned particles.

### Step 1: Run averaging to get aligned particles
After `PEET('peet_project.prm')` completes, aligned particles are written if
`alignedBaseName` is set in the `.prm` (e.g. `alignedBaseName = 'aligned/particle'`).

### Step 2: PCA + K-means in Etomo
1. In Etomo, open the PEET project
2. Go to the **Analysis** tab
3. Set **Number of classes** (k); for a benchmark, try k = 2, 3, 4, 5
4. Set **PCA components** (typically 8–20 for 80px boxes)
5. Click **Run Classification**

### Step 3: PCA + K-means in MATLAB (direct)
```matlab
% After running PEET, classify aligned particles:
PEETclassify('peet_project.prm', ...
    'nClass',    4,   ...   % number of classes
    'nPCAComp',  10,  ...   % PCA components to use
    'maskFile',  '',  ...   % optional mask
    'fnOutput',  'classification/class')
```

### Step 4: Interpreting results
- Class averages written as `class_001_avg.mrc`, `class_002_avg.mrc`, etc.
- Updated MOTL CSV: column 20 now holds class labels (1..k)
- Compare class assignments to `STA/outputs/motl.txt` column 20 (half-set labels)
  for benchmark evaluation using accuracy / adjusted Rand index

### Step 5: Benchmark comparison
```python
import numpy as np

# Load PEET class assignments from updated MOTL
peet_motl = np.loadtxt('peet_run_MOTL.csv', delimiter=',')
peet_classes = peet_motl[:, 19].astype(int)   # col 20 (0-indexed: 19)

# Load ground-truth labels from existing MOTL
gt_motl = np.loadtxt('../outputs/motl.txt')
gt_labels = gt_motl[:, 19].astype(int)

from sklearn.metrics import adjusted_rand_score
ari = adjusted_rand_score(gt_labels, peet_classes)
print(f"ARI: {ari:.4f}")
```

---

## 9. Expected Outputs

After running `PEET('peet_project.prm')`:

| File | Description |
|---|---|
| `peet_run_avg.mrc` | Grand average of all particles |
| `peet_run_MOTL_iter{N}.csv` | MOTL after each iteration with updated angles/shifts |
| `peet_run_MOTL.csv` | Final MOTL after last iteration |
| `peet_run_FSC.csv` | FSC curve (requires two half-sets) |
| `class_001_avg.mrc` ... | Per-class averages (after classification) |
| `aligned/particle_*.mrc` | Individual aligned particles (if `alignedBaseName` set) |

Visualize averages with:
```bash
3dmod peet_run_avg.mrc
```

---

## 10. Environment Setup

Add both to your shell session (or append to `~/.bashrc`):

```bash
source ~/Applications/IMOD-linux.sh
export PATH=/home/jblaser2/matlab/bin:$PATH
export PEET_HOME=~/Applications/PEET   # after downloading PEET
```

Verify:
```bash
which 3dmod        # should be ~/Applications/IMOD/bin/3dmod
which matlab       # should be /home/jblaser2/matlab/bin/matlab
echo $IMOD_DIR     # should be ~/Applications/IMOD
```

---

## Quick Reference: Minimal Run Checklist

- [ ] Download PEET MATLAB package from bio3d.colorado.edu/PEET
- [ ] Set up environment (source IMOD-linux.sh, MATLAB on PATH)
- [ ] `mkdir -p ~/Research/STA/peet/models`
- [ ] Generate model files: loop over subtomograms → `point2model`
- [ ] Run `generate_peet_prm.py` to produce `peet_project.prm`
- [ ] In MATLAB: `addpath(genpath('~/Applications/PEET')); PEET('peet_project.prm')`
- [ ] Open Etomo Analysis tab → set k → Run Classification
- [ ] Compare class assignments to `STA/outputs/motl.txt` column 20
