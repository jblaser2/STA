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

### FM_easy (Synthetic)

- **Particles:** 694 particles, 80³ box, 13.33 Å/px
- **Source:** ETSimulations → IMOD WBP reconstruction → particle extraction at GT orientation
- **Biology:** Flagellar motor assembly intermediates, 3 classes:
  - Class A (`ring_complete`): full motor, C-ring + MS-ring present (246 particles)
  - Class B (`noCring`): motor core + MS-ring, C-ring absent (271 particles)
  - Class C (`Cring_only`, new 2026-06-05): C-ring only, MS-ring/rod/hook absent (177 particles)
- **Ground truth:** Known per-particle labels in `production/labels.csv` (local, not in repo).
  Use ARI / AMI / V-measure for quantitative evaluation.
- **Structural differences:** ~30 Å — large, but realistic for assembly intermediates.
- **Alignment:** Particles extracted at ground-truth orientation (identity pose). No alignment
  step in classification.
- **Missing wedge:** See §Missing Wedge below. No correction needed.
- **Junk class:** None (all 694 particles are valid class members).

### FM_hard (Synthetic, Planned)

- **Biology:** *Borrelia* flagellar motor CCW/CW switching (EMD-21884/21886)
- **Classes:** 2 signal classes + ~30 junk particles
- **Structural differences:** ~15–25 Å (FliG remodeling) — semi-difficult
- **Status:** Not yet simulated. Parameters TBD.

### T4SS (Real, Planned)

- **Biology:** Type IV Secretion System
- **Status:** Dataset TBD.

---

## Classification Protocol

### Common Rules (All Datasets, All Packages)

1. **No alignment step.** All particles are pre-aligned. Every package must be configured to
   skip any alignment/angular search step. Use `dPhi/dTheta/dPsi = [0]`, `searchRadius = [0]`,
   `--no_orient_search`, `--skip_align`, or equivalent per package.
2. **Standardized mask.** Use the dataset-specific mask defined in the table below. Do not use
   a package's default mask. Documented exceptions are listed per package.
3. **Run k = total classes** (including junk where applicable). The junk class is discarded
   before scoring, but must be included in the run.
4. **Canonical run = r01.** Stability replicates are r02, r03, ... See §Naming Convention.

### Per-Dataset Parameters

| Parameter | T4P | FM_easy | FM_hard | T4SS |
|-----------|-----|---------|---------|------|
| **k (reported)** | 2 | 3 | 2 | TBD |
| **k (total in run)** | 3 (2 signal + 1 junk) | 3 (no junk) | 3 (2 signal + 1 junk) | TBD |
| **Mask** | Cylindrical v2 (see below) | TBD | TBD | TBD |
| **Alignment** | None | None | None | None |
| **Missing wedge correction** | No | No | No | No |
| **Junk class** | Yes | No | Yes | TBD |

**Cylindrical mask v2 (T4P canonical):**
- Radius: 13 voxels (~173 Å) in XZ plane
- h_pos: 0 (does not extend above particle center)
- h_neg: 25 voxels (~333 Å, extends below center into periplasm)
- Files: `packages/PyTom/T4P/configs/cylindrical_mask.{em,mrc,npy}` and `packages/peet/T4P/configs/`
- This mask concentrates PCA on the structurally informative periplasmic ring region.
  With this mask, PC1 captures structural signal (include it). Sphere masks cause PC1 to
  capture noise instead (exclude).

---

## Junk Class Protocol

### What counts as junk?

For T4P (and FM_hard): one class is designated junk and excluded from all downstream scoring
(cross-package ARI, FSC, visual inspection). Junk particles are typically lower-quality,
edge-affected, or structurally ambiguous particles.

### Packages with built-in junk filtering

| Package | Built-in mechanism |
|---------|--------------------|
| **PEET** | CCC-based filter: rank all particles by cross-correlation to class average; the lowest-CCC cluster becomes the junk class. Set `numClasses=3`. Junk = the class with lowest mean CCC, consistently the smallest (~68 particles on T4P). |
| **ProTomo** | Centering/edge filter removes outlier particles before classification. Filtered particles (~438 of 672 on T4P) are effectively the junk. Not a classification-step junk class — effectively pre-classification filtering. |

### Packages using k+1 convention

For all other packages (Dynamo, PyTom, RELION, OPUS-TOMO, EMAN2, DISCA, TomoFlow, STOPGAP):

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

**Q: Do FM_easy particles need missing-wedge correction before classification?**

**A: No.** Here is why this is a settled question:

The ETSimulations pipeline simulates a ±54° tilt series (37 tilts, 3° step) with TEM-Simulator,
then reconstructs the tomogram with IMOD WBP. This introduces a real missing wedge — there is
a cone-shaped region of Fourier space with no signal, corresponding to the un-sampled tilt
angles beyond ±54°.

However, all 694 particles are extracted at their **known ground-truth orientations** (identity
pose, meaning they are all rotated to face the same reference direction before extraction). This
means the missing wedge is in the **same Fourier-space direction** for every particle, in every
class.

**Consequence:** The missing wedge is a constant artifact shared by all particles. It does not
discriminate between classes A, B, and C — it degrades all particles equally. Classification
algorithms that look for *differences* between particles are not misled by it.

**What this rules out:**
- WMD (Weighted Missing-Wedge) weighting in PEET — WMD is designed to handle particles
  with *different* wedge orientations. With a uniform wedge, WMD has nothing to exploit and
  can actually hurt (confirmed: PEET ARI=0.026 with WMD on FM_easy vs. ARI=0.116 without).
  Always set `flgWedgeWeight=0` for FM_easy.
- Per-particle wedge correction — pointless since all wedges are identical.

**What this does NOT rule out:** general noise/SNR considerations — the missing wedge does
reduce the effective resolution of individual particles, making classification harder. This is
intentional; it tests packages under realistic cryo-ET conditions.

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
