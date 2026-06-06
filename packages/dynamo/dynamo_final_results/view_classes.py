"""
Open Dynamo final class averages side by side in napari (XY plane).

Requirements:
    conda env: /home/jblaser2/conda-envs/napari-0.4-env  (napari 0.4.19, vispy 0.14.3)

Usage:
    DISPLAY=:0 QT_QPA_PLATFORM=xcb \
        /home/jblaser2/conda-envs/napari-0.4-env/bin/python3 view_classes.py
"""

import os, sys
import numpy as np
import mrcfile
import napari

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
AVG_DIR     = os.path.join(SCRIPT_DIR, 'class_averages')
PIXEL_ANG   = 13.328

class_files = sorted([
    f for f in os.listdir(AVG_DIR) if f.endswith('.mrc')
])
if not class_files:
    sys.exit(f'No .mrc files found in {AVG_DIR}')

print(f'Loading {len(class_files)} class averages...')
vols = []
for fname in class_files:
    path = os.path.join(AVG_DIR, fname)
    with mrcfile.open(path, permissive=True) as f:
        vol = f.data.copy().astype(np.float32)
    vols.append((fname.replace('.mrc', ''), vol))
    print(f'  {fname}: {vol.shape}  ({PIXEL_ANG} Å/vox)')

viewer = napari.Viewer(title='Dynamo Class Averages (r=7.2)', ndisplay=2)

colormaps = ['gray', 'cyan']
for i, (name, vol) in enumerate(vols):
    viewer.add_image(
        vol, name=name,
        colormap=colormaps[i % len(colormaps)],
        contrast_limits=[np.percentile(vol, 1), np.percentile(vol, 99)],
        scale=[PIXEL_ANG] * 3,
    )

viewer.grid.enabled = True
viewer.grid.shape   = (1, len(vols))
viewer.dims.current_step = (vols[0][1].shape[0] // 2, 0, 0)

print('Viewer open. Close the window to exit.')
napari.run()
