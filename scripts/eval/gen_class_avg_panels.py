#!/usr/bin/env python3
"""
gen_class_avg_panels.py — combine per-class average MRC or PNG files into a
single standardized N-panel figure for the packages/README.md figure gallery.

Usage (from MRC files):
  python3 scripts/eval/gen_class_avg_panels.py \
      --inputs class0.mrc class1.mrc class2.mrc \
      --labels "Class A" "Class B" "Class C" \
      --out packages/figures/motor_easy/relion_k3_class_avgs.png

Usage (combine existing PNG thumbnails):
  python3 scripts/eval/gen_class_avg_panels.py \
      --inputs packages/PyTom/figures_v2mask_k2/class_0_central_slice.png \
               packages/PyTom/figures_v2mask_k2/class_1_central_slice.png \
      --labels "Class 0" "Class 1" \
      --out packages/figures/T4P/pytom_k2_class_avgs.png

MRC files: XY central slice is extracted (index D//2 along Z).
PNG files: used as-is, cropped to square if needed.
Output: horizontal strip, each panel 160×160 px, gray colormap (for MRC),
        white label bottom-left, black border between panels.
"""
import argparse
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path


def load_slice(path: str) -> np.ndarray:
    """Return a 2D float32 array for a given MRC or PNG/JPG input."""
    p = Path(path)
    if p.suffix.lower() in (".mrc", ".mrcs", ".map"):
        try:
            import mrcfile
        except ImportError:
            sys.exit("mrcfile is required for MRC inputs: pip install mrcfile")
        with mrcfile.open(path, mode="r", permissive=True) as mrc:
            data = mrc.data.astype(np.float32)
        # handle 3D (Z, Y, X) and 2D
        if data.ndim == 3:
            z = data.shape[0] // 2
            return data[z]
        return data
    else:
        img = plt.imread(path)
        if img.ndim == 3:
            img = img.mean(axis=2)
        return img.astype(np.float32)


def normalize(arr: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
    if hi == lo:
        return np.zeros_like(arr)
    return np.clip((arr - lo) / (hi - lo), 0, 1)


def crop_square(arr: np.ndarray) -> np.ndarray:
    h, w = arr.shape
    s = min(h, w)
    y0 = (h - s) // 2
    x0 = (w - s) // 2
    return arr[y0:y0+s, x0:x0+s]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="MRC or PNG class average files, one per class")
    ap.add_argument("--labels", nargs="+", default=None,
                    help="Label text for each class panel (default: Class 0, 1, …)")
    ap.add_argument("--out", required=True, help="Output PNG path")
    ap.add_argument("--panel-px", type=int, default=160,
                    help="Side length of each square panel in pixels (default: 160)")
    ap.add_argument("--title", default=None, help="Optional figure title")
    args = ap.parse_args()

    n = len(args.inputs)
    labels = args.labels or [f"Class {i}" for i in range(n)]
    if len(labels) != n:
        sys.exit(f"Got {n} inputs but {len(labels)} labels")

    slices = []
    for path in args.inputs:
        if not os.path.exists(path):
            sys.exit(f"Input not found: {path}")
        slices.append(crop_square(normalize(load_slice(path))))

    px = args.panel_px
    pad = 4
    total_w = n * px + (n - 1) * pad
    total_h = px

    dpi = 100
    fig_w = total_w / dpi
    fig_h = (total_h + (30 if args.title else 0)) / dpi

    fig, axes = plt.subplots(1, n, figsize=(fig_w * n / n, fig_h),
                             gridspec_kw={"wspace": pad / px})
    if n == 1:
        axes = [axes]

    fig.patch.set_facecolor("black")
    if args.title:
        fig.suptitle(args.title, color="white", fontsize=9, y=0.98)

    for ax, sl, lbl in zip(axes, slices, labels):
        ax.imshow(sl, cmap="gray", vmin=0, vmax=1, interpolation="nearest",
                  aspect="equal")
        ax.text(0.04, 0.04, lbl, transform=ax.transAxes,
                color="white", fontsize=7, va="bottom", ha="left",
                bbox=dict(facecolor="black", alpha=0.5, pad=1, edgecolor="none"))
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor("white")
            spine.set_linewidth(0.5)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=dpi, bbox_inches="tight", facecolor="black", pad_inches=0.02)
    plt.close(fig)
    print(f"Saved: {out}  ({n} panels)")


if __name__ == "__main__":
    main()
