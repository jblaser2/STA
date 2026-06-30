#!/usr/bin/env python3
"""Score EMAN2 FM_hard pcasplit output against GT labels (base/basal_body/mature).

Usage: python3 score_eman2_fm_hard.py <project_dir> <sptcls_dir>
"""
import os, sys, csv, glob
from EMAN2 import LSXFile
from sklearn.metrics import adjusted_rand_score

LABELS  = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv")
OUT_DIR = os.path.expanduser("~/Research/STA/outputs/FM_hard/eman2")
os.makedirs(OUT_DIR, exist_ok=True)

proj   = os.path.expanduser(sys.argv[1]) if len(sys.argv)>1 else os.path.expanduser("~/Research/eman2_fm_hard")
sptcls = sys.argv[2] if len(sys.argv)>2 else sorted(glob.glob(os.path.join(proj,"sptcls_*")))[-1]
if not os.path.isabs(sptcls):
    sptcls = os.path.join(proj, sptcls)

rows   = list(csv.DictReader(open(LABELS)))
gt_map = {r["file"]: r["label"] for r in rows}
files  = [r["file"] for r in rows]
idx_to_file = {i: r["file"] for i, r in enumerate(rows)}

cls_lsts = sorted(glob.glob(os.path.join(sptcls, "ptcls_cls*.lst")))
pred = {}
for c, lst_path in enumerate(cls_lsts):
    with open(lst_path) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            idx = int(line.strip().split('\t')[0])
            pred[idx_to_file[idx]] = c + 1

gt_list = [gt_map[f] for f in files]
pr_list = [pred.get(f, 0) for f in files]
ari = adjusted_rand_score(gt_list, pr_list)
k = len(cls_lsts)
print(f"EMAN2 FM_hard k={k}  ARI={ari:.3f}")
for c, lst_path in enumerate(cls_lsts):
    cnt = sum(1 for l in open(lst_path) if not l.startswith('#') and l.strip())
    print(f"  class{c+1}: {cnt} particles")

pred_csv = os.path.join(OUT_DIR, f"eman2_fm_hard_k{k}.csv")
with open(pred_csv, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["file","pred_label"])
    for fname, lbl in zip(files, pr_list):
        w.writerow([fname, lbl])
print(f"-> {pred_csv}")
