#!/bin/bash
# run_relion_motor_easy_v4.sh — RELION Class3D on motor_easy synthetic data.
# v4: same as v3 (GT-seeded + firstiter_cc + tau2_fudge=8) but on redesigned
#     class C (C_noRodHook = C-ring only, CUT2_C=46.5). Updated initial_ref.mrc
#     and avg_classC_aligned.mrc (re-simulated 2026-06-05).
# Run from ~/Research/STA project root.
set -e

RELION=/home/jblaser2/relion-install/bin/relion_refine
REFS=outputs/relion_motor_easy/class_refs.star
MASK=outputs/relion_motor_easy/solvent_mask.mrc
ITER="${ITER:-35}"

STAR="outputs/relion_motor_easy/particles_wedge.star"
OUT="outputs/relion_motor_easy/Class3D/k3_wedge_v4"
mkdir -p "$OUT"
echo "=== $(date +%H:%M:%S)  RELION Class3D motor_easy K=3 v4 (firstiter_cc + GT-seeded, new class C) ==="

"$RELION" \
  --i "$STAR" --ref "$REFS" --o "$OUT/run" \
  --K 3 --iter "$ITER" --tau2_fudge 8 --ini_high 60 \
  --solvent_mask "$MASK" --flatten_solvent --zero_mask \
  --skip_align --firstiter_cc \
  --sym C1 --ctf --skip_subtomo_multi --pad 2 \
  --dont_combine_weights_via_disc --j 8 --gpu "" \
  > "$OUT/run.log" 2>&1
echo "=== DONE $(date +%H:%M:%S) (exit $?) -> $OUT ==="
