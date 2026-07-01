# TomoFlow — How It Works, the CUDA-13 Port, and Results

**Method:** TomoFlow = continuous conformational heterogeneity analysis of subtomograms by 3D
**optical flow** (OF).
**Paper:** Harastani, Eltsov, Leforestier, Jonić, "TomoFlow: Analysis of continuous conformational
heterogeneity in cryo electron sub-tomograms," *J. Struct. Biol.* 2022.
**Upstream:** the `heteroflow` protocols in ContinuousFlex (`continuousflex-org/continuousflex-code`),
normally run through Scipion. We run it **standalone** (no Scipion), using the real OF engine.

TomoFlow takes **pre-aligned subtomograms** (no tilt series), computes a dense 3D optical flow from a
global-average reference to each particle, treats the per-particle OF displacement field as the
conformational descriptor, projects all of them to a low-dimensional space with PCA, and clusters /
visualises that landscape. It is a **continuous** method; we read out discrete classes by k-means.

---

## 1. Pipeline (faithful, standalone)

1. **Reference** = voxel-wise mean of the 672 aligned subtomograms (global average).
2. **Optical flow** — for each subtomogram, `farneback3d.Farneback(...).calc_flow(reference, vol)`
   (the exact engine ContinuousFlex calls in `protocol_heteroflow.py`), with that protocol's default
   parameters: `pyr_scale=0.5, levels=4, winsize=10, iterations=10, poly_n=5, poly_sigma=1.2`, gray
   `factor=100`. Output per particle: a `(3, d, d, d)` displacement field.
3. **Dimensionality reduction** — stack the OF fields `(N, 3·d³)` and project with sklearn PCA to 2D
   (ContinuousFlex `protocol_heteroflow_dimred.py` default = sklearn PCA), giving the conformational
   landscape.
4. **Clustering** — k-means at k=2/3/4 on the landscape; class averages from full-res 80³ originals.

Scripts: `~/Research/tomoflow_work/tomoflow_run.py` (steps 1–3, the real `farneback3d`),
`scripts/analysis/tomoflow_report.py` (step 4 + landscape/bimodality + figures).

---

## 2. The CUDA-13 / Blackwell port (the hard part — durable knowledge)

`farneback3d` (theHamsta/farneback3d, the GPU OF library TomoFlow uses) does **not** build on this
node out of the box. Two incompatibilities with **CUDA 13.2 + RTX 5080 (sm_120)**, and a fundamental
constraint:

- **Texture references were removed in CUDA 12.** The kernels declared
  `texture<float, cudaTextureType3D, ...> sourceTex;` and sampled with `tex3D(sourceTex, …)`
  (in `resize.cu` and `farneback_kernels.cu`). nvcc 13.2 rejects this.
- **`<surface_functions.h>` was removed in CUDA 13**, but `farneback_kernels.cu` pulled it in via
  `#include <pycuda-helpers.hpp>` (only needed for the texture helper type `fp_tex_float`).
- **The constraint:** there is **no CUDA toolkit that supports both** texture references (nvcc ≤ 11)
  **and** Blackwell `sm_120` (nvcc ≥ 12.8). So "use an older CUDA" is not an option — the kernels
  must be ported. (PyCUDA itself compiles custom kernels on sm_120 fine — verified — so only the
  texture API was the blocker.)

**The port** (kept in `~/Research/tomoflow_work/farneback3d_patched/`, installed into env `tomoflow`):
- Replaced each `tex3D(sourceTex, cx, cy, cz)` with a `__device__` **manual trilinear sampler**
  reading from a plain global-memory `float*`, replicating the texture's exact behaviour:
  `cudaFilterModeLinear` + `cudaAddressModeBorder` (out-of-range → 0) + unnormalized coords (CUDA
  texture HW subtracts 0.5 from the coordinate before interpolating — we do the same).
- Added the source volume as a global-memory kernel argument (`resize`, `warpByFlowField`); on the
  host (`_utils.py`, `_farneback3d.py`) removed `get_texref` / `ndarray_to_float_tex` and pass the
  gpuarray directly (for `warpByFlowField`, pass the contiguous slice `R1_gpu[i]`).
- Dropped `#include <pycuda-helpers.hpp>` (no longer needed → avoids `surface_functions.h`).
- Also fixed a numpy-2 incompatibility (`np.int` → `int`) in `_utils.resize_gpu`.

**Build:** the package uses **pbr** (version from git → `0.0.0` in an sdist; empty wheel because pbr
lists files from git). Build the wheel **in-place** where the `egg-info/SOURCES.txt` lives, with the
version pinned: `PBR_VERSION=0.1.4 python setup.py bdist_wheel` (after removing the sibling
`travis/`,`docs/`,`tests/` dirs so setuptools' flat-layout discovery doesn't choke), then
`pip install dist/*.whl`.

**Validation:** patched OF recovers a known +3-voxel blob shift (Fx≈2.9, Fy≈Fz≈0) on the GPU. (Sign
follows the library's documented reverse convention.)

---

## 3. Install summary

- conda env **`tomoflow`** (python 3.11): `pycuda` (builds against CUDA 13.2), `numpy<... (2.x ok)`,
  `scipy`, `scikit-learn`, `mrcfile`, `matplotlib`, and the **patched** `farneback3d` above.
- Need `nvcc` on PATH at runtime: `export PATH=/usr/local/cuda-13.2/bin:$PATH; export CUDA_ROOT=/usr/local/cuda-13.2`.

## 4. Run

```bash
conda activate tomoflow
export PATH=/usr/local/cuda-13.2/bin:$PATH CUDA_ROOT=/usr/local/cuda-13.2
python ~/Research/tomoflow_work/tomoflow_run.py \
    --subtomo-dir ~/Research/STA/subtomos_mrc --outdir ~/Research/tomoflow_work
python scripts/analysis/tomoflow_report.py        # -> tomoflow/results/
```
~30 s/particle at native 80³ (≈5.5 h for 672; downsample with `--downsample 2` to speed up).
Runtime artifacts (`of_features.npy` ≈ 3.9 GB, `embedding.npy`, `reference.mrc`) stay in
`~/Research/tomoflow_work/` (local, gitignored).

## 5. Results on T4P (672 particles)

| k | class sizes (occupancy) | inter-class CC |
|---|---|---|
| 2 | 638 (95%), 34 (5%) | 0.840 |
| 3 | 391 (58%), 252 (38%), 29 (4%) | 0.773–0.956 |
| 4 | 327 (49%), 305 (45%), 26 (4%), 14 (2%) | 0.532–0.964 |

**The conformational landscape is a single unimodal blob** (`tomoflow/results/tomoflow_landscape.png`):
PC1 has one peak with a long outlier tail — **not bimodal**. At k=3/k=4 k-means does produce two
*large balanced* clusters, but they are **the same structure** — the two big k=3 classes (n=252, 391)
have inter-class CC **0.956** and their averages are visually identical crisp pili
(`tomoflow_k3_classes.png`); k-means is merely bisecting a continuous unimodal cloud, not finding a
gap.

**Conclusion: TomoFlow does NOT recover the two pili phases either.** It joins RELION, PyTom, Protomo,
and DISCA — **five general-purpose packages now miss the two-phase split that Dynamo recovers**
([[dynamo]] = reference). The OF descriptor here is dominated by a continuous noise/missing-wedge
axis rather than the (apparently subtle) phase difference.

**Masked run (2026-07-01, ORC SLURM job 12460059):** Re-run with cylindrical mask v2 applied.
Result: k=2 → 403/269. ARI vs Dynamo = **-0.001**, but cross-package comparison reveals:
**ARI = 1.000 vs DISCA, 0.993 vs EMAN2, 0.887 vs OPUS**. The masked optical-flow landscape
captures the same contrast/intensity axis as the non-structural group — not the conformational
axis. Reclassified: TomoFlow is **non-structural** on T4P (not collapsed). The OF descriptor
is sensitive to contrast/missing-wedge variation, consistent with the bimodal PC1 split that
is real but biologically uninformative for conformational classification.

## 6. Files

| File | Purpose |
|---|---|
| `~/Research/tomoflow_work/tomoflow_run.py` | OF (real farneback3d) + PCA landscape |
| `~/Research/tomoflow_work/farneback3d_patched/` | CUDA-13-ported farneback3d (texture→global mem) |
| `scripts/analysis/tomoflow_report.py` | landscape + bimodality + k-means + class averages |
| `tomoflow/results/` | `RESULTS.md`, landscape + per-k class-average PNGs |
