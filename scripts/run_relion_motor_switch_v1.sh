#!/bin/bash
# run_relion_motor_switch_v1.sh — RELION Class3D on motor_switch synthetic data.
# v1: GT-seeded (CCW + CW averages) + firstiter_cc + skip_align + tau2_fudge=8.
#     k=2 (two real conformational states; junk particles treated as noise).
#     Same params as motor_easy v4 which gave best ARI=0.475.
# Run from ~/Research/STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REFS=outputs/FM_switch/relion/run_r01/class_refs.star
MASK=outputs/FM_switch/relion/run_r01/solvent_mask.mrc
STAR=outputs/FM_switch/relion/run_r01/particles_wedge.star
OUT=outputs/FM_switch/relion/run_r01/Class3D/k2_wedge_v1
ITER="${ITER:-35}"

mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION Class3D motor_switch K=2 v1 (GT-seeded firstiter_cc) ==="

"$RELION" \
  --i "$STAR" --ref "$REFS" --o "$OUT/run" \
  --K 2 --iter "$ITER" --tau2_fudge 8 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 \
  --dont_combine_weights_via_disc --trust_ref_size --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1

echo "=== DONE $(date +%H:%M:%S) (exit $?) -> $OUT ==="
