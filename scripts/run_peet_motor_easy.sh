#!/bin/bash
# run_peet_motor_easy.sh — PEET PCA + k-means on motor_easy synthetic data.
# Assumes motor_easy_stack.py has been run to create the stacked MRC + MOTL.
# Run from ~/Research/peet/motor_easy/results/
set -e

PRM=~/Research/STA/peet/motor_easy.prm
REF=~/Research/peet/motor_easy/results/motor_easy_initial_ref.mrc
N=634

source ~/Applications/IMOD-linux.sh
source ~/Applications/Particle.sh

echo "=== $(date +%H:%M:%S)  PEET averageAll motor_easy ==="
averageAll "$PRM" 1 2>&1 | tee averageAll_motor_easy.log

# averageAll outputs motor_easy_avg_Tom1_Iter1.mrc — copy to ref path
if [ -f motor_easy_avg_Tom1_Iter1.mrc ]; then
    cp motor_easy_avg_Tom1_Iter1.mrc "$REF"
    echo "Copied initial reference -> $REF"
else
    echo "ERROR: averageAll output not found. Check averageAll_motor_easy.log"
    exit 1
fi

echo "=== $(date +%H:%M:%S)  PEET PCA motor_easy ==="
pca "$PRM" 1 $N "$REF" 1 2>&1 | tee pca_motor_easy.log

echo "=== $(date +%H:%M:%S)  PCA done. Run k-means manually: ==="
echo "  cd ~/Research/peet/motor_easy/results"
echo "  # PCs are in motor_easy_PCA_Tom1_Iter2.csv"
echo "  # Run: python3 ~/Research/STA/peet/results/post_sweep.py (adapt paths)"
echo "  # Or use IMOD's PcaForSubvolumes GUI for k-means classification"
