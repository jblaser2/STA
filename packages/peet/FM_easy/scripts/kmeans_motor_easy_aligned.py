#!/usr/bin/env python3
"""
kmeans_motor_easy.py — k-means classification on PEET PCA scores for motor_easy.

Reads pca542_motor_easy_aligned.mat (from PEET pca command), applies sklearn k-means on
the top N principal components, and writes predictions.csv for score_synthetic.py.

Usage:
  conda run -n eman2 python3 peet/kmeans_motor_easy.py
"""
import os
import csv
import numpy as np
import h5py
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

RESULTS = "/home/jblaser2/Research/peet/motor_easy_aligned/results"
MAT     = os.path.join(RESULTS, "pca542_motor_easy_aligned.mat")
LABELS  = "/home/jblaser2/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_aligned/labels.csv"
STA_DIR = "/home/jblaser2/Research/STA"
OUT_DIR = "outputs/FM_easy/peet_aligned"
GT_LABEL_FILE = LABELS

# PC subsets to try for k-means (based on T4P experience: PCs 1:3 best)
PC_SETS = {
    "pc1_3":  slice(0, 3),
    "pc1_5":  slice(0, 5),
    "pc1_10": slice(0, 10),
}
KS = [2]
N_INIT = 10
SEED   = 42


def load_pc_scores(mat_path):
    with h5py.File(mat_path, 'r') as f:
        coeffs = np.array(f['coeffs'])  # (694, 20)
    print(f"Loaded coeffs: {coeffs.shape} from {mat_path}")
    return coeffs


def get_file_order(labels_csv):
    files = []
    with open(labels_csv) as f:
        for row in csv.DictReader(f):
            files.append(os.path.basename(row["file"]))
    return files


def run_kmeans(coeffs, pc_slice, k, seed=SEED, n_init=N_INIT):
    X = coeffs[:, pc_slice]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    km = KMeans(n_clusters=k, n_init=n_init, random_state=seed)
    labels = km.fit_predict(X_scaled)
    return labels


def write_predictions(file_order, labels, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "pred_label"])
        for fname, lbl in zip(file_order, labels):
            w.writerow([fname, str(lbl + 1)])  # 1-indexed to match RELION/PEET conventions


def main():
    coeffs = load_pc_scores(MAT)
    file_order = get_file_order(LABELS)
    assert len(file_order) == coeffs.shape[0], \
        f"Mismatch: {len(file_order)} files vs {coeffs.shape[0]} PC rows"

    os.makedirs(os.path.join(STA_DIR, OUT_DIR), exist_ok=True)

    for k in KS:
        for pc_name, pc_slice in PC_SETS.items():
            run_tag = f"k{k}_{pc_name}"
            pred_csv = os.path.join(STA_DIR, OUT_DIR, f"predictions_{run_tag}.csv")
            labels = run_kmeans(coeffs, pc_slice, k)
            write_predictions(file_order, labels, pred_csv)
            counts = {c: (labels == c).sum() for c in range(k)}
            count_str = " ".join(f"class{i+1}:{n}" for i, n in sorted(counts.items()))
            print(f"  k={k} {pc_name}: {count_str} -> {pred_csv}")

    print(f"\nDone. Score each run with:")
    print(f"  cd {STA_DIR}")
    print(f"  GT={LABELS}")
    for k in KS:
        for pc_name in PC_SETS:
            run_tag = f"k{k}_{pc_name}"
            print(f"  python3 scripts/eval/score_synthetic.py "
                  f"--pred {OUT_DIR}/predictions_{run_tag}.csv "
                  f"--gt $GT --package peet --k {k} --run {run_tag}")


if __name__ == "__main__":
    main()
