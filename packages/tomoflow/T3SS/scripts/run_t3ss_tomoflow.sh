#!/bin/bash
# TomoFlow on T3SS injectisome (415 particles, 48^3).
# Runs on tomoflow conda env (pycuda + farneback3d).
# Downsample 48->24 (factor=2) for speed; mask applied before OF.
set -euo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS/../../../.." && pwd)"
PARTICLES="$HOME/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss"
MASK="$HOME/Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc"
GT_LABELS="$PARTICLES/labels.csv"
OUTDIR="$HOME/Research/tomoflow_t3ss"
K=${1:-3}

log() { echo "[$(date '+%H:%M:%S')] $*"; }
log "=== TomoFlow T3SS k=$K ==="

source ~/miniforge3/etc/profile.d/conda.sh
conda activate tomoflow

# Step 1: Compute optical-flow features
if [[ ! -f "$OUTDIR/of_features.npy" ]]; then
    log "Step 1: Preparing downsampled mask (48->24)..."
    MASK_DS="$OUTDIR/mask24.mrc"
    mkdir -p "$OUTDIR"
    conda run -n eman2 python3 -c "
import numpy as np, mrcfile
from scipy.ndimage import zoom
with mrcfile.open('$MASK', permissive=True) as m: d=m.data.astype(np.float32)
d24 = zoom(d, 0.5, order=1)
with mrcfile.new('$MASK_DS', overwrite=True) as m: m.set_data(d24); m.voxel_size=26.66
print('mask24:', d24.shape, 'nonzero:', (d24>0.1).sum())
"
    log "Step 1: Computing optical flow (downsample=2, ~5 min)..."
    python ~/Research/tomoflow_work/tomoflow_run.py \
        --subtomo-dir "$PARTICLES" \
        --outdir "$OUTDIR" \
        --mask "$MASK_DS" \
        --downsample 2 \
        --n-components 10 \
        --gpu-id 0 \
        2>&1 | tee "$OUTDIR/tomoflow_t3ss.log"
else
    log "Step 1: of_features.npy exists, skipping."
fi

# Step 2: k-means + score
log "Step 2: k-means (k=$K)..."
conda run -n eman2 python3 - <<PYEOF
import os, csv, numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from collections import Counter

outdir = '$OUTDIR'; gt_csv = '$GT_LABELS'; K = $K
repo_root = '$REPO_ROOT'

emb = np.load(os.path.join(outdir,'embedding.npy'))
with open(os.path.join(outdir,'keys.txt')) as f:
    keys = [l.strip() for l in f if l.strip()]

rows = list(csv.DictReader(open(gt_csv)))
gt_map = {r['file']: r['label'] for r in rows}

km = KMeans(n_clusters=K, n_init=20, random_state=42).fit_predict(emb)
signal = [r['file'] for r in rows if gt_map[r['file']] in ('class_B','class_C')]
key_to_pred = {k+'.mrc': int(km[i]) for i,k in enumerate(keys)}
gt_sig = [gt_map[f] for f in signal]
pr_sig = [key_to_pred.get(f, 0) for f in signal]
ari = adjusted_rand_score(gt_sig, pr_sig)
print(f'TomoFlow T3SS k={K}: ARI(B/C)={ari:.3f}  classes={dict(sorted(Counter(km).items()))}')

# Save CSV
out = os.path.join(repo_root, f'outputs/T3SS/tomoflow/tomoflow_t3ss_k{K}.csv')
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out,'w',newline='') as f:
    w=csv.writer(f); w.writerow(['file','pred_label'])
    for row in rows: w.writerow([row['file'], key_to_pred.get(row['file'],0)])
print(f'Saved: {out}')
PYEOF
log "=== Done ==="
