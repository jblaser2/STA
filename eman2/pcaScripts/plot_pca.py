#!/usr/bin/env python3
"""
Plot PCA scatter from pca_ptcls.txt.
Usage: python plot_pca.py [path/to/pca_ptcls.txt]
       With no argument, finds the latest sptcls_XX/pca_ptcls.txt automatically.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")  # save to file without display
import matplotlib.pyplot as plt
import glob
import sys
import os

if len(sys.argv) > 1:
    pca_file = sys.argv[1]
else:
    candidates = sorted(glob.glob("sptcls_*/pca_ptcls.txt"))
    if not candidates:
        print("ERROR: No sptcls_XX/pca_ptcls.txt found. Run e2spt_pcasplit.py first.")
        sys.exit(1)
    pca_file = candidates[-1]

print(f"Loading {pca_file}")
data = np.loadtxt(pca_file)
coords = data[:, 1:]   # column 0 is particle ID; 1..N are PCA coordinates
n_particles, nbasis = coords.shape
print(f"{n_particles} particles, {nbasis} PCA components")

if nbasis < 2:
    print("ERROR: Need at least 2 PCA components to plot.")
    sys.exit(1)

out_dir = os.path.dirname(os.path.abspath(pca_file))
out_path = os.path.join(out_dir, "pca_scatter.png")

n_plots = min(nbasis - 1, 3)
pairs = [(0, 1), (0, 2), (1, 2)][:n_plots]
labels = [f"PC{i+1}" for i in range(nbasis)]

fig, axes = plt.subplots(1, n_plots, figsize=(5 * n_plots, 5))
if n_plots == 1:
    axes = [axes]

for ax, (i, j) in zip(axes, pairs):
    ax.scatter(coords[:, i], coords[:, j], alpha=0.5, s=10, c="steelblue")
    ax.set_xlabel(labels[i])
    ax.set_ylabel(labels[j])
    ax.set_title(f"{labels[i]} vs {labels[j]}")

fig.suptitle(f"{n_particles} particles — {pca_file}", fontsize=9)
plt.tight_layout()
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved: {out_path}")
