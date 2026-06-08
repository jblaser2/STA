#!/usr/bin/env bash
# OPUS-TOMO classification of motor_easy (3-class synthetic flagellar motor).
#
# 694 GT-aligned particles (A=246, B=271, C=177), 96^3 box, 13.33 A/px.
# Produces k=3 cluster labels scored against GT in results/synthetic_scores.csv.
#
# Usage:
#   bash run_motor_easy_opus.sh              # full pipeline
#   bash run_motor_easy_opus.sh --skip-train # re-run analysis only (training done)
#   bash run_motor_easy_opus.sh --k 3       # explicit k (default: 3)
#   bash run_motor_easy_opus.sh --epoch 14  # use a specific epoch for analysis

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PROJ_DIR="$SCRIPT_DIR/opus_project_motor_easy"
LOG="$PROJ_DIR/run.log"

PARTICLE_DIR="$HOME/Research/synthetic_sta/motor_easy/production/subtomos/merged_all_aln"
GT_LABELS="$PARTICLE_DIR/labels.csv"

K=3
EPOCH=""
SKIP_TRAIN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --k)          K="$2";       shift 2 ;;
        --epoch)      EPOCH="$2";   shift 2 ;;
        --skip-train) SKIP_TRAIN=1; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
run_step() {
    local label="$1"; shift
    log "=== $label ==="
    "$@" 2>&1 | tee -a "$LOG"
    log "--- $label done ---"
    echo ""
}

source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

mkdir -p "$PROJ_DIR"
echo "" >> "$LOG"
log "Pipeline started (K=$K)"
log "Proj dir:     $PROJ_DIR"
log "Particle dir: $PARTICLE_DIR"

# ---------- Step 1: STAR file ----------
if [[ ! -f "$PROJ_DIR/particles.star" ]]; then
    run_step "Step 1: Write STAR file" python "$SCRIPT_DIR/setup_motor_easy_opus.py" "$PROJ_DIR"
else
    log "Step 1: particles.star exists, skipping."
fi

# ---------- Step 2: Pose pickle ----------
if [[ ! -f "$PROJ_DIR/pose_euler.pkl" ]]; then
    run_step "Step 2: Create pose pickle" \
        dsd parse_pose_star "$PROJ_DIR/particles.star" \
            -D 96 --Apix 13.33 -o "$PROJ_DIR/pose_euler.pkl"
else
    log "Step 2: pose_euler.pkl exists, skipping."
fi

# ---------- Step 3: Consensus + threshold mask ----------
if [[ ! -f "$PROJ_DIR/mask.mrc" ]]; then
    log "=== Step 3: Consensus average + threshold mask ==="
    python - <<PYEOF 2>&1 | tee -a "$LOG"
import os, glob, sys
import numpy as np
import mrcfile
from scipy.ndimage import binary_dilation

proj_dir     = '$PROJ_DIR'
particle_dir = '$PARTICLE_DIR'
APIX         = 13.33
SIGMA_THRESH = 1.0
DILATE_ITERS = 2

files = sorted(glob.glob(os.path.join(particle_dir, 'subtomo_*.mrc')))
if not files:
    sys.exit(f'ERROR: No subtomo_*.mrc in {particle_dir}')

print(f'Averaging {len(files)} volumes ...')
acc = None
for i, f in enumerate(files):
    if i % 100 == 0:
        print(f'  {i}/{len(files)}')
    with mrcfile.open(f, permissive=True) as m:
        v = m.data.astype(np.float32)
    acc = v.copy() if acc is None else acc + v
avg = acc / len(files)

consensus_out = os.path.join(proj_dir, 'consensus.mrc')
with mrcfile.new(consensus_out, overwrite=True) as m:
    m.set_data(avg)
    m.voxel_size = APIX
print(f'Consensus map -> {consensus_out}')

thresh = avg.mean() + SIGMA_THRESH * avg.std()
mask   = (avg > thresh).astype(np.float32)
mask   = binary_dilation(mask, iterations=DILATE_ITERS).astype(np.float32)

mask_out = os.path.join(proj_dir, 'mask.mrc')
with mrcfile.new(mask_out, overwrite=True) as m:
    m.set_data(mask)
    m.voxel_size = APIX

frac = 100 * mask.mean()
print(f'Threshold mask ({frac:.1f}% voxels, sigma={SIGMA_THRESH}) -> {mask_out}')
PYEOF
    log "--- Step 3 done ---"
    echo ""
else
    log "Step 3: mask.mrc exists, skipping."
fi

# ---------- Step 4: Training ----------
OUTDIR="$PROJ_DIR/output"
if [[ $SKIP_TRAIN -eq 1 ]]; then
    log "Step 4: Training skipped (--skip-train)."
elif ls "$OUTDIR"/z.*.pkl 2>/dev/null | grep -q .; then
    log "Step 4: z.*.pkl exists, skipping training."
else
    mkdir -p "$OUTDIR"
    run_step "Step 4: Train OPUS-ET (20 epochs)" \
        dsd train_tomo "$PROJ_DIR/particles.star" \
            --poses "$PROJ_DIR/pose_euler.pkl" \
            -n 20 \
            -b 16 \
            --zdim 8 \
            --zaffinedim 0 \
            --lr 1e-4 \
            --beta-control 1.0 \
            --lamb 0 \
            -o "$OUTDIR" \
            -r "$PROJ_DIR/mask.mrc" \
            --downfrac 1.0 \
            --templateres 128 \
            --angpix 13.33 \
            --datadir "$PARTICLE_DIR" \
            --ctfalpha 0. --ctfbeta 0. \
            --split "$OUTDIR/split.pkl"
fi

# ---------- Auto-detect last epoch ----------
if [[ -z "$EPOCH" ]]; then
    EPOCH=$(ls "$OUTDIR"/z.*.pkl 2>/dev/null \
            | sed 's/.*z\.\([0-9]*\)\.pkl/\1/' \
            | sort -n | tail -1)
    [[ -n "$EPOCH" ]] || { log "ERROR: No z.*.pkl in $OUTDIR"; exit 1; }
    log "Using epoch $EPOCH for analysis."
fi

ANALYZE_DIR="$OUTDIR/analyze.${EPOCH}"

# ---------- Step 5: Latent space analysis ----------
if [[ ! -d "$ANALYZE_DIR/kmeans${K}" ]]; then
    run_step "Step 5: Latent analysis (epoch=$EPOCH K=$K)" \
        dsdsh analyze "$OUTDIR" "$EPOCH" 2 "$K"
else
    log "Step 5: $ANALYZE_DIR/kmeans${K} exists, skipping."
fi

# ---------- Step 6: Volume generation ----------
if [[ ! -f "$ANALYZE_DIR/kmeans${K}/reference0.mrc" ]]; then
    run_step "Step 6: Generate class volumes" \
        dsdsh eval_vol "$OUTDIR" "$EPOCH" kmeans "$K" 13.33
else
    log "Step 6: Volumes exist, skipping."
fi

# ---------- Step 7: Extract labels to CSV ----------
RESULT_CSV="$REPO_ROOT/outputs/opus_tomo_motor_easy_k3.csv"
log "=== Step 7: Extract labels -> $RESULT_CSV ==="
python - <<PYEOF 2>&1 | tee -a "$LOG"
import os, pickle, csv
from collections import Counter

proj_dir    = '$PROJ_DIR'
analyze_dir = '$ANALYZE_DIR'
k           = $K
result_csv  = '$RESULT_CSV'

labels_path = os.path.join(analyze_dir, f'kmeans{k}', 'labels.pkl')
star_path   = os.path.join(proj_dir, 'particles.star')

labels = pickle.load(open(labels_path, 'rb'))

filenames = []
with open(star_path) as f:
    for line in f:
        s = line.strip()
        if s and not s.startswith(('#', 'data', 'loop', '_')):
            parts = s.split()
            if parts:
                filenames.append(parts[0])

if len(filenames) != len(labels):
    raise ValueError(f'Mismatch: {len(filenames)} particles vs {len(labels)} labels')

os.makedirs(os.path.dirname(os.path.abspath(result_csv)), exist_ok=True)
with open(result_csv, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['file', 'pred_label'])
    for fn, lb in zip(filenames, labels):
        w.writerow([fn, int(lb)])

print(f'K={k} distribution: {dict(sorted(Counter(int(l) for l in labels).items()))}')
print(f'Saved {len(labels)} rows -> {result_csv}')
PYEOF
log "--- Step 7 done ---"
echo ""

# ---------- Step 8: Score against GT ----------
log "=== Step 8: Score ARI/AMI/V ==="
python "$REPO_ROOT/scripts/eval/score_synthetic.py" \
    --pred "$RESULT_CSV" \
    --gt   "$GT_LABELS" \
    --package opus-tomo \
    --dataset motor_easy \
    --k "$K" \
    --run threshold_mask \
    2>&1 | tee -a "$LOG"
log "--- Step 8 done ---"

log "Pipeline complete."
echo ""
echo "=== Results ==="
echo "  Consensus:    $PROJ_DIR/consensus.mrc"
echo "  Mask:         $PROJ_DIR/mask.mrc"
echo "  UMAP:         $ANALYZE_DIR/umap.png"
echo "  PCA:          $ANALYZE_DIR/z_pca.png"
echo "  Class vols:   $ANALYZE_DIR/kmeans${K}/reference*.mrc"
echo "  Labels CSV:   $RESULT_CSV"
echo "  Scores:       $REPO_ROOT/results/synthetic_scores.csv"
echo "  Full log:     $LOG"
