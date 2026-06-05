#!/usr/bin/env python3
"""Average all subtomograms to produce a consensus map, then threshold it
to create a solvent mask.

For pili (rod-shaped particles) the averaged density will naturally be
cylindrical. Inspect consensus.mrc in ChimeraX after running; if the
automatic threshold looks wrong, adjust SIGMA_THRESH below.

This is the OPUS-TOMO baseline mask — broader than the v2 cylindrical mask
used by PyTom (which is too tight for the VAE's global template reconstruction).
"""
import glob, os, sys
import numpy as np
import mrcfile
from scipy.ndimage import binary_dilation

PARTICLE_DIR  = os.path.expanduser('~/Research/STA/subtomos_mrc')
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CONSENSUS_OUT = os.path.join(SCRIPT_DIR, 'consensus.mrc')
MASK_OUT      = os.path.join(SCRIPT_DIR, 'mask.mrc')
APIX          = 13.33
SIGMA_THRESH  = 1.0
DILATE_ITERS  = 2

files = sorted(glob.glob(os.path.join(PARTICLE_DIR, 'aligned_tom*.mrc')))
if not files:
    sys.exit(f'ERROR: No MRC files found in {PARTICLE_DIR}')

# --- Average ---
print(f'Averaging {len(files)} volumes...')
acc = None
for i, f in enumerate(files):
    if i % 100 == 0:
        print(f'  {i}/{len(files)}')
    with mrcfile.open(f, permissive=True) as m:
        v = m.data.astype(np.float32)
    acc = v.copy() if acc is None else acc + v
avg = acc / len(files)

with mrcfile.new(CONSENSUS_OUT, overwrite=True) as m:
    m.set_data(avg)
    m.voxel_size = APIX
print(f'Consensus map  -> {CONSENSUS_OUT}')

# --- Threshold mask ---
thresh = avg.mean() + SIGMA_THRESH * avg.std()
mask = (avg > thresh).astype(np.float32)
mask = binary_dilation(mask, iterations=DILATE_ITERS).astype(np.float32)

with mrcfile.new(MASK_OUT, overwrite=True) as m:
    m.set_data(mask)
    m.voxel_size = APIX

frac = 100 * mask.mean()
print(f'Threshold mask ({frac:.1f}% voxels, sigma={SIGMA_THRESH}) -> {MASK_OUT}')
