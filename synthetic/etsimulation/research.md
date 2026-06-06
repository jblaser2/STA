# ETSimulations: Cryo-ET Simulation Pipeline

ETSimulations is an open-source pipeline for generating synthetic cryo-electron tomography (cryo-ET) datasets. It couples UCSF Chimera (for particle model assembly) with TEM-Simulator (for physics-based tilt-series generation), producing both noisy and noise-free MRC stacks with full ground-truth metadata. This makes it directly useful for benchmarking subtomogram averaging (STA) workflows, training machine learning models, and validating reconstruction pipelines.

**Repo:** https://github.com/kmshin1397/ETSimulations  
**Installation (this machine):** `/home/jblaser2/Research/ETSimulations`

---

## Installation on This Machine

### Dependencies

| Dependency | Status | Path |
|---|---|---|
| Python 3.10 (conda env `etsim`) | Installed | `/home/jblaser2/conda-envs/etsim/` |
| TEM-Simulator 1.3 | Compiled | `/home/jblaser2/Applications/TEM-Simulator/TEM-simulator_1.3/src/TEM-simulator` |
| UCSF Chimera | Not needed for basic assembler | Install to `/home/jblaser2/Applications/UCSF-Chimera/` if needed |
| FFTW3 | Pre-installed (RHEL system) | `/lib64/libfftw3*` |

### TEM-Simulator Build

Downloaded from SourceForge (v1.3), compiled with GCC 14.3 against system FFTW:

```bash
cd /home/jblaser2/Applications/TEM-Simulator/TEM-simulator_1.3/src
make
```

No Makefile edits required — GCC and FFTW headers were already on the default paths.

### Python Environment

```bash
conda create -n etsim python=3.10 -y
conda run -n etsim pip install mrcfile numpy scipy PyYAML requests pytest pytest-mock
```

The pinned versions in `requirements.txt` are too old for Python 3.10; installing without version pins works correctly.

### Run Command

```bash
cd /home/jblaser2/Research/ETSimulations
/home/jblaser2/conda-envs/etsim/bin/python src/ets_generate_data.py -i configs.yaml
```

---

## Configuration

The pipeline is driven entirely by `configs.yaml`. The installed copy at `/home/jblaser2/Research/ETSimulations/configs.yaml` is configured for this machine:

```yaml
# Executables
tem_simulator_executable: "/home/jblaser2/Applications/TEM-Simulator/TEM-simulator_1.3/src/TEM-simulator"
chimera_exec_path: "/home/jblaser2/Applications/UCSF-Chimera/bin/chimera"  # only needed for non-basic assembler

# Input files (templates ship with the repo)
model:  "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/bead.mrc"
config: "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/sim.txt"
coord:  "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/coord.txt"
bead_map: "/home/jblaser2/Research/ETSimulations/templates/tem_simulator/bead.mrc"

# Output
root: "/home/jblaser2/Research/ETSimulations/output"
name: "Bead"

# Simulation parameters
num_stacks: 1
num_cores: 4
apix: 0.283          # pixel size in nm
defocus_values: [1]  # µm; cycles across stacks if list is shorter than num_stacks
bead_occupancy: 0.00025
num_chimera_windows: 1

# Assembler
assembler: "basic"
custom_configs:
  orientations_source: "gauss(0, 1)"
  use_common_model: true   # skips Chimera entirely
```

### Full Parameter Reference

**Persistent (system-level)**

| Parameter | Type | Purpose |
|---|---|---|
| `tem_simulator_executable` | path | Full path to TEM-Simulator binary |
| `chimera_exec_path` | path | Full path to UCSF Chimera binary |

**Run-specific**

| Parameter | Type | Purpose |
|---|---|---|
| `model` | path | Base particle model MRC |
| `root` | path | Output root directory |
| `config` | path | TEM-Simulator config template (sim.txt) |
| `coord` | path | Particle coordinate template |
| `num_stacks` | int | Total tilt series to generate |
| `name` | str | Project name; prefixes all output files/dirs |
| `num_cores` | int | Parallel worker processes |
| `apix` | float | Pixel size in nm |
| `num_chimera_windows` | int | Chimera REST server instances |
| `defocus_values` | list[float] | Defocus values in µm; cycled across stacks |
| `bead_map` | path | Fiducial marker MRC (gold beads) |
| `bead_occupancy` | float | Random fiducial density in sample volume |
| `assembler` | str | `"basic"` or `"t4ss"` (or custom) |
| `email` | str | Optional notification address on completion |

**BasicAssembler `custom_configs`**

| Parameter | Type | Purpose |
|---|---|---|
| `use_common_model` | bool | If true: skip Chimera, use model directly for all particles |
| `orientations_source` | str | `"none"`, `"gauss(mu, sigma)"`, or path to angle file |
| `orientations_error` | `{mu, sigma}` | Gaussian noise added to orientations |
| `coord_error` | `{mu, sigma}` | Gaussian noise added to coordinates (pixels) |

**T4SSAssembler `custom_configs`**

| Parameter | Type | Purpose |
|---|---|---|
| `membrane_path` | path | Membrane background structure MRC |
| `barrel` | path | Central barrel complex MRC |
| `rod` | path | Peripheral rod structure MRC |
| `orientations_tbl` | path | Dynamo `.tbl` file with orientation distribution |
| `num_rods` | int | Rods per complex (arranged in circle) |
| `rod_distance_from_center` | float | Distance of rods from barrel center (pixels) |

---

## Architecture Overview

### Two-Stage Pipeline

1. **Data Generation** (`src/ets_generate_data.py`) — produces raw simulated tilt stacks
2. **Data Processing** (`src/ets_process_data.py`) — sets up downstream STA workflows (EMAN2, IMOD, Dynamo, Artiatomi, I3)

### Process Hierarchy

```
Main Process
├── Logger Listener Process
│   └── Aggregates logs → <name>.log
├── Metadata Logger Process
│   └── Aggregates metadata → sim_metadata.json
├── Chimera Server Process(es)   [num_chimera_windows]
│   └── REST server on localhost:<port>
└── Worker Processes             [num_cores]
    └── run_process() — simulation loop
```

### Key Source Files

| File | Purpose |
|---|---|
| `src/ets_generate_data.py` | Main entry; orchestrates multiprocessing |
| `src/ets_process_data.py` | Post-processing setup for STA tools |
| `src/simulation/tem_simulation.py` | `Simulation` class — wraps TEM-Simulator config and execution |
| `src/simulation/chimera_server.py` | `ChimeraServer`, `ChimeraCommandSet` — HTTP REST interface |
| `src/simulation/particle_set.py` | `ParticleSet` — aggregates particle data for one stack |
| `src/simulation/logger.py` | Multiprocessing-safe logging infrastructure |
| `src/assemblers/basic_assembler.py` | `BasicAssembler` — simple/no-Chimera particle placement |
| `src/assemblers/t4ss_assembler.py` | `T4SSAssembler` — multi-component T4SS complex assembly |
| `src/processors/eman2_processor.py` | EMAN2 workflow setup |
| `src/processors/imod_processor.py` | IMOD/batchruntomo setup + coordinate conversion |
| `src/processors/dynamo_processor.py` | Dynamo MATLAB script generation |
| `src/processors/artiatomi_processor.py` | EmSART config and MOTL file generation |

---

## Data Flow

```
configs.yaml
    │
    ▼
main() → creates raw_data/, launches processes
    │
    ├── [per worker] run_process()
    │       │
    │       ├── Copy sim.txt, coord.txt → temp_{pid}/
    │       ├── Instantiate Assembler
    │       └── [per stack]
    │               │
    │               ├── Assembler.set_up_tiltseries(sim)
    │               │       └── (optional) Chimera REST commands
    │               │           → particle MRCs in temp_{pid}/
    │               │
    │               ├── Modify sim.txt (output paths, defocus)
    │               ├── Add fiducial config to sim.txt
    │               ├── TEM-Simulator → Bead_0.mrc + Bead_0_nonoise.mrc
    │               ├── Scale MRC voxel sizes (apix × 10 Å)
    │               └── Enqueue metadata JSON
    │
    ├── metadata_queue → sim_metadata.json
    └── logs_queue    → <name>.log
```

---

## Assembler Framework

Assemblers are responsible for preparing particle models and populating `ParticleSet` objects before TEM-Simulator runs.

### BasicAssembler

- **`use_common_model: true`** — No Chimera needed. The single `model` MRC is referenced directly for all particles. Fastest option.
- **`use_common_model: false`** — Chimera opens `model` and saves a copy per particle to `temp_{pid}/truth_vols/<i>.mrc`. Supports per-particle orientation/coordinate error injection.

Orientation generation (`orientations_source`):
- `"none"` → [0, 0, 0]
- `"gauss(mu, sigma)"` → three independent normals for Z1, X, Z2 (degrees)
- `"/path/to/file"` → random row from space-separated 3-column angle file

### T4SSAssembler

Simulates Type IV Secretion System complexes by assembling multiple sub-structures in Chimera:

1. **Membrane** — background slab (1.5× scaled)
2. **Barrel** — central complex, rotated around X/Y axes
3. **Rods** — `num_rods` copies arranged in a circle at `rod_distance_from_center` pixels, each with random Z rotation

Assembly per particle:
1. Load orientations from Dynamo `.tbl` file
2. Apply 90° X-axis correction (side-view convention)
3. Add membrane, barrel, rods with random angle offsets
4. Combine volumes (`vop add`, `vop scale`)
5. Save assembled MRC

### Custom Assembler

Implement the `BasicAssembler` interface:
```python
class MyAssembler:
    def __init__(self, model, temp_dir, chimera_queue, ack_event, pid, custom_args): ...
    def set_up_tiltseries(self, simulation) -> simulation: ...
    def reset_temp_dir(self): ...
    def close(self): ...
```

Register in `ets_generate_data.py`:
```python
assembler_registry["my_assembler"] = MyAssembler
```

---

## TEM-Simulator Integration

### How `sim.txt` Is Modified

ETSimulations starts from the template `sim.txt` and modifies it per-stack:

| Field | Set at runtime |
|---|---|
| `image_file_out` (noisy) | `Simulation.edit_output_files()` |
| `image_file_out` (nonoise) | `Simulation.__replace_nonoise()` |
| `log_file` | `Simulation.edit_output_files()` |
| `defocus_nominal` | `Simulation.edit_output_files()` |

For each particle set, it appends:
```
=== particle <name> ===
source = map
map_file_re_in = <mrc_path>

=== particleset ===
particle_type = <name>
num_particles = <count>
particle_coords = file
coord_file_in = <coord_path>
```

And for fiducials:
```
=== particle Fiducial ===
source = map
map_file_re_in = <bead_map>

=== particleset ===
particle_type = Fiducial
occupancy = <bead_occupancy>
particle_coords = random
where = volume
```

### Default Simulation Parameters (sim.txt template)

- Detector: 2000×2000 pixels, 15 µm pixel size, 300 kV, DQE=0.4
- Tilt series: 37 images, −54° to +54° in 3° increments
- Magnification: 53000×
- Two detector sections: one with quantization (noisy), one without (noise-free)

### Coordinate File Format

```
<num_particles> 6
<x_pix> <y_pix> <z_pix> <Z1_deg> <X_deg> <Z2_deg>
```

Units: pixels for coordinates, degrees for ZXZ extrinsic Euler angles (reference-to-particle convention).

---

## Output Format

### Directory Structure

```
root/
├── raw_data/
│   ├── <name>_0/
│   │   ├── <name>_0.mrc            # Noisy tilt series
│   │   └── <name>_0_nonoise.mrc    # Noise-free tilt series
│   ├── <name>_1/
│   │   └── ...
│   └── ...
├── sim_metadata.json
└── <name>.log
```

### MRC File Specs

- Shape: 2000 × 2000 × 37 (X × Y × tilts)
- Voxel size: `apix × 10` Å set in header
- Size: ~296 MB per file, ~592 MB per stack (both versions)

### `sim_metadata.json` Schema

```json
[
  {
    "output": "/path/to/<name>_0.mrc",
    "nonoise_output": "/path/to/<name>_0_nonoise.mrc",
    "global_stack_no": 0,
    "apix": 0.283,
    "defocus": 1,
    "sim_configs": "/path/to/sim.txt",
    "particle_coords": "/path/to/coord.txt",
    "orientations": [[z1, x, z2], ...],   // one per particle, radians
    "positions": [[x, y, z], ...],         // one per particle, nm
    "custom_data": {
      "true_orientations": [...],
      "true_coordinates": [...],
      // assembler-specific fields
    }
  }
]
```

**Note:** Defocus assignment cycles: stack `i` gets `defocus_values[i % len(defocus_values)]`.

---

## Processor Framework

`ets_process_data.py` sets up downstream STA workflows from the generated data. Driven by `processor_configs.yaml`.

Supported processors: `eman2`, `imod`, `dynamo`, `artiatomi`, `i3`

Each processor:
1. Copies templates to `processed_data/<processor>/`
2. Substitutes parameters (box size, apix, paths, etc.)
3. Generates a ready-to-run script (Python or MATLAB)
4. Writes `processor_info.json` with timestamp and arguments

Key coordinate transformations applied by processors:
- **Z-rotation by 90°** — accounts for reconstruction orientation in IMOD
- **ZXZ extrinsic → software-specific Euler** conversion
- **Pixel → nm** coordinate scaling

Example `processor_configs.yaml` (Dynamo):
```yaml
root: "/home/jblaser2/Research/ETSimulations/output"
name: "Bead"
processors:
  - name: "dynamo"
    args:
      box_size: 64
      num_workers: 12
      apix: 0.283
      sym_r1: "c1"
      gpus: 0
```

---

## Performance

### Parallelism

- Stacks distributed across `num_cores` workers; remainder stacks go to lower-PID cores first
- Each worker has an independent temp directory
- Chimera server is a shared bottleneck (increase `num_chimera_windows` if using Chimera heavily)

### Timing (approximate, per stack)

| Stage | Time |
|---|---|
| Assembler (Chimera, if used) | 30–60 s |
| TEM-Simulator | 2–5 min |
| MRC scaling | < 1 s |
| **Total per stack** | **~3–6 min** |

### Disk Usage

- ~592 MB per stack (both MRC versions)
- 100 stacks ≈ 60 GB

---

## Chimera Requirement

Chimera is **only needed** when:
- Using `assembler: "t4ss"`
- Using `assembler: "basic"` with `use_common_model: false`

For `basic` assembler with `use_common_model: true` (current config), Chimera is skipped entirely.

To install Chimera if needed:
1. Go to https://www.cgl.ucsf.edu/chimera/download.html in a browser
2. Accept the license agreement (non-commercial academic use)
3. Download `chimera-1.19-linux_x86_64.bin`
4. Run: `chmod +x chimera-1.19-linux_x86_64.bin && ./chimera-1.19-linux_x86_64.bin`
5. Install to `/home/jblaser2/Applications/UCSF-Chimera/`
6. Update `chimera_exec_path` in `configs.yaml`

**Note:** ETSimulations uses UCSF Chimera 1.x (legacy), not ChimeraX. It communicates via a REST server interface (`http://localhost:<port>/run`).

---

## Verified Working Test

A test simulation was run successfully on 2026-05-27:

```
output/raw_data/Bead_0/Bead_0.mrc          # 496 MB noisy stack
output/raw_data/Bead_0/Bead_0_nonoise.mrc  # 496 MB clean stack
output/sim_metadata.json                    # 9-particle ground truth
```

9 particles in a 3×3 grid, 37 tilts (−54° to +54°), 0.283 nm/px, 1 µm defocus.
