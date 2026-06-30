# STA Benchmark — Project Status

> **Single source of truth.** Every session starts by reading this (run `/status`) and ends by
> updating it (run `/handoff`). If reality and this file disagree, fix this file.
> Last updated: **2026-06-29** by Claude (T4P class avg panels + FSC: (1) standardised class-average figures generated for all 7 packages via `scripts/eval/gen_t4p_class_avg_panels.py` (XY central slice, particle counts, ring_complete/ring_altered/junk panels → `packages/figures/T4P/<pkg>_class_avgs_std.png`). (2) FSC computed for unsplit 672p baseline + Dynamo k=2 classes + PyTom k=3 classes via `scripts/eval/compute_t4p_fsc.py`; all-class FSC summary in `results/T4P/fsc_summary.csv`; figure at `packages/figures/T4P/fsc_comparison.png`. (3) **PyTom junk CONFIRMED by FSC:** class 3 (100p) resolves at 63.2 Å (FSC=0.143) vs Nyquist 26.7 Å for signal classes → clear junk verdict. PyTom junk status updated ✅. (4) E7 FSC gain evidence point addressed — unsplit FSC stays above FSC=0.5 to Nyquist (shared gross structure); class-specific FSC=0.5: ring_complete 63 Å, ring_altered 98 Å. `packages/README.md` updated with new figures + FSC block.).

## Now / Next / Parked

- **FM_hard PACKAGE RUNS IN PROGRESS (2026-06-30):** All 10 packages running on 813p assembly-intermediate
  dataset (base/basal_body/mature, 96³, k=3, no junk, `diff_mask_hard.mrc`). 6 done, 4 running:
  **PEET 0.078** (pc1_5; blind baseline) · **DISCA 0.014** (32³ CNN too coarse for ~15-20Å differences) ·
  **Dynamo −0.000** (dpkpca collapsed) · **EMAN2 0.008** (PCA split collapsed) ·
  **OPUS-TOMO 0.017** (VAE collapsed) · **RELION 0.000** (soft-EM collapsed, all-class2) ·
  PyTom RUNNING · ProTomo RUNNING · STOPGAP RUNNING · TomoFlow RUNNING.
  All PCA/alignment-based methods collapse (ARI≈0, blind baseline). DISCA also collapses (subtle inter-
  mediate differences ~15Å too fine for 32³ CNN). PEET near blind baseline (0.078 vs 0.07 chance). 
  Supervised ceiling 0.472. Registration wall confirmed across all 6 completed packages.
  Scripts: `packages/<pkg>/FM_hard/scripts/`. Output CSVs: `outputs/FM_hard/<pkg>/`.
  **NEXT:** Wait for PyTom/ProTomo/STOPGAP/TomoFlow to finish; collect all 10 ARI scores; update
  packages/README.md FM_hard table; commit FM_hard scripts + prediction CSVs; write handoff log.

- **T3SS PACKAGE RUNS COMPLETE (2026-06-30):** All 10 packages classified on T3SS injectisome
  (415p, 48³, class_B=IM ring present vs class_C=absent, +80 junk). ARI(B/C): DISCA **0.720/0.812**
  (best — CNN detects gross ring); PEET 0.069/0.083; STOPGAP 0.020/0.025; PyTom 0.005/0.009;
  OPUS-TOMO −0.013/0.041; ProTomo −0.032/—; Dynamo/EMAN2/TomoFlow/RELION ≈0. Key finding matches
  FM_easy: registration wall — GT-pose particles mis-register WBP, collapsing PCA axes; only
  CNN-based DISCA is immune. Output CSVs: `outputs/T3SS/<pkg>/`. Scripts: `packages/<pkg>/T3SS/scripts/`.

- **T4P EVAL FRAMEWORK — STANDARDISED (2026-06-29):** All T4P result CSVs normalised to
  `results/T4P/<pkg>_k<k>_std.csv` (columns: `particle`, `class_int`, `class_name`) by
  `scripts/eval/standardize_t4p_results.py`. Labels Hungarian-aligned to PEET reference for
  converging packages (class_int 1=ring_complete, 2=ring_altered, 3=junk). EMAN2 index→filename
  mapping applied. ProTomo extractor updated with `--include-junk` flag; `protomo_T4P_k3.csv` now
  covers all 672 rows. Consensus core corrected: **309/672 = 46%** (was 357/53% — k=3 PyTom now
  excludes 100 junk particles). Cross-pkg figure re-generated with updated numbers.
  **Junk audit:** PEET ✅ 68 / EMAN2 ✅ 85 / ProTomo ✅ 126 / PyTom 🟡 100 (assumed smallest
  class — verify by FSC) / Dynamo ❌ k=2 pending / DISCA ❌ k=2 pending / OPUS ❌ k=2 pending /
  STOPGAP ❌ no per-particle CSV.
  **Mask audit:** canonical cyl v2 (r=13, h_neg=25) used by PEET/PyTom/RELION/DISCA.
  STOPGAP used tighter cyl r=8/h=26 (undocumented deviation — Eben's). EMAN2/ProTomo use no
  external mask (package constraints). OPUS uses threshold mask (VAE constraint).
  All documented in `docs/datasets.md §Junk Class Protocol` and §Mask Exceptions.
  `gen_cross_pkg_correlation.py` + `build_labels_matrix.py` updated to use standardised CSVs.
  **Key numbers (ALL COMPUTED 2026-06-29):**
  - Pairwise ARI (all 6 pairs, 4 converging pkgs): **0.40–0.65** (Dynamo–PyTom 0.510, PEET–PyTom 0.653)
  - High-consensus core (all 4 agree with Dynamo): **309/672 = 46%**
  - Dynamo UMAP bootstrap Jaccard (Hennig, 20×80%): **0.562** weighted (class1: 0.587, class2: 0.513) [MODERATE]
  - Dynamo UMAP noise robustness: ARI decays **0.351→0.050** (σ=0→σ=2.0); PEET PCA k-means ARI≈0 (WMD gap — expected)
  - Note: σ=0 ARI=0.351 (not 1.0) reflects HAC-vs-k-means method gap; gradual decay is real-structure signal
  - STOPGAP PCA k-means (eigenval_1.csv, k=2): 385/287, ARI=0.07 vs Dynamo → confirms non-convergence
  **Junk class k=3 COMPLETE (2026-06-29):** All 9 packages with per-particle CSVs now have k=3 junk class:
  - **Dynamo k=3**: Ward HAC re-cut from existing CC matrix → 447/157/68junk; `dynamo_k3_std.csv`
  - **DISCA k=3**: existing `disca_cyl_v2_k3.csv` standardized → 315/267/90junk; `disca_k3_std.csv`
  - **OPUS k=3**: retrained 20 epochs (RTX 5080, ~2 min), analyzed at k=3 → 368/221/83junk; `opus_k3_std.csv`
  - Class-avg panels generated for all three; packages/README.md updated
  **STOPGAP COMPILED LOCALLY (2026-06-29):** R2024a mcc on Josh's node. All 4 binaries verified (stopgap, stopgap_parser, stopgap_watcher, sg_toolbox). Smoke test passed. Script: `packages/STOPGAP/compile_local_r2024a.sh`. STOPGAP can now run on Josh's node without the BYU RC cluster.
  **NEXT:**
  - Run FM_hard on all 10 packages (k=3, `diff_mask_hard.mrc`, start PEET/DISCA/Dynamo)
  - Run STOPGAP on FM_easy locally (first local STOPGAP run on Josh's node)

- **ALIGNED RE-RUN — registration fix re-runs all packages (2026-06-19):** Built a blind reference-based
  alignment of the FM_easy particles (`scripts/data_prep/align_fm_easy.py` — iterative translational FFT
  + rotational search to the masked global average; saved set `…/hc_test_x6/subtomos/merged_AC_aligned/`)
  and re-ran the packages on it. **Blind ARI, GT-pose → aligned:** PyTom (cyl) 0.262→**0.635** · Dynamo
  0.254→**0.475** · ProTomo 0.053→**0.383** · EMAN2 0.146→**0.326** · DISCA 0.407→**0.455** · PEET
  0.450→**0.330 (DOWN)** · RELION-blind 0.009→0.005 (**still collapses**). **Takeaways:** alignment
  *rescues the collapse cases* (ProTomo +0.33, PyTom +0.37, Dynamo +0.22, EMAN2 +0.18) → their failures
  were registration, not algorithm. **PEET drops** (its many-PC WMD already compensated; single-global-ref
  alignment adds a mild reference bias). **RELION soft-EM still collapses even aligned → genuinely
  algorithmic** (consistent with T4P). Class averages visibly sharpen after alignment
  (`packages/figures/FM_easy/align_old_vs_new.png`); comparison bar `aligned_vs_gtpose.png`. Scores under
  `*_ALIGNED` run tag. **⚠️ FOLLOW-UP (firm up magnitudes):** this used a *hand-rolled* blind
  reference-based alignment (single global reference). Swap in a **production aligner (e.g. Dynamo
  `dalign`, RELION/STOPGAP refine, or multi-reference)** to get unbiased magnitudes and confirm the
  PEET-drop is a single-ref-bias artifact. Also: reduce the jitter at the SOURCE in the simulator
  (`tilt_err`, WBP→SIRT). **NEXT: decide whether the benchmark protocol switches to aligned inputs
  (apples-to-apples with real T4P) and, if so, re-run with a production aligner.**

- **DIAGNOSIS — the synthetic-vs-real classification gap is REGISTRATION (2026-06-19):** Chased why real
  T4P's early PCs separate the two classes but synthetic FM_easy's don't, despite "the same" nuisances.
  **Ruled out (all measured):** (1) "real is pre-cleaned" — WRONG, T4P is *messier* (contrast CoV 0.59 vs
  synthetic 0.02); (2) "synthetic difference too small" — WRONG, between-class variance ≈ **2% in BOTH**
  (T4P 2.0–2.6%, FM_easy 1.7%), and the synthetic A–C voxel difference is the *larger* one; (3) "synthetic
  noise whiter/higher-rank" — WRONG, eigenspectra similar (participation ratio 160 vs 229); (4)
  "representation/preprocessing" — WRONG, bandpass + common-mode wedge mask + per-particle z-norm all fail
  to help (0.06–0.12 vs 0.14). **THE CAUSE = registration:** synthetic particles sit at **ground-truth
  poses** (correct for the clean map, NOT for co-registering the noisy/wedge-distorted WBP reconstructions).
  Reference-based refinement: blind masked-PCA ARI **0.14 (GT poses) → 0.26 (translational) → 0.32 (+coarse
  rotational)**; supervised ceiling on the refined set ~0.53. The PC diagnostic (PC1 = class r0.55 entangled
  with noise r0.42 + contrast r0.33; PC2/PC3 = orientation) reflects this mis-registration, not the wedge.
  **Why T4P differs:** its particles came from a real STA **alignment-refinement** pipeline (+CTF/dose/wedge
  weighting); the synthetic set never got that. **PROTOCOL IMPLICATION:** the "GT-poses / no-alignment" rule
  (meant to isolate classification) actually **handicaps the synthetic data** vs how real T4P was prepared.
  **Fix = classify the synthetic set from genuinely ALIGNED particles** (run a real subtomogram alignment,
  or let each package align). Bigger class difference / adding a membrane / switching simulator do NOT
  address it. Side finding: current FM_easy orient pool is constrained (x≤30°) → **common-mode wedge**
  (mean-power azimuthal ratio 0.00; PEET WMD has nothing to weight); a uniform-SO(3) batch makes the wedge
  **per-particle varying** (ratio 0.56) and collapses ARI 0.09→0.00 (so wedge variance IS devastating, but
  absent by design here). Memory [[fm-easy-registration-is-the-gap]]; orient workspace
  `~/Research/synthetic_sta/motor_orient_test/`; diagnostic figs `packages/figures/FM_easy/{pc_factor_diagnostic,
  orient_wedge_test,eigenspectrum_t4p_vs_synth}.png`. **NEXT: (1) bake a real alignment into the FM_easy
  pipeline + re-run packages from aligned particles; this likely lifts every package's blind score.**

- **FM_hard BUILT — 3-class flagellar-motor ASSEMBLY-INTERMEDIATE dataset (2026-06-17):** New synthetic
  benchmark, *slightly harder than FM_easy*. **3 inside-out assembly stages from EMD-5311** (axial-truncation
  cuts, ×6 contrast, same ETSim→WBP→extract pipeline as FM_easy): **base** (C-ring + MS-ring) → **basal_body**
  (+ proximal rod + P-ring, no hook) → **mature** (full motor + hook/bulb). `base` ≡ FM_easy's C and `mature`
  ≡ FM_easy's A (same maps/frame) → directly comparable; the inserted middle stage is the difficulty lever.
  **271 × 3 = 813 particles, 96³, 13.329 Å/px, SNR 0.299, GT-aligned, no junk.** Canonical input
  `~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/` (+`labels.csv`; local). Mask = data-driven
  3-class diff mask `motor_hard/maps/diff_mask_hard.mrc` (~6% box). **Calibration (balanced):** blind
  masked-PCA k=3 ARI **0.07**; supervised 5-fold 3-way ceiling **0.472 / 78% acc**; pairwise ceilings
  base↔mature **0.752** (= FM_easy A–C 0.745 → pipeline cross-check ✓), base↔basal_body **0.611**,
  basal_body↔mature **0.347** (the +bulb step is the wedge-sensitive bottleneck). Pipeline (local, not repo):
  `motor_hard/{make_variants_hard.py,run_full.sh,classify_hard.py}` + self-contained `motor_hard/inputs/`
  (`sim_clean.txt` = sim_13A+dose5000, `orient_pool.txt`, `coords/`). **Gotcha (durable):** do NOT reuse
  ETSim's *consumed* `temp_0/sim.txt` as a master config — re-feeding it mis-simulates (CC 0.07 vs 0.32);
  rebuild a clean master from `sim_13A.txt`. **NEXT:** run all 10 packages at **k=3, no junk** (reuse each
  package's FM_easy config pattern + `diff_mask_hard.mrc`; PEET/DISCA/Dynamo first as FM_easy leaders),
  score → `results/synthetic_scores.csv` (tag `*_ABC_hard_x6_813`), fill the `packages/README.md` FM_hard
  table (skeleton already in place, mirrors FM_easy) + confusion/class-avg figures. STOPGAP blocked (cluster).

- **DISK CLEANUP — synthetic_sta pruned 556G → 199G (2026-06-17):** `/home` was at 100% (245M free),
  blocking work; cleared obsolete synthetic runs to **60% used / 354G free**. **Deleted:**
  `motor_easy/production/` (old scrapped 3-class set), `motor_easy/{run_A,run_B,run_C,test_random,
  snr_test,subtomos_all,subtomos_proc,subtomos_aln}` (June-1 early runs), `motor_easy/{hc_test,
  hc_test_x10,hc_test_nw}` (×3/×10/narrow-wedge experiments superseded by `hc_test_x6`),
  `motor_easy/share_professor/` + `professor_demo/` (one-time deliveries), `nora_test/NorA_0_rec*.mrc`.
  **Kept (canonical/active):** `motor_easy/hc_test_x6/` (FM_easy canonical), all of `motor_hard/`
  (active), and full tomograms in canonical sets (chose not to strip ~128G of `tomo_rec*.mrc`).
  ⚠️ **ERROR — motor_switch canonical set deleted by mistake:** I removed `motor_switch/production_5apix/`
  (the **active 5 Å/px / 160³ set** all motor_switch package runs used) thinking 5 Å/px was off-target;
  it was actually canonical (the 13.33 Å/px `production/` was the superseded one). The 5apix raw
  subtomos/tomograms (incl. `all_particles_aligned/`) are **GONE, no backup**. **Recoverable by
  regeneration** — `motor_switch/maps/5apix/` + `*_5apix.sh` ETSim scripts + `extract_subtomos_5apix.py`/
  `align_all_5apix.py` are intact, and all derived results (scores, predictions, confusions) are committed.
  Decided to **leave it for now** (regenerate only if motor_switch needs re-running). Old 13.33 `production/`
  also deleted (confirmed superseded). See updated motor_switch entry under Datasets.

- **FM_easy REDESIGNED → 2-class high-contrast (542p) + ALL 10 PACKAGES RE-RUN at k=2 (2026-06-16):**
  Old 3-class 694p production-contrast set (every package ARI≈0) **scrapped/archived**; replaced by the
  achievable "easy tier" = **2-class A (mature full motor) vs C (early cytoplasmic base), 271+271=542
  particles, ×6 model contrast (SNR 0.340), 96³, 13.329 Å/px**, GT-aligned. Canonical input
  `~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/` (+`labels.csv`); mask =
  A-vs-C diff sphere `diff_sphere_r23_y55.mrc`. Built by extending the hc pipeline to runs 01–08/class
  (`hc_test/run_full.sh`, `align_classify_full.py`). **BLIND benchmark results (k=2, ARI / Acc) — all
  packages run unsupervised, no class info:**
  **PEET WMD-PCA pc1_10 0.450 / 0.836** · **DISCA 0.407 / 0.819** · **PyTom 0.262 / 0.757 (cylinder mask)** ·
  **Dynamo dpkpca 0.254 / 0.753** · **EMAN2 0.146** · ProTomo 0.053 · TomoFlow 0.036 · **RELION blind 0.008** ·
  OPUS-TOMO 0.008.
  **MASK STANDARDIZATION (2026-06-17):** canonical FM_easy mask = A-vs-C diff sphere (8.7% of 96³ box) —
  used by PEET/DISCA/Dynamo/EMAN2/ProTomo. EMAN2 & ProTomo were **re-run** on the diff sphere
  (EMAN2 0.025→**0.146**, ProTomo 0.030→**0.053**; the focus mask materially changes the result). RELION
  (broad solvent-flattening mask, 21%) and OPUS (broad threshold mask, 15%) *require* broad masks — kept
  as documented exceptions; TomoFlow has no mask step (OF on full volume). EMAN2 diff mask = `e2proc3d`
  hdf; ProTomo diff mask = `i3cut`-converted `mask_diff.i3i`.
  **CYLINDER-VS-SPHERE MASK SWEEP (2026-06-17):** tested a cylinder (r=27 in X-Z, height 24 along the Y
  motor axis, `diff_cyl_r27_h24_y52.mrc`, 9.9%) on all 6 diff-mask packages. **Cylinder helped ONLY PyTom**
  (CC/template `auto_focus`: 0.031→**0.262**, converged iter6 — adopted as PyTom's canonical FM_easy mask)
  and **hurt every PCA/learned-feature method** (PEET 0.450→0.309, DISCA 0.407→**0.005**, Dynamo 0.254→**−0.002**,
  EMAN2 0.146→0.117, ProTomo 0.053→0.044). Reason: the A-vs-C signal extends *axially* (along Y); the cylinder
  crops that height, so PCA loses the discriminative variance, while a CC method benefits from the tighter
  focus. Sweep recorded under `*_CYL` tags in `results/synthetic_scores.csv`.
  **ProTomo deep-dive (2026-06-17):** ProTomo's poor score is a **factor-selection** problem, not the mask —
  its HAC clusters on `hacfactors 1-4` (the top SVD factors = the dominant *nuisance/contrast* axis); the
  class signal lives in higher factors (sweep: 1-4→0.068, **5-20→0.161**, same as PEET pc1_3 0.08 → pc1_10 0.45).
  T4P worked at 1-4 because its two-phase difference IS the dominant variance. Blind factor selection
  (which factors carry class signal) is unsolved → ProTomo's honest blind score stays ~0.05.
  **Supervised upper bounds (NOT in the ranking, reference only):** RELION **GT-seeded** iter1 0.764 /
  0.937 (initialized from the true A & C class averages — effectively supervised; collapses to 0.435 by
  iter2) ≈ the independent **logreg 5-fold ceiling 0.745** — i.e. GT-seeded RELION measures recoverability
  with labels, not blind ability. ⚠️ **Fairness correction (2026-06-17):** earlier draft ranked RELION at
  top via GT-seeding — that gave RELION the answer (the GT density maps) the other packages never got.
  Re-ran RELION **blind** (global-avg init, no `--firstiter_cc`, no GT refs): ARI 0.008 (split 56/486,
  near-collapse) — consistent with the documented blind-RELION SNR failure. **Pattern at high contrast:**
  the BLIND field splits between methods that find the *class axis* (PEET many-PC, DISCA, Dynamo:
  0.25–0.45) and methods that collapse onto a *nuisance/contrast axis* (TomoFlow, PyTom, ProTomo SVD+HAC,
  EMAN2 PCA, RELION soft-EM, OPUS VAE: ≈0) — even though the supervised ceiling is 0.75. The redesign
  separates "method finds class axis" from "method finds nuisance axis," which is the benchmark signal.
  **ERROR-OVERLAP ANALYSIS (2026-06-17, `scripts/eval/fm_easy_error_overlap.py`):** do the blind packages
  miss the *same* subtomos? Mostly **NO** — best-permutation per-particle errors across all 9: **no particle
  missed by all 9** (max 7/9, only 4 particles; modal miss-count 3–4/9, errors spread not concentrated).
  The 3 recovering packages miss **nearly disjoint** sets — PEET–DISCA error Jaccard **0.00**, PEET–Dynamo
  0.02 (*below* the chance level 0.09–0.11 expected if independent), and **0 particles missed by all three**
  → PEET/DISCA/Dynamo are complementary, a consensus would correct almost everything (publishable: argues
  for ensemble/consensus classification). Collapsed packages overlap more (TomoFlow/ProTomo/EMAN2 Jaccard
  ≈0.48–0.54) only because they fail the *same class*, not because they share hard particles. Top-5
  most-missed subtomos = heavily missing-wedge-streaked / low-SNR reconstructions (mix of GT A & C), i.e.
  the hardest particles are degraded reconstructions, not one conformation. Figures: `packages/figures/FM_easy/
  error_overlap_jaccard.png`, `missed_top{1..5}.png`; also added mask-overlay + 2-class perfect-confusion
  figures and rewrote the main `README.md` synthetic section for the 2-class design.
  **STOPGAP: UNBLOCKED (2026-06-29)** — R2024a mcc compiled all 4 binaries locally (`compile_local_r2024a.sh`); smoke test passed. `run_type='local'` + `mpiexec` eliminates SLURM dependency. Can now run FM_easy/FM_hard locally.
  Old k=3 outputs → `outputs/FM_easy/_archive_3class_k3/`; old scores → `results/_archive_motor_easy_3class_scores.csv`.
  New per-package preds/confusions in `outputs/FM_easy/<pkg>/`; scores in `results/synthetic_scores.csv`
  (`*_AC_hc_x6_542`). Scripts: `scripts/data_prep/setup_relion_motor_easy_hc.py` +
  `scripts/run_relion_motor_easy_hc.sh`, `scripts/data_prep/run_disca_fm_easy_hc.sh`,
  `~/Research/eman2_motor_easy_hc/run_pipeline.sh`, `packages/PyTom/FM_easy/scripts/*_hc_*`,
  `packages/peet/FM_easy/scripts/*_hc*`, `packages/opusTomo/FM_easy/scripts/*_hc_*`,
  `~/Research/protomo/motor_easy_hc/`, `packages/dynamo/FM_easy/scripts/setup_hc_pair_pca.py`.
  Scripts: `scripts/run_relion_motor_easy_hc_blind.sh` (blind, fair) + `scripts/run_relion_motor_easy_hc.sh`
  (GT-seeded reference); blind preds `outputs/FM_easy/relion/run_k2_blind/`. **NEXT:** run STOPGAP on the
  RC cluster (Eben); update figures gallery + per-package READMEs; consider nc-sweep Dynamo toward ceiling.

- **FM_easy — HIGH-CONTRAST REGENERATION TEST COMPLETE (2026-06-16, decisive):** Regenerated A/C through
  the real ETSim→WBP→extract pipeline at higher model contrast (×3/×6/×10 of base vs production ×0.1) and
  classified blind. **Findings:** (1) **SNR saturates ~0.4** — scaling model amplitude past ×3–×6 does NOT
  raise SNR (×10 *dropped* to 0.30); strong-phase nonlinearity caps achievable SNR. So you can't buy
  arbitrary SNR via contrast. (2) **Narrowing the missing wedge doesn't help** — ±70°/2°/71 (40° wedge) vs
  ±60°/3°/41 (60° wedge) at matched contrast/dose: ARI 0.12 vs 0.18 (same within noise). Wedge is NOT the
  dominant nuisance. (3) **But contrast strongly helps the recoverable signal:** at the best condition
  (×6, SNR 0.36, 354 particles) the **supervised 5-fold ceiling jumped to ARI 0.796 / 95% acc** (was 0.43
  at production SNR 0.21). (4) **Real-package payoff — Dynamo dpkpca k=2 went 0.003 → 0.280** (acc 0.77,
  a 95%-pure C cluster: 99 C / 5 A); blind masked-PCA 20-seed = 0.151±0.006. **CONCLUSION: the wall is
  REPRESENTATIONAL, not signal-absence** — blind clustering optimizes dominant variance (nuisance/contrast
  axis), but the class difference is strongly present & 95%-recoverable with labels at higher contrast. An
  **achievable easy tier = higher contrast + a method pointed at the class axis** (GT-seeded RELION, nc-swept
  Dynamo, or a good projection like band-Y 0.81); blind voxel k-means is the weak link, and that
  blind-failure-with-ground-truth is itself the headline benchmark result. Pipeline: `synthetic_sta/motor_easy/
  hc_test*/` (`run_contrast.sh`, `run_narrow_wedge.sh`, `run_full.sh`, `align_classify_full.py`); proxies
  `scripts/eval/colored_noise_{snr,jitter}_proxy_motor_easy.py`; Dynamo hc run
  `packages/dynamo/dynamo_outputs/easy_pair_AC_hc/` (ARI 0.280, `confusion_dynamo_hc.png`). **Visual
  confirmation (2026-06-16):** rendered high-contrast subtomos (legible per-particle: A shows the full motor
  with density extending down the box, C truncated to the top base), GT class averages (A=extended assembly,
  C=base only), and **Dynamo's two cluster averages — which match the GT classes** (cluster1 95%-pure C =
  truncated/empty-below, cluster2 A-enriched = extended density), i.e. Dynamo split on the *real* structural
  axis, not a nuisance axis. **NEXT: nc-sweep Dynamo + GT-seeded RELION on the hc set to see how close to the
  0.80 ceiling a real method reaches; decide easy-tier contrast level for a full regeneration.**

- **FM_easy — SNR IS A REAL LEVER (CORRECTION, 2026-06-16 later):** The earlier "SNR is a dead lever"
  conclusion (below) was based on an **idealized white-noise, no-wedge** sweep and is **WRONG**. A
  **faithful proxy** (real ±60° Z-wedge + colored noise whose 3D PSD is *measured* from real class-A
  subtomos) separates A–C at **ARI≈1.0 even at the real SNR 0.21** — so wedge + colored noise + low SNR
  are NOT the wall. **The wall is per-particle registration JITTER:** injecting ~20–30° equivalent rigid
  pose jitter (stand-in for WBP/wedge/noise-induced misregistration of reconstructed densities) drops ARI
  to ~0 at matching SNR, reproducing the real failure. **Jitter and SNR trade off (rescue curve):** at 20°
  jitter a 2× SNR boost (0.21→0.42) lifts ARI from ~0 to **0.77**; at 30° jitter it needs 4–8× and stays
  noisy. So raising **contrast** (not dose — dose is saturated at ~2000 e/Å²) can rescue the easy tier if
  effective jitter is moderate. Empirical pipeline facts: wedge is **perpendicular to the motor/difference
  axis and common-mode** (favorable, not the smear I earlier guessed); **no membrane is modeled** (motor
  floats in ice; "plates" = MS/P-L ring densities). Scripts: `scripts/eval/{colored_noise_snr_proxy_motor_easy,
  colored_noise_jitter_proxy_motor_easy}.py`; rescue curve `outputs/FM_easy/input_qc/snr_rescue_curve.png`.
  Real-package A–C runs (diff mask, raw aligned): Dynamo dpkpca **0.003**, RELION Class3D **0.014**;
  RELION local-realign best **0.047** (global realign scrambles GT poses → 0.004). **NEXT: regenerate a
  small A/C batch at higher contrast (model amp ×2–×5, target SNR≈0.6) through ETSim→WBP→extract and
  classify — decisive test of the rescue curve on the real pipeline.**

- **FM_easy ROOT-CAUSE ANALYSIS COMPLETE — WHY BLIND CLASSIFICATION FAILS (2026-06-16):** Full writeup
  `docs/fm_easy_classification_analysis.md`; durable memory [[fm-easy-classification-wall]]. Findings:
  (1) **Classes are axial halves**, not C-ring edits — A=whole motor, B=periplasmic/upper plate,
  C=cytoplasmic/lower plate (EMD-5311 geometric cuts; `noCring`/`noRodHook` names corrected in memory).
  (2) **Signal is present; failure is representational** — a 1-D band-position feature separates B–C at
  **ARI 0.81 unsupervised**; supervised ceilings A–B 0.20 / A–C 0.43 / B–C 0.54; but blind masked
  PCA+kmeans ≤0.15. (3) **Real-package confirmation:** Dynamo dpkpca k=2 on raw aligned subtomos + best
  spherical mask → **A–C ARI=0.001, A–B=0.026** (chance). (4) **[PARTIALLY SUPERSEDED — see CORRECTION above]**
  The wall is per-particle **nuisance/jitter variance**, confirmed — but the original "raising SNR is a dead
  lever" sub-claim is WRONG (it rested on a white-noise, no-wedge sweep). The faithful colored-noise+wedge
  proxy shows SNR and jitter **trade off**, and raising contrast *can* rescue. 3D-jitter sweep collapses
  A–B at 20°/3px, A–C at 40°/4px (B–C robust), reproducing the real failure ordering. (5) **Deep finding:**
  biologically-real assembly intermediates are NESTED (additive) → "subtle additions on shared bulk" →
  least nuisance-robust; the only robust geometry (disjoint density, B–C) is biologically impossible →
  in-situ assembly-intermediate classification is intrinsically hard for blind STA (publishable). **Best
  spherical mask r≈22 px (~293 Å).** Scripts: `scripts/eval/{qc_motor_easy_class_avgs,
  pairwise_pca_kmeans_motor_easy,diffmask_test_motor_easy,snr_sweep_motor_easy,nuisance_sweep_motor_easy}.py`
  + `packages/dynamo/FM_easy/scripts/{setup_easy_pair_pca.py,dynamo_easy_pair_pca.m,score_easy_pair.py}`.
  **NEXT (UPDATED — see CORRECTION above):** craft the EASY 2-class dataset = early cytoplasmic base (C)
  vs mature full motor (A); levers are (i) higher contrast, (ii) lower jitter/better reconstruction,
  (iii) grosser/disjoint difference — NOT "don't raise SNR" (that was wrong). Hard 3-class = nested stages.

- **EMAN2 FM_easy (motor_easy) COMPLETE (2026-06-15):** EMAN2 no-align PCA split (`e2spt_pcasplit`) on the 694 GT-aligned particles, **k=3 no junk** (no `--clean`), NBASIS=12, **MAXRES=40 Å** (finer than T4P's 60 to resolve the ~30 Å conformational differences at 13.329 Å/px), auto-tight density mask, identity orientations. **Result: split 81/94/519, ARI=−0.0015** (AMI=0.096, V=0.099, Acc=0.395) — collapses to one dominant cluster (519, ~75%); GT class C lands 100% in it (0/0/177), A/B smeared. **Misses the 3-class structure** — same contrast/intensity-axis PCA behavior documented on T4P, now on data with GT. **Note:** `e2spt_pcasplit --clean` adds an extra outlier class (NCLASS+1) = de-facto junk rejection, so for the no-junk protocol I dropped `--clean` to get a clean 3-way partition. Project: `~/Research/eman2_motor_easy/` (local; env at `~/conda-envs/eman2`). Pred CSV `outputs/FM_easy/eman2/eman2_motor_easy_k3.csv`; confusion `outputs/FM_easy/eman2/confusion_eman2_k3_motor_easy_k3.png`. **FM_easy now 8/10: RELION 0.475(GT) / Dynamo 0.200 / PyTom 0.134 / PEET 0.116 / DISCA 0.036 / OPUS 0.021 / ProTomo −0.003 / EMAN2 −0.002. Next FM_easy: TomoFlow, STOPGAP.** Pattern: every package except GT-seeded RELION and Dynamo dpkpca collapses or splits on a non-conformational axis; the dominant cluster consistently absorbs all of class C (ProTomo/EMAN2/OPUS).

- **PROTOMO FM_easy (motor_easy) COMPLETE (2026-06-15):** I3/ProTomo 3.1.0 on the 694 GT-aligned motor_easy particles, **k=3 (no junk, FM_easy protocol)**. **Result: split 517/103/74, ARI=−0.003** (AMI=0.077, V=0.080, Acc=0.382) — SVD+HAC collapse to one dominant cluster (class 0 ≈ 75%); GT class C lands almost entirely in cluster 0 (174/0/3), A/B smeared. **Does NOT recover the 3-class conformational structure** (contrast with T4P, where ProTomo separated the two phases visually). Mask = canonical FM_easy solvent sphere (r=32 Y-10, 96³) applied as the SVD mask (`MSAMASK`, `MSAIMGSIZE=96³` so full box, no central crop). Alignment bypassed (raw→mra copy; particles GT-aligned). **Pipeline-build gotchas (durable):** (1) the subtomo *series* `dataset.i3i` must be built with **`tomoprepare`** (the `attach`/`search`/`save` `.prep`), NOT `tomoprocess` (docs were wrong) and NOT `i3concat` (that makes a 4D *hypervolume* tomoclass reads as 1 image); a real series has centered spatial coords `[-48..47]` + 0-based index axis and references the MRCs by basename via `i3_filepath`. (2) `tomoclass dataset` rejects absolute paths. (3) "no junk" requires `CLSHVO`/`CLSHVM` **empty** (not `0`, which errors as invalid `hacoptions`). (4) `cycle-000/param.sh` is copied at init and overrides edits to `param-template.sh` — sync both. Workspace: `~/Research/protomo/motor_easy/` (`prepare/dataset.prep`, `process/param-template.sh`, `run_motor_easy.sh`). Pred CSV `outputs/FM_easy/protomo/protomo_motor_easy_k3.csv`; confusion `outputs/FM_easy/protomo/confusion_protomo_k3_motor_easy_k3.png`. **FM_easy now 7/10: RELION 0.475(GT) / Dynamo 0.200 / PyTom 0.134 / PEET 0.116 / DISCA 0.036 / OPUS 0.021 / ProTomo −0.003. Next FM_easy: EMAN2, TomoFlow, STOPGAP.**

- **DISCA FM_easy (motor_easy) COMPLETE (2026-06-15):** Template-free DISCA on the 694 GT-aligned motor_easy particles, **k=3 (no junk, per `docs/datasets.md` FM_easy protocol)**. Mask = regenerated FM_easy solvent sphere (r=32 px ~427 Å, center (48,38,48) in 96³, 4 px cosine edge — the same RELION mask prior FM_easy runs used; the MRC was gone so I rebuilt it from the documented spec via new `scripts/data_prep/make_motor_easy_mask.py`). Particles masked then Fourier-cropped 96³→32³, 80 EM iterations on GPU (native sm_120). **Result: balanced split 269/227/198 but ARI=0.036** (AMI=0.036, V=0.039, Acc=0.427) — each GT class (A/B/C) smears across all three clusters, no diagonal. **Splits on a contrast/intensity axis, not the conformational one — identical behavior to its T4P run.** Confirms the benchmark pattern: learned-feature methods (DISCA, OPUS-TOMO 0.021) default to a contrast axis on synthetic data too. Pred CSV `outputs/FM_easy/disca/disca_motor_easy_k3.csv`; confusion `outputs/FM_easy/disca/confusion_disca_k3_motor_easy_k3.png`; score in `results/synthetic_scores.csv`. Input pickle + labels local at `~/Research/disca_work/` (`disca_input_motor_easy.pickle`, `model_motor_easy/`). **FM_easy now 6/10 run: RELION 0.475(GT) / Dynamo 0.200 / PyTom 0.134 / PEET 0.116 / DISCA 0.036 / OPUS 0.021. Next FM_easy: EMAN2, TomoFlow, ProTomo, STOPGAP.**

- **DYNAMO FM_switch (motor_switch) COMPLETE (2026-06-15):** dpkpca on 451 GT-aligned particles (160³, 5 Å/px, RELION ellipsoidal mask r_xz=38/r_y=65), band [0.05,0.45,2], 50 eigenvectors, k-means k=2. **Split 229/222 but ARI=−0.001** (AMI=−0.002, V=0.001, Acc=0.481) — CCW/CW each split ~50/50 across both clusters; the rotational switch is not on the leading PCA axes. Joins **PEET (0.007)** in unsupervised failure; only **GT-seeded RELION (0.379)** found any signal. **Pipeline fix:** the 160³ `ccmatrix` parfor kept dying when the implicit 24-worker pool tore down mid-step (libgtk ServiceHost crash-loop); a foreground 06-15 retry also died via SIGHUP. Fix in `dynamo_motor_switch_pca.m`: `MW_SERVICE_HOST_DISABLE=1` + one explicit `parpool('Processes',16)` with `IdleTimeout=Inf` + `cores=16`, launched detached (`nohup`). Clean run end-to-end in ~22 min (prealign→ccmatrix→eigentable→eigenvolumes). Score in `results/synthetic_scores.csv`; predictions `packages/dynamo/dynamo_outputs/motor_switch_pca/predictions_k2.csv`; confusion `packages/dynamo/FM_switch/results/confusion_dynamo_k2_k2_pca_motor_switch.png`. **FM_switch now: RELION 0.379 (GT) / PEET 0.007 / Dynamo −0.001. Next FM_switch: OPUS-TOMO, PyTom.**

- **DISCA MASKED T4P + CROSS-PKG FIGURE FIXED (2026-06-11):** Re-ran DISCA on T4P with the cylindrical
  v2 mask (same mask as PyTom/PEET/OPUS). `build_disca_input.py` gained a `--mask` arg; driver
  `scripts/data_prep/run_disca_cyl_v2.sh`. Result: **k=2 → 398/274** (balanced, vs the old unmasked
  ~94% collapse), **but ARI≈0 vs PEET/PyTom/Dynamo** — DISCA splits on a contrast/intensity axis, not
  the conformational one. Strongly agrees with OPUS-TOMO (**ARI=0.678**): the two learned-feature
  methods cluster together on a non-conformational discriminant. Conclusion unchanged (misses the two
  phases) but mechanism now quantified. Assignments: `results/disca_cyl_v2_k{2,3,4}.csv`; scorer:
  `scripts/eval/score_disca_t4p.py`. **Also fixed `gen_cross_pkg_correlation.py`**: its hardcoded
  Dynamo/PEET paths were stale post-reorg (silently skipped both); now points to in-repo canonical
  files and includes DISCA (5 pkgs, 10 pairwise panels). Canonical T4P pairwise ARIs: PEET–PyTom 0.532,
  Dynamo–PyTom 0.492, Dynamo–PEET 0.362 (converging cluster); OPUS–DISCA 0.678 (contrast cluster);
  cross-cluster ≈0.

- **STOPGAP T4P COMPLETE + REPLICATION HUB CONSOLIDATED (2026-06-09, Eben):** Full pipeline ran end-to-end (SLURM job **12114811**, 2026-06-05, ~58 min/64 cores, clean exit). Two independent classifiers, k=2/3/4: **PCA+k-means** splits **336/336** (k=2), 251/274/147, 194/121/189/168; **MRA** (6 iter, classify-only) splits **70/602** (k=2), 24/391/257, 22/317/23/310. Cross-method ARI≈**0.001/0.003/0.003** (chance) — PCA slices a continuous PC axis into equal halves, MRA collapses to one dominant class. **Does not cleanly recover the two pili phases** (same SNR-limited failure as RELION/DISCA/TomoFlow). Committed results in `packages/STOPGAP/T4P/results/` (figures/CSVs/params/FSC committed; `.mrc`/`.star` gitignored, local-only). **Hub fix:** `run_pipeline.slurm`/`resume_pca.slurm`/`recompile_stopgap.slurm` had stale `SG=…/STA/STOPGAP` (transient dir) + `$SG/scripts` path — repointed to `…/packages/STOPGAP` + `$SG/T4P/scripts` so the pipeline runs from the persistent repo. `research.md` rewritten (new §15 results + provenance; layout/paths/exec-lib facts corrected); README results table + source-edit bullet reconciled. Compiled binaries gitignored → fresh clone must run `recompile_stopgap.slurm` once. **Next (analysis): compare k=2 class averages vs PEET ring_complete/ring_altered + ARI vs PEET soft GT; then FM_hard/T4SS.**

- **EMAN2 T4P CANONICAL k=3 COMPLETE (2026-06-09):** eman2 2.99.72 nogui installed on Josh's account (`~/miniforge3/envs/eman2`, cryoem conda channel). Workspace: `~/Research/eman2_project/`. No-align PCA-split (NCLASS=3, NBASIS=12, MAXRES=60Å, cyl v2 mask). Split: **270/317/85 junk** (class 3, FSC=152Å vs 82Å for signal). Re-run with cyl v2 mask gives identical split — mask does not change result. PCA captures intensity/contrast axis, not conformational axis. Result: **No convergence** (same conclusion as RELION). Simple per-class averages computed and visually inspected — density orientation confirmed correct (WBP inversion consistent across packages). Results committed `db010c7`; run script: `packages/eman2/T4P/scripts/run_pipeline.sh` (NONINTERACTIVE=1, NCLASS=3).

- **PROTOMO T4P COMPLETE (2026-06-09):** Full-672 rerun with MRAAREA=0.0 and alignment bypassed (MRAPKR="0 0 0" = unbounded search, not no-translation — was shifting 437 edge particles +22px). Fix: copy raw.i3i → mra.i3i before SVD. **Result: 334/212/126 junk (all 672), CC=0.943. Class averages visually separate the two T4P conformational phases.** Committed `09f20fc`. Local workspace: `~/Research/protomo/process/`.

- **BENCHMARK REORGANIZATION PUSHED (2026-06-09):** Dataset-centric structure (`T4P/`, `FM_easy/`, `FM_hard/`, `T4SS/` subdirs in all 10 packages), `docs/datasets.md` created, naming convention documented. Merged with Eben's EMAN2 k=2 result (19b3f04). All pushed.

- **MOTOR_SWITCH — RELION + PEET COMPLETE (2026-06-09):** Borrelia flagellar motor CCW↔CW, 5 Å/px, 160³, 208 CCW + 208 CW + 35 junk = 451 particles. GT-avg CC=0.615. **RELION GT-seeded k=2 (v3):** iter1 ARI=**0.379** (AMI=0.279, V=0.281, Acc=0.769). Class 1: 170 CCW/31 CW (77% CCW); Class 2: 38 CCW/177 CW (77% CW). Collapses to ARI≈0 by iter5. GT-aligned particles at `production_5apix/subtomos/all_particles_aligned/`. Script: `scripts/run_relion_motor_switch_v3.sh`. **PEET k=2 (WMD-PCA):** ARI=**0.007** (best pc1_10) — CCW/CW equally split across both clusters; same WMD-PCA limitation as FM_easy. Stack: `~/Research/peet/motor_switch/results/stacked.mrc`; scripts: `packages/peet/FM_switch/scripts/`. Scores in `results/synthetic_scores.csv`. **Next: run Dynamo on motor_switch k=2.**

- **REPO REORGANIZED (2026-06-06):** All package dirs moved to `packages/` (dynamo, peet, relion, PyTom, eman2, opusTomo, STOPGAP, disca, tomoflow, protomo). Dataset QC moved to `data/` (T4P_subtomos, T4P_mask, alignment_review, masked_average). Synthetic pipeline moved to `synthetic/etsimulation/`. Background docs moved to `docs/`. New files: `packages/README.md` (master progress table), per-package READMEs (11 total), `data/README.md`, `synthetic/README.md`, `docs/excluded-packages.md`. Old lowercase `stopgap/` consolidated; `TomoNet/` removed. `.gitignore` updated: `*.pkl`, `*.mat` added; STOPGAP binary patterns updated to `packages/STOPGAP/exec/lib*/`. `/handoff` skill updated with Package README Protocol (step 1a). Committed + pushed `d4e931c`.

- **MOTOR_EASY CLASS C RE-SIMULATED + RELION/PEET RERUN COMPLETE (2026-06-05):** Class C re-simulated with `class_C_noRodHook.mrc` (5 runs, 177 particles). `merged_all_aln/` rebuilt (A=246, B=271, C=177=694). GT avg CCs: A-B=0.539, A-C=0.339, B-C=0.027 (B vs C near-orthogonal). **RELION v4 (GT-seeded firstiter_cc):** iter1 ARI=**0.475** (up from 0.380 old C), collapses to ARI≈0.16 by iter2+. Class C 92% pure at iter1. Script: `scripts/run_relion_motor_easy_v4.sh`; output: `outputs/relion_motor_easy/Class3D/k3_wedge_v4/`. **PEET new C:** best k=2 pc1_5 ARI=**0.116** (up from 0.026 old C). k=3 best ARI=0.050. WMD-PCA limitation persists but improved with more distinct classes. Scores in `results/synthetic_scores.csv`. **Next: Dynamo motor_easy (PCT ready); emClarity synthetic-only track.**

- **T4P RE-RUNS COMPLETE — PYTOM SUCCESS, RELION EXHAUSTED, OPUS-TOMO DONE (2026-06-05):** **PyTom:** v2 cylindrical mask (r=13, h_pos=0, h_neg=25) + `-a` flag: k=2 → 440/232, k=3 → 422/150/100. **RELION:** all 6 configs collapse to 672/0 at iter 1–2 — (1) cylindrical mask; (2) ini_high=30+diam=500+firstiter_cc; (3) random init; (4) PEET-seeded → ARI=−0.03; (5) PEET-seeded + orientation search (no --skip_align) → 672/0. Algorithm-level SNR failure, no parameter fix possible. Canonical: ARI≈0. **OPUS-TOMO:** env (opuset) rebuilt from scratch; cloned opusTOMO → ~/opusSrc/opusTOMO (patched); particle paths fixed to `subtomos_mrc/`. Re-run with threshold mask (31.2% voxels): K=2 → **447/225** (epoch 19, 2.5 min training). Y-axis cylinder (2.7% voxels, matching PyTom) tried: K=2 collapses (668/4), too restrictive for VAE template reconstruction. Results: `results/opus_tomo_k2.csv`; extraction script: `scripts/eval/extract_opus_tomo_classes.py`. **Next: compute OPUS-TOMO ARI vs PEET soft GT; Dynamo motor_easy; EMAN2 k=3/k=4.**

- **README OVERHAUL COMPLETE (2026-06-04):** Complete rewrite of `README.md`: corrected SPA description, updated to 4 planned datasets, added T4P classes as lower periplasmic ring conformational states (cites Stefano's bioRxiv preprint), replaced PEET diff figure with v2, generated `motor_easy_classA_avg.png` from MRC, added `motor_easy_class_maps.png` showing all 3 input density maps, updated synthetic section to show class A/C averages (not B/C), honest UMAP caption, PEET added as second "converging" package in preliminary findings, team section updated (Recent Graduates, Gus Hart added as advisor). `etsimulation/figures/` directory created with 6 PNG figures.

- **SYNTHETIC DATA — SCORING FRAMEWORK COMPLETE (2026-06-04):** Scoring infrastructure built: `scripts/eval/score_synthetic.py` (ARI/AMI/V/Acc + confusion PNG), `scripts/eval/extract_relion_classes.py`, `scripts/eval/extract_peet_classes.py`, `peet/kmeans_motor_easy.py`. All scores appended to `results/synthetic_scores.csv`. **Missing-wedge decision:** feed GT-aligned particles (`merged_all_aln/`) with identity starting poses + tilt range ±60°; let each package apply its own native wedge correction. Template-matching baseline ARI=0.289 (structural signal confirmed present).

- **RELION motor_easy — INVESTIGATION COMPLETE + C_noRodHook RERUN (2026-06-05):** Root cause of ARI≈0: symmetric EM initialization. `--skip_align` CORRECT. Canonical blind result: ARI=0.006. GT-seeded upper bound (old C, 634 particles): ARI=0.254 iter1. **New C_noRodHook result (v4, 694 particles):** iter1 ARI=0.475 (C class 92% pure), collapses to ~0.16 by iter2+. Old C v3 was ARI=0.380. Improvement confirms new class design. Mask: `outputs/relion_motor_easy/solvent_mask.mrc` (r=32 px, Y-10); refs: `outputs/relion_motor_easy/class_refs.star`. **PEET motor_easy C_noRodHook:** rebuilt stack → averageAll → pca694_cnew. Best k=2 pc1_5 ARI=0.116; k=3 best ARI=0.050. WMD-PCA limitation persists. Scripts: `peet/motor_easy.prm`, `peet/motor_easy_stack.py`, `peet/kmeans_motor_easy.py`.

- **SYNTHETIC DATA — CLASS B EXPANDED + MASK SIZED (2026-06-04):** Added run_07 (36 subtomos) and run_08 (24 subtomos) to class B. New total: **A=246, B=271, C=177 = 694 particles**. `avg_gt_classB.py` updated and rerun → `avg_classB_aligned.mrc` (271 particles). Two ETSim pipeline bugs fixed: (1) `run_classB.sh` now `mkdir -p output/` before ETSim launch (ETSim uses `os.mkdir` not `os.makedirs` for root dir); (2) `sim_metadata.json` truncation on kill-timing — fixed via `reconstruct_metadata.py`. **Mask sizing done:** `visualize_avg_with_mask.py` generates central XY slice of global avg with mask overlay; final mask = r=32 px (427 Å), center offset Y=−10 (center at 48,38 in 96³ box). **Next: rebuild `merged_all_aln/` + RELION/PEET inputs for new 694-particle dataset, then rerun packages.**

- **PACKAGES/README.md FIGURES GALLERY — COMPLETE (2026-06-08):** Added visual classification results directly to the progress tables. T4P: PEET v2 reference averages header + cross-package pairwise co-tabulation heatmaps (Dynamo/PEET/PyTom/OPUS-TOMO; 6 pairs, row-normalized recall + ARI). Key finding: Dynamo+PyTom+PEET agree well (ARI 0.36–0.53); OPUS-TOMO's split is entirely uncorrelated with all three (ARI ≈ 0). Per-package "Class Avgs" column added; OPUS-TOMO T4P and EMAN2 T4P still pending MRC access. motor_easy: perfect confusion matrix reference + per-package "Best Confusion" column (RELION iter1, PEET k=2 pc1_5, Dynamo nc17, OPUS-TOMO threshold). Class-avg panel cells are `_(pending)_` — run `scripts/eval/gen_class_avg_panels.py` with local MRC paths to fill them. New scripts: `scripts/eval/gen_class_avg_panels.py`, `gen_cross_pkg_correlation.py`, `gen_perfect_confusion.py`. Committed + pushed `4e1b90c`.

- **OPUS-TOMO motor_easy — COMPLETE (2026-06-08):** k=3 on 694 GT-aligned particles (96³, threshold mask 28.3% voxels). ARI=**0.021** (near-random). Split: 479/130/85. Confusion: class C (177 particles) 100% in dominant cluster; A and B broadly mixed across all clusters. VAE continuous latent space does not resolve the 3-class discrete structure. Scores: AMI=0.124, V=0.127, Acc=0.437. Scripts: `packages/opusTomo/scripts/setup_motor_easy_opus.py`, `run_motor_easy_opus.sh`. Output: `outputs/opus_tomo_motor_easy_k3.csv`.

- **PYTOM motor_easy — COMPLETE (prior session):** v2 cylindrical mask (r=13, h_pos=0, h_neg=25), same mask as T4P runs. k=2 ARI=**0.090**; k=3 ARI=**0.134** (best). Canonical result: k=3 ARI=0.134. Scripts: `packages/PyTom/setup_motor_easy_pytom.py`, `run_motor_easy_pytom.sh`. Outputs: `outputs/relion_motor_easy/pytom_motor_easy_k{2,3}.csv`; confusion PNGs in same dir. STATUS not updated at time of run.

- **DYNAMO motor_easy — COMPLETE (2026-06-06):** Two approaches run on 694 GT-aligned particles (96³, RELION solvent mask r=32 Y-10). **HAC** (CC Ward, cophenetic=0.094): k=2 ARI=0.005, k=3 ARI=−0.009 — raw pairwise CC has no structure at this SNR. **dpkpca** (bandpass [0.05,0.45,2], 50 eigenvectors, k-means sweep over nc=1..50): best k=2 ARI=**0.143** (nc=32), best k=3 ARI=**0.200** (nc=17). Class B (no C-ring) 96-99% pure in one cluster; A/C mix. dpkpca canonical result: k=3 ARI=0.200. Scores in `results/synthetic_scores.csv`. Scripts: `packages/dynamo/dynamo_scripts/dynamo_motor_easy_hac.m`, `dynamo_motor_easy_pca.m`, `setup_motor_easy_pca.py`.

- **SYNTHETIC DATA — motor_easy ALL CLASSES DONE (2026-06-04):** Class A: 246 subtomos, Class B: 271 subtomos (8 runs), Class C: 177 subtomos. All GT-aligned averages computed + verified. **GT separability validated:** CC-template matching on GT-aligned subtomos gives ARI=0.289 (~68-73% per-class accuracy on noisy particles); class average CCs: A-B=0.72, A-C=0.66, B-C=0.83 — confirming classes are structurally distinct. **NOTE: `merged_all_aln/` still reflects old 634-particle count — must rebuild before next package runs.** Pipeline quirks: `STA/etsimulation/pipeline_quirks.md`.

- **PEET T4P CLASSIFICATION — TWO RUNS COMPLETE (2026-06-04):** Switched from generic sphere masks to T4P cylindrical mask (`T4P_mask/cylindrical_mask.npy`). Junk class = bottom 68 by CCC (exact match to Stefano's 68). **Mask v1** (r=11.2, h_pos=9.8, h_neg=15.8): [388 ring_complete / 216 ring_altered / 68 junk], AIC=518, BIC=363. **Mask v2** (r=13, h_pos=0, h_neg=25 — below-center only): [374 ring_complete / 230 ring_altered / 68 junk], AIC=659, BIC=504 (best). Both saved in `saved_runs/cylindrical_v{1,2}_*/`, pushed to `peet/results/`. Class labels: `ring_complete` / `ring_altered` / `junk`. Comparison figure vs Stefano's reference (509/95/68) panels: `peet/results/comparison_stefano_v1_v2.png`. Key finding: with cylindrical mask, PC1 is structural signal (include it); sphere masks the opposite. **Next: email Stefano for exact MOTL files; use v2 assignments as soft GT for remaining packages.**

- **BENCHMARK FRAMEWORK (2026-06-02, Claude research complete):** Wrote comprehensive `benchmarkIdeas.md`
  covering: (i) four-lens evaluation framework (external validity vs GT, downstream STA resolution,
  stability/robustness, cross-method consensus), (ii) vetted metric catalog with 25+ citations
  (ARI/AMI/V-measure, gold-standard FSC + AUC-FSC from CryoBench, Hennig clusterboot, Monti consensus,
  internal validity indices), (iii) explicit answers to Eben's three concerns (F-beta misses
  downstream goal, doesn't reveal regime-specific wins, not extensible to GT-free data), (iv) real-data
  track (T4P with Dynamo soft-GT) + synthetic-data track design, (v) output format options
  (recommended: multi-pillar profile + composite), (vi) implementation notes tied to existing scripts
  (relion_class_report.py, etc.), (vii) open questions back to team. README §8 weights (35/25/20/20)
  preserved as constraint; five concerns about the framework raised in §7 (not edited into README).
  → **Next: team review of benchmarkIdeas.md before execution; resolve the 5 open questions (Qs 1–5 in §11).**

- **GROUND TRUTH (Stefano consult, 2026-06-01; updated 2026-06-11):** this T4P dataset has **two distinct, obvious pili-phase classes**. Packages now fall into **three groups** (see `packages/figures/T4P/cross_pkg_correlation.png`):
  - **Recover the conformational split:** **Dynamo** (447/225, reference), **PEET** (374/230/68), **PyTom** (440/232), **ProTomo** (334/212/126, CC=0.943, separates visually). Pairwise ARI among Dynamo/PEET/PyTom = 0.36–0.53.
  - **Split on a non-conformational (contrast) axis:** **OPUS-TOMO** (447/225, threshold mask) and **DISCA** (398/274, cyl v2 mask) — both produce balanced splits that **agree with each other (ARI=0.678)** but are **uncorrelated with the conformational cluster (ARI≈0)**. The two learned-feature methods cluster on intensity/contrast, not conformation.
  - **No split / collapse:** **RELION** (672/0, algorithm-level SNR failure, all 6 configs), **TomoFlow** (unimodal landscape), **EMAN2** (~60/40 PCA split = contrast axis, doesn't map to the two phases).
  - Benchmark signal: alignment/CC-based methods (Dynamo/PEET/PyTom/ProTomo) recover the conformational axis; learned-feature methods (OPUS-TOMO/DISCA) default to a contrast axis; EM/optical-flow methods collapse.

- **Package completion status (2026-06-02, updated 2026-06-09):** 10 of 15 packages run on real T4P (RELION, Dynamo, PyTom,
  Protomo, DISCA, TomoFlow, EMAN2, OPUS-TOMO, PEET partial, **STOPGAP k=2/3/4 complete 2026-06-09**). EMAN2 k=2 rerun complete with no-align pipeline (table now ✅). k=3/k=4 not yet run. MDTOMO/HEMNMA
  require atomic models (❌ skipped). AC3D folded into PyTom. TomoNet formally rejected (out-of-box scope
  violated). emClarity can't run real tilt-series data (synthetic only).

- **Parked (need expert input):** missing-wedge standardization; whether to discretize continuous-
  classifier outputs. (Discrete-vs-continuous is **resolved: discrete, two phases**.) → Stefano / Braxton.

## Package Matrix (15 packages, 3D-input classifiers)

Legend: ✅ done · 🟡 in progress · ⬜ not started · ❌ skip · — n/a/unknown

| Package | Installed | Env | Data-prep | k=2 | k=3 | k=4 | Pushed | Notes / blockers |
|---|---|---|---|---|---|---|---|---|
| RELION 3.1–4.0 | ✅ | `relion-5.0` | ✅ `build_relion_star.py` | ✅ | ✅ | ✅ | — | classic 3D-subtomo path **retained in RELION 5**; k=2/3/4 × wedge/uniform run; **T4P: confirmed algorithm-level failure** — soft EM collapses to 672/0 at iter 1–2 under all 6 variants (masked, tuned, random-init, PEET-seeded, PEET-seeded+orientation-search — all 672/0). ARI≈0. Root cause: per-particle SNR too low for CC discrimination. No parameter fix possible. Scripts: `run_relion_class3d_{masked,tuned,noref,peet_seed,noalign}.sh`. |
| STOPGAP | ✅ | MATLAB R2023b MCR | ✅ `T4P/scripts/build_*.m` | ✅ | ✅ | ✅ | — | **owned by Eben. T4P complete (job 12114811, 2026-06-05).** Two methods: PCA+k-means (k=2 **336/336**) and MRA (k=2 **70/602**); cross-method ARI≈0.001/0.003/0.003 — **does not cleanly recover the two phases** (SNR-limited, like RELION/DISCA/TomoFlow). Results: `packages/STOPGAP/T4P/results/` (figs/CSVs/params/FSC committed; .mrc/.star gitignored). Self-contained hub: `T4P/scripts/run_pipeline.slurm` (`SG` set to repo); compiled binaries gitignored → run `recompile_stopgap.slurm` once on fresh clone. Three PCA-path source bugs fixed (research.md §11). **Next: ARI vs PEET soft GT + class-avg comparison; then FM_hard/T4SS.** |
| OPUS-TOMO | ✅ | `opuset` (rebuilt 2026-06-05) | ✅ (paths fixed) | ✅ | ✅ | ✅ | — | 4 bugs patched (CTF, HEALPix, --split, dummy CTF); env rebuilt from scratch (opusTOMO cloned to ~/opusSrc/opusTOMO, cu128 PyTorch). **T4P threshold mask (31.2%): K=2 → 447/225** (epoch 19, 2.5 min). Y-axis cylinder (2.7%): collapses (668/4). **motor_easy k=3 (2026-06-08): ARI=0.021** — threshold mask (28.3%); C (177) perfectly in dominant cluster but A/B unseparated; VAE continuous latent space not resolving 3-class discrete structure. Results: `outputs/opus_tomo_motor_easy_k3.csv`. ARI vs PEET GT not yet computed. |
| Dynamo | ✅ | MATLAB | ✅ | ✅ | — | — | — | **reference result**: recovers the two distinct pili-phase classes well (Josh + Stefano) → the ground-truth split other packages are measured against; workspace in `dynamo/`, `DYNAMO.md` |
| PEET | ✅ | IMOD | ✅ | ✅ | — | — | ✅ | Two runs complete (2026-06-04). **v1** (cyl r=11.2): 388/216/68. **v2** (cyl r=13, below-center): 374/230/68, AIC=659. Labels: ring_complete/ring_altered/junk. CSVs + figures in `peet/results/`. Cylindrical mask → include PC1 (structural signal). Still need Stefano's MOTL for exact GT. |
| MDTOMO | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| TomoFlow | ✅ | `tomoflow` | ✅ `tomoflow_run.py` | ✅ | ✅ | ✅ | — | also ContinuousFlex, but (unlike MDTOMO/HEMNMA) needs only a **subtomogram-average reference, not an atomic model** — so we DID run it standalone. Required porting farneback3d off CUDA texture-refs for CUDA 13.2/sm_120 (`tomoflow/research.md` §2). Landscape unimodal → **misses the two phases** (k=3 two big classes CC 0.956). `tomoflow/results/` |
| I3 / ProTomo | ✅ | (native) | ✅ | ✅ | ✅ | — | ✅ | **T4P complete 2026-06-09.** Split: 334/212/126 junk (all 672). CC=0.943. **Separates the two phases** (visual). Alignment bypassed (MRAPKR=0 bug fixed). **FM_easy complete 2026-06-15:** k=3 no junk, 517/103/74, **ARI=−0.003** — collapses to dominant cluster, misses 3-class structure (unlike T4P). Series built with `tomoprepare` (not tomoprocess/i3concat). See `protomo/README.md`. |
| EMAN2 | ✅ | `eman2` | ✅ | ✅ | ⬜ | ⬜ | ✅ | **No-align rerun complete (2026-06-08, Eben).** Split: **405 / 273** (cls02/cls01). Consensus FSC: masked=82 Å, masked-tight=71 Å; per-class both 82 Å. **Result: still misses the two phases** — ~60/40 partition does not map to ring_complete/ring_altered; class averages nearly identical by eye at 82 Å. Pipeline: identity `particle_parms` via `make_identity_parms.py` → `e2spt_average` → `e2refine_postprocess` → `e2spt_pcasplit` (mask=`spt_noalign/mask_tight.hdf`, maxres=60 Å). Wedgefill patch (Patch 2) active. Outputs: `packages/eman2/results/`; workspace `~/src/eman2_project/`; docs: `packages/eman2/research.md`. T4P k=3/k=4 not yet run. **FM_easy complete 2026-06-15:** k=3 no junk (no `--clean`), MAXRES=40 Å, auto-tight mask → 81/94/519, **ARI=−0.002** — collapses to dominant cluster (class C 0/0/177), misses 3-class structure. Project `~/Research/eman2_motor_easy/`; outputs `outputs/FM_easy/eman2/`. |
| emClarity | ✅ | MCR R2019a | ⬜ (real data n/a) | — | — | — | — | **installed + GPU-verified on RTX 5080/sm_120** (1.5.3.11 + MCR R2019a; CUDA-10 kernels JIT to Blackwell via the 13.2 driver). **Cannot run on real T4P:** tilt-series pipeline, no path to ingest pre-extracted subtomos → **synthetic-data track only**. See `EMCLARITY.md` |
| PyTom | ✅ | `pytom_env` | ✅ | ✅ | ✅ | ⬜ | — | **T4P FIXED (2026-06-05):** v2 cylindrical mask (r=13, h_pos=0, h_neg=25) + `-a` flag (FRM module absent — see memory). k=2: **440/232** (converged iter 5, class 1≈PEET ring_altered). k=3: **422/150/100** (iter 11). Results: `results/pytom_v2mask_k{2,3}.csv`; figures: `PyTom/figures_v2mask_k{2,3}/`. Previous failure was wrong mask. k=4 not yet run. **motor_easy (prior session):** k=2 ARI=0.090, k=3 ARI=**0.134** (v2mask). Scripts: `packages/PyTom/setup_motor_easy_pytom.py`, `run_motor_easy_pytom.sh`. |
| DISCA | ✅ | `disca` | ✅ `build_disca_input.py` (now `--mask`) | ✅ | ✅ | ✅ | ✅ | template-free unsupervised deep clustering (torch, native sm_120). **Unmasked:** one dominant ~94% class. **Cyl v2 mask (2026-06-11):** balanced **398/274** (k=2), but **ARI≈0 vs PEET/PyTom/Dynamo** — split is on a contrast axis, not conformational. Agrees with OPUS-TOMO (ARI=0.678). **Still misses the two phases.** CSVs: `results/disca_cyl_v2_k{2,3,4}.csv`; scoring: `scripts/eval/score_disca_t4p.py`. **FM_easy (2026-06-15):** k=3, FM_easy solvent mask (r=32 Y-10, 96³): balanced 269/227/198 but **ARI=0.036** — same contrast-axis split, misses A/B/C. `outputs/FM_easy/disca/`. |
| HEMNMA-3D | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Part of Scipion3 ContinuousFlex plug-in; requires initial atomic model/reference map; cannot sort datasets like we're doing right now. |
| AC3D | ❌ | — | ⬜ | ⬜ | ⬜ | ⬜ | — | Implemented as part of PyTom, run with that one. |
| TomoNet | ❌ | — | ❌ | — | — | — | — | **evaluated, rejected** — IsoNet denoising only, no classification workflow built-in. Would require custom autoencoder training (see `TomoNet/research.md`), contrary to benchmark scope (out-of-box packages). Denoising as pre-processing could be explored separately if needed. |

## Datasets

- **Real — T4P:** 672 hand-picked, prealigned 80³ subtomograms (`STA/subtomos_mrc/`, gitignored).
  Alignment QC done (`alignment_review/`, `review_alignment.py`). **Expert ground truth (Stefano):
  two distinct pili-phase classes**, recovered by Dynamo — the reference split for the benchmark.
- **Synthetic — motor_easy (3-class flagellar motor, ~30 Å differences):** **CLASS C RE-SIMULATED + merged_all_aln REBUILT (2026-06-05/06)** — C_noRodHook = C-ring only (CUT2_C=46.5 base px). 5 runs, 177 particles. `merged_all_aln/` rebuilt (A=246, B=271, C=177=694). GT-aligned avg: `production/subtomos/avg_classC_aligned.mrc`. GT avg CCs (new C): A-B=0.539, A-C=0.339, B-C=0.027. Results so far: RELION iter1 ARI=0.475, PEET k=2 ARI=0.116, Dynamo dpkpca k=3 ARI=0.200. Mask: r=32 px, center=(48,38), 96³ box. Scoring infra: `scripts/eval/`. ⚠️ **SUPERSEDED by the 2-class FM_easy redesign (see top bullet); the old 3-class `motor_easy/production/` set was scrapped and DELETED 2026-06-17.** Canonical FM_easy input is now `motor_easy/hc_test_x6/subtomos/merged_AC_full/`.
- **Synthetic — injectisome (T3SS, 2-class hard tier):** EMD-8544. **Finalized 2-class design
  (2026-06-30):** class_B (IM ring + outer ring, n=215) vs. class_C (outer ring only, n=120) +
  80 junk. 415 particles total, 48³, 13.33 Å/px. Template-matching ceiling ARI=0.558 (B–C,
  19 px continuous ring). Mask: cylinder R=20, Y=[2,27] in 48³ box.
  **ALL 10 PACKAGES RUN (2026-06-30)** — ARI scored on B/C signal only (junk counted as noise):
  | Package  | k=2 ARI | k=3 ARI | Notes |
  |----------|---------|---------|-------|
  | DISCA    | 0.720   | 0.812   | Best — CNN detects gross ring presence/absence |
  | PEET     | 0.069   | 0.083   | pc1_10; low but non-zero |
  | STOPGAP  | 0.020   | 0.025   | PCA k-means on eigenfac |
  | PyTom    | 0.005   | 0.009   | FRM -a flag; near-zero |
  | OPUS-TOMO| -0.013  | 0.041   | VAE k=3 slightly better |
  | ProTomo  | -0.032  | —       | SVD+HAC 348/67 split |
  | Dynamo   | 0.000   | 0.000   | dpkpca collapsed |
  | EMAN2    | —       | 0.000   | k=3 PCA split, all noise |
  | TomoFlow | 0.000   | 0.000   | OF features collapsed at 24³ |
  | RELION   | 0.000   | 0.014   | Soft-EM collapses (class bias) |
  **Key finding:** Only DISCA (CNN-based, no registration needed) recovers the gross IM-ring
  signal. All PCA/OF methods collapse — consistent with the registration wall identified on
  FM_easy: GT-pose synthetic particles mis-register WBP reconstructions, collapsing PCA axes.
  Supervised ceiling ARI≈0.558; DISCA k=3 (0.812) approaches ceiling in a CNN shortcut sense.
  Output CSVs: `outputs/T3SS/<pkg>/`; scripts: `packages/<pkg>/T3SS/scripts/`.

- **Synthetic — motor_switch (2-class + junk, flagellar motor CCW↔CW, semi-difficult):** **RE-SIMULATED 2026-06-09 at 5 Å/px.** Borrelia burgdorferi (EMD-21884 CCW, EMD-21886 CW). **208 CCW + 208 CW + 35 junk = 451 particles total.** 160³ box, 5 Å/px. GT-avg CC (ccw vs cw) = **0.615** (clean map CC=0.650). Signal/bkg 2.1–2.5×. ⚠️ **DATA DELETED 2026-06-17 (cleanup error)** — `production_5apix/` (the canonical 5 Å/px set incl. `all_particles_aligned/`) and the superseded 13.33 `production/` are both gone; no backup. **Regenerate from** `maps/5apix/` + `motor_switch/*_5apix.sh` + `extract_subtomos_5apix.py`/`align_all_5apix.py` if re-running. Package results (RELION GT 0.379, PEET 0.007, Dynamo −0.001) committed in `results/synthetic_scores.csv` + `outputs/`/`packages/*/FM_switch/`. Maps: `maps/5apix/`.

## Open Decisions (owner)

1. Synthetic scope — # particle types & classes. (Josh → confirm w/ Stefano)
2. Missing-wedge standardization across packages. (Stefano / Braxton)
3. ~~Discrete vs. continuous handling for T4P~~ **RESOLVED: discrete, two pili phases (Stefano).**
   Remaining: how to discretize continuous classifiers' outputs for comparison. (Stefano)
4. What to do with off-class / outlier particles. (Josh)
6. **Per-particle ground-truth labels for T4P (NEW, 2026-06-03):** Exact per-particle class assignments for real T4P are not yet available. Best available signal is structural consistency of class averages with published conformational states. Quantitative per-particle GT is an open scientific need for the real-data benchmark track. (Josh)
5. **Benchmarking framework choices (NEW, 2026-06-02):** five open Qs in `benchmarkIdeas.md` §11:
   - (1a) README pillar weights 35/25/20/20 OK given downstream-resolution priority, or explore 30/20/20/30?
   - (1b) Is Dynamo's two-phase split sturdy enough for numerical GT, or use qualitatively only?
   - (1c) Synthetic sweep budget for regime map — is Josh's track scoped for 3–5 dimensions?
   - (1d) Half-set FSC strategy: pose-locked feasible across packages, true gold-standard is not. OK with that?
   - (1e) Worth commit to "consensus minus soft-GT" analysis to surface cross-package consensus structures?
   (See `benchmarkIdeas.md` §11 for context.)
7. **FSC gain vs unsplit T4P baseline (NEW, 2026-06-29):** Dynamo has per-class FSC (class1/class2:
   both 26.7 Å at FSC 0.143) but not the unsplit all-particle FSC. Need unsplit baseline to report
   Δres for evidence point E7 in `benchmarkIdeas.md §12`. (Josh)

## People

Josh (primary) · Eben (partner, same repo, package setup + runs) · Stefano (postdoc, science/manuscript) · Braxton (PhD, guidance).
