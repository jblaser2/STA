# Session Log — 2026-06-30: FM_hard Package Runs

## What was accomplished

Ran all 10 benchmark packages on FM_hard (813p assembly-intermediate dataset:
base/basal_body/mature, 96³, k=3, no junk, diff_mask_hard.mrc). 8/10 complete by end of session.

### Results table (8/10 done)

| Package | k=3 ARI | Split | Notes |
|---------|---------|-------|-------|
| PEET    | 0.078   | varied | pc1_5; best among completed; near blind baseline 0.07 |
| DISCA   | 0.014   | varied | 32³ CNN too coarse for ~15-20Å assembly differences |
| Dynamo  | -0.000  | collapsed | dpkpca; registration wall |
| EMAN2   | 0.008   | collapsed | PCA split |
| OPUS-TOMO | 0.017 | collapsed | VAE |
| RELION  | 0.000   | 0/813/0 | soft-EM; all class 2 |
| ProTomo | -0.001  | 1/710/102 | SVD+HAC collapsed |
| PyTom   | 0.017   | 175/318/320 | FRM iter14 |
| STOPGAP | RUNNING | — | ccmatrix ~1.4h remaining at session end |
| TomoFlow | RUNNING | — | optical flow 150/813 vol, ~2h remaining |

**Key finding:** Registration wall confirmed on all 8 completed packages. Even DISCA (CNN,
immune to registration wall on T3SS) collapses here — assembly intermediate differences
(P-ring addition, ~15-20Å) are too subtle for a 32³ CNN trained on gross morphology.
Supervised ceiling 0.472 >> best blind 0.078 (PEET).

## Script bugs found and fixed

1. **Dynamo eigencomponents shape:** E is [813×50] (particles×eigenvectors), not [50×813];
   `nc = min(17, size(E,2)); X = E(:, 1:nc)` (fixed in dynamo_fm_hard_pca.m).

2. **STOPGAP parser:** FM_hard script used `stopgap_pca_parser.sh` (doesn't exist) and
   `wedge_name wedgelist` (wrong param name). Fixed to:
   - `stopgap_parser.sh pca` (the correct binary path)
   - `wedgelist_name wedgelist.star` (correct T4P-validated param name)

3. **ProTomo - four bugs:**
   - `save dataset.i3i` not bare `save` in dataset.prep
   - `conda: command not found` after protomo setup.sh clobbers PATH → use `~/miniforge3/bin/conda`
   - `mkdir -p cycle-000` before subvolinitial.sh → cycle-000/param.sh not found error → removed pre-mkdir
   - `CLSMIN/CLSMAX/CLSINC` missing from param-template.sh → added =3/3/1 for k=3 HAC
   - mask_diff.i3i not created (setup failed before mask step) → manually ran `i3cut` direct (no -slice flag)

4. **ProTomo SVD SIGSEGV:** Crashed because mask_diff.i3i was missing; tomoclass read
   813×884736 full volume without mask → segfault. With mask: 813×27896 matrix → success.

5. **PyTom scoring sort:** glob lexicographic sort used iter9 as "final" (iter10>iter9 alphabetically).
   Fixed to numeric sort via `re.search(r'iter(\d+)')`.

6. **ProTomo scoring args:** Original run script passed positional args; extract_protomo_classes.py
   uses --i3i/--stacks/--out flags; also added --include-junk (FM_hard has no junk class).

## What's still running

- **STOPGAP:** `~/Research/stopgap_fm_hard/` — calc_ccmat step in progress (~5158/20629 pairs
  done); will auto-proceed to calc_pca_ccmat and scoring when done. Script:
  `packages/STOPGAP/FM_hard/scripts/run_stopgap_fm_hard.sh`
  Score output: `outputs/FM_hard/stopgap/stopgap_fm_hard_k3.csv`

- **TomoFlow:** `~/Research/tomoflow_fm_hard/` — optical flow computation (150/813 vol done);
  will produce embedding.npy + scoring. Script: `packages/tomoflow/FM_hard/scripts/run_fm_hard_tomoflow.sh`
  Score output: `outputs/FM_hard/tomoflow/tomoflow_fm_hard_k3.csv`

## Commits this session

- `8ac4a60` — FM_hard: all 10 package scripts + 6 completed results
- `d7f16c7` — ProTomo FM_hard: ARI=-0.001 + script fixes
- `88b8e53` — packages/README.md FM_hard table with 7 results
- `fcee1ab` — PyTom FM_hard: ARI=0.017

## Next session

1. Check if STOPGAP/TomoFlow completed; score them with the provided scripts
2. Update `packages/README.md` FM_hard table with final 10/10 results
3. Update `STATUS.md` to mark FM_hard complete
4. Commit final CSVs and updated tables
5. Decide on next dataset/analysis
