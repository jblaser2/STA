"""
Generate all visualizations and data exports for dynamo_final_results/.

Requires:
  - dynamo_outputs/hac_sweep_fine/radius_7p2/  (CC matrix, class averages, assignments)
  - dynamo_final_results/fsc/resolution.txt    (from compute_fsc.m)

Outputs (all in dynamo_final_results/):
  class_averages/class_01.mrc, class_02.mrc   (header-fixed)
  class_assignments.csv
  class_comparison.png
  embedding_umap.png
  embedding_tsne.png
  embedding_coords.csv
  ccmatrix.npy
  fsc/fsc_curves.png
  parameters.json
"""

import os, sys, shutil, json
import numpy as np
import scipy.io
import mrcfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from sklearn.manifold import TSNE
import umap

BASE        = '/home/jblaser2/Research/STA/dynamo'
R72_DIR     = os.path.join(BASE, 'dynamo_outputs/hac_sweep_final_pick/radius_8p9')
FINAL_DIR   = os.path.join(BASE, 'dynamo_final_results')
PIXEL_ANG   = 13.328
MASK_RADIUS = 8.9
COPH        = 0.3574

os.makedirs(os.path.join(FINAL_DIR, 'class_averages'), exist_ok=True)
os.makedirs(os.path.join(FINAL_DIR, 'fsc'), exist_ok=True)

# ------------------------------------------------------------------
# Load CC matrix
# ------------------------------------------------------------------
print('Loading CC matrix...')
mat = scipy.io.loadmat(os.path.join(R72_DIR, 'ccmatrix.mat'))
cc  = mat['ccmatrix'].astype(np.float64)
dist = np.clip(1.0 - cc, 0, None)
np.fill_diagonal(dist, 0.0)
print(f'  CC matrix: {cc.shape}')

# Save CC matrix as numpy for cross-package comparison
np.save(os.path.join(FINAL_DIR, 'ccmatrix.npy'), cc.astype(np.float32))
print('  Saved ccmatrix.npy')

# ------------------------------------------------------------------
# Load class assignments
# ------------------------------------------------------------------
assign_path = os.path.join(R72_DIR, 'class_assignments_2class.txt')
labels = {}
with open(assign_path) as f:
    next(f)
    for line in f:
        name, cls = line.strip().split('\t')
        labels[name] = int(cls)
fnames = sorted(labels.keys())
label_arr = np.array([labels[f] for f in fnames])

# Save as CSV
with open(os.path.join(FINAL_DIR, 'class_assignments.csv'), 'w') as f:
    f.write('particle,class\n')
    for name, cls in zip(fnames, label_arr):
        f.write(f'{name},{cls}\n')
print('  Saved class_assignments.csv')

class_counts = {c: int(np.sum(label_arr == c)) for c in [1, 2]}
print(f'  Class 1: {class_counts[1]}   Class 2: {class_counts[2]}')

# ------------------------------------------------------------------
# Fix MRC headers and copy class averages
# ------------------------------------------------------------------
def load_fix_mrc(src, dst):
    tmp = src + '.tmp'
    with mrcfile.open(src, mode='r', permissive=True) as f:
        data = f.data.copy().astype(np.float32)
    with mrcfile.new(tmp, overwrite=True) as f:
        f.set_data(data)
        f.voxel_size = PIXEL_ANG
    shutil.move(tmp, dst)
    return data

vols = []
for c in [1, 2]:
    src = os.path.join(R72_DIR, 'class_averages', f'class_{c:02d}.mrc')
    dst = os.path.join(FINAL_DIR, 'class_averages', f'class_{c:02d}.mrc')
    vol = load_fix_mrc(src, dst)
    vols.append(vol)
    print(f'  class_{c:02d}.mrc: shape={vol.shape}, voxel_size={PIXEL_ANG} Å')

# ------------------------------------------------------------------
# Read FSC resolution estimates
# ------------------------------------------------------------------
res_path = os.path.join(FINAL_DIR, 'fsc', 'resolution.txt')
res_ang      = {}   # FSC=0.5 resolution in Angstroms
res_ang_0143 = {}   # FSC=0.143 resolution in Angstroms
if os.path.exists(res_path):
    with open(res_path) as f:
        next(f)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                res_ang[int(parts[0])]      = float(parts[3])
                res_ang_0143[int(parts[0])] = float(parts[4])
    print(f'  FSC resolution (0.5): {res_ang}')
    print(f'  FSC resolution (0.143): {res_ang_0143}')
else:
    print('  [warning] resolution.txt not found — skipping resolution labels')

# ------------------------------------------------------------------
# Class comparison PNG (XY central slice, side by side)
# ------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
for i, (vol, ax) in enumerate(zip(vols, axes)):
    c = i + 1
    z = vol.shape[0] // 2
    sl = vol[z, :, :]
    ax.imshow(sl, cmap='gray', origin='lower',
              vmin=np.percentile(vol, 1), vmax=np.percentile(vol, 99))
    r05  = f'{res_ang[c]:.1f} Å'      if c in res_ang      else 'N/A'
    r143 = f'{res_ang_0143[c]:.1f} Å' if c in res_ang_0143 else 'N/A'
    ax.set_title(f'Class {c}  (n={class_counts[c]})\nRes: {r05} (FSC=0.5)  |  {r143} (FSC=0.143)',
                 fontsize=11)
    ax.axis('off')

fig.suptitle(
    f'Dynamo HAC Classification — XY Central Slice\n'
    f'Mask radius: {MASK_RADIUS} vox ({MASK_RADIUS * PIXEL_ANG:.1f} Å)  |  '
    f'Pixel size: {PIXEL_ANG} Å/vox  |  '
    f'N particles: {sum(class_counts.values())}  |  '
    f'Cophenetic: {COPH:.4f}',
    fontsize=10
)
fig.tight_layout()
out = os.path.join(FINAL_DIR, 'class_comparison.png')
fig.savefig(out, dpi=150, bbox_inches='tight')
plt.close(fig)
print(f'Saved: {out}')

# ------------------------------------------------------------------
# FSC curves PNG
# ------------------------------------------------------------------
fsc_files = [os.path.join(FINAL_DIR, 'fsc', f'fsc_class0{c}.txt') for c in [1, 2]]
if all(os.path.exists(p) for p in fsc_files):
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['#2196F3', '#F44336']
    for c in [1, 2]:
        data_fsc = np.loadtxt(fsc_files[c-1], skiprows=1)
        shells, fsc_vals = data_fsc[:, 0], data_fsc[:, 1]
        res_str = f'{res_ang[c]:.1f} Å' if c in res_ang else ''
        ax.plot(shells, fsc_vals, color=colors[c-1], linewidth=2,
                label=f'Class {c}  (n={class_counts[c]}, res={res_str})')
        # Mark resolution threshold
        if c in res_ang:
            res_shell = PIXEL_ANG / res_ang[c]
            ax.axvline(res_shell, color=colors[c-1], linestyle=':', alpha=0.6)
    ax.axhline(0.5, color='gray', linestyle='--', linewidth=1, label='FSC=0.5')
    ax.axhline(0.143, color='lightgray', linestyle=':', linewidth=1, label='FSC=0.143')
    ax2 = ax.twiny()
    xticks = ax.get_xticks()
    xticks = xticks[(xticks > 0) & (xticks <= 0.5)]
    ax2.set_xticks(xticks)
    ax2.set_xticklabels([f'{PIXEL_ANG/x:.0f}' if x > 0 else '' for x in xticks], fontsize=8)
    ax2.set_xlabel('Resolution (Å)', fontsize=9)
    ax.set_xlabel('Spatial frequency (1/vox)', fontsize=10)
    ax.set_ylabel('FSC', fontsize=10)
    ax.set_title('Fourier Shell Correlation — split-half class averages', fontsize=11)
    ax.set_xlim(0, 0.5)
    ax.set_ylim(-0.1, 1.05)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FINAL_DIR, 'fsc', 'fsc_curves.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out}')

# ------------------------------------------------------------------
# Embeddings: t-SNE and UMAP
# ------------------------------------------------------------------
print('Running t-SNE...')
tsne = TSNE(n_components=2, metric='precomputed', perplexity=30,
            max_iter=1000, random_state=42, init='random')
emb_tsne = tsne.fit_transform(dist)

print('Running UMAP...')
reducer = umap.UMAP(n_components=2, metric='precomputed',
                    n_neighbors=15, min_dist=0.1, random_state=42)
emb_umap = reducer.fit_transform(dist)

# Save embedding coordinates
with open(os.path.join(FINAL_DIR, 'embedding_coords.csv'), 'w') as f:
    f.write('particle,class,umap1,umap2,tsne1,tsne2\n')
    for i, name in enumerate(fnames):
        f.write(f'{name},{label_arr[i]},'
                f'{emb_umap[i,0]:.6f},{emb_umap[i,1]:.6f},'
                f'{emb_tsne[i,0]:.6f},{emb_tsne[i,1]:.6f}\n')
print(f'Saved: embedding_coords.csv')

COLORS = ['#2196F3', '#F44336']

def make_embedding_plot(emb, method_name, out_path):
    fig, ax = plt.subplots(figsize=(7, 6))
    for c in [1, 2]:
        mask = label_arr == c
        ax.scatter(emb[mask, 0], emb[mask, 1],
                   c=COLORS[c-1], s=18, alpha=0.7, linewidths=0,
                   label=f'Class {c}  (n={class_counts[c]})')
    ax.set_title(
        f'Dynamo HAC — {method_name}\n'
        f'mask r={MASK_RADIUS} vox  |  cophenetic={COPH:.4f}  |  '
        f'N={sum(class_counts.values())} particles',
        fontsize=10
    )
    ax.legend(fontsize=10, markerscale=1.8)
    ax.set_xlabel('Dim 1', fontsize=10)
    ax.set_ylabel('Dim 2', fontsize=10)
    ax.text(0.02, 0.02, f'Cophenetic correlation: {COPH:.4f}',
            transform=ax.transAxes, fontsize=9, color='gray',
            verticalalignment='bottom')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved: {out_path}')

make_embedding_plot(emb_umap, 'UMAP', os.path.join(FINAL_DIR, 'embedding_umap.png'))
make_embedding_plot(emb_tsne, 't-SNE', os.path.join(FINAL_DIR, 'embedding_tsne.png'))

# ------------------------------------------------------------------
# parameters.json
# ------------------------------------------------------------------
params = {
    "algorithm": "HAC (Hierarchical Ascending Classification)",
    "package": "Dynamo v1.1.558",
    "n_particles": int(len(fnames)),
    "box_size_voxels": 80,
    "pixel_size_angstrom": PIXEL_ANG,
    "mask_type": "spherical",
    "mask_radius_voxels": MASK_RADIUS,
    "mask_radius_angstrom": round(MASK_RADIUS * PIXEL_ANG, 2),
    "mask_active_voxels": 2144,
    "mask_active_fraction": 0.0042,
    "linkage": "Ward",
    "distance_metric": "1 - Pearson_CC",
    "n_classes": 2,
    "missing_wedge_correction": False,
    "cophenetic_correlation": COPH,
    "class_sizes": class_counts,
    "resolution_fsc05_angstrom": res_ang,
    "resolution_fsc0143_angstrom": res_ang_0143,
}
with open(os.path.join(FINAL_DIR, 'parameters.json'), 'w') as f:
    json.dump(params, f, indent=2)
print(f'Saved: parameters.json')
print('\nAll outputs generated.')
