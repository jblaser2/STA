#!/bin/bash
# run_relion_motor_easy_v3.sh — RELION Class3D on motor_easy synthetic data.
# v3: GT-seeded + firstiter_cc (CC assignment on iter 1 breaks EM divergence)
#     + higher tau2_fudge=8 to amplify signal, no --norm --scale (avoid scale issues).
# Background on failure: v1/v2 diverge because per-particle SNR is low → soft EM
#   assignments ~1/3 each → M-step computes near-global-averages → crash.
#   firstiter_cc assigns iter-1 by CC (equivalent to our diagnostic which gives ARI~0.29),
#   producing clean initial class averages for subsequent likelihood iterations.
# Run from ~/Research/STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REFS=outputs/relion_motor_easy/class_refs.star
MASK=outputs/relion_motor_easy/solvent_mask.mrc
ITER="${ITER:-35}"

STAR="outputs/relion_motor_easy/particles_wedge.star"
OUT="outputs/relion_motor_easy/Class3D/k3_wedge_v3"
mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION Class3D motor_easy K=3 v3 (firstiter_cc + GT-seeded) ==="

"$RELION" \
  --i "$STAR" --ref "$REFS" --o "$OUT/run" \
  --K 3 --iter "$ITER" --tau2_fudge 8 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "=== DONE $(date +%H:%M:%S) (exit $?) -> $OUT ==="
