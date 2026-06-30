#!/bin/bash
# TomoFlow FM_hard (813 particles, 96^3, k=3, 3 assembly classes).
# Downsample 96->48 (factor=2); mask downsampled to match.
set -euo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS/../../../.." && pwd)"
PARTICLES="$HOME/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full"
MASK="$HOME/Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc"
GT_LABELS="$PARTICLES/labels.csv"
OUTDIR="$HOME/Research/tomoflow_fm_hard"
K=3

log() { echo "[$(date '+%H:%M:%S')] $*"; }
log "=== TomoFlow FM_hard k=$K ==="

source ~/miniforge3/etc/profile.d/conda.sh
conda activate tomoflow

if [[ ! -f "$OUTDIR/of_features.npy" ]]; then
    log "Step 1: Downsampling mask 96->48..."
    MASK_DS="$OUTDIR/mask48.mrc"
    mkdir -p "$OUTDIR"
    conda run -n eman2 python3 -c "
import numpy as np, mrcfile
from scipy.ndimage import zoom
with mrcfile.open('$MASK', permissive=True) as m: d=m.data.astype(np.float32)
d48 = zoom(d, 0.5, order=1)
with mrcfile.new('$MASK_DS', overwrite=True) as m: m.set_data(d48); m.voxel_size=26.66
print('mask48:', d48.shape, 'nonzero:', (d48>0.1).sum())
"
    log "Step 1: Computing optical flow (downsample=2 -> 48^3, ~10 min)..."
    python ~/Research/tomoflow_work/tomoflow_run.py \
        --subtomo-dir "$PARTICLES" \
        --outdir "$OUTDIR" \
        --mask "$MASK_DS" \
        --downsample 2 \
        --n-components 10 \
        --gpu-id 0 \
        2>&1 | tee "$OUTDIR/tomoflow_fm_hard.log"
else
    log "Step 1: of_features.npy exists, skipping."
fi

log "Step 2: k-means (k=$K)..."
mkdir -p "$REPO_ROOT/outputs/FM_hard/tomoflow"
conda run -n eman2 python3 - <<PYEOF
import os, csv, numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from collections import Counter

outdir    = '$OUTDIR'
gt_csv    = '$GT_LABELS'
repo_root = '$REPO_ROOT'
K         = $K

emb_path = os.path.join(outdir, 'embedding.npy')
key_path = os.path.join(outdir, 'keys.txt')

if not os.path.exists(emb_path):
    print("ERROR: embedding.npy not found"); exit(1)

emb  = np.load(emb_path)
with open(key_path) as f:
    keys = [l.strip() for l in f if l.strip()]

rows   = list(csv.DictReader(open(gt_csv)))
gt_map = {r['file']: r['label'] for r in rows}
files  = [r['file'] for r in rows]

X = StandardScaler().fit_transform(emb)
km = KMeans(n_clusters=K, n_init=20, random_state=42).fit_predict(X)
key_to_pred = {k+'.mrc': int(km[i]) for i,k in enumerate(keys)}

gt_list = [gt_map[f] for f in files]
pr_list = [key_to_pred.get(f, 0) for f in files]
ari = adjusted_rand_score(gt_list, pr_list)
print(f'TomoFlow FM_hard k={K}: ARI={ari:.3f}  classes={dict(sorted(Counter(km).items()))}')

out = os.path.join(repo_root, f'outputs/FM_hard/tomoflow/tomoflow_fm_hard_k{K}.csv')
with open(out,'w',newline='') as f:
    w=csv.writer(f); w.writerow(['file','pred_label'])
    for fname, lbl in zip(files, pr_list):
        w.writerow([fname, lbl])
print(f'Saved: {out}')
PYEOF
log "=== Done ==="
