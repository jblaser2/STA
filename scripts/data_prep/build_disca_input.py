#!/usr/bin/env python3
"""
build_disca_input.py — package the 672 pre-aligned T4P subtomograms into the
AITom/DISCA input format.

DISCA (torch_disca.py) loads a pickle holding the AITom subtomogram container:

    {'vs': { <key>: {'v': <3D numpy array>, 'm': None, 'id': <key>}, ... }}

and stacks the 'v' volumes into a tensor of shape (n, 1, s, s, s). DISCA's YOPO
feature model is trained at the paper's box size of 32^3, so we downsample our
80^3 / 13.328 A-px volumes to 32^3 by Fourier cropping (anti-aliased, no spatial
interpolation artefacts) — new sampling ~33.3 A/px, which is the coarse regime
DISCA is designed to pattern-mine in. Each subtomogram is normalised to
zero-mean / unit-std (DISCA expects standardised inputs).

The particles are already aligned & centered (angles/origins = 0), consistent
with how RELION/PyTom/Protomo were run, so DISCA classifies the same pre-aligned
set the other packages did.

Run in an env with numpy + scipy + mrcfile (e.g. the `disca` env).
Output pickle lives OUTSIDE the repo (local-only, large): ~/Research/disca_work/.
"""
import argparse
import os
import pickle
import numpy as np
import mrcfile


def fourier_crop(vol, out_size):
    """Downsample a cubic volume to out_size^3 by cropping the centered FFT."""
    n = vol.shape[0]
    if out_size == n:
        return vol.astype(np.float32)
    if out_size > n:
        raise ValueError("fourier_crop only downsamples")
    F = np.fft.fftshift(np.fft.fftn(vol))
    c = n // 2
    h = out_size // 2
    # centered crop of the low-frequency block
    Fc = F[c - h:c - h + out_size, c - h:c - h + out_size, c - h:c - h + out_size]
    out = np.fft.ifftn(np.fft.ifftshift(Fc)).real
    # preserve amplitude scale after cropping
    out *= (out_size ** 3) / (n ** 3)
    return out.astype(np.float32)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subtomo-dir", default="subtomos_mrc")
    ap.add_argument("--out", default=os.path.expanduser("~/Research/disca_work/disca_input_672.pickle"))
    ap.add_argument("--box", type=int, default=32, help="DISCA box size (default 32)")
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(args.subtomo_dir) if f.endswith(".mrc"))
    if not files:
        raise SystemExit(f"no .mrc in {args.subtomo_dir}")

    vs = {}
    for i, fname in enumerate(files):
        key = os.path.splitext(fname)[0]            # e.g. aligned_tom100_P0001
        with mrcfile.open(os.path.join(args.subtomo_dir, fname), permissive=True) as mrc:
            d = mrc.data.astype(np.float32)
        v = fourier_crop(d, args.box)
        v = (v - v.mean()) / (v.std() + 1e-8)        # per-subtomo standardisation
        vs[key] = {"v": v, "m": None, "id": key}
        if (i + 1) % 100 == 0:
            print(f"  packed {i+1}/{len(files)}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as f:
        pickle.dump({"vs": vs}, f, protocol=2)
    shp = next(iter(vs.values()))["v"].shape
    print(f"wrote {args.out}  n={len(vs)}  box={shp}")


if __name__ == "__main__":
    main()
