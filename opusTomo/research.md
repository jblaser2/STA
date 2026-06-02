# Plan: Unsupervised Classification of Pre-Picked Subtomograms with OPUS-ET

_Date: 2026-06-02_

---

## Feasibility Assessment

**Yes, OPUS-ET is well-suited for this task.** Unsupervised heterogeneity analysis of subtomogram volumes is the tool's primary purpose. The dataset described — pre-picked, centered particles with the symmetry axis aligned to z — matches the exact input convention OPUS-ET expects.

Key compatibility points:
- The 3D CNN encoder takes raw subtomogram volumes and learns per-particle latent codes.
- Z-axis alignment is native: OPUS-ET handles in-plane rotation (`euler2`) separately via `rotate_2d`. Since particles are already z-aligned, tilt/rot Euler angles can be set to zero.
- K-means and GMM clustering of the learned latent codes provide the unsupervised classification output.
- Since particles are previously picked (volumes already extracted), no particle picking or subtomogram extraction step is needed.

**Important constraints for this dataset:**
- `templateres` must be N×16 where N ∈ {8,...,16}, making 128 the minimum valid value. The 80³ box experimental volumes are compared against a 128³ template that is internally cropped to match the render resolution.
- No CTF metadata is available — CTF modulation will be disabled.

---

## Workstation Specifications

| Resource | Value |
|---|---|
| GPU | 1× NVIDIA GeForce RTX 5080, 16 GB VRAM |
| CUDA driver | 13.2 |
| CPU cores | 24 |
| RAM | 62 GB |
| Disk (/home) | 874 GB total, ~805 GB free |
| Active conda env | `gen` (Python 3.13 — incompatible with OPUS-ET) |
| Other conda env | `eman2` |

**Note**: OPUS-ET's `environment.yml` pins PyTorch 1.11 + CUDA 11.3, which is incompatible with the RTX 5080 (Blackwell architecture). A new conda environment with PyTorch 2.6+ built for CUDA 12.8 (`cu128`) is required — CUDA 12.8 PyTorch wheels run correctly under the installed CUDA 13.2 driver.

---

## Dataset Summary

| Property | Value |
|---|---|
| Location | `~/src/particles/` |
| Number of particles | 672 |
| Number of source tomograms | 294 |
| Average particles per tomogram | ~2.3 |
| Box size | 80 × 80 × 80 voxels |
| Pixel size | 13.33 Å/voxel |
| Data type | float32 (MRC mode 2) |
| Filename convention | `aligned_tomNNN_PNNNN.mrc` |
| CTF metadata | None available |
| Pose metadata | None (particles are z-axis aligned; Euler angles set to zero) |

---

## Step 0: Create the OPUS-ET Conda Environment

PyTorch 2.6+ is required for RTX 5080 (Blackwell) support. Install from the `cu128` wheel index, which is forward-compatible with the installed CUDA 13.2 driver.

```bash
# Create a new environment with Python 3.10 (compatible with OPUS-ET dependencies)
conda create -n opuset python=3.10 -c conda-forge -y
conda activate opuset

# Install PyTorch 2.6+ with CUDA 12.8 wheels (runs on CUDA 13.2 driver)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# Verify GPU is accessible
python -c "import torch; print(torch.__version__); print(torch.cuda.get_device_name(0))"
# Expected: ... NVIDIA GeForce RTX 5080

# Install OPUS-ET dependencies (relax strict pins to avoid conflicts)
pip install mrcfile numpy scipy scikit-learn umap-learn healpy seaborn adjustText \
    monty starfile pyarrow astropy biopython tqdm typeguard

# Install OPUS-ET itself (editable install registers 'dsd' and 'dsdsh' CLIs)
cd ~/opusSrc/opusTomo
pip install -e .

# Confirm installation
dsd --help
```

> **If any dependency fails with Python 3.10**: the most likely culprits are `healpy` (requires numpy <2) and `umap-learn`. Install them with `--no-deps` and manage transitive deps manually.

---
*Feedback:* The installation instructions say to create the invironment using the provided `environment.yml` file. Why do you not recommend doing this? Will not using the yaml file create any problems?

*Response:* The `environment.yml` pins `pytorch=1.11.0=py3.9_cuda11.3_cudnn8.2.0_0` — a build that predates the RTX 5080 (Blackwell architecture) by several years. CUDA 11.3 PyTorch wheels have no compiled kernels for Blackwell's SM architecture (`sm_120`), so using that environment would cause PyTorch to fail to use the GPU entirely. It would either crash on import or silently fall back to CPU, making training impractically slow. This is why a new environment with PyTorch 2.6+ (`cu128` wheels) is necessary.

Not using the yml will not break the OPUS-ET code itself. The codebase uses only standard PyTorch operations (`grid_sample`, 3D convolutions, FFT) whose APIs are stable across PyTorch 1.11→2.x. The main risk from using newer package versions is subtle numerical differences in rarely-used paths, which are not a concern for this use case.
## Step 1: Create the RELION STAR File

No STAR file exists for this dataset. Generate one from the filename convention (`aligned_tomNNN_PNNNN.mrc`). Since particles are z-axis aligned with no known in-plane rotation, all Euler angles are set to zero.

```python
# ~/opusSrc/write_star.py
import glob, os

particle_dir = os.path.expanduser('~/src/particles')
out_star = os.path.expanduser('~/opusSrc/particles.star')
apix = 13.33

mrc_paths = sorted(glob.glob(os.path.join(particle_dir, 'aligned_tom*.mrc')))

lines = [
    'data_',
    'loop_',
    '_rlnImageName',
    '_rlnAngleRot',
    '_rlnAngleTilt',
    '_rlnAnglePsi',
    '_rlnOriginX',
    '_rlnOriginY',
    '_rlnOriginZ',
    '_rlnMicrographName',
]

for p in mrc_paths:
    # e.g. 'aligned_tom100_P0001.mrc' -> tomogram name 'aligned_tom100'
    basename = os.path.basename(p)                  # aligned_tom100_P0001.mrc
    tomo_name = '_'.join(basename.split('_')[:2])   # aligned_tom100
    lines.append(f'{p}\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t{tomo_name}')

with open(out_star, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f'Wrote {len(mrc_paths)} particles to {out_star}')
```

Run with:
```bash
conda activate opuset
python ~/opusSrc/write_star.py
```

---

## Step 2: Create the Pose Pickle

```bash
conda activate opuset
cd ~/opusSrc

# Box size is 80; pass 80 here (the internal lattice will be 81)
dsd parse_pose_star particles.star \
    -D 80 \
    --Apix 13.33 \
    -o pose_euler.pkl
```

---
*Feedback:* What is the pose pickle? Why do I need it?

*Response:* The pose pickle is a binary file (`.pkl`) that stores the 3D orientation (as a rotation matrix) and translation offset for each particle. OPUS-ET needs this because its training loop works by taking each particle's 3D template, rotating and translating it into the particle's known orientation, projecting it along z, and comparing that projection to the experimental subtomogram slice. Without knowing each particle's orientation, it cannot make that comparison.

In a normal cryo-ET workflow these orientations come from prior subtomogram alignment (e.g. template matching or STA refinement). In our case, since the particles are already z-axis aligned with no known in-plane rotation, all orientations are identity (zero Euler angles). The `parse_pose_star` command simply reads those zero angles from the STAR file and converts them into the 3×3 rotation matrix format that PyTorch uses internally during training. Think of it as translating "zero rotation" from human-readable degrees into the matrix math the model expects.
## Step 3: Create a Solvent Mask

### Option A: Average all subtomograms then threshold (recommended)

```python
# ~/opusSrc/make_mask.py
import glob, os
import numpy as np
import mrcfile

particle_dir = os.path.expanduser('~/src/particles')
files = sorted(glob.glob(os.path.join(particle_dir, 'aligned_tom*.mrc')))

print(f'Averaging {len(files)} volumes ...')
acc = None
for f in files:
    with mrcfile.open(f, permissive=True) as m:
        v = m.data.astype(np.float32)
    acc = v if acc is None else acc + v
avg = acc / len(files)

# Write consensus average
with mrcfile.new(os.path.expanduser('~/opusSrc/consensus.mrc'), overwrite=True) as m:
    m.set_data(avg)
    m.voxel_size = 13.33

# Threshold at 1 sigma above mean to create mask, then dilate 2 voxels
from scipy.ndimage import binary_dilation
thresh = avg.mean() + avg.std()
mask = (avg > thresh).astype(np.float32)
mask = binary_dilation(mask, iterations=2).astype(np.float32)

with mrcfile.new(os.path.expanduser('~/opusSrc/mask.mrc'), overwrite=True) as m:
    m.set_data(mask)
    m.voxel_size = 13.33

print(f'Mask covers {mask.sum():.0f} / {mask.size} voxels ({100*mask.mean():.1f}%)')
```

```bash
python ~/opusSrc/make_mask.py
```

### Option B: Spherical mask (quick start if averaging is slow)

```python
# ~/opusSrc/make_sphere_mask.py
import numpy as np, mrcfile, os

D, apix = 80, 13.33
radius = 35   # voxels — adjust to your particle; 35 covers ~467 Å radius

c = D // 2
zz, yy, xx = np.ogrid[:D, :D, :D]
mask = ((zz-c)**2 + (yy-c)**2 + (xx-c)**2 <= radius**2).astype(np.float32)

with mrcfile.new(os.path.expanduser('~/opusSrc/mask.mrc'), overwrite=True) as m:
    m.set_data(mask)
    m.voxel_size = apix
print(f'Sphere mask: radius={radius} px ({radius*apix:.0f} Å)')
```
*Feedback:* I know my partical are pili, could I use a cylindrical mask instead? Is OpusTomo set up for that? Or is averaging all subtomograms still better?

*Response:* A cylindrical mask is absolutely appropriate for pili and OPUS-ET supports it — the mask is just a binary MRC volume (1 inside, 0 outside) and the code doesn't care about its shape. However, **averaging all subtomograms first is still the better approach**, because the threshold of that average will naturally produce a cylindrical mask shaped to your actual data (correct diameter, length, and centering). A hand-drawn cylinder risks getting the radius or length wrong and either masking out real density or including too much solvent noise.

If the averaged mask looks too noisy to threshold cleanly, use the averaging script to generate `consensus.mrc`, inspect it in ChimeraX, then replace the thresholding block with an explicit cylinder:

```python
# Drop-in replacement for the thresholding block in make_mask.py
from scipy.ndimage import binary_dilation

D, apix = 80, 13.33
radius_xy = 12   # voxels — ~160 Å; adjust to pilus diameter in ChimeraX
length_z  = 70   # voxels — adjust to pilus length visible in the average

c = D // 2
zz, yy, xx = np.mgrid[:D, :D, :D]
mask = (
    ((yy - c)**2 + (xx - c)**2 <= radius_xy**2) &
    (np.abs(zz - c) <= length_z // 2)
).astype(np.float32)
mask = binary_dilation(mask, iterations=1).astype(np.float32)
```

Start with Option A (averaging + threshold) and only fall back to the explicit cylinder if the averaged mask is fragmented or too noisy.

---

## Step 4: Training

Single-GPU training on the RTX 5080. The dataset is small (672 particles), so training will be fast — expect 10–30 minutes for 20 epochs.

```bash
conda activate opuset
cd ~/opusSrc

dsd train_tomo particles.star \
    --poses pose_euler.pkl \
    -n 20 \
    -b 16 \
    --zdim 8 \
    --zaffinedim 0 \
    --lr 1e-4 \
    --beta-control 1.0 \
    --lamb 0 \
    -o output_dir \
    -r mask.mrc \
    --downfrac 1.0 \
    --templateres 128 \
    --angpix 13.33 \
    --datadir ~/src/particles \
    --ctfalpha 0. --ctfbeta 0.
```

### Parameter rationale for this dataset

| Parameter | Value | Rationale |
|---|---|---|
| `-b 16` | 16 | 80³ volumes are small; 16 GB VRAM on RTX 5080 easily handles this |
| `--zdim 8` | 8 | Start here for 672 particles; drop to 4 if classes blend, raise to 16 if too coarse |
| `--zaffinedim 0` | 0 | Classification only — no conformational (deformation) analysis needed |
| `--downfrac 1.0` | 1.0 | Box is already small (80 px); keep full resolution (render_size = 80) |
| `--templateres 128` | 128 | Minimum valid value (N×16, N≥8); template is cropped internally to render_size=80 |
| `--angpix 13.33` | 13.33 | Matches MRC voxel size header |
| `--ctfalpha 0. --ctfbeta 0.` | 0, 0 | No CTF metadata available; disables CTF modulation entirely |
| `--lamb 0` | 0 | With ~2.3 particles per tomogram, tomogram-based disentanglement has little signal |
| `-n 20` | 20 | Monitor loss; 672 particles at batch 16 = 42 steps/epoch, so 20 epochs is ~840 steps |

> **No `--multigpu`**: only one GPU is available. Do not add `--multigpu` or `--num-gpus`.

### Monitor training loss

```bash
# In a separate terminal while training runs
python ~/opusSrc/opusTomo/analysis_scripts/plot_loss.py ~/opusSrc/output_dir/run.log
```

Stop training early if the reconstruction loss plateaus before epoch 20.

### Resume training if interrupted

```bash
dsd train_tomo particles.star \
    --poses pose_euler.pkl \
    ... [same args] ... \
    --load output_dir/weights.19.pkl \
    --latents output_dir/z.19.pkl
```

---

## Step 5: Latent Space Analysis and Clustering

```bash
conda activate opuset
cd ~/opusSrc

EPOCH=19   # or whichever epoch had the lowest reconstruction loss
K=8        # number of classes; with 672 particles, 5–10 is reasonable
NUMPC=2

dsdsh analyze output_dir $EPOCH $NUMPC $K
# Omit --skip-umap to get the UMAP embedding (adds ~2 min for 672 particles — worth it)
```

Output in `output_dir/analyze.$EPOCH/`:
- `z_pca.png` — PCA of latent codes, colored by cluster
- `umap.png` — UMAP 2D embedding colored by k-means cluster
- `kmeans$K/labels.pkl` — integer array (672,) of cluster assignments
- `kmeans$K/centers.txt` — latent codes at cluster centers
- `kmeans$K/centers_ind.txt` — indices of particles closest to each center

---

## Step 6: Generate 3D Volumes per Class

```bash
APIX=13.33

dsdsh eval_vol output_dir $EPOCH kmeans $K $APIX
```

Produces `output_dir/analyze.$EPOCH/kmeans$K/vol_k0XX.mrc` for each class. Open in ChimeraX or UCSF Chimera to compare structures.

---

## Step 7: Split Particles by Class

```bash
# Read the correct D from config (should be 80, i.e., lattice D=81, effective D=80)
dsd view_config output_dir/config.pkl | grep "'D'"
# If lattice_args['D'] == 81, use -D 80 below

dsd parse_pose_star particles.star \
    -D 80 \
    --Apix 13.33 \
    --labels output_dir/analyze.$EPOCH/kmeans$K/labels.pkl \
    --outdir output_dir/split_star/
```

Produces `pre0.star` … `pre{K-1}.star` — one STAR file per class. Each can be used for further refinement, re-extraction, or re-training with `--encode-mode fixed` for a higher-resolution reconstruction of a single class.

---

## Step 8: Evaluate and Iterate

### Interpreting results

| Observation | Likely cause | Fix |
|---|---|---|
| All volumes look identical | `zdim` too small, or `beta-control` too high | Reduce `--beta-control` to 0.5, or increase `--zdim` to 16 |
| Volumes look like noise | `zdim` too large, or underfitting | Reduce `--zdim` to 4 or train more epochs |
| Classes split by tomogram rather than structure | Tomogram-level batch effects | Add `--lamb 1.0` |
| One class contains most particles | Heterogeneity is low, or KL collapse | Reduce `--beta-control` to 0.1 |
| Loss diverges | Learning rate too high | Reduce `--lr` to 5e-5 |

### Refining K (number of classes)

Try K=5, 8, 12 and compare cluster volume quality. With 672 particles, avoid K > 15 (too few particles per class for stable volumes).

### Interactive filtering notebook

```bash
conda activate opuset
jupyter notebook ~/opusSrc/opusTomo/cryodrgn/templates/cryoDRGN_filtering_template.ipynb
```

Set `workdir = '~/opusSrc/output_dir'` and `epoch = 19` in the first cell. Use the polygon lasso tool on the UMAP/PCA scatter to select subpopulations or exclude outliers manually.

---

## Summary Workflow

```
~/src/particles/aligned_tom*.mrc   (672 files, 80³, 13.33 Å/px)
        |
        v
[conda activate opuset]
[python write_star.py]        ->  particles.star
[dsd parse_pose_star]         ->  pose_euler.pkl
[python make_mask.py]         ->  mask.mrc
        |
        v
[dsd train_tomo ...]
  -b 16, --zdim 8, --zaffinedim 0
  --templateres 128, --downfrac 1.0
  --angpix 13.33, --ctfalpha 0 --ctfbeta 0
        |
        v  (output_dir/weights.N.pkl + z.N.pkl)
        |
[dsdsh analyze output_dir 19 2 8]
  -> labels.pkl, centers.txt, UMAP/PCA plots
        |
[dsdsh eval_vol output_dir 19 kmeans 8 13.33]
  -> vol_k000.mrc ... vol_k007.mrc
        |
[dsd parse_pose_star --labels labels.pkl]
  -> pre0.star ... pre7.star
```

---

## Known Gotchas (this dataset)

1. **D vs D-1**: `parse_pose_star -D 80` is correct at the preparation stage. After training, verify with `dsd view_config output_dir/config.pkl` — if `lattice_args['D']` is 81, use `-D 80` in the post-training split step.
2. **`templateres` minimum is 128**: The box is 80 voxels, but templateres must be N×16 with N≥8. Use `--templateres 128`; the template is internally cropped to the 80-voxel render size.
3. **No CTF**: `--ctfalpha 0. --ctfbeta 0.` disables CTF entirely. If these flags are omitted and no CTF `.pkl` is provided, training will crash at the first batch.
4. **`refine_pose=False` is broken**: Do not set this flag. The default internal path (`refine_pose=True`) is the only working branch.
5. **Single GPU only**: Do not use `--multigpu` or `--num-gpus`. There is one RTX 5080 on this machine.
6. **In-plane rotation**: All Euler angles are set to zero, which assumes no in-plane rotational variation. If particles have a preferred in-plane orientation (e.g., from template matching with a non-symmetric template), performance may improve by supplying the known psi angles instead of zeros.
