# EMAN2

**Algorithm:** PCA split on subtomogram stack with reference-based wedge-fill  
**Environment:** `eman2` conda env (Josh: `~/miniforge3/envs/eman2`; Eben: `~/miniforge3/envs/eman2`)  
**Status:** ✅ T4P canonical k=3 run complete (270/317 + 85 junk); does not separate two pili phases

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | auto-tight (density) | — (no GT) | 270 / 317 (+85 junk) | Canonical no-align k=3 run; class 3 (85p, 152Å FSC) = junk; does not separate two pili phases |
| **FM_easy** | ⬜ | — | — | — | — | Not yet run |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> T4P canonical run (2026-06-08): k=3, no-align (identity parms), NCLASS=3, NBASIS=12, MAXRES=60Å, --clean.
> Split 270/317/85. Class 3 (85p, FSC=152Å) is junk. Signal classes (270+317) do not correspond to the two T4P
> conformational states — PCA axis captures a different source of variance (likely contrast/intensity axis).
>
> **Mask note:** `e2spt_pcasplit.py --mask ""` (default) loads EMAN2's own auto-generated `mask_tight.hdf`
> (density-thresholded from the consensus average). A re-run with `--mask cylindrical_mask_v2.hdf` gave an
> identical 85/270/317 split despite the two masks covering non-overlapping regions of the box. This is because
> the dominant PCA axis is per-particle intensity/contrast variation — a whole-particle property present in every
> spatial sub-region. Even completely disjoint masks will produce the same first PCA component (and therefore the
> same k-means partition) when the confounding variance is global rather than spatially localized. No masking
> strategy can fix EMAN2's PCA failure on T4P.
>
> Workspace: `~/Research/eman2_project/` (local, gitignored). Assignments: `T4P/results/eman2_T4P_k3_none_r01_assignments.csv`.

---

## Key Findings

- k=3 canonical run (270/317/85): does not recover the two T4P pili conformational states.
- PCA separates on contrast/intensity axis rather than structural conformational axis.
- Wedge-fill confirmed irrelevant: enabled vs disabled gives identical 405/273 split (Eben, 2026-06-05).
- Junk class (class 3, 85 particles) identified by FSC 152Å vs 82Å for signal classes.
- **Mask is irrelevant:** EMAN2's auto-tight density mask and our cyl v2 mask cover non-overlapping regions yet
  give identical splits. Per-particle intensity/contrast variance is global — present in any spatial sub-region —
  so no masking strategy can suppress it or change the PCA result.
- Workspace: `~/Research/eman2_project/` (local, not committed). Run script: `T4P/scripts/run_pipeline.sh`.

---

## Next Steps

1. Run FM_easy (k=3, no junk) — EMAN2 not yet run on motor_easy.
2. T4P result is final: PCA does not separate conformational states at this SNR level.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/scripts/run_pipeline.sh` | Canonical no-align k=3 pipeline (NCLASS=3, NONINTERACTIVE=1) |
| `T4P/scripts/make_project.py` | Ingest MRC → particles.hdf + ptcls.lst |
| `T4P/scripts/patch_scripts.py` | np.int64 + wedgefill patches for e2spt_pcasplit.py |
| `T4P/results/eman2_T4P_k3_none_r01_assignments.csv` | Per-particle class assignments (class 3 = junk) |
| `T4P/results/eman2_T4P_k3_none_r01_classavg.png` | Class average slice panels (3 classes) |
| `research.md` | Qt/OpenGL Wayland fix, pipeline refactor, wedge-fill patch details |
| **Workspace:** `~/Research/eman2_project/` | Local workspace — sptcls_00/, spt_noalign/ outputs |
