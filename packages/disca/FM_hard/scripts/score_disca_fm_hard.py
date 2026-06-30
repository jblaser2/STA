#!/usr/bin/env python3
"""Score DISCA FM_hard output against GT labels (base/basal_body/mature)."""
import os, csv, pickle
from collections import Counter
from sklearn.metrics import adjusted_rand_score

LABELS    = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv")
MODEL_DIR = os.path.expanduser("~/Research/disca_work/model_motor_hard")
OUT_DIR   = os.path.expanduser("~/Research/STA/outputs/FM_hard/disca")
os.makedirs(OUT_DIR, exist_ok=True)

rows   = list(csv.DictReader(open(LABELS)))
files  = [r["file"] for r in rows]
gt_map = {r["file"]: r["label"] for r in rows}

for k in [3]:
    label_path = os.path.join(MODEL_DIR, f"labels_motor_hard_k{k}.pickle")
    if not os.path.exists(label_path):
        print(f"k={k}: {label_path} not found"); continue
    with open(label_path, "rb") as f:
        labels = pickle.load(f)

    pred_map = {files[i]: int(labels[i]) for i in range(len(files))}
    gt_list  = [gt_map[f] for f in files]
    pr_list  = [pred_map[f] for f in files]
    ari = adjusted_rand_score(gt_list, pr_list)
    cnts = Counter(labels)
    print(f"DISCA FM_hard k={k}: ARI={ari:.3f}  classes={dict(sorted(cnts.items()))}")

    pred_csv = os.path.join(OUT_DIR, f"disca_fm_hard_k{k}.csv")
    with open(pred_csv, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["file", "pred_label"])
        for fname, lbl in zip(files, labels):
            w.writerow([fname, str(lbl)])
    print(f"  -> {pred_csv}")
