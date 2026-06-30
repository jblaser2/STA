#!/usr/bin/env python3
"""K-means on PEET PCA scores for T3SS. Evaluates k=2 (B vs C, junk ignored) and k=3."""
import os, csv
import numpy as np, h5py
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score

RESULTS = os.path.expanduser("~/Research/peet/t3ss/results")
MAT     = os.path.join(RESULTS, "pca415_t3ss.mat")
LABELS  = os.path.expanduser(
    "~/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss/labels.csv")
OUT_DIR = os.path.expanduser("~/Research/STA/outputs/T3SS/peet")
os.makedirs(OUT_DIR, exist_ok=True)

PC_SETS = {"pc1_3": slice(0,3), "pc1_5": slice(0,5), "pc1_10": slice(0,10)}

with h5py.File(MAT, 'r') as f:
    coeffs = np.array(f['coeffs'])
print(f"Loaded coeffs: {coeffs.shape}")

rows = list(csv.DictReader(open(LABELS)))
gt   = [r["label"] for r in rows]
files = [r["file"] for r in rows]
assert len(files) == coeffs.shape[0]

signal_idx = [i for i, g in enumerate(gt) if g in ("class_B", "class_C")]
gt_signal  = [gt[i] for i in signal_idx]

for k in [2, 3]:
    for pc_name, pc_sl in PC_SETS.items():
        X = StandardScaler().fit_transform(coeffs[:, pc_sl])
        pred = KMeans(n_clusters=k, n_init=20, random_state=42).fit_predict(X)

        # Write full predictions CSV
        tag = f"k{k}_{pc_name}"
        out = os.path.join(OUT_DIR, f"predictions_{tag}.csv")
        with open(out, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["file","pred_label","gt_label"])
            for fname, p, g in zip(files, pred, gt):
                w.writerow([fname, p+1, g])

        # Score: for k=2 evaluate only signal particles (ignore junk assignment)
        pred_signal = [pred[i] for i in signal_idx]
        ari = adjusted_rand_score(gt_signal, pred_signal)
        cnts = {c: (pred==c).sum() for c in range(k)}
        print(f"k={k} {pc_name:8s}: ARI(B/C)={ari:.3f}  "
              f"classes={[cnts[c] for c in range(k)]}")
