#!/usr/bin/env python3
"""
generate_cylindrical_mask.py

Generates a binary cylindrical mask for PyTom subtomogram classification.

Cylinder geometry (T4P pilus alignment):
  - Long axis  : Y direction  (pilus filament axis)
  - Cross-section: XZ plane   (circular end-on view)
  - Defaults   : height=17.6 voxels, radius=7.2 voxels, box=80 voxels
  - Center     : (box//2, box//2, box//2) = (40, 40, 40)

Output:
  cylindrical_mask.em   -- PyTom native format (required for older classifiers)
  cylindrical_mask.mrc  -- MRC format (compatible with newer PyTom code)

Both formats are accepted by auto_focus_classify.py via the -m and -c flags.

Usage:
    python generate_cylindrical_mask.py
    python generate_cylindrical_mask.py --height 17.6 --radius 7.2 --box 80
"""

import numpy as np
import struct
import argparse
import os


def create_cylindrical_mask(box_size: int, height: float, radius: float) -> np.ndarray:
    """
    Create a binary cylindrical mask.

    Returns float32 array of shape (nz, ny, nx) = (box, box, box).
    The cylinder's long axis runs along Y (axis 1).
    The circular cross-section lives in the XZ plane (axes 2 and 0).

    A voxel at index [iz, iy, ix] is inside the cylinder when:
        (ix - cx)^2 + (iz - cz)^2 <= radius^2   (XZ circle)
        AND |iy - cy| <= height / 2               (Y extent)
    """
    cx = cy = cz = box_size // 2  # center at (40, 40, 40) for an 80-voxel box

    # Build coordinate grids: result[iz, iy, ix] = axis value at that index
    idx = np.arange(box_size)
    zz, yy, xx = np.meshgrid(idx, idx, idx, indexing='ij')

    in_circle = (xx - cx) ** 2 + (zz - cz) ** 2 <= radius ** 2
    in_height = np.abs(yy - cy) <= height / 2.0

    mask = np.where(in_circle & in_height, 1.0, 0.0).astype(np.float32)
    return mask


def write_em(mask: np.ndarray, filename: str) -> None:
    """
    Write a float32 volume in EM (TOM/PyTom) format.

    EM format header is 512 bytes; data follows immediately in
    x-fastest order, which matches C-order for a (nz, ny, nx) array
    (last axis = x varies fastest).
    """
    nz, ny, nx = mask.shape
    header = bytearray(512)
    header[0] = 6                              # Machine type: Linux little-endian
    struct.pack_into('<i', header, 4,  nx)     # columns (x)
    struct.pack_into('<i', header, 8,  ny)     # rows    (y)
    struct.pack_into('<i', header, 12, nz)     # sections(z)
    struct.pack_into('<i', header, 16, 5)      # data type: float32

    with open(filename, 'wb') as f:
        f.write(bytes(header))
        # C-order flatten: last axis (x) varies fastest = EM convention
        f.write(mask.astype(np.float32).flatten().tobytes())


def write_mrc(mask: np.ndarray, filename: str, voxel_size: float) -> None:
    """Write a float32 volume in MRC format using mrcfile."""
    try:
        import mrcfile
    except ImportError:
        print("  WARNING: mrcfile not installed -- skipping .mrc output.")
        return

    with mrcfile.new(filename, overwrite=True) as mrc:
        mrc.set_data(mask.astype(np.float32))
        mrc.voxel_size = voxel_size


def main():
    parser = argparse.ArgumentParser(
        description='Generate a cylindrical mask for PyTom classification.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument('--box', type=int, default=80,
                        help='Box size in voxels (default: 80)')
    parser.add_argument('--height', type=float, default=17.6,
                        help='Total cylinder height along Y in voxels (default: 17.6)')
    parser.add_argument('--radius', type=float, default=7.2,
                        help='Cylinder radius in XZ plane in voxels (default: 7.2)')
    parser.add_argument('--voxel_size', type=float, default=13.328,
                        help='Voxel size in Angstroms for MRC header (default: 13.328)')
    parser.add_argument('--output', type=str, default='cylindrical_mask',
                        help='Output filename stem without extension (default: cylindrical_mask)')
    args = parser.parse_args()

    vox = args.voxel_size
    print("Cylindrical mask parameters:")
    print(f"  Box       : {args.box}^3 voxels")
    print(f"  Height (Y): {args.height} voxels  ({args.height * vox:.1f} A)")
    print(f"  Radius(XZ): {args.radius} voxels  ({args.radius * vox:.1f} A)")
    print(f"  Center    : ({args.box//2}, {args.box//2}, {args.box//2})")

    mask = create_cylindrical_mask(args.box, args.height, args.radius)

    n_voxels = int(mask.sum())
    theoretical = np.pi * args.radius ** 2 * args.height
    print(f"  Voxels in mask : {n_voxels}  (theoretical ~{theoretical:.0f})")

    em_path  = args.output + '.em'
    mrc_path = args.output + '.mrc'

    write_em(mask, em_path)
    print(f"  Saved (EM) : {em_path}")

    write_mrc(mask, mrc_path, args.voxel_size)
    print(f"  Saved (MRC): {mrc_path}")

    print("Done.")


if __name__ == '__main__':
    main()
