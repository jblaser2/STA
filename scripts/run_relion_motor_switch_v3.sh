#!/bin/bash
# run_relion_motor_switch_v3.sh — RELION Class3D on motor_switch 5 A/px data.
# v3: GT-aligned particles (canonical orientation), GT-seeded refs,
#     firstiter_cc + skip_align + tau2_fudge=8. Same approach as motor_easy v4 (ARI=0.475).
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REFS=outputs/FM_switch/relion/run_r02/class_refs.star
MASK=outputs/FM_switch/relion/run_r02/solvent_mask.mrc
STAR=outputs/FM_switch/relion/run_r02/particles_wedge_aln.star
OUT=outputs/FM_switch/relion/run_r02/Class3D/k2_v3
ITER="${ITER:-35}"

mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION motor_switch 5A/px K=2 v3 (GT-aligned + GT-seeded) ==="

"$RELION" \
  --i "$STAR" --ref "$REFS" --o "$OUT/run" \
  --K 2 --iter "$ITER" --tau2_fudge 8 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 \
  --dont_combine_weights_via_disc --trust_ref_size --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1

echo "=== DONE $(date +%H:%M:%S) (exit $?) -> $OUT ==="
