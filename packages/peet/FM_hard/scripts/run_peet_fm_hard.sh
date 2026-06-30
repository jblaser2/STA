#!/bin/bash
# PEET WMD-PCA + k-means on FM_hard (813 particles, 96^3, 3 classes: base/basal_body/mature).
# k=3; pcaFnParticleMask = diff_mask_hard.mrc.
# Run from STA repo root.
set -e
source ~/Applications/IMOD-linux.sh
source ~/Applications/Particle.sh

RES=~/Research/peet/motor_hard/results
PRM=$RES/motor_hard.prm
REF=$RES/motor_hard_initial_ref.mrc
N=813
STA=~/Research/STA

echo "=== Step 1: build stack + prm ($(date +%H:%M:%S)) ==="
conda run -n eman2 python3 packages/peet/FM_hard/scripts/make_stack_fm_hard.py

cd "$RES"   # PEET looks for MOTL files by basename in cwd

echo "=== Step 2: averageAll ($(date +%H:%M:%S)) ==="
averageAll "$PRM" 1 2>&1 | tee averageAll_motor_hard.log

# Copy average to reference path (PEET names it motor_hard_AvgVol_1P813.mrc or similar)
AVG=$(ls motor_hard_Avg*P${N}.mrc 2>/dev/null | head -1)
[ -n "$AVG" ] || AVG=$(ls motor_hard_Avg*.mrc 2>/dev/null | head -1)
[ -n "$AVG" ] && cp "$AVG" motor_hard_initial_ref.mrc || echo "WARNING: no avg mrc found"

echo "=== Step 3: pca ($(date +%H:%M:%S)) ==="
pca "$PRM" 1 "$N" motor_hard_initial_ref.mrc 1 2>&1 | tee pca_motor_hard.log

echo "=== Step 4: k-means + score ($(date +%H:%M:%S)) ==="
cd "$STA"
conda run -n eman2 python3 packages/peet/FM_hard/scripts/kmeans_fm_hard.py

echo "=== Done ($(date +%H:%M:%S)) ==="
