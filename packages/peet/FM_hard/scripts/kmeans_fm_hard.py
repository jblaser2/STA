#!/usr/bin/env python3
"""
kmeans_fm_hard.py — k-means on PEET PCA scores for FM_hard (813p, 3 classes).

Reads pca813_motor_hard.mat, applies k=3 k-means on top N PCs,
saves prediction CSVs to outputs/FM_hard/peet/.

Usage:  conda run -n eman2 python3 packages/peet/FM_hard/scripts/kmeans_fm_hard.py
"""
import os, csv
import numpy as np, h5py
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score

RESULTS   = os.path.expanduser("~/Research/peet/motor_hard/results")
MAT       = os.path.join(RESULTS, "pca813_motor_hard.mat")
LABELS    = os.path.expanduser(
    "~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv")
STA_DIR   = os.path.expanduser("~/Research/STA")
OUT_DIR   = os.path.join(STA_DIR, "outputs/FM_hard/peet")

PC_SETS   = {"pc1_3": slice(0,3), "pc1_5": slice(0,5), "pc1_10": slice(0,10)}
K         = 3
N_INIT    = 10
SEED      = 42

os.makedirs(OUT_DIR, exist_ok=True)

def load_pc_scores(mat_path):
    with h5py.File(mat_path, 'r') as f:
        coeffs = np.array(f['coeffs'])
    print(f"Loaded coeffs: {coeffs.shape}")
    return coeffs

gt_rows  = list(csv.DictReader(open(LABELS)))
gt_map   = {r["file"]: r["label"] for r in gt_rows}
files    = [r["file"] for r in gt_rows]

coeffs = load_pc_scores(MAT)
assert len(files) == coeffs.shape[0], f"Mismatch: {len(files)} vs {coeffs.shape[0]}"

for pc_name, pc_slice in PC_SETS.items():
    X = StandardScaler().fit_transform(coeffs[:, pc_slice])
    labels = KMeans(n_clusters=K, n_init=N_INIT, random_state=SEED).fit_predict(X)

    pred_csv = os.path.join(OUT_DIR, f"predictions_k{K}_{pc_name}.csv")
    with open(pred_csv, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["file", "pred_label"])
        for fname, lbl in zip(files, labels):
            w.writerow([fname, str(lbl + 1)])

    ari = adjusted_rand_score([gt_map[f] for f in files], labels)
    from collections import Counter
    cnts = Counter(labels)
    cnt_str = " ".join(f"c{i+1}:{n}" for i,n in sorted(cnts.items()))
    print(f"  k={K} {pc_name}: ARI={ari:.3f}  {cnt_str}  -> {pred_csv}")
