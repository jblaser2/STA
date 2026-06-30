#!/usr/bin/env python3
"""Score Dynamo FM_hard dpkpca predictions vs GT labels."""
import os, csv
from collections import Counter
from sklearn.metrics import adjusted_rand_score

OUTDIR  = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/motor_hard_pca")
LABELS  = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv")
OUT_CSV_DIR = os.path.expanduser("~/Research/STA/outputs/FM_hard/dynamo")
os.makedirs(OUT_CSV_DIR, exist_ok=True)

gt_rows = list(csv.DictReader(open(LABELS)))
gt_map  = {r["file"]: r["label"] for r in gt_rows}
files   = [r["file"] for r in gt_rows]

for k in [3]:
    pred_path = os.path.join(OUTDIR, f"predictions_k{k}.csv")
    if not os.path.exists(pred_path):
        print(f"k={k}: {pred_path} not found"); continue
    pred_rows = list(csv.DictReader(open(pred_path)))
    pred_map  = {r["file"]: int(r["pred_label"]) for r in pred_rows}
    gt_list   = [gt_map[f] for f in files]
    pr_list   = [pred_map.get(f, 0) for f in files]
    ari = adjusted_rand_score(gt_list, pr_list)
    cnts = Counter(pr_list)
    print(f"Dynamo FM_hard k={k}: ARI={ari:.3f}  classes={dict(sorted(cnts.items()))}")

    out_csv = os.path.join(OUT_CSV_DIR, f"dynamo_fm_hard_k{k}.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["file", "pred_label"])
        for fname, lbl in zip(files, pr_list):
            w.writerow([fname, lbl])
    print(f"  -> {out_csv}")
