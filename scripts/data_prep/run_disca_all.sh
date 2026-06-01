#!/bin/bash
source ~/miniforge3/etc/profile.d/conda.sh; conda activate disca
cd ~/Research/disca_work
export DISCA_INPUT=~/Research/disca_work/disca_input_672.pickle
for K in 2 3 4; do
  echo "############## DISCA k=$K ##############"
  DISCA_K=$K DISCA_TAG=k$K python torch_disca_run.py > log_k$K.txt 2>&1
  echo "k=$K exit=$? ; last cluster sizes:"; grep "Cluster sizes" log_k$K.txt | tail -1
done
echo "ALL DONE"
