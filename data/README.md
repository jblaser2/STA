# Data

This directory holds all dataset files, quality-control artifacts, and preprocessing outputs
for the benchmark. Large `.mrc` files are gitignored — only scripts, masks, and small outputs
are committed.

---

## Contents

### `T4P_subtomos/` — 672 T4P subtomograms (gitignored)

Hand-picked, prealigned 80³ subtomograms of the Type IV Pilus (T4P) complex from *Vibrio*
cells at 13.33 Å/px. These are the input to all real-data benchmark runs.

- All files are `.mrc` format; gitignored via `*.mrc` rule.
- Alignment QC was done before benchmarking; see `alignment_review/`.

### `T4P_mask/` — cylindrical classification mask

Cylindrical mask used to focus classification on the T4P periplasmic ring region.

| File | Description |
|------|-------------|
| `cylindrical_mask.npy` | Numpy array — final v2 mask (r=13, h_pos=0, h_neg=25) |
| `cylindrical_mask.em` | EM-format version |
| `cylindrical_mask_v2.mrc` | MRC version (gitignored) |
| `compute_starting_average.py` | Generates global average from subtomograms |
| `generate_cylindrical_mask.py` | Generates the cylindrical mask |
| `starting_average.npy` | Global average template |
| `README.md` | Mask documentation |

### `alignment_review/` — T4P particle alignment QC

Quality-control data from the pre-benchmark alignment review.

| File | Description |
|------|-------------|
| `alignment_review_progress.json` | Per-particle QC metadata (55 KB) |
| `alignment_review_results.txt` | Summary statistics |
| `review_alignment.py` | QC script |
| `README.md` | Documentation |

### `masked_average/` — masked averaging experiments

| File | Description |
|------|-------------|
| `masked_average.py` | Script for computing masked global averages |
| `masked_average.mrc` | Global T4P average with mask applied (gitignored) |
| `masked_average_comparison.png` | Visualization of mask effect |
| `README.md` | Methods documentation |

### `few_sta_test/` — resolution-scaling validation (archived)

Resolution vs. N particle-count validation suite from May 2026. Not part of the active
benchmark; kept for reference.

| File | Description |
|------|-------------|
| `few_sta_test.py` | FSC and resolution comparison script |
| `fsc_comparison.png` | FSC curve visualization |
| `resolution_vs_N.png` | Resolution scaling plot |
| `avg_real_N*.mrc` / `avg_dup_*.mrc` | Averaged maps at N=25–400 (gitignored) |
