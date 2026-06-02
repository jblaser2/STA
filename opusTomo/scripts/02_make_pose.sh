#!/usr/bin/env bash
# Convert zero Euler angles in the STAR file to the rotation-matrix pickle
# that OPUS-ET expects. Since particles are z-axis aligned, all angles are 0.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

STAR="$SCRIPT_DIR/particles.star"
OUT="$SCRIPT_DIR/pose_euler.pkl"

[[ -f "$STAR" ]] || { echo "ERROR: $STAR not found — run 01_write_star.py first."; exit 1; }

echo "Creating pose pickle from $STAR ..."
dsd parse_pose_star "$STAR" \
    -D 80 \
    --Apix 13.33 \
    -o "$OUT"

echo "Pose pickle -> $OUT"
