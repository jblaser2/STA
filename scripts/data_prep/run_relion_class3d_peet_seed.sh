#!/bin/bash
# run_relion_class3d_peet_seed.sh — DIAGNOSTIC: T4P Class3D seeded from PEET class averages.
#
# NOT a blind benchmark result. Used to find the diagnostic upper bound:
# can RELION maintain a separation when handed structurally distinct references?
# Starting from PEET v2 class averages (ring_complete + ring_altered) as references.
#
# Same corrected params as no-ref run:
#   --ini_high 30          : include ~30-40 A conformational signal from iter 1
#   --particle_diameter 500: real background annulus for noise estimation
#   --firstiter_cc         : hard CC in iter 1 to reinforce the PEET-seeded split
#   --solvent_mask (v2)    : cylindrical mask focused on lower periplasmic ring
#   NO --skip_align: allow RELION to re-check orientations (optional, try both)
#
# k=2 only (PEET v2 produced 2 structural classes).
# Run from the STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
SEED_MODEL=outputs/relion/Class3D/peet_seed_model.star
MASK=T4P_mask/cylindrical_mask_v2.mrc
STAR=outputs/relion/particles_wedge.star
OUT=outputs/relion/Class3D/k2_wedge_peet_seed
ITER="${ITER:-25}"

mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION Class3D (PEET-seeded)  K=2 ==="
"$RELION" \
  --i "$STAR" --ref "$SEED_MODEL" --o "$OUT/run" \
  --K 2 --iter "$ITER" --tau2_fudge 4 --ini_high 30 \
  --particle_diameter 500 --skip_align --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --pad 2 --norm --scale \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "    done -> $OUT (exit $?)"
echo "=== COMPLETE $(date +%H:%M:%S) ==="
