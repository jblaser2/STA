#!/bin/bash
# run_relion_class3d_masked.sh — T4P Class3D classification with T4P cylindrical mask.
# Same as run_relion_class3d.sh but adds --solvent_mask + --flatten_solvent using the
# v2 cylindrical mask (r=13 vox, h_pos=0, h_neg=25; focuses on lower periplasmic ring).
# Runs wedge CTF only (better model for T4P); k=2 and k=3 by default.
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
  OUT="${OUTROOT}/k${K}_wedge_masked"
  mkdir -p "$OUT"
  echo "=== $(date +%H:%M:%S)  RELION Class3D (masked)  K=$K ==="
  "$RELION" \
    --i "$STAR" --ref "$REF" --o "$OUT/run" \
    --K "$K" --iter "$ITER" --tau2_fudge 4 --ini_high 60 \
    --particle_diameter 960 --skip_align \
    --sym C1 --ctf --skip_subtomo_multi \
    --solvent_mask "$MASK" --flatten_solvent --zero_mask \
    --pad 2 --norm --scale \
    --dont_combine_weights_via_disc --j 8 --gpu "" \
    > "$OUT/run.log" 2>&1
  echo "    done -> $OUT (exit $?)"
done
echo "=== ALL RUNS COMPLETE $(date +%H:%M:%S) ==="
