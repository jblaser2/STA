#!/bin/bash
# run_relion_class3d_tuned.sh — T4P Class3D with three targeted fixes over the masked run:
#   1. --ini_high 30    : include the ~30-40 Å conformational signal from iteration 1
#   2. --particle_diameter 500 : give RELION a real background annulus for noise estimation
#   3. --firstiter_cc   : hard CC assignment in iter 1 to break symmetric initialization
# Also keeps --solvent_mask (v2 cylindrical mask, r=13 vox, below-center).
# Runs wedge CTF only; k=2 and k=3 by default.
# Run from the STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REF=outputs/relion/initial_ref.mrc
MASK=T4P_mask/cylindrical_mask_v2.mrc
STAR=outputs/relion/particles_wedge.star
OUTROOT=outputs/relion/Class3D
KS="${KS:-2 3}"
ITER="${ITER:-25}"

for K in $KS; do
  OUT="${OUTROOT}/k${K}_wedge_tuned"
  mkdir -p "$OUT"
  echo "=== $(date +%H:%M:%S)  RELION Class3D (tuned)  K=$K ==="
  "$RELION" \
    --i "$STAR" --ref "$REF" --o "$OUT/run" \
    --K "$K" --iter "$ITER" --tau2_fudge 4 --ini_high 30 \
    --particle_diameter 500 --skip_align --firstiter_cc \
    --sym C1 --ctf --skip_subtomo_multi \
    --solvent_mask "$MASK" --flatten_solvent --zero_mask \
    --pad 2 --norm --scale \
    --dont_combine_weights_via_disc --j 8 --gpu "" \
    > "$OUT/run.log" 2>&1
  echo "    done -> $OUT (exit $?)"
done
echo "=== ALL RUNS COMPLETE $(date +%H:%M:%S) ==="
