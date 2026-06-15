# EMAN2

**Algorithm:** PCA split on subtomogram stack with reference-based wedge-fill  
**Environment:** `eman2` conda env (Josh: `~/conda-envs/eman2`; Eben: `~/miniforge3/envs/eman2`)  
**Status:** ✅ T4P canonical k=3 (270/317 + 85 junk) + ✅ FM_easy k=3 (81/94/519, ARI≈0); collapses to a dominant cluster on both — contrast-axis PCA, not conformational

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=3 / k=2 | auto-tight (density) | — (no GT) | 270 / 317 (+85 junk) | Canonical no-align k=3 run; class 3 (85p, 152Å FSC) = junk; does not separate two pili phases |
| **FM_easy** | ✅ | k=3 / k=3 | auto-tight (density) | **−0.002** | 81 / 94 / 519 (no junk) | No-align PCA split, no `--clean`, NBASIS=12, MAXRES=40 Å. Collapses to dominant cluster (519); GT class C 0/0/177 entirely in it; A/B smeared. Contrast-axis, misses 3-class structure. |
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
- **FM_easy (2026-06-15): ARI=−0.002**, split 81/94/519. Same failure mode as T4P on data with known GT: PCA
  collapses to one dominant cluster (~75%) and class C lands 100% inside it (0/0/177); A/B smeared. MAXRES was
  set to 40 Å (finer than T4P's 60) specifically to resolve the ~30 Å conformational differences — it still
  collapses, confirming the discriminant is contrast/intensity, not the conformational axis.
- **`e2spt_pcasplit --clean` adds an outlier class (NCLASS+1):** with NCLASS=3, `--clean` produced 4 disjoint
  classes (31 outliers + 493/91/79). For the no-junk FM_easy protocol, drop `--clean` → exactly 3 classes
  (81/94/519, all 694 assigned). (The T4P "85 junk" in the canonical k=3 run is this `--clean` outlier class.)
- **Env path note (Josh's machine):** the eman2 env is at `~/conda-envs/eman2`, NOT `~/miniforge3/envs/eman2`;
  `conda activate eman2` works by name, but a hardcoded `$CONDA_BASE/envs/eman2/bin` PATH export is wrong here.

---

## Next Steps

1. T4P/FM_easy complete. FM_hard / T4SS when ready.
2. Both results final: EMAN2 PCA does not separate conformational states at this SNR (collapses to contrast axis).

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
| **Workspace (T4P):** `~/Research/eman2_project/` | Local workspace — sptcls_00/, spt_noalign/ outputs |
| **Workspace (FM_easy):** `~/Research/eman2_motor_easy/` | Local — `make_project.py`, `run_motor_easy.sh`, sptcls_01/ (k=3 no-clean) |
| `outputs/FM_easy/eman2/eman2_motor_easy_k3.csv` | Per-particle FM_easy assignments (k=3) |
| `outputs/FM_easy/eman2/confusion_eman2_k3_motor_easy_k3.png` | FM_easy confusion matrix (ARI=−0.002) |
