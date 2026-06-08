"""
Generate XY orthoslice comparison PNG for HAC class averages.

Usage:
    python save_comparison_png.py [output_dir]

Saves: <output_dir>/class_comparison_<N>class.png
No display required — uses matplotlib Agg backend.
"""

import os
import sys
import glob
import shutil
import numpy as np
import mrcfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/jblaser2/Research/STA/dynamo/outputs/hac_classification'

avg_dir = os.path.join(OUTPUT_DIR, 'class_averages')
mrc_files = sorted(glob.glob(os.path.join(avg_dir, 'class_*.mrc')))

if not mrc_files:
    sys.exit(f'No class_*.mrc files found in {avg_dir}')

n = len(mrc_files)
print(f'Loading {n} class averages...')

vols = []
for path in mrc_files:
    tmp = path + '.tmp'
    with mrcfile.open(path, mode='r', permissive=True) as f:
        data = f.data.copy().astype(np.float32)
    with mrcfile.new(tmp, overwrite=True) as f:
        f.set_data(data)
        f.voxel_size = 1.0
    shutil.move(tmp, path)
    vols.append(data)

fig, axes = plt.subplots(1, n, figsize=(4 * n, 4))
if n == 1:
    axes = [axes]

for i, vol in enumerate(vols):
    z = vol.shape[0] // 2
    sl = vol[z, :, :]
    axes[i].imshow(sl, cmap='gray', origin='lower',
                   vmin=np.percentile(vol, 1), vmax=np.percentile(vol, 99))
    axes[i].set_title(f'Class {i+1}\n({vol.shape})', fontsize=10)
    axes[i].axis('off')

fig.suptitle(f'HAC Class Averages — XY central slice  (N={n})', fontsize=12)
fig.tight_layout()

out_png = os.path.join(OUTPUT_DIR, f'class_comparison_{n}class.png')
fig.savefig(out_png, dpi=150, bbox_inches='tight')
print(f'Saved: {out_png}')
