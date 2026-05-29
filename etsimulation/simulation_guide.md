# ETSimulations: How to Run a Simulation for This Project

This guide covers everything needed to generate a simulated cryo-ET dataset using
ETSimulations, from picking a density map to getting tilt series output ready for
subtomogram extraction.

---

## Prerequisites

| Requirement | Path |
|---|---|
| ETSimulations repo | `/home/jblaser2/Research/ETSimulations/` |
| TEM-Simulator binary | `/home/jblaser2/Applications/TEM-Simulator/TEM-simulator_1.3/src/TEM-simulator` |
| Conda env | `etsim` at `/home/jblaser2/conda-envs/etsim/` |
| Python (in env) | `mrcfile`, `numpy`, `scipy`, `PyYAML` (already installed) |

UCSF Chimera is **not needed** for the basic assembler workflow described here.

---

## Step 1: Set Up a Working Directory

Each simulation run gets its own directory under `~/Research/etsimulation/`:

```bash
mkdir -p ~/Research/etsimulation/<run_name>/output
```

The `output/` subdirectory must be pre-created — the pipeline does not create it.

**Example:** `~/Research/etsimulation/nora_test/` is the first working test run using
EMD-44143 (NorA-Fab36 complex).

---

## Step 2: Get a Density Map

Download the desired map from EMDB and rename it to `.mrc`.

```bash
# Download (adjust accession number)
wget https://ftp.ebi.ac.uk/pub/databases/emdb/structures/EMD-XXXXX/map/emd_XXXXX.map.gz \
  -P ~/Research/etsimulation/<run_name>/

# Decompress
gunzip ~/Research/etsimulation/<run_name>/emd_XXXXX.map.gz

# Rename to .mrc — required, the pipeline only accepts .mrc model files
mv ~/Research/etsimulation/<run_name>/emd_XXXXX.map \
   ~/Research/etsimulation/<run_name>/emd_XXXXX.mrc
```

**Why rename?** `ets_generate_data.py` checks `source.endswith(".mrc")` in
`src/simulation/tem_simulation.py` to write the TEM-Simulator particle section.
A `.map` file silently skips this block and TEM-Simulator runs with no particles,
producing empty (~1 KB) output MRCs.

Verify the header before continuing:

```bash
/home/jblaser2/conda-envs/etsim/bin/python -c "
import mrcfile
m = mrcfile.open('emd_XXXXX.mrc', permissive=True)
print('voxel size:', m.voxel_size)   # should match EMDB metadata
print('shape:', m.data.shape)
"
```

---

## Step 3: Write a `configs.yaml` for the Run

Copy the template below into `~/Research/etsimulation/<run_name>/configs.yaml` and
fill in the three run-specific fields.

```yaml
---
# --- System paths (do not change) ---
tem_simulator_executable: "/home/jblaser2/Applications/TEM-Simulator/TEM-simulator_1.3/src/TEM-simulator"
chimera_exec_path: "/home/jblaser2/Applications/UCSF-Chimera/bin/chimera"

# --- Run-specific inputs ---
model:    "/home/jblaser2/Research/etsimulation/<run_name>/emd_XXXXX.mrc"   # your density map
root:     "/home/jblaser2/Research/etsimulation/<run_name>/output"          # output directory
name:     "<RunName>"                                                         # prefix for output files

# --- Shared templates (reuse as-is for standard runs) ---
config:   "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/sim.txt"
coord:    "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/coord.txt"
bead_map: "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/bead.mrc"

# --- Simulation parameters ---
num_stacks:          1        # number of tilt series to generate
num_cores:           4
apix:                0.283    # simulation output pixel size in nm (15µm detector / 53000x mag)
                              # this is NOT the model voxel size — that comes from the MRC header
num_chimera_windows: 1
defocus_values:      [1]      # µm underfocus; cycles across stacks if list < num_stacks
bead_occupancy:      0.00025  # random gold fiducial density
assembler:           "basic"
email:               "joshuablaser@gmail.com"

custom_configs:
  orientations_source: "gauss(0, 1)"   # slight random orientation variation (degrees, ZXZ)
  use_common_model: true               # skip Chimera; use model MRC directly for all particles
```

### Key parameter notes

- **`apix`** is the *simulation* pixel size, not the model's. It is fixed by `sim.txt`
  (15 µm detector pixels / 53,000× magnification = 0.283 nm/px). Change only if you
  modify `magnification` or `pixel_size` in `sim.txt`.
- **`model` voxel size** is read automatically from the MRC header by TEM-Simulator.
  No manual entry needed.
- **`defocus_values`** cycles: stack `i` gets `defocus_values[i % len(defocus_values)]`.
  Provide a list to vary defocus across stacks, e.g. `[1, 2, 3]`.
- **`orientations_source: "gauss(0, 1)"`** gives each particle a small random orientation
  drawn from N(0°, 1°) independently for each ZXZ Euler angle. Use `"none"` for all
  identical orientations, or a path to a 3-column angle file to draw from a specific
  distribution.

---

## Step 4: (Optional) Customize Particle Positions

The default `coord.txt` places 9 particles in a 3×3 grid at ±706.7-pixel spacing
on a 2000×2000 detector — appropriate for most test runs. To use different positions,
create your own coordinate file:

```
<N> 6
<x_px> <y_px> <z_px> <Z1_deg> <X_deg> <Z2_deg>
...
```

Units: pixels for positions (relative to detector center), degrees for ZXZ extrinsic
Euler angles. Update `coord:` in `configs.yaml` to point to your file.

---

## Step 5: Run the Simulation

```bash
/home/jblaser2/conda-envs/etsim/bin/python \
  /home/jblaser2/Research/ETSimulations/src/ets_generate_data.py \
  -i /home/jblaser2/Research/etsimulation/<run_name>/configs.yaml
```

Expected runtime: ~3–6 minutes per stack (TEM-Simulator dominates; larger models take
longer — a 360³ map takes ~3.5 min).

**Signs of a successful run:**
- Log prints `Total time taken: X.XXX minutes` (should be > 1 minute)
- Output MRCs are ~500 MB each (not ~1 KB — 1 KB means no particles were simulated)

---

## Step 6: Check Output

```
<run_name>/output/
├── raw_data/
│   └── <RunName>_0/
│       ├── <RunName>_0.mrc           # noisy tilt series (37 tilts)
│       └── <RunName>_0_nonoise.mrc   # noise-free reference
├── sim_metadata.json                 # ground-truth positions + orientations
└── <RunName>.log                     # per-step timing and any errors
```

Quick sanity check:

```bash
python3 -c "
import json
d = json.load(open('output/sim_metadata.json'))
print('stacks:', len(d))
print('particles per stack:', len(d[0]['positions']))
print('apix (nm):', d[0]['apix'])
"
```

To preview a tilt as a PNG (no X forwarding needed):

```bash
/home/jblaser2/conda-envs/etsim/bin/python -c "
import mrcfile, numpy as np
from PIL import Image
with mrcfile.open('output/raw_data/<RunName>_0/<RunName>_0_nonoise.mrc', permissive=True) as m:
    tilt = m.data[18]  # index 18 = ~0 degree tilt
lo, hi = np.percentile(tilt, [1, 99])
img = Image.fromarray((np.clip((tilt - lo)/(hi - lo), 0, 1) * 255).astype('uint8'))
img.save('preview.png')
print('Saved preview.png')
"
```

---

## Default Microscope Parameters (`sim.txt`)

These are fixed in the shared template and match a standard Titan Krios cryo-ET setup:

| Parameter | Value |
|---|---|
| Tilt range | −54° to +54°, 3° step (37 tilts) |
| Acceleration voltage | 300 kV |
| Magnification | 53,000× |
| Detector | 2000 × 2000 px, 15 µm pixel size |
| Output pixel size | 2.83 Å/px (0.283 nm/px) |
| DQE | 0.4 |
| Defocus (default) | 1 µm underfocus (overridden by `defocus_values`) |

To change the tilt scheme or microscope parameters, copy `sim.txt` into your run
directory, edit it, and point `config:` in `configs.yaml` to the local copy.

---

## Completed Test Runs

| Run | Map | Particles | Stacks | Output |
|---|---|---|---|---|
| `nora_test` | EMD-44143 (NorA-Fab36, 2.56 Å) | 9 (3×3 grid) | 1 | `~/Research/etsimulation/nora_test/output/` |
