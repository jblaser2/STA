#!/usr/bin/env python3
"""Generate FM_hard figures for packages/README.md.

Produces:
  packages/figures/FM_hard/perfect_confusion.png
  packages/figures/FM_hard/<pkg>_class_avgs.png   (per-package, 3-panel)
  outputs/FM_hard/<pkg>/confusion_<pkg>_fm_hard_k3.png

Run from STA repo root with the eman2 (or relion-5.0) conda env, e.g.:
  conda run -n eman2 python3 scripts/eval/gen_fm_hard_figures.py
"""
import os
import csv
import numpy as np
import mrcfile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter
from sklearn.metrics import adjusted_rand_score, confusion_matrix
from scipy.optimize import linear_sum_assignment

STA   = "/home/jblaser2/Research/STA"
STDIR = "/home/jblaser2/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full"
MAPS  = "/home/jblaser2/Research/synthetic_sta/motor_hard/maps"
FIGDIR = os.path.join(STA, "packages/figures/FM_hard")
os.makedirs(FIGDIR, exist_ok=True)

GT_CLASSES = ["base", "basal_body", "mature"]   # inside-out order
GT_COUNTS  = {"base": 271, "basal_body": 271, "mature": 271}
CLASS_LABELS = {"base": "base\n(C+MS ring)",
                "basal_body": "basal_body\n(+P-ring)",
                "mature": "mature\n(full motor)"}

# ------------------------------------------------------------------ helpers --

def load(path):
    with mrcfile.open(path, permissive=True) as f:
        return f.data.astype(np.float32)

def cslice(vol):
    """Central Z slice (axis 0)."""
    return vol[vol.shape[0] // 2]

def norm(img):
    lo, hi = np.percentile(img, 2), np.percentile(img, 98)
    if hi == lo:
        return np.zeros_like(img)
    return np.clip((img - lo) / (hi - lo), 0, 1)

def show(ax, img, title, fontsize=10):
    ax.imshow(norm(img), cmap="gray", vmin=0, vmax=1)
    ax.set_title(title, fontsize=fontsize)
    ax.axis("off")

# cache subtomo slices — loaded once, reused across packages
_cache = {}
def get_slice(fn):
    if fn not in _cache:
        p = os.path.join(STDIR, fn)
        _cache[fn] = cslice(load(p))
    return _cache[fn]

# GT map
gt_map = {r["file"]: r["label"]
          for r in csv.DictReader(open(os.path.join(STDIR, "labels.csv")))}

def load_pred(path):
    return {r["file"]: r["pred_label"]
            for r in csv.DictReader(open(path))}

def hungarian_accuracy(gt_list, pr_list):
    gt_u = sorted(set(gt_list))
    pr_u = sorted(set(pr_list))
    gt_idx = np.array([gt_u.index(g) for g in gt_list])
    pr_idx = np.array([pr_u.index(p) for p in pr_list])
    cm = confusion_matrix(gt_idx, pr_idx, labels=range(len(gt_u)))
    n = max(len(gt_u), len(pr_u))
    pad = np.zeros((n, n), dtype=float)
    pad[:cm.shape[0], :cm.shape[1]] = cm
    ri, ci = linear_sum_assignment(-pad)
    acc = pad[ri, ci].sum() / len(gt_list)
    return acc, cm, gt_u, pr_u

# -------------------------------------------------------- perfect confusion --

def gen_perfect_confusion():
    n = len(GT_CLASSES)
    counts = [GT_COUNTS[c] for c in GT_CLASSES]
    cm = np.diag(counts).astype(float)
    cm_norm = cm / np.array(counts)[:, None]

    tick_labels = [CLASS_LABELS[c] for c in GT_CLASSES]
    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    im = ax.imshow(cm_norm, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(n)); ax.set_xticklabels(tick_labels, fontsize=9)
    ax.set_yticks(range(n)); ax.set_yticklabels(tick_labels, fontsize=9)
    ax.set_xlabel("Predicted cluster", fontsize=9)
    ax.set_ylabel("GT class", fontsize=9)
    ax.set_title("Perfect classification\nFM_hard k=3  (ARI = 1.0)", fontsize=10,
                 fontweight="bold")
    for i in range(n):
        for j in range(n):
            pct = cm_norm[i, j]
            color = "white" if pct > 0.55 else "black"
            ax.text(j, i, f"{int(cm[i,j])}\n({pct:.0%})",
                    ha="center", va="center", fontsize=9, color=color, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")
    plt.tight_layout()
    out = os.path.join(FIGDIR, "perfect_confusion.png")
    plt.savefig(out, dpi=150, bbox_inches="tight"); plt.close()
    print(f"  wrote {out}")

# ------------------------------------------------- per-package figures ------

def gen_pkg_figures(pkg, pred_path, outdir):
    if not os.path.exists(pred_path):
        print(f"  SKIP {pkg}: {pred_path} not found")
        return None

    pred = load_pred(pred_path)
    shared = sorted(set(gt_map) & set(pred))
    if not shared:
        print(f"  SKIP {pkg}: no overlapping keys")
        return None

    gt_list   = [gt_map[f]  for f in shared]
    pred_list = [pred[f]    for f in shared]

    ari = adjusted_rand_score(gt_list, pred_list)
    acc, cm, gt_u, pr_u = hungarian_accuracy(gt_list, pred_list)

    # cluster sizes and GT majority
    groups = {}
    for f in shared:
        groups.setdefault(pred[f], []).append(f)

    # sort clusters by size descending
    clabels = sorted(groups, key=lambda k: -len(groups[k]))
    n_cls = len(clabels)

    # --- class average panel ---
    fig, axes = plt.subplots(1, n_cls, figsize=(3.2 * n_cls, 3.6))
    if n_cls == 1:
        axes = [axes]
    fig.patch.set_facecolor("black")
    for ax, cl in zip(axes, clabels):
        files = groups[cl]
        avg = np.mean([get_slice(f) for f in files], axis=0)
        maj_gt, maj_n = Counter(gt_map[f] for f in files).most_common(1)[0]
        title = f"n={len(files)}\n(mostly {maj_gt}: {maj_n}/{len(files)})"
        lo, hi = np.percentile(avg, 2), np.percentile(avg, 98)
        ax.imshow(np.clip((avg - lo) / max(hi - lo, 1e-6), 0, 1),
                  cmap="gray", vmin=0, vmax=1)
        ax.set_title(title, color="white", fontsize=9)
        ax.axis("off")
        for sp in ax.spines.values():
            sp.set_edgecolor("white"); sp.set_linewidth(0.5)
    fig.suptitle(f"{pkg}  k=3  ARI={ari:.3f}  Acc={acc:.3f}",
                 color="white", fontsize=10, y=1.01)
    avg_out = os.path.join(FIGDIR, f"{pkg}_class_avgs.png")
    plt.savefig(avg_out, dpi=120, bbox_inches="tight",
                facecolor="black", pad_inches=0.04)
    plt.close()
    print(f"  class avgs → {avg_out}")

    # --- confusion matrix ---
    os.makedirs(outdir, exist_ok=True)
    n_gt = len(gt_u); n_pr = len(pr_u)
    fig2, ax2 = plt.subplots(figsize=(max(4, n_pr + 1), max(3.5, n_gt + 0.5)))
    im2 = ax2.imshow(cm, cmap="Blues")
    ax2.set_xticks(range(n_pr))
    ax2.set_xticklabels([str(p) for p in pr_u], fontsize=10)
    ax2.set_yticks(range(n_gt))
    ax2.set_yticklabels([str(g) for g in gt_u], fontsize=10)
    ax2.set_xlabel("Predicted", fontsize=11)
    ax2.set_ylabel("Ground Truth", fontsize=11)
    ax2.set_title(f"{pkg}  FM_hard  k=3\nARI={ari:.3f}  Acc={acc:.3f}", fontsize=11)
    plt.colorbar(im2, ax=ax2)
    for i in range(n_gt):
        for j in range(n_pr):
            ax2.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=10,
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    plt.tight_layout()
    cm_out = os.path.join(outdir, f"confusion_{pkg}_fm_hard_k3.png")
    plt.savefig(cm_out, dpi=130, bbox_inches="tight"); plt.close()
    print(f"  confusion    → {cm_out}")

    # print split numbers for README
    split = "/".join(str(len(groups[c])) for c in clabels)
    print(f"  {pkg}: ARI={ari:.3f}  Acc={acc:.3f}  split={split}")
    return {"pkg": pkg, "ari": ari, "acc": acc, "split": split,
            "avg_png": avg_out, "cm_png": cm_out}

# ------------------------------------------------------------------ main ----

PKGS = [
    ("peet",     f"{STA}/outputs/FM_hard/peet/predictions_k3_pc1_5.csv",    f"{STA}/outputs/FM_hard/peet"),
    ("disca",    f"{STA}/outputs/FM_hard/disca/disca_fm_hard_k3.csv",       f"{STA}/outputs/FM_hard/disca"),
    ("dynamo",   f"{STA}/outputs/FM_hard/dynamo/dynamo_fm_hard_k3.csv",     f"{STA}/outputs/FM_hard/dynamo"),
    ("eman2",    f"{STA}/outputs/FM_hard/eman2/eman2_fm_hard_k3.csv",       f"{STA}/outputs/FM_hard/eman2"),
    ("opus",     f"{STA}/outputs/FM_hard/opus/opus_fm_hard_k3.csv",         f"{STA}/outputs/FM_hard/opus"),
    ("relion",   f"{STA}/outputs/FM_hard/relion/relion_fm_hard_k3.csv",     f"{STA}/outputs/FM_hard/relion"),
    ("protomo",  f"{STA}/outputs/FM_hard/protomo/protomo_fm_hard_k3.csv",   f"{STA}/outputs/FM_hard/protomo"),
    ("pytom",    f"{STA}/outputs/FM_hard/pytom/pytom_fm_hard_k3.csv",       f"{STA}/outputs/FM_hard/pytom"),
    ("stopgap",  f"{STA}/outputs/FM_hard/stopgap/stopgap_fm_hard_k3.csv",   f"{STA}/outputs/FM_hard/stopgap"),
    ("tomoflow", f"{STA}/outputs/FM_hard/tomoflow/tomoflow_fm_hard_k3.csv", f"{STA}/outputs/FM_hard/tomoflow"),
]

if __name__ == "__main__":
    print("=== FM_hard figure generation ===")
    print("\n[1/2] Perfect confusion matrix")
    gen_perfect_confusion()

    print("\n[2/2] Per-package class averages + confusion matrices")
    results = []
    for pkg, pred_path, outdir in PKGS:
        print(f"\n--- {pkg} ---")
        r = gen_pkg_figures(pkg, pred_path, outdir)
        if r:
            results.append(r)

    print("\n=== Summary (paste into README) ===")
    for r in results:
        print(f"| {r['pkg']:10s} | ARI={r['ari']:.3f}  Acc={r['acc']:.3f} | split {r['split']} |")
    print("Done.")
