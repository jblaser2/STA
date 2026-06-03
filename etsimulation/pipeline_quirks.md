# ETSimulations Pipeline — Bugs, Workarounds, and Non-Obvious Decisions

This document records every gotcha encountered while building the flagellar motor synthetic
dataset (`motor_easy`). Read this before debugging a run that looks stuck or produces
garbage output.

---

## 1. `num_chimera_windows` Must Be in `configs.yaml` and Must Be ≥ 1

**Symptom A:** `KeyError: 'num_chimera_windows'` on startup — the pipeline crashes immediately.

**Symptom B:** `ZeroDivisionError: integer division or modulo by zero` at line 438 of
`ets_generate_data.py` (`chimera_index = pid % num_chimeras`) — the pipeline crashes after
TEM-Simulator finishes.

**Root cause:** ETSimulations always reads this key and computes `num_chimeras = num_chimera_windows`.
Setting the key to `0` (or omitting it and getting a default of 0) causes a division by zero.
ChimeraX is **not actually launched** when `assembler: basic` + `use_common_model: true`, but the
arithmetic still runs.

**Fix:** Always include `num_chimera_windows: 1` in `configs.yaml`.

---

## 2. `scale_mrc` Hangs for 20+ Minutes After TEM-Simulator Finishes

**Symptom:** The main TEM-Simulator run completes in ~3 minutes. The parent process then spawns
worker subprocesses which read the full 626 MB tilt series MRC into memory, set a single header
field (`voxel_size`), and write it back out. These workers consume 99–100% CPU for 20+ minutes
per run. On a 7-run batch this would add 2+ hours of dead time.

**Root cause:** `ets_generate_data.py` calls `scale_mrc()` on every output file to stamp the
correct pixel size into the MRC header. The function uses `mrcfile.open(..., mode='r+')`
then sets `m.voxel_size`, which triggers a full read+write even for a header-only change.
The function runs in multiprocessing workers and the parent waits on `complete_event.wait()`.

**Workaround — poll for MRC file appearance, then move on:**

```bash
MRC="production/class_A/run_01/output/raw_data/MotorA_0/MotorA_0.mrc"
~/conda-envs/etsim/bin/python \
  ~/Research/ETSimulations/src/ets_generate_data.py \
  -i production/class_A/run_01/configs.yaml &> run_01.log &

# Wait only until the MRC file appears (TEM-Simulator done), then kill
until [ -f "$MRC" ] && [ $(stat -c%s "$MRC") -gt 100000000 ]; do sleep 10; done
kill $(pgrep -f "run_01/configs.yaml") 2>/dev/null
pkill -f "ets_generate_data" 2>/dev/null
```

The tilt series MRC is complete once it appears and is >100 MB. The `scale_mrc` step only
sets a header field; we can safely skip it because we know the correct pixel size from
`sim_metadata.json` (`apix` field).

**Important:** `pkill -f ets_generate_data` kills any matching process. If you have multiple
runs going as background tasks, be careful — match by configs path instead:
```bash
kill $(pgrep -f "run_01/configs.yaml")
```

---

## 3. Multiprocessing Workers Become Orphans on `kill -9`

**Symptom:** After killing the parent process with `kill -9`, `ps aux` shows multiple
`python` or `TEM-simulator` processes still running from previous runs, consuming CPU and
competing with the current run.

**Root cause:** Python `multiprocessing` workers are spawned as separate processes. `kill -9`
on the parent does not propagate to them; they continue until they finish their work.

**Fix:** Use `pkill` to kill by argument pattern, or identify orphan PIDs via:
```bash
pgrep -fa "ets_generate_data"
pgrep -fa "TEM-simulator"
```
and kill them manually. Alternatively, use a process group kill:
```bash
kill -- -$(pgrep -f "run_01/configs.yaml" | head -1)
```

---

## 4. Rotation Convention: ZXZ Euler → numpy Array Transform

**Symptom:** Aligned subtomograms are rotated incorrectly — the motor ring appears at wrong
angles, or the average is blurred rather than resolved.

**Root cause:** `scipy.spatial.transform.Rotation.from_euler('ZXZ', angles)` returns a
rotation matrix that acts on **xyz column vectors** (standard math convention). However,
`scipy.ndimage.affine_transform` operates on **zyx array index vectors** (numpy row-major
ordering). Applying the xyz matrix directly to zyx indices produces a wrong rotation.

**Fix — permute the matrix to flip between xyz and zyx conventions:**

```python
from scipy.spatial.transform import Rotation
from scipy.ndimage import affine_transform
import numpy as np

P = np.array([[0, 0, 1],
              [0, 1, 0],
              [1, 0, 0]], dtype=float)   # xyz ↔ zyx permutation matrix

h = BOX // 2
center = np.array([h, h, h], dtype=float)

z1, xt, z2 = euler_angles   # ZXZ, degrees
R = Rotation.from_euler('ZXZ', [z1, xt, z2], degrees=True).as_matrix()
M = P @ R @ P.T              # convert: xyz rotation → zyx array rotation

offset = center - M @ center
aligned = affine_transform(vol, M, offset=offset,
                           order=1, mode='constant', cval=0.0, prefilter=False)
```

This was empirically verified: the `P@R@P.T` convention gave a center/corner signal ratio
of 2.30 vs ~2.17 for all other conventions on no-noise subtomos, and visual inspection of
the average confirmed correct ring alignment.

---

## 5. Coordinate Formula: Single Divide

**Symptom:** Extracted subtomograms show noise/background instead of motor signal; or the
circle overlay (diagnostic image) doesn't line up with visible motors.

**Root cause:** `sim_metadata.json` stores particle positions as `coord_px × apix` (i.e.,
pixel position × nm/px), so the value has units of nm. To get the tomogram pixel position,
divide by `apix` once (not twice).

**Correct formula:**
```python
apix = stk['apix']          # nm/px, e.g. 1.3329 for 13.33 Å/px
pos  = stk['positions']     # stored as real-space nm coordinates

xc = int(round(pos[0] / apix + NX / 2))
yc = int(round(pos[1] / apix + NY / 2))
zc = int(round(pos[2] / apix + NZ / 2))
```

The `+ NX/2` term converts from center-origin (ETSimulations convention) to corner-origin
(numpy/MRC array indexing).

**Double-divide (`pos[0] / apix / apix`) is wrong** — it places particles ~1000× closer
to the tomogram center than they actually are.

---

## 6. Tomogram Array Axis Order: NZ, NY, NX

**Symptom:** Extracted boxes are from the wrong location; computed pixel coordinates are
transposed.

**Root cause:** `mrcfile` returns data as a numpy array with shape `(NZ, NY, NX)` (Z is
the first/slowest axis). It is easy to accidentally assign `NX, NY, NZ = tomo.shape` in
the wrong order.

**Correct unpacking:**
```python
with mrcfile.mmap(tomo_path, mode='r', permissive=True) as m:
    tomo = m.data          # shape is (NZ, NY, NX)
NZ, NY, NX = tomo.shape   # NOT NX, NY, NZ
```

---

## 7. Membrane-Constrained Orientation Pool

For a membrane-embedded complex like the flagellar motor, random SO(3) orientations are
scientifically incorrect. In cryo-ET samples, bacteria lie flat on the grid so the motor
axis is approximately perpendicular to the XY plane. Randomly sampled orientations produce
motors lying on their sides, which never occurs biologically and artificially inflates the
classification difficulty.

**Correct ZXZ sampling for a membrane-perpendicular motor:**
```python
rng = np.random.default_rng(seed)
N = n_particles
z1 = rng.uniform(0, 360, N)                            # azimuthal: fully unconstrained
x  = np.clip(np.abs(rng.normal(0, 10, N)), 0, 30)     # tilt: Gaussian(0°, 10°), clipped ±30°
z2 = rng.uniform(0, 360, N)                            # spin: fully unconstrained
```

The `x` angle (tilt of the motor axis from vertical) uses the absolute value of a Gaussian
so that tilt is always ≥ 0° and most particles are within 10–15° of vertical, matching
published cryo-ET data (Beeby et al. 2016, Chang et al. 2016).

Write these to the `orientations_source` file (one row per particle: `z1 x z2`):
```python
np.savetxt('orient_pool.txt', np.column_stack([z1, x, z2]), fmt='%.4f')
```

---

## 8. Dose Tuning for Realistic SNR

Validated dose for the flagellar motor benchmark (13.33 Å/px, 80³ box, 41 tilts):

| dose_per_im (e⁻/nm²) | Result |
|---|---|
| 30 | No noise visible — motors perfectly clear in individual subtomos |
| 300 | Light noise — motors easily visible, unrealistically clean |
| 1500 | Moderate noise — motors visible but noisy; average slightly blurred |
| **5000** | **Realistic** — individual subtomos show noise with faint ring; average clearly resolves ring |

Set in `sim_test.txt`:
```
dose_per_im = 5000
```

If you change the tilt range, box size, or pixel size, re-validate the dose by opening
3 raw subtomograms and checking that the signal is barely visible before averaging.

---

## 9. Coord File: `z_halfrange` Must Account for Box Padding

**Symptom:** Many particles are flagged as "skipped near edge" during extraction.

**Root cause:** Particles placed too close to the top/bottom of the tomogram (Z = 0 or NZ)
will have their 96³ box partially outside the volume and must be discarded.

**Rule of thumb:** With a 200-slice tomogram (Z = 0..199) and a 96³ box (half = 48 slices),
safe Z centers are in the range [48, 151]. The `z_halfrange` in `gen_coords_random.py`
controls the Z spread around the center (`NZ/2 = 100`). Use `z_halfrange ≤ 50` to keep
particles safely inside.

We used `z_halfrange = 40` in production (safe zone: Z ∈ [60, 140], with 48-slice padding
this gives Z ∈ [60+48, 140−48] = [108, 92] — tight but sufficient with few edge skips).

---

## 10. `sim_test.txt` vs `configs.yaml` Parameter Precedence

`ets_generate_data.py` has two levels of configuration:
- **`configs.yaml`** — high-level pipeline config (model path, output dir, num_cores, etc.)
- **`sim.txt` / `sim_test.txt`** — TEM-Simulator input file (microscope physics, dose, tilt angles)

`dose_per_im`, `tilt_start`, `tilt_incr`, `ntilts` and all microscope parameters live in
`sim_test.txt`. Changing them in `configs.yaml` has no effect. Always edit the `.txt` file
for anything physics-related.

---

## 11. Production Run Layout (Multi-Class, Shared Coords)

To generate a ground-truth-labeled 3-class dataset:
- Use the **same coord files** for all classes (same particle positions and orientations)
- Only the **model MRC** (`class_A_full.mrc`, `class_B_noCring.mrc`, `class_C_core.mrc`)
  differs between classes
- This ensures that any classification signal comes from structural differences, not position
  or orientation bias

Directory layout:
```
production/
├── coords/              # shared coord files: run_01.txt … run_07.txt (seeds 42–48)
├── orient_pool.txt      # shared membrane-constrained orientations
├── sim_test.txt         # shared TEM-Simulator config (dose=5000)
├── class_A/run_01/ … run_07/   # 7 runs (N≈37 particles each → ~259 total)
├── class_B/run_01/ … run_06/   # 6 runs → ~222 particles
└── class_C/run_01/ … run_05/   # 5 runs → ~185 particles
```

Imbalanced class sizes (7/6/5) are intentional — they reflect realistic benchmark conditions
where some conformational states are more common than others.
