#!/usr/bin/env python3
"""Score DISCA T3SS output against GT labels."""
import os, csv, pickle
from sklearn.metrics import adjusted_rand_score

LABELS  = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/labels.csv")
MODEL_DIR = os.path.expanduser("~/Research/disca_work/model_t3ss")

rows = list(csv.DictReader(open(LABELS)))
files = [r["file"] for r in rows]
gt_map = {r["file"]: r["label"] for r in rows}
signal = [r["file"] for r in rows if r["label"] in ("class_B","class_C")]
gt_sig  = [gt_map[f] for f in signal]

# key mapping: DISCA uses stem (subtomo_0000) as key
stems = [os.path.splitext(f)[0] for f in files]
idx_to_file = {s: f for s, f in zip(stems, files)}

for k in [2, 3]:
    label_path = os.path.join(MODEL_DIR, f"labels_t3ss_k{k}.pickle")
    if not os.path.exists(label_path):
        print(f"k={k}: label file not found"); continue
    with open(label_path, "rb") as f:
        labels = pickle.load(f)
    pred_map = {files[i]: int(labels[i]) for i in range(len(files))}
    pr_sig = [pred_map[f] for f in signal]
    ari = adjusted_rand_score(gt_sig, pr_sig)
    from collections import Counter
    cnts = Counter(labels)
    print(f"DISCA T3SS k={k}: ARI(B/C)={ari:.3f}  classes={dict(sorted(cnts.items()))}")
