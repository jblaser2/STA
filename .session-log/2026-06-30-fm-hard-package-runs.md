# Session Log — 2026-06-30: FM_hard Package Runs (ALL 10 COMPLETE)

## What was accomplished

Ran all 10 benchmark packages on FM_hard (813p assembly-intermediate dataset:
base/basal_body/mature, 96³, k=3, no junk, diff_mask_hard.mrc). All 10 complete.

### Final results table (10/10)

| Package   | k=3 ARI | Split       | Notes |
|-----------|---------|-------------|-------|
| **TomoFlow** | **0.223** | 313/400/100 | **BEST** — optical flow partially immune to registration wall; 2.4h compute |
| PEET      | 0.078   | varied      | pc1_5; best among PCA/alignment methods; near blind baseline 0.07 |
| OPUS-TOMO | 0.017   | collapsed   | VAE |
| PyTom     | 0.017   | 175/318/320 | FRM iter14 |
| DISCA     | 0.014   | varied      | 32³ CNN too coarse for ~15-20Å assembly differences |
| STOPGAP   | 0.013   | 240/260/313 | eigenfac PCA k-means |
| EMAN2     | 0.008   | collapsed   | PCA split |
| RELION    | 0.000   | 0/813/0     | soft-EM; all class 2 |
| Dynamo    | -0.000  | collapsed   | dpkpca |
| ProTomo   | -0.001  | 1/710/102   | SVD+HAC collapsed |

Supervised ceiling: 0.472. Blind baseline: ~0.07.

## Key findings

1. **Registration wall confirmed on ALL 9 PCA/alignment packages.** No alignment-based method
   breaks the blind baseline (0.07). Even DISCA (CNN, immune to registration wall on T3SS motor_switch)
   collapses here — assembly intermediate differences (~15-20Å P-ring addition) are too subtle
   for a 32³ CNN trained on gross morphology. This is the third synthetic dataset in a row
   confirming this wall.

2. **TomoFlow breaks the wall (ARI=0.223).** Optical flow computes pairwise volume deformation
   fields directly, without a pre-registration SVD step. This makes it structurally different
   from all other packages and partially immune to the registration wall that collapses the
   eigenspectrum-based approaches. First clear method-level exception found.

3. **Supervised ceiling 0.472 confirms the task IS learnable** — the structural signal is real,
   just unrecoverable by current alignment-first approaches. TomoFlow recovers ~47% of the
   achievable ARI (0.223/0.472).

## Script bugs found and fixed

1. **Dynamo eigencomponents shape:** E is [813×50] (particles×eigenvectors), not [50×813];
   `nc = min(17, size(E,2)); X = E(:, 1:nc)` (fixed in dynamo_fm_hard_pca.m).

2. **STOPGAP parser:** FM_hard script used `stopgap_pca_parser.sh` (doesn't exist) and
   `wedge_name wedgelist` (wrong param name). Fixed to:
   - `stopgap_parser.sh pca` (the correct binary path)
   - `wedgelist_name wedgelist.star` (correct T4P-validated param name)

3. **ProTomo — five bugs:**
   - `save dataset.i3i` not bare `save` in dataset.prep
   - `conda: command not found` after protomo setup.sh clobbers PATH → use `~/miniforge3/bin/conda`
   - `mkdir -p cycle-000` before subvolinitial.sh → cycle-000/param.sh not found → removed pre-mkdir
   - `CLSMIN/CLSMAX/CLSINC` missing from param-template.sh → added =3/3/1 for k=3 HAC
   - mask_diff.i3i not created (setup failed before mask step) → manually ran `i3cut` direct (no -slice flag)

4. **ProTomo SVD SIGSEGV:** Crashed because mask_diff.i3i was missing; tomoclass read
   813×884736 full volume → segfault. With mask: 813×27896 matrix → success.

5. **PyTom scoring sort:** glob lexicographic sort used iter9 as "final" (iter10>iter9 alphabetically).
   Fixed to numeric sort via `re.search(r'iter(\d+)')`.

6. **ProTomo scoring args:** extract_protomo_classes.py uses --i3i/--stacks/--out flags, not positional.

7. **i3cut -slice flag doesn't exist:** correct usage is `i3cut "$TMPFILE" "$PREPARE/mask_diff.i3i"` directly.

## Commits this session

- `8ac4a60` — FM_hard: all 10 package scripts + 6 completed results
- `d7f16c7` — ProTomo FM_hard: ARI=-0.001 + script fixes
- `88b8e53` — packages/README.md FM_hard table with 7 results
- `fcee1ab` — PyTom FM_hard: ARI=0.017
- `8afb15f` — STATUS.md, packages/README.md, session handoff log (8/10 done)
- `069e1c4` — STOPGAP FM_hard: ARI=0.013
- `36441d1` — TomoFlow FM_hard CSV committed
- (this commit) — FM_hard 10/10 complete: TomoFlow ARI=0.223, STATUS.md, README.md, session log

## Next session options

1. **Class-average figures for FM_hard** — generate PNG panels for all 10 packages;
   update packages/README.md gallery cells (currently _(pending)_)
2. **TomoFlow deep-dive** — investigate why optical flow succeeds; check if aligning
   particles first and re-running PEET/DISCA with better poses closes the gap
3. **T3SS injectisome dataset** — per plan in `.claude/plans/logical-purring-pretzel.md`;
   adds structural diversity to the benchmark; EMD-8544; AMP calibration may need 1.5 (not 0.1);
   see memory: etsim-t3ss-amp-calibration.md
4. **Write manuscript section** — FM_hard registration wall finding is publication-ready;
   draft "Registration as the critical bottleneck" section with the 10-package result table
