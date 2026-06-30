#!/bin/bash
# DISCA classification on FM_hard (813 particles, 3 classes, k=3).
# Run from STA repo root.
set -e

echo "=== Step 1: build DISCA input pickle ($(date +%H:%M:%S)) ==="
conda run -n eman2 python3 packages/disca/FM_hard/scripts/make_disca_input_fm_hard.py

echo "=== Step 2: DISCA k=3 ($(date +%H:%M:%S)) ==="
INPUT=~/Research/disca_work/disca_input_motor_hard.pickle
OUTDIR=~/Research/disca_work/model_motor_hard
mkdir -p "$OUTDIR"

cd ~/Research/disca_work
DISCA_INPUT="$INPUT" \
DISCA_K=3 \
DISCA_TAG=motor_hard_k3 \
DISCA_OUTDIR="$OUTDIR" \
conda run -n disca python torch_disca_run.py > "$OUTDIR/log_k3.txt" 2>&1
echo "k=3 done; last cluster line:"
grep "Cluster sizes\|sizes" "$OUTDIR/log_k3.txt" | tail -1

echo "=== Step 3: score ($(date +%H:%M:%S)) ==="
cd ~/Research/STA
conda run -n eman2 python3 packages/disca/FM_hard/scripts/score_disca_fm_hard.py

echo "=== Done ($(date +%H:%M:%S)) ==="
