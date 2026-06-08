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

## Dataset 2 — motor_switch (complete 2026-06-08)

**2-class + junk Borrelia burgdorferi flagellar motor CCW↔CW rotational switching.**

| Class | Definition | N particles |
|-------|-----------|-------------|
| ccw | CCW rotational state (EMD-21884) | 200 |
| cw | CW rotational state (EMD-21886) | 200 |
| junk | Gaussian sphere (0.01× amplitude, pure noise) | 30 |
| **Total** | | **430** |

**Source:** Chang et al. 2020, *Nature Struct Mol Biol* 27:1041–1047 — in-situ subtomogram averaging of cryo-vitrified Borrelia burgdorferi cells. Both maps are SPA-incompatible (native Na⁺-driven stators fall off on purification; conformational change requires proton motive force in native context).

**Difficulty:** Semi-difficult. FliG C-terminal domain repositions ~15–25 Å during CCW↔CW switching. Same mass, same topology in both states — no domain additions/removals. Masked CC between clean maps at 13.33 Å/px: **0.631** (harder than motor_easy A-B: 0.539).

**Specifications:**
- Pixel size: 13.33 Å/px; box size: 96³; tilt-series: ±60°; reconstruction: IMOD WBP
- Maps: EMD-21884/21886 resampled from 2.747 Å/px → 13.33 Å/px (Gaussian anti-alias + zoom); transposed to Y-axis convention; scaled ±9V per map independently; embedded in 96³ box (motor at z:[33-61], y:[23-71], x:[33-61])
- Orientation model: membrane-perpendicular ZXZ (same as motor_easy); orient_pool 1000 entries, seed=42

**GT-aligned average validation:**
- CCW avg vs CW avg masked CC: 0.266 (averages structurally distinguishable)
- Signal/background ratio in GT averages: 2.9–3.8× (structural signal confirmed)
- WBP inverts density (same convention as motor_easy; negated avg correlates +0.11/+0.17 with own clean map)

**Local pipeline:** `~/Research/synthetic_sta/motor_switch/production/`
- Coord files: `coords/run_01–06.txt` (35p each), `run_junk.txt` (30p)
- Merged particles: `subtomos/merged_ccw/`, `subtomos/merged_cw/`, `subtomos/merged_junk/`
- Master list: `subtomos/all_particles/labels.csv` (ccw/cw/junk)
- GT averages: `subtomos/avg_ccw_aligned.mrc`, `subtomos/avg_cw_aligned.mrc`
- Run scripts: `~/Research/synthetic_sta/motor_switch/run_class_{ccw,cw,junk}.sh`

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
