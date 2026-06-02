# 2026-06-02: TomoNet Evaluation and Rejection

## Goal
Evaluate whether TomoNet (IsoNet-based denoising) is suitable for the STA heterogeneity benchmark, and document the decision.

## What Happened
Eben staged two identical files (`TomoNet/plan.md` and `TomoNet/research.md`) containing a detailed plan to add unsupervised classification to TomoNet via custom autoencoder training. Reviewed and rejected this approach because:

1. **Out-of-box requirement violated:** The benchmark evaluates existing classification packages as shipped. Building custom autoencoders for TomoNet introduces development variables (learning rate, bottleneck dim, training epochs) and duplicates effort already done by RELION, PyTom, and OPUS-TOMO (which are designed for this purpose).
2. **No native classification:** TomoNet only does IsoNet-based missing-wedge correction; classification workflow must be engineered from scratch.
3. **Denoising is separate scope:** IsoNet pre-processing *could* be evaluated separately if benchmarking "optimal pre-processing + existing classifier" becomes a future goal, but not in the current out-of-box scope.

## Files Changed
- **Deleted:** `TomoNet/plan.md` (custom implementation plan)
- **Updated:** `TomoNet/research.md` — consolidated into single evaluation doc:
  - Clear rejection rationale with scope explanation
  - Technical capability table (what *could* be reused)
  - Full implementation details preserved under "Implementation Details (If Reconsidered)" for future reference
- **Updated:** `STATUS.md` — marked TomoNet as ❌ rejected with one-line explanation; updated "Last updated" and "Now/Next/Parked"

## Where I Stopped
All changes staged and ready to commit. STATUS.md reflects TomoNet rejection; research.md is a complete evaluation record with implementation details archived.

## Next Step
Proceed to next package in queue (OPUS-TOMO, MDTOMO, or EMAN2 data-prep — check Eben's STATUS section for current ownership).
