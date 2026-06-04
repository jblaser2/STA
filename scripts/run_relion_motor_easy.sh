#!/bin/bash
# run_relion_motor_easy.sh — RELION Class3D on motor_easy synthetic data.
# GT-aligned subtomos (96^3, 13.33 A/px, identity starting angles).
# Uses same flag set as real T4P run; wedge CTF at ±60°.
# Run from ~/Research/STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REF=outputs/relion_motor_easy/initial_ref.mrc
OUTROOT=outputs/relion_motor_easy/Class3D
KS="${KS:-2 3}"
ITER="${ITER:-25}"

for ctf in wedge; do          # run wedge first; add 'uniform' for comparison
  STAR="outputs/relion_motor_easy/particles_${ctf}.star"
  for K in $KS; do
    OUT="${OUTROOT}/k${K}_${ctf}"
    mkdir -p "$OUT"
    echo "=== $(date +%H:%M:%S)  RELION Class3D motor_easy  K=$K  ctf=$ctf ==="
    "$RELION" \
      --i "$STAR" --ref "$REF" --o "$OUT/run" \
      --K "$K" --iter "$ITER" --tau2_fudge 4 --ini_high 60 \
      --particle_diameter 960 --skip_align \
      --sym C1 --ctf --skip_subtomo_multi --zero_mask --pad 2 --norm --scale \
      --dont_combine_weights_via_disc --j 8 --gpu "" \
      > "$OUT/run.log" 2>&1
    echo "    done -> $OUT (exit $?)"
  done
done
echo "=== ALL RUNS COMPLETE $(date +%H:%M:%S) ==="
