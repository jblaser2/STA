"""
Visualize HAC classification in 2D using t-SNE and UMAP.

Loads the precomputed 672×672 CC matrix and the 2-class / 3-class assignments,
then produces a 2×2 figure: rows = t-SNE / UMAP, columns = 2-class / 3-class.

Usage:
    python plot_embedding.py [output_dir]

Saves: <output_dir>/embedding_<tsne|umap>_2v3class.png
No display required.
"""

import os, sys
import numpy as np
import scipy.io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import umap

OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/jblaser2/Research/STA/dynamo/outputs/hac_classification'

# ------------------------------------------------------------------
# Load CC matrix and convert to distance matrix
# ------------------------------------------------------------------
mat = scipy.io.loadmat(os.path.join(OUTPUT_DIR, 'ccmatrix.mat'))
cc = mat['ccmatrix'].astype(np.float64)
dist = 1.0 - cc
np.fill_diagonal(dist, 0.0)
dist = np.clip(dist, 0, None)   # numerical safety
print(f'Loaded CC matrix: {cc.shape}')

# ------------------------------------------------------------------
# Load class assignments
# ------------------------------------------------------------------
def load_assignments(path):
    labels = {}
    with open(path) as f:
        next(f)  # header
        for line in f:
            name, cls = line.strip().split('\t')
            labels[name] = int(cls)
    return labels

a2 = load_assignments(os.path.join(OUTPUT_DIR, 'class_assignments_2class.txt'))
a3 = load_assignments(os.path.join(OUTPUT_DIR, 'class_assignments_3class.txt'))

# Build label arrays in the same order (sorted filenames, matching MATLAB sort)
fnames = sorted(a2.keys())
labels2 = np.array([a2[f] for f in fnames])
labels3 = np.array([a3[f] for f in fnames])
print(f'Particles: {len(fnames)}')

# ------------------------------------------------------------------
# Compute embeddings
# ------------------------------------------------------------------
print('Running t-SNE...')
tsne = TSNE(n_components=2, metric='precomputed', perplexity=30,
            max_iter=1000, random_state=42, init='random')
emb_tsne = tsne.fit_transform(dist)

print('Running UMAP...')
reducer = umap.UMAP(n_components=2, metric='precomputed',
                    n_neighbors=15, min_dist=0.1, random_state=42)
emb_umap = reducer.fit_transform(dist)

# ------------------------------------------------------------------
# Plot 2×2: rows = method, columns = N classes
# ------------------------------------------------------------------
COLORS_2 = ['#2196F3', '#F44336']                    # blue, red
COLORS_3 = ['#2196F3', '#F44336', '#4CAF50']         # blue, red, green
SIZE = 18
ALPHA = 0.7

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('HAC Classification Embedding  (mask r=20, 672 particles)', fontsize=13)

configs = [
    (0, emb_tsne, labels2, 2, COLORS_2, 't-SNE — 2 classes'),
    (1, emb_tsne, labels3, 3, COLORS_3, 't-SNE — 3 classes'),
    (2, emb_umap, labels2, 2, COLORS_2, 'UMAP — 2 classes'),
    (3, emb_umap, labels3, 3, COLORS_3, 'UMAP — 3 classes'),
]

class_sizes_2 = {c: np.sum(labels2 == c) for c in range(1, 3)}
class_sizes_3 = {c: np.sum(labels3 == c) for c in range(1, 4)}

for idx, emb, labels, n_cls, colors, title in configs:
    ax = axes[idx // 2][idx % 2]
    sizes = class_sizes_2 if n_cls == 2 else class_sizes_3
    for c in range(1, n_cls + 1):
        mask = labels == c
        ax.scatter(emb[mask, 0], emb[mask, 1],
                   c=colors[c - 1], s=SIZE, alpha=ALPHA,
                   label=f'Class {c}  (n={sizes[c]})',
                   linewidths=0)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9, markerscale=1.5)
    ax.set_xlabel('Dim 1', fontsize=9)
    ax.set_ylabel('Dim 2', fontsize=9)
    ax.tick_params(labelsize=8)

fig.tight_layout()
out_png = os.path.join(OUTPUT_DIR, 'embedding_2v3class.png')
fig.savefig(out_png, dpi=150, bbox_inches='tight')
print(f'Saved: {out_png}')
