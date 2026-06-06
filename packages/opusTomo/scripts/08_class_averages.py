#!/usr/bin/env python3
"""
Compute 2D class average projections for each OPUS-ET class.

For each class, averages all raw subtomograms assigned to that class, then
produces three 2D views per class: XY projection (top-down cross-section),
XZ projection (side view), and the central Z slice.

Output is saved alongside the class volumes for the same run:
  opus_project/output/analyze.{EPOCH}/kmeans{K}/class_averages.png

Usage:
    python opus_project/08_class_averages.py
    python opus_project/08_class_averages.py --epoch 19 --k 2
"""

import argparse
import glob
import os
import sys

import mrcfile
import numpy as np
import matplotlib.pyplot as plt

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
PARTICLES_DIR = os.path.expanduser("~/src/particles")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--epoch", type=int, default=None,
                   help="Epoch to use (default: auto-detect latest)")
    p.add_argument("--k", type=int, default=2,
                   help="Number of clusters (default: 2)")
    return p.parse_args()


def detect_epoch():
    pkls = glob.glob(os.path.join(PROJ_DIR, "output", "z.*.pkl"))
    if not pkls:
        sys.exit("ERROR: No output/z.*.pkl found. Has training been run?")
    epochs = [int(os.path.basename(p).split(".")[1]) for p in pkls]
    return max(epochs)


def parse_star(star_path):
    """Extract _rlnImageName values from a RELION-style STAR file."""
    names = []
    in_loop = False
    col_idx = None
    col_count = 0
    with open(star_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line == "loop_":
                in_loop = True
                col_idx = None
                col_count = 0
                continue
            if in_loop and line.startswith("_"):
                if line.split()[0] == "_rlnImageName":
                    col_idx = col_count
                col_count += 1
                continue
            if in_loop and col_idx is not None:
                parts = line.split()
                if parts:
                    names.append(parts[col_idx])
    return names


def compute_average(filenames):
    """Accumulate a float64 mean volume over all particles in a class."""
    shape = (80, 80, 80)
    acc = np.zeros(shape, dtype=np.float64)
    n_loaded = 0
    missing = []
    for fname in filenames:
        path = os.path.join(PARTICLES_DIR, fname)
        if not os.path.exists(path):
            missing.append(fname)
            continue
        with mrcfile.open(path, mode='r') as mrc:
            acc += mrc.data.astype(np.float64)
        n_loaded += 1
    if missing:
        print(f"  WARNING: {len(missing)} of {len(filenames)} particles not found, skipping.")
    if n_loaded == 0:
        sys.exit("ERROR: No particles could be loaded for this class.")
    return acc / n_loaded, n_loaded


def normalise(img):
    """Z-score, clip to ±3σ, then rescale to [0, 1] for display."""
    mu, sigma = img.mean(), img.std()
    if sigma == 0:
        return np.zeros_like(img, dtype=np.float32)
    clipped = np.clip((img - mu) / sigma, -3.0, 3.0)
    return ((clipped + 3.0) / 6.0).astype(np.float32)


def main():
    args = parse_args()
    epoch = args.epoch if args.epoch is not None else detect_epoch()
    k = args.k

    analyze_dir = os.path.join(PROJ_DIR, "output", f"analyze.{epoch}", f"kmeans{k}")
    split_dir = os.path.join(PROJ_DIR, "split_star")
    out_path = os.path.join(analyze_dir, "class_averages.png")

    print(f"Epoch {epoch}  |  K={k}")
    print(f"Reading particles from: {PARTICLES_DIR}")
    print(f"Output: {out_path}")

    if not os.path.isdir(analyze_dir):
        sys.exit(f"ERROR: {analyze_dir} does not exist. Has the pipeline been run for this epoch/K?")

    col_titles = [
        "XY projection\n(top-down)",
        "XZ projection\n(side view)",
        "Central Z slice",
    ]

    fig, axes = plt.subplots(k, 3, figsize=(9, 3 * k), squeeze=False)

    for cls in range(k):
        star_path = os.path.join(split_dir, f"pre{cls}.star")
        if not os.path.exists(star_path):
            sys.exit(f"ERROR: {star_path} not found.")

        filenames = parse_star(star_path)
        print(f"\nClass {cls}: {len(filenames)} particles")

        avg, n_loaded = compute_average(filenames)
        print(f"  Averaged {n_loaded} volumes (shape {avg.shape})")

        # MRC axis order is (Z, Y, X)
        mid_z = avg.shape[0] // 2
        views = [
            np.sum(avg, axis=0),        # XY: collapse Z → (Y, X)
            np.sum(avg, axis=1),        # XZ: collapse Y → (Z, X)
            avg[mid_z, :, :],           # central Z slice → (Y, X)
        ]

        for col, view in enumerate(views):
            ax = axes[cls, col]
            ax.imshow(normalise(view), cmap="gray", interpolation="nearest")
            ax.set_xticks([])
            ax.set_yticks([])
            if cls == 0:
                ax.set_title(col_titles[col], fontsize=9)
            if col == 0:
                ax.set_ylabel(f"Class {cls}\n({n_loaded} ptcls)", fontsize=9)

    fig.suptitle(f"Class averages  |  epoch {epoch}  |  K={k}", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
