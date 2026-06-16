# 2026-06-16 — FM_easy high-contrast regeneration test (decisive)

## Goal
Resolve whether the FM_easy (motor_easy) blind-classification wall is signal absence or
representational, and whether higher contrast rescues an achievable easy tier. Then visualize the
result and update the record.

## What happened
- **Faithful proxies first.** Colored-noise proxy (real ±60° Z-wedge + colored noise whose 3D PSD is
  measured from real class-A subtomos) separates A–C at **ARI≈1.0 even at real SNR 0.21** → wedge +
  colored noise + low SNR are NOT the wall. Jitter proxy: injecting ~20–30° rigid pose jitter drops
  ARI to ~0, reproducing the real failure. Rescue curve: at 20° jitter a 2× SNR boost (0.21→0.42)
  lifts A–C to ARI 0.77.
- **Regenerated A/C through the real ETSim→WBP→extract pipeline** at higher model contrast
  (×3/×6/×10 of base vs production ×0.1). Findings: (1) **SNR saturates ~0.4** (×10 dropped to 0.30;
  strong-phase nonlinearity) — can't buy arbitrary SNR via contrast. (2) **Narrow wedge doesn't help**
  (±70°/2°/71 = 40° wedge vs ±60°/3°/41, matched dose: ARI 0.12 vs 0.18). (3) **Contrast strongly
  raises recoverable signal:** ×6 (SNR 0.36, 354 particles) **supervised 5-fold ceiling = ARI 0.796 /
  95% acc** (was 0.43 at production SNR). (4) **Dynamo dpkpca k=2 went 0.003 → 0.280** (acc 0.77,
  95%-pure C cluster).
- **Conclusion:** the wall is **REPRESENTATIONAL** — blind clustering optimizes the dominant-variance
  (nuisance/contrast) axis; the class difference is ~95%-recoverable with labels at higher contrast.
  Corrected the earlier WRONG "SNR is a dead lever" conclusion across STATUS / memory / docs.
- **Visual confirmation.** Rendered (a) single subtomos production vs high-contrast (hc legible per
  particle — A extends down the box, C truncated to top base), (b) hc GT class averages (A=extended
  assembly, C=base only), (c) **Dynamo's two cluster averages match the GT classes** (cluster1 95%-pure
  C = truncated/empty-below; cluster2 A-enriched = extended density) → Dynamo split on the *real*
  structural axis.

## Files changed
- `STATUS.md` — top entry already documented the hc test; added the visual-confirmation paragraph.
- `docs/fm_easy_classification_analysis.md` — ⚠️ correction banner + resolution section (representational wall).
- memory `fm-easy-classification-wall.md` — hc-test results + correction.
- New: `scripts/eval/colored_noise_{snr,jitter}_proxy_motor_easy.py`,
  `packages/dynamo/FM_easy/scripts/setup_hc_pair_pca.py`,
  `packages/dynamo/dynamo_outputs/easy_pair_AC_hc/` (predictions, score/fig scripts, confusion PNG),
  `outputs/FM_easy/input_qc/snr_rescue_curve.png` and other QC PNGs.
- `.gitignore` — added `*.wfs` (Dynamo internal binaries, 5–18 MB each).
- Pipeline (local, not in repo): `synthetic_sta/motor_easy/hc_test*/`.

## Where I stopped
Investigation complete and recorded. Repo files staged + committed + pushed.

## Next step
nc-sweep Dynamo + GT-seeded RELION on the hc set to see how close to the 0.80 supervised ceiling a
real method reaches; then decide the easy-tier contrast level for a full regeneration.
