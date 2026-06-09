#!/usr/bin/env python3
"""
Save slice and projection images for each PCA class average.
Usage: python plot_class_averages.py [path/to/sptcls_XX/]
       With no argument, finds the latest sptcls_XX/ automatically.

Output: sptcls_XX/class_averages.png
  Columns: XY slice | XZ slice | YZ slice | XY MIP | XZ MIP | YZ MIP
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from EMAN2 import EMData, EMNumPy


def load_volume(hdf_path):
    vol = EMData(hdf_path, 0)
    return EMNumPy.em2numpy(vol).copy()  # (nz, ny, nx)


def central_slices(arr):
    nz, ny, nx = arr.shape
    return arr[nz // 2, :, :], arr[:, ny // 2, :], arr[:, :, nx // 2]


def mip(arr):
    return arr.max(axis=0), arr.max(axis=1), arr.max(axis=2)


def contrast_stretch(img, lo=1, hi=99):
    vmin, vmax = np.percentile(img, [lo, hi])
    if vmax == vmin:
        return np.zeros_like(img)
    return np.clip((img - vmin) / (vmax - vmin), 0, 1)


if len(sys.argv) > 1:
    sptcls_dir = sys.argv[1].rstrip("/")
else:
    candidates = sorted(glob.glob("sptcls_*"))
    if not candidates:
        print("ERROR: No sptcls_XX/ directory found. Run e2spt_pcasplit.py first.")
        sys.exit(1)
    sptcls_dir = candidates[-1]

hdf_files = sorted(
    f for f in glob.glob(os.path.join(sptcls_dir, "threed_*.hdf"))
    if not ("_even" in f or "_odd" in f or "unmasked" in f)
)
if not hdf_files:
    print(f"ERROR: No threed_*.hdf files found in {sptcls_dir}/")
    sys.exit(1)

n_classes = len(hdf_files)
n_cols = 6  # 3 slices + 3 MIPs
print(f"Found {n_classes} class average(s) in {sptcls_dir}/")

fig, axes = plt.subplots(
    n_classes, n_cols,
    figsize=(3 * n_cols, 3 * n_classes),
    squeeze=False,
)

col_labels = [
    "XY slice", "XZ slice", "YZ slice",
    "XY MIP",   "XZ MIP",   "YZ MIP",
]

for row, hdf_path in enumerate(hdf_files):
    cls_name = os.path.splitext(os.path.basename(hdf_path))[0]
    # Count particles in matching lst file
    lst_path = os.path.join(sptcls_dir, cls_name.replace("threed_", "ptcls_cls") + ".lst")
    n_ptcls = 0
    if os.path.exists(lst_path):
        with open(lst_path) as f:
            lines = [l for l in f if not l.startswith("#") and l.strip()]
        n_ptcls = len(lines)
    row_label = f"{cls_name}\n(n={n_ptcls})"

    print(f"  Loading {hdf_path}  [{n_ptcls} particles]")
    arr = load_volume(hdf_path)
    images = central_slices(arr) + mip(arr)

    for col, img in enumerate(images):
        ax = axes[row][col]
        ax.imshow(contrast_stretch(img), cmap="gray", origin="lower", interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        if row == 0:
            ax.set_title(col_labels[col], fontsize=9)
        if col == 0:
            ax.set_ylabel(row_label, fontsize=9)

    # vertical divider between slices and MIPs
    if row == 0:
        axes[0][2].annotate(
            "", xy=(1.08, 0.5), xytext=(1.08, 0.5),
            xycoords="axes fraction", annotation_clip=False,
        )

fig.suptitle(f"Class averages — {sptcls_dir}   (left: central slices | right: max projections)",
             fontsize=10)
plt.tight_layout()

out_path = os.path.join(sptcls_dir, "class_averages.png")
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved: {out_path}")
