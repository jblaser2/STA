#!/usr/bin/env python3
"""Score EMAN2 T3SS pcasplit output against GT labels.

Usage: python3 score_eman2_t3ss.py <project_dir> <sptcls_dir>
  e.g. python3 score_eman2_t3ss.py ~/Research/eman2_t3ss sptcls_02
"""
import os, sys, csv, glob
from EMAN2 import LSXFile
from sklearn.metrics import adjusted_rand_score

LABELS = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/labels.csv")

proj  = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.expanduser("~/Research/eman2_t3ss")
sptcls = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob(os.path.join(proj, "sptcls_*")))[-1]
sptcls = os.path.join(proj, sptcls) if not os.path.isabs(sptcls) else sptcls

hdf = os.path.join(proj, "particles.hdf")
rows = list(csv.DictReader(open(LABELS)))
gt = {r["file"]: r["label"] for r in rows}

# Build index: particle index in HDF → filename from source_path
import subprocess, json
idx_to_file = {}
for i, row in enumerate(rows):
    idx_to_file[i] = row["file"]

# Read per-class LST files
cls_lsts = sorted(glob.glob(os.path.join(sptcls, "ptcls_cls*.lst")))
pred = {}
for c, lst_path in enumerate(cls_lsts):
    with open(lst_path) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            idx = int(parts[0])
            pred[idx_to_file[idx]] = c + 1

all_files = [r["file"] for r in rows]
signal = [f for f in all_files if gt[f] in ("class_B", "class_C")]
gt_sig  = [gt[f] for f in signal]
pr_sig  = [pred.get(f, 0) for f in signal]

ari = adjusted_rand_score(gt_sig, pr_sig)
k = len(cls_lsts)
print(f"EMAN2 T3SS  k={k}  ARI(B/C)={ari:.3f}")
for c, lst_path in enumerate(cls_lsts):
    cnt = sum(1 for l in open(lst_path) if not l.startswith('#') and l.strip())
    print(f"  class{c+1}: {cnt} particles")
