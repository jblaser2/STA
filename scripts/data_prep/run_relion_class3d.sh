#!/bin/bash
# run_relion_class3d.sh — classic 3D-subtomogram classification on the pre-aligned
# T4P particles using RELION 5's retained subtomo path (driven directly, no GUI
# tomo pipeline). Runs the k x {wedge,uniform} matrix serially on the single GPU.
#
# Validated flag set (see session notes):
#   --ctf            : 3D CTF correction; requires rlnCtfImage per particle
#   --skip_subtomo_multi : our CTF cubes are plain 80^3 (no multiplicity half)
#   --zero_mask      : mask solvent with zeros (noise-masking unsupported on GPU+3D)
#   --skip_align     : pure classification; particles are already aligned (poses=0)
# Run from the STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REF=outputs/relion/initial_ref.mrc
OUTROOT=outputs/relion/Class3D
KS="${KS:-2 3 4}"
ITER="${ITER:-25}"

for ctf in wedge uniform; do
  STAR="outputs/relion/particles_${ctf}.star"
  for K in $KS; do
    OUT="${OUTROOT}/k${K}_${ctf}"
    mkdir -p "$OUT"
    echo "=== $(date +%H:%M:%S)  RELION Class3D  K=$K  ctf=$ctf ==="
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
