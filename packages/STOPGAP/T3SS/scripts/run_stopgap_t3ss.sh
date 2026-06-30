#!/bin/bash
# STOPGAP PCA + k-means on T3SS injectisome (415 particles, 48^3, 13.33 A/px).
# Junk protocol: k=2 and k=3 runs. Scores B vs C ARI (junk=noise).
set -euo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS/../../../.." && pwd)"
SG_HOME="$REPO_ROOT/packages/STOPGAP"
SG_TOOLBOX="$SG_HOME/sg_toolbox"
export STOPGAPHOME="$SG_HOME/exec"
PARTICLES="$HOME/Research/synthetic_sta/injectisome/subtomos/merged_BC_t3ss"
ROOTDIR="$HOME/Research/stopgap_t3ss"
MASK_MRC="$HOME/Research/synthetic_sta/injectisome/maps/mask_t3ss.mrc"
GT_LABELS="$PARTICLES/labels.csv"
N_CORES=16
ITER=1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
mlbatch() {
    local TMPMAT=$(mktemp /tmp/sg_ml_XXXXXX.m)
    echo "$1" > "$TMPMAT"
    ~/Applications/matlab/bin/matlab -nodisplay -nosplash -batch "run('$TMPMAT')"
    rm -f "$TMPMAT"
}

log "=== STOPGAP T3SS PCA ==="
cd "$ROOTDIR"

# Step 1: Build inputs
if [[ ! -f "$ROOTDIR/lists/allmotl_1.star" ]]; then
    log "Step 1: Build motl + symlinks..."
    mlbatch "addpath(genpath('$SG_TOOLBOX')); addpath('$SCRIPTS'); build_inputs_t3ss('$PARTICLES','$ROOTDIR'); exit;"
fi

# Step 2: Build wedgelist (tilt range -60:3:60)
if [[ ! -f "$ROOTDIR/lists/wedgelist.star" ]]; then
    log "Step 2: Build wedgelist..."
    mlbatch "addpath(genpath('$SG_TOOLBOX')); addpath(genpath('$REPO_ROOT/packages/STOPGAP/T4P/scripts')); build_wedgelist('$ROOTDIR',-60,60,3); exit;"
fi

# Step 3: Copy mask to mask/ dir
mkdir -p "$ROOTDIR/mask"
if [[ ! -f "$ROOTDIR/mask/mask_t3ss.mrc" ]]; then
    log "Step 3: Copy mask..."
    cp "$MASK_MRC" "$ROOTDIR/mask/mask_t3ss.mrc"
fi

# Step 4: Global average reference
mkdir -p "$ROOTDIR/ref"
if [[ ! -f "$ROOTDIR/ref/ref_1.mrc" ]]; then
    log "Step 4: Build global average..."
    conda run -n eman2 python3 -c "
import os, glob, numpy as np, mrcfile
pdir = '$PARTICLES'
files = sorted(glob.glob(os.path.join(pdir,'subtomo_*.mrc')))
acc = None
for f in files:
    with mrcfile.open(f,permissive=True) as m: v = m.data.astype(np.float32)
    acc = v.copy() if acc is None else acc + v
avg = acc / len(files)
os.makedirs('$ROOTDIR/ref', exist_ok=True)
with mrcfile.new('$ROOTDIR/ref/ref_1.mrc',overwrite=True) as m:
    m.set_data(avg); m.voxel_size=13.33
print('Global avg -> ref_1.mrc  shape=%s' % str(avg.shape))
"
fi

# Step 5: PCA auxiliary files (filter_list.star + pca_settings.txt)
# Box=48 -> Nyquist=24px. lp_rad=10 (~0.42 Nyquist), hp_rad=1
if [[ ! -f "$ROOTDIR/lists/filter_list.star" ]]; then
    log "Step 5: PCA aux (filter_list + pca_settings)..."
    mlbatch "addpath(genpath('$SG_TOOLBOX')); addpath(genpath('$REPO_ROOT/packages/STOPGAP/T4P/scripts')); build_pca_aux('$ROOTDIR',10,2,1,2); exit;"
fi

# Step 6: Run STOPGAP PCA (3 tasks: rot_vol, calc_ccmat, calc_pca_ccmat)
mkdir -p "$ROOTDIR/params" "$ROOTDIR/pca"
ROOTS="${ROOTDIR%/}/"

sg_run() {
    # Run a STOPGAP param file via local MPI
    local paramfile="$1"
    mpiexec -np $N_CORES "$STOPGAPHOME/bin/stopgap_mpi_slurm.sh" \
        "$ROOTDIR" "$paramfile" $N_CORES 0 local
}

for task in rot_vol calc_ccmat calc_pca_ccmat; do
    log "Step 6.$task: running..."
    "$STOPGAPHOME/bin/stopgap_pca_parser.sh" \
        param_name params/pca_param.star \
        pca_task "$task" \
        rootdir "$ROOTS" \
        tempdir none commdir none rawdir none refdir none \
        maskdir none listdir none subtomodir none rvoldir none pcadir none metadir none \
        iteration $ITER \
        motl_name allmotl wedgelist_name wedgelist.star binning 1 \
        ref_name ref mask_name mask_t3ss.mrc subtomo_name subtomo \
        rvol_name rvol rwei_name rwei \
        filtlist_name filter_list.star data_type awpd \
        ccmat_name ccmatrix covar_name covar n_eigs 10 \
        eigenvol_name eigenvol eigenfac_name eigenfac eigenval_name eigenval \
        apply_laplacian 0 symmetry c1 fthresh 200 \
        2>&1 | tee "logs/pca_parse_${task}.log"
    sg_run params/pca_param.star 2>&1 | tee "logs/pca_run_${task}.log"
done

if [[ ! -f "$ROOTDIR/pca/eigenval_1.csv" ]]; then
    log "ERROR: eigenval_1.csv not found after PCA — check logs/"
    exit 1
fi
log "PCA complete. eigenval_1.csv found."

# Step 7: k-means (k=2 and k=3) using first 10 PCs from filter 1
for K in 2 3; do
    log "Step 7: k-means (k=$K)..."
    mlbatch "
addpath(genpath('$SG_TOOLBOX'));
addpath(genpath('$REPO_ROOT/packages/STOPGAP/T4P/scripts'));
sg_pca_kmeans_cluster_fn('$ROOTDIR','params/pca_param.star',[1 1;1 2;1 3],[${K}]);
exit;"
done

# Step 8: Score
for K in 2 3; do
    log "Step 8: Score k=$K..."
    PREDSTAR="$ROOTDIR/lists/allmotl_pca_k${K}_${ITER}.star"
    if [[ ! -f "$PREDSTAR" ]]; then
        log "  WARNING: $PREDSTAR not found, skipping k=$K"
        continue
    fi

    # Extract class assignments from allmotl star file
    conda run -n eman2 python3 - <<PYEOF
import os, csv, re
from sklearn.metrics import adjusted_rand_score
from collections import Counter

star_path = '$PREDSTAR'
gt_csv    = '$GT_LABELS'
repo_out  = '$REPO_ROOT/outputs/T3SS/stopgap'
os.makedirs(repo_out, exist_ok=True)

# Parse STAR file: find 'class' column index then read data rows
lines = open(star_path).readlines()
# Find data block
col_names = []
data_lines = []
in_header = False
for l in lines:
    l = l.strip()
    if l.startswith('_rln') or l.startswith('_sg'):
        col_names.append(l.split()[0])
    elif l and not l.startswith('#') and not l.startswith('data') and not l.startswith('loop') and col_names:
        data_lines.append(l.split())

# Find class and motl_idx columns
try:
    ci = col_names.index('_sgMotlClass')
except ValueError:
    ci = col_names.index([c for c in col_names if 'class' in c.lower()][0])
try:
    oi = col_names.index('_sgMotlIdx')
except ValueError:
    oi = 0

print('Star columns: %s' % col_names[:8])
print('Data rows: %d' % len(data_lines))

gt_rows = list(csv.DictReader(open(gt_csv)))
gt_list = [r['file'] for r in gt_rows]

pred_labels = []
for row in data_lines:
    if len(row) > ci:
        pred_labels.append(int(row[ci]))
    else:
        pred_labels.append(0)

if len(pred_labels) != len(gt_rows):
    print('WARNING: pred_labels=%d gt_rows=%d -- mismatched' % (len(pred_labels), len(gt_rows)))
    # Truncate or pad
    pred_labels = pred_labels[:len(gt_rows)]

gt_map = {r['file']: r['label'] for r in gt_rows}
signal_idx = [i for i,r in enumerate(gt_rows) if gt_map[r['file']] in ('class_B','class_C')]
gt_sig  = [gt_map[gt_list[i]] for i in signal_idx]
pr_sig  = [pred_labels[i] for i in signal_idx]

ari = adjusted_rand_score(gt_sig, pr_sig)
print('STOPGAP T3SS k=${K}: ARI(B/C)=%.3f  classes=%s' % (ari, dict(sorted(Counter(pred_labels).items()))))

# Save predictions CSV
out_path = os.path.join(repo_out, 'stopgap_t3ss_k${K}.csv')
with open(out_path,'w',newline='') as cf:
    w=csv.writer(cf); w.writerow(['file','pred_label'])
    for i,r in enumerate(gt_rows):
        lbl = pred_labels[i] if i < len(pred_labels) else 0
        w.writerow([r['file'], lbl])
print('Saved:', out_path)
PYEOF
done

log "=== STOPGAP T3SS Done ==="
