#!/usr/bin/env bash
# End-to-end unsupervised classification of pili subtomograms with OPUS-ET.
#
# Runs all pipeline steps in sequence:
#   Step 1: Create STAR file from MRC filenames
#   Step 2: Create pose pickle (zero Euler angles, z-aligned particles)
#   Step 3: Average subtomograms + create solvent mask
#   Step 4: Train OPUS-ET beta-VAE
#   Step 5: PCA + k-means + UMAP analysis
#   Step 6: Generate 3D volume per class
#   Step 7: Split STAR file by class
#
# Usage:
#   ./runClassification.sh              # run full pipeline with defaults
#   ./runClassification.sh --k 10       # use 10 clusters instead of 8
#   ./runClassification.sh --epoch 14   # analyse a specific epoch
#   ./runClassification.sh --skip-train # skip training (re-run analysis only)
#
# Outputs are written to opus_project/ alongside this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$SCRIPT_DIR/opus_project"
LOG="$PROJ_DIR/runClassification.log"

# --- Defaults ---
K=8
EPOCH=""        # auto-detect last epoch after training
SKIP_TRAIN=0

# --- Parse args ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --k)        K="$2";       shift 2 ;;
        --epoch)    EPOCH="$2";   shift 2 ;;
        --skip-train) SKIP_TRAIN=1; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# --- Helpers ---
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
log "Project dir: $PROJ_DIR"

# Step 1: STAR file
if [[ ! -f "$PROJ_DIR/particles.star" ]]; then
    run_step "Step 1: Write STAR file" python "$PROJ_DIR/01_write_star.py"
else
    log "Step 1: particles.star exists, skipping."
fi

# Step 2: Pose pickle
if [[ ! -f "$PROJ_DIR/pose_euler.pkl" ]]; then
    run_step "Step 2: Create pose pickle" bash "$PROJ_DIR/02_make_pose.sh"
else
    log "Step 2: pose_euler.pkl exists, skipping."
fi

# Step 3: Mask
if [[ ! -f "$PROJ_DIR/mask.mrc" ]]; then
    run_step "Step 3: Create solvent mask" python "$PROJ_DIR/03_make_mask.py"
else
    log "Step 3: mask.mrc exists, skipping."
fi

# Step 4: Training
if [[ $SKIP_TRAIN -eq 1 ]]; then
    log "Step 4: Training skipped (--skip-train)."
elif [[ -n "$EPOCH" && -f "$PROJ_DIR/output/z.${EPOCH}.pkl" ]]; then
    log "Step 4: z.${EPOCH}.pkl exists, skipping training."
else
    run_step "Step 4: Train OPUS-ET" bash "$PROJ_DIR/04_train.sh"
fi

# Auto-detect last epoch if not specified
if [[ -z "$EPOCH" ]]; then
    EPOCH=$(ls "$PROJ_DIR/output/z".*.pkl 2>/dev/null \
            | sed 's/.*z\.\([0-9]*\)\.pkl/\1/' \
            | sort -n | tail -1)
    [[ -n "$EPOCH" ]] || { log "ERROR: No z.*.pkl found in $PROJ_DIR/output/"; exit 1; }
    log "Using epoch $EPOCH for analysis."
fi

# Step 5: Analysis
ANALYZE_DIR="$PROJ_DIR/output/analyze.${EPOCH}"
if [[ ! -d "$ANALYZE_DIR/kmeans${K}" ]]; then
    run_step "Step 5: Latent space analysis (epoch=$EPOCH K=$K)" \
        bash "$PROJ_DIR/05_analyze.sh" "$EPOCH" "$K"
else
    log "Step 5: $ANALYZE_DIR/kmeans${K} exists, skipping."
fi

# Step 6: Volume generation
VOL_EXAMPLE="$ANALYZE_DIR/kmeans${K}/reference0.mrc"
if [[ ! -f "$VOL_EXAMPLE" ]]; then
    run_step "Step 6: Generate class volumes" \
        bash "$PROJ_DIR/06_eval_vol.sh" "$EPOCH" "$K"
else
    log "Step 6: Volumes exist, skipping."
fi

# Step 7: Split STAR
SPLIT_DIR="$PROJ_DIR/split_star"
if [[ ! -d "$SPLIT_DIR" ]] || [[ -z "$(ls "$SPLIT_DIR"/pre*.star 2>/dev/null)" ]]; then
    run_step "Step 7: Split STAR by class" \
        bash "$PROJ_DIR/07_split_star.sh" "$EPOCH" "$K"
else
    log "Step 7: split_star/ exists, skipping."
fi

log "Pipeline complete."
echo ""
echo "=== Results ==="
echo "  Consensus map:  $PROJ_DIR/consensus.mrc"
echo "  UMAP plot:      $ANALYZE_DIR/umap.png"
echo "  PCA plot:       $ANALYZE_DIR/z_pca.png"
echo "  Class volumes:  $ANALYZE_DIR/kmeans${K}/reference*.mrc"
echo "  Split STAR:     $SPLIT_DIR/pre*.star"
echo "  Full log:       $LOG"
