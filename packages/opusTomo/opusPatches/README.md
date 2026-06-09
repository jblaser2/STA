# opusPatches — patched OPUS-ET (opusTomo) source files

These are drop-in replacements for two files in the `cryodrgn/` package of OPUS-ET
(opusTomo). Stock opusTomo **crashes** on the all-zero-pose / no-CTF / pre-aligned
subtomogram workflow used for the pili classification (see `../research.md`); these two
files carry the fixes.

| File | Replaces | Fixes |
|---|---|---|
| `models.py` | `opusTomo/cryodrgn/models.py` | **Bug 4** — NaN loss from a negative CTF exponent |
| `pose.py`   | `opusTomo/cryodrgn/pose.py`   | **Bug 3** — `ValueError: need at least one array to concatenate` when all particles share one HEALPix pose bin |

## How to apply

Starting from a fresh opusTomo checkout:

```bash
# 1. copy these two files over the originals
cp models.py pose.py  /path/to/opusTomo/cryodrgn/

# 2. (re)install editable
cd /path/to/opusTomo
pip install -e .
```

That's it — no other source files are modified.

## What the patches are

- **pose.py** — `sample_full_neighbors()` / `sample_neighbors()`: guard `pose_sample.remove(cur_idx)`
  and fall back to sampling within the single occupied bin when it would otherwise be empty.
  Safe because `--lamb 0` zeroes the contrastive term that uses these samples.
- **models.py** — clamp the CTF exponent to ≥ 0:
  `c.abs().pow(max(self.ctf_beta + ctf_beta_rand, 0.0))`, so CTF zeros don't blow up to Inf→NaN
  when `ctf_beta = 0`.

Full rationale and the exact before/after diffs are in `../research.md`
("OPUS-ET Source Code Bugs and Fixes", Bugs 3 & 4).

## What is NOT here (handled outside the source tree)

These other fixes do **not** patch opusTomo — they live in the pipeline scripts
(`../T4P/scripts/`) and are documented in `../research.md`:

- **Bug 1** (`_rlnCtfImage` always required) → a dummy CTF STAR in the particle dir.
- **Bug 2** (`args.split is None` crash) → always pass `--split`.
- **Bug 5** (`snr` undefined when the orientation search is collapsed) and skipping the
  in-training orientation search → the `train_skipalign.py` wrapper, which monkeypatches
  `VanillaDecoder.get_particle_hopfs` at runtime (returns two identical seed orientations).

So a colleague needs: **these two files** + the **pipeline scripts** + the **input particles**
+ `research.md`. See `research.md` → "What to Share for Replication".
