#!/bin/bash
# Run DISCA on T4P with the v2 cylindrical mask (r=13, h_pos=0, h_neg=25).
# Mirrors PyTom/PEET mask usage: multiply each 80^3 subtomogram by the mask
# before Fourier-cropping to 32^3, so DISCA sees only the pilus signal.
set -e
source ~/miniforge3/etc/profile.d/conda.sh; conda activate disca

MASK=~/Research/STA/data/T4P_mask/cylindrical_mask_v2.mrc
PICKLE=~/Research/disca_work/disca_input_672_cyl_v2.pickle
SUBTOMO_DIR=~/Research/STA/data/T4P_subtomos

echo "=== Building masked pickle ==="
python ~/Research/STA/scripts/data_prep/build_disca_input.py \
    --subtomo-dir "$SUBTOMO_DIR" \
    --mask "$MASK" \
    --out "$PICKLE"

cd ~/Research/disca_work
export DISCA_INPUT="$PICKLE"
for K in 2 3 4; do
  echo "############## DISCA (cyl_v2) k=$K ##############"
  DISCA_K=$K DISCA_TAG=cyl_v2_k$K DISCA_OUTDIR=./model_cyl_v2 \
    python torch_disca_run.py > log_cyl_v2_k$K.txt 2>&1
  echo "k=$K exit=$?"
  grep "Cluster sizes" log_cyl_v2_k$K.txt | tail -1
done
echo "ALL DONE"
