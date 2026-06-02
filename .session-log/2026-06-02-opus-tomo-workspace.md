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
