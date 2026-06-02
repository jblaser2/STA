#!/usr/bin/env bash
# Generate one 3D density map per k-means cluster.
#
# Usage:
#   ./06_eval_vol.sh [epoch] [K]
#   ./06_eval_vol.sh 19 8     # defaults
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

OUTDIR="$SCRIPT_DIR/output"
APIX=13.33

if [[ $# -ge 1 ]]; then
    EPOCH="$1"
else
    EPOCH=$(ls "$OUTDIR"/z.*.pkl 2>/dev/null \
            | sed 's/.*z\.\([0-9]*\)\.pkl/\1/' \
            | sort -n | tail -1)
    [[ -n "$EPOCH" ]] || { echo "ERROR: No z.*.pkl in $OUTDIR — run 04_train.sh first."; exit 1; }
    echo "Auto-detected last epoch: $EPOCH"
fi

K="${2:-8}"
KMEANS_DIR="$OUTDIR/analyze.${EPOCH}/kmeans${K}"

[[ -d "$KMEANS_DIR" ]] || { echo "ERROR: $KMEANS_DIR not found — run 05_analyze.sh first."; exit 1; }

echo "Generating $K volumes for epoch=$EPOCH ..."
dsdsh eval_vol "$OUTDIR" "$EPOCH" kmeans "$K" "$APIX"

echo ""
echo "Volumes written to $KMEANS_DIR/"
ls "$KMEANS_DIR"/vol_k*.mrc 2>/dev/null | head -10
echo "Open in ChimeraX to inspect class structures."
