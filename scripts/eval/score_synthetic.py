#!/usr/bin/env python3
"""
score_synthetic.py — score package predictions against motor_easy ground truth.

Usage:
  python3 scripts/eval/score_synthetic.py \
    --pred outputs/relion_motor_easy/Class3D/k3_wedge/predictions.csv \
    --gt ~/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv \
    --package relion --k 3 --run k3_wedge

Input CSVs:
  pred: file,pred_label    (file column = basename only, e.g. subtomo_0000.mrc)
  gt:   file,label         (same basename; extra columns ignored)

Outputs:
  confusion matrix PNG next to --pred CSV (or --outdir)
  row appended to results/synthetic_scores.csv
"""
import argparse
import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import (adjusted_rand_score, adjusted_mutual_info_score,
                              v_measure_score, confusion_matrix)
from scipy.optimize import linear_sum_assignment

SCORES_CSV = "results/synthetic_scores.csv"
SCORES_FIELDS = ["package", "dataset", "k", "run", "n_particles",
                 "ARI", "AMI", "V_measure", "accuracy", "pred_csv", "notes"]


def load_csv_map(path, key_col, val_col):
    result = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            result[os.path.basename(row[key_col])] = row[val_col]
    return result


def hungarian_accuracy(gt_labels, pred_labels):
    gt_u = sorted(set(gt_labels))
    pr_u = sorted(set(pred_labels))
    gt_idx = np.array([gt_u.index(g) for g in gt_labels])
    pr_idx = np.array([pr_u.index(p) for p in pred_labels])
    cm = confusion_matrix(gt_idx, pr_idx, labels=range(len(gt_u)))
    n = max(len(gt_u), len(pr_u))
    pad = np.zeros((n, n), dtype=cm.dtype)
    pad[:cm.shape[0], :cm.shape[1]] = cm
    row_ind, col_ind = linear_sum_assignment(-pad)
    acc = pad[row_ind, col_ind].sum() / len(gt_labels)
    return acc, cm, gt_u, pr_u


def plot_confusion(cm, gt_labels, pred_labels, out_path, title=""):
    fig, ax = plt.subplots(figsize=(max(5, len(pred_labels) + 1),
                                    max(4, len(gt_labels) + 1)))
    im = ax.imshow(cm, cmap='Blues')
    ax.set_xticks(range(len(pred_labels)))
    ax.set_yticks(range(len(gt_labels)))
    ax.set_xticklabels([str(p) for p in pred_labels], fontsize=11)
    ax.set_yticklabels([str(g) for g in gt_labels], fontsize=11)
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("Ground Truth", fontsize=12)
    ax.set_title(title or "Confusion matrix", fontsize=12)
    plt.colorbar(im, ax=ax)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, cm[i, j], ha='center', va='center',
                    color='white' if cm[i, j] > cm.max() / 2 else 'black',
                    fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
    print(f"  confusion matrix -> {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred", required=True,
                    help="CSV with columns: file, pred_label")
    ap.add_argument("--gt", required=True,
                    help="GT labels CSV with columns: file, label")
    ap.add_argument("--package", required=True)
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--run", default="", help="Run identifier e.g. k3_wedge")
    ap.add_argument("--dataset", default="motor_easy")
    ap.add_argument("--notes", default="")
    ap.add_argument("--outdir", default=None,
                    help="Dir for confusion PNG; defaults to dirname of --pred")
    args = ap.parse_args()

    gt_map = load_csv_map(args.gt, "file", "label")
    pred_map = load_csv_map(args.pred, "file", "pred_label")

    shared = sorted(set(gt_map) & set(pred_map))
    if not shared:
        raise SystemExit(
            f"No overlapping file keys between\n  gt:   {args.gt}\n  pred: {args.pred}\n"
            f"  gt sample keys:   {list(gt_map)[:3]}\n"
            f"  pred sample keys: {list(pred_map)[:3]}")

    gt_labels   = [gt_map[k]   for k in shared]
    pred_labels = [pred_map[k] for k in shared]

    ari = adjusted_rand_score(gt_labels, pred_labels)
    ami = adjusted_mutual_info_score(gt_labels, pred_labels)
    vm  = v_measure_score(gt_labels, pred_labels)
    acc, cm, gt_u, pr_u = hungarian_accuracy(gt_labels, pred_labels)

    print(f"\n=== {args.package} k={args.k} {args.run} ===")
    print(f"  N={len(shared)}  ARI={ari:.4f}  AMI={ami:.4f}  V={vm:.4f}  Acc={acc:.4f}")
    print(f"  GT classes: {gt_u}")
    print(f"  Pred classes: {pr_u}")
    print(f"  Confusion matrix (GT rows × Pred cols):")
    for i, g in enumerate(gt_u):
        row_str = "  ".join(f"{cm[i,j]:4d}" for j in range(len(pr_u)))
        print(f"    {g}: {row_str}")

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.pred))
    os.makedirs(outdir, exist_ok=True)
    run_tag = args.run.replace("/", "_")
    cm_path = os.path.join(outdir,
                           f"confusion_{args.package}_k{args.k}_{run_tag}.png")
    plot_confusion(cm, gt_u, pr_u, cm_path,
                   title=f"{args.package} k={args.k} {args.run}  ARI={ari:.3f}")

    os.makedirs(os.path.dirname(os.path.abspath(SCORES_CSV)), exist_ok=True)
    write_header = not os.path.exists(SCORES_CSV)
    with open(SCORES_CSV, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCORES_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow({
            "package":     args.package,
            "dataset":     args.dataset,
            "k":           args.k,
            "run":         args.run,
            "n_particles": len(shared),
            "ARI":         f"{ari:.6f}",
            "AMI":         f"{ami:.6f}",
            "V_measure":   f"{vm:.6f}",
            "accuracy":    f"{acc:.6f}",
            "pred_csv":    args.pred,
            "notes":       args.notes,
        })
    print(f"  appended to {SCORES_CSV}")


if __name__ == "__main__":
    main()
