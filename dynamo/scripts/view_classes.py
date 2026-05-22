"""
Open HAC class average MRC files side by side in napari (XY plane).

Usage:
    python view_classes.py [output_dir]

output_dir defaults to /home/jblaser2/Research/STA/dynamo/outputs/hac_classification
"""

import os
import sys
import glob
import shutil
import numpy as np
import mrcfile
import napari

OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/jblaser2/Research/STA/dynamo/outputs/hac_classification'

avg_dir = os.path.join(OUTPUT_DIR, 'class_averages')
mrc_files = sorted(glob.glob(os.path.join(avg_dir, 'class_*.mrc')))

if not mrc_files:
    sys.exit(f'No class_*.mrc files found in {avg_dir}')

print(f'Loading {len(mrc_files)} class averages from {avg_dir}')

# Load volumes, fixing incomplete MRC headers written by dynamo_write
vols = []
for path in mrc_files:
    tmp = path + '.tmp'
    with mrcfile.open(path, mode='r', permissive=True) as f:
        data = f.data.copy().astype(np.float32)
    with mrcfile.new(tmp, overwrite=True) as f:
        f.set_data(data)
        f.voxel_size = 1.0
    shutil.move(tmp, path)
    vols.append((os.path.basename(path).replace('.mrc', ''), data))
    print(f'  {os.path.basename(path)}: shape={data.shape}')

viewer = napari.Viewer(title=f'HAC Class Averages — {len(vols)} classes', ndisplay=2)

colormaps = ['gray', 'cyan', 'magenta', 'yellow']
for i, (name, vol) in enumerate(vols):
    viewer.add_image(
        vol,
        name=name,
        colormap=colormaps[i % len(colormaps)],
        contrast_limits=[np.percentile(vol, 1), np.percentile(vol, 99)],
        visible=True,
    )

# Grid mode: show all layers side by side
viewer.grid.enabled = True
viewer.grid.shape = (1, len(vols))   # single row

# Set to XY plane, central Z slice
mid_z = vols[0][1].shape[0] // 2
viewer.dims.current_step = (mid_z, 0, 0)

print('Viewer open. Close the window to exit.')
napari.run()
