# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-04** by Claude (class B expanded to 271 particles; mask sized; ETSim pipeline bugs fixed).

## Now / Next / Parked

- **README OVERHAUL COMPLETE (2026-06-04):** Complete rewrite of `README.md`: corrected SPA description, updated to 4 planned datasets, added T4P classes as lower periplasmic ring conformational states (cites Stefano's bioRxiv preprint), replaced PEET diff figure with v2, generated `motor_easy_classA_avg.png` from MRC, added `motor_easy_class_maps.png` showing all 3 input density maps, updated synthetic section to show class A/C averages (not B/C), honest UMAP caption, PEET added as second "converging" package in preliminary findings, team section updated (Recent Graduates, Gus Hart added as advisor). `etsimulation/figures/` directory created with 6 PNG figures.

- **SYNTHETIC DATA — SCORING FRAMEWORK COMPLETE (2026-06-04):** Scoring infrastructure built: `scripts/eval/score_synthetic.py` (ARI/AMI/V/Acc + confusion PNG), `scripts/eval/extract_relion_classes.py`, `scripts/eval/extract_peet_classes.py`, `peet/kmeans_motor_easy.py`. All scores appended to `results/synthetic_scores.csv`. **Missing-wedge decision:** feed GT-aligned particles (`merged_all_aln/`) with identity starting poses + tilt range ±60°; let each package apply its own native wedge correction. Template-matching baseline ARI=0.289 (structural signal confirmed present).

- **SYNTHETIC DATA — FIRST PACKAGE RUNS COMPLETE (2026-06-04):** RELION and PEET both run on motor_easy; both score ARI≈0. RELION k=2: ARI=0.005, k=3: ARI=0.006. PEET WMD-PCA k=2: ARI≈0, k=3: ARI≈0. **Interpretation:** (1) RELION `--skip_align` with global-average reference doesn't find classes from cold start — need next step: run WITHOUT `--skip_align` to let alignment help differentiate. (2) PEET WMD-PCA fails for same reason as real T4P: all GT-aligned particles share the same wedge direction (uniform wedge), so WMD correction degrades to masking the same Fourier region. Known limitation. **PEET quirk:** Iter2 MOTL needs CCC=0.5 (not 0) for particles to be included — bug/design in PEET (CCC=0 causes particles to be skipped). Motor_easy PEET scripts: `peet/motor_easy.prm`, `peet/motor_easy_stack.py`, `peet/kmeans_motor_easy.py`. Runs: `outputs/relion_motor_easy/`, `outputs/peet_motor_easy/`. **Next: run RELION without `--skip_align` on motor_easy to give it fair chance; then Dynamo (blocked on MATLAB PCT install).**

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
| PEET | ✅ | IMOD | ✅ | ✅ | — | — | ✅ | Two runs complete (2026-06-04). **v1** (cyl r=11.2): 388/216/68. **v2** (cyl r=13, below-center): 374/230/68, AIC=659. Labels: ring_complete/ring_altered/junk. CSVs + figures in `peet/results/`. Cylindrical mask → include PC1 (structural signal). Still need Stefano's MOTL for exact GT. |
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
- **Synthetic — motor_easy (3-class flagellar motor, ~30 Å differences):** All 3 classes complete, **694 GT-aligned subtomos** (A=246, B=271, C=177). `merged_all_aln/` **not yet rebuilt** (still has 634 particles — run `align_all_classes.py` before next package runs). GT separability validated (template CC ARI=0.289). First benchmark runs on old 634-particle set: RELION ARI≈0.005, PEET WMD-PCA ARI≈0 (both miss classes — expected for these settings). Scoring infra: `scripts/eval/`. Mask for classification: r=32 px, center=(48,38), 96³ box. `~/Research/synthetic_sta/motor_easy/production/`.

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
