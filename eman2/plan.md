# Classification Pipeline Plan: 672 Pili Subtomogram Volumes

## Dataset Summary

| Property | Value |
|----------|-------|
| Particles | 672 MRC files, `aligned_tom{NNN}_P{MMMM}.mrc` |
| Box size | 80 × 80 × 80 voxels |
| Pixel size | 13.328 Å/px |
| Nyquist | 26.7 Å |
| Physical box | ~1066 Å (~106 nm) |
| Orientation | Pili axis along Z (rotated after extraction) |
| Tilt range | ±60° |
| Missing wedge | Rotated with particles — **NOT at standard Z orientation** |
| References | None |
| Target classes | 2–3 |
| Platform | RHEL 10 workstation, NVIDIA RTX 5080 |
| EMAN2 version | Latest (conda install) |

---

## Algorithm Choice

Since we have no references, reference-based classification (`e2spt_classify.py`) is out. Given the pre-aligned pili axis and the goal of 2–3 classes, **Fourier-PCA + K-Means** (`e2spt_pcasplit.py`) is the recommended primary algorithm. It operates in Fourier space, is robust to noise, and uses an unsupervised approach well-suited for heterogeneity discovery.

**Missing wedge caveat:** The particles were rotated post-extraction so the pili axis aligns with Z. This means the missing wedge is NOT along EMAN2's default Z orientation — it has been rotated along with each particle. We therefore use `--nowedgefill` to skip the wedge masking, which prevents the code from incorrectly zeroing out valid Fourier signal. The cost is that wedge-related noise is included, but with 672 well-aligned particles this is acceptable.

**Alternative:** `e2classifykmeans.py` (voxel-space K-Means, no setup required) is also documented at the end as a quick-check option.

---

## Directory Layout

```
/home/ejl62/groups/grp_tomo/Pili_PCA/
├── particles/                       # original MRC files (input, read-only)
│   └── aligned_tom*.mrc
└── eman2_project/                   # all EMAN2 work goes here
    ├── particles.hdf                # single stacked HDF (672 particles)
    ├── ptcls.lst                    # EMAN2 particle list file
    ├── make_project.py              # Step 2 setup script
    ├── spt_01/                      # synthetic refinement dir (Step 3)
    │   ├── threed_01.hdf            # simple average as reference
    │   ├── particle_parms_01.json   # identity transforms for each particle
    │   └── mask_tight.hdf          # cylindrical mask along Z
    └── sptcls_01/                   # pcasplit output (auto-created)
        ├── ptcls_cls01.lst          # class 1 particle list
        ├── ptcls_cls02.lst          # class 2 particle list
        ├── pca_ptcls.txt            # PCA coordinates for all particles
        ├── pca_basis.hdf            # PCA eigenvector volumes
        └── particle_parms_01.json   # alignment params per class
```

---

## Step 1 — Environment Setup

EMAN2 runs directly on the RHEL 10 workstation. Activate the conda environment and verify the install:

```bash
conda activate eman2
which e2version.py && e2version.py

# Create project directory
mkdir -p /home/ejl62/groups/grp_tomo/Pili_PCA/eman2_project
cd /home/ejl62/groups/grp_tomo/Pili_PCA/eman2_project
```

**GUI:** All EMAN2 graphical tools (`e2display.py`, `e2projectmanager.py`, `e2spt_boxer.py`) work natively on RHEL 10 via X11/Wayland. The RTX 5080 drives both display and GPU-accelerated processing. Launch the project manager to browse results interactively at any point:

```bash
e2projectmanager.py &
```

**CUDA check:** EMAN2's GPU alignment requires CUDA. The RTX 5080 needs CUDA 12.5+ — verify the conda environment ships a compatible runtime:

```bash
python3 -c "import EMAN2; print(EMAN2.EMUtil.cuda_available())"
```

---

## Step 2 — Data Ingestion

Convert 672 individual MRC files into a single HDF stack and create an EMAN2 particle list. Run directly on the workstation — takes 1–2 minutes:

**`make_project.py`** (create this file in `eman2_project/`):

```python
#!/usr/bin/env python
"""
Converts 672 MRC particles to EMAN2 HDF stack + LST + identity-transform JSON.
Run from: /home/ejl62/groups/grp_tomo/Pili_PCA/eman2_project/
"""
from EMAN2 import *
import glob, os, json

PARTICLES_DIR = "/home/ejl62/groups/grp_tomo/Pili_PCA/particles"
APIX = 13.328
PROJECT_DIR = "/home/ejl62/groups/grp_tomo/Pili_PCA/eman2_project"
SPT_DIR = os.path.join(PROJECT_DIR, "spt_01")

# ── 1. Stack all MRC files into particles.hdf ────────────────────────────────
mrc_files = sorted(glob.glob(os.path.join(PARTICLES_DIR, "aligned_tom*.mrc")))
print(f"Found {len(mrc_files)} MRC files")

out_hdf = os.path.join(PROJECT_DIR, "particles.hdf")
if os.path.exists(out_hdf):
    os.remove(out_hdf)

for i, f in enumerate(mrc_files):
    e = EMData(f)
    e["apix_x"] = e["apix_y"] = e["apix_z"] = APIX
    e["source_path"] = f               # track origin
    e["source_n"] = i
    e.write_image(out_hdf, i)
    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(mrc_files)}")

print(f"Wrote {len(mrc_files)} particles → {out_hdf}")

# ── 2. Create LST particle list ───────────────────────────────────────────────
lst_path = os.path.join(PROJECT_DIR, "ptcls.lst")
lst = LSXFile(lst_path, False)
for i in range(len(mrc_files)):
    lst.write(-1, i, out_hdf, " ")
lst.close()
print(f"Wrote particle list → {lst_path}")

# ── 3. Create spt_01/ with reference average + identity-transform JSON ────────
os.makedirs(SPT_DIR, exist_ok=True)

# Build simple average as reference
print("Averaging all particles for reference...")
avgr = Averagers.get("mean")
for i in range(len(mrc_files)):
    avgr.add_image(EMData(out_hdf, i))
avg = avgr.finish()
avg["apix_x"] = avg["apix_y"] = avg["apix_z"] = APIX
ref_path = os.path.join(SPT_DIR, "threed_01.hdf")
avg.write_image(ref_path, 0)
print(f"Wrote reference → {ref_path}")

# Build identity-transform JSON
# Format: key = "('path/to/particles.hdf', index)" → {"xform.align3d": <identity>, "score": 0.0}
identity = Transform()                    # EMAN2 identity transform
parms = {}
for i in range(len(mrc_files)):
    k = f"('{out_hdf}', {i})"
    parms[k] = {"xform.align3d": identity, "score": 0.0}

json_path = os.path.join(SPT_DIR, "particle_parms_01.json")
js = js_open_dict(json_path)
js.update(parms)
js.close()
print(f"Wrote identity transforms → {json_path}")

# ── 4. Create a cylindrical mask along Z ─────────────────────────────────────
# Cylinder axis = Z (pili axis); full box height; radius 20 px in XY.
# At 13.328 Å/px, r=20 px ≈ 267 Å — generous enough to contain the pili
# without including much background. Adjust CYLINDER_RADIUS if density
# is clipped when viewing the masked average in e2display.py.
import numpy as np
BOX = 80
CX, CY = BOX // 2, BOX // 2
CYLINDER_RADIUS = 20  # pixels; tune after inspecting masked average

msk = EMData(BOX, BOX, BOX)
msk.to_zero()
arr = msk.numpy()                          # shape (nz, ny, nx), view into EMData
y_idx, x_idx = np.mgrid[0:BOX, 0:BOX]
disk = ((x_idx - CX)**2 + (y_idx - CY)**2) <= CYLINDER_RADIUS**2
arr[:] = disk[np.newaxis, :, :]            # broadcast disk to all Z slices
msk_path = os.path.join(SPT_DIR, "mask_tight.hdf")
msk.write_image(msk_path, 0)
print(f"Wrote cylindrical mask (r={CYLINDER_RADIUS} px = {CYLINDER_RADIUS*APIX:.0f} Å) → {msk_path}")

print("\nSetup complete. Ready for e2spt_pcasplit.py")
```

Run it:

```bash
cd /home/ejl62/groups/grp_tomo/Pili_PCA/eman2_project
python make_project.py
```

This takes 1–2 minutes. Run it directly in the terminal.

---

## Step 3 — Compatibility Check

The newest EMAN2 release likely ships with Python 3.11+ and a modern NumPy, so these issues may already be fixed. Verify before running:

```bash
# Check for known broken lines in e2spt_pcasplit.py
SCRIPT=$(which e2spt_pcasplit.py)
grep -n "np\.int\b\|find_peaks_cwt" "$SCRIPT"
```

**If `np.int` appears** (NumPy ≥ 1.24 removed this alias), patch it:

```bash
sed -i 's/r = r\.astype(np\.int)/r = r.astype(np.int64)/' "$SCRIPT"
```

**If `find_peaks_cwt` appears** (removed from SciPy ≥ 1.12), comment it out — it is never called:

```bash
sed -i 's/^from scipy.signal import find_peaks_cwt/# from scipy.signal import find_peaks_cwt/' "$SCRIPT"
```

After patching, do a dry-run import check:

```bash
python3 -c "import e2spt_pcasplit" && echo "OK"
```

---

## Step 4 — PCA Classification

### 4a. Single run (start here)

```bash
cd /home/ejl62/groups/grp_tomo/Pili_PCA/eman2_project

e2spt_pcasplit.py \
  --path spt_01 \
  --iter 1 \
  --nclass 2 \
  --nbasis 8 \
  --maxres 30 \
  --sym c1 \
  --nowedgefill \
  --verbose 1
```

**Parameter rationale:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| `--path spt_01` | `spt_01` | Points to our synthetic refinement dir |
| `--iter 1` | 1 | Matches `particle_parms_01.json` and `threed_01.hdf` |
| `--nclass 2` | 2 | Start with binary split; repeat with 3 |
| `--nbasis 8` | 8 | More basis vectors than classes to see separation; 5–10 is reasonable |
| `--maxres 30` | 30 Å | Band-limits to ~30 Å; safe relative to 26.7 Å Nyquist; removes noise |
| `--sym c1` | c1 | No symmetry — check for c1 heterogeneity first |
| `--nowedgefill` | on | **Critical:** particles were rotated post-extraction, wedge is NOT at Z |
| `--verbose 1` | 1 | Shows per-particle progress |

Output is written to a new `sptcls_01/` directory.

### 4b. Run in the background (optional)

`e2spt_pcasplit.py` is single-threaded and takes 5–20 minutes for 672 × 80³ particles. To keep the terminal free and capture a log:

```bash
nohup e2spt_pcasplit.py \
  --path spt_01 \
  --iter 1 \
  --nclass 2 \
  --nbasis 8 \
  --maxres 30 \
  --sym c1 \
  --nowedgefill \
  --verbose 1 \
  > pca_classify.log 2>&1 &

echo "PID: $!"
tail -f pca_classify.log   # follow progress; Ctrl-C to detach
```

---

## Step 5 — Inspect Results

### 5a. Plot PCA scatter

```python
#!/usr/bin/env python3
"""
Plots PCA scatter for the first three components.
Run from eman2_project/ after pcasplit completes.
"""
import numpy as np
import matplotlib.pyplot as plt
import glob, os

# Find the most recent sptcls output
dirs = sorted(glob.glob("sptcls_*/pca_ptcls.txt"))
pca_file = dirs[-1]
print(f"Loading {pca_file}")

data = np.loadtxt(pca_file)
ptcl_ids = data[:, 0].astype(int)
coords = data[:, 1:]          # columns 1..nbasis are PCA coordinates

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
pairs = [(0, 1), (0, 2), (1, 2)]
labels = ["PC1", "PC2", "PC3"]

for ax, (i, j) in zip(axes, pairs):
    ax.scatter(coords[:, i], coords[:, j], alpha=0.5, s=10)
    ax.set_xlabel(labels[i])
    ax.set_ylabel(labels[j])
    ax.set_title(f"{labels[i]} vs {labels[j]}")

plt.tight_layout()
plt.savefig("pca_scatter.png", dpi=150)
print("Saved pca_scatter.png")
plt.show()
```

**Interpretation guide:**
- Clear clusters → distinct particle classes, K-Means assignment is reliable
- Continuous cloud → conformational continuum; 2–3 classes still valid but boundaries are soft
- Outlier points far from the main cloud → junk particles / damaged particles; use `--clean` flag on a re-run

### 5b. View class averages

`e2spt_pcasplit.py` automatically runs `e2spt_average.py` on each class after classification. Class averages appear in `sptcls_01/threed_01.hdf` and `threed_02.hdf`. View them with:

```bash
e2display.py sptcls_01/threed_01.hdf sptcls_01/threed_02.hdf
```

Or read statistics:

```python
from EMAN2 import EMData
for i in (1, 2):
    e = EMData(f"sptcls_01/threed_0{i}.hdf")
    n = EMData(f"sptcls_01/ptcls_cls0{i}.lst")   # won't load, just checking
    print(f"Class {i}: {e['nx']}^3, mean={e['mean']:.4f}, sigma={e['sigma']:.4f}")
```

Check the class counts in the log output (the `Class: Particle count` block) or count LST file lines:

```bash
wc -l sptcls_01/ptcls_cls*.lst
```

### 5c. Decision tree after inspection

```
PCA scatter shows:
├── 2 clear clusters      → nclass=2 was correct, proceed to Step 6
├── 3 clear clusters      → re-run Step 4 with --nclass 3
├── 1 tight cloud         → all particles are similar; no major classes
├── Outlier fringe        → re-run with --clean flag to remove outliers first
└── Noisy / no structure  → try --maxres 40 or --nbasis 12; or try e2classifykmeans.py
```

---

## Step 6 — Iterate if Needed

### Re-run with different parameters

```bash
# Try 3 classes with --clean outlier removal
e2spt_pcasplit.py \
  --path spt_01 \
  --iter 1 \
  --nclass 3 \
  --nbasis 10 \
  --maxres 35 \
  --sym c1 \
  --nowedgefill \
  --clean \
  --verbose 1
```

Each run creates a new auto-numbered `sptcls_XX/` directory so previous results are not overwritten.

### Re-run with alignment refinement

If class averages look noisy or misaligned, optionally run a proper 1-iteration refinement first to get better per-particle alignment, then re-run pcasplit on those results:

```bash
# 1-iteration SPT refinement — runs on the RTX 5080 workstation
e2spt_refine.py ptcls.lst \
  --path spt_02 \
  --iter 1 \
  --sym c1 \
  --threads 16 \
  --maxtilt 60 \
  --verbose 1

# Then re-run pcasplit on spt_02
e2spt_pcasplit.py \
  --path spt_02 \
  --iter 1 \
  --nclass 2 \
  --nbasis 8 \
  --maxres 30 \
  --sym c1 \
  --nowedgefill \
  --verbose 1
```

`e2spt_refine.py` with `--maxtilt 60` correctly handles the standard ±60° missing wedge in the original tomogram frame. Note: this alignment works best if particles are in their original extracted orientation; since they have been rotated to Z, you may want to use `--orientgen eman:delta=5:phitoo=1:inc_mirror=1` to limit the angular search to small refinements around the current orientation.

---

## Step 7 — Per-Class Refinement (Optional)

Once classes are defined, generate high-quality per-class averages by refining each class subset independently:

```bash
for CLASS in 01 02; do
  e2spt_refine.py sptcls_01/ptcls_cls${CLASS}.lst \
    --path spt_cls${CLASS} \
    --iter 3 \
    --sym c1 \
    --threads 16 \
    --maxtilt 60 \
    --verbose 1
done
```

Run classes sequentially as shown, or in two terminals in parallel to use the workstation fully. This produces `spt_cls01/threed_03.hdf` and `spt_cls02/threed_03.hdf` — the final per-class averages. FSC curves (`fsc_masked_03.txt`) give resolution estimates for each class.

**GPU acceleration:** If EMAN2 detects CUDA (Step 1 check), add `--parallel gpu:1` to use the RTX 5080 for the alignment inner loop — can cut wall time by 3–5×:

```bash
e2spt_refine.py sptcls_01/ptcls_cls01.lst \
  --path spt_cls01 \
  --iter 3 \
  --sym c1 \
  --threads 16 \
  --parallel gpu:1 \
  --maxtilt 60 \
  --verbose 1
```

---

## Alternative: Direct K-Means (`e2classifykmeans.py`)

If the PCA approach fails or you want a fast sanity check with no setup:

```bash
# No spt_01/ directory needed — operates directly on the HDF stack
e2classifykmeans.py particles.hdf \
  --nclasses 2 \
  --normalize \
  --verbose 1
```

This performs K-Means in real (voxel) space and outputs class averages. It is less principled than Fourier-PCA (ignores missing wedge structure, no dimensionality reduction) but runs faster and requires no setup.

---

## Execution Order Summary

```
Step 1  conda activate eman2 + CUDA check           ~2 min    RHEL 10 workstation
Step 2  python make_project.py                      ~2 min    workstation
Step 3  grep + patch compatibility issues           ~1 min    workstation
Step 4  e2spt_pcasplit.py (nohup or foreground)     ~5-20 min workstation (CPU, single-threaded)
Step 5  python plot_pca.py + e2display.py           ~10 min   workstation (GUI)
Step 6  (if needed) re-run pcasplit, new params     ~20 min   workstation
Step 7  (optional) per-class e2spt_refine.py        ~1-4 hr   workstation (16 threads + RTX 5080)
```

---

## Known Issues and Caveats

1. **`np.int` deprecation** — `e2spt_pcasplit.py` line 162 uses `r = r.astype(np.int)` which is removed in NumPy ≥ 1.24. Apply the patch in Step 3 before running.

2. **`find_peaks_cwt` import** — `e2spt_pcasplit.py` line 43 imports `from scipy.signal import find_peaks_cwt` which was removed in newer SciPy versions. If this causes an import error, comment out that line — it is not called anywhere in the script.

3. **Missing wedge orientation** — Since particles were rotated post-extraction, the `--nowedgefill` flag is required. Without it, the amplitude-based wedge detection may zero out real signal or fail to zero the actual wedge.

4. **Print bug in pcasplit line 289** — `print("{}: {}".format(lb, ...))` should be `lb[i]` but this is just cosmetic; classification is unaffected.

5. **Pixel size in MRC headers** — The MRC files report 13.328 Å/px. Confirm this matches the actual acquisition parameters. If incorrect, update `APIX` in `make_project.py` before running Step 2.

6. **Gold-standard FSC** — Per-class averages from `e2spt_refine.py` include gold-standard FSC via even/odd splitting. With 300–400 particles per class at this pixel size, expect resolution estimates of 30–50 Å.

7. **HDF append behavior** — `e2proc3d.py` can also build the stack (`e2proc3d.py input.mrc output.hdf --append`), but the Python loop in `make_project.py` gives finer control over metadata per particle.
