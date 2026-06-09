#!/usr/bin/env python3
"""Build a cylindrical mask for the pili subtomograms.

The pilus is a rod-shaped particle, so a parametric cylinder is a cleaner focus
mask than a threshold of the (noisy, missing-wedge-dominated) consensus average.

Geometry was measured from the consensus map (see research.md "Mask"): the dense
pilus core is centred in the box and runs along the **Y axis**, with a compact
perpendicular cross-section. Defaults below come from that measurement; override
on the CLI.

OPUS-ET consumes the mask in the box frame and gates the reconstruction loss with
`(valid > 0)` (cryodrgn/models.py), i.e. it binarises whatever we pass -- so the
mask written here is binary. The cylinder RADIUS is the important knob: it also
sets the encoder crop window inside OPUS-ET,
    window_r  ~=  (2*radius + 4) / D
so a tighter radius focuses the encoder harder on the pilus (less surrounding
context). That is exactly what the --sweep mode lets you compare.

Usage
-----
  # write the default production mask (axis=y, radius=16) to mask.mrc
  python 03_make_mask.py

  # regenerate the consensus average too (needed after a clean slate)
  python 03_make_mask.py --consensus

  # generate a set of candidate masks + an inspection montage for ChimeraX
  python 03_make_mask.py --sweep
"""
import argparse
import glob
import os
import sys

import numpy as np
import mrcfile

PARTICLE_DIR = os.path.expanduser("~/src/particles")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONSENSUS_OUT = os.path.join(SCRIPT_DIR, "consensus.mrc")
MASK_OUT = os.path.join(SCRIPT_DIR, "mask.mrc")
SWEEP_DIR = os.path.join(SCRIPT_DIR, "mask_tests")

D = 80
APIX = 13.33

# Defaults from the consensus measurement (voxels).
DEF_AXIS = "y"        # filament long axis
DEF_RADIUS = 12       # perpendicular radius  (window_r ~= (2*12+4)/80 = 0.35)
DEF_HALFLEN = 34      # half-length along the filament axis (length = 68 of 80)

AXES = {"z": 0, "y": 1, "x": 2}  # MRC array order is (Z, Y, X)


def build_consensus():
    files = sorted(glob.glob(os.path.join(PARTICLE_DIR, "aligned_tom*.mrc")))
    if not files:
        sys.exit(f"ERROR: no MRC files in {PARTICLE_DIR}")
    print(f"Averaging {len(files)} volumes...")
    acc = None
    for i, f in enumerate(files):
        if i % 100 == 0:
            print(f"  {i}/{len(files)}")
        with mrcfile.open(f, permissive=True) as m:
            v = m.data.astype(np.float32)
        acc = v.copy() if acc is None else acc + v
    avg = acc / len(files)
    with mrcfile.new(CONSENSUS_OUT, overwrite=True) as m:
        m.set_data(avg)
        m.voxel_size = APIX
    print(f"Consensus map -> {CONSENSUS_OUT}")
    return avg


def cylinder(axis="y", radius=DEF_RADIUS, half_len=DEF_HALFLEN, d=D):
    """Binary (float32) cylinder centred in a d^3 box, long axis = `axis`."""
    c = (d - 1) / 2.0
    zz, yy, xx = np.mgrid[:d, :d, :d].astype(np.float32)
    coords = {"z": zz, "y": yy, "x": xx}
    long_ax = axis.lower()
    perp = [coords[a] for a in "zyx" if a != long_ax]
    r2 = (perp[0] - c) ** 2 + (perp[1] - c) ** 2
    along = np.abs(coords[long_ax] - c)
    mask = ((r2 <= radius ** 2) & (along <= half_len)).astype(np.float32)
    return mask


def sweep(consensus):
    os.makedirs(SWEEP_DIR, exist_ok=True)
    # 2-3 sizes around the measurement, plus a Z-axis comparison (research.md
    # historically called the data "z-aligned" -- the measurement says Y, so let
    # the user eyeball both).
    candidates = [
        ("y", 12, DEF_HALFLEN),
        ("y", 16, DEF_HALFLEN),
        ("y", 20, DEF_HALFLEN),
        ("z", 16, DEF_HALFLEN),
    ]
    masks = []
    for axis, r, hl in candidates:
        m = cylinder(axis, r, hl)
        wr = (2 * r + 4) / D
        name = f"cyl_{axis}_r{r}_l{2*hl}.mrc"
        path = os.path.join(SWEEP_DIR, name)
        with mrcfile.new(path, overwrite=True) as f:
            f.set_data(m)
            f.voxel_size = APIX
        print(f"  {name}: occ={100*m.mean():.1f}%  encoder window_r~={wr:.2f}  -> {path}")
        masks.append((f"{axis} r={r} l={2*hl}\nwindow_r~{wr:.2f}", m))

    # Inspection montage: each candidate overlaid on the consensus orthoslices.
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"(skipping montage, matplotlib unavailable: {e})")
        return
    mid = D // 2
    views = [("XZ (midY)", lambda v: v[:, mid, :]),
             ("YZ (midX)", lambda v: v[:, :, mid]),
             ("XY (midZ)", lambda v: v[mid, :, :])]
    nrow = len(masks) + 1
    fig, axes = plt.subplots(nrow, 3, figsize=(9, 3 * nrow), squeeze=False)
    for col, (vt, fn) in enumerate(views):
        img = fn(consensus)
        im = (img - img.mean()) / (img.std() + 1e-9)
        axes[0, col].imshow(np.clip(im, -3, 3), cmap="gray")
        axes[0, col].set_title(vt, fontsize=9)
        axes[0, col].set_xticks([]); axes[0, col].set_yticks([])
    axes[0, 0].set_ylabel("consensus", fontsize=9)
    for row, (lbl, m) in enumerate(masks, start=1):
        for col, (vt, fn) in enumerate(views):
            base = fn(consensus)
            im = (base - base.mean()) / (base.std() + 1e-9)
            ax = axes[row, col]
            ax.imshow(np.clip(im, -3, 3), cmap="gray")
            ax.contour(fn(m), levels=[0.5], colors="red", linewidths=1.0)
            ax.set_xticks([]); ax.set_yticks([])
        axes[row, 0].set_ylabel(lbl, fontsize=8)
    fig.suptitle("Candidate cylindrical masks (red) over consensus", fontsize=11)
    fig.tight_layout()
    out = os.path.join(SWEEP_DIR, "mask_candidates.png")
    fig.savefig(out, dpi=120, bbox_inches="tight")
    print(f"\nInspection montage -> {out}")
    print(f"Inspect the .mrc candidates in ChimeraX against {CONSENSUS_OUT}, then run")
    print("  python 03_make_mask.py --axis <a> --radius <r> --half-len <hl>")
    print("to write the chosen geometry to mask.mrc.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--consensus", action="store_true",
                    help="(re)compute the consensus average from the particles")
    ap.add_argument("--sweep", action="store_true",
                    help="generate candidate masks + inspection montage in mask_tests/")
    ap.add_argument("--axis", choices=list(AXES), default=DEF_AXIS)
    ap.add_argument("--radius", type=int, default=DEF_RADIUS)
    ap.add_argument("--half-len", dest="half_len", type=int, default=DEF_HALFLEN)
    args = ap.parse_args()

    if args.consensus or not os.path.exists(CONSENSUS_OUT):
        consensus = build_consensus()
    else:
        consensus = mrcfile.open(CONSENSUS_OUT, permissive=True).data.astype(np.float32)

    if args.sweep:
        sweep(consensus)
        return

    m = cylinder(args.axis, args.radius, args.half_len)
    with mrcfile.new(MASK_OUT, overwrite=True) as f:
        f.set_data(m)
        f.voxel_size = APIX
    wr = (2 * args.radius + 4) / D
    print(f"Cylinder mask (axis={args.axis}, r={args.radius}, half_len={args.half_len}): "
          f"{100 * m.mean():.1f}% occ, encoder window_r~={wr:.2f} -> {MASK_OUT}")


if __name__ == "__main__":
    main()
