#!/usr/bin/env bash
# Train the OPUS-ET beta-VAE on the pili subtomogram dataset.
#
# Single-GPU training on RTX 5080 (16 GB VRAM).
# 672 particles, 80^3 box, 13.33 A/px, no CTF metadata.
#
# Usage:
#   ./04_train.sh            # run 20 epochs from scratch
#   ./04_train.sh <epoch>    # resume from weights.<epoch>.pkl
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

STAR="$SCRIPT_DIR/particles.star"
POSES="$SCRIPT_DIR/pose_euler.pkl"
MASK="$SCRIPT_DIR/mask.mrc"
OUTDIR="$SCRIPT_DIR/output"
DATADIR="$HOME/Research/STA/subtomos_mrc"

for f in "$STAR" "$POSES" "$MASK"; do
    [[ -f "$f" ]] || { echo "ERROR: $f not found — run prerequisite scripts first."; exit 1; }
done
[[ -d "$DATADIR" ]] || { echo "ERROR: particle directory $DATADIR not found."; exit 1; }

mkdir -p "$OUTDIR"

# Build resume args if a checkpoint epoch is given
RESUME_ARGS=()
if [[ $# -ge 1 ]]; then
    RESUME_EPOCH="$1"
    WEIGHTS="$OUTDIR/weights.${RESUME_EPOCH}.pkl"
    LATENTS="$OUTDIR/z.${RESUME_EPOCH}.pkl"
    [[ -f "$WEIGHTS" ]] || { echo "ERROR: $WEIGHTS not found."; exit 1; }
    [[ -f "$LATENTS" ]] || { echo "ERROR: $LATENTS not found."; exit 1; }
    RESUME_ARGS=(--load "$WEIGHTS" --latents "$LATENTS")
    echo "Resuming from epoch $RESUME_EPOCH ..."
fi

echo "Starting training -> $OUTDIR"
dsd train_tomo "$STAR" \
    --poses "$POSES" \
    -n 20 \
    -b 16 \
    --zdim 8 \
    --zaffinedim 0 \
    --lr 1e-4 \
    --beta-control 1.0 \
    --lamb 0 \
    -o "$OUTDIR" \
    -r "$MASK" \
    --downfrac 1.0 \
    --templateres 128 \
    --angpix 13.33 \
    --datadir "$DATADIR" \
    --ctfalpha 0. --ctfbeta 0. \
    --split "$OUTDIR/split.pkl" \
    "${RESUME_ARGS[@]}"

echo "Training complete. Outputs in $OUTDIR/"
echo "Monitor loss: python ~/opusSrc/opusTomo/analysis_scripts/plot_loss.py $OUTDIR/run.log"
