# 2026-05-29 — Protomo (I3) Installation, Setup, and First Classification Run

**Goal:** Get Protomo 3.1.0 fully documented, run its subtomogram classification pipeline on
the 672 T4P particles, diagnose and fix problems, and push clean results to GitHub.

---

## What Was Done

### 1. Codebase Documentation (`protomo/research.md`)
Explored the full Protomo 3.1.0 installation at `~/Applications/protomo-3.1.0` and wrote a
comprehensive research document covering:
- Directory structure (37 binaries, 51 workflow scripts, 17 shared libraries)
- Core concepts: shell-variable parameter system, `.i3i` format, numbered cycle workflow
- Complete subtomogram classification pipeline with every script annotated
- Full parameter reference table (drawn from the tutorial param files)
- File format reference (`.i3i`, `.coo`, `.sv`, `.rsv`, `.cls`, `.avg`, `.fsc`, etc.)
- Known limitations (binaries-only, no GTK2 GUI on headless HPC, ILP64/LP64 LAPACK issue)

Also extracted the v3.0 tutorial archive into `protomo/tutorial/` (sample `.pos` files and
workflow scripts demonstrating a worked example on insect flight muscle).

### 2. Classification Pipeline Setup (`~/Research/protomo/`)
All processing lives locally under `~/Research/protomo/` (not on GitHub — large outputs).

**Key setup steps:**
- Created `prepare/stacks/` with symlinks to all 672 MRC files (Protomo requires relative
  paths in `.prep` files, so absolute paths via symlink is the workaround)
- Assembled `prepare/dataset.i3i` index file via `tomoprepare -log dataset.prep`
- Wrote `process/param-template.sh` adapted from the tutorial for 80×80×80 T4P subtomos:
  - `MOTIFSIZE="80 80 80"`, `CLASSES="2"`, spherical masks instead of actin-slab masks
  - `MRALIMIT=` / `MRASTEPS=` blank (translation-only, no rotation — particles prealigned)
  - `CLSFACT="1-4"`, `CLSHVO=0.1`, `CLSHVM=0.1` (10% junk exclusion)

### 3. Technical Issues Encountered (and Solutions)

**Issue A: `tomoprepare` refuses absolute paths in `attach` commands.**
- Root cause: Protomo's file resolution uses a `search` directory + relative filenames.
  Absolute paths are explicitly rejected.
- Fix: Created `prepare/stacks/` with symlinks; used `search stacks` in the prep file.
  When `tomoprepare` runs from `prepare/`, it stores the resolved absolute path of `stacks/`
  in `dataset.i3i`, so the index still works after `subvolinitial.sh` copies it to `cycle-000/`.

**Issue B: `DATADIR` path mismatch (i3_filepath not finding MRC files).**
- Root cause: `subvolsetup.sh` sets `i3_filepath=".:${DIR}:${DATADIR}"`. We had
  `DATADIR="../prepare"` but the MRC symlinks live in `../prepare/stacks`.
- Fix: Changed to `DATADIR="../prepare/stacks"` in `param-template.sh`.

**Issue C: SVD (`subvolsvd.sh`) crashes with `SGESDD error code 140295106723840`.**
- Root cause: Protomo's `tomoclass` binary uses 64-bit Fortran integers for LAPACK calls
  (ILP64), but the conda OpenBLAS in `~/miniforge3/lib/liblapack.so.3` uses 32-bit integers
  (LP64). When LAPACK writes a 4-byte `INFO=0` result, Protomo reads 8 bytes → garbage value
  → reports false error.
- Fix: Preload MATLAB R2024a's MKL (which is ILP64-compatible) before running SVD/HAC:
  ```
  LD_PRELOAD="/usr/local/MATLAB/R2024a/bin/glnxa64/mkl.so \
              /usr/local/MATLAB/R2024a/sys/os/glnxa64/libiomp5.so" \
  subvolsvd.sh 0
  ```
  This must be applied to every `subvolsvd.sh` and `subvolhac.sh` call.

**Issue D: Class averages showed ~20px lateral offset.**
- Root cause: Despite `MRALIMIT` and `MRASTEPS` being blank (translation-only mode),
  `MRAPKR="5 5 5"` still allowed the CCF peak search within a 5-pixel radius. But more
  importantly, 438 of 672 particles (65%) were extracted near the edges of their source
  tomograms. Protomo stores the original tomogram bounds in `.i3i` metadata and marks these
  particles as having < 80% box overlap. When averaged, their off-center density pulls the
  class average off-axis.
- Fix 1 (tried): Set `MRAPKR="0 0 0"` to force the peak to origin (zero translation).
  Result: PNGs unchanged — the real cause was the edge particles, not alignment shifts.
- Fix 2 (applied): Filtered out all 438 edge particles (overlap < 0.8) before building
  the dataset. Only 234 fully-centered particles were used for classification.

---

## Final Classification Results

**Dataset:** 234 of 672 T4P subtomograms (80×80×80, fully within tomogram bounds)

**Settings:**
- No rotation, no translation alignment (`MRALIMIT` blank, `MRAPKR="0 0 0"`)
- SVD with 40 factors, clustering using factors 1–4
- 10% junk exclusion (`CLSHVO=0.1`, `CLSHVM=0.1`)
- 2-class partition (`CLASSES="2"`)

**Results:**

| Class | Particles | Fraction |
|---|---|---|
| Class 0 | 111 | 47.4% |
| Class 1 | 80 | 34.2% |
| Junk | 43 | 18.4% |

- **Top singular values (scree):** 10.02, 6.06, 5.43, 5.20, 4.76, ...
  (decreasing slowly — no clear "elbow," suggesting gradual continuous variation or noise dominance)
- **Class-to-class cross-correlation:** 0.921 (high — the two class averages are very similar)
- **Class average density range:** ±1.8 (higher contrast than the unfiltered run's ±1.1)

**Result files:**
- `protomo/results/clustering_scatter.png` — SVD factor-space scatter plot (factors 1v2, 1v3, 2v3)
- `protomo/results/class_averages_slices.png` — central XY, XZ, YZ slices of each class average

---

## Interpretation and Caveats

**What the 0.921 inter-class cross-correlation means:**
The two classes are very similar to each other. This can arise from several causes:
1. **Small dataset:** 234 particles is quite small for 3D classification. SNR per class is low,
   so class averages are noisy and hard to distinguish.
2. **Continuous heterogeneity:** T4P conformational changes may be continuous (not discrete),
   in which case 2-class HAC clustering will always find two halves of a continuum, not two
   genuinely distinct states.
3. **Noise-dominated SVD:** The scree plot shows no clear elbow, meaning the top factors may
   be capturing noise or missing-wedge artifacts rather than structural signal. Using only
   factors 1–4 for HAC may not be selecting the most biologically meaningful dimensions.
4. **No missing-wedge compensation:** `WDGCOMP=false`. For a single-axis tilt series, the
   missing wedge creates systematic density artifacts. All particles in this dataset are from
   the same tomogram orientation, so the wedge effect is identical across particles and may
   not affect classification much — but it's worth noting.

**The 65% edge-particle rate is unusually high.** It suggests the original T4P picking was done
over the full tomogram volume without excluding particles near the z-boundaries (typically the
thin dimension in tilt series). For a refined analysis, re-picking with a z-margin exclusion
would recover more usable particles.

**Comparison to other packages:**
- PyTom k=2 and k=3 also showed near-identical class averages (known blocker). The
  similarity between packages suggests the T4P dataset may genuinely lack strong discrete
  classification signal — either continuous heterogeneity or insufficient particle count.
- The synthetic datasets (ETSimulations) will be critical for benchmarking: they'll provide
  ground truth to distinguish "no real classes" from "package can't find real classes."

---

## Files in This Repo from This Session

```
protomo/
├── research.md                   ← full Protomo codebase documentation
├── tutorial/                     ← extracted v3.0 tutorial (insect flight muscle)
│   └── protomo-subvolume-tutorial-3.0/
│       ├── pos/ all-pos/         ← .pos particle position files
│       ├── prepare/              ← dataset.prep, extract.prep
│       └── process/              ← template-initial.sh, template-cycle-1.sh, ...
└── results/
    ├── clustering_scatter.png    ← SVD factor-space scatter (234 filtered particles)
    └── class_averages_slices.png ← central slices of 2 class averages + junk
```

**Local only (not on GitHub):** `~/Research/protomo/` — dataset.i3i, cycle-000/, all .avg/.coo/.sv files.

---

## How to Re-run (or Continue to Cycle 1)

Environment setup required for every run:
```bash
source ~/Applications/protomo-3.1.0/setup.sh
cd ~/Research/protomo/process
```

SVD and HAC require MKL preload (ILP64 fix):
```bash
export MKLLIB="/usr/local/MATLAB/R2024a/bin/glnxa64/mkl.so \
               /usr/local/MATLAB/R2024a/sys/os/glnxa64/libiomp5.so"
LD_PRELOAD="$MKLLIB" subvolsvd.sh 0
LD_PRELOAD="$MKLLIB" subvolhac.sh 0
```

To run a second cycle using class averages as references:
```bash
# Edit param-template.sh: REFIMG="classaverages", REFSEL="0-1"
subvolnext.sh 0 1
subvolreference.sh 1
subvolalign.sh 1
LD_PRELOAD="$MKLLIB" subvolsvd.sh 1
LD_PRELOAD="$MKLLIB" subvolhac.sh 1
subvolclassaverage.sh 1
subvolclassalign.sh 1
```

To regenerate result PNGs:
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate eman2
source ~/Applications/protomo-3.1.0/setup.sh
python3 ~/Research/protomo/process/visualize.py
```

---

## Next Steps for Protomo

- [ ] Try k=3 and k=4 (change `CLASSES="3"` / `"4"` in param-template.sh)
- [ ] Run a second cycle with `REFIMG="classaverages"` to see if classes sharpen
- [ ] Compute FSC per class (`subvolfsc.sh 0`) for resolution estimate
- [ ] Consult Stefano on whether 0.921 inter-class CC is expected for T4P or indicates
      no real discrete heterogeneity
- [ ] Re-pick particles with z-margin exclusion to recover more of the 672 original particles
