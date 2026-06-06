"""
Visualize how a spherical mask crops the class average density maps.

Opens napari with 4 panels in a 2x2 grid:
  Col 1: Class 1 original  |  Col 2: Class 2 original
  Col 3: Class 1 masked    |  Col 4: Class 2 masked

Each class shows the original density + a translucent red overlay for the
region that falls OUTSIDE the mask, so you can see exactly what gets excluded.

Usage:
    DISPLAY=:0 QT_QPA_PLATFORM=xcb \\
        /home/jblaser2/conda-envs/napari-0.4-env/bin/python3 \\
        visualize_mask.py [--radius 7.2] [--compare 8.8]

    --radius   primary mask radius to inspect  (default: 7.2)
    --compare  optional second radius shown side by side  (default: 8.8)
"""

import argparse
import os
import numpy as np
import mrcfile
import napari

FINAL_DIR = '/home/jblaser2/Research/STA/dynamo/dynamo_final_results'
PIXEL_ANG = 13.328

def make_spherical_mask(box, radius, soft=True):
    """Spherical mask with optional soft edge (matches Dynamo's dynamo_ellipsoid behaviour)."""
    center = (box - 1) / 2.0
    coords = np.indices((box, box, box)).astype(np.float32)
    dist   = np.sqrt(np.sum((coords - center) ** 2, axis=0))
    if soft:
        # sigmoid falloff over ~2 voxels, similar to Dynamo smoothness=2
        hard_mask = 1.0 / (1.0 + np.exp(dist - radius))
        return (hard_mask > 0.5).astype(np.float32), hard_mask
    else:
        binary = (dist <= radius).astype(np.float32)
        return binary, binary

def load_vol(path):
    with mrcfile.open(path, permissive=True) as f:
        return f.data.copy().astype(np.float32)

def add_class_panels(viewer, vols, mask_binary, mask_soft, radius, col_offset=0):
    """Add one pair of columns (original + outside-mask highlight) for a given radius."""
    outside = (mask_binary == 0).astype(np.float32)   # 1 where excluded

    for ci, vol in enumerate(vols):
        col = col_offset + ci

        # Original density
        viewer.add_image(
            vol,
            name=f'r={radius}  class{ci+1}  original',
            colormap='gray',
            contrast_limits=[np.percentile(vol, 1), np.percentile(vol, 99)],
            scale=[PIXEL_ANG] * 3,
            translate=[0, 0, col * vol.shape[2] * PIXEL_ANG * 1.1],
        )

        # Outside-mask region highlighted in orange-red
        outside_density = vol * outside
        viewer.add_image(
            outside_density,
            name=f'r={radius}  class{ci+1}  excluded region',
            colormap='red',
            contrast_limits=[np.percentile(vol, 1), np.percentile(vol, 99)],
            opacity=0.6,
            scale=[PIXEL_ANG] * 3,
            translate=[0, 0, col * vol.shape[2] * PIXEL_ANG * 1.1],
            blending='additive',
        )

        # Mask boundary as a semi-transparent sphere outline
        viewer.add_image(
            (1.0 - mask_binary),           # 1 = just outside; creates a shell
            name=f'r={radius}  mask boundary',
            colormap='cyan',
            contrast_limits=[0, 1],
            opacity=0.15,
            scale=[PIXEL_ANG] * 3,
            translate=[0, 0, col * vol.shape[2] * PIXEL_ANG * 1.1],
            blending='additive',
            visible=False,                 # toggle on if wanted
        )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--radius',  type=float, default=7.2,
                        help='Primary mask radius to inspect (default: 7.2)')
    parser.add_argument('--compare', type=float, default=8.8,
                        help='Second mask radius for comparison (default: 8.8)')
    args = parser.parse_args()

    avg_dir = os.path.join(FINAL_DIR, 'class_averages')
    vols = [load_vol(os.path.join(avg_dir, f'class_{c:02d}.mrc')) for c in [1, 2]]
    box  = vols[0].shape[0]
    print(f'Loaded 2 class averages: box={box}, pixel={PIXEL_ANG} Å')

    radii = [args.radius]
    if args.compare and args.compare != args.radius:
        radii.append(args.compare)

    viewer = napari.Viewer(
        title=f'Mask comparison: r={args.radius} vs r={args.compare}',
        ndisplay=2
    )

    col_offset = 0
    for r in radii:
        mask_bin, mask_soft = make_spherical_mask(box, r, soft=True)
        print(f'r={r}: {int(mask_bin.sum())} active voxels '
              f'({100*mask_bin.mean():.1f}% of box)')
        add_class_panels(viewer, vols, mask_bin, mask_soft, r, col_offset)
        col_offset += 2

    # Set to XY plane at central slice
    viewer.dims.current_step = (box // 2, 0, 0)
    viewer.dims.axis_labels  = ('Z', 'Y', 'X')

    print(f'\nControls:')
    print(f'  - Gray layer  = full class average density')
    print(f'  - Red layer   = density EXCLUDED by the mask')
    print(f'  - Cyan layer  = mask boundary (hidden by default, toggle in layer list)')
    print(f'  - Scroll Z to move through slices')
    print(f'  - Toggle layers on/off in the layer list to compare')
    napari.run()

if __name__ == '__main__':
    main()
