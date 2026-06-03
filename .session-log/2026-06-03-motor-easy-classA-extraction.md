# Session: motor_easy class A extraction + pipeline quirks doc
Date: 2026-06-03

## Goal
Extract subtomograms for all 7 class A ETSimulations runs, compute GT-aligned average as
checkpoint, and document all pipeline bugs/workarounds discovered during this and prior sessions.

## What happened

- **Extraction (class A):** Ran `extract_subtomos.py` on all 7 class A tomograms
  (`production/class_A/run_01/` – `run_07/`). Extracted 246 subtomograms total
  (37+37+35+34+33+34+36; a few skipped near tomogram edge). Merged into flat directory
  `production/subtomos/merged_A/` with unified `labels.csv`.
- **GT-aligned average:** Computed aligned average of all 246 class A particles using
  verified `P@R@P.T` ZXZ→zyx rotation convention. Opened in 3dmod — motor ring clearly
  resolved. Checkpoint passed.
- **Pipeline quirks doc:** Wrote `STA/etsimulation/pipeline_quirks.md` (11 sections):
  `num_chimera_windows` bug, `scale_mrc` 20-min hang + polling workaround, orphaned workers,
  rotation convention, coordinate formula, axis order, membrane-constrained orientations,
  dose table, z_halfrange padding, sim_test.txt vs configs.yaml precedence, multi-class layout.
  Committed to STA repo (commit c74ee21).

## Files changed

- `STA/etsimulation/pipeline_quirks.md` — new, committed
- `~/Research/synthetic_sta/motor_easy/production/subtomos/merged_A/` — 246 subtomos + labels.csv
- `~/Research/synthetic_sta/motor_easy/production/subtomos/avg_classA_aligned.mrc` — GT average
- `STA/STATUS.md` — updated

## Where I stopped

Class A fully done. Classes B (6 runs) and C (5 runs) not yet started — no simulations,
no reconstructions, no extractions.

## Next step

1. Run class B simulations: for run_01–run_06 using `class_B_noCring.mrc`, same coords/orient
   as class A (already configured in `production/class_B/run_XX/configs.yaml`).
2. Reconstruct each: `bash reconstruct.sh ... tomo_rec_rotx.mrc`
3. Extract: `python extract_subtomos.py ... B`
4. Repeat for class C (5 runs, `class_C_core.mrc`).
5. Merge all three into one `labels.csv` (A=246, B≈222, C≈185).
6. Run quick PCA k-means at k=3 to verify ground-truth separability (ARI/NMI vs labels).

Watch for the `scale_mrc` hang — use MRC-file-polling approach from `pipeline_quirks.md §2`.
