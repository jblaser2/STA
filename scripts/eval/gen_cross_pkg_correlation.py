#!/usr/bin/env python3
"""
gen_cross_pkg_correlation.py — cross-package particle-assignment correlation
figure for the T4P dataset.

For each pair of converged packages (Dynamo, PEET, PyTom, OPUS-TOMO), computes
a co-tabulation matrix (how many particles were assigned to each class
combination) and plots all 6 pairwise heatmaps in a 3×2 grid.  Each panel is
row-normalized (recall: fraction of Package A's class going to Package B's
class) and annotated with raw counts and the pairwise ARI.

Usage (run from repo root):
  python3 scripts/eval/gen_cross_pkg_correlation.py \
      --out packages/figures/T4P/cross_pkg_correlation.png

CSV paths are hardcoded to the canonical per-package assignment files; override
with --csvs if paths change (order must match --names).
"""
import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from itertools import combinations
from pathlib import Path
from sklearn.metrics import adjusted_rand_score

REPO = Path(__file__).resolve().parents[2]

DEFAULT_PKGS = [
    dict(
        name="Dynamo",
        csv=REPO / "packages/dynamo/dynamo_final_results/class_assignments.csv",
        id_col="particle",
        label_col="class",
        class_names=None,
    ),
    dict(
        name="PEET",
        csv=REPO / "packages/peet/results/peet_final_class_assignments_v2.csv",
        id_col="particle",
        label_col="class",
        class_names={1: "ring_complete", 2: "ring_altered", 3: "junk"},
    ),
    dict(
        name="PyTom",
        csv=REPO / "results/pytom_v2mask_k2.csv",
        id_col="file",
        label_col="pred_label",
        class_names=None,
    ),
    dict(
        name="OPUS-TOMO",
        csv=REPO / "results/opus_tomo_k2.csv",
        id_col="file",
        label_col="pred_label",
        class_names=None,
    ),
]


def load_pkg(cfg: dict) -> pd.Series:
    """Load a package CSV; return a Series indexed by particle basename."""
    df = pd.read_csv(cfg["csv"])
    df[cfg["id_col"]] = df[cfg["id_col"]].apply(lambda x: os.path.basename(str(x)))
    s = df.set_index(cfg["id_col"])[cfg["label_col"]]
    return s


def class_tick_labels(series: pd.Series, class_names: dict | None) -> list[str]:
    classes = sorted(series.unique())
    if class_names:
        return [class_names.get(c, str(c)) for c in classes]
    return [f"Cls {c}" for c in classes]


def plot_pair(ax, sA: pd.Series, sB: pd.Series,
              nameA: str, nameB: str,
              labelsA: list[str], labelsB: list[str]):
    shared = sA.index.intersection(sB.index)
    vA = sA.loc[shared].values
    vB = sB.loc[shared].values

    clsA = sorted(np.unique(vA))
    clsB = sorted(np.unique(vB))
    cm = np.zeros((len(clsA), len(clsB)), dtype=int)
    for a, b in zip(vA, vB):
        cm[clsA.index(a), clsB.index(b)] += 1

    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True).clip(min=1)

    ari = adjusted_rand_score(vA, vB)

    im = ax.imshow(cm_norm, vmin=0, vmax=1, cmap="Blues", aspect="auto")

    ax.set_xticks(range(len(clsB)))
    ax.set_xticklabels(labelsB, fontsize=7, rotation=30, ha="right")
    ax.set_yticks(range(len(clsA)))
    ax.set_yticklabels(labelsA, fontsize=7)
    ax.set_xlabel(nameB, fontsize=8)
    ax.set_ylabel(nameA, fontsize=8)
    ax.set_title(f"ARI = {ari:.3f}  (n={len(shared)})", fontsize=8)

    for i in range(len(clsA)):
        for j in range(len(clsB)):
            raw = cm[i, j]
            pct = cm_norm[i, j]
            color = "white" if pct > 0.55 else "black"
            ax.text(j, i, f"{raw}\n{pct:.0%}", ha="center", va="center",
                    fontsize=6, color=color)

    return im


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out",
                    default="packages/figures/T4P/cross_pkg_correlation.png",
                    help="Output PNG path")
    args = ap.parse_args()

    pkgs = []
    missing = []
    for cfg in DEFAULT_PKGS:
        if not cfg["csv"].exists():
            missing.append(f"  {cfg['name']}: {cfg['csv']}")
            continue
        s = load_pkg(cfg)
        pkgs.append(dict(name=cfg["name"], series=s,
                         labels=class_tick_labels(s, cfg["class_names"])))

    if missing:
        print("WARNING: missing CSVs (skipping):")
        for m in missing:
            print(m)

    if len(pkgs) < 2:
        raise SystemExit("Need at least 2 packages with available CSVs")

    pairs = list(combinations(range(len(pkgs)), 2))
    ncols = 2
    nrows = (len(pairs) + 1) // ncols

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(ncols * 4.2, nrows * 3.6))
    fig.suptitle("T4P — Cross-Package Particle Agreement",
                 fontsize=12, fontweight="bold")
    axes_flat = axes.flat if hasattr(axes, "flat") else [axes]

    im_ref = None
    for ax, (i, j) in zip(axes_flat, pairs):
        pA, pB = pkgs[i], pkgs[j]
        im = plot_pair(ax, pA["series"], pB["series"],
                       pA["name"], pB["name"],
                       pA["labels"], pB["labels"])
        im_ref = im

    # Hide unused axes
    for ax in list(axes_flat)[len(pairs):]:
        ax.set_visible(False)

    if im_ref is not None:
        fig.colorbar(im_ref, ax=list(axes.flat)[:len(pairs)],
                     fraction=0.02, pad=0.02, label="Recall (row-normalized)")

    plt.tight_layout()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
