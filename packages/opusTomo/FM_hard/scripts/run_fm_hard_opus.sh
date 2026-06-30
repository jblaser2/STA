#!/bin/bash
# OPUS-TOMO classification of FM_hard (813 particles, 96^3, k=3, 3 classes).
# Run from STA repo root.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
PROJ_DIR="$SCRIPT_DIR/opus_project_fm_hard"
LOG="$PROJ_DIR/run.log"

PARTICLE_DIR="$HOME/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full"
GT_LABELS="$PARTICLE_DIR/labels.csv"
OUT_DIR="$REPO_ROOT/outputs/FM_hard/opus"

K=3
EPOCH=""

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

mkdir -p "$PROJ_DIR" "$OUT_DIR"
echo "" >> "$LOG"
log "Pipeline started (K=$K)"

if [[ ! -f "$PROJ_DIR/particles.star" ]]; then
    log "=== Step 1: Write STAR file ==="
    python "$SCRIPT_DIR/setup_fm_hard_opus.py" "$PROJ_DIR" 2>&1 | tee -a "$LOG"
else
    log "Step 1: particles.star exists."
fi

if [[ ! -f "$PROJ_DIR/pose_euler.pkl" ]]; then
    log "=== Step 2: Create pose pickle ==="
    dsd parse_pose_star "$PROJ_DIR/particles.star" -D 96 --Apix 13.33 \
        -o "$PROJ_DIR/pose_euler.pkl" 2>&1 | tee -a "$LOG"
else
    log "Step 2: pose_euler.pkl exists."
fi

if [[ ! -f "$PROJ_DIR/mask.mrc" ]]; then
    log "=== Step 3: Consensus + threshold mask ==="
    conda run -n eman2 python3 - <<'PYEOF' 2>&1 | tee -a "$LOG"
import os, glob
import numpy as np, mrcfile
from scipy.ndimage import binary_dilation

proj_dir = os.path.expanduser("~/Research/STA/packages/opusTomo/FM_hard/scripts/opus_project_fm_hard")
pdir     = os.path.expanduser("~/Research/synthetic_sta/motor_hard/subtomos/merged_ABC_full")
APIX = 13.329

files = sorted(glob.glob(os.path.join(pdir, "subtomo_*.mrc")))
print(f"Averaging {len(files)} volumes...")
acc = None
for f in files:
    with mrcfile.open(f, permissive=True) as m:
        v = m.data.astype(np.float32)
    acc = v if acc is None else acc + v
avg = acc / len(files)

with mrcfile.new(os.path.join(proj_dir, "consensus.mrc"), overwrite=True) as m:
    m.set_data(avg); m.voxel_size = APIX

thresh = avg.mean() + avg.std()
mask = binary_dilation((avg > thresh).astype(np.float32), iterations=2).astype(np.float32)
with mrcfile.new(os.path.join(proj_dir, "mask.mrc"), overwrite=True) as m:
    m.set_data(mask); m.voxel_size = APIX
print(f"Threshold mask ({100*mask.mean():.1f}% voxels)")
PYEOF
else
    log "Step 3: mask.mrc exists."
fi

OUTDIR="$PROJ_DIR/output"
if ls "$OUTDIR"/z.*.pkl 2>/dev/null | grep -q .; then
    log "Step 4: z.*.pkl exists — skipping training."
else
    mkdir -p "$OUTDIR"
    log "=== Step 4: Train OPUS-ET (20 epochs) ==="
    dsd train_tomo "$PROJ_DIR/particles.star" \
        --poses "$PROJ_DIR/pose_euler.pkl" \
        -n 20 -b 16 --zdim 8 --zaffinedim 0 --lr 1e-4 \
        --beta-control 1.0 --lamb 0 \
        -o "$OUTDIR" -r "$PROJ_DIR/mask.mrc" \
        --downfrac 1.0 --templateres 128 --angpix 13.33 \
        --datadir "$PARTICLE_DIR" \
        --ctfalpha 0. --ctfbeta 0. \
        --split "$OUTDIR/split.pkl" 2>&1 | tee -a "$LOG"
fi

EPOCH=$(ls "$OUTDIR"/z.*.pkl 2>/dev/null | sed 's/.*z\.\([0-9]*\)\.pkl/\1/' | sort -n | tail -1)
[[ -n "$EPOCH" ]] || { log "ERROR: No z.*.pkl"; exit 1; }
ANALYZE_DIR="$OUTDIR/analyze.${EPOCH}"

if [[ ! -d "$ANALYZE_DIR/kmeans${K}" ]]; then
    log "=== Step 5: Latent analysis (epoch=$EPOCH K=$K) ==="
    dsdsh analyze "$OUTDIR" "$EPOCH" 2 "$K" 2>&1 | tee -a "$LOG"
fi

if [[ ! -f "$ANALYZE_DIR/kmeans${K}/reference0.mrc" ]]; then
    log "=== Step 6: Generate class volumes ==="
    dsdsh eval_vol "$OUTDIR" "$EPOCH" kmeans "$K" 13.33 2>&1 | tee -a "$LOG"
fi

RESULT_CSV="$OUT_DIR/opus_fm_hard_k${K}.csv"
log "=== Step 7: Extract labels ==="
conda run -n eman2 python3 - <<PYEOF 2>&1 | tee -a "$LOG"
import os, pickle, csv
from collections import Counter
from sklearn.metrics import adjusted_rand_score

analyze_dir = "${ANALYZE_DIR}"
star_path   = "${PROJ_DIR}/particles.star"
gt_csv      = "${GT_LABELS}"
result_csv  = "${RESULT_CSV}"
k           = ${K}

labels = pickle.load(open(os.path.join(analyze_dir, f"kmeans{k}", "labels.pkl"), "rb"))
filenames = []
with open(star_path) as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith(('#','data','loop','_')):
            p = s.split()
            if p: filenames.append(os.path.basename(p[0]))

gt_rows = list(__import__('csv').DictReader(open(gt_csv)))
gt_map  = {r['file']: r['label'] for r in gt_rows}
files   = [r['file'] for r in gt_rows]

os.makedirs(os.path.dirname(os.path.abspath(result_csv)), exist_ok=True)
with open(result_csv, 'w', newline='') as f:
    w = __import__('csv').writer(f); w.writerow(['file','pred_label'])
    for fn, lb in zip(files, labels):
        w.writerow([fn, int(lb)])

ari = adjusted_rand_score([gt_map[f] for f in files], list(labels))
print(f"OPUS-TOMO FM_hard k={k}: ARI={ari:.3f}  {dict(sorted(Counter(int(l) for l in labels).items()))}")
print(f"  -> {result_csv}")
PYEOF

log "=== Pipeline complete. ==="
