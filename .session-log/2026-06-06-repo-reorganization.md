# 2026-06-06 — Repo Reorganization

## Goal
Reorganize the GitHub repo into a clean, navigable structure: unify all package dirs under
`packages/`, consolidate dataset/QC dirs under `data/`, create per-package READMEs, add a
master progress table, and wire in a protocol keeping package docs in sync with STATUS.md.

## What Happened

**Structure changes (all via `git mv`, committed as `d4e931c`):**
- 9 existing package dirs moved to `packages/` (dynamo, peet, PyTom, eman2, opusTomo, STOPGAP, disca, tomoflow, protomo); `packages/relion/` created fresh.
- Dataset/QC dirs moved to `data/` (T4P_mask, alignment_review, masked_average, few_sta_test).
- `subtomos_mrc/` renamed to `data/T4P_subtomos/` (plain mv, gitignored).
- `etsimulation/` moved to `synthetic/etsimulation/`.
- Background docs moved to `docs/` (Package_installation.md, benchmarkIdeas.md, Relion-algorithm-use.md, Particle-PCA-Research-Report.md).

**Cleanup:**
- `stopgap/` (lowercase, orphaned): `research.md` preserved as `packages/STOPGAP/setup_notes.md`; all other files removed (`git rm`).
- `TomoNet/`: key content captured in `docs/excluded-packages.md`; directory removed.
- `build/` (empty): deleted.
- Root-level duplicate files removed: `alignment_review_progress.json`, `alignment_review_results.txt`, `masked_average.py`, `review_alignment.py` (subdir versions were the up-to-date copies).
- `.gitignore`: added `*.pkl` and `*.mat`; updated STOPGAP binary patterns to `packages/STOPGAP/exec/lib*/`.

**New documentation:**
- `packages/README.md` — master progress matrix (all 10 packages × T4P + motor_easy × k=2/3/4).
- `packages/<pkg>/README.md` — per-package status + results + next steps (11 files total).
- `data/README.md`, `synthetic/README.md`, `docs/excluded-packages.md`.

**Protocol wired:**
- `CLAUDE.md` §"Package README Protocol": after any STATUS.md package update, also update `packages/README.md` and `packages/<pkg>/README.md`.
- `/handoff` skill: step 1a now explicitly calls for package README sync.

**Push issue:** Initial push failed (HTTP 500) because OPUS-TOMO model weights (`packages/opusTomo/scripts/output/weights.*.pkl`, 760 MB each) and a MATLAB `.mat` file were swept up by `git add -A`. Fixed by `git rm --cached`, added `*.pkl`/`.mat` to `.gitignore`, amended commit, then pushed successfully as `d4e931c`.

## Files Changed
- Committed: `d4e931c` — 2097 files changed (renames + new README files)
- `.gitignore` — added `*.pkl`, `*.mat`; updated STOPGAP patterns
- `CLAUDE.md` — new directory structure block + Package README Protocol section
- `.claude/commands/handoff.md` — step 1a (package README sync) added
- Memory files updated: `opus-tomo-setup-and-results.md`, `pytom-autofocus-mask-and-flag.md`, `peet-pca-iteration-and-wedge.md` (stale paths corrected)

## Where I Stopped
All reorganization tasks complete. Repo pushed to GitHub at `d4e931c`.

## Next Step
Continue with science work: Dynamo motor_easy full sweep, EMAN2 k=3/k=4, PyTom motor_easy.
No structural/organizational work needed.
