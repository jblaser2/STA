# 2026-06-15 — DISCA on FM_easy (motor_easy)

**Goal:** Run an unrun package on motor_easy (FM_easy). Picked DISCA (native sm_120, template-free,
already-scripted masked pipeline from the T4P run).

**What happened:**
- Followed FM_easy protocol from `docs/datasets.md`: **k=3, no junk class**.
- The canonical FM_easy solvent mask MRC was missing from disk, so regenerated it from the documented
  spec (RELION solvent sphere: r=32 px ≈427 Å, center (48,38,48) in 96³ box = box-center shifted Y-10,
  4 px cosine edge) via a new script `scripts/data_prep/make_motor_easy_mask.py`. Saved local at
  `~/Research/synthetic_sta/motor_easy/production/motor_easy_solvent_mask.mrc`.
- Built DISCA input pickle: 694 GT-aligned `merged_all_aln` particles, masked then Fourier-cropped
  96³→32³ (`build_disca_input.py --mask`). Pickle local at `~/Research/disca_work/disca_input_motor_easy.pickle`.
- Ran `torch_disca_run.py` with `DISCA_K=3 DISCA_TAG=motor_easy_k3 DISCA_OUTDIR=./model_motor_easy`
  on GPU, 80 EM iterations (~2 min). Converged to balanced split **269/227/198**.
- Scored vs `labels.csv` with `score_synthetic.py`: **ARI=0.036** (AMI=0.036, V=0.039, Acc=0.427).
  Confusion matrix has no diagonal — each GT class (A/B/C) smeared across all 3 clusters.

**Conclusion:** DISCA splits on a contrast/intensity axis, NOT the conformational one — identical to
its T4P behavior, now confirmed on data with known ground truth. Joins OPUS-TOMO (0.021) as a
learned-feature method that misses the conformational structure.

**Files changed:**
- new `scripts/data_prep/make_motor_easy_mask.py`
- new `outputs/FM_easy/disca/disca_motor_easy_k3.csv`, `confusion_disca_k3_motor_easy_k3.png`
- `results/synthetic_scores.csv` (appended disca/motor_easy/k3 row)
- `STATUS.md` (Now/Next bullet + DISCA matrix row + last-updated)
- `packages/README.md` (FM_easy table: DISCA row added, "All others" trimmed)
- `packages/disca/README.md` (status, results table, key findings, next steps, files)

**Where I stopped:** DISCA FM_easy complete and documented. Changes staged, not committed.
Working tree also carries earlier-today uncommitted Dynamo FM_switch work (separate topic).

**Next step:** Run ProTomo on motor_easy (next unrun package; also EMAN2, TomoFlow, STOPGAP remain).
FM_easy now 6/10: RELION 0.475(GT) / Dynamo 0.200 / PyTom 0.134 / PEET 0.116 / DISCA 0.036 / OPUS 0.021.
