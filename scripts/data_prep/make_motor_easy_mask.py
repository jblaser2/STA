#!/usr/bin/env python3
"""
make_motor_easy_mask.py — regenerate the canonical motor_easy (FM_easy) solvent
mask used by all prior FM_easy package runs (RELION/PEET/Dynamo).

Spec (from STATUS.md + visualize_avg_with_mask.py):
  96^3 box, 13.329 A/px. Sphere radius 32 px (~427 A), centered at
  (x=48, y=38, z=48) — i.e. box center (48,48,48) shifted Y-10 to sit over the
  motor density. Soft cosine edge (default 4 px) to avoid Fourier-crop ringing,
  matching a RELION relion_mask_create solvent mask.

Output is a single-precision MRC, same box as the 96^3 subtomograms, so it can be
multiplied into each particle before downsampling (DISCA build_disca_input.py).
"""
import argparse
import numpy as np
import mrcfile


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--box", type=int, default=96)
    ap.add_argument("--radius", type=float, default=32.0, help="hard-1 radius in px")
    ap.add_argument("--center", type=float, nargs=3, default=[48, 38, 48],
                    help="sphere center (x y z) in voxels")
    ap.add_argument("--edge", type=float, default=4.0, help="soft cosine edge width in px")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    n = args.box
    # mrc axis order is (z, y, x); build coords accordingly
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float32)
    cx, cy, cz = args.center
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)

    mask = np.ones_like(r, dtype=np.float32)
    edge = args.edge
    R = args.radius
    # cosine falloff from R to R+edge
    falloff = (r - R) / edge
    in_edge = (r > R) & (r <= R + edge)
    mask[in_edge] = 0.5 * (1 + np.cos(np.pi * falloff[in_edge]))
    mask[r > R + edge] = 0.0

    with mrcfile.new(args.out, overwrite=True) as m:
        m.set_data(mask.astype(np.float32))
        m.voxel_size = 13.329

    frac = 100 * float(mask.sum()) / mask.size
    print(f"wrote {args.out}  box={n}^3  r={R}px center=({cx},{cy},{cz}) edge={edge}px")
    print(f"  mask mass = {mask.sum():.0f} voxel-equiv  ({frac:.1f}% of box)")


if __name__ == "__main__":
    main()
