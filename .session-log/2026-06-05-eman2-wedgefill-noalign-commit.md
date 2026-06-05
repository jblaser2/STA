# 2026-06-05 — EMAN2 wedgefill patch + no-alignment pipeline committed

## Goal
Get Eben's staged EMAN2 changes into the shared repo.

## What happened
- Reviewed the three staged EMAN2 files and committed them (`54f6124`).
- `git push` was rejected — Josh had pushed `0b8f89b` to `origin/main` meanwhile.
- `git pull --rebase origin main` replayed the EMAN2 commit cleanly on top (no
  conflicts); pushed → remote now at `ccf279c`. Working tree clean.

## Files changed (committed this session)
- `eman2/pcaScripts/patch_scripts.py` — added **Patch 2**: re-activates
  reference-based `mask.wedgefill` in `e2spt_pcasplit.py`'s active (numpy)
  preprocessing path, gated on `--nowedgefill`. Before this, `--nowedgefill`
  was a no-op because the intended reference fill existed only in a
  commented-out real-space block. Patch precomputes `threed.do_fft()` once
  before the particle loop and fills each particle's wedge from it before
  masking. Idempotent (guarded by `#WEDGEFILL_PATCH` sentinel + anchor checks).
- `eman2/pcaScripts/run_pipeline.sh` — converted to a **NO-ALIGNMENT variant**:
  subvolumes are already aligned at Euler (0,0,0), so skip any orientation
  search (`e2spt_refine`/`e2spt_align`); average + classify with identity
  transforms.
- `eman2/research.md` — documents the wedgefill patch and the no-alignment
  rationale.

## Where I stopped
Changes committed + pushed to `origin/main`. EMAN2 classification has **not**
been rerun with the new wedgefill / no-alignment behaviour — only the code is in.

## Next step
Rerun the EMAN2 PCA pipeline with the wedgefill patch active (default, without
`--nowedgefill`) on the real T4P set to see whether reference-based wedge fill
changes the k=2 split / lets it separate the two pili phases. Then k=3/4 still
outstanding.
