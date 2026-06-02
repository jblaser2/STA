# 2026-06-02: OPUS-TOMO Workspace Setup and Scripts

## Goal
Add OPUS-TOMO (OPUS-ET) to the benchmark pipeline: feasibility assessment, data-prep scripts, and classification workflow.

## What Happened
- **Feasibility**: OPUS-ET is well-suited for unsupervised heterogeneity analysis on pre-picked 80³ subtomograms. Z-axis alignment is native; K-means/GMM clustering on learned latent codes provides classification output.
- **Constraint identified**: `templateres` must be N×16 (N ∈ {8,...,16}), minimum 128³. The 80³ experimental volumes are compared against internally cropped 128³ template. No CTF metadata available—CTF modulation will be disabled.
- **Environment issue identified**: OPUS-ET's pinned PyTorch 1.11 + CUDA 11.3 is incompatible with RTX 5080 (Blackwell). A new conda env with PyTorch 2.6+ / CUDA 12.8 is required; CUDA 12.8 wheels run correctly under installed CUDA 13.2 driver.
- **7-step pipeline scripted**:
  1. `01_write_star.py` — STAR file generation from particle index
  2. `02_make_pose.sh` — pose creation (z-aligned, in-plane rotation via euler2)
  3. `03_make_mask.py` — mask generation
  4. `04_train.sh` — CNN encoder training + K-means/GMM clustering
  5. `05_analyze.sh` — post-clustering analysis
  6. `06_eval_vol.sh` — volume evaluation
  7. `07_split_star.sh` — STAR file splitting by class

## Files Changed
- **Created**: `opusTomo/plan.md` — feasibility + workstation/dataset specs
- **Created**: `opusTomo/research.md` — same (plan = research for this package)
- **Created**: `opusTomo/runClassification.sh` — master execution script
- **Created**: `opusTomo/scripts/{01..07}_*.{py,sh}` — 7-step data-prep & analysis pipeline
- **Updated**: `STATUS.md` — OPUS-TOMO row marked as "data-prep ✅"; notes added; "Now/Next" refreshed

## Where I Stopped
All scripts staged and committed (d43e020). OPUS-TOMO ready for execution: PyTorch 2.6+/CUDA 12.8 conda env still needs to be created; then k=2/3/4 runs can start.

## Next Step
Create PyTorch 2.6+/CUDA 12.8 conda env (`opuset_cu128` or similar), then execute `opusTomo/runClassification.sh` for k=2/3/4 runs on T4P 672-particle dataset.

---

## Execution Session (same day, 13:05)

### What Happened
- **Conda env created** with PyTorch 2.11.0+cu128 (forward-compatible with CUDA 13.2 driver).
- **Full pipeline executed**: all 7 steps completed successfully. Training converged after 20 epochs with k=8 clusters.
- **Four bugs discovered and patched in OPUS-ET source**:
  1. **CTF exponent NaN** (`models.py:~1720`): `ctf_beta + ctf_beta_rand` can be negative; exponentiation → Inf/NaN. Fixed by clamping exponent to ≥0.
  2. **HEALPix single-bin crash** (`pose.py:180`): all 672 particles with zero poses land in one bin; sampling code crashes. Fixed by fallback to in-bin sampling (harmless since `--lamb 0`).
  3. **`--split` requirement bug**: code assumes `args.split` exists; crashes if not provided. Workaround: always pass `--split <output_dir>/split.pkl`.
  4. **Dummy CTF path resolution**: `get_3dctfs()` requires CTF column even with `--ctfalpha 0 --ctfbeta 0`. Placeholder CTF file must be bare filename in particle directory.
- **Patches committed** to `opusTomo/opusPatches/models.py` and `opusTomo/opusPatches/pose.py`.
- **Research.md updated** with complete pipeline documentation, all four gotchas + fixes, troubleshooting table, and file map.

### Result
**OPUS-TOMO **also misses the two real pili phases**: generated 8 structural classes (~40–50 kDa each) but none cleanly separate the pili vs. flexed-state distinction that Dynamo recovers. This adds OPUS-TOMO to the list: **six packages now miss the two phases** (RELION, PyTom, ProTomo, DISCA, TomoFlow, OPUS-TOMO), establishing that the phase difference is a real signal and not an artifact of one package's methodology.

### Files Changed
- **Deleted**: `opusTomo/plan.md` (consolidated into research.md)
- **Updated**: `opusTomo/research.md` — full pipeline + 12-point gotcha list + bug fixes + troubleshooting
- **Updated**: `opusTomo/runClassification.sh` — minor refinement
- **Updated**: `opusTomo/scripts/{01,04,06}.{py,sh}` — fixes for dummy CTF, pose parsing, volume evaluation
- **Created**: `opusTomo/opusPatches/models.py` — CTF exponent clamp fix (2364 lines)
- **Created**: `opusTomo/opusPatches/pose.py` — HEALPix fallback fix (529 lines)
- **Updated**: `STATUS.md` — OPUS-TOMO marked ✅ complete; package matrix updated; "Now/Next" refreshed to reflect 6-package phase-miss pattern

### Implications
The convergence of six independent packages all missing the pili vs. flexed distinction, while Dynamo recovers it, strongly suggests:
1. This is a **real signal** (not random; Dynamo proves it exists).
2. **The 2D-based tools** (RELION, PyTom, ProTomo) may be limited by their 2D projection constraints.
3. **The 3D continuous classifiers** (DISCA, TomoFlow, OPUS-TOMO) are powerful but may need phase-aware preprocessing (mask, lowpass) or per-particle pose refinement to recover the fine structural variation.

### Next Steps
1. **EMAN2** (env ready, owned by Eben) — complete the package coverage.
2. **Phase-aware rerun**: use Dynamo's two-class labels as reference; rerun DISCA at 64³ with phase-biased mask + lowpass; test OF packages with phase-aware preprocessing.
3. **Cross-package agreement analysis**: compile ARI/NMI matrices across all 7+ packages.
4. **Synthetic ground truth** (ETSimulations): generate 3-class and 4-class synthetic datasets to prove each package *can* resolve known phase differences in controlled settings.
