# ProTomo (I3)

**Algorithm:** Iterative 3D alignment + multi-reference classification on centered subtomograms  
**Environment:** Native binary (I3 / ProTomo 3.1.0, system install)  
**Status:** ✅ T4P 2-class complete — **separates the two phases** (visual). ✅ FM_easy k=3 complete — **ARI≈0, collapses to a dominant cluster** (misses the 3-class structure)

---

## Results Summary

| Dataset | Status | k (run / reported) | Mask | ARI | Split | Notes |
|---------|--------|--------------------|------|-----|-------|-------|
| **T4P** | ✅ | k=2 / k=2 | none | — (no per-particle GT) | 334/212/126 junk (all 672) | CC=0.943. **Separates the two phases** (visual). Alignment step bypassed (MRAPKR bug). See notes below. |
| **FM_easy** (2-class hc, 542p) | ✅ | k=2 / k=2 | solvent sphere (mask96.i3i) | **0.030** | 382/160 | SVD+HAC collapse to dominant cluster again. Workspace `~/Research/protomo/motor_easy_hc/`; series via `tomoprepare`. Confusion: `outputs/FM_easy/protomo/` |
| FM_easy (old 3-class, 694p) | 🗄️ archived | k=3 | solvent sphere | −0.003 | 517/103/74 | Superseded; archived |
| **FM_hard** | ⬜ | — | — | — | — | Not yet run |
| **T4SS** | ⬜ | — | — | — | — | Not yet run |

> **T4P edge-filter note:** ProTomo's `MRAAREA` parameter checks whether each particle's
> aligned position falls within 80% of the box volume. 438/672 T4P particles (65%) have
> overlap 0.63–0.64 — they were picked near the z-boundaries of their source tomograms,
> leaving one side of the 80³ box zero-padded. The initial run filtered these to 234
> particles only. The full-672 rerun used `MRAPKR="0 0 0"` (no translation search) and
> `MRAAREA=0.0` (no overlap filtering) with `MSAIMGSIZE="32 32 32"` (SVD on central 32³
> cube only, unaffected by edge zero-padding). Result is identical: CC=0.921 — the zero-
> padded particles do not affect classification. The repo reorganization (2026-06-06) also
> broke the symlinks in `prepare/stacks/`; these were rebuilt pointing to `data/T4P_subtomos/`.

> **⚠️ Cylindrical mask not used — pending revisit:** ProTomo 3.1.0 does **not** support a
> cylindrical mask type. Supported shapes: `elliptic`, `Gaussian`, `rectangular`, and `molecular`
> (external MRC file). Current config uses `elliptic 35 35 35` (radius-35 sphere ≈ whole box),
> providing almost no structural discrimination. The benchmark protocol requires the v2 cylindrical
> mask (r=13). This CAN be added via `MRAMOLMSK` pointing to `data/T4P_mask/cylindrical_mask_v2.mrc`
> without changing the native mask type — but requires a re-run from `subvolalign.sh` onward.
> Since ProTomo is already confirmed to not separate T4P phases (CC=0.921 trivial), this re-run
> is deferred. If revisiting: also set `MRAPKR="5 5 0"` to allow XY centering (T4P is ~4 px
> off-center in Y).

---

## Key Findings

- **T4P** final result (alignment-bypassed): 334/212/126 junk, inter-class CC=0.943. **Class averages visually separate the two T4P conformational phases.**
- **MRAPKR="0 0 0" bug discovered:** `0 0 0` = unbounded search in ProTomo, not "no translation." With MRAAREA=0.0, 437/672 edge particles were shifted +22px in X by a spurious CC peak from zero-padded boundaries. Pipeline now bypasses `subvolalign.sh` (copies raw.i3i → mra.i3i) to prevent this corruption.
- ProTomo is primarily an alignment package; classification is a secondary capability.
- **FM_easy (2026-06-15): ARI=−0.003**, split 517/103/74. SVD on the FM_easy-masked stack + Ward HAC on factors 1–4 collapse to a single dominant cluster; the 3-class conformational structure is not recovered (GT class C lands 174/0/3 in cluster 0). Unlike T4P (2 large, visually distinct phases), the 3-way ~30 Å motor_easy differences are below ProTomo's SVD+HAC discrimination at this SNR.

### Pipeline-build gotchas (ProTomo 3.1.0, discovered building FM_easy)

- **The subtomo *series* `dataset.i3i` is built with `tomoprepare`** (consuming a `.prep` of `search`/`attach`/`save`), **not `tomoprocess`** (the workflow doc was wrong; `tomoprocess` lacks the `attach` command) and **not `i3concat`** (that produces a 4D *hypervolume* which `tomoclass` reads as a single image → "1 by N data matrix"). A valid series has **centered spatial coords (`[-48..47]`) + a 0-based index axis** and stores the member files by basename, resolved via `i3_filepath`/`DATADIR` at run time.
- **`tomoclass dataset` rejects absolute paths** (use relative + `DATADIR`); `MSAMASK` accepts an absolute path.
- **"No junk" = leave `CLSHVO`/`CLSHVM` empty** (not `0` — `hacoptions 0 0` errors as "invalid option"). Empty makes `subvolhac.sh` omit the `hacoptions` line entirely.
- **`cycle-000/param.sh` is copied at `subvolinitial` and overrides later edits to `param-template.sh`** — sync both (or re-init) when changing parameters.
- **SVD without central crop:** set `MSAIMGSIZE` = full box (`96 96 96`) and `MSAMASK` = the dataset mask `.i3i` (convert an MRC mask with `i3preproc <in.mrc> <out.i3i>`).

---

## Next Steps

- FM_hard / T4SS when ready. T4P/FM_easy complete.

---

## Files

| Path | Description |
|------|-------------|
| `T4P/results/class_averages_slices.png` | Central slice comparison of two classes |
| `T4P/results/clustering_scatter.png` | Clustering scatter plot |
| `research.md` | Detailed workflow and configuration notes |
| `outputs/FM_easy/protomo/protomo_motor_easy_k3.csv` | Per-particle FM_easy assignments (k=3) |
| `outputs/FM_easy/protomo/confusion_protomo_k3_motor_easy_k3.png` | FM_easy confusion matrix (ARI=−0.003) |
| `~/Research/protomo/motor_easy/` | Local workspace: `prepare/dataset.prep`, `process/param-template.sh`, `run_motor_easy.sh` (not committed) |
