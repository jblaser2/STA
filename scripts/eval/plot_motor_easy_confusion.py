#!/usr/bin/env python3
"""Plot confusion matrices for all motor_easy packages (k=3 unless noted)."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import linear_sum_assignment
from pathlib import Path

GT_CSV = Path("~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv").expanduser()
OUT_PNG = Path("outputs/relion_motor_easy/motor_easy_confusion_matrices.png").expanduser()

GT_NAMES = {1: "A (full)", 2: "B (no C-ring)", 3: "C (C-ring only)"}

RUNS = [
    dict(
        label="RELION\n(GT-seeded, iter1)\nARI=0.475",
        pred_csv=Path("/tmp/relion_v4_iter001.csv"),
        k=3,
    ),
    dict(
        label="PEET\n(pc1, k=2 best)\nARI=0.116",
        pred_csv=Path("~/Research/STA/outputs/peet_motor_easy/predictions_k2_pc1_5.csv").expanduser(),
        k=2,
    ),
    dict(
        label="Dynamo dpkpca\n(nc=17 best)\nARI=0.200",
        pred_csv=Path("~/Research/STA/packages/dynamo/dynamo_outputs/motor_easy_pca/predictions_k3_best.csv").expanduser(),
        k=3,
    ),
    dict(
        label="Dynamo HAC\n(Ward CC)\nARI≈0",
        pred_csv=Path("~/Research/STA/packages/dynamo/dynamo_outputs/motor_easy_hac/predictions_k3.csv").expanduser(),
        k=3,
    ),
]

GT_CLASS_MAP = {"A": 1, "B": 2, "C": 3}

def load_merged(pred_csv, gt_csv):
    pred = pd.read_csv(pred_csv)
    gt   = pd.read_csv(gt_csv)
    pred["file"] = pred["file"].apply(lambda x: Path(x).name)
    gt["file"]   = gt["file"].apply(lambda x: Path(x).name)
    merged = pd.merge(pred, gt, on="file")
    true_int = merged["label"].map(GT_CLASS_MAP).values
    return merged["pred_label"].values, true_int

def optimal_confusion(pred, true, n_pred, n_true=3):
    """Build confusion matrix with columns permuted to maximize diagonal sum."""
    cm = np.zeros((n_true, n_pred), dtype=int)
    for p, t in zip(pred, true):
        cm[t - 1, p - 1] += 1
    if n_pred == n_true:
        row_ind, col_ind = linear_sum_assignment(-cm)
        cm = cm[:, col_ind]
        col_labels = [f"Cluster {i+1}" for i in col_ind]
    else:
        col_labels = [f"Cluster {i+1}" for i in range(n_pred)]
    return cm, col_labels

fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
fig.suptitle("motor_easy — Confusion Matrices by Package", fontsize=14, fontweight="bold", y=1.01)

row_labels = ["A (full)\nn=246", "B (no C-ring)\nn=271", "C (C-ring only)\nn=177"]

for ax, run in zip(axes, RUNS):
    pred, true = load_merged(run["pred_csv"], GT_CSV)
    k = run["k"]
    cm, col_labels = optimal_confusion(pred, true, n_pred=k, n_true=3)

    # normalize rows → recall per GT class
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    im = ax.imshow(cm_norm, vmin=0, vmax=1, cmap="Blues")

    ax.set_xticks(range(k))
    ax.set_xticklabels(col_labels, fontsize=9)
    ax.set_yticks(range(3))
    ax.set_yticklabels(row_labels, fontsize=9)
    ax.set_xlabel("Predicted cluster", fontsize=9)
    ax.set_ylabel("GT class", fontsize=9)
    ax.set_title(run["label"], fontsize=10)

    for i in range(3):
        for j in range(k):
            raw = cm[i, j]
            pct = cm_norm[i, j]
            color = "white" if pct > 0.55 else "black"
            ax.text(j, i, f"{raw}\n({pct:.0%})", ha="center", va="center",
                    fontsize=8, color=color)

    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")

plt.tight_layout()
OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT_PNG}")
