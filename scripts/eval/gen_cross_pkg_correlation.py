#!/usr/bin/env python3
"""
gen_cross_pkg_correlation.py — cross-package particle-assignment correlation
figure for the T4P dataset.

For each pair of the four converging packages (Dynamo, PEET, PyTom, ProTomo),
computes a co-tabulation matrix (how many particles were assigned to each class
combination) and plots all 6 pairwise heatmaps in a 3×2 grid, row-normalized
(recall) with ARI annotated.  A 7th panel shows a per-particle consensus
score histogram: how many packages agree on each particle's cluster after
label alignment to Dynamo as the reference.

Junk handling: packages with a junk class (PEET class 3, ProTomo class 2) have
those particles excluded; pairwise comparisons use the intersection of
non-junk particles between each pair.

Usage (run from repo root):
  python3 scripts/eval/gen_cross_pkg_correlation.py \
      --out packages/figures/T4P/cross_pkg_correlation.png
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
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score

REPO = Path(__file__).resolve().parents[2]

DEFAULT_PKGS = [
    dict(
        name="Dynamo",
        csv=REPO / "packages/dynamo/T4P/results/dynamo_final_results/class_assignments.csv",
        id_col="particle",
        label_col="class",
        sep=",",
        junk_classes=set(),
        class_names=None,
    ),
    dict(
        name="PEET",
        csv=REPO / "packages/peet/T4P/results/peet_final_class_assignments_v2.csv",
        id_col="particle",
        label_col="class",
        sep=",",
        junk_classes={3},
        class_names={1: "ring_complete", 2: "ring_altered"},
    ),
    dict(
        name="PyTom",
        csv=REPO / "results/pytom_v2mask_k2.csv",
        id_col="file",
        label_col="pred_label",
        sep=",",
        junk_classes=set(),
        class_names=None,
    ),
    dict(
        name="ProTomo",
        csv=REPO / "results/protomo_T4P_k2.csv",
        id_col="file",
        label_col="pred_label",
        sep=",",
        junk_classes=set(),   # junk already excluded at extraction time
        class_names=None,
    ),
]


def load_pkg(cfg: dict) -> pd.Series:
    """Load a package CSV; return a Series indexed by particle basename, junk excluded."""
    df = pd.read_csv(cfg["csv"], sep=cfg.get("sep", ","))
    df[cfg["id_col"]] = df[cfg["id_col"]].apply(lambda x: os.path.basename(str(x)))
    s = df.set_index(cfg["id_col"])[cfg["label_col"]]
    if cfg["junk_classes"]:
        s = s[~s.isin(cfg["junk_classes"])]
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


def align_to_ref(ref: pd.Series, other: pd.Series) -> pd.Series:
    """Permute `other`'s labels to maximally agree with `ref` (Hungarian, k=2 or k=3)."""
    shared = ref.index.intersection(other.index)
    vR = ref.loc[shared].values
    vO = other.loc[shared].values

    clsR = sorted(np.unique(vR))
    clsO = sorted(np.unique(vO))
    cm = np.zeros((len(clsR), len(clsO)), dtype=int)
    for r, o in zip(vR, vO):
        cm[clsR.index(r), clsO.index(o)] += 1

    row_ind, col_ind = linear_sum_assignment(-cm)
    mapping = {clsO[col_ind[i]]: clsR[row_ind[i]] for i in range(len(row_ind))}
    return other.map(mapping)


def plot_consensus(ax, series_list: list[pd.Series], names: list[str]):
    """Histogram of per-particle consensus score (how many packages agree after alignment)."""
    ref = series_list[0]
    aligned = [ref] + [align_to_ref(ref, s) for s in series_list[1:]]

    # Intersection of all packages
    common = aligned[0].index
    for s in aligned[1:]:
        common = common.intersection(s.index)

    if len(common) == 0:
        ax.text(0.5, 0.5, "No common particles", transform=ax.transAxes,
                ha="center", va="center")
        return

    # For each particle, count how many packages give the same label as ref
    matrix = pd.DataFrame({names[i]: aligned[i].loc[common] for i in range(len(aligned))})
    ref_col = names[0]
    scores = (matrix.eq(matrix[ref_col], axis=0)).sum(axis=1)

    n = len(common)
    bins = range(1, len(series_list) + 2)  # 1 to n_pkgs (ref always agrees with itself)
    counts = [int((scores == v).sum()) for v in range(1, len(series_list) + 1)]
    bars = ax.bar(range(1, len(series_list) + 1), counts,
                  color=["#d0e8f7", "#6baed6", "#2171b5", "#084594"][:len(counts)],
                  edgecolor="white", linewidth=0.5)

    for bar, cnt in zip(bars, counts):
        if cnt > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3,
                    str(cnt), ha="center", va="bottom", fontsize=7)

    ax.set_xticks(range(1, len(series_list) + 1))
    ax.set_xticklabels([f"{v}/{len(series_list)}" for v in range(1, len(series_list) + 1)],
                       fontsize=7)
    ax.set_xlabel("Packages agreeing with Dynamo", fontsize=8)
    ax.set_ylabel("# particles", fontsize=8)
    high_consensus = int((scores == len(series_list)).sum())
    ax.set_title(
        f"Consensus score  (n={n}, {high_consensus} fully aligned)",
        fontsize=8
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def print_ari_summary(pkgs: list[dict]):
    print("\nPairwise ARI summary:")
    pairs = list(combinations(range(len(pkgs)), 2))
    for i, j in pairs:
        sA = pkgs[i]["series"]
        sB = pkgs[j]["series"]
        shared = sA.index.intersection(sB.index)
        vA = sA.loc[shared].values
        vB = sB.loc[shared].values
        ari = adjusted_rand_score(vA, vB)
        print(f"  {pkgs[i]['name']:10s} vs {pkgs[j]['name']:10s}: ARI={ari:.3f}  n={len(shared)}")


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

    print_ari_summary(pkgs)

    pairs = list(combinations(range(len(pkgs)), 2))
    n_panels = len(pairs) + 1  # +1 for consensus histogram
    ncols = 2
    nrows = (n_panels + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(ncols * 4.2, nrows * 3.6 + 0.5))
    fig.suptitle("T4P — Cross-Package Particle Agreement (4 converging packages)",
                 fontsize=12, fontweight="bold", y=0.998)
    axes_flat = list(axes.flat) if hasattr(axes, "flat") else [axes]

    im_ref = None
    for ax, (i, j) in zip(axes_flat, pairs):
        pA, pB = pkgs[i], pkgs[j]
        im = plot_pair(ax, pA["series"], pB["series"],
                       pA["name"], pB["name"],
                       pA["labels"], pB["labels"])
        im_ref = im

    # Consensus histogram in next panel
    consensus_ax = axes_flat[len(pairs)]
    plot_consensus(consensus_ax,
                   [p["series"] for p in pkgs],
                   [p["name"] for p in pkgs])

    # Hide unused axes
    for ax in axes_flat[n_panels:]:
        ax.set_visible(False)

    if im_ref is not None:
        heatmap_axes = axes_flat[:len(pairs)]
        fig.colorbar(im_ref, ax=heatmap_axes,
                     fraction=0.015, pad=0.02, label="Recall (row-normalized)")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
