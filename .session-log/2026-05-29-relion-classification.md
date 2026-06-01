# 2026-05-29 — RELION 3D-Subtomogram Classification on T4P

**Goal:** Confirm which RELION version classifies already-reconstructed 3D subtomograms, install/
configure RELION, document how to run subtomo classification, and run it on the 672 aligned T4P
particles.

---

## Key finding: RELION 5 retains the classic 3D-subtomo path

The user's premise ("only RELION 3.1–4.0 did STA classification on 3D data") is **essentially
correct**: the documented GUI workflow for classifying reconstructed 3D subvolumes is RELION
3.0/3.1's classic path; RELION 4/5 replaced it with **pseudo-subtomograms** that optimize against
the raw 2D tilt-series images and **require the tilt series + tomograms** — which this dataset
doesn't have.

**But** the classic 3D code was never removed from RELION 5's `relion_refine` binary (just dropped
from the GUI tomo pipeline). Verified on the local `5.0.1-commit-cad71b` build:
- `--help` shows a "Subtomogram averaging" section (`--skip_subtomo_multi`, `--ctf3d_not_squared`…).
- `rlnCtfImage` 3D-CTF field at `src/metadata_label.h:886`; required for 3D+`--ctf`
  (`ml_optimiser.cpp:10343`). 3D mode set by `rlnImageDimensionality 3` (`exp_model.cpp:888`).

So we ran classic 3D Class3D **directly via the command line on RELION 5 — no 3.1 build needed.**
(3.1 build documented as a fallback in `RELION.md` §7.)

## What was built (committed: scripts + docs + small PNGs)

- `scripts/data_prep/build_relion_star.py` — emits two-block (optics+particles) star,
  `particles_wedge.star` / `particles_uniform.star`, 672 particles, angles/origins=0.
- `scripts/data_prep/make_wedge_ctf.py` — shared 3D CTF cubes: `wedge_ctf.mrc` (±60° single-axis,
  ~71% measured) and `uniform_ctf.mrc` (all-ones).
- `scripts/data_prep/make_initial_ref.py` — real-space average of the 672 aligned subtomos →
  `initial_ref.mrc` (low-passed at startup via `--ini_high 60`).
- `scripts/data_prep/run_relion_class3d.sh` — k∈{2,3,4} × CTF∈{wedge,uniform} driver.
- `scripts/analysis/relion_class_report.py` — occupancy/CC/slice figures + `RESULTS.md`.
- `scripts/markdown_instructions/RELION.md` — full runbook (version rationale, star format,
  CTF model, validated flags, results, 3.1 fallback).

## Validated command (the flags that mattered)

```bash
relion_refine --i outputs/relion/particles_wedge.star --ref outputs/relion/initial_ref.mrc \
  --o outputs/relion/Class3D/k2_wedge/run --K 2 --iter 25 --tau2_fudge 4 --ini_high 60 \
  --particle_diameter 960 --skip_align --sym C1 --ctf --skip_subtomo_multi --zero_mask \
  --pad 2 --norm --scale --dont_combine_weights_via_disc --j 8 --gpu ""
```

Gotchas: **`--zero_mask` is mandatory on GPU+3D** (default noise-masking is hard-coded 2D and
aborts — `acc_ml_optimiser_impl.h:365`); **`--skip_subtomo_multi`** + a plain 80³ CTF cube avoids
the pseudo-subtomo multiplicity branch; **`--skip_align`** = pure classification (particles already
aligned), also much faster.

## Results (672 particles, 25 iters)

| Run | Class sizes (occupancy) | Inter-class CC |
|---|---|---|
| k2_wedge   | 656 (98%), 16 (2%) | 0.971 |
| k2_uniform | 637 (95%), 35 (5%) | 0.981 |
| k3_wedge   | 574 (85%), 50, 48 | 0.990–0.996 |
| k3_uniform | 608 (90%), 39, 25 | 0.983–0.993 |
| k4_wedge   | 573 (85%), 42, 29, 28 | 0.987–0.997 |
| k4_uniform | 598 (89%), 32, 25, 17 | 0.979–0.992 |

**Interpretation:** every run = one dominant class (85–98%) + small outliers, class averages
near-identical (CC 0.97–0.997). Maps are genuine pilus density (periodic subunits in XY, missing-
wedge smear in XZ/YZ), so the classifier works — there's just no balanced discrete split.
Wedge vs uniform changes *which* particles peel off but creates no separation ⇒ the missing wedge
is not masking a real signal. **Three independent packages (PyTom, Protomo, RELION) now converge on
"no strong discrete heterogeneity in T4P."**

## Next steps

- Consult **Stefano**: the convergent null makes "is T4P discrete at all?" the gating question.
- **ETSimulations** synthetic ground-truth datasets to distinguish "no real classes" vs "packages
  can't find them."
- Local outputs (not on GitHub): `~/Research/STA/outputs/relion/{Class3D,particles_*.star,ctf,
  initial_ref.mrc}`.

## Where I stopped

All scripts/docs/figures + STATUS + this log committed as **`69d1c1e`** and **pushed to
`origin/main`** (in sync). Memory `project_relion_classification.md` written + indexed.

## Next step

Consult **Stefano** on whether T4P is discretely heterogeneous at all (3-package convergent null),
then proceed to **ETSimulations** synthetic ground-truth datasets. Untracked repo leftovers
(PyTom `*.xml`, root-level `review_alignment.py`/`masked_average.py`/etc.) predate this session and
are unrelated — triage separately.
