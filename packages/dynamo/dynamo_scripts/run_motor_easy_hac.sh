#!/bin/bash
# Run Dynamo HAC on motor_easy synthetic data.
# Estimated ~30 min (CC matrix is cached — safe to interrupt/resume).
# Run from anywhere; outputs go to dynamo/dynamo_outputs/motor_easy_hac/
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MATLAB=~/Applications/matlab/bin/matlab

echo "=== Dynamo HAC motor_easy ($(date +%H:%M:%S)) ==="
"$MATLAB" -nodisplay -nosplash -nodesktop \
  -r "cd('${SCRIPT_DIR}'); run('dynamo_motor_easy_hac.m'); exit;" \
  2>&1 | tee /tmp/dynamo_motor_easy_hac.log

echo ""
echo "=== Scoring ($(date +%H:%M:%S)) ==="
python3 "${SCRIPT_DIR}/score_dynamo_motor_easy.py"
echo "=== Done ($(date +%H:%M:%S)) ==="
