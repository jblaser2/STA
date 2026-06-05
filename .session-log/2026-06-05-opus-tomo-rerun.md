# 2026-06-05 — RELION no-align result + OPUS-TOMO setup and re-run

## Goal
1. Check RELION no-align (PEET-seeded + orientation search) result.
2. Set up OPUS-TOMO from scratch (opuset env missing) and re-run with cylindrical mask
   to see if the v2 Y-axis mask improves T4P classification.

---

## What happened

### RELION no-align (config 6, orientation search) — CONFIRMED COLLAPSE
- Run completed: `outputs/relion/Class3D/k2_wedge_noalign/run_it025_data.star`
- Class distribution: **672/0** — all particles in class 1.
- Orientation search (no `--skip_align`) does NOT prevent collapse. Even at ~11 min/iter
  the algorithm still collapses because per-particle SNR is too low regardless of how the
  E-step orientation is sampled. This is the 6th and final config tested.
- **RELION T4P canonical result: ARI≈0 under all configurations. Algorithm-level failure confirmed.**
- Updated memory `relion-t4p-soft-em-failure.md` with config 6 result.

### OPUS-TOMO setup (from scratch — opuset env and ~/opusSrc deleted since last session)

**Environment setup:**
1. Cloned opusTOMO to `~/opusSrc/opusTOMO`: `git clone https://github.com/alncat/opusTOMO.git`
2. Applied patches from `opusTomo/opusPatches/` (models.py, pose.py) before install
3. `conda create -n opuset python=3.10 -c conda-forge -y`
4. `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128` (RTX 5080 needs cu128)
5. `pip install mrcfile numpy scipy scikit-learn umap-learn healpy seaborn adjustText monty starfile pyarrow astropy biopython tqdm typeguard`
6. `pip install -e ~/opusSrc/opusTOMO` → `dsd` CLI working, GPU verified

**Script fixes (paths were wrong — particles at subtomos_mrc/ not ~/src/particles/):**
- `scripts/01_write_star.py`: PARTICLE_DIR → `~/Research/STA/subtomos_mrc`
- `scripts/03_make_mask.py`: PARTICLE_DIR fixed; mask logic updated (see below)
- `scripts/04_train.sh`: DATADIR → `~/Research/STA/subtomos_mrc`

### OPUS-TOMO Run 1: Y-axis cylinder mask (v2 params, matching PyTom)

Mask: Y-axis cylinder, r=13 vox (XZ circle), h_pos=0, h_neg=25 vox. Coverage: **2.7% of voxels**.

```
K=2: [668, 4]   ← collapsed
K=4: [1, 2, 377, 292]   ← main clusters 377/292
K=8: [1, 1, 3, 5, 241, 51, 184, 186]
```

**Conclusion: The tight cylindrical mask is too restrictive for OPUS-TOMO's VAE.** Unlike PyTom
(which uses difference maps to focus on discriminative voxels), the VAE decoder reconstructs
a full 3D template constrained by the mask. With only 2.7% of voxels unmasked, the decoder
has too little signal to learn latent representations that cleanly separate the two phases.
K=4 shows the two main groups (377/292) but K=2 collapses.

### OPUS-TOMO Run 2: Threshold mask (mean + 1σ + 2px dilation)

Mask: threshold-based, coverage: **31.2% of voxels**.

Training: 20 epochs, ~2:31 (7.5 s/epoch on RTX 5080).

```
K=2: [447, 225]   ← consistent with research.md's 430/242 result
K=8: [1, 1, 4, 206, 25, 65, 167, 203]
```

**K=2: 447/225** — this is the OPUS-TOMO baseline result. Class 0 (447) ≈ ring_complete,
class 1 (225) ≈ ring_altered. Consistent with previous documented result (430/242).

**Result CSV:** `results/opus_tomo_k2.csv` (447/225 assignments)

---

## Files changed (repo)

| File | Change |
|---|---|
| `opusTomo/scripts/01_write_star.py` | PARTICLE_DIR fixed to subtomos_mrc |
| `opusTomo/scripts/03_make_mask.py` | PARTICLE_DIR fixed; now threshold mask |
| `opusTomo/scripts/04_train.sh` | DATADIR fixed to subtomos_mrc |
| `scripts/eval/extract_opus_tomo_classes.py` | NEW — extract labels.pkl → CSV |
| `results/opus_tomo_k2.csv` | NEW — OPUS-TOMO K=2 class assignments (447/225) |
| `STATUS.md` | Updated OPUS-TOMO row, RELION noalign, GROUND TRUTH bullet |

**Local-only (not in repo):**
- `~/opusSrc/opusTOMO/` — cloned opusTOMO source (patched)
- `opusTomo/scripts/output/` — training weights + analysis (z.*.pkl, analyze.19/)
- `opusTomo/scripts/{particles.star, pose_euler.pkl, consensus.mrc, mask.mrc, train.log}`
- `~/Research/STA/subtomos_mrc/dummy_ctf.star` — placeholder CTF file for OPUS-TOMO

---

## Where I stopped
- OPUS-TOMO K=2 result: 447/225 (threshold mask, epoch 19). ARI vs PEET soft GT not yet computed.
- Y-axis cylinder mask experiment documented: K=2 collapses (668/4), mask too restrictive for VAE.
- Both run outputs saved to `opusTomo/scripts/output/` (local only).

## Next step
1. Compute ARI (OPUS-TOMO K=2 vs PEET v2 soft GT) using `scripts/eval/score_predictions.py` or similar
2. Update `results/synthetic_scores.csv` or equivalent T4P comparison table
3. Consider EMAN2 k=3/k=4 (quick run, just needs more iterations)
4. Dynamo motor_easy (PCT confirmed installed, merged_all_aln rebuilt)
