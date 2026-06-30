#!/usr/bin/env python3
"""Score Dynamo dpkpca predictions against T3SS GT labels."""
import os, csv
from sklearn.metrics import adjusted_rand_score

OUTDIR  = os.path.expanduser(
    "~/Research/STA/packages/dynamo/dynamo_outputs/t3ss_pca")
LABELS  = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/labels.csv")

rows = list(csv.DictReader(open(LABELS)))
gt_map = {r["file"]: r["label"] for r in rows}

signal_files = [r["file"] for r in rows if r["label"] in ("class_B","class_C")]
signal_gt    = [gt_map[f] for f in signal_files]

for k in [2, 3]:
    pred_path = os.path.join(OUTDIR, f"predictions_k{k}.csv")
    if not os.path.exists(pred_path):
        print(f"k={k}: predictions file not found, skipping")
        continue
    pred_map = {}
    for row in csv.DictReader(open(pred_path)):
        pred_map[row["file"]] = int(row["pred_label"])
    pred_signal = [pred_map[f] for f in signal_files]
    ari = adjusted_rand_score(signal_gt, pred_signal)
    cnts = {}
    for v in pred_map.values():
        cnts[v] = cnts.get(v, 0) + 1
    print(f"k={k}: ARI(B/C)={ari:.3f}  classes={sorted(cnts.items())}")
