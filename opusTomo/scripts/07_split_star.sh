#!/usr/bin/env bash
# Split particles.star into one STAR file per k-means cluster.
# Output: split_star/pre0.star ... pre{K-1}.star
#
# Usage:
#   ./07_split_star.sh [epoch] [K]
#   ./07_split_star.sh 19 8     # defaults
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

OUTDIR="$SCRIPT_DIR/output"
STAR="$SCRIPT_DIR/particles.star"
APIX=13.33
# Effective box size = lattice_args['D'] - 1; for 80^3 volumes this is 80.
# Verify after training with: dsd view_config output/config.pkl | grep "'D'"
D=80

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
LABELS="$OUTDIR/analyze.${EPOCH}/kmeans${K}/labels.pkl"
SPLIT_DIR="$SCRIPT_DIR/split_star"

[[ -f "$LABELS" ]] || { echo "ERROR: $LABELS not found — run 05_analyze.sh first."; exit 1; }

mkdir -p "$SPLIT_DIR"

echo "Splitting STAR by cluster (epoch=$EPOCH K=$K) ..."
dsd parse_pose_star "$STAR" \
    -D "$D" \
    --Apix "$APIX" \
    --labels "$LABELS" \
    --outdir "$SPLIT_DIR"

echo ""
echo "Per-class STAR files -> $SPLIT_DIR/"
ls "$SPLIT_DIR"/pre*.star 2>/dev/null
echo ""
echo "Particle counts per class:"
for f in "$SPLIT_DIR"/pre*.star; do
    n=$(grep -c '\.mrc' "$f" 2>/dev/null || echo 0)
    echo "  $(basename $f): $n particles"
done
