# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-01** by Claude (emClarity + DISCA session; DISCA docs not yet committed).

## Now / Next / Parked

- **Now:** **DISCA done** — template-free unsupervised deep clustering (the most method-independent
  package yet) selects, by its own DDBI validity index, **one dominant ~94% class + small noisy
  outliers** at k=2/3/4 → the **same null** as RELION/PyTom/Protomo. **Four packages now converge on
  "no strong discrete heterogeneity in T4P."** See `DISCA.md` §7 + `outputs/disca/results/`.
- **Also this session:** emClarity installed + GPU-verified on the RTX 5080 (CUDA-10 kernels JIT to
  sm_120), but it's a tilt-series pipeline → **can't classify the real T4P set**, synthetic-track only
  (`EMCLARITY.md`).
- **Next:** **Consult Stefano** — the four-package convergent null makes "is T4P discrete at all?" the
  gating question; then **ETSimulations** synthetic ground-truth datasets (unblocks emClarity +
  RELION-modern AND distinguishes "no real classes" from "can't find them," incl. DISCA's coarse-32³ blind spot).
- **Next:** (a) **Consult Stefano** — the convergent null across PyTom/Protomo/RELION makes "is T4P
  discrete at all?" the gating question; (b) **ETSimulations** synthetic ground-truth datasets
  (needed to distinguish "no real classes" from "can't find them"); (c) continue package coverage.
- **Parked (need expert input):** missing-wedge standardization; whether T4P is discrete vs.
  continuous heterogeneity; how to discretize continuous-classifier outputs. → Stefano / Braxton.

## Package Matrix (15 packages, 3D-input classifiers)

Legend: ✅ done · 🟡 in progress · ⬜ not started · — n/a/unknown

| Package | Installed | Env | Data-prep | k=2 | k=3 | k=4 | Pushed | Notes / blockers |
|---|---|---|---|---|---|---|---|---|
| RELION 3.1–4.0 | ✅ | `relion-5.0` | ✅ `build_relion_star.py` | ✅ | ✅ | ✅ | — | classic 3D-subtomo path **retained in RELION 5** `relion_refine` (no 3.1 build needed); k=2/3/4 × wedge/uniform run; no discrete split (CC 0.97–0.997); see `RELION.md` §9 |
| STOPGAP | 🟡 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; scripts/binaries in `stopgap/` |
| OPUS-TOMO | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| Dynamo | ✅ | MATLAB | ✅ | ✅ | — | — | — | classification run on subtomos, decent results (Josh); workspace in `dynamo/`, `DYNAMO.md` |
| PEET | ✅ | IMOD | ✅ | — | — | — | ✅ | clusterPca + central-slice figures committed |
| MDTOMO | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| TomoFlow | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| I3 / ProTomo | ✅ | (native) | ✅ | ✅ | — | — | ✅ | 3.1.0 installed; 2-class run on 234 centered particles (438 edge filtered); CC=0.921; see `protomo/research.md` + session log |
| EMAN2 | 🟡 | `eman2` | ⬜ | ⬜ | ⬜ | ⬜ | — | **owned by Eben**; env + workspace ready; `EMAN2.md` |
| emClarity | ✅ | MCR R2019a | ⬜ (real data n/a) | — | — | — | — | **installed + GPU-verified on RTX 5080/sm_120** (1.5.3.11 + MCR R2019a; CUDA-10 kernels JIT to Blackwell via the 13.2 driver). **Cannot run on real T4P:** tilt-series pipeline, no path to ingest pre-extracted subtomos → **synthetic-data track only**. See `EMCLARITY.md` |
| PyTom | ✅ | `pytom_env` | ✅ | ✅ | ✅ | ⬜ | ✅ | **blocker:** k=2 & k=3 averages look identical — classification not separating structure |
| DISCA | ✅ | `disca` | ✅ `build_disca_input.py` | ✅ | ✅ | ✅ | — | template-free unsupervised deep clustering (torch, native sm_120); k=2/3/4 run; best-DDBI = one dominant ~94% class + small noisy outliers → **same null** as RELION/PyTom/Protomo. See `DISCA.md` §7 |
| HEMNMA-3D | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| AC3D | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| TomoNet | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |

## Datasets

- **Real — T4P:** 672 hand-picked, prealigned 80³ subtomograms (`STA/subtomos_mrc/`, gitignored).
  Alignment QC done (`alignment_review/`, `review_alignment.py`). No reliable ground truth.
- **Synthetic — planned:** 3-class & 4-class conformational sets, ~30 Å and ~10 Å class
  differences, matched SNR, simulated missing wedge, imbalanced sizes. Tooling: **ETSimulations**
  ✅ installed & validated (`nora_test` run). Production datasets not yet generated.

## Open Decisions (owner)

1. Synthetic scope — # particle types & classes. (Josh → confirm w/ Stefano)
2. Missing-wedge standardization across packages. (Stefano / Braxton)
3. Discrete vs. continuous handling for T4P; how to discretize continuous classifiers. (Stefano)
4. What to do with off-class / outlier particles. (Josh)

## People

Josh (primary) · Eben (partner, same repo, package setup + runs) · Stefano (postdoc, science/manuscript) · Braxton (PhD, guidance).
