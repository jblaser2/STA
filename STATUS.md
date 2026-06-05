# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-05** by Claude/Eben (694-particle RELION ARI=0.380 iter1; PEET motor_easy rerun ARI≈0 WMD; EMAN2 wedgefill patch; T4P: PyTom 440/232, RELION all 6 configs 672/0, OPUS-TOMO 447/225 threshold mask).

## Now / Next / Parked

- **T4P RE-RUNS COMPLETE — PYTOM SUCCESS, RELION EXHAUSTED, OPUS-TOMO DONE (2026-06-05):** **PyTom:** v2 cylindrical mask (r=13, h_pos=0, h_neg=25) + `-a` flag: k=2 → 440/232, k=3 → 422/150/100. **RELION:** all 6 configs collapse to 672/0 at iter 1–2 — (1) cylindrical mask; (2) ini_high=30+diam=500+firstiter_cc; (3) random init; (4) PEET-seeded → ARI=−0.03; (5) PEET-seeded + orientation search (no --skip_align) → 672/0. Algorithm-level SNR failure, no parameter fix possible. Canonical: ARI≈0. **OPUS-TOMO:** env (opuset) rebuilt from scratch; cloned opusTOMO → ~/opusSrc/opusTOMO (patched); particle paths fixed to `subtomos_mrc/`. Re-run with threshold mask (31.2% voxels): K=2 → **447/225** (epoch 19, 2.5 min training). Y-axis cylinder (2.7% voxels, matching PyTom) tried: K=2 collapses (668/4), too restrictive for VAE template reconstruction. Results: `results/opus_tomo_k2.csv`; extraction script: `scripts/eval/extract_opus_tomo_classes.py`. **Next: compute OPUS-TOMO ARI vs PEET soft GT; Dynamo motor_easy; EMAN2 k=3/k=4.**

- **README OVERHAUL COMPLETE (2026-06-04):** Complete rewrite of `README.md`: corrected SPA description, updated to 4 planned datasets, added T4P classes as lower periplasmic ring conformational states (cites Stefano's bioRxiv preprint), replaced PEET diff figure with v2, generated `motor_easy_classA_avg.png` from MRC, added `motor_easy_class_maps.png` showing all 3 input density maps, updated synthetic section to show class A/C averages (not B/C), honest UMAP caption, PEET added as second "converging" package in preliminary findings, team section updated (Recent Graduates, Gus Hart added as advisor). `etsimulation/figures/` directory created with 6 PNG figures.

- **SYNTHETIC DATA — SCORING FRAMEWORK COMPLETE (2026-06-04):** Scoring infrastructure built: `scripts/eval/score_synthetic.py` (ARI/AMI/V/Acc + confusion PNG), `scripts/eval/extract_relion_classes.py`, `scripts/eval/extract_peet_classes.py`, `peet/kmeans_motor_easy.py`. All scores appended to `results/synthetic_scores.csv`. **Missing-wedge decision:** feed GT-aligned particles (`merged_all_aln/`) with identity starting poses + tilt range ±60°; let each package apply its own native wedge correction. Template-matching baseline ARI=0.289 (structural signal confirmed present).

- **RELION motor_easy — INVESTIGATION COMPLETE + 694-PARTICLE RERUN (2026-06-05):** Root cause of ARI≈0: symmetric EM initialization (all K classes start from global average → soft EM diverges in 2 iters). `--skip_align` CORRECT for pre-aligned identity-pose particles. **Canonical blind result:** ARI=0.006 (k3_wedge). **GT-seeded upper bound on 634 particles:** ARI=0.254 iter 1 (firstiter_cc + skip_align + tau=8; collapses to ARI≈0 by iter 2). **694-particle rebuild (2026-06-05):** Rebuilt `merged_all_aln/` (A=246, B=271, C=177 = 694), rebuilt STAR, global avg, and GT class refs → reran RELION v3 config → **ARI=0.380 iter 1, then collapses to ARI=0.099 at iter 2**. GT-seeded results in `results/synthetic_scores.csv`. Scripts: `scripts/run_relion_motor_easy_v2/v3.sh`; mask: `outputs/relion_motor_easy/solvent_mask.mrc` (r=32 px, center Y-10); refs: `outputs/relion_motor_easy/class_refs.star`. **PEET motor_easy 694-particle rerun (2026-06-05):** Fixed mask: `szVol=[96³]`, `pcaFnParticleMask`→RELION solvent mask (r=32 px, Y-10), `outsideMaskRadius=44`. Result: max ARI=0.026 (k3_pc1_10) — confirms WMD-PCA limitation on uniform-wedge pre-aligned stacks. Scripts: `peet/motor_easy.prm`, `peet/motor_easy_stack.py`, `peet/kmeans_motor_easy.py`. **Next: Dynamo motor_easy (PCT confirmed installed); emClarity synthetic-only track.**

- **SYNTHETIC DATA — CLASS B EXPANDED + MASK SIZED (2026-06-04):** Added run_07 (36 subtomos) and run_08 (24 subtomos) to class B. New total: **A=246, B=271, C=177 = 694 particles**. `avg_gt_classB.py` updated and rerun → `avg_classB_aligned.mrc` (271 particles). Two ETSim pipeline bugs fixed: (1) `run_classB.sh` now `mkdir -p output/` before ETSim launch (ETSim uses `os.mkdir` not `os.makedirs` for root dir); (2) `sim_metadata.json` truncation on kill-timing — fixed via `reconstruct_metadata.py`. **Mask sizing done:** `visualize_avg_with_mask.py` generates central XY slice of global avg with mask overlay; final mask = r=32 px (427 Å), center offset Y=−10 (center at 48,38 in 96³ box). **Next: rebuild `merged_all_aln/` + RELION/PEET inputs for new 694-particle dataset, then rerun packages.**

- **DYNAMO motor_easy — UNBLOCKED (PCT confirmed installed 2026-06-04):** PCT IS installed. Dynamo MRA on motor_easy can proceed once merged_all_aln/ is rebuilt.

- **SYNTHETIC DATA — motor_easy ALL CLASSES DONE (2026-06-04):** Class A: 246 subtomos, Class B: 271 subtomos (8 runs), Class C: 177 subtomos. All GT-aligned averages computed + verified. **GT separability validated:** CC-template matching on GT-aligned subtomos gives ARI=0.289 (~68-73% per-class accuracy on noisy particles); class average CCs: A-B=0.72, A-C=0.66, B-C=0.83 — confirming classes are structurally distinct. **NOTE: `merged_all_aln/` still reflects old 634-particle count — must rebuild before next package runs.** Pipeline quirks: `STA/etsimulation/pipeline_quirks.md`.

- **PEET T4P CLASSIFICATION — TWO RUNS COMPLETE (2026-06-04):** Switched from generic sphere masks to T4P cylindrical mask (`T4P_mask/cylindrical_mask.npy`). Junk class = bottom 68 by CCC (exact match to Stefano's 68). **Mask v1** (r=11.2, h_pos=9.8, h_neg=15.8): [388 ring_complete / 216 ring_altered / 68 junk], AIC=518, BIC=363. **Mask v2** (r=13, h_pos=0, h_neg=25 — below-center only): [374 ring_complete / 230 ring_altered / 68 junk], AIC=659, BIC=504 (best). Both saved in `saved_runs/cylindrical_v{1,2}_*/`, pushed to `peet/results/`. Class labels: `ring_complete` / `ring_altered` / `junk`. Comparison figure vs Stefano's reference (509/95/68) panels: `peet/results/comparison_stefano_v1_v2.png`. Key finding: with cylindrical mask, PC1 is structural signal (include it); sphere masks the opposite. **Next: email Stefano for exact MOTL files; use v2 assignments as soft GT for remaining packages.**

- **BENCHMARK FRAMEWORK (2026-06-02, Claude research complete):** Wrote comprehensive `benchmarkIdeas.md`
  covering: (i) four-lens evaluation framework (external validity vs GT, downstream STA resolution,
  stability/robustness, cross-method consensus), (ii) vetted metric catalog with 25+ citations
  (ARI/AMI/V-measure, gold-standard FSC + AUC-FSC from CryoBench, Hennig clusterboot, Monti consensus,
  internal validity indices), (iii) explicit answers to Eben's three concerns (F-beta misses
  downstream goal, doesn't reveal regime-specific wins, not extensible to GT-free data), (iv) real-data
  track (T4P with Dynamo soft-GT) + synthetic-data track design, (v) output format options
  (recommended: multi-pillar profile + composite), (vi) implementation notes tied to existing scripts
  (relion_class_report.py, etc.), (vii) open questions back to team. README §8 weights (35/25/20/20)
  preserved as constraint; five concerns about the framework raised in §7 (not edited into README).
  → **Next: team review of benchmarkIdeas.md before execution; resolve the 5 open questions (Qs 1–5 in §11).**

- **GROUND TRUTH (Stefano consult, 2026-06-01; updated 2026-06-05):** this T4P dataset has **two distinct, obvious pili-phase classes**, and **Dynamo recovers them well** (`dynamo/`). **PEET also separates** (v2 cyl mask, 374/230/68). **PyTom NOW SEPARATES** (v2 cyl mask + auto_focus + -a flag: 440/232). **RELION, Protomo, DISCA, TomoFlow still fail** (one dominant class; RELION exhausted all 6 configs, algorithm-level SNR failure). **OPUS-TOMO: partial result** — K=2 gives 447/225 split (threshold mask) but ARI vs GT not yet computed; Y-axis cylindrical mask (matching PyTom v2) collapses K=2 (VAE needs broader mask). Benchmark signal: correct-mask versions of Dynamo/PEET/PyTom vs algorithm-level failures of the others.

- **Package completion status (2026-06-02):** 9 of 15 packages run on real T4P (RELION, Dynamo, PyTom,
  Protomo, DISCA, TomoFlow, EMAN2, OPUS-TOMO, PEET partial). EMAN2 k=2 complete but k=3/4 not yet run
  (table shows ⬜ discrepancy — needs fixing). STOPGAP owned by Eben, not started. MDTOMO/HEMNMA
  require atomic models (❌ skipped). AC3D folded into PyTom. TomoNet formally rejected (out-of-box scope
  violated). emClarity can't run real tilt-series data (synthetic only).

- **Parked (need expert input):** missing-wedge standardization; whether to discretize continuous-
  classifier outputs. (Discrete-vs-continuous is **resolved: discrete, two phases**.) → Stefano / Braxton.

## Package Matrix (15 packages, 3D-input classifiers)

Legend: ✅ done · 🟡 in progress · ⬜ not started · ❌ skip · — n/a/unknown

| Package | Installed | Env | Data-prep | k=2 | k=3 | k=4 | Pushed | Notes / blockers |
|---|---|---|---|---|---|---|---|---|
| RELION 3.1–4.0 | ✅ | `relion-5.0` | ✅ `build_relion_star.py` | ✅ | ✅ | ✅ | — | classic 3D-subtomo path **retained in RELION 5**; k=2/3/4 × wedge/uniform run; **T4P: confirmed algorithm-level failure** — soft EM collapses to 672/0 at iter 1–2 under all 6 variants (masked, tuned, random-init, PEET-seeded, PEET-seeded+orientation-search — all 672/0). ARI≈0. Root cause: per-particle SNR too low for CC discrimination. No parameter fix possible. Scripts: `run_relion_class3d_{masked,tuned,noref,peet_seed,noalign}.sh`. |
| STOPGAP | 🟡 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; full source + pipeline scripts committed to repo at `STOPGAP/` (commit 42122b0): `scripts/`, `src/`, `sg_toolbox/`, slurm jobs (`run_pipeline.slurm`, `resume_pca.slurm`); edited files (incl. `check_crashes.m`) live directly in source tree; compiled R2023b MCR binaries excluded from git (gitignored); 6-iter optimized schedule designed; `run_watcher_guarded` described in research.md §7 but **not yet added to `run_pipeline.slurm`**; next: add crash guard → run `build_inputs.m` → `sbatch run_pipeline.slurm` |
| OPUS-TOMO | ✅ | `opuset` (rebuilt 2026-06-05) | ✅ (paths fixed) | ✅ | ✅ | ✅ | — | 4 bugs patched (CTF, HEALPix, --split, dummy CTF); env rebuilt from scratch (opusTOMO cloned to ~/opusSrc/opusTOMO, cu128 PyTorch). **Threshold mask (31.2% voxels): K=2 → 447/225** (epoch 19, 2.5 min). Y-axis cylinder (2.7%): K=2 collapses (668/4) — mask too restrictive for VAE. Results: `results/opus_tomo_k2.csv`; extraction: `scripts/eval/extract_opus_tomo_classes.py`. ARI vs PEET GT not yet computed. |
| Dynamo | ✅ | MATLAB | ✅ | ✅ | — | — | — | **reference result**: recovers the two distinct pili-phase classes well (Josh + Stefano) → the ground-truth split other packages are measured against; workspace in `dynamo/`, `DYNAMO.md` |
| PEET | ✅ | IMOD | ✅ | ✅ | — | — | ✅ | Two runs complete (2026-06-04). **v1** (cyl r=11.2): 388/216/68. **v2** (cyl r=13, below-center): 374/230/68, AIC=659. Labels: ring_complete/ring_altered/junk. CSVs + figures in `peet/results/`. Cylindrical mask → include PC1 (structural signal). Still need Stefano's MOTL for exact GT. |
| MDTOMO | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| TomoFlow | ✅ | `tomoflow` | ✅ `tomoflow_run.py` | ✅ | ✅ | ✅ | — | also ContinuousFlex, but (unlike MDTOMO/HEMNMA) needs only a **subtomogram-average reference, not an atomic model** — so we DID run it standalone. Required porting farneback3d off CUDA texture-refs for CUDA 13.2/sm_120 (`tomoflow/research.md` §2). Landscape unimodal → **misses the two phases** (k=3 two big classes CC 0.956). `tomoflow/results/` |
| I3 / ProTomo | ✅ | (native) | ✅ | ✅ | — | — | ✅ | 3.1.0 installed; 2-class run on 234 centered particles (438 edge filtered); CC=0.921; see `protomo/research.md` + session log |
| EMAN2 | ✅ | `eman2` | ✅ | ⬜ | ⬜ | ⬜ | ✅ | k=2 completed (PCA: 393 vs 279 particles). Workspace `~/src/eman2_project/`; outputs spt_cls01/02; research.md in `eman2/` + pcaScripts/. **Result: EMAN2 misses the two phases**—splits particles but not into pili vs flexed. Comprehensive pipeline docs + Qt/OpenGL Wayland display fix in research.md. **2026-06-05 (Eben): code improvements committed+pushed** — `patch_scripts.py` Patch 2 re-activates reference-based `mask.wedgefill` in `e2spt_pcasplit.py` active path (the `--nowedgefill` flag was a no-op since fill lived only in a commented-out real-space block); `run_pipeline.sh` now a NO-ALIGNMENT variant (particles pre-aligned at (0,0,0) → identity transforms, skip orientation search). Not yet rerun with these changes. |
| emClarity | ✅ | MCR R2019a | ⬜ (real data n/a) | — | — | — | — | **installed + GPU-verified on RTX 5080/sm_120** (1.5.3.11 + MCR R2019a; CUDA-10 kernels JIT to Blackwell via the 13.2 driver). **Cannot run on real T4P:** tilt-series pipeline, no path to ingest pre-extracted subtomos → **synthetic-data track only**. See `EMCLARITY.md` |
| PyTom | ✅ | `pytom_env` | ✅ | ✅ | ✅ | ⬜ | — | **FIXED (2026-06-05):** v2 cylindrical mask (r=13, h_pos=0, h_neg=25) + `-a` flag (FRM module absent — see memory). k=2: **440/232** (converged iter 5, class 1≈PEET ring_altered). k=3: **422/150/100** (iter 11). Results: `results/pytom_v2mask_k{2,3}.csv`; figures: `PyTom/figures_v2mask_k{2,3}/`. Previous failure was wrong mask (r=7.2 symmetric defaults). k=4 not yet run. |
| DISCA | ✅ | `disca` | ✅ `build_disca_input.py` | ✅ | ✅ | ✅ | ✅ | template-free unsupervised deep clustering (torch, native sm_120); k=2/3/4 → one dominant ~94% class + small noisy outliers — **missed the two real phases** (cf. Dynamo). `disca/research.md` + `disca/results/` |
| HEMNMA-3D | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| AC3D | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Implemented as part of PyTom, run with that one. |
| TomoNet | ❌ | — | ❌ | — | — | — | — | **evaluated, rejected** — IsoNet denoising only, no classification workflow built-in. Would require custom autoencoder training (see `TomoNet/research.md`), contrary to benchmark scope (out-of-box packages). Denoising as pre-processing could be explored separately if needed. |

## Datasets

- **Real — T4P:** 672 hand-picked, prealigned 80³ subtomograms (`STA/subtomos_mrc/`, gitignored).
  Alignment QC done (`alignment_review/`, `review_alignment.py`). **Expert ground truth (Stefano):
  two distinct pili-phase classes**, recovered by Dynamo — the reference split for the benchmark.
- **Synthetic — motor_easy (3-class flagellar motor, ~30 Å differences):** All 3 classes complete, **694 GT-aligned subtomos** (A=246, B=271, C=177). `merged_all_aln/` **rebuilt (2026-06-05)**. GT separability validated (template CC ARI=0.289). RELION v3 (GT-seeded+firstiter_cc) on 694 particles: ARI=0.380 iter 1 → 0.099 iter 2. PEET WMD-PCA ARI≈0 (uniform-wedge limitation). Scoring infra: `scripts/eval/`. Mask for classification: r=32 px, center=(48,38), 96³ box. `~/Research/synthetic_sta/motor_easy/production/`.

## Open Decisions (owner)

1. Synthetic scope — # particle types & classes. (Josh → confirm w/ Stefano)
2. Missing-wedge standardization across packages. (Stefano / Braxton)
3. ~~Discrete vs. continuous handling for T4P~~ **RESOLVED: discrete, two pili phases (Stefano).**
   Remaining: how to discretize continuous classifiers' outputs for comparison. (Stefano)
4. What to do with off-class / outlier particles. (Josh)
6. **Per-particle ground-truth labels for T4P (NEW, 2026-06-03):** Exact per-particle class assignments for real T4P are not yet available. Best available signal is structural consistency of class averages with published conformational states. Quantitative per-particle GT is an open scientific need for the real-data benchmark track. (Josh)
5. **Benchmarking framework choices (NEW, 2026-06-02):** five open Qs in `benchmarkIdeas.md` §11:
   - (1a) README pillar weights 35/25/20/20 OK given downstream-resolution priority, or explore 30/20/20/30?
   - (1b) Is Dynamo's two-phase split sturdy enough for numerical GT, or use qualitatively only?
   - (1c) Synthetic sweep budget for regime map — is Josh's track scoped for 3–5 dimensions?
   - (1d) Half-set FSC strategy: pose-locked feasible across packages, true gold-standard is not. OK with that?
   - (1e) Worth commit to "consensus minus soft-GT" analysis to surface cross-package consensus structures?
   (See `benchmarkIdeas.md` §11 for context.)

## People

Josh (primary) · Eben (partner, same repo, package setup + runs) · Stefano (postdoc, science/manuscript) · Braxton (PhD, guidance).
