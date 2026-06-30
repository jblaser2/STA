#!/bin/bash
# ProTomo FM_hard classification — 813 GT-aligned particles (k=3, no junk).
# Run from STA repo root or from ~/Research/protomo/motor_hard/process/.
set -e
source ~/Applications/protomo-3.1.0/setup.sh

STA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
PROCESS="$HOME/Research/protomo/motor_hard/process"
PREPARE="$HOME/Research/protomo/motor_hard/prepare"
GT_LABELS="$HOME/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full/labels.csv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MKLLIB="/usr/local/MATLAB/R2024a/bin/glnxa64/mkl.so /usr/local/MATLAB/R2024a/sys/os/glnxa64/libiomp5.so"
DATASET="$PREPARE/dataset.i3i"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# Setup if needed
if [ ! -f "$DATASET" ]; then
    log "Running setup first..."
    bash "$SCRIPT_DIR/setup_fm_hard_protomo.sh"
fi

# Copy param-template and run script to process/
cp "$SCRIPT_DIR/param-template.sh" "$PROCESS/param-template.sh"
source "$PROCESS/param-template.sh"

cd "$PROCESS"

log "=== ProTomo FM_hard (813p, k=3) ==="

log "[1/6] Initialize cycle-000"
# Don't pre-create cycle-000 — subvolinitial.sh creates it itself and copies param.sh
# If cycle-000/fmh-000-raw.i3i already exists, skip initialization
if [ ! -f "$PROCESS/cycle-000/fmh-000-raw.i3i" ]; then
    [ -d "$PROCESS/cycle-000" ] && rm -rf "$PROCESS/cycle-000"
    subvolinitial.sh "$DATASET"
else
    log "  cycle-000 already initialized, skipping"
fi

log "[2/6] Global average"
subvolglobalaverage.sh 0

log "[3/6] Bypass alignment: copy raw -> mra (GT-aligned particles)"
cp -p cycle-000/fmh-000-raw.i3i cycle-000/fmh-000-mra.i3i

log "[4/6] SVD (MKL preload)"
LD_PRELOAD="$MKLLIB" subvolsvd.sh 0

log "[5/6] HAC clustering (k=3)"
LD_PRELOAD="$MKLLIB" subvolhac.sh 0

log "[6/6] Class averages"
subvolclassaverage.sh 0
subvolclassalign.sh 0 || true  # ignore alignment errors

log "=== ProTomo FM_hard done. Results in $PROCESS/cycle-000/ ==="

# Extract and score (no junk class in FM_hard: use --include-junk to keep all 3 classes)
log "Scoring..."
mkdir -p "$STA_DIR/outputs/FM_hard/protomo"
~/miniforge3/bin/conda run -n eman2 python3 "$STA_DIR/scripts/eval/extract_protomo_classes.py" \
    --i3i    "$PROCESS/cycle-000/fmh-000-class.i3i" \
    --stacks "$PREPARE/stacks" \
    --out    "$STA_DIR/outputs/FM_hard/protomo/protomo_fm_hard_k3.csv" \
    --include-junk 2>&1 || \
    log "WARNING: extract_protomo_classes.py failed — check manually"

# Score ARI against GT
~/miniforge3/bin/conda run -n eman2 python3 -c "
import csv, os
from sklearn.metrics import adjusted_rand_score
from collections import Counter

pred_csv = '$STA_DIR/outputs/FM_hard/protomo/protomo_fm_hard_k3.csv'
gt_csv   = '$GT_LABELS'

if not os.path.exists(pred_csv):
    print('ERROR: pred_csv not found'); exit(1)

pred_rows = list(csv.DictReader(open(pred_csv)))
gt_rows   = list(csv.DictReader(open(gt_csv)))
gt_map    = {r['file']: r['label'] for r in gt_rows}

pred_map = {r['file']: int(r['pred_label']) for r in pred_rows}
files    = [r['file'] for r in gt_rows]
gt_list  = [gt_map[f] for f in files]
pr_list  = [pred_map.get(f, 0) for f in files]

ari = adjusted_rand_score(gt_list, pr_list)
print(f'ProTomo FM_hard k=3: ARI={ari:.3f}  classes={dict(sorted(Counter(pr_list).items()))}')
" 2>&1
