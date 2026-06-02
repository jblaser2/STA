# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-02** by Eben (OPUS-TOMO completed: k=8 clusters, 20 epochs, 4 bugs patched in OPUS-ET) + Claude (Dynamo `dtutorial` cold-start MRA run completed + evaluated).

## Now / Next / Parked

- **GROUND TRUTH (Stefano consult, 2026-06-01):** this T4P dataset has **two distinct, obvious
  pili-phase classes**, and **Dynamo recovers them well** (`dynamo/`). So the matching one-dominant-
  ~94%-class results from **RELION, PyTom, Protomo, and DISCA are a shared FAILURE to separate the two
  known phases**, *not* a true null. This is a real benchmark signal: at our settings those four
  underperform Dynamo on real data with expert ground truth. Initial full pass through the packages is
  a good baseline; revisit parameters/sampling to chase the two-phase split.
- **Now:** **OPUS-TOMO complete** (2026-06-02): pipeline executed successfully, 20 epochs, k=8 clusters, reference volumes generated. **Discovered and patched 4 bugs in OPUS-ET** (CTF exponent NaN, HEALPix single-bin crash, `--split` requirement, dummy CTF path resolution). **Result: OPUS-TOMO also misses the two real phases**—generates 8 clusters but none cleanly separate pili vs. flexed states. Patches archived in `opusPatches/models.py` and `pose.py`. Earlier: TomoFlow unimodal (missed phases); DISCA one dominant ~94% class (missed phases); TomoNet rejected (denoising only).
- **Next:** (a) **Six packages miss the two phases** (RELION, PyTom, Protomo, DISCA, TomoFlow, OPUS-TOMO). Run final 3D-input classifiers: EMAN2 (env ready, owned by Eben); MDTOMO blocked by atomic-model requirement; AC3D (implemented as PyTom extension); skip others or check HEMNMA/Scipion3 path. (b) Once coverage complete: analyze cross-package agreement (ARI/NMI matrices) and compile Phase-I results. (c) Chase the two-phase split—use Dynamo's two-class labels as ground truth; rerun DISCA at 64³ with phase-aware mask/lowpass, test OF packages with phase-aware preprocessing. (d) **ETSimulations** synthetic ground-truth datasets (Josh) to prove each package *can* recover known phase differences.
- **Dynamo methodology side-track (2026-06-01/02, DONE):** explored Dynamo's `dtutorial` synthetic
  set (`dynamo/dynamo_outputs/ttest128_tutorial/`, 128 particles, 40³, 2 size-variant classes). PCA
  command-line walkthrough (headless CPU): perfect poses (`real.tbl`) → ARI 1.000; unaligned
  (`initial.tbl`, identity poses) → ARI 0.017 (chance) ⇒ **Dynamo PCA is post-alignment only**.
  Two-stage cold-start MRA project `mra_ttest128` (6 rounds/18 ites, `nref=2`) **ran to completion**
  (PCT installed 2026-06-02, unblocking it; IPT also installed + `dynamo_mollify` bug patched).
  Result: the **embedded MRA's own 2-class assignment COLLAPSED** (final ref col 34 = all 1s; col-22
  "64/64" is just passive carryover of the input GT labels — do not mistake for a recovered split).
  But cold-start **alignment** partly worked (shift err 4.93→2.06 vox; 63/128 within 20° of truth,
  bimodal), and **PCA on the MRA-aligned poses → ARI 0.878 / acc 0.969**, near the 1.0 ceiling.
  ⇒ on this synthetic set Dynamo's classification power = alignment quality + PCA, NOT the MRA
  class-swapping. Spectrum: `initial` 0.017 | cold-start 0.878 | `real` 1.000. See session-log
  `2026-06-01-dynamo-dtutorial-pca-mra.md`.
- **Parked (need expert input):** missing-wedge standardization; how to discretize continuous-
  classifier outputs. (Discrete-vs-continuous is **resolved: discrete, two phases**.) → Stefano / Braxton.

## Package Matrix (15 packages, 3D-input classifiers)

Legend: ✅ done · 🟡 in progress · ⬜ not started · ❌ skip · — n/a/unknown

| Package | Installed | Env | Data-prep | k=2 | k=3 | k=4 | Pushed | Notes / blockers |
|---|---|---|---|---|---|---|---|---|
| RELION 3.1–4.0 | ✅ | `relion-5.0` | ✅ `build_relion_star.py` | ✅ | ✅ | ✅ | — | classic 3D-subtomo path **retained in RELION 5** `relion_refine` (no 3.1 build needed); k=2/3/4 × wedge/uniform run; no discrete split (CC 0.97–0.997); see `RELION.md` §9 |
| STOPGAP | 🟡 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; scripts/binaries in `stopgap/` |
| OPUS-TOMO | ✅ | opuset (conda -> python)| ✅ | ✅ | ✅ | ✅ | — | k=8 clusters, 20 epochs; 4 bugs patched (CTF exponent NaN, HEALPix single-bin crash, `--split` requirement, dummy CTF path); reference volumes generated; `opusPatches/` holds fixes for OPUS-ET code. **Result: generates multiple ~40-50kDa classes, structured heterogeneity captured.** |
| Dynamo | ✅ | MATLAB | ✅ | ✅ | — | — | — | **reference result**: recovers the two distinct pili-phase classes well (Josh + Stefano) → the ground-truth split other packages are measured against; workspace in `dynamo/`, `DYNAMO.md` |
| PEET | ✅ | IMOD | ✅ | — | — | — | ✅ | clusterPca + central-slice figures committed |
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
