#!/bin/bash
# run_relion_class3d_noalign.sh — DIAGNOSTIC: T4P k=2 WITHOUT --skip_align.
#
# Tests whether allowing orientation search breaks the soft-EM collapse.
# Since our particles are pre-aligned (zero poses), RELION will search from
# zero rotation for each particle; the orientation-specific CC may introduce
# enough asymmetry to maintain class separation.
# Uses PEET-seeded refs + all corrected params (ini_high=30, diameter=500,
# firstiter_cc, v2 cylindrical mask).
# Run from the STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
SEED_MODEL=outputs/relion/Class3D/peet_seed_model.star
MASK=T4P_mask/cylindrical_mask_v2.mrc
STAR=outputs/relion/particles_wedge.star
OUT=outputs/relion/Class3D/k2_wedge_noalign
ITER="${ITER:-25}"

mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION Class3D (no-skip-align, PEET-seeded)  K=2 ==="
"$RELION" \
  --i "$STAR" --ref "$SEED_MODEL" --o "$OUT/run" \
  --K 2 --iter "$ITER" --tau2_fudge 4 --ini_high 30 \
  --particle_diameter 500 --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --pad 2 --norm --scale \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "    done -> $OUT (exit $?)"
echo "=== COMPLETE $(date +%H:%M:%S) ==="
