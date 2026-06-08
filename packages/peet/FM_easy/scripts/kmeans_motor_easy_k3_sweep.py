#!/usr/bin/env python3
"""Sweep nc=1..20 for PEET k=3 k-means on motor_easy to find best PC subset."""
import os, csv
import numpy as np
import h5py
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import adjusted_rand_score

MAT    = "/home/jblaser2/Research/peet/motor_easy/results/pca694_motor_easy.mat"
LABELS = "/home/jblaser2/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln/labels.csv"
STA_DIR = "/home/jblaser2/Research/STA"
OUT_DIR = os.path.join(STA_DIR, "outputs/peet_motor_easy")
GT_CLASS_MAP = {"A": 1, "B": 2, "C": 3}

K = 3
N_INIT = 50
N_REPEAT = 5
SEED = 42

def load_data():
    with h5py.File(MAT, 'r') as f:
        coeffs = np.array(f['coeffs'])  # (694, 20)
    files, gt = [], []
    with open(LABELS) as f:
        for row in csv.DictReader(f):
            files.append(os.path.basename(row["file"]))
            gt.append(GT_CLASS_MAP[row["label"]])
    return coeffs, files, np.array(gt)

coeffs, files, gt = load_data()
print(f"coeffs: {coeffs.shape}, GT classes: {np.bincount(gt)[1:]}")

results = []
for nc in range(1, 21):
    X = StandardScaler().fit_transform(coeffs[:, :nc])
    best_ari, best_labels = -999, None
    for seed in range(N_REPEAT):
        km = KMeans(n_clusters=K, n_init=N_INIT, random_state=SEED + seed)
        pred = km.fit_predict(X)
        ari = adjusted_rand_score(gt, pred)
        if ari > best_ari:
            best_ari = ari
            best_labels = pred.copy()
    counts = " ".join(f"c{i+1}:{(best_labels==i).sum()}" for i in range(K))
    print(f"  nc={nc:2d}: ARI={best_ari:.4f}  [{counts}]")
    results.append((nc, best_ari, best_labels))

best_nc, best_ari, best_pred = max(results, key=lambda x: x[1])
print(f"\nBest: nc={best_nc}, ARI={best_ari:.4f}")

# Save best predictions
out_path = os.path.join(OUT_DIR, "predictions_k3_nc_best.csv")
with open(out_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "pred_label"])
    for fname, lbl in zip(files, best_pred):
        w.writerow([fname, str(lbl + 1)])
print(f"Saved: {out_path}")

# Score with eval script
import subprocess
result = subprocess.run(
    ["/home/jblaser2/conda-envs/eman2/bin/python3",
     "scripts/eval/score_synthetic.py",
     "--pred", out_path,
     "--gt", LABELS,
     "--package", "peet", "--k", str(K),
     "--run", f"k3_nc{best_nc}_best_cnew"],
    capture_output=True, text=True, cwd=STA_DIR
)
print(result.stdout.strip())
if result.stderr:
    print(result.stderr.strip())
