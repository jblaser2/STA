# 2026-06-15 — ProTomo + EMAN2 on FM_easy (motor_easy)

**Goal:** Continue the FM_easy package sweep. Run the next unrun packages on motor_easy
(after DISCA earlier same day): ProTomo, then EMAN2. Both at k=3, no junk, right-size mask.

**What happened:**

*ProTomo (I3) — ARI=−0.003, split 517/103/74.* SVD+HAC collapse to one dominant cluster;
GT class C 174/0/3 → almost all in cluster 0. Misses the 3-class structure (contrast with T4P,
which separated 2 phases). Significant pipeline-build debugging (all now documented):
- The subtomo *series* `dataset.i3i` must be built with **`tomoprepare`** (the `attach`/`search`/`save`
  `.prep`), NOT `tomoprocess` (docs were wrong — no `attach` command) and NOT `i3concat` (makes a 4D
  *hypervolume* that `tomoclass` reads as a single image → "1 by N data matrix").
- `tomoclass dataset` rejects absolute paths; `MSAMASK` accepts them.
- "No junk" = leave `CLSHVO`/`CLSHVM` **empty** (not `0` — `hacoptions 0 0` errors).
- `cycle-000/param.sh` is copied at init and overrides `param-template.sh` edits — sync both.
- Mask applied via SVD: `MSAIMGSIZE=96 96 96` (full box) + `MSAMASK=mask96.i3i` (canonical FM_easy
  solvent sphere converted with `i3preproc`).

*EMAN2 — ARI=−0.0015, split 81/94/519.* No-align PCA split (`e2spt_pcasplit`), k=3 no junk
(dropped `--clean`, which adds an NCLASS+1 outlier class), NBASIS=12, MAXRES=40 Å (finer than T4P's
60 to resolve ~30 Å diffs), auto-tight mask. Collapses to dominant cluster (519); GT class C 0/0/177
entirely inside it. Same contrast-axis PCA failure as T4P, now on data with GT. Env at
`~/conda-envs/eman2` (not `~/miniforge3/envs`).

**Cross-package pattern:** FM_easy now 8/10 (RELION 0.475 GT / Dynamo 0.200 / PyTom 0.134 /
PEET 0.116 / DISCA 0.036 / OPUS 0.021 / ProTomo −0.003 / EMAN2 −0.002). Only GT-seeded RELION and
Dynamo dpkpca find signal; everything else collapses or splits on a non-conformational axis, and the
dominant cluster consistently swallows all of class C (ProTomo/EMAN2/OPUS).

**Files changed:**
- ProTomo: `packages/protomo/{README,research}.md`, `outputs/FM_easy/protomo/`,
  local workspace `~/Research/protomo/motor_easy/` (not committed).
- EMAN2: `packages/eman2/README.md`, `outputs/FM_easy/eman2/`,
  local project `~/Research/eman2_motor_easy/` (not committed).
- `STATUS.md`, `packages/README.md`, `results/synthetic_scores.csv`.
- Commits: `dccbc10` (DISCA+ProTomo FM_easy + Dynamo FM_switch), `cfede02` (EMAN2 FM_easy).

**Where I stopped:** ProTomo + EMAN2 complete, documented, committed. Pushing this session.

**Next step:** Remaining FM_easy packages: **TomoFlow, STOPGAP**. (STOPGAP owned by Eben.)
