#!/bin/bash
# PEET WMD-PCA + k-means on the REDESIGNED 2-class hc FM_easy (542 A/C), k=2.
set -e
source ~/Applications/IMOD-linux.sh
source ~/Applications/Particle.sh
RES=~/Research/peet/motor_easy_hc/results
PRM=$RES/motor_easy_hc.prm
REF=$RES/motor_easy_hc_initial_ref.mrc
N=542
STA=~/Research/STA
cd "$RES"

echo "=== averageAll ($(date +%H:%M:%S)) ==="
averageAll "$PRM" 1 2>&1 | tee averageAll_motor_easy_hc.log
cp motor_easy_hc_AvgVol_1P542.mrc "$REF"

echo "=== pca ($(date +%H:%M:%S)) ==="
pca "$PRM" 1 "$N" "$REF" 1 2>&1 | tee pca_motor_easy_hc.log

echo "=== kmeans + score ($(date +%H:%M:%S)) ==="
cd "$STA"
conda run -n eman2 python3 packages/peet/FM_easy/scripts/kmeans_motor_easy_hc.py

GT=~/Research/synthetic_sta/motor_easy/hc_test_x6/subtomos/merged_AC_full/labels.csv
for pc in pc1_3 pc1_5 pc1_10; do
  PRED=outputs/FM_easy/peet/predictions_k2_${pc}.csv
  [ -f "$PRED" ] && conda run -n eman2 python3 scripts/eval/score_synthetic.py \
     --pred "$PRED" --gt "$GT" --package peet --k 2 --run "k2_${pc}_AC_hc_x6_542" \
     --notes "WMD-PCA k-means ${pc}; 2-class A/C x6 542p"
done
echo "=== DONE ($(date +%H:%M:%S)) ==="
