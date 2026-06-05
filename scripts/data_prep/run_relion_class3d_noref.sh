#!/bin/bash
# run_relion_class3d_noref.sh — T4P Class3D with random initialization.
#
# Root cause of previous collapse: all K classes started from the same single
# global-average reference, so CC/likelihood scores were identical for every
# class -> symmetric fixed point. Fix: omit --ref entirely so RELION randomizes
# particle-to-class assignments first, computes K distinct starting averages
# from those subsets, then begins soft EM from a non-symmetric state.
#
# Also keeps the three targeted parameter fixes:
#   --ini_high 30          : include ~30-40 A conformational signal from iter 1
#   --particle_diameter 500: give real background annulus for noise estimation
#   --firstiter_cc         : hard CC in iter 1 to reinforce the random-init split
#   --solvent_mask (v2)    : cylindrical mask focused on lower periplasmic ring
#
# Run from the STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
MASK=T4P_mask/cylindrical_mask_v2.mrc
STAR=outputs/relion/particles_wedge.star
OUTROOT=outputs/relion/Class3D
KS="${KS:-2 3}"
ITER="${ITER:-25}"
SEED="${SEED:-42}"

for K in $KS; do
  OUT="${OUTROOT}/k${K}_wedge_noref"
  mkdir -p "$OUT"
  echo "=== $(date +%H:%M:%S)  RELION Class3D (no-ref/random-init)  K=$K ==="
  "$RELION" \
    --i "$STAR" --o "$OUT/run" \
    --K "$K" --iter "$ITER" --tau2_fudge 4 --ini_high 30 \
    --particle_diameter 500 --skip_align --firstiter_cc \
    --sym C1 --ctf --skip_subtomo_multi \
    --solvent_mask "$MASK" --flatten_solvent --zero_mask \
    --pad 2 --norm --scale \
    --random_seed "$SEED" \
    --dont_combine_weights_via_disc --j 8 --gpu "" \
    > "$OUT/run.log" 2>&1
  echo "    done -> $OUT (exit $?)"
done
echo "=== ALL RUNS COMPLETE $(date +%H:%M:%S) ==="
