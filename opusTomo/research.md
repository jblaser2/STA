# OPUS-ET Pili Subtomogram Classification — Research Notes

_Last updated: 2026-06-02_  
_Status: Pipeline completed successfully (20 epochs, K=8 clusters)_

---

## Overview

This document describes an end-to-end unsupervised classification of 672 pili subtomograms using OPUS-ET (opusTomo), a beta-VAE framework for cryo-ET heterogeneity analysis. It is written to be self-contained: a lab member should be able to replicate the full pipeline from raw MRC files to per-class STAR files and 3D density maps.

---

## What OPUS-ET Does

OPUS-ET trains a **HetOnlyVAE** — a 3D CNN encoder that maps each subtomogram to an 8-dimensional latent code, and a ConvTemplate decoder that reconstructs a 3D density from that code. After training, k-means clustering on the latent codes partitions particles into structural classes, and the decoder generates one 3D volume per class center.

Architecture (61M parameters):
- **Encoder**: 3D conv stack → 512-d FC → μ and log σ (zdim=8)
- **Decoder**: FC → ConvTranspose3d stack → 128³ template → SpatialTransformer → z-projection → CTF → MSE loss
- **Loss**: reconstruction MSE + KL divergence (beta-VAE) + optional contrastive term (`c_mmd`, disabled here with `--lamb 0`)

---

## Hardware and Software

| Resource | Value |
|---|---|
| GPU | 1× NVIDIA GeForce RTX 5080, 16 GB VRAM |
| CUDA driver | 13.2 |
| CPU cores | 24 |
| RAM | 62 GB |
| OS | RHEL 10.1 x86_64 |
| Conda env | `opuset` (Python 3.10) |
| PyTorch | 2.11.0+cu128 |

**Why not use the bundled `environment.yml`**: It pins PyTorch 1.11 + CUDA 11.3, which has no compiled kernels for the RTX 5080 (Blackwell SM_120 architecture). A cu128 wheel is required.

---

## Dataset

| Property | Value |
|---|---|
| Location | `~/src/particles/` |
| Particles | 672 |
| Source tomograms | 294 (~2.3 particles/tomogram) |
| Box size | 80 × 80 × 80 voxels |
| Pixel size | 13.33 Å/voxel |
| Data type | float32 (MRC mode 2) |
| Filename convention | `aligned_tomNNN_PNNNN.mrc` |
| CTF metadata | None |
| Pose metadata | None — particles are z-axis aligned; Euler angles set to zero |

---

## Environment Setup

```bash
conda create -n opuset python=3.10 -c conda-forge -y
conda activate opuset

# PyTorch cu128 — forward-compatible with CUDA 13.2 driver
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# Verify GPU
python -c "import torch; print(torch.__version__, torch.cuda.get_device_name(0))"
# Expected: 2.11.0+cu128  NVIDIA GeForce RTX 5080

# OPUS-ET dependencies (setup.py has install_requires commented out — install manually)
pip install mrcfile numpy scipy scikit-learn umap-learn healpy seaborn adjustText \
    monty starfile pyarrow astropy biopython tqdm typeguard

# Editable install registers 'dsd' and 'dsdsh' CLIs
cd ~/opusSrc/opusTomo
pip install -e .
dsd --help
```

---

## Pipeline

All scripts live in `~/opusSrc/opus_project/`. The master orchestrator is `~/opusSrc/runClassification.sh`.

### Run everything end-to-end

```bash
cd ~/opusSrc
conda activate opuset
bash runClassification.sh 2>&1 | tee opus_project/logs/pipeline_$(date +%Y%m%d_%H%M%S).log
```

The script skips steps whose outputs already exist, so it is safe to re-run after interruption. Options:

```bash
bash runClassification.sh --k 10         # use 10 clusters
bash runClassification.sh --epoch 14     # analyse a specific epoch
bash runClassification.sh --skip-train   # skip training, re-run analysis only
```

---

### Step 0: Dummy CTF File (CRITICAL — required even with no CTF)

`dataset.load_subtomos()` unconditionally calls `star.get_3dctfs()`, which requires `_rlnCtfImage` in the STAR file **regardless of `--ctfalpha`/`--ctfbeta`**. Training crashes at startup with `RuntimeError: '_rlnCtfImage'` if this column is absent.

**Workaround**: create a single shared placeholder CTF file in the particle directory:

```
# ~/src/particles/dummy_ctf.star
data_images

loop_
_rlnAngleTilt
_rlnDefocusU
_rlnVoltage
_rlnSphericalAberration
_rlnAmplitudeContrast
_rlnCtfBfactor
_rlnCtfScalefactor
0.0	20000.0	300.0	2.7	0.07	0.0	1.0
```

Key details:
- `get_3dctfs()` takes `_rlnCtfImage = dummy_ctf.mrc`, changes extension `.mrc`→`.star`, and reads CTF parameters from the resulting `dummy_ctf.star`.
- Path resolution: `prefix_paths()` tries `datadir/basename(path)` first — so the file must live in `~/src/particles/dummy_ctf.star` and the STAR column must be the bare filename `dummy_ctf.mrc` (no directory prefix).
- With `--ctfalpha 0 --ctfbeta 0`, the loaded CTF values are **never applied**; the file is read but ignored. Placeholder values are fine.

---

### Step 1: STAR File (`opus_project/01_write_star.py`)

Creates `opus_project/particles.star` with all required columns including `_rlnCtfImage`.

```python
PARTICLE_DIR = os.path.expanduser('~/src/particles')
# columns: _rlnImageName _rlnCtfImage _rlnAngleRot _rlnAngleTilt _rlnAnglePsi
#          _rlnOriginX _rlnOriginY _rlnOriginZ _rlnMicrographName
# All angles and offsets are zero. _rlnCtfImage = 'dummy_ctf.mrc' for all particles.
```

Run: `python opus_project/01_write_star.py`

---

### Step 2: Pose Pickle (`opus_project/02_make_pose.sh`)

```bash
dsd parse_pose_star opus_project/particles.star -D 80 --Apix 13.33 -o opus_project/pose_euler.pkl
```

Converts zero Euler angles to 3×3 identity rotation matrices stored in a pickle. The `-D 80` argument sets the effective box size; internally the lattice is D+1=81.

---

### Step 3: Consensus Map + Mask (`opus_project/03_make_mask.py`)

Averages all 672 subtomograms → `opus_project/consensus.mrc`, then thresholds at mean+1σ with 2-voxel binary dilation → `opus_project/mask.mrc`.

Cylindrical masks are appropriate for pili and work fine. If the averaged mask looks fragmented, inspect `consensus.mrc` in ChimeraX and use an explicit cylinder:

```python
radius_xy = 12   # voxels (~160 Å)
length_z  = 70   # voxels
c = D // 2
zz, yy, xx = np.mgrid[:D, :D, :D]
mask = (((yy-c)**2 + (xx-c)**2 <= radius_xy**2) & (np.abs(zz-c) <= length_z//2)).astype(np.float32)
```

---

### Step 4: Training (`opus_project/04_train.sh`)

```bash
dsd train_tomo opus_project/particles.star \
    --poses opus_project/pose_euler.pkl \
    -n 20 -b 16 --zdim 8 --zaffinedim 0 \
    --lr 1e-4 --beta-control 1.0 --lamb 0 \
    -o opus_project/output \
    -r opus_project/mask.mrc \
    --downfrac 1.0 --templateres 128 --angpix 13.33 \
    --datadir ~/src/particles \
    --ctfalpha 0. --ctfbeta 0. \
    --split opus_project/output/split.pkl
```

**`--split` is required**: without it, `args.split` is `None` and `os.path.exists(None)` crashes at `train_tomo.py:898`.

#### Parameter rationale

| Parameter | Value | Rationale |
|---|---|---|
| `-b 16` | 16 | 80³ is small; 16 GB VRAM handles this easily |
| `--zdim 8` | 8 | Good starting point for 672 particles |
| `--zaffinedim 0` | 0 | Classification only, no conformational deformation |
| `--downfrac 1.0` | 1.0 | Keep full resolution (render_size = 80) |
| `--templateres 128` | 128 | Minimum valid value (N×16, N≥8); cropped internally to 80 |
| `--angpix 13.33` | 13.33 | Matches MRC header |
| `--ctfalpha 0 --ctfbeta 0` | 0, 0 | No CTF metadata; disables CTF modulation |
| `--lamb 0` | 0 | ~2.3 particles/tomogram — contrastive loss has little signal |

#### Actual training results (epoch 0–19)

- Train split: 537 particles / 33 batches per epoch
- Val split: 135 particles / 8 batches per epoch
- Epoch 1 avg train gen_loss: −0.980, SNR²: 1.17
- Epoch 2 avg train gen_loss: −1.230, SNR²: 1.64
- Loss steadily decreasing through epoch 20 — no divergence, no NaN

#### Resume training if interrupted

```bash
dsd train_tomo ... --load opus_project/output/weights.19.pkl --latents opus_project/z.19.pkl
```

---

### Step 5: Latent Analysis + Clustering (`opus_project/05_analyze.sh`)

```bash
dsdsh analyze opus_project/output 19 2 8
```

Outputs in `opus_project/output/analyze.19/`:
- `z_pca.png`, `z_pca_hex.png` — PCA of latent codes
- `umap.png`, `umap_hex.png` — UMAP embedding
- `kmeans8/labels.pkl` — integer array (672,) of cluster IDs
- `kmeans8/centers.txt` — latent vectors at cluster centers
- `kmeans8/centers_ind.txt` — particle indices closest to each center

**Known non-fatal warning**: `analyze_zN` runs a second PCA on the affine-z component (shape=(672,0) since `--zaffinedim 0`), producing `ValueError: Found array with 0 feature(s)`. This does not affect the main z-latent PCA, UMAP, or k-means — they all complete successfully.

---

### Step 6: Generate Class Volumes (`opus_project/06_eval_vol.sh`)

```bash
dsdsh eval_vol opus_project/output 19 kmeans 8 13.33
```

Produces `reference0.mrc` – `reference7.mrc` in `opus_project/output/analyze.19/kmeans8/`.

**Note**: volumes are named `reference*.mrc`, NOT `vol_k0XX.mrc` as the OPUS-ET docs suggest. Any skip-condition checks must use this naming.

---

### Step 7: Split STAR by Class (`opus_project/07_split_star.sh`)

```bash
dsd parse_pose_star opus_project/particles.star \
    -D 80 --Apix 13.33 \
    --labels opus_project/output/analyze.19/kmeans8/labels.pkl \
    --outdir opus_project/split_star/
```

Produces `pre0.star` – `pre7.star` in `opus_project/split_star/`.

---

## Actual Results (K=8, Epoch 19)

| Class | Particles | Fraction |
|---|---|---|
| 0 | 44 | 6.5% |
| 1 | 85 | 12.6% |
| 2 | 67 | 10.0% |
| 3 | 120 | 17.9% |
| 4 | 126 | 18.8% |
| 5 | **6** | **0.9%** |
| 6 | 146 | 21.7% |
| 7 | 78 | 11.6% |

Class 5 (6 particles) is very small and may represent outliers.

3D density maps: `opus_project/output/analyze.19/kmeans8/reference{0..7}.mrc`
Split STAR files: `opus_project/split_star/pre{0..7}.star`

---

## OPUS-ET Source Code Bugs and Fixes

Four bugs were found in `opusTomo/cryodrgn/` that are triggered by the all-zero-pose, no-CTF use case. All fixes are minimal and targeted.

### Bug 1: `_rlnCtfImage` unconditionally required

**File**: `cryodrgn/dataset.py` → `load_subtomos()` → `star.get_3dctfs()`  
**Symptom**: `RuntimeError: '_rlnCtfImage'` at startup, even with `--ctfalpha 0 --ctfbeta 0`  
**Fix**: Create `dummy_ctf.star` in the particle datadir and add `_rlnCtfImage = dummy_ctf.mrc` to every particle row in the STAR file (see Step 0 above). Do NOT modify the source — the dummy workaround is cleaner and survives updates.

### Bug 2: `args.split = None` crash

**File**: `cryodrgn/commands/train_tomo.py`, line 898  
**Symptom**: `TypeError: stat: path should be string, bytes, os.PathLike or integer, not NoneType`  
**Cause**: `args.split` defaults to `None`; `os.path.exists(args.split)` is called unconditionally  
**Fix**: Always pass `--split <path>` explicitly (e.g. `--split opus_project/output/split.pkl`)

### Bug 3: HEALPix single-bin crash in contrastive loss

**File**: `cryodrgn/pose.py`, functions `sample_full_neighbors()` and `sample_neighbors()`  
**Symptom**: `ValueError: need at least one array to concatenate` at `pose.py:180`  
**Cause**: All 672 particles have identical zero poses → all land in HEALPix bin 3 (of 48). `sample_full_neighbors` removes the current bin from `pose_sample`, leaving an empty list. `np.concatenate([])` fails.  
**Fix applied to both functions**:
```python
# Before:
pose_sample = list(self.valid_poses)
pose_sample.remove(cur_idx)           # crashes if cur_idx not in list
num_pose = min(len(pose_sample), num_pose)

# After:
pose_sample = list(self.valid_poses)
if cur_idx in pose_sample:
    pose_sample.remove(cur_idx)
# When all particles share one bin, sample within it (lamb=0 zeroes out c_mmd anyway)
if len(pose_sample) == 0:
    pose_sample = list(self.valid_poses)
num_pose = min(len(pose_sample), num_pose)
```
Safe because `--lamb 0` multiplies `c_mmd` by zero — the fallback sampling has no effect on training.

### Bug 4: NaN in loss from CTF exponent

**File**: `cryodrgn/models.py`, line ~1720  
**Symptom**: `AssertionError: assert torch.isnan(gen_loss).item() is False` at `train_tomo.py:434`  
**Cause**: `ctf_beta_rand = (np.random.randn()/4.) * 0.01` (std≈0.0025) is added to `ctf_beta=0.0`. When `ctf_beta_rand < 0`, the exponent `ctf_beta + ctf_beta_rand < 0`. Then `|c|^{negative}` = `1/|c|^{positive}` → `Inf` at CTF zeros (|c|=0) → NaN in loss.  
**Fix**:
```python
# Before:
image_fft = image_fft * c[i:i+1].abs().pow(self.ctf_beta + ctf_beta_rand)

# After:
image_fft = image_fft * c[i:i+1].abs().pow(max(self.ctf_beta + ctf_beta_rand, 0.0))
```
`0^0 = 1`, so clamping to ≥0 means CTF zeros become identity at those frequencies, which is correct behaviour with no CTF.

---

## Complete Gotcha List

1. **`_rlnCtfImage` is always required** — `get_3dctfs()` is called unconditionally. `--ctfalpha 0 --ctfbeta 0` does NOT bypass the load. Always provide a dummy CTF file.

2. **`_rlnCtfImage` is a per-particle CTF STAR, not an MRC** — `get_3dctfs()` changes the `.mrc` extension to `.star` and reads a `data_images` block. Required columns: `_rlnAngleTilt`, `_rlnDefocusU`, `_rlnVoltage`, `_rlnSphericalAberration`, `_rlnAmplitudeContrast`, `_rlnCtfBfactor`, `_rlnCtfScalefactor`.

3. **`prefix_paths` resolution**: tries `datadir/basename(path)` first. Use a bare filename (no directory) in `_rlnCtfImage` so it reliably resolves to `datadir/filename.star`.

4. **`--split` must always be provided** — `args.split = None` by default causes a crash at `train_tomo.py:898`.

5. **`templateres` minimum is 128** — must be N×16 with N∈{8..16}. Box size 80 still requires `--templateres 128`; the template is cropped internally to the 80-voxel render size.

6. **Volume output names are `reference*.mrc`** — not `vol_k0XX.mrc` as implied by some docs. Any file-existence checks or glob patterns must use `reference*.mrc`.

7. **`analyze` raises non-fatal PCA error with `--zaffinedim 0`** — the `analyze_zN` call tries to run PCA on a (N,0) array. The traceback appears in the log but analysis completes successfully.

8. **D vs D-1**: `parse_pose_star -D 80` and the split step use `-D 80`. After training, `config.pkl` shows `lattice_args['D'] == 81` (D+1 convention). This is expected.

9. **`refine_pose=False` is broken** — do not set this flag. The default (True) is the only working path.

10. **Single GPU only** — one RTX 5080. Do not pass `--multigpu` or `--num-gpus`.

11. **All poses are zero** — no in-plane rotation variation is assumed. If particles have known psi angles from template matching, supply them for better results.

12. **PyTorch 2.6+ required** — the bundled `environment.yml` pins PyTorch 1.11+CUDA 11.3, which has no Blackwell (SM_120) kernels. Install cu128 wheels.

---

## Troubleshooting Training

| Symptom | Likely cause | Fix |
|---|---|---|
| `RuntimeError: '_rlnCtfImage'` | Missing CTF column | Add dummy CTF (Step 0) |
| `TypeError: stat: ... NoneType` | `args.split` is None | Add `--split <path>` |
| `ValueError: need at least one array` | Single HEALPix bin | Applied fix in `pose.py` |
| `AssertionError: NaN in gen_loss` | Negative CTF exponent | Applied fix in `models.py` |
| All class volumes identical | KL collapse or zdim too small | Reduce `--beta-control` to 0.5 or increase `--zdim` |
| Volumes look like noise | Underfitting | Reduce `--zdim` or train more epochs |
| Classes correlate with tomogram | Batch effects | Enable `--lamb 1.0` |
| Loss diverges | LR too high | Reduce `--lr` to 5e-5 |

---

## File Map

```
~/opusSrc/
├── runClassification.sh          # master orchestrator (run this)
├── opusTomo/                     # OPUS-ET source (pip install -e .)
│   └── cryodrgn/
│       ├── pose.py               # PATCHED: single-bin HEALPix fallback
│       └── models.py             # PATCHED: CTF exponent clamped to >=0
└── opus_project/
    ├── 01_write_star.py          # generates particles.star + dummy_ctf.star
    ├── 02_make_pose.sh           # dsd parse_pose_star -> pose_euler.pkl
    ├── 03_make_mask.py           # average subtomograms -> mask.mrc
    ├── 04_train.sh               # dsd train_tomo
    ├── 05_analyze.sh             # dsdsh analyze -> PCA/UMAP/kmeans
    ├── 06_eval_vol.sh            # dsdsh eval_vol -> reference*.mrc
    ├── 07_split_star.sh          # dsd parse_pose_star --labels -> pre*.star
    ├── logs/                     # pipeline run logs
    ├── particles.star            # RELION 3.0 STAR file (672 particles)
    ├── pose_euler.pkl            # rotation matrices (all identity)
    ├── consensus.mrc             # average of all 672 subtomograms
    ├── mask.mrc                  # binary solvent mask (1σ threshold + 2px dilation)
    ├── output/                   # training outputs
    │   ├── weights.N.pkl         # model weights per epoch
    │   ├── z.N.pkl               # latent codes per epoch
    │   ├── config.pkl            # model/data config
    │   └── analyze.19/
    │       ├── z_pca.png         # PCA plot
    │       ├── umap.png          # UMAP plot
    │       └── kmeans8/
    │           ├── labels.pkl    # cluster assignments (672,)
    │           ├── centers.txt   # latent codes at centers
    │           └── reference*.mrc  # one 3D map per class
    └── split_star/
        └── pre{0..7}.star        # per-class particle lists

~/src/particles/
    ├── aligned_tom*.mrc          # 672 subtomogram MRC files
    └── dummy_ctf.star            # placeholder CTF file (required by OPUS-ET)
```

---

## Iterating on Results

- **Try different K**: re-run with `bash runClassification.sh --skip-train --k 5` (or 12). Deletes nothing — creates new `kmeans5/` subdirectory.
- **Interactive filtering**: `jupyter notebook opusTomo/cryodrgn/templates/cryoDRGN_filtering_template.ipynb` — polygon-lasso UMAP to manually curate subpopulations.
- **More epochs**: re-run training without `--skip-train`; existing `split.pkl` is reused, epochs resume from checkpoint.
- **Higher resolution**: take particles from one class's `pre*.star` and re-run STA refinement in RELION or EMAN2 on just that subpopulation.
