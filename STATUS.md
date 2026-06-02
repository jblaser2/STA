# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-02** by Claude (TomoNet evaluation: rejected, not suitable for out-of-box benchmark)

## Now / Next / Parked

- **GROUND TRUTH (Stefano consult, 2026-06-01):** this T4P dataset has **two distinct, obvious
  pili-phase classes**, and **Dynamo recovers them well** (`dynamo/`). So the matching one-dominant-
  ~94%-class results from **RELION, PyTom, Protomo, and DISCA are a shared FAILURE to separate the two
  known phases**, *not* a true null. This is a real benchmark signal: at our settings those four
  underperform Dynamo on real data with expert ground truth. Initial full pass through the packages is
  a good baseline; revisit parameters/sampling to chase the two-phase split.
- **Now:** **TomoFlow done** (env `tomoflow`; required porting `farneback3d`'s CUDA kernels off the
  removed texture-reference API to run on CUDA 13.2 / sm_120 — see `tomoflow/research.md` §2).
  Continuous OF landscape is **unimodal** → at k=3 the two large clusters (n=252, 391) are the SAME
  pilus (CC 0.956) → TomoFlow **also misses the two phases**. **Five packages now miss the split
  (RELION, PyTom, Protomo, DISCA, TomoFlow) vs Dynamo recovering it.** Earlier same session: DISCA
  done (`disca/`); emClarity installed + GPU-verified but tilt-series-only → synthetic-track
  (`EMCLARITY.md`). **TomoNet evaluated (2026-06-02) and rejected:** IsoNet-based denoising only;
  would require custom autoencoder training, contrary to benchmark scope (out-of-box packages).
- **Next:** (a) **continue package coverage** — next 3D-input classifier (e.g. MDTOMO, OPUS-TOMO);
  (b) chase the two-phase split using Dynamo's labels as reference (DISCA at 64³; phase-aware
  mask/lowpass for the alignment + OF packages); (c) **ETSimulations** synthetic ground-truth sets
  (Josh, separate chat) to confirm each package *can* separate a known phase difference.
- **Dynamo methodology side-track (2026-06-01):** explored Dynamo's `dtutorial` synthetic set
  (`dynamo/dynamo_outputs/ttest128_tutorial/`, 128 particles, 40³, 2 size-variant classes). PCA
  command-line walkthrough validated headless on CPU: perfect poses (`real.tbl`) → ARI 1.000;
  unaligned (`initial.tbl`, all-zero poses) → ARI 0.017 (chance) ⇒ **Dynamo PCA is post-alignment
  only**. Two-stage MRA project `mra_ttest128` set up + validated. **BLOCKED:** in-MATLAB Dynamo
  execution needs **Parallel Computing Toolbox** (licensed, not installed) — install it, then
  `run_mra.m` runs as-is. (Also installed Image Processing Toolbox this session + patched a
  `dynamo_mollify` IPT bug.) See session-log `2026-06-01-dynamo-dtutorial-pca-mra.md`.
- **Parked (need expert input):** missing-wedge standardization; how to discretize continuous-
  classifier outputs. (Discrete-vs-continuous is **resolved: discrete, two phases**.) → Stefano / Braxton.

## Package Matrix (15 packages, 3D-input classifiers)

Legend: ✅ done · 🟡 in progress · ⬜ not started · ❌ skip · — n/a/unknown

| Package | Installed | Env | Data-prep | k=2 | k=3 | k=4 | Pushed | Notes / blockers |
|---|---|---|---|---|---|---|---|---|
| RELION 3.1–4.0 | ✅ | `relion-5.0` | ✅ `build_relion_star.py` | ✅ | ✅ | ✅ | — | classic 3D-subtomo path **retained in RELION 5** `relion_refine` (no 3.1 build needed); k=2/3/4 × wedge/uniform run; no discrete split (CC 0.97–0.997); see `RELION.md` §9 |
| STOPGAP | 🟡 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; scripts/binaries in `stopgap/` |
| OPUS-TOMO | 🟡 | opuset (conda -> python)| ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| Dynamo | ✅ | MATLAB | ✅ | ✅ | — | — | — | **reference result**: recovers the two distinct pili-phase classes well (Josh + Stefano) → the ground-truth split other packages are measured against; workspace in `dynamo/`, `DYNAMO.md` |
| PEET | ✅ | IMOD | ✅ | — | — | — | ✅ | clusterPca + central-slice figures committed |
| MDTOMO | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| TomoFlow | ✅ | `tomoflow` | ✅ `tomoflow_run.py` | ✅ | ✅ | ✅ | — | also ContinuousFlex, but (unlike MDTOMO/HEMNMA) needs only a **subtomogram-average reference, not an atomic model** — so we DID run it standalone. Required porting farneback3d off CUDA texture-refs for CUDA 13.2/sm_120 (`tomoflow/research.md` §2). Landscape unimodal → **misses the two phases** (k=3 two big classes CC 0.956). `tomoflow/results/` |
| I3 / ProTomo | ✅ | (native) | ✅ | ✅ | — | — | ✅ | 3.1.0 installed; 2-class run on 234 centered particles (438 edge filtered); CC=0.921; see `protomo/research.md` + session log |
| EMAN2 | ✅ | `eman2` | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; env + workspace ready; `EMAN2.md` |
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
- **Synthetic — planned:** 3-class & 4-class conformational sets, ~30 Å and ~10 Å class
  differences, matched SNR, simulated missing wedge, imbalanced sizes. Tooling: **ETSimulations**
  ✅ installed & validated (`nora_test` run). Production datasets not yet generated.

## Open Decisions (owner)

1. Synthetic scope — # particle types & classes. (Josh → confirm w/ Stefano)
2. Missing-wedge standardization across packages. (Stefano / Braxton)
3. ~~Discrete vs. continuous handling for T4P~~ **RESOLVED: discrete, two pili phases (Stefano).**
   Remaining: how to discretize continuous classifiers' outputs for comparison. (Stefano)
4. What to do with off-class / outlier particles. (Josh)

## People

Josh (primary) · Eben (partner, same repo, package setup + runs) · Stefano (postdoc, science/manuscript) · Braxton (PhD, guidance).
