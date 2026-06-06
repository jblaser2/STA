# Packages Considered but Not Tested

This benchmark evaluates **out-of-the-box 3D-input classification packages** on pre-extracted
subtomograms under identical preprocessing. The packages below were evaluated against that
criterion and excluded for the reasons listed.

| Package | Algorithm | Reason Excluded |
|---------|-----------|-----------------|
| **TomoNet** | IsoNet denoising (3D U-Net) | Denoising only — no built-in classification or clustering workflow. Would require training custom convolutional autoencoders, which introduces design variables (bottleneck size, epochs, learning rate) outside the package's documented scope. Custom development would duplicate packages like OPUS-TOMO and RELION that are purpose-built for classification. |
| **emClarity** | Tilt-series subtomogram averaging | Cannot ingest pre-extracted subtomograms; requires full raw tilt-series data and a complete in-house STA pipeline. No path to evaluate on the T4P real dataset. Deferred to synthetic-data track where tilt-series could be provided, but not yet run. |
| **MDTOMO** | ContinuousFlex normal-mode analysis (Scipion3) | Requires an initial atomic model or high-resolution reference map to compute normal modes. Cannot sort conformational populations from subtomograms without prior structural knowledge. |
| **HEMNMA-3D** | ContinuousFlex hybrid EM/NMA (Scipion3) | Same limitation as MDTOMO — requires an atomic model as input. Both MDTOMO and HEMNMA-3D are designed for fine-structure refinement, not initial heterogeneity sorting. |
| **AC3D** | Angular correlation 3D | Implemented inside the PyTom codebase as an optional classification mode. Evaluated implicitly through the PyTom package run. |

## Notes

- **emClarity** was installed and GPU-verified on this machine (RTX 5080 / sm_120). See
  `packages/STOPGAP/` and `STATUS.md` for the current status of packages still being run.
- **TomoNet** was evaluated in detail before rejection; see `git log` for the full technical
  analysis that was committed and later consolidated into this file.
- The benchmark scope is 3D-input classifiers that operate on pre-extracted subtomograms
  out-of-the-box. Extending to 2D-input classifiers (operating on tilt-series images) is a
  natural next step discussed in `README.md`.
