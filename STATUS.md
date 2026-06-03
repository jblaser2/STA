# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-03** by Josh (motor_easy class A: 246 subtomos extracted, GT-aligned average checkpoint passed; pipeline_quirks.md committed to repo).

## Now / Next / Parked

- **SYNTHETIC DATA — motor_easy class A DONE, B+C pending (2026-06-03):** Class A: 7 runs × ~35 particles = **246 subtomos extracted** to `production/subtomos/merged_A/`; GT-aligned average computed + opened in 3dmod — checkpoint passed. Class B (6 runs) and Class C (5 runs): simulations, reconstructions, and extraction **not yet started**. After B+C: merge all three into one `labels.csv` → quick PCA k-means at k=3 to validate ground-truth separability. Production layout: `~/Research/synthetic_sta/motor_easy/production/`. Pipeline quirks documented in `STA/etsimulation/pipeline_quirks.md`.

- **PEET GROUND-TRUTH REPRODUCTION (2026-06-03, in progress):** Goal: reproduce Stefano's PEET 5:1 (509:95) per-particle class labels to know which subtomo is which. Added `tiltRange={[-60,60]}` + `flgWedgeWeight=1` to prm, reran WMD PCA, swept 14 k-means + 8 HAC configurations. Best k-means result: **412:260 (1.58:1) with PCs 1:3** — visually closer to paper per 3dmod inspection. HAC degenerates to 671:1. Root cause of 5:1 mismatch: pre-aligned particles all share the same wedge direction so WMD correction degrades to masking the same Fourier region for all particles; can't replicate Stefano's per-particle tilt geometry. **Next: ask Stefano for his PEET MOTL files (per-particle class labels)**, or accept 412:260 as proxy ground truth. Class averages: `~/Research/peet/results/winner_class_{1,2}_avg.mrc`. Sweep scripts: `run_pca_sweep.sh`, `post_sweep.py` (in results/).

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

- **GROUND TRUTH (Stefano consult, 2026-06-01):** this T4P dataset has **two distinct, obvious
  pili-phase classes**, and **Dynamo recovers them well** (`dynamo/`). So the matching one-dominant-
  ~94%-class results from **RELION, PyTom, Protomo, DISCA, TomoFlow, OPUS-TOMO are a shared FAILURE** to separate the two
  known phases, *not* a true null. Benchmark signal: at our settings those six underperform Dynamo on real data with expert ground truth.

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
| RELION 3.1–4.0 | ✅ | `relion-5.0` | ✅ `build_relion_star.py` | ✅ | ✅ | ✅ | — | classic 3D-subtomo path **retained in RELION 5** `relion_refine` (no 3.1 build needed); k=2/3/4 × wedge/uniform run; no discrete split (CC 0.97–0.997); see `RELION.md` §9 |
| STOPGAP | 🟡 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; scripts + compiled R2023b binaries in `stopgap/`; 6-iter optimized schedule designed (§1–§6 in research.md, ~13–15× speedup); `check_crashes.m` edited (abort on first crash, in `editedSTOPGAPfiles/`); bash-layer `run_watcher_guarded` described in research.md §7 but **not yet added to `runClassification.sh`**; next: add crash guard → run `createStopgapInputs.m` → `subtomoParams.sh` → `sbatch runClassification.sh` |
| OPUS-TOMO | ✅ | opuset (conda -> python)| ✅ | ✅ | ✅ | ✅ | — | k=8 clusters, 20 epochs; 4 bugs patched (CTF exponent NaN, HEALPix single-bin crash, `--split` requirement, dummy CTF path); reference volumes generated; `opusPatches/` holds fixes for OPUS-ET code. **Result: generates multiple ~40-50kDa classes, structured heterogeneity captured.** |
| Dynamo | ✅ | MATLAB | ✅ | ✅ | — | — | — | **reference result**: recovers the two distinct pili-phase classes well (Josh + Stefano) → the ground-truth split other packages are measured against; workspace in `dynamo/`, `DYNAMO.md` |
| PEET | ✅ | IMOD | ✅ | 🟡 | — | — | ✅ | WMD PCA rerun with ±60° tilt range (2026-06-03). Best k-means k=2: 412:260 (1.58:1, PCs 1:3) — visually closer to paper. Cannot reproduce paper's 5:1 from pre-aligned stack (uniform wedge → WMD degrades). Need Stefano's MOTL for exact ground-truth labels. Sweep + class avg scripts in `~/Research/peet/results/`. |
| MDTOMO | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| TomoFlow | ✅ | `tomoflow` | ✅ `tomoflow_run.py` | ✅ | ✅ | ✅ | — | also ContinuousFlex, but (unlike MDTOMO/HEMNMA) needs only a **subtomogram-average reference, not an atomic model** — so we DID run it standalone. Required porting farneback3d off CUDA texture-refs for CUDA 13.2/sm_120 (`tomoflow/research.md` §2). Landscape unimodal → **misses the two phases** (k=3 two big classes CC 0.956). `tomoflow/results/` |
| I3 / ProTomo | ✅ | (native) | ✅ | ✅ | — | — | ✅ | 3.1.0 installed; 2-class run on 234 centered particles (438 edge filtered); CC=0.921; see `protomo/research.md` + session log |
| EMAN2 | ✅ | `eman2` | ✅ | ⬜ | ⬜ | ⬜ | — | k=2 completed (PCA: 393 vs 279 particles). Workspace `~/src/eman2_project/`; outputs spt_cls01/02; research.md in `eman2/` + pcaScripts/. **Result: EMAN2 misses the two phases**—splits particles but not into pili vs flexed. Comprehensive pipeline docs + Qt/OpenGL Wayland display fix in research.md. |
| emClarity | ✅ | MCR R2019a | ⬜ (real data n/a) | — | — | — | — | **installed + GPU-verified on RTX 5080/sm_120** (1.5.3.11 + MCR R2019a; CUDA-10 kernels JIT to Blackwell via the 13.2 driver). **Cannot run on real T4P:** tilt-series pipeline, no path to ingest pre-extracted subtomos → **synthetic-data track only**. See `EMCLARITY.md` |
| PyTom | ✅ | `pytom_env` | ✅ | ✅ | ✅ | ⬜ | ✅ | **blocker:** k=2 & k=3 averages look identical — classification not separating structure |
| DISCA | ✅ | `disca` | ✅ `build_disca_input.py` | ✅ | ✅ | ✅ | ✅ | template-free unsupervised deep clustering (torch, native sm_120); k=2/3/4 → one dominant ~94% class + small noisy outliers — **missed the two real phases** (cf. Dynamo). `disca/research.md` + `disca/results/` |
| HEMNMA-3D | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| AC3D | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Implemented as part of PyTom, run with that one. |
| TomoNet | ❌ | — | ❌ | — | — | — | — | **evaluated, rejected** — IsoNet denoising only, no classification workflow built-in. Would require custom autoencoder training (see `TomoNet/research.md`), contrary to benchmark scope (out-of-box packages). Denoising as pre-processing could be explored separately if needed. |

## Datasets

- **Real — T4P:** 672 hand-picked, prealigned 80³ subtomograms (`STA/subtomos_mrc/`, gitignored).
  Alignment QC done (`alignment_review/`, `review_alignment.py`). **Expert ground truth (Stefano):
  two distinct pili-phase classes**, recovered by Dynamo — the reference split for the benchmark.
- **Synthetic — motor_easy (3-class flagellar motor, ~30 Å differences):** Class A complete (246 subtomos, GT-aligned average validated). Classes B+C pending. `~/Research/synthetic_sta/motor_easy/production/`. Pipeline quirks: `STA/etsimulation/pipeline_quirks.md`.

## Open Decisions (owner)

1. Synthetic scope — # particle types & classes. (Josh → confirm w/ Stefano)
2. Missing-wedge standardization across packages. (Stefano / Braxton)
3. ~~Discrete vs. continuous handling for T4P~~ **RESOLVED: discrete, two pili phases (Stefano).**
   Remaining: how to discretize continuous classifiers' outputs for comparison. (Stefano)
4. What to do with off-class / outlier particles. (Josh)
6. **Per-particle ground-truth labels for T4P (NEW, 2026-06-03):** Stefano's PEET MOTL files would give exact class assignment per subtomogram. Without them, best available proxy is Dynamo HAC (447:225) confirmed visually by Stefano. Email Stefano for MOTL. (Josh)
5. **Benchmarking framework choices (NEW, 2026-06-02):** five open Qs in `benchmarkIdeas.md` §11:
   - (1a) README pillar weights 35/25/20/20 OK given downstream-resolution priority, or explore 30/20/20/30?
   - (1b) Is Dynamo's two-phase split sturdy enough for numerical GT, or use qualitatively only?
   - (1c) Synthetic sweep budget for regime map — is Josh's track scoped for 3–5 dimensions?
   - (1d) Half-set FSC strategy: pose-locked feasible across packages, true gold-standard is not. OK with that?
   - (1e) Worth commit to "consensus minus soft-GT" analysis to surface cross-package consensus structures?
   (See `benchmarkIdeas.md` §11 for context.)

## People

Josh (primary) · Eben (partner, same repo, package setup + runs) · Stefano (postdoc, science/manuscript) · Braxton (PhD, guidance).
