# 2026-06-01 — Package coverage: emClarity, DISCA, TomoFlow

**Goal:** Extend the STA benchmark with more 3D-input classifiers on the real T4P set; check each
against the ground truth (Stefano: two distinct pili-phase classes, recovered by Dynamo).

## What happened

### emClarity (committed `fee530c`)
- Installed 1.5.3.11 + MATLAB Runtime R2019a. Fixed RHEL-10 `libcrypt.so.1` (shimmed a libxcrypt
  `.so.1`). **GPU works on the RTX 5080 (sm_120)**: its CUDA-10 cuFFT/gpuArray kernels forward-JIT to
  Blackwell via the CUDA 13.2 driver (verified: cuFFT 80³ + `emClarity rescale`). **But** emClarity
  is a tilt-series pipeline with no path to ingest pre-extracted subtomograms → **cannot run the real
  T4P set**; it's a synthetic-data-track package. Runbook: `EMCLARITY.md`.

### DISCA (committed `83a6977`, reorganised `4af3f2c`)
- Installed (env `disca`, torch 2.11+cu128, **native sm_120**). Template-free unsupervised deep
  clustering; runs directly on pre-aligned subtomos. Fixed two stock bugs (`cuda:2`→`cuda:0`; stripped
  util.py keras import). Data prep 80³→32³. k=2/3/4 → one dominant ~94% class + small noisy outliers.
- **Stefano consult (this session):** T4P really has **two distinct pili-phase classes**, Dynamo
  recovers them. So DISCA's result (and RELION/PyTom/Protomo's) is a **failure to separate the two
  phases**, not a null. Corrected STATUS + DISCA.md + 4 memory files; added `project_t4p_ground_truth`.
  Moved DISCA into a package dir (`disca/research.md`, `disca/results/`).

### TomoFlow (this session — not yet committed)
- 3D optical-flow continuous heterogeneity (ContinuousFlex `heteroflow`), run **standalone** (no
  Scipion) using the real `farneback3d` engine + sklearn PCA + k-means.
- **Major install hurdle (durable):** `farneback3d` won't build on CUDA 13.2 — kernels use **texture
  references** (removed in CUDA 12) and pull in `surface_functions.h` (removed in CUDA 13). No toolkit
  supports both texture-refs and Blackwell sm_120, so **ported the kernels**: replaced `tex3D` with a
  manual trilinear sampler reading global memory (replicating LINEAR+BORDER+unnormalized, −0.5 coord),
  passed the source volume as a kernel arg, dropped the pycuda-helpers include, fixed `np.int`. Build
  via pbr needs in-place `PBR_VERSION=0.1.4 python setup.py bdist_wheel`. Patched source kept in
  `~/Research/tomoflow_work/farneback3d_patched/`. Verified: recovers a known +3-voxel shift on GPU.
- Ran OF on all 672 (native 80³, ~30 s/vol) → PCA 2D landscape. **Landscape is unimodal**; k=3's two
  large clusters (n=252, 391) are the same pilus (CC 0.956). **TomoFlow also misses the two phases.**
  → **five packages now miss the split vs Dynamo.** Doc: `tomoflow/research.md`, figures in
  `tomoflow/results/`.

## Files changed (TomoFlow, staged not committed)
- `tomoflow/research.md`, `tomoflow/results/{RESULTS.md, tomoflow_landscape.png, tomoflow_k{2,3,4}_classes.png}`
- `scripts/analysis/tomoflow_report.py`
- `STATUS.md` (date, Now/Next, TomoFlow row)
- (local, not in repo) `~/Research/tomoflow_work/{tomoflow_run.py, farneback3d_patched/, *.npy, reference.mrc}`
- Memory: `project_tomoflow.md` (+ index). emClarity/DISCA/ground-truth memories written earlier in session.

## Where I stopped
TomoFlow complete and documented; files **staged, not committed** (handoff). emClarity (`fee530c`) and
DISCA (`83a6977`, `4af3f2c`) already committed + pushed earlier this session.

## Next step
Continue package coverage (MDTOMO / OPUS-TOMO), and/or chase the two-phase split with Dynamo's labels
as reference. ETSimulations synthetic two-class set (Josh, separate chat) to confirm packages can
separate a known phase difference. A parallel Dynamo-methodology session is logged separately
(`2026-06-01-dynamo-dtutorial-pca-mra.md`).
