#!/usr/bin/env python3
"""
gen_perfect_confusion.py — generate a "perfect score" 3×3 confusion matrix
PNG for the motor_easy dataset reference (A=246, B=271, C=177).

Usage:
  python3 scripts/eval/gen_perfect_confusion.py \
      --out packages/figures/motor_easy/perfect_confusion.png
"""
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

GT_SIZES = {"A\n(full)": 246, "B\n(no C-ring)": 271, "C\n(C-ring only)": 177}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="packages/figures/motor_easy/perfect_confusion.png",
                    help="Output PNG path")
    args = ap.parse_args()

    labels = list(GT_SIZES.keys())
    counts = list(GT_SIZES.values())
    n = len(labels)

    cm = np.diag(counts).astype(float)
    cm_norm = cm / np.array(counts)[:, None]

    fig, ax = plt.subplots(figsize=(3.2, 3.0))
    im = ax.imshow(cm_norm, vmin=0, vmax=1, cmap="Blues")

    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicted cluster", fontsize=9)
    ax.set_ylabel("GT class", fontsize=9)
    ax.set_title("Perfect classification\nmotor_easy (ARI = 1.0)", fontsize=10,
                 fontweight="bold")

    for i in range(n):
        for j in range(n):
            raw = int(cm[i, j])
            pct = cm_norm[i, j]
            color = "white" if pct > 0.55 else "black"
            ax.text(j, i, f"{raw}\n({pct:.0%})", ha="center", va="center",
                    fontsize=9, color=color, fontweight="bold")

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")
    plt.tight_layout()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
