"""
Compute the global average of all 672 T4P subtomograms and export it
as starting_average.mrc (local only) and starting_average.npy (committed).

Requires: pytom_env conda environment (has mrcfile and PyTom).

Usage:
    conda run -n pytom_env python compute_starting_average.py
"""
import os
import xml.etree.ElementTree as ET
import numpy as np
import mrcfile

here = os.path.dirname(os.path.abspath(__file__))

PARTICLE_LIST = '/home/jblaser2/Research/STA/PyTom/particle_list.xml'
OUT_MRC = os.path.join(here, 'starting_average.mrc')
OUT_NPY = os.path.join(here, 'starting_average.npy')
MASK_NPY = os.path.join(here, 'cylindrical_mask.npy')

tree = ET.parse(PARTICLE_LIST)
filenames = [p.get('Filename') for p in tree.getroot().findall('Particle')]
print(f"Found {len(filenames)} particles")

accumulator = None
for i, fname in enumerate(filenames):
    with mrcfile.open(fname, mode='r', permissive=True) as mrc:
        data = mrc.data.astype(np.float64)
    accumulator = data.copy() if accumulator is None else accumulator + data
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(filenames)}")

avg = (accumulator / len(filenames)).astype(np.float32)
print(f"Average: shape={avg.shape}, min={avg.min():.4f}, max={avg.max():.4f}")

with mrcfile.new(OUT_MRC, overwrite=True) as mrc:
    mrc.set_data(avg)
    mrc.voxel_size = 13.328
print(f"Saved {OUT_MRC}  (local only — gitignored)")

np.save(OUT_NPY, avg)
print(f"Saved {OUT_NPY}")

# Also regenerate cylindrical_mask.npy from .em for consistency
from pytom.lib.pytom_volume import read as em_read
from pytom.lib.pytom_numpy import vol2npy
mask_vol = em_read(os.path.join(here, 'cylindrical_mask.em'))
mask_arr = vol2npy(mask_vol).copy().astype(np.float32)
np.save(MASK_NPY, mask_arr)
print(f"Saved {MASK_NPY}  ({int(mask_arr.sum())} active voxels)")
