#!/usr/bin/env python3
"""
make_initial_ref.py — build an initial 3D reference for RELION Class3D by averaging
the pre-aligned subtomograms in real space.

The T4P subtomograms are already aligned and centered (angles/origins = 0), so a
plain voxel-wise mean is a valid, unbiased starting reference. RELION Class3D then
low-pass filters it at startup (--ini_high) and splits it into K classes via the
stochastic E-step. Normalised to zero-mean/unit-std to match relion's expectations.

Run in an env with numpy + mrcfile (e.g. relion-5.0).
"""
import argparse
import os
import numpy as np
import mrcfile


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subtomo-dir", default="subtomos_mrc")
    ap.add_argument("--out", default="outputs/relion/initial_ref.mrc")
    ap.add_argument("--pixel-size", type=float, default=13.328)
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(args.subtomo_dir) if f.endswith(".mrc"))
    if not files:
        raise SystemExit(f"no .mrc in {args.subtomo_dir}")

    acc = None
    for i, fname in enumerate(files):
        with mrcfile.open(os.path.join(args.subtomo_dir, fname), permissive=True) as mrc:
            d = mrc.data.astype(np.float64)
        acc = d if acc is None else acc + d
        if (i + 1) % 100 == 0:
            print(f"  averaged {i+1}/{len(files)}")
    avg = (acc / len(files)).astype(np.float32)
    avg = (avg - avg.mean()) / (avg.std() + 1e-8)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with mrcfile.new(args.out, overwrite=True) as mrc:
        mrc.set_data(avg)
        mrc.voxel_size = args.pixel_size
    print(f"wrote {args.out}  shape={avg.shape}  from {len(files)} particles")


if __name__ == "__main__":
    main()
