#!/usr/bin/env python3
"""
make_wedge_ctf.py — build the 3D CTF/missing-wedge models that RELION's classic
subtomogram path reads via the `rlnCtfImage` star field.

These pre-aligned T4P subtomograms have NO tilt series, so there is no per-particle
CTF. We instead supply ONE shared 3D model reused for all particles (they share the
same tomogram orientation). Two models are produced for the wedge-vs-uniform
comparison:

  wedge_ctf.mrc    single-axis missing-wedge mask (tilt axis = Y, ±TILT deg),
                   1.0 in the measured region, 0.0 inside the missing wedge.
  uniform_ctf.mrc  all-ones cube (no CTF/wedge weighting; a controlled baseline).

Format requirement (see RELION src/ml_optimiser.cpp:get3DCTFAndMulti, ~L10557):
a full cube with XSIZE==YSIZE==ZSIZE (here 80^3), CENTERED (DC at box/2), real,
values in [0,1]. A plain cube (ZSIZE==YSIZE, not *2) bypasses the subtomo-
multiplicity branch entirely, which is what we want with --skip_subtomo_multi.

Run in an env with numpy + mrcfile (e.g. relion-5.0 or eman2).
"""
import argparse
import numpy as np
import mrcfile


def build_wedge(box, tilt_deg, pixel_size):
    """Centered single-axis (Y) missing-wedge mask.

    Tilt about the Y axis over [-tilt, +tilt]. A Fourier voxel in the kx-kz plane
    is *measured* if its angle from the kx-axis is <= tilt_deg; otherwise it lies
    in the missing wedge (a 2*(90-tilt) cone around kz). The Y axis (tilt axis) is
    unrestricted.
    """
    c = box // 2
    ax = np.arange(box) - c                      # centered coordinate axis
    kz, ky, kx = np.meshgrid(ax, ax, ax, indexing="ij")
    # angle from the kx axis within the kx-kz plane, in [0, 90] degrees
    phi = np.degrees(np.arctan2(np.abs(kz), np.abs(kx)))
    mask = (phi <= tilt_deg).astype(np.float32)
    mask[c, c, c] = 1.0                          # keep DC term
    return mask


def write_mrc(path, data, pixel_size):
    with mrcfile.new(path, overwrite=True) as mrc:
        mrc.set_data(data.astype(np.float32))
        mrc.voxel_size = pixel_size
    print(f"wrote {path}  shape={data.shape}  measured_frac={data.mean():.3f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--box", type=int, default=80)
    ap.add_argument("--tilt", type=float, default=60.0,
                    help="half tilt range in degrees (default 60 -> +/-60)")
    ap.add_argument("--pixel-size", type=float, default=13.328)
    ap.add_argument("--outdir", default="outputs/relion/ctf")
    args = ap.parse_args()

    import os
    os.makedirs(args.outdir, exist_ok=True)

    wedge = build_wedge(args.box, args.tilt, args.pixel_size)
    write_mrc(os.path.join(args.outdir, "wedge_ctf.mrc"), wedge, args.pixel_size)

    uniform = np.ones((args.box, args.box, args.box), dtype=np.float32)
    write_mrc(os.path.join(args.outdir, "uniform_ctf.mrc"), uniform, args.pixel_size)


if __name__ == "__main__":
    main()
