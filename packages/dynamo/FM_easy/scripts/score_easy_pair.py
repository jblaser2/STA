#!/usr/bin/env python3
"""Score a 2-class dpkpca pair run. Usage: score_easy_pair.py <PAIR>"""
import os, csv, sys
from sklearn.metrics import adjusted_rand_score, accuracy_score
import numpy as np

PAIR = sys.argv[1].upper()
OUT = os.path.expanduser(f"~/Research/STA/packages/dynamo/dynamo_outputs/easy_pair_{PAIR}")
lab = {r["tag"]: r["gt_label"] for r in csv.DictReader(open(os.path.join(OUT, "pair_labels.csv")))}
pred = {r["tag"]: r["pred_label"] for r in csv.DictReader(open(os.path.join(OUT, "predictions_k2.csv")))}
tags = sorted(lab, key=int)
y = [lab[t] for t in tags]; p = [pred[t] for t in tags]
classes = sorted(set(y))
ymap = {c: i for i, c in enumerate(classes)}
yi = np.array([ymap[c] for c in y]); pi = np.array([int(c) for c in p])
ari = adjusted_rand_score(yi, pi)
# best-permutation accuracy + confusion
acc = max((pi == yi).mean(), (pi != yi).mean())
print(f"=== Dynamo dpkpca pair {PAIR[0]}-{PAIR[1]}  (n={len(y)}) ===")
print(f"  ARI = {ari:.3f}   acc = {acc:.3f}")
for c in classes:
    idx = [i for i, v in enumerate(y) if v == c]
    n1 = sum(pi[i] == 1 for i in idx); n2 = sum(pi[i] == 2 for i in idx)
    print(f"  GT {c}: pred1={n1}  pred2={n2}")
