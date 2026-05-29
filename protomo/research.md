# Protomo 3.1.0 — How It Works

**Author:** Hanspeter Winkler (2012–2022)
**License:** BSD-style redistribution
**Installation:** `~/Applications/protomo-3.1.0` (sourced via `setup.sh` in `.bashrc`)

Protomo (also called I3/Protomo) is a compiled C suite for cryo-ET tilt-series alignment and
subtomogram classification. It provides the full pipeline from raw tilt series through particle
extraction, iterative alignment, MSA-based dimensionality reduction, and hierarchical clustering.
The suite is headless-compatible (no GUI required for classification); GTK2 GUI tools are present
but unavailable on HPC nodes.

---

## Directory Structure

```
~/Applications/protomo-3.1.0/
├── bin/
│   ├── linux/x86-64/     # 37 compiled binaries
│   ├── subvol/           # Internal helper scripts (not called directly)
│   ├── tomo/             # Internal tomo-reconstruction helpers
│   └── *.sh              # 11 high-level subtomogram workflow scripts + tomo scripts
├── lib/linux/x86-64/     # 17 shared libraries (.so 3.0.0)
├── util/                 # Filter visualization (gnuplot-based)
├── setup.sh              # Sources bin/ and lib/ into PATH/LD_LIBRARY_PATH
├── LICENSE
└── COPYING
```

Source code is not distributed — only precompiled x86-64 Linux binaries.

---

## Core Concepts

### Shell-Variable Parameter System
All workflow scripts source a parameter file (`param.sh`) that exports shell variables. There is
no separate config format — you configure the workflow by editing environment variables in this
file. Cycles inherit these variables at execution time.

### Cycles
Work is organized in numbered cycles (`cycle-000/`, `cycle-001/`, ...) with a configurable
directory prefix (`DIRPRFX`) and file prefix (`CYCPRFX`). Each cycle uses the previous cycle's
class averages as references for the next alignment round.

### Native Image Format (.i3i)
Protomo's primary data container. Tomograms, subtomogram stacks, averages, masks, and SVD
outputs are all stored as `.i3i` files. The software also reads/writes CCP4, SPIDER, EM, and
TIFF formats.

### Process Definition Files (.prep / .proc)
ASCII command lists interpreted by the `tomoprocess` binary. One command per line with
space-separated arguments. Used for data preparation (extraction) and general image processing.

---

## Data Preparation: Tomogram → Particle Stacks

Before classification, subtomograms must be extracted from tomograms into `.i3i` stacks.

### Step 1: Pick particle positions → .pos files
`.pos` files are plain text with one particle per line: `x y z` coordinates in pixel space.

```
48 782 38
46 838 37
45 891 37
```

Each `.pos` file typically represents particles from one tomogram column/tile.

### Step 2: Extract subtomograms via a .prep file (`extract.prep`)
```
mapdir ../maps
map emd_1561.map       # tomogram file
window 90 80 80        # extraction box size (x y z)
area 0.8               # fractional overlap allowed
rotation  1 0 0  0 0 -1  0 1 0   # optional initial rotation matrix

extract ../pos/col0.pos to stacks/col0.i3i
extract ../pos/col1.pos to stacks/col1.i3i
...
```
Run with: `tomoprocess -f extract.prep`

### Step 3: Assemble dataset (`dataset.prep`)
```
search stacks
attach col0.i3i
attach col1.i3i
...
save dataset.i3i
```
Run with: `tomoprocess -f dataset.prep`

This creates a single `dataset.i3i` image stack containing all subtomograms — the input to
the classification workflow.

---

## Subtomogram Classification Workflow

The workflow is iterative: align → SVD (MSA) → HAC clustering → class averages → repeat.

### Overview diagram
```
dataset.i3i (raw subtomograms)
    │
    ▼
subvolinitial.sh       ← initialize database, cycle-000/ directory
    │
    ▼
subvolglobalaverage.sh ← compute global average (used as initial reference)
    │
    ▼
  ┌─── per cycle ─────────────────────────────────────────────────────┐
  │                                                                    │
  │  subvolreference.sh  → filter + mask → reference.i3i              │
  │  subvolalign.sh      → cross-correlate → mra.i3i (aligned stack)  │
  │  subvolsvd.sh        → SVD projection → .sv, .rsv, .coo           │
  │  subvolhac.sh        → HAC clustering → class.i3i                 │
  │  subvolclassaverage.sh → per-class average → .avg files           │
  │  subvolclassalign.sh → align class averages to each other         │
  │  subvolfsc.sh        → even/odd FSC per class → .fsc.dat, .fsc.ps│
  │                                                                    │
  └──── subvolnext.sh 0 1 → seeds cycle-001 from class averages ──────┘
```

### Script-by-script Reference

#### `subvolinitial.sh <dataset>`
Initializes the classification database from a `.i3i` subtomogram stack. Creates `cycle-000/`
and required directory structure.

#### `subvolglobalaverage.sh`
Computes the unaligned sum of all subtomograms. Output is used as the initial reference when
`REFIMG` is blank.

#### `subvolreference.sh <cycle> [image]`
Filters and masks the reference image (or builds one from global average). Applies rectangular,
ellipsoidal, or Gaussian spatial masks and Fourier frequency filters.

Key parameters:
- `MOTIFSIZE` — subtomogram box size in pixels (`"84 64 72"` = x y z)
- `REFIMG` — reference source: blank = global avg, `classaverages` = previous cycle's class avgs
- `REFSEL` — which class averages to use (e.g., `"1-3"` excludes junk class)
- `REFMSKOPT1/2/3` — up to 3 spatial masks (rectangular, elliptic, gaussian)
  - format: `"elliptic x y z apod ax ay az"` where `apod` = soft-edge apodization width
- `REFMOLMSK` — optional binary molecular mask file (same size as MOTIFSIZE)
- `LOWPASS` / `HIGHPASS` — Fourier bandpass, format `"freq freq freq apod apod apod"` in
  fractional Nyquist (0–0.5); applied independently in x, y, z
- `FOUGAUSS` — Gaussian Fourier weighting (optional, sharpens or blurs)

#### `subvolalign.sh <cycle>`
Aligns each raw subtomogram to the reference by cross-correlation (or matched/phase correlation).
This is the most computationally expensive step.

Key parameters:
- `WDGCOMP` — missing wedge compensation (`true`/`false`); compensates for the limited
  angular range of tilt series
- `MRACC` — correlation mode: `xcf` (cross-correlation), `mcf` (matched), `pcf` (phase), `dbl`
- `MRALIMIT` / `MRASTEPS` — angular search range and step size:
  - `"0 180"` / `"0 180"` = search full 360° spin, no tilt-axis search (z-axis rotation only)
  - format: `"nutation spin"` in degrees
- `MRAMSKOPT1/2/3` — masks applied to raw motifs before correlation
- `MRAAREA` — fractional overlap required for valid alignment peak (0–1)
- `MRAPKR` — peak search radius in pixels (`"5 5 5"` = x y z)
- `MRAAVG` — produce global average of all aligned subtomograms (`true`/`false`)

Outputs: `<prefix>-mra.i3i` (aligned stack), `<prefix>-mra.avg` (average if enabled)

#### `subvolsvd.sh <cycle>`
Performs Singular Value Decomposition on the aligned subtomogram stack for dimensionality
reduction. This is the "MSA" (Multivariate Statistical Analysis) step equivalent to correspondence
analysis used in 2D classification.

Key parameters:
- `MSAIMGSIZE` — sub-box size for SVD extraction (`"24 24 36"` x y z); smaller than MOTIFSIZE
  to focus on the central region of interest
- `MSAMASK` — mask strategy:
  - `opt` = use `MSAMSKOPT1/2/3` to build mask from geometric shapes
  - `auto` = automatically determine mask from data
  - filename = use a precomputed mask file
- `MSAMSKOPT1/2/3` — geometric mask shapes for SVD region (e.g., `"elliptic 21 21 0"`)
- `MSAMASKSUPERPOS` — image to overlay mask visualization on; `avg` = use global average
- `MSAIMGMSKOPT1/2/3` — masks applied to individual motifs before projection
- `MSALOWPASS` / `MSAHIGHPASS` — Fourier filters applied before SVD
- `MSAFACT` — max number of singular vectors to compute (dimensions retained)
- `MSAVAR` — compute variance image (`true`/`false`)

Outputs:
- `.sv` — singular values (scree plot equivalent)
- `.rsv` — right singular vectors (eigen-images)
- `.coo` — particle coordinates in SVD space (one row per particle, one column per factor)

#### `subvolhac.sh <cycle>`
Hierarchical Ascendant Classification on the SVD coordinate matrix (`.coo` file). Uses
agglomerative clustering (Ward linkage or similar) to group particles into classes.

Key parameters:
- `CLASSES` — number of classes to generate; can be a list: `"4 8"` produces both 4-class and
  8-class partitions in one run
- `CLSMIN` / `CLSMAX` / `CLSINC` — range of class numbers stored in output (allows checking
  multiple k values without re-running)
- `CLSFACT` — which SVD factors to use for clustering, e.g., `"1-4"` (comma-separated or range)
- `CLSHVO` — fraction of highest-variance outlier particles excluded (junk rejection)
- `CLSHVM` — fraction of highest-variance members within each class excluded
- `CLSMONT` — low-pass frequency for montaged class average visualization (0 = skip)

Output: `<prefix>-class.i3i` — image with per-particle class labels embedded

Note: Class `N` (where N = CLASSES) is always the "junk" class containing excluded particles.
When `CLASSES="4"`, classes 0–3 are real classes and class 4 is junk.

#### `subvolclassaverage.sh <cycle>`
Computes the average of all particles assigned to each class. Uses the aligned subtomograms
from `subvolalign.sh`.

Output: `<prefix>-avg<N>.i3i` per class (one file per class)

#### `subvolclassalign.sh <cycle>`
Aligns class averages to each other using the same cross-correlation machinery as particle
alignment. Parameters mirror the MRA parameters but with `SEL*` prefix.

Key parameters:
- `SELNR` — which classification (by number of classes) to use for alignment
- `SELAVG` — which class indices to include (e.g., `"0-3"` to exclude junk class `4`)
- `SELLIMIT` / `SELSTEPS` — angular search for class average alignment

#### `subvolfsc.sh <cycle>`
Computes gold-standard Fourier Shell Correlation for each class average by splitting particles
into even/odd halves, averaging each half separately, and computing FSC between them.

Key parameters:
- `FSCMSKOPT1/2/3` — spatial masks applied before FSC computation
- `FSCCLASS` — also compute FSC for class averages (not just global average)

Outputs: `<prefix>-fsc.dat` (correlation vs. spatial frequency table), `<prefix>-fsc.ps`
(PostScript plot, view with gnuplot or convert to PNG)

#### `subvolnext.sh <current> <next>`
Seeds the next cycle directory from the results of the current one. Class averages from cycle N
become the reference for alignment in cycle N+1.

Example: `subvolnext.sh 0 1` → creates `cycle-001/` initialized from `cycle-000/` results.

---

## Full Workflow Command Sequence

```sh
# Environment
source ~/Applications/protomo-3.1.0/setup.sh

# --- Data preparation (run once) ---
# 1. Pick particles → place .pos files in pos/
# 2. Extract subtomograms
tomoprocess -f prepare/extract.prep
# 3. Assemble dataset
tomoprocess -f prepare/dataset.prep

# --- Classification (copy and edit process/template-initial.sh as param.sh) ---
cp process/template-initial.sh param.sh
# Edit param.sh: set MOTIFSIZE, LOWPASS, HIGHPASS, CLASSES, etc.

# Cycle 0
subvolinitial.sh dataset.i3i
subvolglobalaverage.sh
subvolreference.sh 0
subvolalign.sh 0
subvolsvd.sh 0
subvolhac.sh 0
subvolclassaverage.sh 0
subvolclassalign.sh 0
subvolfsc.sh 0

# Inspect results, then iterate
cp process/template-cycle-1.sh cycle-001-param.sh
# Edit: set REFIMG="classaverages", REFSEL="1-3" (exclude junk), adjust CLASSES
subvolnext.sh 0 1
subvolreference.sh 1
subvolalign.sh 1
subvolsvd.sh 1
subvolhac.sh 1
subvolclassaverage.sh 1
subvolclassalign.sh 1
subvolfsc.sh 1
```

---

## Parameter File Reference

All parameters are shell variables exported in `param.sh`. The tutorial provides
`template-initial.sh` (cycle 0, uses global average as reference) and `template-cycle-1.sh`
(subsequent cycles, uses class averages as reference — only `REFIMG` differs).

| Variable | Example | Description |
|---|---|---|
| `DATADIR` | `"../prepare/stacks"` | Path to input `.i3i` stacks |
| `DIRPRFX` | `"cycle-"` | Directory name prefix |
| `CYCPRFX` | `"hst-"` | Output file name prefix |
| `MOTIFSIZE` | `"84 64 72"` | Subtomogram box size (x y z) |
| `WDGCOMP` | `false` | Missing wedge compensation |
| `REFIMG` | `""` or `"classaverages"` | Reference source |
| `REFSEL` | `"1-3"` | Class range to use as reference |
| `REFMSKOPT1/2/3` | `"elliptic 45 45 0 apod 7 7 0"` | Reference spatial masks |
| `LOWPASS` | `"0.400 0.400 0.400 apod 0.050 0.050 0.050"` | Fourier low-pass (per-axis, fractional Nyquist) |
| `HIGHPASS` | `"0.060 0.060 0.060 apod 0.007 0.007 0.007"` | Fourier high-pass |
| `FOUGAUSS` | `""` | Gaussian Fourier weight |
| `MRACC` | `"xcf"` | Correlation mode (xcf/mcf/pcf/dbl) |
| `MRALIMIT` | `"0 180"` | Angular search (nutation, spin) degrees |
| `MRASTEPS` | `"0 180"` | Angular step sizes |
| `MRAPKR` | `"5 5 5"` | Peak search radius (x y z) |
| `MRAAREA` | `0.8` | Fractional overlap for valid peak |
| `MRAAVG` | `"true"` | Produce global average after alignment |
| `MSAIMGSIZE` | `"24 24 36"` | Sub-box size for SVD |
| `MSAMASK` | `"opt"` | SVD mask: filename, `opt`, or `auto` |
| `MSAMSKOPT1/2/3` | `"elliptic 21 21 0"` | Geometric masks for SVD region |
| `MSAIMGMSKOPT1/2/3` | `"elliptic 45 45 0 apod 7 7 0"` | Masks applied to motifs before SVD |
| `MSALOWPASS/HIGHPASS` | same as LOWPASS | Fourier filters for SVD |
| `MSAFACT` | `40` | Max SVD factors to compute |
| `MSAVAR` | `"true"` | Compute variance image |
| `CLASSES` | `"4 8"` | Number(s) of classes |
| `CLSMIN/MAX/INC` | `2 / 8 / 2` | Range of k stored in output |
| `CLSFACT` | `"1-4"` | SVD factors used for clustering |
| `CLSHVO` | `0.1` | Fraction of outlier particles to discard |
| `CLSHVM` | `0.1` | Fraction of outlier class members to discard |
| `CLSMONT` | `0.4` | Low-pass for class average montage |
| `SELNR` | `4` | Number of classes for class-average alignment |
| `SELAVG` | `"0-3"` | Class indices to include (excludes junk) |
| `FSCMSKOPT1/2/3` | `"elliptic 31 31 0 apod 7 7 0"` | FSC masks |
| `FSCCLASS` | `"false"` | Compute per-class FSC |
| `CYCLOG` | `"true"` | Print progress messages |
| `GLBLAVG` | `"false"` | Produce global average each cycle |
| `YPERM` | `"true"` | Produce side views (y-permuted) of averages |
| `CYCDBG` | `"false"` | Write intermediate debug files |

---

## File Format Reference

| Extension | Description |
|---|---|
| `.i3i` | Native Protomo image / image stack (subtomograms, averages, masks) |
| `.prep` / `.proc` | ASCII command list for `tomoprocess` |
| `.tlt` | Tilt angle file (tomogram metadata) |
| `.pos` | Particle positions: one `x y z` per line (picked coordinates) |
| `.sv` | Singular values (SVD scree data) |
| `.rsv` | Right singular vectors (eigen-images) |
| `.coo` | Particle coordinates in SVD space (input to HAC) |
| `.cls` | Classification result labels |
| `.avg` | Class average image |
| `.wgt` | Weight map |
| `.fsc` / `.fsc.dat` | FSC data (frequency vs. correlation table) |
| `.fsc.ps` | PostScript FSC plot (gnuplot-rendered) |
| `.dat` | Generic ASCII data |

---

## Key Binaries

| Binary | Purpose |
|---|---|
| `protomo` | Main engine (tilt-series alignment) |
| `tomoprocess` | General image processing, reads `.prep`/`.proc` command files |
| `tomoclass` | Classification engine (SVD + clustering); called by `subvol*.sh` scripts |
| `i3avg` | Image averaging |
| `i3fsc` | Fourier Shell Correlation |
| `i3fourier` | FFT operations |
| `i3mask` | Mask creation / application |
| `i3register` | Image registration |
| `i3resample` | Resampling / interpolation |
| `i3match` | Template matching |
| `i3peak3d` | 3D peak detection |
| `i3stat` | Image statistics |
| `i3montage` | Create image montages |
| `i3unbend3d` | 3D unwarping (requires libdierckx) |
| `tomoalign-gui` | GTK2 GUI — unavailable on headless HPC |
| `i3display` | Image viewer — unavailable on headless HPC |

---

## Shared Libraries

| Library | Description |
|---|---|
| `libi3core.so.3.0.0` (1.3 MB) | Core algorithms |
| `libi3series.so.3.0.0` | Image series handling |
| `libi3tomo.so.3.0.0` | Tomography-specific functions |
| `libi3fourier.so.3.0.0` | FFT and frequency-domain operations |
| `libi3fftpack.so.3.0.0` | FFTPACK routines |
| `libi3ccp4io.so.3.0.0` | CCP4 format I/O |
| `libi3emio.so.3.0.0` | EM format I/O |
| `libi3tiffio.so.3.0.0` | TIFF I/O |
| `libi3spiderio.so.3.0.0` | SPIDER format I/O |
| `libi3imagicio.so.3.0.0` | Generic image I/O |
| `libi3suprimio.so.3.0.0` | SUPRIM format I/O |
| `libminpack.so` | Levenberg-Marquardt optimization (locally compiled from netlib) |
| `libdierckx.so` | B-spline fitting (locally compiled from netlib) |
| `libi3gui.so.3.0.0` | GTK2 graphics (unavailable on headless HPC) |

---

## Tutorial Data

Extracted to `~/Research/STA/protomo/tutorial/protomo-subvolume-tutorial-3.0/`

```
all-pos/    # Full set of .pos files (13 tomograms, col0–colm)
pos/        # Subset used in tutorial
prepare/    # dataset.prep and extract.prep command files
process/    # template-initial.sh, template-cycle-1.sh, template-cycle-2.sh
maps/       # Reference to map files (emd_1561.map — not included, download separately)
```

The tutorial dataset is HST (hollow-sphere test; synthetic protein complex columns) with
particles arranged in pseudo-helical arrays. It demonstrates how to run 2 cycles and obtain
4- and 8-class averages showing structural heterogeneity of the GroEL-like barrel.

---

## Notes and Limitations

- **Binaries only.** No source code is distributed; algorithm internals are opaque beyond what
  the scripts reveal.
- **GUI unavailable on HPC.** `tomoalign-gui` and `i3display` require GTK2. All classification
  steps work headlessly; inspection of `.ps` plots requires converting to PNG (e.g., `ps2pdf` +
  `convert`) or transferring to a desktop.
- **Missing wedge compensation.** `WDGCOMP=false` is the default in the tutorial, but for real
  cryo-ET data with a limited tilt range this may affect alignment quality. Enable by setting
  `WDGCOMP="true"` and providing tilt geometry.
- **Junk class.** The highest-numbered class is always the excluded/junk partition. When
  selecting class averages as references (`REFSEL`), explicitly exclude it (e.g., `"0-3"` for a
  4-class run).
- **Factor selection is critical.** `CLSFACT` controls which SVD factors drive the clustering.
  Including too many factors incorporates noise; too few misses real variation. Inspect eigenvalue
  scree (`.sv` file) to choose an appropriate cutoff.
- **libminpack and libdierckx** were compiled from netlib Fortran source during installation
  because no pre-built versions were compatible with RHEL 10. Both `.so` files live in
  `lib/linux/x86-64/` alongside the package libraries.
