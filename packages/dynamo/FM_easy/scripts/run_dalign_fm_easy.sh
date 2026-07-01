#!/usr/bin/env bash
# run_dalign_fm_easy.sh — Full FM_easy production alignment pipeline
#
# Steps:
#   1. setup_dalign_fm_easy.py  — build data dir, table, labels, initial ref
#   2. dalign_fm_easy.m         — Dynamo MRA alignment (9 iters, 3 rounds)
#   3. extract_dalign_fm_easy.py — apply alignment, write merged_AC_dalign/
#
# Usage (from STA repo root, inside tmux):
#   bash packages/dynamo/FM_easy/scripts/run_dalign_fm_easy.sh 2>&1 | tee run_dalign.log
#
# Runtime estimate: ~45-90 min (9 iters × 542 particles × 3 rounds).
# Monitor: tail -f run_dalign.log

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../" && pwd)"
LOG="${REPO_ROOT}/packages/dynamo/dynamo_outputs/easy_AC_dalign/run_dalign.log"

mkdir -p "${REPO_ROOT}/packages/dynamo/dynamo_outputs/easy_AC_dalign"
echo "=== FM_easy dalign pipeline $(date) ===" | tee -a "$LOG"

# Step 1: setup
echo "[1/3] Setting up data directory and initial reference..." | tee -a "$LOG"
conda run -n eman2 python3 "${SCRIPT_DIR}/setup_dalign_fm_easy.py" 2>&1 | tee -a "$LOG"

# Step 2: Dynamo alignment (MW_SERVICE_HOST_DISABLE already set in the .m script)
echo "[2/3] Running Dynamo alignment..." | tee -a "$LOG"
MW_SERVICE_HOST_DISABLE=1 ~/Applications/matlab/bin/matlab -nodisplay -batch \
    "cd('${SCRIPT_DIR}'); run('dalign_fm_easy.m')" 2>&1 | tee -a "$LOG"

# Step 3: extract aligned particles
echo "[3/3] Extracting aligned particles..." | tee -a "$LOG"
conda run -n eman2 python3 "${SCRIPT_DIR}/extract_dalign_fm_easy.py" 2>&1 | tee -a "$LOG"

echo "=== Pipeline complete $(date) ===" | tee -a "$LOG"
echo "Aligned set: ~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_dalign/"
echo "Next: re-run all 10 packages from merged_AC_dalign/ and compare ARI with GT-pose results"
