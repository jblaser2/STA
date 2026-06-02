#!/usr/bin/env bash
# PCA + k-means + UMAP analysis of the trained latent space.
#
# Usage:
#   ./05_analyze.sh [epoch] [K]
#   ./05_analyze.sh 19 8      # epoch 19, 8 clusters (defaults)
#   ./05_analyze.sh 14 10     # epoch 14, 10 clusters
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate opuset

OUTDIR="$SCRIPT_DIR/output"
NUMPC=2

# Auto-detect last trained epoch if not specified
if [[ $# -ge 1 ]]; then
    EPOCH="$1"
else
    EPOCH=$(ls "$OUTDIR"/z.*.pkl 2>/dev/null \
            | sed 's/.*z\.\([0-9]*\)\.pkl/\1/' \
            | sort -n | tail -1)
    [[ -n "$EPOCH" ]] || { echo "ERROR: No z.*.pkl files in $OUTDIR — run 04_train.sh first."; exit 1; }
    echo "Auto-detected last epoch: $EPOCH"
fi

K="${2:-8}"

[[ -f "$OUTDIR/z.${EPOCH}.pkl" ]] || { echo "ERROR: z.${EPOCH}.pkl not found."; exit 1; }

echo "Analyzing epoch=$EPOCH K=$K ..."
dsdsh analyze "$OUTDIR" "$EPOCH" "$NUMPC" "$K"

ANALYZE_DIR="$OUTDIR/analyze.${EPOCH}"
echo ""
echo "Analysis complete -> $ANALYZE_DIR/"
echo "  PCA plot:  $ANALYZE_DIR/z_pca.png"
echo "  UMAP:      $ANALYZE_DIR/umap.png"
echo "  K-means:   $ANALYZE_DIR/kmeans${K}/"
