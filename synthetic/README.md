# Synthetic Data

This directory contains pipeline documentation and analysis scripts for the synthetic benchmark
datasets. **Actual simulation data lives locally** at `~/Research/synthetic_sta/` and is not
committed to the repo (too large and machine-specific).

---

## Current Dataset — motor_easy

**3-class flagellar motor assembly intermediate, ~30 Å structural differences between classes.**

| Class | Definition | N particles |
|-------|-----------|-------------|
| A | Full motor (rod + hook + C-ring) | 246 |
| B | No C-ring | 271 |
| C | C-ring only (C_noRodHook) | 177 |
| **Total** | | **694** |

**Class definitions redesigned 2026-06-05:** Class C changed from nested C_core (old: B minus
rod/hook, L2=0.340) to C-ring only (CUT2_C=46.5 base px, L2=0.387 vs A). The old nested
A⊃B⊃C structure was the root cause of RELION/PEET B/C confusion.

**Current state:** Class A and B particles are simulated and committed to the local pipeline.
**Class C re-simulation is needed** using the new `class_C_noRodHook.mrc` map before any
package runs reflect the redesigned classes.

**Specifications:**
- Pixel size: 13.33 Å/px (matched to real T4P data)
- Box size: 80³ (particles), 96³ (reconstruction)
- Tilt-series: ±60°, simulated with ETSimulations
- Reconstruction: IMOD WBP
- SNR: matched to real T4P data

**Ground-truth separability (old class C):**
- Template-matching ARI = 0.289 (confirmed structural signal present)
- Class average CCs: A–B=0.72, A–C=0.66, B–C=0.83

**Mask for classification:** r=32 px, center offset Y=−10 (center at 48,38 in 96³ box).

---

## `etsimulation/` — Pipeline documentation and scripts

Contains documentation, quirks, and research notes for the ETSimulations pipeline used
to generate the synthetic datasets.

| File | Description |
|------|-------------|
| `simulation_guide.md` | Step-by-step simulation instructions |
| `pipeline_quirks.md` | Documented bugs and workarounds (mkdir issue, metadata truncation) |
| `research.md` | ETSim workflow notes and validation |
| `figures/` | Synthetic data visualizations (class maps, tomo reconstructions, averages) |

---

## Local Pipeline Location

Full simulation data at `~/Research/synthetic_sta/motor_easy/production/` on this machine.
Pipeline scripts: `01_setup.py`, `02_reconstruct.sh`, `03_rotate.sh`, `04_convert_coords.py`,
`05_extract.py`. Conda env: `etsim`.
