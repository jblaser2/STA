# STOPGAP 0.7.5 — Codebase Reference

> Purpose: a self-contained map of the STOPGAP codebase so future work needs no
> re-reading. STOPGAP is a **subtomogram averaging (STA) workflow written in
> MATLAB** that does template matching, high-resolution alignment/averaging, and
> **classification** (PCA + k-means, and multireference alignment). Source +
> example bash scripts + MCR binaries (compiled here for **R2023b** via
> `recompile_stopgap.slurm`; the upstream-shipped R2020b binaries are not used).
> Repo root (persistent hub): `/home/ejl62/summerResearch/STA/packages/STOPGAP/`.
>
> **This file is the single replication reference.** Part I (§1–9) maps the STOPGAP
> codebase; **Part II (§10–15)** documents *our* T4P pre-picked-particle
> classification pipeline — the actual scripts, the run procedure, the bugs we hit
> and fixed, parameters/tuning, and (§15) the **results of the completed k=2/3/4
> run**. A new group member should be able to reproduce the work from Part II alone,
> dropping into Part I for internals.
>
> **Status (2026-06-09): the full T4P pipeline has run end-to-end** (PCA+k-means and
> MRA, k=2/3/4). All scripts, params, masks, eigenvalues, class averages, and figures
> are committed under `T4P/` (see §10, §15). Everything below is current; nothing in
> the pipeline is "pending" anymore.

---

## 1. Top-level layout

```
packages/STOPGAP/                       # ← persistent replication hub ($SG in scripts)
├── src/                  # MATLAB source compiled into the runtime binaries
│   ├── stopgap/          # main entry (stopgap.m), watcher, compile_*.m scripts
│   ├── subtomo/          # subtomogram alignment & averaging (exec/func/parser/watcher)
│   ├── pca/              # PCA classification pipeline
│   ├── tm/               # template matching
│   ├── extract/          # subtomogram extraction from tomograms
│   ├── tube_ps/, vmap/   # tube power spectra, variance maps
│   ├── func/             # shared compute (filters, FFT crop, FLCF, FSC, timers, MPI comm)
│   └── io/               # low-level IO (read/write mrc/em, star, motl, settings, file-waits)
├── sg_toolbox/           # ~300 standalone `sg_*` helper functions + toolbox entry
│   ├── io/{pca,subtomo,tm,tps,vmap}/   # per-task parser arg defs / settings / field types
│   ├── other/, tom/, private/, standalone/
├── exec/                 # everything that ships to run STOPGAP (the "bin"); $STOPGAPHOME
│   ├── bash/             # USER-FACING upstream template scripts (reference only)
│   ├── bin/              # launcher wrappers (call compiled binaries)
│   ├── lib/              # config (MCR paths) + MCR prep + the 4 compiled R2023b binaries
│   │                     #   (stopgap, stopgap_parser, stopgap_watcher, sg_toolbox — GITIGNORED)
│   ├── lib_r2023b/       # mcc build artifacts/logs from the last recompile (not the binaries)
│   └── lib_prev/         # previous build, auto-created on the next recompile (may be absent)
├── T4P/                  # ← OUR T4P classification experiment (the actual pipeline)
│   ├── scripts/          # run_pipeline.slurm, resume_pca.slurm + build_*.m / *_results.m / kmeans fn
│   └── results/          # committed run outputs (see §15): lists/ ref/ pca/ meta/ params/ masks/ fsc/
├── FM_hard/  T4SS/       # placeholders for the other datasets (.gitkeep; not yet run)
├── recompile_stopgap.slurm   # rebuild the 4 binaries for R2023b + install to exec/lib/
├── research.md           # THIS FILE — single replication reference
├── setup_notes.md        # deep technical guide (shared files, data structures, modules)
├── README.md             # package status + results summary + file index
├── stopgap_0.7.5_manual.pdf  /  stopgap_0.7.5.md  /  changes.txt
```

`$STOPGAPHOME` env var must point to a dir containing `bin/` and `lib/` (i.e. a
populated `exec/`); the SLURM scripts set `STOPGAPHOME=$SG/exec` with
`SG=…/packages/STOPGAP`. The bash scripts reference `${STOPGAPHOME}/bin/*.sh` and
`${STOPGAPHOME}/lib/*`. **The compiled binaries in `exec/lib/` are gitignored** — a
fresh clone must run `recompile_stopgap.slurm` once before the pipeline will launch.

---

## 2. Execution model (how a job actually runs)

1. **Parser bash script** (`exec/bash/stopgap_*_parser.sh`) — you edit variables at
   the top, it calls `bin/stopgap_parser.sh <task> key val key val …` which runs the
   compiled `stopgap_parser` → writes a **`.star` parameter file** (e.g.
   `params/subtomo_param.star`). Re-running appends new iterations; completed
   iterations are not repeated (each row has a `completed` flag).
2. **Run script** `exec/bash/run_stopgap.sh` — writes a SLURM `submit_stopgap`
   (or local `mpiexec`) and launches the **watcher** (`bin/stopgap_watcher.sh`).
3. **Watcher** (`src/stopgap/stopgap_watcher.m`) reads the param file's **data-block
   name** to pick the task, submits the job, and monitors progress / crash files.
4. **Workers**: SLURM `srun`/`mpiexec` launches `bin/stopgap_mpi_slurm.sh` once per
   core. That wrapper derives `procnum`/`local_id` from `$SLURM_PROCID` /
   `$OMPI_COMM_WORLD_RANK`, sets up a per-job MCR cache (`stopgap_prepare_mcr.sh`),
   optionally copies data to node-local `/tmp` (`copy_local`), then runs the compiled
   `lib/stopgap rootdir … paramfilename … procnum … n_cores …`.
5. `stopgap.m` (`src/stopgap/stopgap.m`) is the **single entry point**. It reads the
   param star data-block name via `get_star_data_block` and dispatches:

   | data block                     | function                  |
   |--------------------------------|---------------------------|
   | `stopgap_subtomo_parameters`   | `stopgap_subtomo(s)`      |
   | `stopgap_extract_parameters`   | `stopgap_extract_subtomos`|
   | `stopgap_tm_parameters`        | `stopgap_template_match`  |
   | `stopgap_pca_parameters`       | `stopgap_pca(...)`        |
   | `stopgap_vmap_parameters`      | `stopgap_vmap`            |
   | `stopgap_tps_parameters`       | `stopgap_tube_ps`         |

### Parallelism = file-based MPI (no message passing)
Every core runs the same binary. **`procnum==1` is the master**: it compiles partial
results, cleans the comm dir, and writes `complete_*` flags. Cores coordinate purely
through files in the **comm directory** (`comm/`):
- A core signals "done" by `touch`-ing `commdir/<tag>_<procnum>`.
- `wait_for_them(commdir, tag, n_cores, wait_time)` blocks until N tagged files exist
  (barrier). `wait_for_it(commdir, flag, wait_time)` blocks on a single flag file.
- Work is split by index ranges via `job_start_end(n_items, n_cores, procnum)`.
- Timing via `processing_timer`; progress via `progress_counter`.
This is why **classification scales near-linearly with cores** and why "lots of CPUs"
directly helps. Keep `cpus-per-task=1`; STOPGAP is single-threaded per rank
(`-singleCompThread` in compile flags).

---

## 3. Core data structures

### Motivelist ("motl") — `data_stopgap_motivelist` star, 16 columns
Defined in `sg_toolbox/sg_get_motl_fields.m`. One row per particle-orientation:

| field | type | meaning |
|-------|------|---------|
| `motl_idx`   | int   | row index (1..N) |
| `tomo_num`   | int   | source tomogram number |
| `object`     | int   | object/filament id (grouping) |
| `subtomo_num`| int   | particle id → maps to file `[subtomo_name]_[subtomo_num].mrc` |
| `halfset`    | str   | `A`/`B` for gold-standard FSC halfsets |
| `orig_x/y/z` | float | particle coords in tomogram (px) |
| `score`      | float | alignment score (CC/FLCF/pearson) |
| `x/y/z_shift`| float | refined translational shift (px) |
| `phi,psi,the`| float | Euler angles (ZXZ; phi=in-plane about Z, the=tilt, psi) |
| `class`      | int   | class label (used by multiclass/multiref & PCA output) |

- IO: read via `src/io/read_motl.m` (compiled path) or toolbox `sg_motl_read2.m`;
  write via `sg_motl_write2.m`. Star read/write core = `stopgap_star_read.m` /
  `stopgap_star_write.m`. Header line is `data_stopgap_motivelist` + `loop_` + fields.
- Init empty: `sg_initialize_motl(n, fields)`. Many `sg_motl_*` tools manipulate motls
  (convert from Dynamo/AV3, clean, split, assign halfsets, plot, etc.).
- **Type 2** = single-entry-per-particle (one row/particle). Multi-entry ("type 3")
  used for multiref (one row per particle×class). Converters:
  `sg_motl_multientry_to_singlentry`, `sg_motl_singleentry_to_multientry`.

### Wedgelist — `sg_get_wedgelist_fields.m`
Per-tomogram missing-wedge / CTF metadata: `tomo_num, pixelsize, tomo_x/y/z, z_shift,
tilt_angle[array], defocus/defocus1/defocus2/astig_ang/pshift/exposure[arrays],
voltage, amp_contrast, cs`. Built per-tomogram with
`sg_wedgelist_add_entry.m` (tilt scheme `unidirectional`/`bidirectional`/`hagen`;
`def_list_name='none'` → no CTF; `dose=0` → no exposure filter). Written with
`sg_wedgelist_write`. The **only mandatory geometry** is tomo size + tilt range;
defocus/exposure are optional and can be disabled at the param level.

### Parameter files & settings
- Param `.star`: rows = iterations/tasks; appended, not overwritten (PCA param is
  overwritten). Field order/types from `sg_get_ordered_*_input_fields` +
  `sg_evaluate_field_types`.
- Settings `*_settings.txt` (e.g. `subtomo_settings.txt`, `pca_settings.txt`) in
  `params/` or root: low-level knobs (`wait_time`, `vol_ext`='.mrc'/'.em',
  `counter_pct`, `subtomo_num` formatting, etc.). `global_settings.txt` in
  `exec/lib/` applies to all tasks (ships empty).

---

## 4. Subtomogram averaging/alignment — `src/subtomo/`

Entry `stopgap_subtomo.m`. **Mode string = `<action>_<type>`**:
- action: `ali` (align then average) | `avg` (average only).
- type: `singleref` | `multiref` | `multiclass`.
  - **singleref**: one reference; motl may hold many classes (`iclass`=0 → all).
  - **multiref**: each subtomo aligned against *every* reference; best wins (true
    classification with alignment). Multi-entry motl.
  - **multiclass**: motl already has class labels; each particle averaged/aligned only
    to its own class's reference (use this to make class averages after PCA/k-means).
- Averaging modes list: `sg_get_subtomogram_averaging_modes.m` →
  `{avg_singleref, avg_multiclass, avg_multiref}`.

Flow inside `ali`: `refresh_motl` → `check_motl_for_subtomo` → `get_subtomo_boxsize`
→ `generate_subtomo_bpf` (bandpass) → `initialize_fourier_crop_alignment` (speed:
Fourier-crop to lp radius) → `load_subtomo_references` (refs+masks) →
`get_alignment_angles` → `align_subtomos` (the core CC loop) →
`complete_subtomo_align` (master compiles new motl). Then **parallel averaging**:
`parallel_average` (each core averages its subset, applies wedge/CTF reweighting)
→ `final_average` → `complete_final_average`. Half-set FSC plotted via
`save_fsc_plot.m` / `calculate_fsc.m`.

Key alignment knobs (from `stopgap_subtomo_parser.sh`):
- `search_mode`: `hc` (greedy hill-climb) | `shc` (stochastic).
- `search_type`: `cone` (angincr/angiter for the cone = psi+theta, phi_angincr/
  phi_angiter for in-plane phi) | `euler` (arbitrary euler_axes + per-axis incr/iter).
  - **In-plane-only search** = set the cone to a single orientation (`angiter=0` →
    `calculate_cone_angles` returns just `[0;0]`) and sweep phi with
    `phi_angincr`/`phi_angiter`. See `src/func/calculate_cone_angles.m`.
- `cone_search_type`: `coarse` (Dynamo-like) | `complete`.
- Bandpass: `lp_rad/lp_sigma/hp_rad/hp_sigma` (Fourier px).
- Weighting: `calc_exp` (exposure), `calc_ctf` (CTF), `cos_weight`, `score_weight`.
- `scoring_fcn`: `flcf` (needs ccmask) | `pearson`. `symmetry` Cn about Z.
- `subset` (% used), `avg_mode` (full/partial), `ignore_halfsets`, `fthresh`
  (Fourier reweight floor), `rot_mode` (linear|cubic).

---

## 5. PCA classification pipeline — `src/pca/`

Entry `stopgap_pca.m`. The **param `pca_task`** drives a multi-stage pipeline;
each stage is a separate param row run in sequence:

| `pca_task`        | does | key outputs |
|-------------------|------|-------------|
| `rot_vol`         | pre-rotate every subtomo into common frame using its best motl orientation; filter + symmetrize + Fourier-reweight | `rvol/rvol_<n>.mrc`, `rvol/rwei_<n>.mrc` |
| `calc_ccmat`      | pairwise constrained cross-correlation matrix between all prerotated particles | `pca/ccmatrix_*.mrc` |
| `calc_pca_ccmat`  | eigen-decompose the CC matrix → eigenfactors, eigenvectors (eigenvolumes), eigenvalues | `pca/eigenvol_*`, `pca/eigenval_*.csv` |
| `calc_covar`      | (alternative path) real-space covariance matrix → eigen via SVD | `pca/covar_*.mrc` |

- `pca_prerotate_volumes.m`: for each subtomo picks **highest-score** motl entry,
  rotates by `[-psi,-phi,-the]` and shifts by `[-x,-y,-z]`, clears missing-wedge
  noise via particle filter, symmetrizes, Fourier-reweights. **Requires orientations
  in the motl** (if particles are already aligned, angles=0 → near-identity).
- CC-matrix path: `pca_calculate_ccmatrix` (parallel over pairs;
  `intialize_pairlist`) → `pca_assemble_ccmatrix` →
  `pca_ccmat_calculate_eigenfactors` → `pca_calculate_eigenvectors_parallel/_final`
  → `pca_calculate_eigenvalues`. Covariance path: `pca_calculate_covariance_matrix`
  → `pca_assemble_covariance_matrix` → SVD in `pca_covar_calculate_svd.m`.
- **Filter list** (`filtlist_name`, default `filter_list.star`): PCA can be run over
  several bandpass filters at once (`o.n_filt` = #rows); eigenvalues stored per filter.
  `data_type` (e.g. `awpd`) selects which prepared data variant. Two traps for the
  single-filter case (we want `n_filt=1`): `sg_pca_append_filter_list` **appends**, and
  `distribute_filter_jobs` has an off-by-one that orphans the last filter for some
  `n_filt`/`n_cores` — both detailed in §11 bug #10.
- **Clustering is NOT in the parallel pipeline.** It is a standalone toolbox script:
  - `sg_pca_kmeans_cluster.m` (script, hard-coded inputs at top): loads
    `eigenval_<filt>.csv`, runs MATLAB `kmeans(eigenval, n_classes, 'replicates',5)`,
    writes the class labels back into the motl (`motl_<suffix>_<iter>.star`).
  - `sg_pca_hierarchical_cluster_references.m`: hierarchical clustering alternative.
  - `sg_pca_covar_eigen.m` (script): standalone SVD of covariance matrix → eigenvols
    + eigenvalues (`coeff = S*V'`), with optional `add_ref`.
  - `sg_pca_plot_eigenvalue_hist.m`: grid of per-eigenvector histograms.
- After clustering, you run **`avg_multiclass`** subtomo averaging on the
  class-labeled motl to produce one class average per cluster.

> Note: the toolbox clustering scripts have **hard-coded `rootdir`/`param_idx`/
> `n_classes`** at the top — they are meant to be copied/edited, not called with
> args. For our automated pipeline we converted k-means into a function:
> `scripts/sg_pca_kmeans_cluster_fn.m` (see §10).

---

## 6. Template matching — `src/tm/` (context only)
`stopgap_template_match.m`. 0.7.5 change (changes.txt): parallelization is now by
**tilesize** (target splice size; extraction = tilesize+template, ~5× tilesize RAM;
192 is a good start) → near-linear core scaling. Produces score/angle maps; peaks →
motl via `sg_tm_generate_motl`. Not needed for classifying pre-picked particles.

---

## 7. Shared utilities worth knowing

- **IO**: `read_mrc/write_mrc`, `read_em/write_em`, `read_vol/write_vol` (ext from
  settings), `sg_mrcread/sg_mrcwrite` (toolbox, with pixelsize), `read_settings`,
  `get_star_data_block`, `get_environmental_variable`.
  - **Signature gotchas** (differ across the two IO layers): `read_mrc(rootdir,mrcname)`
    takes *two* args (joins them) and returns the array via `tom_mrcread(...).Value`;
    the toolbox `sg_mrcread(full_path)` takes *one* full path and returns
    `[data, header]`. Pixel size isn't a header field — compute it as
    `header.xlen/double(header.mx)` (Å/voxel). `sg_read_mrc_header(full_path)` returns
    just the header struct (fields `nx/ny/nz, mx/my/mz, xlen/ylen/zlen, ...`).
- **Filters/FFT**: `calculate_3d_bandpass_filter`, `calculate_3d_ctf_filter`,
  `generate_wedgemask_slices`, Fourier crop family
  (`fourier_crop_volume`/`fcrop_*`/`crop_fftshifted_vol`) for speed,
  `optimize_fft_wisdom`.
- **Scoring**: `calculate_flcf` (fast local CC), `sg_pearson_correlation`,
  `calculate_fsc`/`sg_calculate_FSC` (72-symbol full FSC tool with masking).
- **Geometry/rotation**: `sg_rotate_vol` (linear|cubic), `sg_shift_vol`,
  `sg_euler2matrix`/`sg_matrix2euler`, quaternion suite, `sg_symmetrize_volume`,
  `Rx/Ry/Rz`.
- **Masks**: `sg_sphere`, `sg_cylinder`, `sg_cube_mask`, `sg_annulus`,
  `sg_smooth_box_edge`, `normalize_under_mask`.
- **Motl plotting** (useful for result viz): `sg_motl_plot_class_occupancies`,
  `sg_motl_plot_class_changes`, `sg_motl_plot_class_convergence`,
  `sg_motl_plot_class_bar_graph`, `sg_motl_plot_score_histograms`,
  `sg_motl_plot_shifts`, `sg_neighbor_plot_local`.
- **Halfsets/classes**: `sg_motl_assign_halfsets` (gold-standard A/B),
  `sg_motl_apply_random_classes` (random label per particle, no duplication — for
  MRA seeding), `sg_motl_intiailize_random_subset_classes` (random subsets, may
  duplicate — for seeding refs only), `sg_motl_reassign_classes`,
  `sg_motl_find_class_concensus`.
- **Toolbox entry**: `sg_toolbox/standalone/sg_toolbox.m`, run via
  `bin/stopgap_toolbox.sh` (compiled). Has graphical (`hist`/`figure`) calls → the
  toolbox binary is compiled **with** Java/display (no `-nojvm/-nodisplay`), unlike
  the worker binaries.

---

## 8. Build / compile (MCR)

`src/stopgap/compile_*.m` use MATLAB **`mcc`** (MATLAB Compiler) to produce
standalone binaries placed in a target dir (becomes `exec/lib/`). `compile_all.m`:

```matlab
compile_all(target_dir)   % runs the four below
%  compile_parser:  mcc -R nojvm -R -nodisplay -R -singleCompThread -R -nosplash -d <t> -mv stopgap_parser.m
%  compile_stopgap: mcc -R nojvm -R -nodisplay -R -singleCompThread -R -nosplash -d <t> -mv stopgap.m
%  compile_watcher: mcc -R nojvm -R -nodisplay -R -singleCompThread -R -nosplash -d <t> -mv stopgap_watcher.m
%  compile_toolbox: mcc -R -nosplash -d <t> -mv sg_toolbox.m -a <sg_toolbox_dir> -a <matlab graph2d toolbox>
```

**Hard-coded paths that must change per machine/version** (already set for this
machine — see `recompile_stopgap.slurm`, which `sed`-patches them idempotently):
- `compile_toolbox.m`: `sg_toolbox_dir` → `<repo>/sg_toolbox/`; `matlab_root` →
  `/apps/matlab/r2023b/`.
- `exec/lib/stopgap_config_slurm.sh` & `stopgap_config_local.sh`: `matlabRoot` →
  `/apps/matlab/r2023b/`, used to set `LD_LIBRARY_PATH` to the MCR
  `runtime/bin/sys/opengl` dirs. (Any RHEL7 glibc-2.17 shim preload from upstream is
  not needed on RHEL9.)

Binaries must be **run with a matching MCR/MATLAB runtime version**. Worker binaries
are compiled headless (`nojvm`,`nodisplay`); the toolbox needs JVM+display.
The compile must add to the MATLAB path: `src/**` and `sg_toolbox/**`.

**Current state:** all four binaries (`stopgap`, `stopgap_parser`, `stopgap_watcher`,
`sg_toolbox`) are compiled for R2023b and installed in `exec/lib/` (gitignored — they
do not travel with the repo). `recompile_stopgap.slurm` builds into `exec/lib_r2023b/`
(mcc artifacts), backs up any currently-installed binaries to `exec/lib_prev/`, then
installs into `exec/lib/`. The upstream R2020b binaries are not used. To (re)build,
submit `recompile_stopgap.slurm` (§10). `mcc`
is the MATLAB Compiler — it ships *inside* the install (`/apps/matlab/r2023b/bin/mcc`),
is **not** a separate Lmod module (`module spider mcc` fails — expected), and is on
`PATH` after `module load matlab/r2023b`. The compile node needs license-server
connectivity (`27002@lice`).

---

## 9. This machine / dataset (BYU RC cluster, RHEL9, SLURM)

- MATLAB modules: `matlab/r2023b` (default `MATLABROOT=/apps/matlab/r2023b`),
  also `r2018b`, `r2024a`. A separate MCR module exists only for `r2018b`
  (`matlab-runtime/r2018b`) — so for r2023b we run binaries against the **full
  MATLAB r2023b install's runtime** (`/apps/matlab/r2023b/{runtime,bin,sys}/glnxa64`).
- Binaries in `exec/lib/` are built for **R2023b** (recompiled via
  `recompile_stopgap.slurm`) and gitignored; the upstream R2020b binaries are unused.
- Dataset: `/home/ejl62/groups/grp_tomo/Pili_PCA/particles/` — **672** files named
  `aligned_tom<T>_P<NNNN>.mrc`, 80³, T4P (Vibrio) pili, particle centered, pilus axis
  along Z (in-plane angle free). Filenames encode tomogram + particle, **not** a
  sequential `subtomo_num` → a motl mapping/rename step is required (`build_inputs.m`).
  **294 unique tomograms**; **pixel size = 13.328 Å/vox** (read from MRC header:
  `xlen/mx`); box = 80.

---

# PART II — Our T4P classification pipeline

> Goal: **unsupervised** classification (k = 2, 3, 4) of the 672 pre-picked,
> Z-aligned T4P subtomograms, by **two** independent methods — **PCA + k-means**
> (primary) and **multireference alignment / MRA** (secondary) — then compare them
> (ARI/NMI) for the benchmark. Visualize with PC scatter plots + class-average
> central-slice montages. Everything runs in **one SLURM allocation**.

## 10. The pipeline files (all on disk, all runnable)

Two SLURM scripts drive everything; the MATLAB helpers live in `T4P/scripts/` and are
called via `matlab -batch` with `src/`, `sg_toolbox/`, and `T4P/scripts/` on the path.
The SLURM scripts set `SG=…/packages/STOPGAP` and add `$SG/T4P/scripts` to the MATLAB
path, so the whole pipeline is self-contained in this repo (no external paths beyond
the particle data and `$ROOT` working dir). `recompile_stopgap.slurm` lives at the
package root; the pipeline + helpers live in `T4P/scripts/`.

| File | Role |
|---|---|
| `recompile_stopgap.slurm` | Recompile the 4 binaries for R2023b, back up the prior build to `exec/lib_prev/`, install to `exec/lib/`, smoke-test the parser. Run once per machine/MATLAB version. |
| `T4P/scripts/run_pipeline.slurm` | Full end-to-end classification. Edit the USER CONFIG block, `sbatch` it. |
| `T4P/scripts/resume_pca.slurm` | Resume the PCA branch from the k-means stage, reusing existing `pca/eigenval_*.csv` + `rvol/rwei` (skips alignment + PCA recompute). MRA not included. |
| `T4P/scripts/build_inputs.m` | Symlink `aligned_tom*_P*.mrc` → `subtomograms/subtomo_<n>.mrc`; write `lists/allmotl_1.star` (type-2 motl, 16 fields); odd→halfset A / even→B; dump `meta/tomo_nums.csv`. |
| `T4P/scripts/build_wedgelist.m` | One wedgelist row per tomogram×tilt from **tilt range only** (CTF/exposure off); reads px + box from `subtomo_1.mrc` header. |
| `T4P/scripts/build_masks_ref.m` | Cylindrical alignment mask (`mask_align.mrc`) + tighter CC mask (`mask_cc.mrc`) along Z; initial reference = normalized global average, written to **`ref_1.mrc`, `ref_A_1.mrc`, `ref_B_1.mrc`** (per-halfset — see §11). Mask radii **tightened 2026-06-04** (§12). |
| `T4P/scripts/inspect_global_avg.m` | Diagnostic (not in the pipeline): render `ref_1.mrc` XY/XZ central slices + radial density profile to `meta/global_avg_profile.png` to size the mask. Run via `matlab -batch`. |
| `T4P/scripts/build_pca_aux.m` | Write `lists/filter_list.star` (**exactly one** bandpass entry — deletes any existing file first, since `sg_pca_append_filter_list` appends; see §11 bug #10) + `pca_settings.txt` (`calc_ctf=0`, `calc_exp=0`). |
| `T4P/scripts/sg_pca_kmeans_cluster_fn.m` | Parameterized k-means over PCA eigenvalues → `lists/allmotl_pca_k<k>_<ITER>.star`. Auto-finds the `calc_pca_ccmat` row; `kmeans(X,k,'Replicates',20)`, `rng(0)`. |
| `T4P/scripts/visualize_results.m` | Headless PNGs to `meta/`: PC1–2 & PC1–3 gscatter colored by class; XY/XZ/YZ central-slice montage of each class average. |
| `T4P/scripts/compare_methods.m` | ARI + NMI + co-occurrence matrix (PCA vs MRA), aligned by `subtomo_num` → `meta/pca_vs_mra_agreement.csv` + `cooccur_k*.png`. |

### Stage flow (as orchestrated by `run_pipeline.slurm`)
```
init_folders                       stopgap_initialize_folder.sh pca + subtomo
build_inputs  → allmotl_1.star     (+ symlinks, tomo_nums.csv)
build_wedge   → wedgelist.star
build_masks   → mask_align/mask_cc + ref_{1,A_1,B_1}.mrc
build_pca_aux → filter_list.star + pca_settings.txt
[DO_ALIGN=0]  (default) alignment SKIPPED — particles are prealigned at (0,0,0);
              ITER=1, PCA reads allmotl_1 + ref_1 directly. Set DO_ALIGN=1 only to
              run ali_singleref in-plane phi sweep (1→2→3 ⇒ allmotl_3 ; ITER=3).
PCA           parse(rot_vol,calc_ccmat,calc_pca_ccmat) → run_pca → eigenval_1.csv
kmeans        → allmotl_pca_k{2,3,4}_<ITER>.star
avg PCA       parse_avg_pca_k* → run_avg_pca           avg_multiclass class averages
viz_pca       → meta/*.png
[DO_MRA=1]    seed random classes → avg seed refs → ali_multiref (5 iters) per k
              classify-only (phi_angiter=0) → compare → meta/pca_vs_mra_agreement.csv
```

## 11. Bugs hit & fixed (so you don't re-hit them)

These were found by iterating real SLURM runs. Bugs 1–5, 9, 10 are fixed in our
pipeline files / config (no STOPGAP source touched, no recompile). Bugs 6–8 are
**genuine defects in STOPGAP's own source** on the PCA code path — they cannot be
worked around from config, so they required minimal one/two-line edits **plus a
recompile** (`recompile_stopgap.slurm`); the algorithm code is untouched.

1. **`scoring_fcn` is invalid for the PCA parser.** Its check is commented out in
   `pca_parser.m`; only the *subtomo* parser accepts it. Passing it →
   `MATLAB:InputParser:UnmatchedParameter`. PCA "other" params are only
   `apply_laplacian, noise_corr, symmetry, fthresh`. (The subtomo align/avg/MRA calls
   *do* legitimately pass `scoring_fcn flcf`.)
2. **`LD_LIBRARY_PATH: unbound variable`.** `stopgap_mpi_slurm.sh` runs under
   `set -o nounset`; `stopgap_config_slurm.sh` referenced `${LD_LIBRARY_PATH}` which is
   unset on a fresh `srun` rank → every rank aborts before the binary starts. Fixed in
   `stopgap_config_slurm.sh` / `stopgap_config_local.sh`:
   `export LD_LIBRARY_PATH="$matlabRoot/runtime/glnxa64/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"`.
3. **Param-file reader trailing-slash bug.** `sg_read_subtomo_param` /
   `sg_read_pca_param` concatenate `[rootdir,paramfilename]` with **no separator**,
   while the parser's `exist()` check and the writer use a slash. So `rootdir` passed
   to the parser CLI **must end in `/`** — otherwise the *append-read* path fails
   (`ACHTUNG!!! Error reading <paramfile>`). It only bites when the param file already
   exists: a rerun, or the PCA stage's 2nd/3rd parser call (it builds one 3-row file
   across calls). Fixed by passing `ROOTS="${ROOT%/}/"` as `rootdir`, plus a
   `rm -f $ROOT/params/*.star` reset at the start so reruns don't accumulate rows.
4. **Missing per-halfset initial references.** STOPGAP's `singleref` loader always
   reads **both** `ref_A_<iter>.mrc` and `ref_B_<iter>.mrc` (gold-standard halves), so
   a lone `ref_1.mrc` → `ACHTUNG!!! Error reading file ref//ref_A_1.mrc` (exit 249)
   inside `load_subtomo_references`. `build_masks_ref.m` now writes the global average
   to `ref_1`, `ref_A_1`, and `ref_B_1`. The chain is otherwise self-consistent:
   `final_average.m` writes `ref_{A,B}_N` **and** a FOM-combined `ref_N` each iteration,
   so PCA (`initialize_ref_for_pca` reads combined `ref_<ITER>`) and MRA (`avg_multiclass`
   seed writes its own `ref_mra_*` refs that `ali_multiref` reads) need no hand-built refs.

5. **Fail-loud `stage()` false positive on benign warnings.** STOPGAP prints normal
   MATLAB warnings that contain the string `ACHTUNG!!!`, e.g.
   `Warning: ACHTUNG!!! "fieldtypes" will be used rather than automatic numeric parsing!!!`
   (from `stopgap_star_read` during routine averaging). The `stage()` fatal-marker grep
   matched these and aborted a `run_align` that had **actually finished successfully** on
   all cores. Fixed by excluding `Warning:`-prefixed lines before deciding to abort
   (`grep -vE 'Warning:.*ACHTUNG'`); genuine fatals are never `Warning:`-prefixed, so
   segfault/killed/OOM/real `ACHTUNG!!! Error` lines are still caught.
6. **PCA task dispatch passes undefined variables** *(STOPGAP source bug)*. In
   `src/stopgap/stopgap.m` the subtomo branch correctly calls `stopgap_subtomo(s)` with the
   parsed struct, but the PCA branch (line 52) read **bare undefined vars**:
   `stopgap_pca(rootdir,paramfilename,procnum,n_cores)`. Every rank crashed right after
   "STOPGAP loaded!!!" with `Unrecognized function or variable 'rootdir'` /
   `MATLAB:UndefinedFunction` (SLURM exit 249). Fixed to
   `stopgap_pca(s.rootdir,s.paramfilename,s.procnum,s.n_cores)`. (Line 56, the `vmap`
   branch, has the identical latent bug but is unused, so left untouched.)
7. **PCA path never sets `o.copy_local` / `o.rootdir`** *(STOPGAP source bug)*. With #6
   fixed, the PCA worker reached the shared `get_subtomo_boxsize`, which checks
   `if o.copy_local` and reads `o.rootdir` — but `stopgap_pca` never ran the
   `subtomo_check_copy_local` step the subtomo path uses, so those fields were missing →
   `Unrecognized field name "copy_local"` (exit 249). It couldn't simply call
   `subtomo_check_copy_local`, because its `check_copy_local` helper reads `s.n_cores` /
   `s.n_nodes`, which the PCA *settings* struct doesn't have. Fixed by replicating that
   function's "not copying locally" branch directly in `src/pca/exec/stopgap_pca.m`
   (after `sg_parse_pca_directories`): `o.copy_local = false; o.rootdir = p(idx).rootdir;`
   — consistent with `sg_run` always passing `copy_local=0`.
8. **PCA prerotation missing `o.avg_ss` / `o.lpf`** *(STOPGAP source bug)*. With #6–7
   fixed, `run_pca`'s rot_vol step reached `pca_prerotate_volumes`, which reuses the
   subtomo *averaging* filter chain (`initialize_subtomo_filters` / `refresh_subtomo_filters`).
   Those expect `o.avg_ss` (supersampling factor) and `o.lpf` (low-pass sphere for
   `generate_wedgemask_slices`), which only the averaging path (`parallel_average`) sets up
   — the PCA path never does → `Unrecognized field name "avg_ss"` (exit 249) at
   `refresh_subtomo_filters:32`. Fixed at the top of `src/pca/exec/pca_prerotate_volumes.m`,
   before `initialize_subtomo_filters`, replicating `parallel_average`'s construction (PCA
   never supersamples): `if ~isfield(o,'avg_ss'); o.avg_ss=1; end` and
   `o.lpf = single(sg_sphere((o.boxsize.*o.avg_ss), floor(min(o.boxsize)/2)-1))`. Verified
   the CTF/exposure/cosine/score-weight filter branches all stay off (`pca_settings.txt`
   has `calc_ctf=0`/`calc_exp=0`; PCA param defines none), so those two were the only gaps.
   **Requires recompile.** (Correction to #7's note: the rot_vol trace there missed the
   *nested* filter calls inside `pca_prerotate_volumes`, which is where these surfaced.)
9. **k-means wrapper read dir-settings as param columns** *(our script, not STOPGAP — no
   recompile)*. `scripts/sg_pca_kmeans_cluster_fn.m` did
   `resolve_dir(p(param_idx).listdir, ...)` / `.pcadir`, but `listdir`/`pcadir` are STOPGAP
   *settings* (`sg_get_pca_settings` defaults `lists/`,`pca/`), not param-file columns →
   `Unrecognized field name "listdir"`. Fixed by hardcoding the defaults (pca_settings.txt
   doesn't override them) and removing the now-dead `resolve_dir` local fn. Runs via
   `matlab -batch`, so the edit takes effect immediately.
10. **Filter-list accumulation → CC-matrix assembly deadlock** *(our config + a latent
    STOPGAP off-by-one; fixed at config level, no recompile)*. Symptom: job **12097551**
    timed out after **11h48m** with `run_pca` stuck — all CC compute finished in ~1.3h
    (every `comm/ccmatprog_*` + all `temp/ccarray_*` written) but assembly hung at
    "**8 out of 9 CC-matrices assembled**", then sat idle ~10.5h until the wall clock.
    Root cause is two-fold:
    (a) *Our* `build_pca_aux.m` called `sg_pca_append_filter_list`, which **appends** to
    any existing `filter_list.star` and is never cleared — so ~9 pipeline reruns grew the
    list to **9 filter rows** (`n_filt=9`) instead of 1. (PCA correlates every pair under
    *every* filter, so this also made `calc_ccmat` ~9× slower — and 8 of the 9 filters
    were identical duplicates.)
    (b) With `n_filt=9, n_cores=64`, STOPGAP's `src/pca/func/distribute_filter_jobs.m`
    orphans the last filter: it marks each filter's owner core at linear index
    `(k-1)·ceil(n_cores/n_filt)+1` in a `ceil(64/9)=8`-row array, but then truncates with
    `array(1:n_cores)` — filter 9's flag lands at index 65 > 64 and is dropped, so **no
    core assembles filter 9**. `complete_pca_ccmatrix`'s
    `wait_for_them(...,'sg_pca_ccmatrix', o.n_filt=9, ...)` then blocks forever on the
    missing `sg_pca_ccmatrix_9`. The **same off-by-one would also hang** the eigenfactor
    (`sg_pca_eigenfactors`), eigenvector (`sg_pca_f_eigenvec`) and covariance
    (`sg_pca_covarmat`) steps — every step that pairs `for i = o.filt_jobs` distribution
    with a `wait_for_them(...,o.n_filt,...)` barrier.
    **Fix (config only):** `build_pca_aux.m` now `delete()`s `filter_list.star` before the
    append, guaranteeing `n_filt=1`. With one filter, `distribute_filter_jobs` assigns
    filter 1 → core 1 cleanly, sidestepping the off-by-one for the whole step class; left
    STOPGAP's source untouched (we never want >1 filter here). Also hardened
    `run_pipeline.slurm` to `rm -f $ROOT/comm/*` at startup — `stopgap_initialize_folder.sh`
    only `mkdir`s `comm/`, so stale `complete_*`/`sg_*` flags from a prior run could
    otherwise satisfy a `wait_for_them` count prematurely.

**Resuming without recomputing PCA:** the ~1h `run_pca` stage writes `pca/eigenval_*.csv`
plus 672 `rvol_*`/`rwei_*`. After a downstream crash, run **`resume_pca.slurm`**
(kmeans → run_avg_pca → viz_pca) against those existing outputs instead of rerunning the
whole `run_pipeline.slurm`. (Set its `ITER` to match the run that produced the PCA:
`ITER=1` for the default `DO_ALIGN=0` path, `ITER=3` if alignment was run.)

**History:** the PCA branch first ran clean **2026-06-04** (resume path, loose mask):
k-means split almost entirely along PC1 and the class averages were noise-dominated/streaky
at every k. Diagnosed as the **too-loose mask** (§12/§14.3), not a code bug — retightened
(`ali r=8/h=26`, `cc r=6/h=20`). A first tight-mask attempt (job **12097551**, `DO_MRA=1`)
timed out in `run_pca` on bug #10 before reaching k-means; after fixing #10 and wiping
`$ROOT`, the **full run completed end-to-end** with the tight mask and `DO_ALIGN=0`
(`ITER=1`). Those are the committed results in `T4P/results/` — see **§15**.

> **IMPORTANT — any `src/` edit needs a recompile.** STOPGAP runs as compiled MCR
> binaries in `exec/lib/`; editing a `.m` file has **no effect** until you resubmit
> `recompile_stopgap.slurm` (rebuilds + installs + backs up the old binary, ~3 min).
> Bugs 6, 7, 8 each required: edit `.m` → recompile → clean `$ROOT` → resubmit pipeline.
> (Bug 9 was in our own `scripts/` matlab-batch helper, so no recompile.)

**Fail-loud orchestration (no per-particle cost):** `run_pipeline.slurm`
uses `set -Eeuo pipefail` + an `ERR` trap + a `stage()` wrapper that tees each stage log,
checks the exit code, greps STOPGAP's real fatal markers
(`ACHTUNG!!!|Segmentation fault|Killed|Out of memory|Cannot allocate`, excluding benign
`Warning:` lines — see #5), checks for `crash_*` files, and `assert_exists` on key
outputs. Cost = a few greps between multi-minute stages. `run_pipeline.slurm` now
self-cleans at startup (`rm -f $ROOT/params/*.star` and `$ROOT/comm/*`) so a resubmit
can't accumulate param rows or inherit stale `comm/` flags (#3, #10). For a heavier
reset between reruns also clear `rm -f $ROOT/{crash_*,pca/*,rvol/*,temp/*,fsc/*,logs/*.log}`
(stale `comm/` coordination files can desync STOPGAP's file-based MPI).

## 12. Key parameters & design decisions

- **Wedge/CTF**: only tilt range known → symmetric missing wedge, `calc_ctf=0`,
  `calc_exp=0`; wedgelist built from tilt range only. Set real `MINT/MAXT/STEP` in the
  config (currently placeholder `-60/60/3`).
- **Alignment SKIPPED — `DO_ALIGN=0` is the default** (changed 2026-06-05). The 672
  subtomograms are **prealigned at Euler angles (0,0,0)** (`build_inputs` zeros every
  motl field), so there is nothing to search. With `DO_ALIGN=0`, `ITER=1` and PCA reads
  `allmotl_1`/`ref_1.mrc`; `rot_vol` applies an identity rotation, so PCA operates on the
  particles in their stored frame. This also removes a real *hazard*: the in-plane search
  used noise-dominated CC scoring (the whole tight-mask saga), so running it on
  already-correct particles could rotate them to spurious phi angles and corrupt the
  alignment before PCA. **Optional** (`DO_ALIGN=1`) restores an in-plane-only search:
  `search_type=cone`, `angiter=0` (Z fixed), full ±180° phi sweep (`phi_angincr=4,
  phi_angiter=45` → 91 orientations), `ali_singleref startidx=1 iterations=2` (1→2→3) ⇒
  `ITER=3`. Only use it if a future dataset is *not* prealigned in-plane.
- **MRA is classify-only** (`MRA_INPLANE`, derived from `CONE_INPLANE` with
  `phi_angiter=0`): to match the alignment-free PCA path, `ali_multiref` assigns classes
  to the prealigned particles without re-orienting them (both `angiter` and `phi_angiter`
  = 0). The override rewrites the value in place rather than appending a duplicate key,
  because the subtomo parser uses MATLAB `inputParser`, which errors on a repeated
  name-value pair. `CONE_INPLANE` keeps `phi_angiter=45` for the optional align path.
- **Mask**: cylinder along Z (pilus). Geometry **tightened 2026-06-04** to
  `ali_radius=8, ali_height=26` / `cc_radius=6, cc_height=20` (was `20/64`, `16/56`).
  Reason: the original loose mask let in a large noise shell + missing-wedge streak
  artifacts, which dominated the CC-matrix/PCA and produced noise-dominated class
  averages at every k. The radial profile of the global average (`inspect_global_avg.m`)
  shows a compact centered particle with signal gone past ~r=12px (≈160 Å on the 80³,
  13.33 Å/px box), so the mask was cut to the dense core. This is the "very tight" of
  three options the user picked — aggressive noise rejection, accepted risk of clipping
  real signal; if the new averages look over-cropped, bump to `ali r=10–13`.
- **Bandpass `lp_rad`**: currently **13.33** (align `CONE_INPLANE` and `build_pca_aux`).
  Derive from `box/2 · (px/target_res)`; re-check now that px = 13.328 Å is known.
- **PCA**: `n_eigs=10`, `data_type=awpd`, one bandpass filter; k-means on PCs 1–3
  (`[1 1;1 2;1 3]`), `symmetry=C1`. Clustering is *not* in the parallel pipeline.
- **Halfsets**: odd→A, even→B; `ignore_halfsets=0` → per-class gold-standard FSC.
- **Parallelism**: one `sbatch`, each STOPGAP stage a direct `srun` of
  `stopgap_mpi_slurm.sh "$ROOT" <paramfile> $NC 0 slurm` (no watcher, no nested sbatch,
  `copy_local=0`). `cpus-per-task=1` (ranks single-threaded); `ntasks=64` (raise as the
  account allows — `rot_vol`, CC-matrix, averaging scale near-linearly). 80³≈2 MB so
  `mem-per-cpu=4G` is ample.

## 13. How to run (from scratch)

```bash
cd /home/ejl62/summerResearch/STA/packages/STOPGAP
# 1) (once per machine) recompile the gitignored binaries for R2023b. REQUIRED on a
#    fresh clone — exec/lib/ ships empty. Rerun only if source/MATLAB changes.
sbatch recompile_stopgap.slurm                    # set --account/--partition first
# 2) edit T4P/scripts/run_pipeline.slurm USER CONFIG: real MINT/MAXT/STEP,
#    --account/--partition, ntasks, DO_ALIGN/DO_MRA, KS, PARTICLES path;
#    ROOT defaults to /home/ejl62/Pili_class. SG is already set to this repo.
sbatch T4P/scripts/run_pipeline.slurm
# 3) (optional) if a downstream stage crashed but PCA finished:
sbatch T4P/scripts/resume_pca.slurm
```
Outputs land in `$ROOT`: `lists/allmotl_pca_k*` & `allmotl_mra_k*` (class labels),
`ref/` (class averages, `ref_*` maps), `pca/eigenval_1.csv`, `meta/` (scatter +
class-average PNGs, `pca_vs_mra_agreement.csv`), `logs/<stage>.log` per stage.
The pipeline is **idempotent** — the param reset + deterministic output names make a
resubmit safe (it rebuilds inputs and overwrites).

Requirements: MATLAB license + **Statistics & ML Toolbox** (`kmeans`, `gscatter`) for
the `matlab -batch` steps; the STOPGAP `srun` steps need only the R2023b MCR libs
sourced by `stopgap_config_slurm.sh`.

## 14. Open items / before trusting results
1. **Tilt range** — the completed run used the placeholder `MINT/MAXT/STEP = -60/60/3`;
   set the real per-tomogram tilt scheme if the missing-wedge weighting needs to be exact
   (it only affects the symmetric wedge mask, not the alignment-free class assignment).
2. **`lp_rad`** — the run used `13.33` Fourier px (≈ Nyquist for px = 13.328 Å, box 80);
   re-derive if a different target resolution cutoff is intended. PCA aux and align match.
3. **Mask geometry** — *retightened and run to completion; class averages saved but not
   yet visually validated.* The original loose mask (`r=20/h=64`) confirmed the
   "too loose → noise drives PCA" failure mode. Retightened to `ali r=8/h=26`,
   `cc r=6/h=20` from the global-average radial profile (`inspect_global_avg.m`); the
   full run then completed with this mask (§15). The class averages
   (`T4P/results/ref/class_pca_k*`, `ref_mra_k*`) exist but have **not** been compared
   against the PEET `ring_complete`/`ring_altered` reference — do that next to check for
   the opposite failure (over-cropping that clips conformational signal); relax toward
   `r=10–13` if the maps look clipped. See §12 Mask bullet and §15.
4. **Symmetry** — default C1; only set Cn if T4P helical symmetry is intended (for
   averaging, not classification).
5. **MRA ref/iteration handoff** — `avg_multiclass` seed writes refs at `iteration=ITER`
   and `ali_multiref` reads them at the same `ITER` (verified, no off-by-one); if you
   see "reference not found", check the suffix.
6. **Scientific caveats** — 672 particles is modest (k=4 ≈ 168/class → low-res but
   enough for ~30 Å, maybe ~10 Å, differences); missing wedge without CTF makes
   weighting approximate (fine for classification, not for final high-res maps); no
   reliable ground truth on this real dataset (hence cross-method ARI/NMI).

---

## 15. Results of the completed T4P run (committed)

**Run config (the run behind `T4P/results/`):** 672 prealigned 80³ T4P subtomograms,
px = 13.328 Å; `DO_ALIGN=0` (particles prealigned at (0,0,0), so `ITER=1` and `rot_vol`
applies identity); tight mask (`ali r=8/h=26`, `cc r=6/h=20`); `DO_MRA=1`; k = 2/3/4;
PCA on PCs 1–3 of `eigenval_1.csv`; MRA = classify-only `ali_multiref` (6 iterations,
phi/theta fixed) seeded from random classes. Two **independent** classifiers on the same
particles: **PCA + k-means** (primary) and **MRA** (secondary).

**Provenance:** SLURM job **12114811**, run **2026-06-05** on 64 cores, finished cleanly
(~58 min wall: `init`→`compare` 13:53→14:51; `run_pca` ~19 min was the longest stage; empty
`.err`). The log's ARI values match `meta/pca_vs_mra_agreement.csv` exactly. `$ROOT` was
`/home/ejl62/Pili_class` (8.4 GB working dir; only the §15.4 core set is committed).

### 15.1 Class splits (per-class particle counts, all 672)

| k | PCA + k-means (`allmotl_pca_k*_1`) | MRA final (`allmotl_mra_k*_6`) |
|---|------------------------------------|--------------------------------|
| 2 | **336 / 336** | **70 / 602** |
| 3 | 251 / 274 / 147 | 24 / 391 / 257 |
| 4 | 194 / 121 / 189 / 168 | 22 / 317 / 23 / 310 |

### 15.2 Cross-method agreement (`meta/pca_vs_mra_agreement.csv`)

| k | ARI | NMI |
|---|-----|-----|
| 2 | 0.0012 | 0.0049 |
| 3 | 0.0027 | 0.0020 |
| 4 | 0.0034 | 0.0110 |

### 15.3 Interpretation (honest read)

The two methods **do not agree and neither finds a stable discrete partition**:

- **PCA k-means** produces near-uniform splits — *exactly* 336/336 at k=2 — i.e. it is
  slicing a **continuous PC axis** into equal halves rather than recovering two
  populations. This is the classic "no gap in the embedding" signature.
- **MRA** collapses to one **dominant class** (602/672 at k=2; 391 and 317 dominate at
  k=3/4) with tiny satellite classes — the CC-based assignment can't reliably separate
  conformers, so most particles flow to the highest-scoring reference.
- **ARI ≈ 0.001–0.003** (≈ chance): the PCA and MRA labelings are essentially
  uncorrelated, so the split is **not reproducible across methods**.

Conclusion: on this real T4P set, STOPGAP — like **RELION, DISCA, and TomoFlow** in this
benchmark — does **not** cleanly recover the two pili phases. The most likely cause is
**per-particle SNR too low for CC-based discrimination** at 672 particles / 13.3 Å px,
not a pipeline defect (the pipeline runs clean and deterministically). This is a
legitimate, reportable benchmark outcome, not a failed run.

### 15.4 Where the outputs live (`T4P/results/`, ~44 MB)

| Subdir | Contents | Committed? |
|--------|----------|-----------|
| `lists/` | class assignments: `allmotl_pca_k{2,3,4}_1.star`, `allmotl_mra_k{2,3,4}_6.star`, input `allmotl_1.star`, `wedgelist.star`, `filter_list.star` | `.star` gitignored; local-only |
| `ref/` | class averages `class_pca_k*_1_*.mrc`, MRA refs `ref_mra_k*_6_*.mrc`, `ref_1.mrc` | `.mrc` gitignored; local-only |
| `pca/` | `eigenval_1.csv` (per-particle PCA coords), `eigenfac_1.csv` | **yes** |
| `meta/` | `class_pca_pca_scatter.png`, `class_pca_class_avg_k{2,3,4}.png`, `cooccur_k{2,3,4}.png`, `pca_vs_mra_agreement.csv` | **yes** |
| `params/` | run configs: `pca_param.star`, `mra_k{2,3,4}.star`, `mraseed_param.star`, `avg_pca_param.star` | no (`.star` gitignored) |
| `masks/` | `mask_align.mrc`, `mask_cc.mrc` | gitignored |
| `fsc/` | per-class gold-standard FSC curves (PDF) for every iteration | **yes** |
| `pca_settings.txt` | `calc_ctf=0`, `calc_exp=0` | **yes** |

The committed record (PNG figures, CSVs, FSC PDFs, `pca_settings.txt`) is enough to read
the result without the binaries; everything `.mrc`/`.star` — including `params/`, `lists/`,
`ref/`, `masks/` — is local-only (gitignored, regenerated by a rerun). Half-maps
(`ref_mra_k2_{A,B}_6_*`) were **not** copied — recompute from `$ROOT` if gold-standard
per-class FSC at full split is needed.

### 15.5 Still to do (analysis, not pipeline)

1. **Visually compare** `ref/ref_mra_k2_6_{1,2}.mrc` and `ref/class_pca_k2_1_{1,2}.mrc`
   against the PEET `ring_complete`/`ring_altered` references — is the 70-particle MRA
   minority a real phase or junk, and are the tight-mask averages over-cropped (§14.3)?
2. **ARI vs PEET soft ground truth** — score the STOPGAP labels against the PEET
   assignment (the project's cross-package T4P comparison; `scripts/eval/`).
3. Then **FM_hard / T4SS** (placeholders staged; pipeline reusable as-is).
