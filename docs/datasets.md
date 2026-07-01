# Benchmark Datasets — Description and Classification Protocol

This document is the authoritative reference for how to run classifications across all packages
on all datasets. When in doubt about k, mask, junk class, or any other parameter, read this
file first. Do not infer protocol from individual package READMEs — those may be out of date.

---

## Datasets

### T4P (Real)

- **Particles:** 672 pre-aligned 80³ subtomograms, 13.33 Å/px
- **Source:** *Vibrio* cryo-tomograms, hand-picked by Stefano
- **Biology:** Type IV Pilus system — two known conformational states of the lower periplasmic
  ring (ring_complete vs. ring_altered), as described in Bharat lab bioRxiv 2025
- **Ground truth:** No per-particle labels. Validation is by visual inspection of class averages
  against the published structure. Packages whose averages are consistent with both known states
  are considered "converged."
- **Alignment:** Particles are pre-aligned. No alignment step in classification.
- **Missing wedge:** Real data; standard tilt-series correction was applied upstream. No
  additional wedge correction is needed at the classification step.

### FM_easy (Synthetic) — REDESIGNED 2026-06-16 (2-class, high-contrast)

- **Particles:** 542 particles (271 A + 271 C), 96³ box, 13.329 Å/px
- **Source:** ETSimulations → IMOD WBP reconstruction → particle extraction at GT orientation,
  at **×6 model contrast** (base ×0.6 vs production ×0.1)
- **Biology:** Flagellar motor assembly intermediates, **2 classes**:
  - Class A (`full motor`): mature/extended assembly, density extends down the box (271 particles)
  - Class C (`base only`): early cytoplasmic base, truncated to the top of the box (271 particles)
- **Canonical input:** `~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/`
  (542 GT-aligned MRCs + `labels.csv`; local, not in repo).
- **Contrast / SNR:** ×6 → measured SNR **0.340** (production was 0.21). ×6 is the sweet spot:
  ×10 *dropped* SNR to 0.30 (strong-phase nonlinearity caps achievable SNR ~0.4).
- **Reference ceilings (on this set):** blind masked-PCA k=2 ARI ≈ 0.14; supervised 5-fold ceiling
  ARI ≈ 0.75 / 93% acc — the class difference is strongly present and recoverable with labels.
- **Ground truth:** Known per-particle labels in `merged_AC_full/labels.csv`. Use ARI / AMI / V-measure.
- **Alignment:** Particles extracted at ground-truth orientation (identity pose). No alignment
  step in classification.
- **Missing wedge:** ±60°/3°/41 tilts. See §Missing Wedge below. No correction needed.
- **Junk class:** None (all 542 particles are valid class members).
- **Mask:** A-vs-C difference sphere `diff_sphere_r23_y55.mrc`
  (in `packages/dynamo/dynamo_outputs/easy_pair_AC_hc/`; 8.7% of the 96³ box).
  **Per-package exceptions:** used by PEET, DISCA, Dynamo, EMAN2, ProTomo. **PyTom** uses a **cylinder**
  (`diff_cyl_r27_h24_y52.mrc`, r=27 in X-Z, height 24 along the Y motor axis, 9.9%) — the CC/template
  `auto_focus` method gains a lot from a tight focus mask (0.031→0.262), whereas every PCA method got
  *worse* with the cylinder (it crops the axial A-vs-C signal; see STATUS cylinder-vs-sphere sweep).
  RELION uses a broad solvent-flattening mask (`solvent_mask.mrc`, 21%) — `--solvent_mask` must enclose
  the whole particle, so the tight diff sphere can't be used there. OPUS-TOMO uses a broad threshold mask
  (15%) — a tight mask collapses the VAE. TomoFlow applies no mask (optical flow runs on the full volume).
  All masks are the 96³ box.
- **Why the redesign:** the original 3-class 694-particle set at production contrast (SNR 0.21) was a
  documented *blind-failure-with-ground-truth* (every package ARI ≈ 0; analysis in
  `docs/fm_easy_classification_analysis.md`). The wall is representational, not signal absence —
  raising contrast lifts the supervised ceiling to ~0.80. This 2-class ×6 set is the achievable
  "easy tier." Old 3-class results archived in `outputs/FM_easy/_archive_3class_k3/` and
  `results/_archive_motor_easy_3class_scores.csv`.

### T3SS Injectisome (Synthetic) — BUILT 2026-06-30 (2-class + junk, structurally distinct complex)

<img src="../packages/figures/T3SS/header_maps_and_avgs.png" width="780">

*Left = source maps (class_B = full injectisome base, class_C = IM ring absent); right = GT subtomo
averages (central slice, dark = density). The structural difference is at the cytoplasmic base.*

- **Particles:** 415 total — 215 class_B + 120 class_C + 80 junk, **48³ box, 13.33 Å/px**
- **Source:** ETSimulations → IMOD WBP → particle extraction at GT orientation, **AMP=1.5**
  (higher than FM_easy because EMD-8544 needs AMP=1.5 to reach usable SNR; see memory
  `etsim-t3ss-amp-calibration.md`). Based on EMD-8544 (Hu et al. 2017 Cell).
- **Biology:** T3SS injectisome sorting-platform presence/absence:
  - **class_B** (215p): IM ring + cytoplasmic sorting platform + ATPase present (full assembled base)
  - **class_C** (120p): IM ring absent (partially assembled; sorting platform missing)
  - **junk** (80p): background noise boxes (no structure)
  The class difference is a full ring-tier presence/absence — larger structural signal than FM_easy's
  axial truncation, but a completely different fold (six-fold cytoplasmic cage vs flagellar motor).
- **Why this dataset:** provides structural/geometric diversity beyond flagellar motors. All three
  prior synthetic datasets (FM_easy, FM_hard, FM_switch) used EMD-5311 variants; T3SS is an
  independent complex with different symmetry and spatial arrangement.
- **Contrast / SNR:** AMP=1.5 → estimated SNR ~0.25 (class_C harder — fewer structural features).
- **Reference ceilings (signal only, class_B vs class_C):** supervised logistic regression
  ARI ≈ **0.95**; blind DISCA (best package) k=3 ARI = **0.812** — large enough signal that the
  CNN recovers it. All PCA methods collapse (registration wall, same as FM_easy).
- **Canonical input:** `~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/`
  (415 GT-aligned MRCs + `labels.csv`; local, not in repo).
- **Ground truth:** per-particle labels in `merged_BC_t3ss/labels.csv` (class_B / class_C / junk).
  ARI is scored on signal particles only (class_B + class_C, **excluding junk**).
- **Alignment:** Particles extracted at ground-truth orientation. No alignment step.
- **Missing wedge:** ±60°/3°/41 tilts. No correction needed.
- **Junk class:** Yes — 80 background-noise boxes. Protocol: k=3 where the package can isolate
  a third class; ARI always scored on B vs C signal only.
- **Mask:** Cylinder `mask_t3ss.mrc` — R=20, ZC=24, XC=24, Y=[2,27] in 48³ box (~18% of box).
  Local: `~/Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc`.
- **Pipeline (local, not repo):** `~/Research/synthetic_sta/injectisome/` — `make_variants_t3ss.py`
  (3 maps from EMD-8544 axial cuts), `run_full.sh` (3 classes × 8 runs), `classify_t3ss.py`
  (GT-align → merged_BC_t3ss + GT averages + mask + calibration). Sim config in `inputs/sim_clean.txt`.

### T4SS (Real, Planned)

- **Biology:** Type IV Secretion System
- **Status:** Dataset TBD.

---

## Classification Protocol

### Common Rules (All Datasets, All Packages)

1. **No alignment step.** All particles are pre-aligned. Every package must be configured to
   skip any alignment/angular search step. Use `dPhi/dTheta/dPsi = [0]`, `searchRadius = [0]`,
   `--no_orient_search`, `--skip_align`, or equivalent per package.
   > ⚠️ **CAVEAT — under review (2026-06-19).** This rule is *not* apples-to-apples between real and
   > synthetic. Real T4P was pre-aligned by an actual STA **refinement** pipeline (registration optimized
   > on the real densities); the synthetic sets are extracted at **ground-truth poses** — correct for the
   > clean map but NOT optimal for co-registering the noisy, wedge-distorted WBP reconstructions. Measured
   > impact: refining the synthetic registration lifts blind masked-PCA ARI on FM_easy from **0.14 → 0.32**.
   > So "GT poses / no alignment" *handicaps* the synthetic data. Likely protocol revision: classify the
   > synthetic sets from **genuinely aligned** particles (real subtomogram alignment, or each package's own),
   > matching how the real data was prepared. See STATUS [[fm-easy-registration-is-the-gap]].
2. **Standardized mask.** Use the dataset-specific mask defined in the table below. Do not use
   a package's default mask. Documented exceptions are listed per package.
3. **Run k = total classes** (including junk where applicable). The junk class is discarded
   before scoring, but must be included in the run.
4. **Canonical run = r01.** Stability replicates are r02, r03, ... See §Naming Convention.

### Per-Dataset Parameters

| Parameter | T4P | FM_easy | T3SS | T4SS |
|-----------|-----|---------|------|------|
| **k (reported)** | 2 | 2 | 2 (signal B vs C) | TBD |
| **k (total in run)** | 3 (2 signal + 1 junk) | 2 (no junk) | 3 (2 signal + 1 junk) | TBD |
| **Mask** | Cylindrical v2 (see below) | A-vs-C diff sphere `diff_sphere_r23_y55.mrc` | Cylinder `mask_t3ss.mrc` (R=20, Y=[2,27], 48³) | TBD |
| **Alignment** | None | None | None | None |
| **Missing wedge correction** | No | No | No | No |
| **Junk class** | Yes | No | Yes (80 junk) | TBD |

**Cylindrical mask v2 (T4P canonical):**
- Radius: 13 voxels (~173 Å) in XZ plane
- h_pos: 0 (does not extend above particle center)
- h_neg: 25 voxels (~333 Å, extends below center into periplasm)
- Files: `packages/PyTom/T4P/configs/cylindrical_mask.{em,mrc,npy}` and `packages/peet/T4P/configs/`
- This mask concentrates PCA on the structurally informative periplasmic ring region.
  With this mask, PC1 captures structural signal (include it). Sphere masks cause PC1 to
  capture noise instead (exclude).

**Per-package mask exceptions:**

| Package | Mask used | Reason |
|---------|-----------|--------|
| RELION | Cyl v2 | — |
| PEET | Cyl v2 | — |
| Dynamo | Cyl v2 (pending re-run) | k=2 re-run needed anyway |
| PyTom | Cyl v2 | — |
| DISCA | Cyl v2 | — |
| EMAN2 | Auto-tight (from EMAN2 average) | No external mask path in e2spt_pcasplit; auto-mask preserves molecule |
| ProTomo | None (full box for SVD) | ProTomo's SVD doesn't use an explicit mask in the same sense |
| OPUS-TOMO | Threshold 31.2% | Tight mask collapses VAE (documented exception) |
| TomoFlow | None (full volume) | Optical flow acts on the full subvolume |
| STOPGAP | Tight cyl r=8/h=26 | **Undocumented deviation** — Eben used a tighter cylinder than v2; results may differ from other packages |

---

## Standard Result CSV Format

All per-package T4P result CSVs are normalised by `scripts/eval/standardize_t4p_results.py`
to a common format and stored in `results/T4P/<pkg>_k<k>_std.csv`:

| Column | Type | Values |
|--------|------|--------|
| `particle` | str | MRC filename (`aligned_tom*.mrc`) |
| `class_int` | int | 1=signal_a, 2=signal_b, [3=junk] |
| `class_name` | str | Converging pkgs: `ring_complete` / `ring_altered` / `junk`; non-converging: `class_a` / `class_b` / `junk` |

Label assignment: converging packages (Dynamo/PEET/PyTom/ProTomo) have their labels
Hungarian-aligned to PEET as the reference, so `class_int=1` always maps to the larger
ring_complete class across all of them. Non-converging packages sort by class size.

**EMAN2 special case:** raw CSV uses `particle_index` (0-based integer) not filename.
The mapping is `idx → sorted(glob("aligned_tom*.mrc"))[idx]` — verified from `make_project.py`.

**To regenerate:** `conda run -n eman2 python3 scripts/eval/standardize_t4p_results.py`

---

## Junk Class Protocol

### What counts as junk?

For T4P: one class is designated junk and excluded from all downstream scoring
(cross-package ARI, FSC, visual inspection). Junk particles are typically lower-quality,
edge-affected, or structurally ambiguous particles. (FM_easy has **no** junk class — all 542
particles are valid. T3SS has 80 junk background-noise boxes; ARI is always scored signal-only.)

### Per-package junk status (T4P)

| Package | Junk class | Count | How | Status |
|---------|-----------|-------|-----|--------|
| **PEET** | class 3 | 68 | CCC-ranked: lowest-CCC cluster at k=3 | ✅ done |
| **EMAN2** | class 3 | 85 | PCA outlier removal (`--clean` flag) at k=3 | ✅ done |
| **ProTomo** | extracted separately | 126 | `tomoinfo -cls` returns junk as class 2; `extract_protomo_classes.py --include-junk` writes all 672 rows | ✅ done (class 2 → junk) |
| **PyTom** | class 2 (k=3) | 100 | Smallest class in k=3 run assumed junk — **verify by FSC** | 🟡 assumed |
| **Dynamo** | none | — | Currently k=2 only — **needs k=3 re-run** | ❌ pending |
| **DISCA** | none | — | Currently k=2 only — **needs k=3 re-run** | ❌ pending |
| **OPUS-TOMO** | none | — | Currently k=2 only — **needs k=3 re-run** | ❌ pending |
| **STOPGAP** | — | — | No per-particle CSV exists (only PCA eigenfactors) — Eben's | ❌ no CSV |
| **RELION** | n/a | — | Collapses to 672/0 regardless of k | n/a |
| **TomoFlow** | n/a | — | No per-particle class CSV | n/a |

### k+1 convention for packages without built-in junk

- Run with total k = (signal classes + 1)
- After classification: the **smallest class by particle count** is labeled junk
- Junk heuristic: junk class has < 15% of total particles, OR is ≥2× smaller than the
  next-smallest class
- Log the junk class assignment in `_params.json`
- If no class meets the junk heuristic (all classes roughly equal size), note this —
  it means the package could not isolate junk particles

---

## Per-Package Key Parameters (Classification Step)

These are the parameters that differ from each package's defaults. All other settings
should be left at defaults unless a research.md note documents a specific override.

### T4P

| Package | Key classification parameters |
|---------|-------------------------------|
| **PEET** | `numClasses=3`, mask=cylv2, `flgWedgeWeight=0`, `sampleSphere='none'`, `dPhi/dTheta/dPsi=[0]`, `searchRadius=[0]`, `szVol=[78,78,78]`, z-score normalize particles before PCA |
| **Dynamo** | HAC `k=3`, mask=cylv2, `nIter=1` (already aligned) |
| **PyTom** | `-k 3`, `-m cylindrical_mask.em`, `-a` flag (required — enables Python FRM fallback), no alignment iterations |
| **RELION** | `--K 3`, `--no_orient_search` (or `--psi_step 0 --tilt_step 0`), `--mask_diameter` from cylv2 dimensions, `--tau2_fudge 4`, `--iter 25` |
| **OPUS-TOMO** | `K=3`, threshold mask (see note), `--zdim 8`, `--epochs 20`, `--no_trans` |
| **EMAN2** | `--seg 3`, `--wedge-fill`, no `--align` |
| **DISCA** | `--nclass 3`, `--lr 1e-3`, `--epochs 100` |
| **TomoFlow** | `--nclass 3`, consensus average as reference |
| **STOPGAP** | `nclass 3`, PCA+kmeans pipeline |
| **ProTomo** | `k=2` multi-reference (centering filter acts as junk removal pre-classification) |

> **OPUS-TOMO mask exception:** OPUS-TOMO uses a **threshold mask** (computed from consensus
> average, ~28–31% of voxels) for all datasets. The cylindrical v2 mask (2.7% of voxels) is
> too restrictive for the VAE reconstruction loss — causes classification collapse (668/4 split
> observed on T4P). This is a documented package-level constraint, not an error.

### FM_easy

| Package | Key classification parameters |
|---------|-------------------------------|
| **PEET** | `numClasses=3`, mask=TBD, `flgWedgeWeight=0`, no angle/translation search |
| **Dynamo** | dpkpca `nc=17`, `k=3`, sphere mask (r=32 px, Y-10 offset) |
| **PyTom** | `-k 3`, `-a` flag, `-m <motor_mask>` |
| **RELION** | `--K 3`, GT-seeded (`--ini_model`), `--tau2_fudge 4`, `--iter 1` (GT-seeded upper bound) |
| **OPUS-TOMO** | `K=3`, threshold mask |
| **EMAN2** | `--seg 3`, `--wedge-fill` |
| **DISCA** | `--nclass 3` |
| **TomoFlow** | `--nclass 3` |
| **STOPGAP** | `nclass 3` |

---

## Missing Wedge — Synthetic Data

**Q: Do synthetic particles need missing-wedge correction before classification?**

**A: No.** Here is why this is a settled question:

The ETSimulations pipeline simulates a ±54° tilt series (motor_easy/nora_test) or ±60°
(motor_switch) with TEM-Simulator, then reconstructs the tomogram with IMOD WBP
(`-RADIAL "0.35,0.05"`; no CTF correction). This introduces a real missing wedge — a
cone-shaped region of Fourier space with no signal corresponding to the un-sampled tilt angles.

All particles are extracted at their **known ground-truth orientations** (aligned to a common
reference frame before extraction). This means the missing wedge points in the **same
Fourier-space direction** for every particle, in every class.

**Consequence:** The missing wedge is a constant artifact shared by all particles. It does not
discriminate between classes — it degrades all particles equally. Classification algorithms that
look for *differences* between particles are not misled by it. The artifact does reduce
per-particle resolution and makes classification harder, which is intentional — it tests packages
under realistic cryo-ET conditions.

### Per-package wedge handling

Packages fall into four categories:

**Statistical pseudo-subtomogram modeling — RELION (full pipeline)**
RELION's proper STA pipeline builds a pseudo-subtomogram per particle by back-projecting all 2D
tilt images into 3D, weighted by CTF². A paired weight volume records which Fourier-space voxels
were sampled. During classification the EM likelihood is evaluated only over *sampled* voxels —
the missing wedge region is skipped implicitly; no mask needed.
*Caveat for our runs:* we supplied pre-extracted subtomograms with a flat STAR file, bypassing
the tilt-series pipeline. RELION therefore treated particles as SPA data with no wedge modeling.
This is a contributing factor to the ARI≈0 collapse and would be fixed by running the full
`relion_tomo_subtomo` pseudo-subtomogram pipeline.

**Wedge-masked cross-correlation — Dynamo, PEET, PyTom, I3/ProTomo, STOPGAP**
These packages zero out the missing wedge in Fourier space before computing cross-correlation
between a subtomogram and reference: FFT both volumes, multiply the reference by a binary wedge
mask (1 = sampled, 0 = missing cone), then correlate. This prevents empty-wedge voxels from
contributing spurious signal.
*For our uniform-wedge data this is largely irrelevant* — all particles share the same wedge
orientation, so the mask cancels symmetrically and provides no discriminative benefit. Empirically
confirmed with PEET: ARI=0.026 with WMD on vs. ARI=0.116 without. **Always set
`flgWedgeWeight=0` for synthetic datasets; do not enable per-particle wedge weighting.**

**Reference-based wedge filling — EMAN2 (`--wedge-fill`)**
EMAN2's `e2spt_pcasplit.py` can extrapolate density into the missing wedge region using the
current class reference before PCA. Tested on T4P: wedge-fill on vs. off gave an identical
405/273 split. Irrelevant for uniform-wedge data. Safe to include `--wedge-fill` in the command
(it is the documented flag) but it has no measurable effect.

**No explicit handling — OPUS-TOMO, TomoFlow, DISCA**
All three are deep learning approaches (VAE, neural field, CNN). They process subtomograms as
voxel grids and learn features directly from the data distribution. The missing wedge artifact is
part of the input the network sees. No masking or compensation is performed. For uniform-wedge
data this is not a disadvantage relative to the masking-based packages above.

### Summary table

| Package | Wedge handling | Effect on synthetic data |
|---|---|---|
| RELION (full pipeline) | Pseudo-subtomogram; likelihood over sampled voxels only | Correct; bypassed in our runs |
| STOPGAP | Wedge-masked FSC/CC | Irrelevant for uniform wedge |
| Dynamo | Wedge-masked CC + Fourier PCA | Irrelevant for uniform wedge |
| PEET | WMD per-particle weighting | Actively hurts — always `flgWedgeWeight=0` |
| PyTom | Wedge-masked FLCF | Irrelevant for uniform wedge |
| I3/ProTomo | Wedge-masked CC | Irrelevant for uniform wedge |
| EMAN2 | Reference-based wedge fill | Tested, no effect |
| OPUS-TOMO | None (VAE) | Fine for uniform wedge |
| TomoFlow | None (neural field) | Fine for uniform wedge |
| DISCA | None (CNN) | Fine for uniform wedge |

---

## Naming Convention

### Run Directories

Stored in `outputs/<dataset>/<pkg>/` (gitignored):

```
<pkg>_<dataset>_k<n>_<mask>_r<run>
```

| Field | Values | Notes |
|-------|--------|-------|
| `<pkg>` | `dynamo`, `peet`, `pytom`, `relion`, `opus`, `eman2`, `disca`, `tomoflow`, `protomo`, `stopgap` | Lowercase, no underscores |
| `<dataset>` | `T4P`, `FM_easy`, `FM_hard`, `T4SS` | Exact case |
| `k<n>` | `k2`, `k3`, `k4` | Total classes **including junk** |
| `<mask>` | `cylv2`, `threshold`, `sphere`, `none` | `cylv2` = cyl mask v2 (T4P standard) |
| `r<run>` | `r01`, `r02`, `r03` | `r01` = canonical; `r02`+ = stability replicates |

Examples:
- `peet_T4P_k3_cylv2_r01` — PEET canonical T4P run (2 signal + 1 junk, cyl v2)
- `dynamo_T4P_k3_cylv2_r01` — Dynamo T4P (k=3 HAC, cyl mask)
- `relion_FM_easy_k3_sphere_r01` — RELION motor_easy GT-seeded
- `pytom_T4P_k3_cylv2_r02` — PyTom second stability replicate

### Result Files

Stored in `packages/<pkg>/<dataset>/results/` (committed if small):

```
<pkg>_<dataset>_k<n>_<mask>_r<run>_assignments.csv   ← per-particle class labels
<pkg>_<dataset>_k<n>_<mask>_r<run>_classavg_c1.mrc   ← class 1 average
<pkg>_<dataset>_k<n>_<mask>_r<run>_classavg_c2.mrc   ← class 2 average
<pkg>_<dataset>_k<n>_<mask>_r<run>_classavg_junk.mrc ← junk class (where applicable)
<pkg>_<dataset>_k<n>_<mask>_r<run>_confusion.png      ← confusion matrix (FM datasets only)
<pkg>_<dataset>_k<n>_<mask>_r<run>_params.json        ← key run parameters + junk assignment
```

The `_params.json` must record at minimum:
```json
{
  "package": "peet",
  "dataset": "T4P",
  "k_total": 3,
  "k_reported": 2,
  "mask": "cylv2",
  "run": "r01",
  "junk_class": 3,
  "junk_n": 68,
  "notes": "PEET CCC-based junk filter"
}
```
