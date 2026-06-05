# PyTom T4P Classification: Workflow Instructions

## Dataset Summary

| Property | Value |
|---|---|
| Particles | 672 pre-aligned subtomograms |
| File pattern | `aligned_tom{N}_P{NNNN}.mrc` |
| Box size | 80 × 80 × 80 voxels |
| Voxel size | 13.328 Å |
| Alignment | Pre-applied — volumes are already centered and oriented |
| Pilus axis | Y direction (long axis) |

---

## MPI Runtime Requirements

PyTom classification requires **OpenMPI** (`mpirun`). All classification and
correlation commands must be launched with `mpirun`:

```bash
mpirun -np N python script.py [args]
```

| Method | Min processes | Recommended |
|---|---|---|
| `auto_focus_classify` | 2 | 8–32 |
| `calculate_correlation_matrix` (CPU) | 2 | 8–32 |
| `calculate_correlation_matrix` (GPU) | num_GPUs + 1 | — |

**Minimum:** `mpirun -np 2` (1 master + 1 worker). The master (rank 0) orchestrates;
all other ranks are workers. More workers = proportionally faster.

Check MPI is available:
```bash
mpirun --version
which mpirun
```

---

## Paths

```bash
SUBTOMOS=/home/jblaser2/Research/STA/subtomos_mrc
PYTOM=/home/jblaser2/Research/pytom
SCRIPTS=/home/jblaser2/Research/STA/PyTom
OUTDIR=/home/jblaser2/Research/STA/PyTom/autofocus_output
```

---

## Step 1: Generate the Particle List XML

PyTom requires an XML file describing each subtomogram. Since the particles are
already aligned, rotations and shifts are set to zero.

```bash
python $SCRIPTS/generate_particle_list.py \
    --input_dir  $SUBTOMOS \
    --output     $SCRIPTS/particle_list.xml \
    --wedge_angle 30
```

**`--wedge_angle`** is the *missing* wedge half-angle in degrees.
`30` assumes a ±60° tilt range (the most common cryo-ET collection range).
If your data used a different tilt range, adjust with:
`missing_wedge_angle = 90 - max_tilt_angle_degrees`

Verify the output (should show 672 `<Particle>` entries):
```bash
grep -c "<Particle" $SCRIPTS/particle_list.xml
```

---

## Step 2: Generate the Cylindrical Mask

The **v2 mask** (tuned to the T4P lower periplasmic ring, matching PEET v2) is the
current canonical mask and is already on disk. To regenerate it:

```bash
cd $SCRIPTS
python generate_cylindrical_mask.py --radius 13 --height_pos 0 --height_neg 25 --box 80
```

| Parameter | Value | Physical size | Notes |
|---|---|---|---|
| Box | 80 voxels | — | |
| Radius (XZ) | 13 voxels | 173 Å | Captures lower periplasmic ring |
| Height +Y | 0 voxels | 0 Å | Flat at center — no upward extent |
| Height -Y | 25 voxels | 333 Å | Below-center only (ring region) |

This geometry matches PEET v2 (which gave the best AIC/BIC on T4P). The mask was
generated from `T4P_mask/generate_cylindrical_mask.py` and copied to `PyTom/`.
`T4P_mask/cylindrical_mask_v2.mrc` holds the same mask for RELION use.

Previous default params (r=7.2, symmetric ±8.8 vox) failed to separate T4P phases.

---

## Step 3: Run Auto-Focus Classification

Auto-focus is the recommended method for T4P pili. It computes structural
*difference maps* between class pairs to focus scoring on the most
discriminative voxels — ideal when conformational differences are localized.

```bash
mkdir -p $OUTDIR

mpirun -np 16 python $PYTOM/pytom/classification/auto_focus_classify.py \
    -p  $SCRIPTS/particle_list.xml \
    -k  3 \
    -f  20 \
    -m  $SCRIPTS/cylindrical_mask.em \
    -c  $SCRIPTS/cylindrical_mask.em \
    -b  1 \
    -i  15 \
    -a  \
    -o  $OUTDIR
```

> **Note — `-a` is required on this machine:** The compiled FRM extension
> (`_swig_frm`) is absent from `pytom_env`, so running without `-a` causes an
> MPI_ABORT on all workers at the alignment step. Our particles are pre-aligned
> (zero rotations/shifts in the particle list), so `-a` is scientifically correct
> here: difference-map scoring uses the stored orientations rather than
> re-running FRM.

### Key Parameters

| Flag | Meaning | Recommended starting value |
|---|---|---|
| `-p` | Particle list XML | `particle_list.xml` |
| `-k` | Number of classes | 3 (try 2–6) |
| `-f` | Max frequency in pixels for scoring | 10 (coarse) → 20 (finer) |
| `-m` | Alignment mask (EM/MRC volume) | `cylindrical_mask.em` |
| `-c` | Focus mask for difference maps | `cylindrical_mask.em` |
| `-b` | Binning factor | 1 (no extra binning) |
| `-i` | Number of iterations | 10–20 |
| `-o` | Output directory | `./autofocus_output/` |
| `-n` | Noise fraction (0–1) | 0.1 (flag 10% lowest-scoring as noise) |
| `-d` | Dispersion: remove classes smaller than max/d | 5 |
| `-a` | Skip FRM alignment (use stored orientations only) | **required** — see note above |

### Frequency (`-f`) Guide

With an 80-voxel box at 13.328 Å/voxel (Nyquist = 40 pixels):

| `-f` value | Nyquist fraction | Real-space resolution |
|---|---|---|
| 10 | 25% | ~53 Å (good starting point) |
| 20 | 50% | ~27 Å (refined run) |
| 30 | 75% | ~18 Å (aggressive) |

Start with `f=10` for initial class discovery, then rerun with `f=20` for refinement.

### Output Files

| File pattern | Description |
|---|---|
| `classified_pl_iter{N}.xml` | Particle list with class assignments at iteration N |
| `iter{N}_class{K}.em` | Class K average volume at iteration N |
| `iter{N}_class{K}_wedge.em` | Wedge sum for class K at iteration N |
| `iter{N}_dmap_{A}_{B}.em` | Difference map between classes A and B at iteration N |
| `initial_{K}.em` | Initial k-means++ seed reference for class K |

---

## Step 4: Visualize Results

```bash
python $SCRIPTS/visualize_classification.py \
    --output_dir $OUTDIR \
    --save_dir   $SCRIPTS/figures
```

This produces:
- `figures/clustering_map.png` — class size bar chart
- `figures/class_0_central_slice.png`, `class_1_central_slice.png`, ... — orthogonal
  slices of each final class average (XZ transverse view + XY side view)

---

## Step 5: Push Results to GitHub

```bash
cd /home/jblaser2/Research/STA
git add PyTom/
git commit -m "Add T4P classification results"
git push origin main
```

---

## Iterative Refinement Strategy

1. **First pass:** `-k 3 -f 10 -i 10` — fast, discover major classes
2. **Second pass:** Inspect `clustering_map.png`; increase `-k` if all classes
   look similar, decrease if one class dominates
3. **Third pass:** `-k <best_k> -f 20 -i 15 -n 0.1 -d 5` — full resolution,
   noise removal, dispersion pruning
4. **Compare class averages:** Look for structural differences in XZ cross-section
   slices (pilus end-on view)

---

## Troubleshooting

**Import error for PyTom:**
```bash
python generate_particle_list.py --pytom_dir /home/jblaser2/Research/pytom ...
```

**MPI not found:**
```bash
module load openmpi   # on HPC clusters
# or
conda activate pytom_env
```

**Too few MPI processes error (`mpi.size < 2`):**
Always use at least `mpirun -np 2`.

**Class collapse (all particles in one class):**
- Lower the frequency (`-f 10`)
- Increase number of iterations (`-i 20`)
- Try a different number of classes (`-k`)

**Very slow CCC matrix step (CPCA alternative):**
Use GPU acceleration:
```bash
mpirun -np 3 python $PYTOM/pytom/classification/calculate_correlation_matrix.py \
    -p particle_list.xml -m cylindrical_mask.em -f 20 -b 1 \
    -o ./cpca_output/ --gpuID 0,1
```
(requires `mpirun -np num_GPUs+1`)

---

## Script Reference

| Script | Purpose |
|---|---|
| `generate_particle_list.py` | Create PyTom XML from MRC directory |
| `generate_cylindrical_mask.py` | Create cylindrical mask (.em + .mrc) |
| `visualize_classification.py` | Plot clustering map + class central slices |
| `instructions.md` | This file |
