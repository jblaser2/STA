#!/usr/bin/env python3
"""
Diagnostic: masked PCA + k-means (k=2) on PAIRS of motor_easy GT classes.
Mirrors the core engine of Dynamo dpkpca / PEET PCA / EMAN2 pcasplit so we can
see whether the per-particle compositional signal is separable, and which pair
(A-B, A-C, B-C) is the confound. Also reports whether PC1 is the contrast axis.

Run: conda run -n relion-5.0 python3 scripts/eval/pairwise_pca_kmeans_motor_easy.py
"""
import os, csv, itertools
import numpy as np
import mrcfile
from scipy.ndimage import gaussian_filter
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

SUB  = ("/home/jblaser2/Research/synthetic_sta/motor_easy/production/"
        "subtomos/merged_all_aln")
MASK = "/home/jblaser2/Research/STA/outputs/FM_easy/input_qc/motor_easy_mask.mrc"
LOWP_SIGMA = 1.5          # light real-space lowpass (denoise) before PCA
NPC = 20

rows = [(r["file"], r["label"]) for r in csv.DictReader(open(os.path.join(SUB, "labels.csv")))]
mask = np.asarray(mrcfile.open(MASK, permissive=True).data, np.float32)
idx = mask > 0.05         # voxels to keep

def feat(fn, normalize):
    v = np.asarray(mrcfile.open(os.path.join(SUB, fn), permissive=True).data, np.float32)
    v = gaussian_filter(v, LOWP_SIGMA) * mask
    x = v[idx]
    if normalize:                       # per-particle z-score: removes contrast/DC axis
        x = (x - x.mean()) / (x.std() + 1e-6)
    return x

def run_pair(c1, c2, normalize):
    files = [(f, l) for f, l in rows if l in (c1, c2)]
    X = np.stack([feat(f, normalize) for f, _ in files])
    y = np.array([0 if l == c1 else 1 for _, l in files])
    X = X - X.mean(0)
    P = PCA(n_components=NPC, svd_solver="randomized", random_state=0).fit(X)
    Z = P.transform(X)
    km = KMeans(n_clusters=2, n_init=20, random_state=0).fit(Z)
    ari = adjusted_rand_score(y, km.labels_)
    # is PC1 the contrast axis? correlate PC1 score with per-particle raw mean
    rawmean = np.array([np.asarray(mrcfile.open(os.path.join(SUB, f), permissive=True).data,
                                   np.float32)[idx].mean() for f, _ in files])
    pc1_contrast = np.corrcoef(Z[:, 0], rawmean)[0, 1]
    n1, n2 = int((y == 0).sum()), int((y == 1).sum())
    return ari, pc1_contrast, n1, n2

print(f"mask {idx.sum()} voxels | lowpass sigma={LOWP_SIGMA} | {NPC} PCs | KMeans k=2\n")
for norm in (False, True):
    tag = "per-particle NORMALIZED (contrast removed)" if norm else "RAW (contrast free to dominate)"
    print(f"=== {tag} ===")
    print(f"{'pair':6s} {'n1/n2':>9s} {'ARI':>8s}   corr(PC1, mean-intensity)")
    for c1, c2 in itertools.combinations("ABC", 2):
        ari, pc1c, n1, n2 = run_pair(c1, c2, norm)
        print(f"{c1}-{c2:4s} {n1:4d}/{n2:<4d} {ari:8.3f}   {pc1c:+.2f}")
    print()
