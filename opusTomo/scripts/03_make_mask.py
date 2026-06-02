#!/usr/bin/env python3
"""Average all subtomograms to produce a consensus map, then threshold it
to create a solvent mask.

For pili (rod-shaped particles, z-axis aligned) the averaged density will
naturally be cylindrical. Inspect consensus.mrc in ChimeraX after running;
if the automatic threshold looks wrong, adjust SIGMA_THRESH below or switch
to the explicit cylinder option at the bottom of this file.
"""
import glob, os, sys
import numpy as np
import mrcfile
from scipy.ndimage import binary_dilation

PARTICLE_DIR  = os.path.expanduser('~/src/particles')
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CONSENSUS_OUT = os.path.join(SCRIPT_DIR, 'consensus.mrc')
MASK_OUT      = os.path.join(SCRIPT_DIR, 'mask.mrc')
APIX          = 13.33
SIGMA_THRESH  = 1.0    # threshold = mean + SIGMA_THRESH * std; raise if mask is too large
DILATE_ITERS  = 2      # voxels to grow the mask boundary

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

# --- Mask by threshold ---
thresh = avg.mean() + SIGMA_THRESH * avg.std()
mask = (avg > thresh).astype(np.float32)
mask = binary_dilation(mask, iterations=DILATE_ITERS).astype(np.float32)

with mrcfile.new(MASK_OUT, overwrite=True) as m:
    m.set_data(mask)
    m.voxel_size = APIX

frac = 100 * mask.mean()
print(f'Mask ({frac:.1f}% of voxels) -> {MASK_OUT}')
print()
print('Inspect consensus.mrc and mask.mrc in ChimeraX.')
print('If the mask looks wrong, adjust SIGMA_THRESH or use the cylinder option below.')

# --- Optional: explicit cylinder (uncomment to use instead of threshold) ---
# For pili where the averaged mask is too noisy to threshold cleanly.
# Measure radius_xy and length_z from consensus.mrc in ChimeraX, then uncomment:
#
# D = 80
# radius_xy = 12   # voxels (~160 Å); adjust to pilus diameter
# length_z  = 70   # voxels; adjust to pilus length visible in the average
# c = D // 2
# zz, yy, xx = np.mgrid[:D, :D, :D]
# cyl = (
#     ((yy - c)**2 + (xx - c)**2 <= radius_xy**2) &
#     (np.abs(zz - c) <= length_z // 2)
# ).astype(np.float32)
# cyl = binary_dilation(cyl, iterations=1).astype(np.float32)
# with mrcfile.new(MASK_OUT, overwrite=True) as m:
#     m.set_data(cyl)
#     m.voxel_size = APIX
# print(f'Cylinder mask (r={radius_xy}px, l={length_z}px) -> {MASK_OUT}')
