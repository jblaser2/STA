import xml.etree.ElementTree as ET
import numpy as np
import mrcfile
import os

particle_list_path = '/home/jblaser2/Research/STA/PyTom/particle_list.xml'
out_mrc = '/home/jblaser2/Research/STA/PyTom/starting_average.mrc'
out_npy = '/home/jblaser2/Research/STA/PyTom/starting_average.npy'
mask_npy = '/home/jblaser2/Research/STA/PyTom/cylindrical_mask.npy'

tree = ET.parse(particle_list_path)
filenames = [p.get('Filename') for p in tree.getroot().findall('Particle')]
print(f"Found {len(filenames)} particles")

accumulator = None
count = 0
for i, fname in enumerate(filenames):
    with mrcfile.open(fname, mode='r', permissive=True) as mrc:
        data = mrc.data.astype(np.float64)
    if accumulator is None:
        accumulator = data.copy()
    else:
        accumulator += data
    count += 1
    if (i + 1) % 100 == 0:
        print(f"  {i+1}/{len(filenames)}")

avg = (accumulator / count).astype(np.float32)
print(f"Average computed: shape={avg.shape}, min={avg.min():.4f}, max={avg.max():.4f}")

with mrcfile.new(out_mrc, overwrite=True) as mrc:
    mrc.set_data(avg)
    mrc.voxel_size = 13.328
print(f"Saved {out_mrc}")

np.save(out_npy, avg)
print(f"Saved {out_npy}")

# Convert cylindrical mask from .em to .npy
from pytom.lib.pytom_volume import read as em_read
from pytom.lib.pytom_numpy import vol2npy
mask_vol = em_read('/home/jblaser2/Research/STA/PyTom/cylindrical_mask.em')
mask_arr = vol2npy(mask_vol).copy().astype(np.float32)
np.save(mask_npy, mask_arr)
print(f"Saved {mask_npy}: shape={mask_arr.shape}, nonzero={np.count_nonzero(mask_arr)}")

# Quick sanity check: center vs edge RMS
cx, cy, cz = [s//2 for s in avg.shape]
center_region = avg[cx-8:cx+8, cy-8:cy+8, cz-8:cz+8]
edge_region = avg[:8, :8, :8]
print(f"\nSanity check — center RMS: {np.sqrt(np.mean(center_region**2)):.4f}, edge RMS: {np.sqrt(np.mean(edge_region**2)):.4f}")
print("(Higher center RMS suggests coherent averaging with structure in the center)")
