# 2026-06-15 — Dynamo FM_switch (motor_switch) dpkpca

## Goal
Resume the stalled Dynamo motor_switch session — prior runs kept dying at `ccmatrix`.

## What happened
- Diagnosed two failure modes:
  1. **06-11 run** — implicit 24-worker pool tore down mid-`ccmatrix` parfor (libgtk-x11
     ServiceHost crash-loop); STEP_FAIL logged.
  2. **06-15 12:14 run** — *had* the parpool hardening but vanished at 12:18 with no error in
     its log → external SIGHUP (launched foreground, killed when shell ended).
- Relaunched the hardened script **detached** (`nohup`, background): `MW_SERVICE_HOST_DISABLE=1`,
  explicit `parpool('Processes',16)` with `IdleTimeout=Inf`, `cores=16`.
- Clean run end-to-end in ~22 min: prealign → ccmatrix → eigentable → eigenvolumes → k-means.
- **Result: k=2 split 229/222, ARI=−0.001** (AMI=−0.002, V=0.001, Acc=0.481). CCW (101/107) and
  CW (110/98) each split ~50/50 across both clusters — dpkpca does not capture the CCW↔CW switch.
- FM_switch leaderboard now: RELION 0.379 (GT-seeded only) / PEET 0.007 / Dynamo −0.001.
  Both unsupervised methods fail at this SNR.

## Files changed
- `STATUS.md` — new dated FM_switch entry; Last updated → 2026-06-15.
- `packages/README.md` — Dynamo FM_switch row ⬜→✅ with confusion thumbnail.
- `packages/dynamo/README.md` — status line, results table, findings (parpool quirk), next steps, files.
- `results/synthetic_scores.csv` — dynamo motor_switch k=2 row appended.
- `packages/dynamo/FM_switch/results/confusion_dynamo_k2_k2_pca_motor_switch.png` — new (committed copy).
- `packages/dynamo/FM_switch/scripts/dynamo_motor_switch_pca.m` — parpool hardening (was already
  edited 06-15 12:13 before this session; now validated by a clean run).
- Memory: `dynamo-ccmatrix-parpool-160.md` + MEMORY.md pointer.
- Outputs (gitignored): `packages/dynamo/dynamo_outputs/motor_switch_pca/{eigencomponents.mat,
  ccmatrix_pca.mat,predictions_k2.csv}`.

## Where I stopped
Run complete and scored; all docs/memory synced. Changes staged, not committed.
`.claude/settings.json` shows as modified but is unrelated to this session.

## Next step
FM_switch per protocol: run **OPUS-TOMO** and **PyTom** k=2. Then FM_hard / T4SS remain unstarted
across all packages.
