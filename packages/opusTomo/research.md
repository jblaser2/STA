# OPUS-ET Pili Subtomogram Classification — Research Notes

_Last updated: 2026-06-09_  
_Status: Pipeline completed successfully — 20 epochs, **cylindrical r=12 mask**, **in-training orientation search disabled** (data is pre-aligned). K=2 gives a 438 / 234 (65% / 35%) split, reproducing the earlier 430/242 result with a cleaner setup. Validation SNR² ≈ 3.7 (vs ≈1.6 in the earlier threshold-mask + search-on run)._

> **For someone replicating this:** read "Environment Setup" → "Pipeline" top-to-bottom. Two things differ from stock OPUS-ET and matter a lot: (1) the mask is an explicit **cylinder along the Y axis**, and (2) training runs through `train_skipalign.py`, which **disables OPUS-ET's per-step orientation search** because our particles are already aligned at Euler (0,0,0). Both are explained in Steps 3 and 4. You also need the **patched `opusTomo`** (see "OPUS-ET Source Code Bugs and Fixes").

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
| Pose metadata | None — particles are pre-aligned, Euler angles set to zero. The filament **long axis is Y** (measured from the consensus; see Step 3), not Z as earlier notes said. |

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
bash runClassification.sh 2>&1 | tee opus_project/pipeline_$(date +%Y%m%d_%H%M%S).log
```

This runs **skip-align** training (the default in `04_train.sh`) and finishes at K=8; produce the chosen K=2 result afterward (see "Iterating on Results"). Wall time on the RTX 5080 is a few minutes.

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

### Step 3: Consensus Map + Cylindrical Mask (`opus_project/03_make_mask.py`)

Averages all 672 subtomograms → `opus_project/consensus.mrc`, then writes a **parametric cylindrical mask** → `opus_project/mask.mrc`. (Earlier versions used a `mean+1σ` threshold of the consensus; that average is dominated by a curved membrane arc + heavy missing-wedge streaking and thresholds into a fragmented blob, so we switched to an explicit cylinder.)

**Measured geometry (from the existing consensus):** the dense pilus core is centred in the box and runs along the **Y axis** (per-axis spread σ: Z=8.7, Y=12.0, X=8.5), with a compact perpendicular cross-section (radial σ ≈ 8.6 vox). NB: this contradicts the old "z-axis aligned" note — for *this* dataset the filament long axis is Y. Per-particle density COMs are consistent (std ≈ 2–4 vox), so the particles are well centred.

```bash
python 03_make_mask.py                       # default mask: axis=y, radius=12, half_len=34 (the chosen geometry)
python 03_make_mask.py --consensus           # also (re)compute consensus.mrc first (needed after a clean slate)
python 03_make_mask.py --sweep               # write candidate masks + montage to mask_tests/
python 03_make_mask.py --axis y --radius 16 --half-len 34   # write a different geometry
```

The production mask used for the results below is **`axis=y, radius=12`** (`DEF_RADIUS=12` in the script). If `mask.mrc` already exists the orchestrator's Step 3 is **skipped**, so to regenerate the consensus for inspection run `03_make_mask.py --consensus` explicitly (it won't touch `mask.mrc` unless you also pass mask args).

**Radius is the key knob — it also sets the OPUS-ET encoder crop window:**
`window_r ≈ (2·radius + 4) / D`. So radius {12, 16, 20} → window_r {0.35, 0.45, 0.55}; a tighter radius focuses the encoder harder on the pilus with less surrounding context. Candidate sweep (in `mask_tests/`, inspect against `consensus.mrc` in ChimeraX via `mask_candidates.png`):

| Mask | Occupancy | window_r | Note |
|---|---|---|---|
| `cyl_y_r12_l68` | 6.0% | 0.35 | **chosen default** — tight focus on the core |
| `cyl_y_r16_l68` | 10.8% | 0.45 | balanced |
| `cyl_y_r20_l68` | 16.8% | 0.55 | generous, keeps context |
| `cyl_z_r16_l68` | 10.8% | 0.45 | wrong axis (Z) — for comparison only; mismatches the consensus |

**Binarisation gotcha:** OPUS-ET gates the reconstruction loss with `(valid > 0)` (`models.py`), so any soft/tapered mask edge is treated as fully inside. The mask written here is therefore **binary** — a soft cosine edge would just silently enlarge the effective mask.

---

### Step 4: Training (`opus_project/04_train.sh`)

Run it via the wrapper script (this is what the orchestrator calls):

```bash
bash opus_project/04_train.sh          # skip-align (default): no orientation search
ALIGN=1 bash opus_project/04_train.sh  # stock OPUS-ET path: orientation search ON
```

`04_train.sh` builds and runs the following. In the **default** (skip-align) mode the launcher is `python opus_project/train_skipalign.py …`; with `ALIGN=1` it is `dsd train_tomo …`. The argument list is identical either way:

```bash
<launcher> opus_project/particles.star \
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

#### In-training subtomogram alignment — and how to skip it (`train_skipalign.py`)

**OPUS-ET re-aligns every subtomogram on every training step, regardless of the input poses.** The decoder (`VanillaDecoder.forward`, `models.py:1437`) builds a local Hopf grid of candidate orientations (`get_particle_hopfs`, ~8 samples) plus a random ±180° in-plane angle, then the loss marginalises the reconstruction error over those orientations with a softmax-EM weighting (`loss_function`, the `C > 1` branch, `train_tomo.py:384`). The identity input poses only seed the search. (The `refine_pose=False` branch that would bypass this is unimplemented — it raises `RuntimeError("Not implemented")` at `models.py:1671`; that is gotcha #9.)

Since our dataset is already aligned at Euler (0,0,0), this search is wasted compute and lets orientation absorb variance that should go into the latent — blurring the classification. **`04_train.sh` now skips it by default** via a non-invasive wrapper (opusTomo source is left untouched):

- `opus_project/train_skipalign.py` monkeypatches `VanillaDecoder.get_particle_hopfs` to return **two identical copies of the seed orientation** instead of the ~8-point local grid. Two identical candidates make the softmax-EM marginalisation a no-op (uniform weights → same loss and gradient as a single orientation), so there is effectively **no orientation search**. Both candidate rotations are the identity (verified).
- **Why two and not one:** OPUS-ET's `loss_function` only assigns `snr` inside its `C > 1` branch but then uses `snr` unconditionally (`train_tomo.py:463`). A literal `C = 1` therefore crashes with `UnboundLocalError: local variable 'snr'`. Returning two identical orientations keeps `C > 1` so `snr` is defined, without reintroducing a real search. (This is issue #5 below; handled entirely in the wrapper, no opusTomo edit.)
- Toggle in `04_train.sh`: default = skip-align (`python train_skipalign.py …`); set `ALIGN=1 bash 04_train.sh` to restore the stock search-on path (`dsd train_tomo …`).
- **Residual:** a random in-plane angle is still drawn per step but applied *identically* to the reference and the template projection — matched augmentation, not a search; it cannot let pose explain heterogeneity. Fully removing it would need a 2-line edit to `VanillaDecoder.forward`, which we avoid to keep opusTomo pristine.
- The encoder also applies a tiny random orientation jitter (`models.py:720`); it is augmentation-scale (≈ one HEALPix pixel at nside 128) and left in place.

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

#### Actual training results (this run: cylindrical r=12 mask, skip-align)

- Train/val split: 537 train / 135 val (`--valfrac 0.2`); 33 train batches, 8 val batches per epoch. Split frozen in `output/split.pkl`.
- 20 epochs (`z.0.pkl` … `z.19.pkl`; epoch index is 0-based, log labels them 1–20). No NaN, no divergence.
- Validation SNR² climbs from ≈2.3 (epoch 1) to ≈3.4–4.8 (epochs 12–20), settling ≈3.7 at epoch 20 — substantially higher than the earlier threshold-mask + search-on run (≈1.6), consistent with the tighter mask and removal of the orientation search.
- Wall time: ~5 s/epoch on the RTX 5080 (the local search being off also speeds training).

#### Resume training if interrupted

```bash
# resume from a checkpoint epoch (re-uses output/split.pkl):
bash opus_project/04_train.sh 19        # loads weights.19.pkl + z.19.pkl, continues
# equivalently, by hand:
python opus_project/train_skipalign.py ... --load opus_project/output/weights.19.pkl --latents opus_project/z.19.pkl
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

### Step 8: 2D Class Average Projections (`opus_project/08_class_averages.py`)

For each class, loads all raw subtomograms assigned to that class, accumulates a float64 mean volume, then generates three 2D views: XY projection (top-down cross-section), XZ projection (side view), and the central Z slice.

```bash
python opus_project/08_class_averages.py              # auto-detect epoch, K=2
python opus_project/08_class_averages.py --epoch 19 --k 2  # explicit
```

Output saved alongside the 3D volumes for the same run:
`opus_project/output/analyze.{EPOCH}/kmeans{K}/class_averages.png`

Saving inside `analyze.{EPOCH}/kmeans{K}/` means the directory path encodes both epoch and K. Re-running with different parameters writes to a different directory automatically.

**Implementation details:**
- MRC axis order is `(Z, Y, X)`: XY projection = `np.sum(avg, axis=0)`, XZ = `np.sum(avg, axis=1)`, central Z slice = `avg[D//2, :, :]`
- Per-panel normalisation: z-score, clip to ±3σ, rescale to [0, 1]
- STAR parsing: `_rlnImageName` column contains bare filenames; prepend `~/src/particles/` to get full paths

---

## Actual Results (epoch 19)

The orchestrator runs K=8 by default; the natural answer is **K=2**, chosen by inspecting the UMAP.

**Latent embedding.** The UMAP (`output/analyze.19/umap.png`) is a single **continuous arc** whose density along UMAP1 is **bimodal** (two humps with a dip near the middle) — i.e. a continuum with two dominant modes rather than 8 discrete blobs. K=8 therefore over-segments (it produces classes of just 2 and 7 particles). K=2 captures the two modes.

**K=2 split (chosen):**

| Class | Particles | Fraction |
|---|---|---|
| 0 | 438 | 65% |
| 1 | 234 | 35% |

This reproduces the earlier run's 430/242 split with a cleaner mask and no orientation search — good evidence the two-population result is real and not a setup artifact.

- 3D density maps: `opus_project/output/analyze.19/kmeans2/reference{0,1}.mrc` ← **the real differences live here; open in ChimeraX**
- Split STAR files: `opus_project/split_star/pre{0,1}.star`
- 2D class averages: `opus_project/output/analyze.19/kmeans2/class_averages.png`

(The initial K=8 analysis was pruned once K=2 was confirmed — only `kmeans2/` is retained. Regenerate any K with the recipe in "Iterating on Results".)

**2D projection averages** (XY, XZ, central Z slice): with the cylindrical mask the central pilus core is now clearly focused (a compact dark lens in the XZ view). Gross morphology is still similar between classes — these are *raw real-space* means, so the horizontal membrane band and missing-wedge cross dominate; assess the actual class differences in the 3D maps.

**K selection rationale.** Run K=8 first, inspect `umap.png`. Discrete well-separated blobs → use K = number of blobs. A continuous arc with N density modes (our case) → use K = N. Re-run analysis only (no retrain) — see "Iterating on Results" for the correct way to do this (the split step needs care).

---

## OPUS-ET Source Code Bugs and Fixes

Five issues surface in this all-zero-pose, no-CTF, pre-aligned use case. **Bugs 1, 2, 5 are handled without touching opusTomo** (dummy CTF / required CLI arg / the skip-align wrapper). **Bugs 3 and 4 are applied as minimal source patches** to `opusTomo/cryodrgn/pose.py` and `models.py` — so a fresh `pip install -e .` of upstream opusTomo will *not* have them. Anyone replicating must use **our patched `opusTomo/` tree** (or re-apply Bugs 3 & 4 below). See "What to share".

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

### Bug 5: `snr` undefined when the orientation search is collapsed (`C == 1`)

**File**: `cryodrgn/commands/train_tomo.py`, `loss_function` (line ~463)
**Symptom**: `UnboundLocalError: local variable 'snr' referenced before assignment`, hit only when skipping the orientation search.
**Cause**: `snr` is assigned only inside the `if C > 1:` branch (line ~422) but used unconditionally afterwards (`lamb = args.lamb * (… snr …)`, line 463). With a single orientation candidate, `C == 1`, the `else` branch never sets `snr`.
**Fix (non-invasive, in `train_skipalign.py`)**: have the patched `get_particle_hopfs` return **two identical** seed orientations instead of one, so `C == 2`. The marginalisation over identical candidates is a no-op but keeps the `C > 1` path that defines `snr`. No opusTomo edit. (See Step 4.)

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

9. **`refine_pose=False` is broken** — the decoder's `refine_pose=False` branch raises `RuntimeError("Not implemented")` (`models.py:1671`), so it cannot be used to skip alignment. To skip the in-training orientation search use the `train_skipalign.py` wrapper instead (default in `04_train.sh`); it keeps `refine_pose=True` but collapses the orientation grid to one sample. See Step 4.

10. **Single GPU only** — one RTX 5080. Do not pass `--multigpu` or `--num-gpus`.

11. **All poses are zero, but OPUS-ET still searches orientations** — see Step 4. The pipeline now skips that search by default (`train_skipalign.py`). Also: the filament long axis in this dataset is **Y**, not Z (measured from the consensus), despite older "z-aligned" wording.

12. **PyTorch 2.6+ required** — the bundled `environment.yml` pins PyTorch 1.11+CUDA 11.3, which has no Blackwell (SM_120) kernels. Install cu128 wheels.

13. **`split_star/` is NOT K-namespaced** — `07_split_star.sh` writes `pre0.star … pre{K-1}.star` straight into `opus_project/split_star/`. Re-running at a different K does **not** clear the old files, so a K=2 run leaves stale `pre2…pre7` from a prior K=8 run (and the orchestrator's Step 7 skips entirely if any `pre*.star` exists). Always `rm -f opus_project/split_star/pre*.star` before splitting at a new K. (`analyze.{epoch}/kmeans{K}/` *is* properly namespaced — only the split STARs are not.)

14. **Skipping the orientation search needs `C == 2`, not `C == 1`** — see Bug 5. A literal single-orientation collapse crashes on an undefined `snr`. The wrapper uses two identical orientations.

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
    ├── 04_train.sh               # launches train_skipalign.py (or `dsd train_tomo` if ALIGN=1)
    ├── train_skipalign.py        # wrapper: monkeypatches out the orientation search (no opusTomo edits)
    ├── 05_analyze.sh             # dsdsh analyze -> PCA/UMAP/kmeans
    ├── 06_eval_vol.sh            # dsdsh eval_vol -> reference*.mrc
    ├── 07_split_star.sh          # dsd parse_pose_star --labels -> pre*.star
    ├── 08_class_averages.py      # 2D projection class averages (XY, XZ, central Z)
    ├── pipeline_*.log            # pipeline run logs (also runClassification.log)
    ├── mask_tests/               # candidate cylindrical masks + mask_candidates.png
    ├── particles.star            # RELION 3.0 STAR file (672 particles)
    ├── pose_euler.pkl            # rotation matrices (all identity)
    ├── consensus.mrc             # average of all 672 subtomograms
    ├── mask.mrc                  # binary cylindrical mask (axis=y, r=12, window_r~0.35)
    ├── consensus_inspect.png     # ortho-slices of consensus + sample particles (assessment aid)
    ├── output/                   # training outputs
    │   ├── config.pkl            # model/data config (REQUIRED to load weights later)
    │   ├── split.pkl             # frozen train/val split (REQUIRED to reproduce/resume)
    │   ├── weights.N.pkl         # model weights per epoch (N=0..19)
    │   ├── z.N.pkl               # latent codes per epoch (N=0..19)
    │   ├── pose.N.pkl            # per-epoch pose state
    │   ├── run.log               # training log
    │   └── analyze.19/
    │       ├── z_pca.png, umap.png (+ *_hexbin.png, umap.pkl)   # latent embeddings
    │       ├── pc1/, pc2/        # PC-traversal volumes
    │       └── kmeans2/          # chosen result (K=2; initial kmeans8 was pruned)
    │           ├── labels.pkl    # cluster assignments (672,)
    │           ├── centers.txt / centers.pkl / centers_ind.txt
    │           ├── reference0.mrc, reference1.mrc  # one 3D map per class
    │           └── class_averages.png
    └── split_star/
        └── pre{0,1}.star         # per-class particle lists (NOT K-namespaced — gotcha #13)

~/src/particles/                 # INPUT DATA (not produced by the pipeline)
    ├── aligned_tom*.mrc          # 672 subtomogram MRC files
    └── dummy_ctf.star            # placeholder CTF file (required by OPUS-ET)
```

---

## What to Share for Replication

To let a lab member reproduce this from raw particles, share the following. Items marked **(required)** are essential; the run will not reproduce without them.

### 1. Pipeline scripts — `opus_project/` (all required)

| Script | Role |
|---|---|
| `runClassification.sh` *(lives in `~/opusSrc/`, not `opus_project/`)* | Master orchestrator — runs Steps 1–7 in order |
| `01_write_star.py` | Build `particles.star` (+ documents the dummy-CTF column) |
| `02_make_pose.sh` | Zero Euler angles → `pose_euler.pkl` |
| `03_make_mask.py` | Consensus average + **cylindrical mask** (`--sweep`, `--consensus`, `--axis/--radius/--half-len`) |
| `04_train.sh` | Training launcher (skip-align by default; `ALIGN=1` for stock) |
| `train_skipalign.py` | **The monkeypatch wrapper that disables the orientation search** — without it, training re-aligns every particle |
| `05_analyze.sh` | PCA / UMAP / k-means |
| `06_eval_vol.sh` | Per-class 3D volumes (`reference*.mrc`) |
| `07_split_star.sh` | Per-class STAR files (`pre*.star`) |
| `08_class_averages.py` | 2D class-average projections |

### 2. Patched OPUS-ET — **(required)**
Share the **`opusTomo/` tree as patched here**, or have them re-apply Bugs 3 & 4 to a fresh clone. A stock `pip install opusTomo` will crash on this dataset (`pose.py` single-bin, `models.py` CTF NaN). The skip-align and dummy-CTF fixes are *not* in opusTomo — they live in the scripts above, so they travel automatically.

### 3. Input data + setup docs — **(required)**
- `~/src/particles/aligned_tom*.mrc` — the 672 subtomograms.
- `~/src/particles/dummy_ctf.star` — placeholder CTF (Step 0). If missing, regenerate per Step 0.
- This `research.md` (the replication doc), and the `opuset` conda recipe in "Environment Setup" (PyTorch **cu128**, not the bundled `environment.yml`).

### 4. Optional, but helpful
- `opus_project/mask_tests/` (candidate masks + `mask_candidates.png`) so they can see how the radius was chosen.
- A copy of the final run log.

> **Minimal hand-off:** the 10 scripts above + the patched `opusTomo/` + the particle directory + this doc. Everything else (STAR, poses, consensus, mask, latents, volumes) regenerates from `bash runClassification.sh`.

---

## Output Files Worth Keeping

The `output/` directory is ~15 GB, almost entirely per-epoch `weights.*.pkl` (722 MB each). You do **not** need to archive all of it. Priorities:

### Tier 1 — keep always (tiny, fully describe the result; ~20 MB total)
- `output/config.pkl` — model/data config; **required** to reload the model.
- `output/split.pkl` — frozen train/val split; **required** to reproduce or resume.
- `output/z.19.pkl` — final latent codes (24 KB). The clustering is computed from this.
- `output/analyze.19/kmeans2/` (3 MB) — `labels.pkl`, `centers*`, `reference0/1.mrc`, `class_averages.png`. **The actual scientific result.**
- `output/analyze.19/{umap,z_pca}.png` — the embeddings that justify K=2.
- `split_star/pre0.star`, `pre1.star` — per-class particle lists (feed downstream STA refinement).
- `mask.mrc`, `pose_euler.pkl`, `particles.star` — small inputs to the run (or note they regenerate).

### Tier 2 — keep if you may resume / re-analyze later
- `output/weights.19.pkl` (722 MB) — final model weights; needed to generate new volumes or resume. Keeping just the **last** epoch is usually enough.
- `consensus.mrc` (~2 MB) and `consensus_inspect.png` — useful context.

### Tier 3 — safe to delete
- `output/weights.0.pkl … weights.18.pkl`, `z.0…18.pkl`, `pose.*.pkl` — intermediate epochs (~14 GB). Drop unless you specifically need an earlier epoch.

A compact archive of Tier 1 (+ `weights.19.pkl` from Tier 2) is well under 1 GB and is sufficient to reproduce every figure and to restart analysis.

---

## Iterating on Results

- **Try different K (no retrain).** The clean way, given the un-namespaced split (gotcha #13):
  ```bash
  K=2; E=19
  bash opus_project/05_analyze.sh   $E $K          # -> analyze.$E/kmeans$K/
  bash opus_project/06_eval_vol.sh  $E $K          # -> reference*.mrc
  rm -f opus_project/split_star/pre*.star          # clear stale split from a prior K
  bash opus_project/07_split_star.sh $E $K         # -> pre0..pre{K-1}.star
  python opus_project/08_class_averages.py --epoch $E --k $K
  ```
  `runClassification.sh --skip-train --k N` also works for analysis/volumes (new `kmeans{N}/`), but **will not** refresh `split_star/` if it is non-empty — clear it first.
- **K selection guide**: run K=8 first, inspect `umap.png`. Discrete separated blobs → K = number of blobs. A continuous arc with N density humps (our case → N=2) → K = N. A featureless smear → no discrete heterogeneity (or undertrained).
- **Interactive filtering**: `jupyter notebook opusTomo/cryodrgn/templates/cryoDRGN_filtering_template.ipynb` — polygon-lasso the UMAP to manually curate subpopulations.
- **More epochs**: re-run `bash opus_project/04_train.sh` (no checkpoint arg starts fresh from the frozen `split.pkl`; pass an epoch to resume).
- **Higher resolution**: take particles from one class's `pre*.star` and re-run STA refinement in RELION or EMAN2 on just that subpopulation.
- **Mask sensitivity**: regenerate at another radius (`03_make_mask.py --radius 16`), overwrite `mask.mrc`, and retrain — radius also sets the encoder crop (Step 3). Compare resulting UMAP/SNR².
