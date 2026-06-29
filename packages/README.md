# Packages — Benchmark Progress

This directory contains all 10 actively-tested classification packages. Each package has its
own subdirectory organized into per-dataset workstreams (`T4P/`, `FM_easy/`, `FM_hard/`, `T4SS/`).

See [docs/datasets.md](../docs/datasets.md) for the authoritative protocol: k values, masks,
junk class handling, naming convention, and missing-wedge policy.

See [docs/excluded-packages.md](../docs/excluded-packages.md) for packages evaluated but not
included in the benchmark.

---

## Progress Matrix

Legend: ✅ done · 🟡 in progress · ⬜ not started · ❌ skip · — not applicable

### T4P Real Dataset (672 pre-aligned 80³ subtomograms, 13.33 Å/px)

**Protocol:** k=3 total (2 signal + 1 junk), cylindrical mask v2 (r=13, h_pos=0, h_neg=25),
no alignment step. OPUS-TOMO uses threshold mask (package-level exception — VAE cannot use
tight cylindrical). See `docs/datasets.md` for junk class handling per package.

**Classification mask (cylindrical v2, red contour on the global average):**

<img src="figures/T4P/mask_overlay.png" width="720">

**Reference class averages (Stefano — ring_complete / ring_altered / junk, 509/95/68):**

<img src="figures/T4P/reference_class_avgs.png" width="420">

**Cross-package consensus** — 4 packages converge (Dynamo/PEET/PyTom/ProTomo), 5 do not. Pairwise ARI 0.40–0.65; 357/672 (53%) in full 4-way consensus. See `docs/benchmarkIdeas.md §12` for the no-GT evidence chain.

<img src="figures/T4P/cross_pkg_correlation.png" width="860">

| Package | T4P Status | Result (signal classes) | Mask | Converged? | Class Avgs | Notes |
|---------|-----------|------------------------|------|------------|------------|-------|
| [Dynamo](dynamo/) | 🟡 | 447/225 (junk pending) | cyl v2 (pending re-run) | **Yes** | <img src="dynamo/T4P/results/dynamo_final_results/class_comparison.png" width="340"> | HAC; reference result; re-run needed with k=3+junk |
| [PEET](peet/) | ✅ | **374/230** (+68 junk) | cyl v2 | **Yes** | <img src="figures/T4P/peet_v2_class_avgs.png" width="340"> | Cyl mask v2 critical; junk class = bottom 68 by CCC |
| [PyTom](PyTom/) | 🟡 | 440/232 (junk pending) | cyl v2 | **Yes** | <img src="figures/T4P/pytom_k2_class_avgs.png" width="340"> | `-a` flag + v2 mask both required; re-run needed with k=3+junk |
| [OPUS-TOMO](opusTomo/) | 🟡 | 447/225 (junk pending) | threshold (31.2%) | **Partial** | _(pending)_ | Threshold mask required for VAE; junk pending; ARI vs GT pending |
| [RELION](relion/) | ✅ (exhausted) | 672/0 | cyl v2 | **No** | — | Algorithm-level SNR failure; all configs collapse |
| [EMAN2](eman2/) | ✅ | 270/317 (+85 junk) | none | **No** | <img src="eman2/T4P/results/eman2_T4P_k3_none_r01_classavg.png" width="340"> | Canonical k=3 complete; does not separate two phases; PCA axis = contrast, not conformation |
| [DISCA](disca/) | ✅ | **398/274** (cyl v2) | cyl v2 | **No** | <img src="disca/T4P/results/disca_k2_classes.png" width="340"> | Masked: balanced split but ARI≈0 vs converging pkgs; splits on contrast axis. Agrees w/ OPUS-TOMO (ARI=0.678). Misses the two phases |
| [TomoFlow](tomoflow/) | 🟡 | — (old run) | none | **No** | <img src="tomoflow/T4P/results/tomoflow_k2_classes.png" width="340"> | Unimodal; k=3 canonical run needed |
| [ProTomo](protomo/) | ✅ | 334/212/126 junk (all 672) | none | **Yes** | <img src="protomo/T4P/results/class_averages_slices.png" width="340"> | Separates the two phases (visual). CC=0.943. MRAPKR=0 bug fixed (shifting 437 particles +22px); alignment bypassed. |
| [STOPGAP](STOPGAP/) | ✅ | PCA 336/336 · MRA **70/602** (k=2) | cyl (tight r=8/h=26) | **No** | <img src="STOPGAP/T4P/results/meta/class_pca_class_avg_k2.png" width="340"> | Owned by Eben; k=2/3/4 done (job 12114811). PCA k-means vs MRA disagree at chance (ARI≈0.001–0.003); does not separate the two phases |

---

### Synthetic Dataset — FM_easy (REDESIGNED 2026-06-16: 542 particles, 2 classes, high-contrast)

> **Redesigned 2026-06-16.** Old 3-class 694p production-contrast set (every package ARI≈0) archived
> in `outputs/FM_easy/_archive_3class_k3/`. New = **2-class A (mature full motor) vs C (early
> cytoplasmic base), 271+271=542 particles, ×6 contrast (SNR 0.340), 96³, 13.329 Å/px**, GT-aligned.
> **Protocol:** k=2, no junk. Mask: A-vs-C diff sphere `diff_sphere_r23_y55.mrc`.
> Reference ceilings on this set: blind masked-PCA ARI≈0.14; supervised 5-fold ARI≈0.75 / 93% acc.
> **All package numbers below are BLIND (unsupervised, no class info)** — equal footing.

**Ground truth — source density maps (input) and subtomogram averages of each class:**

<img src="figures/FM_easy/header_maps_and_avgs.png" width="900">

*(Central slice, dark = density. Class A = mature full motor, density extends down the box;
Class C = early cytoplasmic base, truncated. The two subtomo averages are what each blind package
is trying to recover.)*

**Classification mask (A-vs-C diff sphere, red contour on the global average):**

<img src="figures/FM_easy/mask_overlay.png" width="720">

The **Class averages** column shows each package's two predicted clusters (mean of the subtomos it
assigned to each), same central slice — a package "finds the class axis" when its two averages look
like the A and C panels above (one full motor, one truncated).

**Perfect classification reference (ARI = 1.0) — what a confusion-column entry looks like at the top of the table:**

<img src="figures/FM_easy/perfect_confusion.png" width="300">

| Package | k=2 ARI (blind) | Acc | Class averages (2 predicted clusters) | Confusion | Notes |
|---------|-----------------|-----|---------------------------------------|-----------|-------|
| [PEET](peet/) | **0.450** (pc1_10) | 0.836 | <img src="figures/FM_easy/peet_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/peet/confusion_peet_k2_k2_pc1_10_AC_hc_x6_542.png" width="300"> | diff sphere. WMD-PCA recovers axis with more PCs (pc1_3=0.08, pc1_5=0.12, pc1_10=0.45); cluster averages match A/C |
| [DISCA](disca/) | **0.407** | 0.819 | <img src="figures/FM_easy/disca_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/disca/confusion_disca_k2_k2_AC_hc_x6_542.png" width="300"> | diff sphere. Locks onto structural axis at high contrast (was 0.036 at k=3); A 268/3 pure |
| [PyTom](PyTom/) | **0.262** | 0.757 | <img src="figures/FM_easy/pytom_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/pytom/confusion_pytom_k2_k2_AC_hc_x6_542.png" width="300"> | **CYLINDER mask** (r27 h24, adopted 2026-06-17 — CC/template method prefers a tight focus mask; converged iter6). Was **0.031** on the diff sphere. |
| [Dynamo](dynamo/) | **0.254** | 0.753 | <img src="figures/FM_easy/dynamo_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/dynamo/confusion_dynamo_k2_k2_AC_hc_x6_542.png" width="300"> | diff sphere. dpkpca band[0.05,0.45,2] 50 eig; 95%-pure C cluster |
| [EMAN2](eman2/) | **0.146** | 0.692 | <img src="figures/FM_easy/eman2_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/eman2/confusion_eman2_k2_k2_AC_hc_x6_542.png" width="300"> | diff sphere (re-run 2026-06-17; was 0.025 with auto-tight mask). 438/104; class C 271/0 pure — partial recovery |
| [ProTomo](protomo/) | 0.053 | 0.616 | <img src="figures/FM_easy/protomo_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/protomo/confusion_protomo_k2_k2_AC_hc_x6_542.png" width="300"> | diff sphere (re-run 2026-06-17; was 0.030 with solvent sphere). SVD+HAC; small A-enriched cluster (79: 71A/8C) |
| [TomoFlow](tomoflow/) | 0.036 | 0.596 | <img src="figures/FM_easy/tomoflow_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/tomoflow/confusion_tomoflow_k2_k2_AC_hc_x6_542.png" width="300"> | **no mask** (OF on full volume). Landscape collapses (downsample 3 / 32³); unimodal, as on T4P |
| [RELION](relion/) | 0.008 (blind) | 0.548 | <img src="figures/FM_easy/relion_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/relion/run_k2_blind/confusion_relion_k2_k2_AC_hc_x6_542_BLIND.png" width="300"> | solvent sphere (21%, *required* for solvent flattening). Soft-EM blind: near-collapse 486/56 — SNR failure |
| [OPUS-TOMO](opusTomo/) | 0.008 | 0.550 | <img src="figures/FM_easy/opus_class_avgs.png" width="340"> | <img src="../outputs/FM_easy/opus/confusion_opus-tomo_k2_k2_AC_hc_x6_542.png" width="300"> | threshold mask (15%, *required* for VAE). Latent does not resolve the 2 classes |
| [STOPGAP](STOPGAP/) | _blocked_ | | — | — | Needs `/apps/matlab/r2023b` (BYU RC cluster); SLURM-only on this node — run via Eben on the cluster |

> **Mask policy:** the canonical FM_easy mask is the **A-vs-C diff sphere** (8.7% of box, shown above), used by
> PEET, DISCA, Dynamo, EMAN2, and ProTomo. Per-package exceptions: **PyTom** uses a **cylinder** (r27 h24, 9.9%;
> the CC/template method gains a lot from a tight focus mask — 0.031→**0.262**, while every PCA method got
> *worse* with it); **RELION** needs a broad solvent-flattening mask (21%); **OPUS-TOMO** needs a broad
> threshold mask for the VAE (15%, a tight mask collapses it); **TomoFlow** has no mask step (optical flow on
> the full volume). All masks are the same 96³ box. *(Cylinder-vs-sphere sweep recorded under `*_CYL` tags in
> `results/synthetic_scores.csv`; the cylinder helped only PyTom and hurt PCA methods — DISCA 0.41→0.005,
> Dynamo 0.25→0.00 — because the A-vs-C signal extends axially and the cylinder crops it.)*

**Supervised upper bounds (reference only — NOT blind, excluded from the ranking):**

| Reference | ARI | Acc | Notes |
|-----------|-----|-----|-------|
| RELION **GT-seeded** (iter1) | 0.764 | 0.937 | Initialized from the true A & C class averages (`--firstiter_cc`) — effectively supervised; collapses to 0.435 by iter2 |
| Logreg 5-fold ceiling | 0.745 | 0.932 | Supervised classifier on masked-PCA features (`align_classify_full.py`) |

**Benchmark signal:** at high contrast the BLIND field splits between methods that recover the *class axis*
(PEET, DISCA, PyTom, Dynamo: ARI 0.25–0.45; EMAN2 0.15 partial) and those that collapse onto a
*nuisance/contrast axis* (ProTomo, TomoFlow, RELION soft-EM, OPUS: ARI≈0–0.05) — even though the supervised
ceiling is 0.75. The old 3-class set put *every* package at ≈0; this 2-class hc set resolves the blind field.
(Masks: diff sphere for all except PyTom=cylinder, RELION/OPUS=broad, TomoFlow=none — see Mask policy above.)

#### Do packages misclassify the *same* subtomos?

Mostly **no** — and that is itself a result. Per-particle errors (best-permutation map of each package's
clusters to GT) were compared across all 9 blind packages (`scripts/eval/fm_easy_error_overlap.py`):

- **No particle is missed by all 9** packages (max 7/9, only 4 particles); errors are spread across the
  set (modal miss-count 3–4 of 9), not concentrated on a small universally-hard subset.
- **The three recovering packages miss nearly disjoint sets.** PEET–DISCA error overlap = **Jaccard 0.00**,
  PEET–Dynamo 0.02 — *below* the chance level expected if their errors were independent (0.09–0.11). **0
  particles are missed by all three** of PEET/DISCA/Dynamo. So a consensus of these three would correct
  almost everything — the methods are complementary, keying on different parts of the signal.
- The **collapsed** packages overlap much more with each other (TomoFlow/ProTomo/EMAN2 Jaccard ≈ 0.48–0.54)
  because they all fail on the same class (whichever collapses), not because they share *hard particles*.

<img src="figures/FM_easy/error_overlap_jaccard.png" width="560">

**Top-5 most-missed subtomos** (highest miss-count across the 9 packages; each panel = average of the 10
central Z-slices of that subtomogram). These are dominated by heavy missing-wedge streaking / low local
SNR — i.e. the hardest particles are degraded reconstructions, not a particular conformation (mix of GT A & C):

<p>
<img src="figures/FM_easy/missed_top1.png" width="175">
<img src="figures/FM_easy/missed_top2.png" width="175">
<img src="figures/FM_easy/missed_top3.png" width="175">
<img src="figures/FM_easy/missed_top4.png" width="175">
<img src="figures/FM_easy/missed_top5.png" width="175">
</p>

---

### Synthetic Dataset — FM_switch (451 particles, 2 classes + junk, ~15–25 Å differences)

> Borrelia burgdorferi flagellar motor CCW↔CW rotational switching (EMD-21884/21886, Chang et al. 2020).
> Re-simulated at 5 Å/px, 160³. 208 CCW + 208 CW + 35 junk = 451 particles. GT-avg CC=0.615.
> **Protocol:** k=2 (CCW vs CW, exclude junk from ARI). Mask: RELION ellipsoidal (r_xz=38, r_y=65 + soft edge).

| Package | FM_switch Status | k=2 ARI | Best Confusion | Notes |
|---------|-----------------|---------|----------------|-------|
| [RELION](relion/) | ✅ | **0.379** (iter 1 GT) | <img src="relion/FM_switch/results/confusion_relion_k2_k2_v3_GT_seeded_iter1.png" width="200"> | GT-seeded+firstiter_cc+skip_align; collapses to ARI≈0 by iter5 |
| [PEET](peet/) | ✅ | **0.007** (k=2 pc1_10) | <img src="peet/FM_switch/results/confusion_peet_k2_motor_switch_k2_pc1_10.png" width="200"> | WMD-PCA ARI≈0; CCW/CW equally split; same limitation as FM_easy |
| [Dynamo](dynamo/) | ✅ | **−0.001** (k=2 dpkpca) | <img src="dynamo/FM_switch/results/confusion_dynamo_k2_k2_pca_motor_switch.png" width="200"> | dpkpca 50 eigs, k-means k=2 → 229/222; CCW/CW split ~50/50 across both clusters; same unsupervised failure as PEET |
| [OPUS-TOMO](opusTomo/) | ⬜ | — | ⬜ | Not yet run |
| [PyTom](PyTom/) | ⬜ | — | ⬜ | Not yet run |
| All others | ⬜ | — | ⬜ | EMAN2, DISCA, TomoFlow, ProTomo, STOPGAP not yet run |

---

### Synthetic Dataset — FM_hard (BUILT 2026-06-17: 813 particles, 3 classes, assembly intermediates)

> **3-class flagellar-motor assembly-intermediate series** (inside-out): **base** (C-ring + MS-ring) →
> **basal_body** (+ proximal rod + P-ring, no hook) → **mature** (full motor + hook/bulb = FM_easy's A).
> Built from EMD-5311 at ×6 contrast through the same ETSim→WBP→extract pipeline as FM_easy; `base` ≡
> FM_easy's C and `mature` ≡ FM_easy's A, so it nests in the same frame. "Slightly harder than FM_easy"
> by design: inserting the real middle stage creates two harder *adjacent* pairs while base↔mature stays
> as the recoverable anchor. 271 × 3 = 813 particles, 96³, 13.329 Å/px, SNR 0.299, GT-aligned, **no junk**.
> Reference ceilings: blind masked-PCA k=3 ARI ≈ **0.07**; supervised 5-fold 3-way ARI **0.472 / 78% acc**.
> **All package numbers below will be BLIND (unsupervised, no class info)** — equal footing.

**Ground truth — source class maps (top) and subtomogram averages of each stage (bottom):**

<img src="figures/FM_hard/header_maps_and_avgs.png" width="900">

*(Central slice, dark = density. Top = the 3 clean source maps; bottom = the GT subtomo averages each
blind package is trying to recover. Inside-out progression: base = one band (C/MS-ring), basal_body
adds the P-ring tier, mature adds the L-ring/bulb cap.)*

| Package | FM_hard k=3 ARI | Acc | Class Avgs | Best Confusion | Notes |
|---|---|---|---|---|---|
| [PEET](peet/) | ⬜ pending | — | _(pending)_ | _(pending)_ | FM_easy leader; run WMD-PCA pc1_10 first as the sanity check |
| [DISCA](disca/) | ⬜ pending | — | _(pending)_ | _(pending)_ | FM_easy leader |
| [Dynamo](dynamo/) | ⬜ pending | — | _(pending)_ | _(pending)_ | dpkpca |
| [EMAN2](eman2/) | ⬜ pending | — | _(pending)_ | _(pending)_ | |
| [ProTomo](protomo/) | ⬜ pending | — | _(pending)_ | _(pending)_ | |
| [TomoFlow](tomoflow/) | ⬜ pending | — | _(pending)_ | _(pending)_ | |
| [PyTom](PyTom/) | ⬜ pending | — | _(pending)_ | _(pending)_ | |
| [RELION](relion/) | ⬜ pending | — | _(pending)_ | _(pending)_ | run blind (not GT-seeded) |
| [OPUS-TOMO](opusTomo/) | ⬜ pending | — | _(pending)_ | _(pending)_ | |
| [STOPGAP](STOPGAP/) | ⬜ blocked (cluster) | — | — | — | needs BYU RC cluster (Eben) |

> **Run protocol:** k=3, no junk, mask = 3-class diff mask `diff_mask_hard.mrc`, no alignment step.
> Canonical input `~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/` (+ `labels.csv`).
> Reuse each package's FM_easy config pattern with k=3. Score into `results/synthetic_scores.csv`
> (run tag `*_ABC_hard_x6_813`); confusions → `outputs/FM_hard/<pkg>/`; class-avg panels →
> `packages/figures/FM_hard/` via `scripts/eval/gen_class_avg_panels.py`.

**Supervised upper bounds (reference only — NOT blind, excluded from any ranking):**

| Method | 3-way ARI | Acc | Note |
|---|---|---|---|
| Logreg 5-fold ceiling (25 PC) | 0.472 | 0.782 | supervised classifier on masked-PCA feats (`classify_hard.py`) |
| — pairwise: base↔mature | 0.752 | 0.934 | = FM_easy A–C (0.745); pipeline cross-check ✓ |
| — pairwise: base↔basal_body | 0.611 | 0.891 | the +P-ring step |
| — pairwise: basal_body↔mature | 0.347 | 0.795 | the +bulb step — the bottleneck (wedge-sensitive) |

### T4SS (Planned)

No runs yet. See `docs/datasets.md` for planned parameters.

---

## Package Descriptions

| Package | Algorithm | Environment | Key Characteristic |
|---------|-----------|-------------|-------------------|
| **Dynamo** | HAC on PCA-reduced subtomogram distances | MATLAB | Reference result for T4P; recovers both conformational states |
| **PEET** | PCA + k-means with cylindrical masks; WMD weighting | IMOD | Best result with cyl v2 mask; built-in CCC-based junk class |
| **PyTom** | FRM-based rotational alignment + k-means with cylindrical focus mask | `pytom_env` | Requires `-a` flag and v2 mask; both critical |
| **OPUS-TOMO** | Variational autoencoder (VAE) continuous latent-space clustering | `opuset` (cu128 PyTorch) | 4 bugs patched; threshold mask required (cyl too restrictive for VAE) |
| **RELION** | Soft EM (3D maximum-likelihood classification) | `relion-5.0` | Algorithm-level failure on low-SNR T4P; FM_easy (2-class hc) **blind ARI=0.008** (GT-seeded 0.764 = supervised upper bound, not a blind score) |
| **EMAN2** | PCA split on subtomogram stack | `eman2` (Josh + Eben) | T4P k=3 canonical done; PCA captures contrast axis, not conformation |
| **DISCA** | Template-free deep unsupervised clustering (pytorch) | `disca` | Unmasked: ~94% dominant class. Masked (cyl v2): balanced 398/274 but ARI≈0 vs converging pkgs — clusters on contrast axis, agrees w/ OPUS-TOMO (0.678) |
| **TomoFlow** | ContinuousFlex optical-flow conformational classification | `tomoflow` | Unimodal landscape; CUDA texture-ref porting for sm_120 |
| **ProTomo (I3)** | Iterative alignment + multi-reference classification | native binary | Full-672 rerun complete 2026-06-09; CC=0.921 trivial (same as 234-particle run) |
| **STOPGAP** | Subtomogram averaging + PCA + k-means (MATLAB MCR) | MATLAB R2023b MCR | Owned by Eben; T4P k=2/3/4 complete (2026-06-09); does not separate two phases (ARI≈0); FM/T4SS pending |

---

## Packages Not Tested

See [docs/excluded-packages.md](../docs/excluded-packages.md) for TomoNet, emClarity, MDTOMO, HEMNMA-3D, and AC3D.

---

## How to Update This File

After any result changes:
1. Update the relevant row in the Progress Matrix above
2. Update `packages/<pkg>/README.md` results summary table

See `docs/datasets.md` for naming convention and canonical parameters.
See `CLAUDE.md` §"Package README Protocol" for the full update rule.
