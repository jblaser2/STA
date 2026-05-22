"""
Post-sweep analysis: comparison grid, cophenetic plot, and ARI stability matrix.

Usage:
    python hac_sweep_compare.py [sweep_dir]

sweep_dir defaults to /home/jblaser2/Research/STA/dynamo/outputs/hac_sweep

Outputs (all in sweep_dir/summary/):
    comparison_grid.png   — XY central slices for every radius x class
    stability_plot.png    — cophenetic score vs mask radius
    ari_matrix.png        — pairwise ARI heatmap between radii
"""

import os, sys, glob
import numpy as np
import scipy.io
import mrcfile, shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import adjusted_rand_score

SWEEP_DIR = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/jblaser2/Research/STA/dynamo/outputs/hac_sweep'
SUMMARY_DIR = os.path.join(SWEEP_DIR, 'summary')
os.makedirs(SUMMARY_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Discover radius directories
# ------------------------------------------------------------------
radius_dirs = sorted(glob.glob(os.path.join(SWEEP_DIR, 'radius_*')))
if not radius_dirs:
    sys.exit(f'No radius_XX directories found in {SWEEP_DIR}')

radii = []
coph_scores = []
assignments = {}   # radius -> sorted label array

for rd in radius_dirs:
    r = int(os.path.basename(rd).split('_')[1])

    # Cophenetic score from hac_result.mat
    mat_path = os.path.join(rd, 'hac_result.mat')
    if not os.path.exists(mat_path):
        print(f'  [skip] {rd}: no hac_result.mat')
        continue
    mat = scipy.io.loadmat(mat_path)
    coph = float(mat['coph'].flat[0])
    n_cls = int(mat['N_CLASSES'].flat[0])

    # Class assignments
    assign_path = os.path.join(rd, f'class_assignments_{n_cls}class.txt')
    if not os.path.exists(assign_path):
        print(f'  [skip] {rd}: no assignment file')
        continue
    labels = {}
    with open(assign_path) as f:
        next(f)
        for line in f:
            name, cls = line.strip().split('\t')
            labels[name] = int(cls)

    fnames = sorted(labels.keys())
    radii.append(r)
    coph_scores.append(coph)
    assignments[r] = np.array([labels[f] for f in fnames])
    print(f'  r={r:2d}  coph={coph:.4f}  n_cls={n_cls}')

if not radii:
    sys.exit('No valid radius directories found.')

# ------------------------------------------------------------------
# 1. Cophenetic score vs radius (line plot)
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(radii, coph_scores, 'o-', color='steelblue', linewidth=2, markersize=7)
for r, c in zip(radii, coph_scores):
    ax.annotate(f'{c:.3f}', (r, c), textcoords='offset points',
                xytext=(0, 8), ha='center', fontsize=8)
ax.set_xlabel('Mask radius (voxels)', fontsize=11)
ax.set_ylabel('Cophenetic correlation', fontsize=11)
ax.set_title('HAC Classification Quality vs Mask Radius', fontsize=12)
ax.set_ylim(0, 1.0)
ax.axhline(0.7, color='gray', linestyle='--', linewidth=1, label='0.7 threshold')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
fig.tight_layout()
out = os.path.join(SUMMARY_DIR, 'stability_plot.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out}')

# ------------------------------------------------------------------
# 2. ARI pairwise matrix
# ------------------------------------------------------------------
n = len(radii)
ari_matrix = np.ones((n, n))
for i in range(n):
    for j in range(i + 1, n):
        ari = adjusted_rand_score(assignments[radii[i]], assignments[radii[j]])
        ari_matrix[i, j] = ari
        ari_matrix[j, i] = ari

fig, ax = plt.subplots(figsize=(7, 6))
im = ax.imshow(ari_matrix, vmin=0, vmax=1, cmap='RdYlGn')
plt.colorbar(im, ax=ax, label='Adjusted Rand Index')
labels_str = [f'r={r}' for r in radii]
ax.set_xticks(range(n)); ax.set_xticklabels(labels_str, rotation=45, ha='right')
ax.set_yticks(range(n)); ax.set_yticklabels(labels_str)
for i in range(n):
    for j in range(n):
        ax.text(j, i, f'{ari_matrix[i,j]:.2f}', ha='center', va='center',
                fontsize=8, color='black' if ari_matrix[i,j] > 0.3 else 'white')
ax.set_title('Classification Stability: ARI Between Radii', fontsize=11)
fig.tight_layout()
out = os.path.join(SUMMARY_DIR, 'ari_matrix.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out}')

# ------------------------------------------------------------------
# 3. Comparison grid: one row per radius, one column per class
# ------------------------------------------------------------------
def load_vol(path):
    tmp = path + '.tmp'
    with mrcfile.open(path, mode='r', permissive=True) as f:
        data = f.data.copy().astype(np.float32)
    with mrcfile.new(tmp, overwrite=True) as f:
        f.set_data(data); f.voxel_size = 1.0
    shutil.move(tmp, path)
    return data

# Find max n_classes across all radii so the grid is uniform
max_cls = max(
    int(scipy.io.loadmat(os.path.join(SWEEP_DIR, f'radius_{r:02d}', 'hac_result.mat'))
        ['N_CLASSES'].flat[0])
    for r in radii
)

n_rows = len(radii)
n_cols = max_cls
fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.5 * n_cols, 3.0 * n_rows))
if n_rows == 1: axes = axes[np.newaxis, :]
if n_cols == 1: axes = axes[:, np.newaxis]

for ri, r in enumerate(radii):
    rd     = os.path.join(SWEEP_DIR, f'radius_{r:02d}')
    avg_d  = os.path.join(rd, 'class_averages')
    coph   = coph_scores[ri]
    mrc_files = sorted(glob.glob(os.path.join(avg_d, 'class_*.mrc')))

    for ci in range(n_cols):
        ax = axes[ri][ci]
        if ci < len(mrc_files):
            vol = load_vol(mrc_files[ci])
            z   = vol.shape[0] // 2
            sl  = vol[z, :, :]
            ax.imshow(sl, cmap='gray', origin='lower',
                      vmin=np.percentile(vol, 1), vmax=np.percentile(vol, 99))
            if ri == 0:
                ax.set_title(f'Class {ci+1}', fontsize=10)
        else:
            ax.axis('off')

        if ci == 0:
            ax.set_ylabel(f'r={r}\ncoph={coph:.3f}', fontsize=9)
        ax.set_xticks([]); ax.set_yticks([])

fig.suptitle('HAC Class Averages — XY Central Slice by Mask Radius', fontsize=13)
fig.tight_layout()
out = os.path.join(SUMMARY_DIR, 'comparison_grid.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out}')
