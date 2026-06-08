#!/bin/bash
# Run Dynamo dpkpca on motor_easy synthetic data.
# Step 1: Python setup (symlinks + Dynamo table) — fast
# Step 2: MATLAB dpkpca (prealign→ccmatrix→eigentable→eigenvolumes) — ~15-30 min
# Step 3: Score k=2,3 against GT
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MATLAB=~/Applications/matlab/bin/matlab
PYTHON=~/conda-envs/eman2/bin/python3

echo "=== Step 1: Setup data folder + table ($(date +%H:%M:%S)) ==="
"$PYTHON" "${SCRIPT_DIR}/setup_motor_easy_pca.py"

echo ""
echo "=== Step 2: dpkpca MATLAB ($(date +%H:%M:%S)) ==="
"$MATLAB" -nodisplay -nosplash -nodesktop \
  -r "cd('${SCRIPT_DIR}'); run('dynamo_motor_easy_pca.m'); exit;" \
  2>&1 | tee /tmp/dynamo_motor_easy_pca.log

echo ""
echo "=== Step 3: Scoring ($(date +%H:%M:%S)) ==="
"$PYTHON" "${SCRIPT_DIR}/score_dynamo_motor_easy.py" \
  --outdir "$SCRIPT_DIR/../dynamo_outputs/motor_easy_pca" \
  --run_suffix pca_cnew 2>&1 || \
  "$PYTHON" "${SCRIPT_DIR}/score_dynamo_motor_easy.py"

echo "=== Done ($(date +%H:%M:%S)) ==="
