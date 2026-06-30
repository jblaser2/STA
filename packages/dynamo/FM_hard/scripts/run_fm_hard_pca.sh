#!/bin/bash
# Dynamo dpkpca on FM_hard (813 particles, 96^3, k=3).
# Run from STA repo root.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MATLAB=~/Applications/matlab/bin/matlab
PYTHON=~/conda-envs/eman2/bin/python3

echo "=== Step 1: Setup data folder + table ($(date +%H:%M:%S)) ==="
"$PYTHON" "${SCRIPT_DIR}/setup_fm_hard_pca.py"

echo ""
echo "=== Step 2: dpkpca MATLAB ($(date +%H:%M:%S)) ==="
export LD_PRELOAD=/usr/lib64/libmkl_rt.so.2
"$MATLAB" -nodisplay -nosplash -nodesktop \
  -r "cd('${SCRIPT_DIR}'); run('dynamo_fm_hard_pca.m'); exit;" \
  2>&1 | tee /tmp/dynamo_fm_hard_pca.log

echo ""
echo "=== Step 3: Scoring ($(date +%H:%M:%S)) ==="
"$PYTHON" "${SCRIPT_DIR}/score_dynamo_fm_hard.py"

echo "=== Done ($(date +%H:%M:%S)) ==="
