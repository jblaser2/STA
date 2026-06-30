#!/bin/bash
# STOPGAP PCA + k-means on FM_hard (813 particles, 96^3, 13.33 A/px, k=3).
# 3 classes: base / basal_body / mature (no junk).
set -euo pipefail

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPTS/../../../.." && pwd)"
SG_HOME="$REPO_ROOT/packages/STOPGAP"
SG_TOOLBOX="$SG_HOME/sg_toolbox"
export STOPGAPHOME="$SG_HOME/exec"
PARTICLES="$HOME/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full"
ROOTDIR="$HOME/Research/stopgap_fm_hard"
MASK_MRC="$HOME/Research/synthetic_sta/motor_hard/maps/diff_mask_hard.mrc"
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

log "=== STOPGAP FM_hard PCA ==="
mkdir -p "$ROOTDIR"
cd "$ROOTDIR"

# Step 1: Build inputs (motl + symlinks)
if [[ ! -f "$ROOTDIR/lists/allmotl_1.star" ]]; then
    log "Step 1: Build motl + symlinks..."
    mlbatch "addpath(genpath('$SG_TOOLBOX')); addpath('$REPO_ROOT/packages/STOPGAP/T3SS/scripts'); build_inputs_t3ss('$PARTICLES','$ROOTDIR'); exit;"
fi

# Step 2: Build wedgelist
if [[ ! -f "$ROOTDIR/lists/wedgelist.star" ]]; then
    log "Step 2: Build wedgelist..."
    mlbatch "addpath(genpath('$SG_TOOLBOX')); addpath(genpath('$REPO_ROOT/packages/STOPGAP/T4P/scripts')); build_wedgelist('$ROOTDIR',-60,60,3); exit;"
fi

# Step 3: Copy mask
mkdir -p "$ROOTDIR/masks"
if [[ ! -f "$ROOTDIR/masks/mask_fm_hard.mrc" ]]; then
    log "Step 3: Copy mask..."
    cp "$MASK_MRC" "$ROOTDIR/masks/mask_fm_hard.mrc"
fi

# Step 4: Global average
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
    m.set_data(avg); m.voxel_size=13.329
print('Global avg -> ref_1.mrc  shape=%s' % str(avg.shape))
"
fi

# Step 5: PCA aux files. Box=96 -> Nyquist=48. lp_rad=20 (~0.42 Nyquist), hp_rad=2
if [[ ! -f "$ROOTDIR/lists/filter_list.star" ]]; then
    log "Step 5: PCA aux (filter_list + pca_settings)..."
    mlbatch "addpath(genpath('$SG_TOOLBOX')); addpath(genpath('$REPO_ROOT/packages/STOPGAP/T4P/scripts')); build_pca_aux('$ROOTDIR',20,2,2,2); exit;"
fi

# Initialize STOPGAP folder structure
if [[ ! -d "$ROOTDIR/comm" ]]; then
    log "Step 5b: Initializing STOPGAP folder structure..."
    "$STOPGAPHOME/bin/stopgap_initialize_folder.sh" pca
fi

# Step 6: Run STOPGAP PCA
mkdir -p "$ROOTDIR/params" "$ROOTDIR/pca" "$ROOTDIR/rvol" "$ROOTDIR/logs"
ROOTS="${ROOTDIR%/}/"
MPIRUN="/usr/lib64/openmpi/bin/mpiexec"

sg_run() {
    local task="$1"
    local paramfile="params/pca_param.star"
    "$STOPGAPHOME/bin/stopgap_parser.sh" pca \
        param_name "$paramfile" \
        pca_task "$task" \
        rootdir "$ROOTS" \
        tempdir none commdir none rawdir none refdir none \
        maskdir none listdir none subtomodir none rvoldir none pcadir none metadir none \
        iteration "$ITER" \
        motl_name allmotl wedgelist_name wedgelist.star binning 1 \
        ref_name ref mask_name mask_fm_hard.mrc subtomo_name subtomo \
        rvol_name rvol rwei_name rwei \
        filtlist_name filter_list.star data_type awpd \
        ccmat_name ccmatrix covar_name covar n_eigs 20 \
        eigenvol_name eigenvol eigenfac_name eigenfac eigenval_name eigenval \
        apply_laplacian 0 symmetry c1 fthresh 200 \
        2>&1 | tee "$ROOTDIR/logs/pca_parse_${task}.log"
    "$MPIRUN" -np "$N_CORES" "$STOPGAPHOME/bin/stopgap_mpi_slurm.sh" \
        "$ROOTS" "$paramfile" "$N_CORES" 0 local >> "$ROOTDIR/logs/${task}.log" 2>&1
}

for task in rot_vol calc_ccmat calc_pca_ccmat; do
    log "Step 6.$task..."
    sg_run "$task"
    log "  $task done"
done

# Step 7: k-means on eigenfac
log "Step 7: k-means scoring..."
mkdir -p "$REPO_ROOT/outputs/FM_hard/stopgap"
conda run -n eman2 python3 - <<PYEOF
import os, csv, numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from collections import Counter

rootdir   = '$ROOTDIR'; repo_root = '$REPO_ROOT'; gt_csv = '$GT_LABELS'; iter = $ITER
eigenfac  = os.path.join(rootdir, 'pca', f'eigenfac_{iter}.csv')

if not os.path.exists(eigenfac):
    print(f"ERROR: {eigenfac} not found"); exit(1)

E = np.loadtxt(eigenfac, delimiter=',')
print(f"Eigenfac shape: {E.shape}")

rows   = list(csv.DictReader(open(gt_csv)))
gt_map = {r['file']: r['label'] for r in rows}
files  = [r['file'] for r in rows]

for k in [3]:
    nc = min(17, E.shape[1])
    km = KMeans(n_clusters=k, n_init=20, random_state=42).fit_predict(E[:, :nc])
    ari = adjusted_rand_score([gt_map[f] for f in files], km)
    print(f"STOPGAP FM_hard k={k}: ARI={ari:.3f}  classes={dict(sorted(Counter(km).items()))}")
    pred_csv = os.path.join(repo_root, f'outputs/FM_hard/stopgap/stopgap_fm_hard_k{k}.csv')
    with open(pred_csv,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['file','pred_label'])
        for fname, lbl in zip(files, km): w.writerow([fname, int(lbl)])
    print(f"  -> {pred_csv}")
PYEOF

log "=== STOPGAP FM_hard done ==="
