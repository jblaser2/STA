# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-05-29** by Claude (Protomo session).

## Now / Next / Parked

- **Now:** Protomo (I3) initial classification done. Two classes found; inter-class CC = 0.921
  (very similar). See session log for full interpretation.
- **Next:** (a) Consult Stefano on whether T4P shows discrete heterogeneity at all — both PyTom
  and Protomo found near-identical class averages; (b) try k=3/k=4 in Protomo; (c) ETSimulations
  synthetic data production; (d) RELION classification.
- **Parked (need expert input):** missing-wedge standardization; whether T4P is discrete vs.
  continuous heterogeneity; how to discretize continuous-classifier outputs. → Stefano / Braxton.

## Package Matrix (15 packages, 3D-input classifiers)

Legend: ✅ done · 🟡 in progress · ⬜ not started · — n/a/unknown

| Package | Installed | Env | Data-prep | k=2 | k=3 | k=4 | Pushed | Notes / blockers |
|---|---|---|---|---|---|---|---|---|
| RELION 3.1–4.0 | 🟡 | `relion-5.0` | 🟡 `prepare_relion.sh` | ⬜ | ⬜ | ⬜ | — | env present; classification not run yet |
| STOPGAP | 🟡 | — | ⬜ | ⬜ | ⬜ | ⬜ | — | scripts/binaries in `stopgap/`; setup in progress |
| OPUS-TOMO | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| Dynamo | 🟡 | MATLAB | ⬜ | ⬜ | ⬜ | ⬜ | — | workspace in `dynamo/`; `DYNAMO.md` guide |
| PEET | ✅ | IMOD | ✅ | — | — | — | ✅ | clusterPca + central-slice figures committed |
| MDTOMO | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| TomoFlow | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
| I3 / ProTomo | ✅ | (native) | ✅ | ✅ | — | — | ✅ | 3.1.0 installed; 2-class run on 234 centered particles (438 edge filtered); CC=0.921; see `protomo/research.md` + session log |
| EMAN2 | 🟡 | `eman2` | ⬜ | ⬜ | ⬜ | ⬜ | — | env + workspace ready; `EMAN2.md` |
| emClarity | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | `EMCLARITY.md` notes only; not installed |
| PyTom | ✅ | `pytom_env` | ✅ | ✅ | ✅ | ⬜ | ✅ | **blocker:** k=2 & k=3 averages look identical — classification not separating structure |
| DISCA | ⬜ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | not started |
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
