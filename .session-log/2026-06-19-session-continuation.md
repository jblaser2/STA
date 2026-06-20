# Session Continuation Context — 2026-06-19 (FM_easy aligned re-run)

> Purpose: hand this session to the next one (different Claude account). Read this first,
> then `STATUS.md`, then the memory files linked at the bottom.

## Where things stand
The FM_easy dataset was redesigned and all packages re-run. Everything below is **done,
committed, and pushed** (latest commit `08dd860`). The user was about to ask "a few questions"
when we paused to switch accounts — **no new work is in flight.** Pick up by answering the
user's questions; do not start new work without confirmation.

## What FM_easy is now (current canonical dataset)
- **2-class, high-contrast (×6):** 271 class A + 271 class C = **542 particles**, 96³, 13.329 Å/px.
- Classes are **axial halves** of the flagellar motor: A = whole, C = cytoplasmic/lower half.
- GT-pose input:  `~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/`
- Aligned input:  `~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_aligned/`
  (542 particles, same filenames/labels, produced by `scripts/data_prep/align_fm_easy.py`)
- Canonical masks (in `packages/dynamo/dynamo_outputs/easy_pair_AC_hc/`):
  - `diff_sphere_r23_y55.mrc` — sphere, used by **all packages except PyTom**
  - `diff_cyl_r27_h24_y52.mrc` — cylinder, **PyTom only** (CC method benefits; PCA methods hurt)

## The headline scientific result (the "registration is the gap" finding)
Blind classification works on real T4P but collapsed on synthetic FM_easy. We ruled out (by
measurement) class-size, imaging, noise, missing-wedge variance, and membrane. **The cause is
REGISTRATION:** synthetic particles were extracted at ground-truth poses (correct for the clean
map, NOT optimal for co-registering noisy WBP reconstructions). Real T4P particles went through an
actual alignment-refinement pipeline; the synthetic set never did.

**Proof — aligned re-run (blind ARI, GT-pose → aligned):**

| Package        | GT-pose | Aligned | Δ        |
|----------------|---------|---------|----------|
| PyTom (cyl)    | 0.262   | 0.635   | +0.37    |
| Dynamo         | 0.254   | 0.475   | +0.22    |
| ProTomo        | 0.053   | 0.383   | +0.33    |
| DISCA          | 0.407   | 0.455   | +0.05    |
| EMAN2          | 0.146   | 0.326   | +0.18    |
| PEET           | 0.450   | 0.330   | −0.12 (down) |
| RELION-blind   | 0.009   | 0.005   | ≈0 (still collapses) |

Interpretation: alignment **rescues the collapse cases** (their failure was registration, not the
algorithm). **PEET drops** — its many-PC WMD already compensated, and a single-global-reference
alignment adds mild reference bias. **RELION soft-EM still collapses even when aligned →
genuinely algorithmic** (matches its T4P behavior).

## Open follow-up (recorded, NOT yet requested to run)
The alignment in `align_fm_easy.py` is **hand-rolled** (single global reference, iterative FFT
translation + coarse rotational search). To firm up magnitudes and confirm the PEET drop is a
single-ref artifact, swap in a **production aligner** (Dynamo `dalign`, RELION/STOPGAP refine, or
multi-reference). Also consider reducing jitter at the source (sim `tilt_err`, WBP→SIRT) and
deciding whether the benchmark protocol should switch to aligned inputs as standard.

## Other standing facts
- **STOPGAP** cannot run on this node (needs BYU RC cluster + /apps/matlab/r2023b runtime + SLURM).
  It's Eben's package — mark "blocked (cluster)", not ARI≈0.
- **Benchmark fairness:** never give one package GT/class info others lack. GT-seeded RELION
  (init from true class avgs) = supervised upper bound, reported separately, NOT a blind score.
- **k protocol:** FM_easy is now k=2 (was k=3 when 3-class). T4P is k=2. No sweeps unless asked.
- **FM_hard** (new, 2026-06-17): 3-class assembly intermediates (base/basal_body/mature), 813p,
  ×6, SNR 0.299. Package runs pending. (Note: "FM_hard" name was repurposed from the old
  Borrelia-switch dataset, which is now "FM_switch".)

## Recurring environment gotcha
`conda run` + heredoc silently fails (no output, files not written) — recurred ~5× this session.
**Fix:** write Python to `/tmp/*.py`, then `conda run -n <env> python3 /tmp/file.py`. This bit the
RELION aligned STAR/ref build (silent failure → "File does not exist"); rebuilt via a /tmp script.

## Key files
- `scripts/data_prep/align_fm_easy.py` — the blind alignment script
- `results/synthetic_scores.csv` — all scores; aligned rows tagged `k2_AC_hc_x6_542_ALIGNED`
- `packages/figures/FM_easy/` — header maps, mask overlay, perfect confusion, per-package class
  avgs, error-overlap (Jaccard), top-5 missed subtomos, PC diagnostic, eigenspectrum T4P vs synth,
  `align_old_vs_new.png`, `aligned_vs_gtpose.png`
- `STATUS.md` — single source of truth (has the ALIGNED RE-RUN entry + follow-up)

## Relevant memory files
(`/home/jblaser2/.claude/projects/-home-jblaser2-Research-STA/memory/`)
- `fm-easy-registration-is-the-gap.md` ← the main finding
- `fm-easy-mask-shape-and-protomo-factors.md`
- `fm-easy-classification-wall.md`
- `benchmark-gt-seeding-fairness.md`
- `stopgap-cluster-only.md`
- `motor-hard-dataset-design.md`

## Next action
Wait for the user's questions and answer them. Recording + commit of the aligned results is
complete (`08dd860`, pushed). Three orphan watcher shells from the aligned re-run were cleaned up
at end of session — nothing is running.
