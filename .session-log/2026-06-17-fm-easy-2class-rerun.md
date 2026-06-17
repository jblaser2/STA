# 2026-06-17 — FM_easy redesigned to 2-class high-contrast + ALL packages re-run at k=2 (blind)

## Goal
Scrap the failed 3-class FM_easy runs, rebuild FM_easy as the achievable 2-class high-contrast set
(bigger: ~500–600 particles), then run every package on it at k=2 and score.

## What happened
- **Dataset rebuilt.** Extended the ×6 hc pipeline to runs 01–08/class (`hc_test/run_full.sh`,
  `align_classify_full.py`) → **2-class A (mature full motor) vs C (early base), 271+271 = 542
  particles, SNR 0.340, 96³, 13.329 Å/px**, GT-aligned. Canonical input
  `~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/` (+`labels.csv`).
  Mask = A-vs-C diff sphere `diff_sphere_r23_y55.mrc`. Ceilings: blind masked-PCA ≈0.14, supervised
  5-fold logreg **0.745 / 0.932**.
- **Old 3-class k=3 runs archived** (reversible): per-pkg outputs → `outputs/FM_easy/_archive_3class_k3/`,
  40 score rows → `results/_archive_motor_easy_3class_scores.csv`.
- **All 10 packages run at k=2, scored** (`results/synthetic_scores.csv`, run tag `*_AC_hc_x6_542`):
  BLIND ranking — **PEET 0.450** (pc1_10) · **DISCA 0.407** · **Dynamo 0.254** · TomoFlow 0.036 ·
  PyTom 0.031 · ProTomo 0.030 · EMAN2 0.025 · **RELION blind 0.008** · OPUS 0.008. STOPGAP blocked.
- **Fairness correction (mid-session, per Josh).** First draft put RELION on top via **GT-seeding**
  (initialized from the true A/C class averages = effectively supervised). Re-ran RELION **blind**
  (global-avg init, no `--firstiter_cc`, no GT refs) → **0.008** (near-collapse 56/486). Moved the
  GT-seeded **0.764** out of the ranking into a "supervised upper bound" row next to the 0.745 logreg
  ceiling. All docs relabeled (every package number is now explicitly BLIND).
- **Benchmark signal:** old 3-class set put every package ≈0; the 2-class hc set splits the blind field
  into "finds class axis" (PEET/DISCA/Dynamo 0.25–0.45) vs "collapses on nuisance/contrast axis"
  (TomoFlow/PyTom/ProTomo/EMAN2/RELION-EM/OPUS ≈0), against a 0.75 supervised ceiling.
- **Confusion matrices** for all 9 run packages + RELION-blind exist under `outputs/FM_easy/<pkg>/`
  and are referenced (with images) in the `packages/README.md` FM_easy table.

## Files changed
- `STATUS.md` — new top entry (blind ranking + supervised-reference split + fairness note); date 2026-06-17.
- `docs/datasets.md` — FM_easy section rewritten to the 2-class ×6 design + parameter table.
- `packages/README.md` — FM_easy matrix rewritten (blind table + supervised-upper-bound table + images).
- `packages/{relion,peet,disca,dynamo,PyTom,eman2,opusTomo,protomo,tomoflow}/README.md` — FM_easy rows.
- New scripts: `scripts/data_prep/setup_relion_motor_easy_hc.py`, `scripts/run_relion_motor_easy_hc.sh`
  (GT-seeded ref) + `scripts/run_relion_motor_easy_hc_blind.sh` (blind), `scripts/data_prep/run_disca_fm_easy_hc.sh`,
  `packages/PyTom/FM_easy/scripts/*_hc_*`, `packages/peet/FM_easy/scripts/*_hc*`,
  `packages/opusTomo/FM_easy/scripts/*_hc_*`. Local (not repo): `~/Research/eman2_motor_easy_hc/`,
  `~/Research/protomo/motor_easy_hc/`, `~/Research/tomoflow_work/run_motor_easy_hc.sh`,
  `~/Research/synthetic_sta/motor_easy/hc_test/run_full.sh` (RUNS extended to 08).
- `results/synthetic_scores.csv` — new `*_AC_hc_x6_542` rows; `results/_archive_motor_easy_3class_scores.csv`.

## Where I stopped
9/10 packages scored + documented. STATUS, datasets.md, packages/README, all 9 per-pkg READMEs synced.
Confusion matrices verified present and linked. `/handoff` run (this entry).

## Next step
- Run **STOPGAP** on the BYU RC cluster (Eben) — blocked here (`/apps/matlab/r2023b` absent; SLURM-only).
- Refresh the figures gallery / class-average panels for the new k=2 runs if desired.
- Optional: nc-sweep Dynamo / more-PC sweeps to probe how close blind methods get to the 0.75 ceiling.
